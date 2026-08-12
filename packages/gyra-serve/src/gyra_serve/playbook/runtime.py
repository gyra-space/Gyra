"""Playbook runtime — executes a Task by driving the workspace Agent in the task's
conversation session, then materializes deliverables and deliveries.

MVP scope:
- Assemble playbook declaration + workspace/task context
- Send the initial user query via app_chat_v3 (async background chat)
- Poll conversation status until COMPLETE / FAILED
- Create Artifact(s) from the final output
- Create Delivery record(s) from declaration and attempt to send them
- Transition task status: running -> delivered / awaiting_human / failed
"""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks

from gyra.core.interface.message import HumanMessage
from gyra_serve.agent.agents.controller import multi_agents
from gyra_serve.playbook.finalize import finalize_task
from gyra_serve.playbook.finalize import _collect_deliverable_files  # noqa: F401  (兼容旧 import 路径)
from gyra_serve.playbook.service.service import (
    PLAYBOOK_SERVICE_COMPONENT_NAME, PlaybookService,
)
from gyra_serve.workspace.scene_resource_assembler import SceneResourceAssembler
from gyra_serve.workspace.service.service import (
    WORKSPACE_SERVICE_COMPONENT_NAME, WorkspaceService,
)

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 3.0
MAX_POLL_MINUTES = 30


