"""大厅直接对话的交付文件物化为空间交付产物(Artifact)。

场景:大厅模式(task_id 为空)agent 通过 deliver_file / create_file 交付文件时,
文件会存进 AFS 并标记为 deliverable,但不会自动进入空间的"交付产物"列表
(只有 playbook 任务收尾才会物化 Artifact)。本模块在每轮大厅对话结束后,
把本轮明确交付的文件物化为 Artifact(task_id=0 表示"会话级交付,无关联任务"),
按 file_id/url 去重,避免重复建产物。
"""
import logging
from typing import Any, List, Optional

from gyra.component import SystemApp

logger = logging.getLogger(__name__)

# 会话级交付产物标记:Artifact 无关联任务时用 0 作为哨兵值(DB 层 Integer 非空)。
LOBBY_ARTIFACT_TASK_ID = 0


def _get_artifact_service(system_app: SystemApp) -> Any:
    from gyra_serve.artifact.service.service import (
        ARTIFACT_SERVICE_COMPONENT_NAME,
        ArtifactService,
    )

    return system_app.get_component(ARTIFACT_SERVICE_COMPONENT_NAME, ArtifactService)


async def _collect_deliverable_files(
    agent_conv_id: Optional[str], conv_id: Optional[str]
) -> List[dict]:
    """复用 playbook runtime 的交付文件收集逻辑，避免重复实现。"""
    from gyra_serve.playbook.runtime import _collect_deliverable_files as _collect

    return await _collect(agent_conv_id, conv_id)


def _existing_file_keys(service: Any, workspace_id: int) -> tuple:
    """收集该空间已有 Artifact 的 (file_id 集合, content_ref 集合)，用于去重。"""
    from gyra_serve.artifact.api.schemas import ArtifactListFilter

    file_ids = set()
    content_refs = set()
    try:
        existing = service.list_artifacts(
            ArtifactListFilter(workspace_id=workspace_id, limit=1000)
        ) or []
        for art in existing:
            if art.content_ref:
                content_refs.add(art.content_ref)
            prov = art.provenance or {}
            if prov.get("file_id"):
                file_ids.add(str(prov["file_id"]))
    except Exception as e:
        logger.warning(
            f"[workspace] list existing artifacts for dedup failed: {e}"
        )
    return file_ids, content_refs


def _fmt_dict_value(v: Any) -> Optional[str]:
    return str(v) if v is not None else None


async def materialize_direct_conversation_deliverables(
    system_app: SystemApp,
    workspace_id: int,
    conv_id: Optional[str],
    agent_conv_id: Optional[str],
    created_by_agent: Optional[str] = None,
) -> int:
    """把大厅直接对话中明确交付(deliverable)的文件物化为空间交付产物。

    Args:
        system_app: 运行中的 SystemApp。
        workspace_id: 场景空间 id。
        conv_id: 会话 id(前端/用户会话)。
        agent_conv_id: agent 内部对话 id。
        created_by_agent: 产出方 app_code(用于溯源)。

    Returns:
        本次新建的 Artifact 数量。
    """
    if not workspace_id:
        return 0
    try:
        files = await _collect_deliverable_files(agent_conv_id, conv_id)
    except Exception as e:
        logger.warning(f"[workspace] collect deliverable files failed: {e}")
        return 0
    if not files:
        return 0

    service = _get_artifact_service(system_app)
    existing_file_ids, existing_refs = _existing_file_keys(service, workspace_id)

    from gyra_serve.artifact.api.schemas import ArtifactRequest
    from gyra_serve.workspace.event_bus import emit_workspace_event

    created = 0
    for f in files:
        file_id = _fmt_dict_value(f.get("file_id"))
        file_url = f.get("download_url") or f.get("preview_url") or f.get("oss_url")
        if not file_url:
            continue
        # 去重:同一文件已物化过则跳过
        if (file_id and file_id in existing_file_ids) or file_url in existing_refs:
            continue
        file_name = f.get("file_name") or "unnamed"
        try:
            artifact = service.create(ArtifactRequest(
                task_id=LOBBY_ARTIFACT_TASK_ID,
                workspace_id=workspace_id,
                type="file",
                title=file_name,
                content_ref=file_url,
                provenance={
                    "source": "deliverable_file",
                    "conv_id": conv_id,
                    "agent_conv_id": agent_conv_id,
                    "file_id": file_id,
                    "mime_type": f.get("mime_type"),
                    "file_size": f.get("file_size"),
                    "object_path": f.get("object_path"),
                    "description": f.get("description"),
                },
                created_by_agent=created_by_agent,
            ))
            created += 1
            existing_file_ids.add(file_id) if file_id else None
            existing_refs.add(file_url)
            emit_workspace_event(workspace_id, "artifact_produced", {
                "artifact_id": artifact.id,
                "title": file_name,
                "type": "file",
                "task_id": LOBBY_ARTIFACT_TASK_ID,
                "workspace_id": workspace_id,
            })
            logger.info(
                f"[workspace] lobby deliverable materialized as artifact "
                f"#{artifact.id} file={file_name} ws={workspace_id}"
            )
        except Exception as e:
            logger.warning(
                f"[workspace] materialize deliverable artifact failed "
                f"file={file_name}: {e}"
            )
    return created