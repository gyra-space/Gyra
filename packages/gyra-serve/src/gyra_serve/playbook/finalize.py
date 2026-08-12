"""公共任务收尾 finalize_task —— 后台 run_task 与会话内 in_session 任务共用。

消除两套收尾逻辑(设计文档:2026-08-12-workspace-conversation-initiation-routing.md §5):

- background: playbook_runtime.run_task 后台执行完毕后调用;
- in_session: 回合前路由预建的会话内任务,aggregation_chat 会话收尾调用。

统一职责(结果一律进空间交付与飞轮事件):
1. 物化产出:最终答复(final_message Artifact)+ 交付文件(file Artifact,按 file 去重);
2. 创建交付记录(declaration deliverables 中 notify 类)并尝试外发;
3. review 介入检查:需要人工评审 -> 建介入并停在 awaiting_human;
4. 状态流转 running -> delivered / awaiting_human;
5. 发 workspace 事件(artifact_produced / delivery_sent / intervention_triggered)。

任务已非 running(被终止/已关闭)时直接跳过,幂等安全。
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _get_service(system_app, component_name, service_cls):
    return system_app.get_component(component_name, service_cls)


def _fmt_dict_value(v: Any) -> Optional[str]:
    return str(v) if v is not None else None


def _existing_file_keys(service: Any, workspace_id: int) -> tuple:
    """收集该空间已有 Artifact 的 (file_id 集合, content_ref 集合),用于去重。"""
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
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[playbook finalize] list existing artifacts failed: {e}")
    return file_ids, content_refs


async def _collect_deliverable_files(
    agent_conv_id: Optional[str], fallback_conv_id: Optional[str],
) -> List[Dict[str, Any]]:
    """收集任务运行期间被标记为交付物(deliverable)的文件。

    主路径:DB 文件元数据存储(沙箱模式下 deliver_file 经 GptsMemory 持久化);
    兜底:解析 gpts messages 的 action_report[].output_files(本地模式
    deliver_file 用内存元数据存储,运行结束即丢,只能从消息记录里捞)。
    """
    files: Dict[str, Dict[str, Any]] = {}

    try:
        from gyra_serve.agent.agents.gyras_memory import (
            MetaGyrasFileMetadataStorage,
        )

        storage = MetaGyrasFileMetadataStorage()
        conv_ids = {c for c in (agent_conv_id, fallback_conv_id) if c}
        for conv_id in conv_ids:
            for f in await storage.list_files(conv_id, file_type="deliverable"):
                if f.file_id in files:
                    continue
                files[f.file_id] = {
                    "file_id": f.file_id,
                    "file_name": f.file_name,
                    "mime_type": f.mime_type,
                    "file_size": f.file_size,
                    "download_url": f.download_url,
                    "preview_url": f.preview_url,
                    "oss_url": f.oss_url,
                    "object_path": (f.metadata or {}).get("object_path"),
                    "description": (f.metadata or {}).get("description"),
                }
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[playbook finalize] deliverable DB query failed: {e}")

    if files:
        return list(files.values())

    # 兜底:从消息 action_report 提取(与 vis converter 同一数据源)
    try:
        from gyra_serve.agent.db.gpts_messages_db import GptsMessagesDao

        conv_id = agent_conv_id or fallback_conv_id
        if not conv_id:
            return []
        messages = await GptsMessagesDao().get_by_conv_id(conv_id)
        for msg in messages:
            for action_out in msg.action_report or []:
                if isinstance(action_out, dict):
                    output_files = action_out.get("output_files") or []
                else:
                    output_files = getattr(action_out, "output_files", None) or []
                for fi in output_files:
                    if not isinstance(fi, dict):
                        continue
                    if fi.get("file_type") != "deliverable":
                        continue
                    fid = fi.get("file_id")
                    if fid and fid not in files:
                        files[fid] = fi
    except Exception as e:  # noqa: BLE001
        logger.warning(
            f"[playbook finalize] deliverable message fallback failed: {e}"
        )

    return list(files.values())


async def finalize_task(
    system_app,
    task_id: int,
    *,
    agent_conv_id: Optional[str] = None,
    conv_id: Optional[str] = None,
    deliverable_content: str = "",
    created_by_agent: Optional[str] = None,
) -> Dict[str, Any]:
    """公共任务收尾(见模块 docstring)。

    Args:
        system_app: 运行中的 SystemApp。
        task_id: 要收尾的任务 id。
        agent_conv_id: agent 内部对话 id(收集交付文件 / 溯源)。
        conv_id: 会话 id(收集交付文件兜底)。
        deliverable_content: 最终答复文本(非空才建 final_message Artifact,
            并作为交付消息正文;in_session 收尾可不传,靠交付文件承载产出)。
        created_by_agent: 产出方 app_code(溯源)。

    Returns:
        {"task_id", "status", "artifact_ids", "delivery_ids"}
    """
    from gyra_serve.task.service.service import (
        TASK_SERVICE_COMPONENT_NAME, TaskService,
    )
    from gyra_serve.playbook.service.service import (
        PLAYBOOK_SERVICE_COMPONENT_NAME, PlaybookService,
    )
    from gyra_serve.artifact.service.service import (
        ARTIFACT_SERVICE_COMPONENT_NAME, ArtifactService,
    )
    from gyra_serve.delivery.service.service import (
        DELIVERY_SERVICE_COMPONENT_NAME, DeliveryService,
    )
    from gyra_serve.intervention.service.service import (
        INTERVENTION_SERVICE_COMPONENT_NAME, InterventionService,
    )
    from gyra_serve.artifact.api.schemas import ArtifactRequest
    from gyra_serve.delivery.api.schemas import DeliveryRequest
    from gyra_serve.intervention.api.schemas import InterventionRequest
    from gyra_serve.workspace.event_bus import emit_workspace_event

    task_service: TaskService = _get_service(
        system_app, TASK_SERVICE_COMPONENT_NAME, TaskService
    )
    playbook_service: PlaybookService = _get_service(
        system_app, PLAYBOOK_SERVICE_COMPONENT_NAME, PlaybookService
    )
    artifact_service: ArtifactService = _get_service(
        system_app, ARTIFACT_SERVICE_COMPONENT_NAME, ArtifactService
    )
    delivery_service: DeliveryService = _get_service(
        system_app, DELIVERY_SERVICE_COMPONENT_NAME, DeliveryService
    )
    intervention_service: InterventionService = _get_service(
        system_app, INTERVENTION_SERVICE_COMPONENT_NAME, InterventionService
    )

    task = task_service.get_by_id(task_id)
    if not task:
        return {"task_id": task_id, "status": "deleted"}
    # 幂等:任务已非 running(被终止/已关闭/已收尾)直接跳过
    if task.status != "running":
        return {"task_id": task_id, "status": task.status}

    workspace_id = task.workspace_id
    playbook = playbook_service.get_by_id(task.playbook_id) if task.playbook_id else None
    declaration = (playbook.declaration or {}) if playbook else {}
    playbook_name = (playbook.name if playbook else "") or ""

    # 交付文件物化去重:同一文件已建过 Artifact 则跳过
    deliverable_files = await _collect_deliverable_files(agent_conv_id, conv_id)
    existing_file_ids, existing_refs = _existing_file_keys(
        artifact_service, workspace_id
    )

    artifact_ids: List[int] = []

    async def _create_artifact(**kwargs) -> Optional[int]:
        try:
            artifact = artifact_service.create(ArtifactRequest(
                task_id=task_id,
                workspace_id=workspace_id,
                created_by_agent=created_by_agent,
                **kwargs,
            ))
        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"[playbook finalize] create artifact failed "
                f"type={kwargs.get('type')}: {e}"
            )
            return None
        artifact_ids.append(artifact.id)
        emit_workspace_event(workspace_id, "artifact_produced", {
            "artifact_id": artifact.id,
            "title": kwargs.get("title"),
            "type": kwargs.get("type"),
            "task_id": task_id,
            "workspace_id": workspace_id,
        })
        return artifact.id

    # 1) 最终答复(final_message Artifact)——非空才建
    final_message_artifact_id: Optional[int] = None
    if deliverable_content:
        final_message_artifact_id = await _create_artifact(
            type="final_message",
            title=f"{playbook_name} — 最终答复",
            content_text=str(deliverable_content)[:16000],
            provenance={
                "playbook_id": task.playbook_id,
                "playbook_name": playbook_name,
                "agent_conv_id": agent_conv_id,
            },
        )

    # 2) 交付文件(file Artifact,只存引用 URL,按 file 去重)
    for f in deliverable_files:
        file_url = f.get("download_url") or f.get("preview_url") or f.get("oss_url")
        if not file_url:
            continue
        file_id = _fmt_dict_value(f.get("file_id"))
        if (file_id and file_id in existing_file_ids) or file_url in existing_refs:
            continue
        file_name = f.get("file_name") or "unnamed"
        created = await _create_artifact(
            type="file",
            title=file_name,
            content_ref=file_url,
            provenance={
                "playbook_id": task.playbook_id,
                "playbook_name": playbook_name,
                "agent_conv_id": agent_conv_id,
                "source": "deliverable_file",
                "file_id": file_id,
                "mime_type": f.get("mime_type"),
                "file_size": f.get("file_size"),
                "object_path": f.get("object_path"),
                "description": f.get("description"),
            },
        )
        if created is not None:
            if file_id:
                existing_file_ids.add(file_id)
            existing_refs.add(file_url)

    # 3) 交付记录(declaration deliverables 中 notify 类)+ 尝试外发
    delivery_ids: List[int] = []
    delivery_message = str(deliverable_content)[:8000]
    file_links = [
        (f.get("file_name") or "file", f.get("download_url") or f.get("preview_url"))
        for f in deliverable_files
    ]
    file_links = [(n, u) for n, u in file_links if u]
    if file_links:
        links_md = "\n".join(f"- [{n}]({u})" for n, u in file_links)
        delivery_message = f"{delivery_message}\n\n交付文件:\n{links_md}"

    deliverables = declaration.get("deliverables") or []
    for d in deliverables:
        for delivery_decl in d.get("delivery") or []:
            if delivery_decl.get("category") != "notify":
                continue
            try:
                delivery = delivery_service.create(DeliveryRequest(
                    artifact_id=final_message_artifact_id,
                    task_id=task_id,
                    workspace_id=workspace_id,
                    category="notify",
                    channel=delivery_decl.get("channel", "in_app"),
                    target=delivery_decl.get("target", ""),
                    title=f"[{playbook_name}] {d.get('type', 'report')} delivered",
                    message=delivery_message,
                    format=delivery_decl.get("format", "message_card"),
                    require_intervention=delivery_decl.get("require_intervention", "none"),
                ))
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    f"[playbook finalize] create delivery failed "
                    f"channel={delivery_decl.get('channel')}: {e}"
                )
                continue
            delivery_ids.append(delivery.id)
            try:
                await delivery_service.send(delivery.id)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"delivery send failed for {delivery.id}: {e}")
            emit_workspace_event(workspace_id, "delivery_sent", {
                "delivery_id": delivery.id,
                "artifact_id": delivery.artifact_id,
                "task_id": task_id,
                "workspace_id": workspace_id,
                "channel": delivery_decl.get("channel", "in_app"),
            })

    # 4) review 介入检查:需要人工评审 -> 停在 awaiting_human
    requires_review = any(
        d.get("require_intervention") == "review"
        for dlv in deliverables
        for d in dlv.get("delivery") or []
    )
    if requires_review:
        try:
            intervention = intervention_service.create(InterventionRequest(
                task_id=task_id,
                workspace_id=workspace_id,
                type="review",
                requested_by="system",
                question={
                    "playbook_id": task.playbook_id,
                    "playbook_name": playbook_name,
                    "reason": "delivery requires human review before close",
                },
                context={"agent_conv_id": agent_conv_id, "artifact_ids": artifact_ids},
            ))
            emit_workspace_event(workspace_id, "intervention_triggered", {
                "intervention_id": intervention.id,
                "task_id": task_id,
                "workspace_id": workspace_id,
                "tool": "delivery_review",
                "requested_by": "system",
            })
        except Exception as e:  # noqa: BLE001
            logger.warning(f"failed to create review intervention: {e}")
        task_service.transition(task_id, "awaiting_human")
        return {
            "task_id": task_id,
            "status": "awaiting_human",
            "agent_conv_id": agent_conv_id,
            "artifact_ids": artifact_ids,
            "delivery_ids": delivery_ids,
        }

    # 5) 正常路径:delivered
    task_service.transition(task_id, "delivered")
    return {
        "task_id": task_id,
        "status": "delivered",
        "agent_conv_id": agent_conv_id,
        "artifact_ids": artifact_ids,
        "delivery_ids": delivery_ids,
    }
