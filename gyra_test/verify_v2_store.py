"""模拟服务器 DB 初始化，确认 create_state_store 真实落库路径。

验证：服务器 [service.web.database] 初始化后，V2 事件写入系统 DB 还是 fallback SQLite。
运行: .venv/bin/python gyra_test/verify_v2_store.py
"""
import asyncio
import os
import sqlite3
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../packages/gyra-core/src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../packages/gyra-ext/src"))


async def main():
    # 1. 初始化模块级 db（模拟服务器 serve 层 init_db）
    from gyra.storage.metadata import db

    sim_dir = tempfile.mkdtemp(prefix="v2_store_verify_")
    sim_db = os.path.join(sim_dir, "gyra_sim.db")
    db.init_db(f"sqlite:///{sim_db}")
    print(f"模块级 db 初始化: is_initialized={db.is_initialized}")
    print(f"engine url: {db.engine.url}")

    # 2. create_state_store 实际选择
    from gyra.agent.core.v2.state_store import create_state_store

    store = create_state_store(agent_id="sim-agent")
    print(f"create_state_store 返回: {type(store).__name__}")

    # 3. 写一条事件
    from gyra.agent.core.v2.step_event import StepEvent
    from gyra.agent.core.v2.step_state import StepState

    ev = StepEvent(
        event_id="evt-verify-1",
        step_id="step-verify-1",
        conv_id="sim-conv",
        agent_id="sim-agent",
        parent_step_id=None,
        state=StepState.DONE,
        event_type="user/message",
        input={},
        output={"text": "hello"},
        seq=0,
        timestamp=time.time(),
    )
    await store.append_event(ev)
    events = await store.get_events("sim-conv")
    print(f"写读回事件数: {len(events)}")

    # 4. 检查事件落在哪：系统模拟库 or v2_state 目录
    conn = sqlite3.connect(sim_db)
    tables = [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    conn.close()
    v2_tables = [t for t in tables if "v2" in t or "step" in t]
    print(f"系统模拟库中 v2/step 表: {v2_tables}")

    v2_state_dir = "/Users/yanghongjun/code/Gyra/pilot/data/v2_state"
    files = os.listdir(v2_state_dir)
    new_files = [f for f in files if f.startswith("sim-agent")]
    print(f"v2_state 目录新文件: {new_files}")

    # 5. 结论
    if v2_tables:
        print("\n=> V2 事件写入系统数据库（v2_* 表）")
    elif new_files:
        print("\n=> V2 事件写入 v2_state 本地 SQLite 文件")
    else:
        print("\n=> V2 事件未落盘到可见位置（可能被静默丢弃！）")


if __name__ == "__main__":
    asyncio.run(main())
