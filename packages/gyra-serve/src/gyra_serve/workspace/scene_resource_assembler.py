"""SceneResourceAssembler — 场景空间业务:对话前按 lobby/workbench 装配资源。

agent 代码不感知;由 chat_completions 端点预处理层调用。产出 List[AgentResource],
并进 ext_info["dynamic_resources"],由标准 build_pack 消费。

装配规则:
- lobby(task_id 为空) -> [WorkspaceSceneResource AgentResource]
- workbench 有 playbook_id -> [PlaybookResource AgentResource(完整 config)]
- workbench 无 playbook_id -> []
- 缺 workspace / 缺 task / 缺 playbook -> []
- 任何异常 -> [](装配器永不把异常抛入 chat 路径)

两分支均追加 ecp AgentResource(派生 ECP workspace,见 ecp_derive):使场景
agent 的 ECP 工具/目录/asset_gate 硬门禁自动落在本空间专属 ECP workspace,
语意资产按空间隔离;default 仅作全局共享库。
"""
import json
import logging
from typing import List, Optional

from gyra.agent.resource.base import AgentResource
from gyra_serve.playbook.resource.playbook_resource import (
    PlaybookConfig, PlaybookResource,
)
from gyra_serve.workspace.ecp_derive import derived_ecp_workspace_id
from gyra_serve.workspace.scene_resource import (
    WorkspaceSceneConfig, WorkspaceSceneResource,
)

logger = logging.getLogger(__name__)

# 真实组件名常量(与 workspace/service/service.py:WORKSPACE_SERVICE_COMPONENT_NAME、
# task/service/service.py:TASK_SERVICE_COMPONENT_NAME、
# playbook/service/service.py:PLAYBOOK_SERVICE_COMPONENT_NAME 对齐)。
_WORKSPACE = "serve_workspace_service"
_TASK = "serve_task_service"
_PLAYBOOK = "serve_playbook_service"


def _workspace_service(system_app):
    from gyra_serve.workspace.service.service import WorkspaceService

    return system_app.get_component(_WORKSPACE, WorkspaceService)


def _task_service(system_app):
    from gyra_serve.task.service.service import TaskService

    return system_app.get_component(_TASK, TaskService)


def _playbook_service(system_app):
    from gyra_serve.playbook.service.service import PlaybookService

    return system_app.get_component(_PLAYBOOK, PlaybookService)


