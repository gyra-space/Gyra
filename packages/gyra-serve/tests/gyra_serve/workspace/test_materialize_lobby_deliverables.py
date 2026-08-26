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


def test_materializes_with_task_id_binds_artifact(artifact_service):
    """会话内任务(in_session)交付:传入真实 task_id,产物绑定该任务而非哨兵 0。"""
    files = [_make_file("f1", "a.txt", "https://x/a.txt")]
    with patch.object(md, "_collect_deliverable_files", return_value=files), \
         patch.object(md, "_get_artifact_service", return_value=artifact_service), \
         patch("gyra_serve.workspace.event_bus.emit_workspace_event"):
        n = asyncio.run(md.materialize_direct_conversation_deliverables(
            MagicMock(), workspace_id=7, conv_id="c1",
            agent_conv_id="a1", created_by_agent="scene-workspace-agent",
            task_id=42,
        ))

    assert n == 1
    listed = artifact_service.list_artifacts(
        ArtifactListFilter(workspace_id=7, limit=100)
    )
    assert len(listed) == 1
    assert listed[0].task_id == 42


def test_list_by_filter_isolates_lobby_session_from_playbook_task(artifact_service):
    """task_id=0(大厅会话)与真实任务(>0)在 listArtifacts 上严格隔离:
    查询 task_id=0 只返回哨兵产物,不混入剧本任务文件;查询真实任务只返回该任务文件。"""
    from gyra_serve.artifact.api.schemas import ArtifactRequest
    from gyra_serve.workspace.agent_tools.materialize_deliverables import (
        LOBBY_ARTIFACT_TASK_ID,
    )

    artifact_service.create(ArtifactRequest(
        task_id=LOBBY_ARTIFACT_TASK_ID, workspace_id=7, type="file",
        title="lobby_a.txt", content_ref="https://x/lobby_a.txt",
        provenance={"source": "deliverable_file", "conv_id": "conv-a"},
    ))
    artifact_service.create(ArtifactRequest(
        task_id=LOBBY_ARTIFACT_TASK_ID, workspace_id=7, type="file",
        title="lobby_b.txt", content_ref="https://x/lobby_b.txt",
        provenance={"source": "deliverable_file", "conv_id": "conv-b"},
    ))
    artifact_service.create(ArtifactRequest(
        task_id=42, workspace_id=7, type="file",
        title="task42.txt", content_ref="https://x/task42.txt",
    ))

    lobby = artifact_service.list_artifacts(
        ArtifactListFilter(workspace_id=7, task_id=LOBBY_ARTIFACT_TASK_ID, limit=100)
    )
    assert len(lobby) == 2
    assert all(x.task_id == LOBBY_ARTIFACT_TASK_ID for x in lobby)
    titles = {x.title for x in lobby}
    assert "task42.txt" not in titles  # 剧本任务文件不混入大厅会话查询

    task42 = artifact_service.list_artifacts(
        ArtifactListFilter(workspace_id=7, task_id=42, limit=100)
    )
    assert [x.title for x in task42] == ["task42.txt"]  # 任务详情不含大厅会话文件


def test_list_by_filter_isolates_lobby_conversations_by_conv_id(artifact_service):
    """两个独立大厅会话(task_id=0 相同)在 listArtifacts 上彻底隔离:
    会话级交付物写入各自 conv_id,按 conv_id 精确过滤,互不串扰。
    这是「a 会话的交付文件展示在 b 会话」问题的修复验证。"""
    from gyra_serve.artifact.api.schemas import ArtifactRequest
    from gyra_serve.workspace.agent_tools.materialize_deliverables import (
        LOBBY_ARTIFACT_TASK_ID,
    )

    # conv-a 的交付文件
    artifact_service.create(ArtifactRequest(
        task_id=LOBBY_ARTIFACT_TASK_ID, workspace_id=7, conv_id="conv-a",
        type="file", title="a_report.pdf",
        content_ref="https://x/a_report.pdf",
        provenance={"source": "deliverable_file", "conv_id": "conv-a", "file_id": "fa1"},
    ))
    # conv-b 的交付文件(与 conv-a 同属 task_id=0)
    artifact_service.create(ArtifactRequest(
        task_id=LOBBY_ARTIFACT_TASK_ID, workspace_id=7, conv_id="conv-b",
        type="file", title="b_notes.xlsx",
        content_ref="https://x/b_notes.xlsx",
        provenance={"source": "deliverable_file", "conv_id": "conv-b", "file_id": "fb1"},
    ))
    # 未落 conv_id 的旧数据(历史遗留/奇葩),仅按 task_id 查会露出,按 conv_id 查则隔离
    artifact_service.create(ArtifactRequest(
        task_id=LOBBY_ARTIFACT_TASK_ID, workspace_id=7, conv_id=None,
        type="file", title="legacy.txt",
        content_ref="https://x/legacy.txt",
    ))

    conv_a = artifact_service.list_artifacts(
        ArtifactListFilter(
            workspace_id=7, task_id=LOBBY_ARTIFACT_TASK_ID,
            conv_id="conv-a", limit=100,
        )
    )
    assert [x.title for x in conv_a] == ["a_report.pdf"]  # 只返回 conv-a,不带 b/legacy

    conv_b = artifact_service.list_artifacts(
        ArtifactListFilter(
            workspace_id=7, task_id=LOBBY_ARTIFACT_TASK_ID,
            conv_id="conv-b", limit=100,
        )
    )
    assert [x.title for x in conv_b] == ["b_notes.xlsx"]  # 只返回 conv-b

    # 兜底:不带 conv_id 的会话级查询仍能看到该桶全部(兼容旧前端/历史数据迁移期间)
    all_lobby = artifact_service.list_artifacts(
        ArtifactListFilter(workspace_id=7, task_id=LOBBY_ARTIFACT_TASK_ID, limit=100)
    )
    assert len(all_lobby) == 3


def test_aggregation_chat_finally_materializes_lobby_only():
    """收尾仅在 workspace + task_id 空(大厅)时调用物化,任务模式跳过。"""
    src = (
        Path(__file__).parents[3]
        / "src/gyra_serve/agent/agents/chat/agent_chat.py"
    ).read_text(encoding="utf-8")
    assert "materialize_direct_conversation_deliverables" in src
    assert "not ext_info.get(\"task_id\")" in src
    assert "_ws_id_for_bus and not ext_info.get(\"task_id\")" in src