"""按名字解析多媒体 Agent 并构建异步委派协程（Path A）。

供两处共用，保证 v1/v2 路径行为一致：
- V2:``ToolContextFactory`` 把本模块函数注入 ToolContext 资源
  ``subagent_delegate_factory``；
- V1:``SpawnAgentTaskTool`` 在 context 即主 agent 本身（无 ToolContext 资源）
  时直接调用。

解析顺序：``multimedia_resolver``（serve 层注入,app_code → 多媒体配置）→
``capability_pack`` 里的 AppCapability → AgentManager 共享模板（兼容既有行为）。
全部未命中/异常时记 warning 返回 None，由调用方回退 Path B
（subagent_manager delegate 的完整 react 循环、独立子会话）。
"""
from typing import Any, Callable, Optional

import logging

logger = logging.getLogger(__name__)


def resolve_multimedia_config(
    name: str,
    *,
    capability_pack: Optional[Any] = None,
    multimedia_resolver: Optional[Any] = None,
) -> tuple:
    """按名称（app_code / app_name）解析目标多媒体 app 的配置。

    返回 ``(config, app_code, app_name, app_desc)``；未命中返回 ``(None, "", "", "")``。
    优先用注入的 ``multimedia_resolver``，其次扫描 ``capability_pack`` 中匹配的
    ``AppCapability``（其 ``get_multimedia_config`` 只在 app 启用多媒体时返回配置）。
    """
    # 1) 注入的解析器（serve 层：app_code → 多媒体配置）
    if callable(multimedia_resolver):
        try:
            cfg = multimedia_resolver(name)
            if cfg:
                return cfg, name, "", ""
        except Exception:  # noqa: BLE001
            pass
    # 2) capability_pack 里的 AppCapability（按 app_code 或 app_name 匹配）
    for cap in (capability_pack.get_all("app") if capability_pack else []):
        code = getattr(cap, "app_code", "") or ""
        app_name = getattr(cap, "app_name", "") or ""
        if name not in (code, app_name):
            continue
        getter = getattr(cap, "get_multimedia_config", None)
        if not callable(getter):
            continue
        try:
            cfg = getter()
        except Exception:  # noqa: BLE001
            cfg = None
        return (
            cfg,
            code,
            app_name or name,
            getattr(cap, "app_desc", "") or "",
        )
    return None, "", "", ""


def build_multimedia_delegate(
    name: str,
    *,
    capability_pack: Optional[Any] = None,
    multimedia_resolver: Optional[Any] = None,
    running_agent: Optional[Any] = None,
    afs: Optional[Any] = None,
    conv_id: str = "",
) -> Optional[Callable[..., Any]]:
    """把名称解析为多媒体 Agent 的委派协程函数（按 app_code 寻址，多实例独立）。

    命中时按目标 app 自身的多媒体配置动态构造独立 ``MultimediaAgent`` 实例
    （互不覆盖）；未命中 app_code 时回退到协议层 AgentManager 按 role/别名
    （MULTIMEDIA）取共享模板（兼容既有行为）。

    Returns:
        ``MultimediaAgent.to_async_delegate`` 返回的 async callable
        ``(subagent_name, task, context)``；未命中/异常返回 None。
    """
    if not name:
        return None
    try:
        from gyra.agent.multimedia import MultimediaAgent

        config, code, app_name, app_desc = resolve_multimedia_config(
            name,
            capability_pack=capability_pack,
            multimedia_resolver=multimedia_resolver,
        )
        if config is not None:
            cfg = dict(config)
            if not cfg.get("name"):
                cfg["name"] = app_name or code or "multimedia_agent"
            if not cfg.get("description"):
                cfg["description"] = (
                    app_desc or f"多媒体生成 Agent（{app_name or code}）"
                )
            inst = MultimediaAgent(config=cfg)
        else:
            # 回退：role/别名 寻址到共享模板（兼容既有行为）
            from gyra.agent.core.agent_manage import get_agent_manager

            inst = get_agent_manager().get_agent(name)
            if not isinstance(inst, MultimediaAgent):
                return None
            if running_agent is not None and getattr(
                running_agent, "ext_config", None
            ):
                inst.ext_config = running_agent.ext_config

        # Path A 在主会话内直跑,spawn 的 conv_id 即主会话 id:注入 executor,
        # 使媒体轮询任务 context 记录 main_conv_id,主会话产物聚合
        # (collect_artifacts_for_main_conv)能查到。Path B 由 _start_app 经
        # agent_context.extra["main_conv_id"] 注入(见 agent._ensure_agent_file_system)。
        if conv_id:
            inst.executor.main_conv_id = conv_id
        return inst.to_async_delegate(afs=afs, conv_id=conv_id)
    except Exception as e:  # noqa: BLE001 - 注册表未就绪时回退
        # 不再静默:回退会让 spawn_agent_task 走 subagent_manager.delegate 的
        # 完整 react 循环路径(独立子会话),与 delegate 直跑 executor 的预期不同,
        # 且影响任务状态/success 判定(见 react_master_agent _delegate_via_app)。
        # 记 warning 使该回退可观测,便于排查"任务状态异常/子会话意外创建"。
        logger.warning(
            f"[subagent_delegate_factory] build delegate for {name} failed, "
            f"fallback to subagent_manager delegate path: {e}"
        )
        return None