class SceneResourceAssembler:
    """场景资源装配器:chat 前预处理,产出 List[AgentResource]。

    永不抛异常:任何装配失败都降级为 [],由调用方(端点预处理)原样写
    ext_info["dynamic_resources"];绝不阻塞对话链路。
    """

    @staticmethod
    def assemble(system_app, workspace_id: int,
                 task_id: Optional[int], conv_uid: str) -> List[AgentResource]:
        try:
            if task_id:
                return SceneResourceAssembler._assemble_workbench(
                    system_app, workspace_id, task_id,
                )
            return SceneResourceAssembler._assemble_lobby(
                system_app, workspace_id, conv_uid,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"SceneResourceAssembler failed: {e}", exc_info=True)
            return []

    @staticmethod
    def _ecp_resource(ws) -> AgentResource:
        """派生 ECP workspace 的 AgentResource(type="ecp")。

        由 CapabilityFactory build_pack 还原为 ECPCapability(目录注入 +
        6 工具闭包绑定 workspace_id + asset_gate 硬门禁)。纯计算无写库。
        """
        return AgentResource(
            type="ecp",
            name="ecp",
            value=json.dumps(
                {"workspace_id": derived_ecp_workspace_id(ws.workspace_code)},
                ensure_ascii=False,
            ),
        )

    @staticmethod
    def _assemble_lobby(system_app, workspace_id, conv_uid):
        # Coerce workspace_name to str defensively; production Workspace.name
        # is already str, so this is a no-op there and protects the JSON
        # serializer in to_agent_resource against unexpected object types.
        ws_service = _workspace_service(system_app)
        ws = ws_service.get_by_id(workspace_id) if ws_service else None
        if not ws:
            return []
        # 专家团队清单（Agent Team 空间重构 Phase 1.2）：装配成员行+外挂摘要进
        # Leader 上下文，使 Leader 无需工具调用即可感知本空间团队。
        team_summary = ""
        try:
            from gyra_serve.workspace.expert import WorkspaceExpertService

            team_summary = WorkspaceExpertService().assemble_team_summary(workspace_id)
        except Exception as e:
            logger.warning(f"assemble team summary failed (ws={workspace_id}): {e}")
        config = WorkspaceSceneConfig(
            workspace_id=workspace_id, conv_uid=conv_uid,
            workspace_name=str(getattr(ws, "name", "") or ""),
            team_summary=team_summary,
        )
        resources = [
            WorkspaceSceneResource.to_agent_resource(config),
            SceneResourceAssembler._ecp_resource(ws),
        ]
        # 每位专家挂为 Leader 的 app 资源（AgentResource type="app"）→
        # build_pack 还原为 AppCapability：标准 SubAgent 工具的 sync/async
        # 均可按 app_code 寻址到专家（统一走标准多 Agent 协作机制）。
        resources.extend(SceneResourceAssembler._expert_app_resources(workspace_id))
        return resources

    @staticmethod
    def _expert_app_resources(workspace_id: int) -> List[AgentResource]:
        """空间专家 → app AgentResource 列表;异常降级返回 [](不阻断装配)。"""
        try:
            from gyra_serve.workspace.expert.expert_api import (
                _get_app_info, _service,
            )

            out: List[AgentResource] = []
            for member in _service().list_members(workspace_id):
                app_info = _get_app_info(member.app_code)
                out.append(AgentResource(
                    type="app",
                    name=f"expert_{member.app_code}",
                    value=json.dumps({
                        "app_code": member.app_code,
                        "app_name": getattr(app_info, "app_name", None) or member.app_code,
                        "app_desc": getattr(app_info, "app_describe", None) or member.role_hint or "",
                    }, ensure_ascii=False),
                ))
            return out
        except Exception as e:  # noqa: BLE001
            logger.warning(f"expert app resources failed (ws={workspace_id}): {e}")
            return []

    @staticmethod
    def _assemble_workbench(system_app, workspace_id, task_id):
        task_service = _task_service(system_app)
        task = task_service.get_by_id(task_id) if task_service else None
        if not task:
            return []
        resources: List[AgentResource] = []
        # 派生 ECP workspace 资源(同 lobby);取不到 workspace 则不注入,降级为
        # 无 ECP 能力,不阻塞任务链路。
        ws_service = _workspace_service(system_app)
        ws = ws_service.get_by_id(workspace_id) if ws_service else None
        if ws:
            resources.append(SceneResourceAssembler._ecp_resource(ws))

        # Agent Team 空间重构 Phase 2.1/2.2:任务绑定了专家 →
        # 装配专家空间外挂(workspace_expert_equipment)进 agent 可调用工具集。
        # 无外挂行则跳过(用专家标准装备),异常降级不阻断。
        expert_app_code = getattr(task, "expert_app_code", None)
        if expert_app_code:
            try:
                from gyra_serve.workspace.materializer import (
                    materialize_expert_equipment,
                )
                resources.extend(
                    materialize_expert_equipment(
                        system_app, workspace_id, expert_app_code,
                    )
                )
            except Exception as e:
                logger.warning(
                    f"materialize expert equipment failed: {e}", exc_info=True
                )

        # 合约(收窄后的 playbook 表)存在 → 注入其交付/沉淀声明资源。
        # 合约的技能/数据源等能力已收敛于专家标准装备(GptsApp.resource_tool)+
        # 空间外挂(workspace_expert_equipment),不再从合约声明二次物化,
        # 因此这里仅注入承载合约文本/交付/沉淀规则的 PlaybookResource。
        if not task.playbook_id:
            return resources
        playbook_service = _playbook_service(system_app)
        pb = playbook_service.get_by_id(task.playbook_id) if playbook_service else None
        if not pb:
            return resources
        config = PlaybookConfig.from_playbook_response(pb)
        resources.append(PlaybookResource.to_agent_resource(config))
        return resources
