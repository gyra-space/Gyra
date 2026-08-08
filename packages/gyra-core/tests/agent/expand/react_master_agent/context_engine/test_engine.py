"""ContextEngine 端到端测试（两段式压缩，无真实 LLM）。"""

import pytest

from gyra.agent.expand.react_master_agent.context_engine.compression import (
    CompressionConfig,
)
from gyra.agent.expand.react_master_agent.context_engine.engine import (
    ContextEngine,
    EngineConfig,
    InMemoryCompressionPersistence,
)

from .conftest import CountingSummarizer, FakeMsg, FakeWE, RecordingEmitter, ai_tool_call


def _engine(summarize=None, cfg=None, emitter=None, persistence=None):
    return ContextEngine(
        config=cfg or EngineConfig(),
        compression_persistence=persistence or InMemoryCompressionPersistence(),
        summarize_fn=summarize,
        events=emitter or RecordingEmitter(),
    )


@pytest.mark.asyncio
async def test_build_messages_end_to_end_no_orphans():
    msgs = [
        FakeMsg("c1", "human", "m1", content="查天气", rounds=1, created_at=1.0),
        FakeMsg("c1", "ai", "m2", content="查", tool_calls=[ai_tool_call("tc1", "wx")], rounds=1, created_at=2.0),
        FakeMsg("c1", "ai", "m3", content="晴", rounds=1, created_at=4.0),
    ]
    wls = {"c1": [FakeWE("wx", "tc1", result="晴25度", message_id="m2")]}
    out = await _engine().build_messages(msgs, wls, "c1", "s", 100000)
    roles = [m["role"] for m in out.messages]
    assert roles == ["human", "ai", "tool", "ai"]
    assert out.guard_report.ok or not [
        v for v in out.guard_report.violations if v.startswith(("I1", "I2"))
    ]


@pytest.mark.asyncio
async def test_missing_results_never_loop():
    # 缺失 WorkEntry 的 tool_call 不渲染成 tool 消息，也不出现在 tool_calls
    msgs = [
        FakeMsg("c1", "human", "m1", content="两件事", rounds=1, created_at=1.0),
        FakeMsg(
            "c1", "ai", "m2", content="",
            tool_calls=[ai_tool_call("tc_ok", "fa"), ai_tool_call("tc_missing", "fb")],
            rounds=1, created_at=2.0,
        ),
    ]
    wls = {"c1": [FakeWE("fa", "tc_ok", result="A", message_id="m2")]}
    out = await _engine().build_messages(msgs, wls, "c1", "s", 100000)
    assert not any(
        "result not available" in str(m.get("content", "")).lower() for m in out.messages
    )
    assert not any(m.get("tool_call_id") == "tc_missing" for m in out.messages)
    for m in out.messages:
        for t in m.get("tool_calls", []) or []:
            assert t["id"] != "tc_missing"


@pytest.mark.asyncio
async def test_no_messages_returns_empty():
    out = await _engine().build_messages([], {}, "c1", "s", 100000)
    assert out.messages == []
    assert out.compression_segment is None


@pytest.mark.asyncio
async def test_pure_engine_no_storage_dependency():
    msgs = [
        FakeMsg("c1", "human", "m1", content="q", rounds=1, created_at=1.0),
        FakeMsg("c1", "ai", "m2", content="a", rounds=1, created_at=2.0),
    ]
    out = await _engine().build_messages(msgs, {"c1": []}, "c1", "s", 100000)
    assert len(out.messages) == 2
    assert out.compression_segment is None  # 未触发压缩


