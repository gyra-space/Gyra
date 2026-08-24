"""模拟 cs 场景空间 V2 Agent 多轮追问测试（走真实 HTTP API + SSE 流）。

验证修复后多轮上下文是否符合预期：
- 第一问设置一个"上下文锚点"（幸运数字 42）
- 追问直接验证锚点是否被第二轮 LLM 上下文携带
- 若第二轮答出 42 → 上下文保留（修复符合预期）；答非所问 → 上下文丢失

用法:
    .venv/bin/python gyra_test/test_v2_multi_round.py

前提: 服务已在 127.0.0.1:8888 运行（start.sh）。
"""
import json
import sys
import time
import urllib.request
import uuid

# permissions 插件已启用，需要 session token。用与服务器一致的 secret 签名。
from gyra_app.auth.session import create_session_token

HOST = "127.0.0.1"
PORT = 8888
BASE = f"http://{HOST}:{PORT}"
# V2 引擎测试 Agent（agent_version=v2，PIXIU）
APP_CODE = "ea7ee88386a14e5ea38edda24a05c1fb"
# cs 场景空间 workspace
WORKSPACE_ID = 3

TOKEN = create_session_token({"id": 1, "role": "admin", "name": "admin"})

HEADERS = {
    "Content-Type": "application/json",
    "X-User-ID": "admin",
    "Authorization": f"Bearer {TOKEN}",
}


def chat_completions(conv_uid: str, user_input: str, label: str, timeout: int = 300):
    body = {
        "app_code": APP_CODE,
        "conv_uid": conv_uid,
        "user_input": user_input,
        "ext_info": {
            "incremental": True,
            "workspace_id": WORKSPACE_ID,
            "vis_render": "scene_agent_workspace",
        },
        "incremental": True,
        "work_mode": "simple",
        "temperature": 0.3,
        "max_new_tokens": 2048,
    }
    req = urllib.request.Request(
        f"{BASE}/api/v1/chat/completions",
        data=json.dumps(body).encode(),
        method="POST",
        headers=HEADERS,
    )
    print(f"\n>>> [{label}] user_input={user_input!r} conv_uid={conv_uid}")
    t0 = time.time()
    frames = []
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if not payload:
                    continue
                try:
                    obj = json.loads(payload)
                except Exception:
                    continue
                frames.append(obj)
    except Exception as e:
        print(f"    !! [{label}] 请求异常: {e}")
        return None

    dt = time.time() - t0
    # 从 SSE 帧里提取最终答案内容
    texts = []
    for f in frames:
        vis = f.get("vis")
        if isinstance(vis, str):
            texts.append(vis)
        elif isinstance(vis, dict):
            data = vis.get("data") or vis
            texts.append(json.dumps(data, ensure_ascii=False)[:200])
    content_texts = [t for t in texts if not t.startswith("{\"")]
    print(f"    <<< [{label}] 耗时 {dt:.1f}s, 帧数 {len(frames)}")
    return frames


def extract_final_answer(frames):
    """从 SSE 帧中尽力提取最终 assistant 文本。"""
    collected = []
    for f in frames:
        vis = f.get("vis")
        if not isinstance(vis, str):
            continue
        collected.append(vis)
    # 取最后一段非空、非仅符号的文本
    for t in reversed(collected):
        t = t.strip()
        if t and t not in ("[DONE]", "{"):
            return t
    return ""


def main():
    # 生成一个新会话（跨两轮复用，模拟场景空间前端 ensureConvUid）
    conv_uid = str(uuid.uuid4())
    print(f"新会话 conv_uid = {conv_uid} (workspace_id={WORKSPACE_ID}, app={APP_CODE})")

    round1 = chat_completions(conv_uid, "我的幸运数字是 42，请记住它，并简单回复。", "round1")
    if round1 is None:
        print("\n第一轮失败，终止。")
        return
    ans1 = extract_final_answer(round1)
    print(f"    round1 最终答案: {ans1[:150]!r}")

    # 追问（同一会话）——直接验证上下文锚点
    round2 = chat_completions(
        conv_uid, "我刚才说的幸运数字是多少？只回答数字即可。", "round2-followup"
    )
    if round2 is None:
        print("\n第二轮失败。")
        return
    ans2 = extract_final_answer(round2)
    print(f"    round2 最终答案: {ans2[:150]!r}")

    # 判定
    print("\n" + "=" * 60)
    if "42" in ans2:
        print("✅ 符合预期：第二轮上下文保留了第一轮的幸运数字 42，追问正常！")
    else:
        print("❌ 不符合预期：第二轮没有上下文锚点（应回答 42）。")
        print(f"   实际回答: {ans2[:200]!r}")
    print("=" * 60)


if __name__ == "__main__":
    main()
