"""验证根因 2 修复：缺省 conv_uid 时服务端派生稳定会话 ID，多轮不断裂。

模拟 /chat 页面首次对话：body 不传 conv_uid，只带 workspace_id。
- 修复前：每轮 uuid1().hex 新 ID → 两轮事件落不同 conv → 追问丢上下文
- 修复后：派生 "ws-{wsid}-default"（或 ws-task）→ 两轮事件落同一 conv → 追问连续

用法: .venv/bin/python gyra_test/test_v2_missing_convuid.py
"""
import json
import time
import urllib.request

from gyra_app.auth.session import create_session_token

HOST = "127.0.0.1"
PORT = 8888
BASE = f"http://{HOST}:{PORT}"
APP_CODE = "ea7ee88386a14e5ea38edda24a05c1fb"
WORKSPACE_ID = 3

TOKEN = create_session_token({"id": 1, "role": "admin", "name": "admin"})
HEADERS = {
    "Content-Type": "application/json",
    "X-User-ID": "admin",
    "Authorization": f"Bearer {TOKEN}",
}


def chat_no_convuid(user_input: str, label: str, with_task: bool = False):
    """不带 conv_uid 的请求（模拟 /chat 首次对话/纯 API 调用）。"""
    ext = {"incremental": True, "workspace_id": WORKSPACE_ID}
    if with_task:
        ext["task_id"] = 1
    body = {
        "app_code": APP_CODE,
        "user_input": user_input,
        "ext_info": ext,
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
    print(f"\n>>> [{label}] user_input={user_input!r} (无 conv_uid, workspace={WORKSPACE_ID})")
    t0 = time.time()
    conv_session_id = None
    conv_uid = None
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
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
                vis = obj.get("vis")
                if isinstance(vis, dict) and vis.get("type") == "metadata":
                    conv_session_id = vis.get("conv_session_id")
                    conv_uid = vis.get("conv_uid")
    except Exception as e:
        print(f"    !! [{label}] 异常: {e}")
        return None, None
    print(f"    <<< [{label}] 耗时 {time.time()-t0:.1f}s")
    print(f"    服务端 conv_session_id={conv_session_id}  conv_uid={conv_uid}")
    return conv_session_id, conv_uid


def main():
    for with_task in (False, True):
        mode = "task" if with_task else "workspace"
        print("\n" + "#" * 60)
        print(f"# 场景：缺 conv_uid + workspace({mode} 维度)")
        print("#" * 60)
        sid1, uid1 = chat_no_convuid("我的幸运数字是 42，请记住它，并简单回复。", "round1", with_task)
        sid2, uid2 = chat_no_convuid("我刚才说的幸运数字是多少？只回答数字即可。", "round2-followup", with_task)

        if sid1 is None or sid2 is None:
            print(f"  ({mode}) 有请求失败，跳过。")
            continue

        same = sid1 == sid2 and sid1 is not None
        print(f"\n  ({mode}) 两轮 conv_session_id 相同: {same}")
        print(f"    round1 sid={sid1!r}")
        print(f"    round2 sid={sid2!r}")
        if same:
            print(f"  ✅ ({mode}) 根因 2 修复生效：缺 conv_uid 时派生稳定 ID，多轮会话连续")
        else:
            print(f"  ❌ ({mode}) 仍断裂")
        print()


if __name__ == "__main__":
    main()