@pytest.mark.asyncio
async def test_compression_triggered_prepends_summary():
    # 大量历史轮 -> 触发压缩 -> 摘要 user 消息置于最前
    msgs = []
    t = 0.0
    for r in range(1, 15):
        t += 1
        msgs.append(FakeMsg(f"c{r}", "human", f"u{r}", content="x" * 400, rounds=r, created_at=t))
        t += 1
        msgs.append(FakeMsg(f"c{r}", "ai", f"a{r}", content="y" * 400, rounds=r, created_at=t))
    current = "c14"
    cfg = EngineConfig(
        compression=CompressionConfig(threshold_ratio=0.5, retain_ratio=0.2, min_interval_turns=0),
        history_budget_ratio=1.0,
    )
    summ = CountingSummarizer("HISTORY_SUMMARY")
    out = await _engine(summarize=summ, cfg=cfg).build_messages(
        msgs, {f"c{r}": [] for r in range(1, 15)}, current, "s", 2000
    )
    # 触发了压缩
    assert out.compression_segment is not None
    assert summ.calls >= 1
    # 第一条是摘要 user 消息
    assert out.messages[0]["role"] == "human"
    assert "HISTORY_SUMMARY" in out.messages[0]["content"]
    # 最新段生效
    assert out.latest_segment is not None
    assert out.latest_segment.seq == 1


@pytest.mark.asyncio
async def test_incremental_compression_uses_prev_summary():
    # 第二次压缩：摘要输入应含第一次摘要 + 新待压缩段
    msgs = []
    t = 0.0
    for r in range(1, 21):
        t += 1
        msgs.append(FakeMsg(f"c{r}", "human", f"u{r}", content="x" * 400, rounds=r, created_at=t))
        t += 1
        msgs.append(FakeMsg(f"c{r}", "ai", f"a{r}", content="y" * 400, rounds=r, created_at=t))

    captured_prompts = []

    class _Capture:
        calls = 0

        async def __call__(self, prompt, max_tokens):
            _Capture.calls += 1
            captured_prompts.append(prompt)
            return f"SUMMARY_{_Capture.calls}"

    cfg = EngineConfig(
        compression=CompressionConfig(threshold_ratio=0.3, retain_ratio=0.1, min_interval_turns=0),
        history_budget_ratio=1.0,
    )
    engine = _engine(summarize=_Capture(), cfg=cfg)
    out = await engine.build_messages(msgs, {f"c{r}": [] for r in range(1, 21)}, "c20", "s", 2000)
    # 第一次压缩
    assert out.compression_segment is not None
    first_summary = out.latest_segment.summary
    # 第二次：再加几轮后重建
    more = []
    for r in range(21, 31):
        t += 1
        more.append(FakeMsg(f"c{r}", "human", f"u{r}", content="x" * 400, rounds=r, created_at=t))
        t += 1
        more.append(FakeMsg(f"c{r}", "ai", f"a{r}", content="y" * 400, rounds=r, created_at=t))
    out2 = await engine.build_messages(msgs + more, {f"c{r}": [] for r in range(1, 31)}, "c30", "s", 2000)
    # 第二次压缩发生
    if out2.compression_segment is not None:
        assert out2.latest_segment.seq == 2
        # 第二次摘要输入应含第一次摘要正文
        assert any("SUMMARY_1" in p for p in captured_prompts[1:])


@pytest.mark.asyncio
async def test_retained_tool_result_truncated():
    # 保留区大工具结果被截断（不触发压缩）
    long_result = "Z" * 5000
    msgs = [
        FakeMsg("c1", "human", "m1", content="q", rounds=1, created_at=1.0),
        FakeMsg("c1", "ai", "m2", content="", tool_calls=[ai_tool_call("tc1", "fa")], rounds=1, created_at=2.0),
        FakeMsg("c1", "human", "m3", content="q2", rounds=2, created_at=3.0),
    ]
    wls = {"c1": [FakeWE("fa", "tc1", result=long_result, message_id="m2", tokens=1250)]}
    cfg = EngineConfig(
        compression=CompressionConfig(retain_tool_result_max_length=400),
        history_budget_ratio=1.0,
    )
    out = await _engine(cfg=cfg).build_messages(msgs, wls, "c1", "s", 100000)
    tool_msgs = [m for m in out.messages if m["role"] == "tool"]
    assert tool_msgs  # 保留区有工具结果
    assert len(str(tool_msgs[0]["content"])) < 5000  # 被截断


