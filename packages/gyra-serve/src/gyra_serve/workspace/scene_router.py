"""回合前路由:页面输入命中剧本 -> 预建会话内任务(execution_mode=in_session)。

空间对话发起方式 × 执行模式路由(见 docs/superpowers/specs/
2026-08-12-workspace-conversation-initiation-routing.md):

- 页面输入 + 命中剧本 -> 回合前预建 Task 并注入 ext_info.task_id,
  使 SceneResourceAssembler 走 workbench 装配(PlaybookResource + 物化
  skills/resources 注入当前对话),主 Agent 在当前对话同步执行;
  任务列表可见、交付进空间、参与飞轮循环。
- 其余发起(API/定时/订阅/显式异步)由 start_task / fire_trigger / cron 各自
  建任务,走 playbook_runtime.run_task 后台执行,不经本路由。

设计取舍:
- **回合前预建任务,不做对话中途 promote**——规避"主 Agent 既建任务又自分析"
  导致的重复工作与卡死(历史教训:inline 任务包装)。
- 路由只在 workspace_id 有、task_id 无、initiator=page(或未指定)时触发;
  已绑定任务的会话(workbench 对话)与 API/定时/订阅发起一律跳过。
- 任何异常降级返回 None,保持原大厅对话行为,绝不阻断对话链路。
"""
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# 执行模式常量(存 Task.context_json["execution_mode"],P0 免迁移)
EXECUTION_MODE_IN_SESSION = "in_session"
EXECUTION_MODE_BACKGROUND = "background"

_INITIATORS_BACKGROUND = ("api", "cron", "webhook", "alert", "manual")


def extract_user_text(user_input: Any) -> str:
    """从 user_input 抽取纯文本(支持 str / OpenAI 消息对象 / content blocks)。"""
    if not user_input:
        return ""
    if isinstance(user_input, str):
        return user_input
    content = user_input.get("content") if isinstance(user_input, dict) else None
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, dict) and p.get("type") == "text":
                parts.append(p.get("text", ""))
            elif isinstance(p, str):
                parts.append(p)
        return " ".join(parts)
    return ""


def _playbook_service(system_app):
    from gyra_serve.playbook.service.service import (
        PLAYBOOK_SERVICE_COMPONENT_NAME, PlaybookService,
    )
    return system_app.get_component(PLAYBOOK_SERVICE_COMPONENT_NAME, PlaybookService)


def _task_service(system_app):
    from gyra_serve.task.service.service import (
        TASK_SERVICE_COMPONENT_NAME, TaskService,
    )
    return system_app.get_component(TASK_SERVICE_COMPONENT_NAME, TaskService)


def _workspace_service(system_app):
    from gyra_serve.workspace.service.service import (
        WORKSPACE_SERVICE_COMPONENT_NAME, WorkspaceService,
    )
    return system_app.get_component(WORKSPACE_SERVICE_COMPONENT_NAME, WorkspaceService)


def _match_playbook_id(playbook_service, workspace_id: int, text: str) -> Optional[int]:
    """隐式命中:用户文本包含空间内某个剧本名(名称匹配起步,后续可升级 LLM 判定)。"""
    if not text:
        return None
    try:
        from gyra_serve.playbook.api.schemas import PlaybookListFilter

        playbooks = playbook_service.list_playbooks(
            PlaybookListFilter(workspace_id=workspace_id, limit=200)
        ) or []
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[scene_router] list playbooks for match failed: {e}")
        return None
    # 名称越长越特异,优先精确包含的长名,避免短名误中
    best: Optional[int] = None
    best_len = 0
    for pb in playbooks:
        name = (getattr(pb, "name", "") or "").strip()
        if not name:
            continue
        if name in text and len(name) > best_len:
            best = getattr(pb, "id", None)
            best_len = len(name)
    return best


def route_scene_execution(
    ext_info: Dict[str, Any],
    user_input: Any,
    conv_uid: str,
    system_app: Any,
) -> Optional[Dict[str, Any]]:
    """回合前路由:判定并预建会话内任务。

    Args:
        ext_info: 对话请求的 ext_info(会就地注入 task_id / initiator)。
        user_input: 用户输入(用于隐式剧本名匹配)。
        conv_uid: 当前会话 id(会话内任务复用该会话,不新建专属会话)。
        system_app: 运行中的 SystemApp。

    Returns:
        {"task_id", "playbook_id", "playbook_name"} 命中并预建成功;
        None 未命中/跳过/异常(保持原大厅对话行为)。
    """
    if not ext_info:
        return None
    ws_id = ext_info.get("workspace_id")
    if not ws_id or ext_info.get("task_id") is not None:
        return None
    # 只路由"页面输入";API/定时/订阅/显式异步走各自后台路径
    if (ext_info.get("initiator") or "page") not in ("page", None):
        return None
    # 该会话已绑定任务(workbench 对话/后续轮次)-> 不重复建任务
    try:
        ws_service = _workspace_service(system_app)
        link = ws_service.get_conversation_workspace(conv_uid) if ws_service else None
        if link and link.get("task_id") is not None:
            return None
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[scene_router] check conv link failed: {e}")

    text = extract_user_text(user_input).strip()
    try:
        playbook_service = _playbook_service(system_app)
        task_service = _task_service(system_app)

        playbook_id = ext_info.get("playbook_id")
        if not playbook_id:
            playbook_id = _match_playbook_id(playbook_service, int(ws_id), text)
        if not playbook_id:
            return None

        playbook = playbook_service.get_by_id(int(playbook_id))
        if not playbook or not getattr(playbook, "is_active", True):
            return None

        from gyra_serve.task.api.schemas import TaskRequest

        task = task_service.create(TaskRequest(
            workspace_id=int(ws_id),
            playbook_id=int(playbook_id),
            title=text[:64] or getattr(playbook, "name", "") or "剧本任务",
            description=text or "",
            type="adhoc",
            status="running",
            triggered_by="page",
            conv_session_id=conv_uid,  # 复用当前会话:主 Agent 在当前对话同步执行
            created_by_user_id=ext_info.get("user_id"),
            context={"execution_mode": EXECUTION_MODE_IN_SESSION},
        ))

        # 注入 task_id:SceneResourceAssembler 据此走 workbench 装配(加载剧本能力)
        ext_info["task_id"] = task.id
        ext_info["initiator"] = "page"
        logger.info(
            f"[scene_router] page input hit playbook #{playbook_id} "
            f"'{getattr(playbook, 'name', '')}' -> in-session task #{task.id} "
            f"conv={conv_uid}"
        )
        return {
            "task_id": task.id,
            "playbook_id": int(playbook_id),
            "playbook_name": getattr(playbook, "name", "") or "",
        }
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[scene_router] route in-session task failed: {e}")
        return None
