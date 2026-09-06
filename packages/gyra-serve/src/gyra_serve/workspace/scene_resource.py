"""WorkspaceSceneResource — RFC-005 资源协议实现(场景空间 lobby 资源)。

包含:
- SYSTEM 槽:静态框架(workspace_name + 四类管理工具使用引导),零 I/O
- TOOLS 槽:任务/剧本/介入/产物交付资产 管理工具全集(读+写)

设计:declare 纯函数;workspace_name 由装配器查 DB 填入 config;实时数据靠工具查。
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List

from gyra.agent.resource.tool.base import FunctionTool
from gyra.core.interface.resource.bundle import (
    CacheScope, Contribution, Lifetime, Slot,
)
from gyra.core.interface.resource.protocol import ResourceProtocol

from gyra_serve.workspace.agent_tools.read_tools import build_read_tools
from gyra_serve.workspace.agent_tools.write_tools import build_scene_write_tools


@dataclass
class WorkspaceSceneConfig:
    workspace_id: int
    conv_uid: str
    workspace_name: str
    team_summary: str = ""


def build_scene_management_tools(workspace_id: int, conv_uid: str) -> List[FunctionTool]:
    """四类管理工具全集:读(build_read_tools,10)+ 写(build_scene_write_tools,10)。

    system_app 取自全局 Config —— 此函数在请求上下文外(资源协议 declare)被调用,
    无法从请求取 system_app,故走全局单例 Config().SYSTEM_APP(运行时由 SystemApp
    初始化设置,见 gyra_app.base)。工具仅在此绑定闭包,不发起服务调用;真正调用
    工具时 system_app 已就绪。

    on_event 走 workspace 事件总线:工具执行产生的事件(task_created /
    intervention_triggered)广播进该 workspace 活跃对话的 SSE 流。
    """
    from gyra._private.config import Config
    from gyra_serve.workspace.event_bus import emit_workspace_event

    system_app = Config().SYSTEM_APP
    reads = build_read_tools(system_app, workspace_id)
    writes = build_scene_write_tools(
        system_app, workspace_id, user_id=None, conv_uid=conv_uid, task_id=None,
        on_event=lambda event_type, payload: emit_workspace_event(
            workspace_id, event_type, payload
        ),
    )
    return reads + writes


class WorkspaceSceneResource(ResourceProtocol):
    capability_id: str = "workspace_scene"

    @classmethod
    def declare(cls, config: WorkspaceSceneConfig) -> List[Contribution]:
        contributions: List[Contribution] = []
        contributions.append(Contribution(
            capability_id="workspace_scene:system",
            slot=Slot.SYSTEM,
            content=cls._render_system_framework(config),
            lifetime=Lifetime.SESSION, cache_scope=CacheScope.USER, order=0,
        ))
        if config.team_summary:
            # 专家团队清单（Agent Team 空间重构 Phase 1.2）：成员行+外挂摘要，
            # 使 Leader 无需工具调用即可看到"本空间有哪些专家、各带什么外挂"。
            contributions.append(Contribution(
                capability_id="workspace_scene:team",
                slot=Slot.SYSTEM,
                content=config.team_summary,
                lifetime=Lifetime.SESSION, cache_scope=CacheScope.USER, order=1,
            ))
        for tool in build_scene_management_tools(config.workspace_id, config.conv_uid):
            contributions.append(Contribution(
                capability_id=f"workspace_scene:tool:{tool.name}",
                slot=Slot.TOOLS, content=tool,
                lifetime=Lifetime.CONFIG_STATIC, cache_scope=CacheScope.NONE, order=0,
            ))
        return contributions

    @staticmethod
    def _render_system_framework(config: WorkspaceSceneConfig) -> str:
        # 唯一的工具速查表:身份与执行规则在 app 的 system_prompt_template,
        # 此块只按用途分组列出工具用法,不重复身份声明与行为规则。
        # Tool names below MUST exist in build_scene_management_tools output
        # (reads: list_tasks, get_task_info, list_artifacts, list_deliveries,
        # list_assets, get_workspace_memory, list_workspace_members,
        # list_playbooks(合约), get_playbook_detail,
        # get_expert_detail, list_interventions, list_triggers;
        # writes: start_task, close_task, publish_asset, create_delivery,
        # update_workspace, resolve_intervention,
        # abort_intervention, update_trigger, delete_trigger, fire_trigger).
        # 专家协作不走本表:专家清单在 SYSTEM 上下文【本空间专家团队】,各专家
        # 已作为 app 资源挂载,用标准 SubAgent 工具(agent_id=专家 app_code)协作。
        # Do NOT reference tools the agent doesn't have (e.g. create_task).
        return (
            f"# 场景空间工具速查（{config.workspace_name}）\n"
            "以当前会话实际挂载的工具为准，实时数据一律用工具按需查询：\n"
            "- 任务：list_tasks / get_task_info / start_task / close_task\n"
            "- 专家协作：标准 SubAgent 工具（agent_id=专家 app_code；mode=sync 同步等待结果，mode=async 后台独立运行完成后自动回传）；"
            "需要合约/交付物/任务台账的正式派单用 start_task(app_code=专家)；详情 get_expert_detail\n"
            "- 交付合约：list_playbooks / get_playbook_detail\n"
            "- 触发规则：list_triggers / update_trigger / fire_trigger / delete_trigger（删除需确认）\n"
            "- 交付与资产：list_artifacts / list_deliveries / list_assets / publish_asset / create_delivery\n"
            "- 协作与空间：list_interventions / resolve_intervention / abort_intervention / list_workspace_members / get_workspace_memory / update_workspace\n"
        )

    @staticmethod
    def to_agent_resource(config: "WorkspaceSceneConfig"):
        """序列化 WorkspaceSceneConfig 为 AgentResource(type="workspace_scene")。

        RFC-006 SSR Task 5:供 SceneResourceAssembler 装配 lobby 资源,并由
        CapabilityFactoryRegistry.build_pack 还原为 Contribution。

        序列化 config(workspace_id / conv_uid / workspace_name),使 factory
        反序列化时零 I/O(无需 DB refetch)。与 PlaybookResource.to_agent_resource
        (Task 4)对齐同模式。

        Args:
            config: 场景空间配置

        Returns:
            AgentResource(type="workspace_scene", value=<config JSON>)
        """
        import json as _json

        from gyra.agent.resource.base import AgentResource

        value = _json.dumps({
            "workspace_id": config.workspace_id,
            "conv_uid": config.conv_uid,
            "workspace_name": config.workspace_name,
            "team_summary": config.team_summary,
        }, ensure_ascii=False)
        return AgentResource(
            type="workspace_scene",
            name=f"workspace_scene_{config.workspace_id}",
            value=value,
        )