@pytest.mark.asyncio
async def test_history_breakdown_populated():
    # 无压缩：compressed=0, retained=全部单元 token
    msgs = [
        FakeMsg("c1", "human", "m1", content="q", rounds=1, created_at=1.0),
        FakeMsg("c1", "ai", "m2", content="a", rounds=1, created_at=2.0),
    ]
    out = await _engine().build_messages(msgs, {"c1": []}, "c1", "s", 100000)
    assert out.history_breakdown["compressed"] == 0
    assert out.history_breakdown["retained"] > 0

    # 触发压缩：compressed>0（摘要）, retained>0（保留区）
    long_msgs = []
    t = 0.0
    for r in range(1, 15):
        t += 1
        long_msgs.append(FakeMsg(f"c{r}", "human", f"u{r}", content="x" * 400, rounds=r, created_at=t))
        t += 1
        long_msgs.append(FakeMsg(f"c{r}", "ai", f"a{r}", content="y" * 400, rounds=r, created_at=t))
    cfg = EngineConfig(
        compression=CompressionConfig(threshold_ratio=0.5, retain_ratio=0.2, min_interval_turns=0),
        history_budget_ratio=1.0,
    )
    out2 = await _engine(summarize=CountingSummarizer("SUMMARY_TEXT"), cfg=cfg).build_messages(
        long_msgs, {f"c{r}": [] for r in range(1, 15)}, "c14", "s", 2000
    )
    assert out2.compression_segment is not None
    assert out2.history_breakdown["compressed"] > 0  # 摘要 token
    assert out2.history_breakdown["retained"] > 0  # 保留区 token


@pytest.mark.asyncio
async def test_summary_message_not_overwritten_by_injection_skipped():
    # 摘要是首条 human；验证其在 output 中保留（注入跳过逻辑由 runtime 负责，
    # 这里仅确认 engine 产出摘要为首条 human）
    msgs = []
    t = 0.0
    for r in range(1, 15):
        t += 1
        msgs.append(FakeMsg(f"c{r}", "human", f"u{r}", content="x" * 400, rounds=r, created_at=t))
        t += 1
        msgs.append(FakeMsg(f"c{r}", "ai", f"a{r}", content="y" * 400, rounds=r, created_at=t))
    cfg = EngineConfig(
        compression=CompressionConfig(threshold_ratio=0.5, retain_ratio=0.2, min_interval_turns=0),
        history_budget_ratio=1.0,
    )
    out = await _engine(summarize=CountingSummarizer("SUM"), cfg=cfg).build_messages(
        msgs, {f"c{r}": [] for r in range(1, 15)}, "c14", "s", 2000
    )
    assert out.messages[0]["role"] == "human"
    assert out.messages[0]["content"].startswith("[历史上下文摘要")


@pytest.mark.asyncio
async def test_compressed_messages_excluded_from_llm_output():
    # 压缩区原文不进 LLM 输出（被摘要替代）；保留区逐字保留
    msgs = []
    t = 0.0
    for r in range(1, 21):  # 旧轮：OLDCONTENT
        t += 1
        msgs.append(FakeMsg(f"c{r}", "human", f"u{r}", content="OLDCONTENT" * 50, rounds=r, created_at=t))
        t += 1
        msgs.append(FakeMsg(f"c{r}", "ai", f"a{r}", content="OLDCONTENT" * 50, rounds=r, created_at=t))
    for r in range(21, 23):  # 新轮：NEWCONTENT（应保留）
        t += 1
        msgs.append(FakeMsg(f"c{r}", "human", f"u{r}", content="NEWCONTENT" * 50, rounds=r, created_at=t))
        t += 1
        msgs.append(FakeMsg(f"c{r}", "ai", f"a{r}", content="NEWCONTENT" * 50, rounds=r, created_at=t))
    cfg = EngineConfig(
        compression=CompressionConfig(threshold_ratio=0.3, retain_ratio=0.1, min_interval_turns=0),
        history_budget_ratio=1.0,
    )
    out = await _engine(summarize=CountingSummarizer("MYSUMMARY"), cfg=cfg).build_messages(
        msgs, {f"c{r}": [] for r in range(1, 23)}, "c22", "s", 2000
    )
    assert out.compression_segment is not None
    all_text = " ".join(str(m.get("content", "")) for m in out.messages)
    assert "MYSUMMARY" in all_text  # 摘要在
    assert "NEWCONTENT" in all_text  # 保留区在
    assert "OLDCONTENT" not in all_text  # 压缩区原文被摘要替代，不进 LLM


