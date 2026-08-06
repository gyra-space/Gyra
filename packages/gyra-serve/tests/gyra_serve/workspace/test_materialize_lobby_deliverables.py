"""大厅直接对话交付文件物化为空间交付产物(Artifact) 的测试。

聚焦 materialize_direct_conversation_deliverables:
- 收集到的 deliverable 文件会落成 Artifact(task_id=0 哨兵值)
- 重复物化(同一轮 or 多轮)按 file_id/url 去重,不重复建产物
- aggregation_chat 收尾仅在大厅(task_id 空)触发物化
"""
import asyncio
from pathlib import Path

from unittest.mock import MagicMock, patch

import pytest

from gyra.storage.metadata import db
from gyra_serve.artifact.api.schemas import ArtifactListFilter
from gyra_serve.artifact.models.models import ArtifactDao, ArtifactVersionDao
from gyra_serve.artifact.service.service import ArtifactService
from gyra_serve.workspace.agent_tools import materialize_deliverables as md


@pytest.fixture
def artifact_service(tmp_path):
    db.init_db(f"sqlite:///{tmp_path / 't.db'}")
    db.create_all()
    svc = ArtifactService(MagicMock(), MagicMock())
    svc._dao = ArtifactDao()
    svc._version_dao = ArtifactVersionDao()
    svc._system_app = MagicMock()
    return svc


def _make_file(file_id, name, url):
    return {
        "file_id": file_id,
        "file_name": name,
        "mime_type": "text/plain",
        "file_size": 10,
        "download_url": url,
        "preview_url": url,
        "oss_url": url,
        "object_path": f"obj/{name}",
        "description": "delivered",
    }


def _materialize(artifact_service, workspace_id, files):
    with patch.object(md, "_collect_deliverable_files", return_value=files), \
         patch.object(md, "_get_artifact_service", return_value=artifact_service), \
         patch("gyra_serve.workspace.event_bus.emit_workspace_event"):
        return asyncio.run(md.materialize_direct_conversation_deliverables(
            MagicMock(), workspace_id=workspace_id, conv_id="c1",
            agent_conv_id="a1", created_by_agent="scene-workspace-agent",
        ))


def test_materializes_deliverable_files_as_artifacts(artifact_service):
    files = [
        _make_file("f1", "a.txt", "https://x/a.txt"),
        _make_file("f2", "b.pdf", "https://x/b.pdf"),
    ]
    n = _materialize(artifact_service, 7, files)

    assert n == 2
    listed = artifact_service.list_artifacts(
        ArtifactListFilter(workspace_id=7, limit=100)
    )
    assert len(listed) == 2
    by_title = {x.title: x for x in listed}
    assert by_title["a.txt"].task_id == 0
    assert by_title["a.txt"].content_ref == "https://x/a.txt"
    assert by_title["a.txt"].provenance.get("file_id") == "f1"
    assert by_title["a.txt"].created_by_agent == "scene-workspace-agent"
    assert by_title["b.pdf"].task_id == 0


def test_idempotent_on_repeat_materialization(artifact_service):
    files = [_make_file("f1", "a.txt", "https://x/a.txt")]
    n1 = _materialize(artifact_service, 3, files)
    n2 = _materialize(artifact_service, 3, files)

    assert n1 == 1
    assert n2 == 0  # 第二次不再重复建产物(按 file_id 去重)
    listed = artifact_service.list_artifacts(
        ArtifactListFilter(workspace_id=3, limit=100)
    )
    assert len(listed) == 1


def test_no_files_returns_zero(artifact_service):
    assert _materialize(artifact_service, 3, []) == 0


def test_skips_file_without_url(artifact_service):
    files = [{"file_id": "f9", "file_name": "nope.txt", "download_url": None}]
    assert _materialize(artifact_service, 3, files) == 0


def test_aggregation_chat_finally_materializes_lobby_only():
    """收尾仅在 workspace + task_id 空(大厅)时调用物化,任务模式跳过。"""
    src = (
        Path(__file__).parents[3]
        / "src/gyra_serve/agent/agents/chat/agent_chat.py"
    ).read_text(encoding="utf-8")
    assert "materialize_direct_conversation_deliverables" in src
    assert "not ext_info.get(\"task_id\")" in src
    assert "_ws_id_for_bus and not ext_info.get(\"task_id\")" in src