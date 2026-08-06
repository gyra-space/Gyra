"""Media gen jobs now live on AsyncTaskManager's media singleton.

Tests the JSONL ledger durability & queryability that replaced the removed
MediaJobRegistry (media coroutine mode of AsyncTaskManager).
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from gyra.agent.util.async_task_manager import (
    AsyncTaskManager,
    AsyncTaskSpec,
    AsyncTaskStatus,
    TaskLedger,
)


@pytest.fixture
def ledger_path():
    with tempfile.TemporaryDirectory() as d:
        yield str(Path(d) / "media_jobs.jsonl")


def _spec(conv_id="conv-1", kind="video", model="happyhorse-1.1-t2v", desc="测试视频"):
    async def _resume():
        return None

    async def _deliver(_result):
        raise NotImplementedError

    return AsyncTaskSpec(
        conv_id=conv_id,
        kind=kind,
        model=model,
        task_description=desc,
        resume=_resume,
        deliver=_deliver,
    )


def _fresh_media(ledger_path):
    AsyncTaskManager._media_instance = None
    return AsyncTaskManager.media_instance(ledger_path=ledger_path)


def _reset_singleton():
    AsyncTaskManager._media_instance = None


def test_ledger_upsert_read_and_last_wins(ledger_path):
    ledger = TaskLedger(ledger_path)
    ledger.upsert({"task_id": "mjob_a", "status": "pending", "seq": 1})
    ledger.upsert({"task_id": "mjob_a", "status": "completed", "seq": 2})
    ledger.upsert({"task_id": "mjob_b", "status": "running"})

    records = ledger.read_all()
    # 同 task_id 以最后一次为准
    assert records["mjob_a"]["status"] == "completed"
    assert records["mjob_b"]["status"] == "running"
    assert set(records.keys()) == {"mjob_a", "mjob_b"}


async def test_submit_persists_pending_record(ledger_path):
    reg = _fresh_media(ledger_path)
    task_id = await reg.spawn(_spec())
    record = reg.get_job(task_id)
    assert record is not None
    assert record["task_id"] == task_id
    assert record["status"] == AsyncTaskStatus.PENDING.value
    assert record["kind"] == "video"
    assert record["model"] == "happyhorse-1.1-t2v"
    assert record["conv_id"] == "conv-1"
    assert record["created_at"] is not None
    _reset_singleton()


def test_list_jobs_filters_and_orders(ledger_path):
    # 直接写台账，模拟已存在的历史任务
    ledger = TaskLedger(ledger_path)
    ledger.upsert(
        {
            "task_id": "mjob_old",
            "conv_id": "conv-1",
            "kind": "video",
            "model": "m",
            "description": "d",
            "status": "completed",
            "created_at": "2026-01-01T00:00:00",
        }
    )
    ledger.upsert(
        {
            "task_id": "mjob_new",
            "conv_id": "conv-2",
            "kind": "image",
            "model": "m2",
            "description": "d2",
            "status": "running",
            "created_at": "2026-01-02T00:00:00",
        }
    )

    reg = _fresh_media(ledger_path)
    all_jobs = reg.list_jobs()
    assert [j["task_id"] for j in all_jobs] == ["mjob_new", "mjob_old"]  # 倒序

    conv1 = reg.list_jobs(conv_id="conv-1")
    assert [j["task_id"] for j in conv1] == ["mjob_old"]

    running = reg.list_jobs(status="running")
    assert [j["task_id"] for j in running] == ["mjob_new"]

    limited = reg.list_jobs(limit=1)
    assert len(limited) == 1
    _reset_singleton()


async def test_reload_after_restart_keeps_records(ledger_path):
    # 第一次“进程”：提交并完成一个任务
    reg = _fresh_media(ledger_path)
    task_id = await reg.spawn(_spec())
    # 手动把状态推进到终态并持久化（模拟后台 _run_task 终点）
    state = reg.get_status(task_id)
    state.status = AsyncTaskStatus.COMPLETED
    state.completed_at = datetime.now()
    reg._persist(state)
    _reset_singleton()

    # 第二次“进程”：仅从台账恢复，不依赖内存
    reg2 = _fresh_media(ledger_path)
    restored = reg2.get_job(task_id)
    assert restored is not None
    assert restored["status"] == AsyncTaskStatus.COMPLETED.value
    _reset_singleton()


async def test_to_record_extracts_artifact_and_preview(ledger_path):
    from gyra.agent.tools.result import Artifact, ToolResult

    reg = _fresh_media(ledger_path)
    task_id = await reg.spawn(_spec())
    state = reg.get_status(task_id)
    state.status = AsyncTaskStatus.COMPLETED
    state.completed_at = datetime.now()
    state.result = ToolResult.ok(
        output="✅ 视频生成成功: generated_video_abc.mp4\n**交付文件:** ...",
        tool_name="generate_video",
        artifacts=[
            Artifact(
                name="generated_video_abc.mp4",
                type="file",
                url="https://file-service/xxx.mp4",
                mime_type="video/mp4",
            )
        ],
    )
    record = state.to_record()
    assert record["status"] == AsyncTaskStatus.COMPLETED.value
    assert record["result_preview"].startswith("✅ 视频生成成功")
    assert record["artifact"]["name"] == "generated_video_abc.mp4"
    assert record["artifact"]["url"] == "https://file-service/xxx.mp4"
    assert record["artifact"]["mime_type"] == "video/mp4"
    _reset_singleton()