@pytest.mark.asyncio
async def test_multiple_compression_single_summary_not_stacked():
    # 两次压缩后 LLM 输出只有一条摘要（最新），不堆叠 S1+S2
    msgs = []
    t = 0.0
    for r in range(1, 21):
        t += 1
        msgs.append(FakeMsg(f"c{r}", "human", f"u{r}", content="x" * 400, rounds=r, created_at=t))
        t += 1
        msgs.append(FakeMsg(f"c{r}", "ai", f"a{r}", content="y" * 400, rounds=r, created_at=t))
    cfg = EngineConfig(
        compression=CompressionConfig(threshold_ratio=0.3, retain_ratio=0.1, min_interval_turns=0),
        history_budget_ratio=1.0,
    )
    engine = _engine(summarize=CountingSummarizer("SUMMARY_TEXT"), cfg=cfg)
    out1 = await engine.build_messages(msgs, {f"c{r}": [] for r in range(1, 21)}, "c20", "s", 2000)
    assert out1.compression_segment is not None

    more = []
    for r in range(21, 31):
        t += 1
        more.append(FakeMsg(f"c{r}", "human", f"u{r}", content="x" * 400, rounds=r, created_at=t))
        t += 1
        more.append(FakeMsg(f"c{r}", "ai", f"a{r}", content="y" * 400, rounds=r, created_at=t))
    out2 = await engine.build_messages(msgs + more, {f"c{r}": [] for r in range(1, 31)}, "c30", "s", 2000)

    summary_count = sum(
        1 for m in out2.messages
        if isinstance(m.get("content"), str) and m["content"].startswith("[历史上下文摘要")
    )
    assert summary_count == 1, f"expected 1 summary, got {summary_count}"
    assert out2.latest_segment.seq >= 2


@pytest.mark.asyncio
async def test_segment_association_with_original_messages():
    # 压缩段通过 source_message_ids + boundary_message_id 关联原文 gpts_message；
    # 原文消息本身不被修改，仅被段引用
    msgs = []
    t = 0.0
    for r in range(1, 15):
        t += 1
        msgs.append(FakeMsg(f"c{r}", "human", f"u{r}", content="x" * 400, rounds=r, created_at=t))
        t += 1
        msgs.append(FakeMsg(f"c{r}", "ai", f"a{r}", content="y" * 400, rounds=r, created_at=t))
    cfg = EngineConfig(
        compression=CompressionConfig(threshold_ratio=0.5, retain_ratio=0.2, min_interval_turns=0),
        history_budget_ratio=1.0,
    )
    pers = InMemoryCompressionPersistence()
    engine = _engine(summarize=CountingSummarizer("SUMMARY_TEXT"), cfg=cfg, persistence=pers)
    out = await engine.build_messages(msgs, {f"c{r}": [] for r in range(1, 15)}, "c14", "s", 2000)
    seg = out.latest_segment
    assert seg is not None
    assert len(seg.source_message_ids) > 0  # 引用了原文 message_id
    assert seg.boundary_message_id in seg.source_message_ids  # boundary 是覆盖的最后一条
    # 持久化后可按 session 读回，关联信息完整
    loaded = await engine.compression.load_latest("s")
    assert loaded is not None
    assert loaded.source_message_ids == seg.source_message_ids
    assert loaded.boundary_message_id == seg.boundary_message_id


@pytest.mark.asyncio
async def test_ask_user_followup_same_conv_assembles_chronologically():
    # ask_user 追问复用 conv_id：一个 conv 内多条 user 消息，按时序组装、不丢
    msgs = [
        FakeMsg("c1", "human", "m1", content="问题1", rounds=1, created_at=1.0),
        FakeMsg("c1", "ai", "m2", content="需要澄清", rounds=1, created_at=2.0,
                tool_calls=[ai_tool_call("tc1", "ask_user")]),
        FakeMsg("c1", "human", "m3", content="补充回答", rounds=1, created_at=3.0),  # 同 conv_id
        FakeMsg("c1", "ai", "m4", content="最终回答", rounds=1, created_at=4.0),
    ]
    wls = {"c1": [FakeWE("ask_user", "tc1", result="等待用户输入", message_id="m2")]}
    out = await _engine().build_messages(msgs, wls, "c1", "s", 100000)
    roles = [m["role"] for m in out.messages]
    assert roles == ["human", "ai", "tool", "human", "ai"]  # 时序正确
    all_text = " ".join(str(m.get("content", "")) for m in out.messages)
    assert "问题1" in all_text and "补充回答" in all_text and "最终回答" in all_text