async def run_task(
    system_app,
    task_id: int,
    user_code: Optional[str] = None,
    sys_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Run a task through its bound playbook.

    Args:
        system_app: SystemApp to look up services
        task_id: task id to execute
        user_code: optional user code for the agent run
        sys_code: optional system code

    Returns:
        dict with task_id, status, artifact_ids, delivery_ids
    """
    from gyra_serve.task.service.service import (
        TASK_SERVICE_COMPONENT_NAME, TaskService,
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
    # 执行轨迹采集相关导入
    from gyra.distributed import (
        GateTriggerRecord, SkillCallRecord, TraceContext, get_shared_event_bus,
    )
    from gyra_serve.playbook.trace.collector import BufferedTraceCollector
    from gyra_serve.playbook.trace.sink import DBTraceSink

    task_service: TaskService = system_app.get_component(
        TASK_SERVICE_COMPONENT_NAME, TaskService,
    )
    playbook_service: PlaybookService = system_app.get_component(
        PLAYBOOK_SERVICE_COMPONENT_NAME, PlaybookService,
    )
    workspace_service: WorkspaceService = system_app.get_component(
        WORKSPACE_SERVICE_COMPONENT_NAME, WorkspaceService,
    )
    artifact_service: ArtifactService = system_app.get_component(
        ARTIFACT_SERVICE_COMPONENT_NAME, ArtifactService,
    )
    delivery_service: DeliveryService = system_app.get_component(
        DELIVERY_SERVICE_COMPONENT_NAME, DeliveryService,
    )
    intervention_service: InterventionService = system_app.get_component(
        INTERVENTION_SERVICE_COMPONENT_NAME, InterventionService,
    )

    task = task_service.get_by_id(task_id)
    if not task:
        raise ValueError(f"task {task_id} not found")
    if not task.playbook_id:
        raise ValueError(f"task {task_id} has no playbook")
    playbook = playbook_service.get_by_id(task.playbook_id)
    if not playbook:
        raise ValueError(f"playbook {task.playbook_id} not found")
    workspace = workspace_service.get_by_id(task.workspace_id)
    if not workspace:
        raise ValueError(f"workspace {task.workspace_id} not found")

    declaration = playbook.declaration or {}
    app_code = workspace.default_agent_app_code or "chat_normal"

    # 创建执行轨迹采集器——采集失败仅 log warning,不阻断主流程
    trace_collector = None
    try:
        trace_context = TraceContext(
            playbook_id=playbook.id,
            playbook_version_id=getattr(playbook, "current_version", None) or 0,
            task_id=task.id,
            workspace_id=task.workspace_id,
            agent_id=app_code,
        )
        # 飞轮联动: 接入共享事件总线, finalize 时发布 TRACE_FINALIZED
        # 触发 TraceToEvolutionHandler 累积分析 + AgentMaturityHandler 重算执行统计
        shared_bus = get_shared_event_bus(system_app)
        trace_collector = BufferedTraceCollector(
            trace_context, DBTraceSink(), event_bus=shared_bus,
        )
    except Exception as e:
        logger.warning(f"[playbook runtime] trace collector init failed: {e}")

    # 轨迹最终状态——try/finally 中据此 finalize(默认 failed 覆盖意外异常)
    _trace_status = "failed"
    _trace_failure_reason = ""
    _skill_call_order = 0

    async def _safe_record_skill(skill_name, success, summary=""):
        """记录 skill 调用——失败仅 log,不阻断主流程。"""
        nonlocal _skill_call_order
        if trace_collector is None:
            return
        try:
            _skill_call_order += 1
            await trace_collector.record_skill(SkillCallRecord(
                skill_name=skill_name,
                call_order=_skill_call_order,
                success=success,
                duration_ms=0,
                result_summary=summary,
            ))
        except Exception as e:
            logger.warning(f"[playbook runtime] record_skill failed: {e}")

    async def _safe_record_gate(
        gate_name, intervention_type="review", resolution="pending",
    ):
        """记录 gate 触发——失败仅 log,不阻断主流程。"""
        if trace_collector is None:
            return
        try:
            await trace_collector.record_gate(GateTriggerRecord(
                gate_name=gate_name,
                intervention_type=intervention_type,
                resolved_by="",
                resolution=resolution,
            ))
        except Exception as e:
            logger.warning(f"[playbook runtime] record_gate failed: {e}")

    try:
        # Build the initial user query from playbook + task
        user_query = _build_user_query(playbook, task, workspace, declaration)

        # Ensure task is running (idempotent when caller already transitioned it)
        if task.status != "running":
            try:
                task_service.start(task_id)
            except Exception as e:
                logger.warning(f"task start skipped or failed: {e}")

        # Assemble scene resources for the workbench path. Unlike the HTTP
        # chat_completions endpoint (which wires SceneResourceAssembler in its
        # pre-processing layer), run_task calls app_chat_v3 directly, so it must
        # assemble here and forward via ext_info["dynamic_resources"]. The
        # forwarding path: app_chat_v3(**ext_info) -> async_chat.chat(**ext_info)
        # -> aggregation_chat(**ext_info), where ext_info["dynamic_resources"] is
        # consumed by AgentChat (preserved/extended, never overwritten).
        scene_resources = SceneResourceAssembler.assemble(
            system_app=system_app,
            workspace_id=task.workspace_id,
            task_id=task.id,
            conv_uid=task.conv_session_id,
        )

        # 飞轮体系: 按 Playbook declaration 的 roles 块装配职能角色团队。
        # 产出角色蓝图(role/skills/maturity_min/prompt/resources),供运行时
        # 按角色装配不同 skill 集与 prompt。装配失败仅 log,不阻断主流程。
        try:
            from gyra_serve.workspace.materializer import materialize_playbook_roles
            role_team = materialize_playbook_roles(
                system_app, declaration, task.workspace_id
            )
            if role_team:
                logger.info(
                    f"[playbook runtime] task={task_id} assembled "
                    f"{len(role_team)} roles: "
                    f"{[r.get('role') for r in role_team]}"
                )
        except Exception as e:
            logger.warning(
                f"[playbook runtime] materialize_playbook_roles failed: {e}"
            )

        # Launch agent in the task's conversation session
        logger.info(
            f"[playbook runtime] starting task={task_id} conv={task.conv_session_id} "
            f"app={app_code} playbook={playbook.id}"
        )
        _, agent_conv_id = await multi_agents.app_chat_v3(
            conv_uid=task.conv_session_id,
            gpts_name=app_code,
            user_query=HumanMessage(content=user_query),
            background_tasks=BackgroundTasks(),
            user_code=user_code or str(task.created_by_user_id or "system"),
            sys_code=sys_code,
            workspace_id=task.workspace_id,
            task_id=task.id,
            dynamic_resources=scene_resources,
        )

        if not agent_conv_id:
            task_service.transition(task_id, "failed")
            _trace_failure_reason = "agent did not return conv id"
            return {"task_id": task_id, "status": "failed", "error": "agent did not return conv id"}

        # Poll until the agent run finishes
        final_state = await _poll_chat_completion(agent_conv_id)
        logger.info(f"[playbook runtime] task={task_id} final_state={final_state}")

        # 任务可能在运行期间被用户终止(terminate → closed):跳过状态流转与交付物物化
        current = task_service.get_by_id(task_id)
        if not current or current.status != "running":
            logger.info(
                f"[playbook runtime] task={task_id} no longer running "
                f"(status={getattr(current, 'status', None)}), skip finalize"
            )
            _trace_status = "aborted"
            return {"task_id": task_id, "status": getattr(current, "status", "deleted")}

        if final_state.get("state") == "FAILED":
            task_service.transition(task_id, "failed")
            _trace_failure_reason = final_state.get("error") or "agent run failed"
            return {"task_id": task_id, "status": "failed"}

        vis_final = final_state.get("vis_final") or ""
        # 交付物/通知内容是给人看的最终答复文本;vis_final 是场景空间 VIS 渲染协议帧,
        # 只用于 SSE 推送,不应作为交付物内容持久化(否则前端只能展示协议 JSON)。
        deliverable_content = final_state.get("user_answer") or vis_final

        # 公共收尾:物化产出(最终答复 + 交付文件 Artifact)、创建交付记录并外发、
        # review 介入检查、状态流转 —— 与 in_session 会话内任务共享同一实现
        # (playbook/finalize.py::finalize_task),消除两套收尾逻辑。
        result = await finalize_task(
            system_app,
            task.id,
            agent_conv_id=agent_conv_id,
            conv_id=task.conv_session_id,
            deliverable_content=str(deliverable_content),
            created_by_agent=app_code,
        )
        _trace_status = (
            "success"
            if result.get("status") in ("delivered", "awaiting_human")
            else "failed"
        )
        return result
    finally:
        # 确保轨迹一定被 finalize——失败仅 log,不影响返回值/异常传播
        if trace_collector is not None:
            try:
                await trace_collector.finalize(
                    status=_trace_status,
                    failure_reason=_trace_failure_reason,
                )
            except Exception as e:
                logger.warning(f"[playbook runtime] trace finalize failed: {e}")


def _build_user_query(
    playbook: Any, task: Any, workspace: Any, declaration: Dict[str, Any],
) -> str:
    """Build the initial user prompt: just the task goal (instruction).

    skills/resources are injected as agent tools via SceneResourceAssembler
    (dynamic_resources); deliverables/distill are playbook-level config rendered
    into the system prompt by render_workspace_context_summary. The user query
    only needs to tell the agent the task goal - 剧本名/workspace/skills 等不必
    重复(已在工具和 system prompt 里),否则任务输入会塞满无关内容。
    """
    lines: List[str] = []
    if task.title:
        lines.append(task.title)
    if task.description:
        lines.append(task.description)
    if not lines:
        # 兜底(不应发生:TaskRequest.title 必填)
        lines.append(f"Execute playbook {playbook.name}")
    return "\n".join(lines)


async def _poll_chat_completion(agent_conv_id: str) -> Dict[str, Any]:
    """Poll query_chat until the agent run reaches a final state."""
    max_attempts = int((MAX_POLL_MINUTES * 60) / POLL_INTERVAL_SECONDS)
    for attempt in range(max_attempts):
        try:
            result = await multi_agents.query_chat(conv_id=agent_conv_id)
            if result is None:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                continue
            vis_final, user_answer, current_vis_render, is_final, state, dock = result
            if state in ("COMPLETE", "FAILED") or is_final:
                return {
                    "state": state,
                    "is_final": is_final,
                    "vis_final": vis_final,
                    "user_answer": user_answer,
                    "vis_render": current_vis_render,
                    "dock": dock,
                }
        except Exception as e:
            logger.warning(f"playbook runtime poll error: {e}")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

    return {"state": "FAILED", "error": "polling timeout"}
