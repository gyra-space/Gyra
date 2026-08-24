"""复现 V2Agent 多轮追问上下文丢失问题。

用真实代码路径验证：
1. 正常两轮对话（user/assistant 事件成对）→ 第三轮投影应包含完整历史
2. 模拟"第一轮 assistant 为空"（_emit_dialog_message 空内容直接 return）
   → 第二轮投影是否出现 user-user 连排（缺少 assistant），导致 LLM 把
   追问当作首问补充而"一直回答第一次提问"

运行: .venv/bin/python gyra_test/reproduce_v2_context.py
"""
import asyncio
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../packages/gyra-core/src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../packages/gyra-ext/src"))

from gyra.agent.core.agent import AgentContext


def make_agent(v2_state_dir: str, conv_session_id: str):
    from gyra.agent.expand.v2_agent.v2_agent import V2Agent

    ctx = AgentContext(
        user_id="admin",
        user_name="admin",
        staff_no="admin",
        conv_id=f"{conv_session_id}_1",
        conv_session_id=conv_session_id,
        gpts_app_code="repro-app",
        agent_app_code="repro-app",
    )
    agent = V2Agent(v2_state_dir=v2_state_dir)
    agent.bind(ctx)
    return agent


async def scenario_normal(tmp: str):
    """正常场景：两轮对话，assistant 事件成对写入，模拟第三轮追问。"""
    print("=" * 70)
    print("场景 A（对照组）：正常两轮，第三轮投影")
    print("=" * 70)
    sid = "repro-session-A"
    a1 = make_agent(tmp, sid)  # 第一轮实例
    a2 = make_agent(tmp, sid)  # 第二轮实例（serve 层每轮重建）

    # 第一轮
    await a1._emit_dialog_message("user", "帮我分析一下 8 月销售数据")
    await a1._emit_dialog_message("assistant", "8月销售额 1200 万，环比增长 15%，华东占比最高。")

    # 第二轮（追问）
    await a2._emit_dialog_message("user", "那华东大区的具体贡献是多少？")

    # 模拟 default_thinking 组装：读投影
    msgs = await a2._v2_build_full_context(sid)
    print("\n[事件投影结果]")
    for m in msgs:
        print(f"  role={m.get('role'):<10} content={str(m.get('content'))[:60]!r}")
    roles = [m.get("role") for m in msgs]
    has_assistant = "assistant" in roles
    print(f"\n=> 历史中含 assistant 回复: {has_assistant}")
    return has_assistant


async def scenario_missing_assistant(tmp: str):
    """缺陷场景：第一轮 assistant 最终答案为空 → _emit_dialog_message 直接 return。

    模拟代码路径：v2_agent.py:1189 ``if not content: return``。
    实际中常见于：ask_user 挂起 / run_loop 异常 / max_steps 触达 / 只出 thinking。
    """
    print("=" * 70)
    print("场景 B（缺陷复现）：第一轮 assistant 为空 → 第二轮投影")
    print("=" * 70)
    sid = "repro-session-B"
    a1 = make_agent(tmp, sid)
    a2 = make_agent(tmp, sid)

    # 第一轮：user 事件写入
    await a1._emit_dialog_message("user", "帮我分析一下 8 月销售数据")
    # 第一轮：assistant 为空（模拟 final_answer=""），事件不写
    await a1._emit_dialog_message("assistant", "")

    # 第二轮（追问）：user 事件写入
    await a2._emit_dialog_message("user", "那华东大区的具体贡献是多少？")

    # 读取事件日志原始记录
    store = a2._ensure_v2_state_store()
    events = await store.get_events(sid)
    print("\n[事件日志原始记录]")
    for e in events:
        if e.event_type.endswith("/message"):
            out = e.output or {}
            print(f"  seq={e.seq} {e.event_type:<20} content={str(out.get('text',''))[:50]!r}")

    msgs = await a2._v2_build_full_context(sid)
    print("\n[事件投影结果]（喂给 LLM 的消息序列）")
    for i, m in enumerate(msgs):
        print(f"  [{i}] role={m.get('role'):<10} content={str(m.get('content'))[:60]!r}")

    roles = [m.get("role") for m in msgs]
    consecutive_user = any(
        roles[i] == "user" and roles[i + 1] == "user"
        for i in range(len(roles) - 1)
    )
    print(f"\n=> 出现 user-user 连排（缺 assistant）: {consecutive_user}")
    print("=> 现象：LLM 会把追问 C 当作首问 A 的补充，继续回答 A —— 即'一直在回答第一次提问'")
    return consecutive_user


async def scenario_session_id_broken(tmp: str):
    """缺陷场景：每轮 conv_session_id 不同（前端未传 conv_uid，服务端 uuid 兜底）。

    模拟 api_v1.py:589-590 ``if not dialogue.conv_uid: dialogue.conv_uid = uuid.uuid1().hex``
    —— 每轮生成新会话 ID → 事件日志按不同 conv_id 分开落库 → 下轮投影为空。
    """
    print("=" * 70)
    print("场景 C（缺陷复现）：每轮 conv_session_id 不同 → 第二轮投影")
    print("=" * 70)
    sid1 = "repro-session-C1"
    sid2 = "repro-session-C2"  # 第二轮用了新 ID（会话断裂）
    a1 = make_agent(tmp, sid1)
    a2 = make_agent(tmp, sid2)

    # 第一轮（会话 C1）
    await a1._emit_dialog_message("user", "帮我分析一下 8 月销售数据")
    await a1._emit_dialog_message("assistant", "8月销售额 1200 万。")

    # 第二轮（会话 C2，全新 ID）
    await a2._emit_dialog_message("user", "那华东大区的具体贡献是多少？")

    msgs = await a2._v2_build_full_context(sid2)
    print("\n[第二轮事件投影结果]（喂给 LLM 的消息序列）")
    for i, m in enumerate(msgs):
        print(f"  [{i}] role={m.get('role'):<10} content={str(m.get('content'))[:60]!r}")
    print(f"\n=> 投影消息数: {len(msgs)}（若为 1 条即只有当前追问，历史全丢）")
    return len(msgs) <= 1


async def main():
    tmp = tempfile.mkdtemp(prefix="v2_repro_")
    print(f"v2_state_dir = {tmp}")
    ok_normal = await scenario_normal(tmp)
    ok_missing = await scenario_missing_assistant(tmp)
    ok_broken = await scenario_session_id_broken(tmp)
    print("\n" + "=" * 70)
    print(f"场景A 正常两轮历史保留:          {'OK' if ok_normal else 'FAIL'}")
    print(f"场景B 空 assistant 致 user 连排:  {'已复现' if ok_missing else '未复现'}")
    print(f"场景C 会话 ID 断裂致历史全丢:     {'已复现' if ok_broken else '未复现'}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