@pytest.mark.asyncio
async def test_token_counter_injection_unifies_counting():
    # 注入自定义 token_counter，验证 assembler/engine 用它而非 chars//4
    def counter(t):
        return len(t)  # 1 char = 1 token

    engine = ContextEngine(
        config=EngineConfig(),
        compression_persistence=InMemoryCompressionPersistence(),
        summarize_fn=None,
        token_counter=counter,
    )
    msgs = [
        FakeMsg("c1", "human", "m1", content="abcdefghij", rounds=1, created_at=1.0),  # 10 chars
        FakeMsg("c1", "ai", "m2", content="xyz", rounds=1, created_at=2.0),  # 3 chars
    ]
    out = await engine.build_messages(msgs, {"c1": []}, "c1", "s", 100000)
    # m1 是当前用户消息（最后一个 USER），从 retained_display 排除；retained=[m2]=3 tokens
    # 若用 chars//4 则为 max(1, 3//4)=1；用 counter(len) 则为 3
    assert out.history_breakdown["retained"] == 3


@pytest.mark.asyncio
async def test_current_user_appended_when_missing():
    # DB 读回竞态：当前 user 不在 messages 里 -> 引擎追加到末尾（不覆盖历史）
    msgs = [
        FakeMsg("c1", "human", "m1", content="历史问题", rounds=1, created_at=1.0),
        FakeMsg("c1", "ai", "m2", content="历史回答", rounds=1, created_at=2.0),
    ]
    out = await _engine().build_messages(
        msgs, {"c1": []}, "c1", "s", 100000, current_user_content="当前新问题"
    )
    all_text = " ".join(str(m.get("content", "")) for m in out.messages)
    assert "当前新问题" in all_text  # 被补上
    assert "历史问题" in all_text  # 历史 user 未被覆盖
    assert out.messages[-1]["role"] == "human"
    assert out.messages[-1]["content"] == "当前新问题"


@pytest.mark.asyncio
async def test_current_user_not_duplicated_when_present():
    # 当前 user 已在 messages 里 -> 不重复追加
    msgs = [
        FakeMsg("c1", "human", "m1", content="历史问题", rounds=1, created_at=1.0),
        FakeMsg("c1", "ai", "m2", content="历史回答", rounds=1, created_at=2.0),
        FakeMsg("c1", "human", "m3", content="当前新问题", rounds=2, created_at=3.0),
    ]
    out = await _engine().build_messages(
        msgs, {"c1": []}, "c1", "s", 100000, current_user_content="当前新问题"
    )
    user_msgs = [
        m for m in out.messages
        if m.get("role") == "human" and m.get("content") == "当前新问题"
    ]
    assert len(user_msgs) == 1  # 只一次
    assert out.messages[-1]["content"] == "当前新问题"  # 在时序末位（最新）


@pytest.mark.asyncio
async def test_current_user_not_moved_in_react_retry():
    # ReAct retry：[user, ai tool_call, tool] -- user 在首位，末条应是 tool，不追加到末尾
    msgs = [
        FakeMsg("c1", "human", "m1", content="执行任务", rounds=1, created_at=1.0),
        FakeMsg("c1", "ai", "m2", content="", tool_calls=[ai_tool_call("tc1", "fa")], rounds=1, created_at=2.0),
    ]
    wls = {"c1": [FakeWE("fa", "tc1", result="工具结果", message_id="m2")]}
    out = await _engine().build_messages(
        msgs, wls, "c1", "s", 100000, current_user_content="执行任务"
    )
    roles = [m["role"] for m in out.messages]
    assert roles == ["human", "ai", "tool"]  # user 首位、末条 tool，未被移动
    assert sum(1 for m in out.messages if m.get("content") == "执行任务") == 1
