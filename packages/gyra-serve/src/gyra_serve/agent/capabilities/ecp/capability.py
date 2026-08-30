"""ECPCapability -- 企业语义层自管理资源能力(ECP P1「通电」)。

ECP 执行链路(DbBindingExecutor 门禁 / resolver 缓存 / ECP 工具集)已就绪并 8/8 验证,
本 capability 是把它「通电」到 Agent 的桥梁:

- ``prepare``:预载已确认目录文本(``build_catalog_text``)到 ``self``(declare 必须纯)
- ``declare``:目录摘要 + 行为约定 -> SYSTEM 槽;ECP 工具集(workspace_id 闭包绑定)
  -> TOOLS 槽
- 工具走 Route A builtin(react_master 装配 TOOLS 槽),``execute`` 留 NotImplementedError,
  与 DBCapability/WorkspaceSceneCapability 一致

照 ``WorkspaceSceneCapability``/``DBCapability`` 模式。``capability_id="ecp"``。
Agent 经 ``AgentResource(type="ecp", value={"workspace_id": ...})`` 绑定。
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from gyra.core.interface.resource.bundle import (
    CacheScope,
    Contribution,
    Lifetime,
    Slot,
)
from gyra.core.interface.resource.capability import Capability
from gyra.core.interface.resource.executor import (
    ExecutorCall,
    ExecutorStatus,
    ReleaseReason,
)

from gyra_serve.ecp.config import DEFAULT_WORKSPACE_ID

logger = logging.getLogger(__name__)


class ECPCapability(Capability):
    """企业语义层能力:declare 注入已确认目录 + 行为约定 + ECP 工具集。

    capability_id="ecp";executor_id 同。无 live state(目录文本 prepare 预载),
    prepare 载目录,release no-op。工具走 Route A builtin(react_master 装配)。
    """

    capability_id = "ecp"

    def __init__(
        self, workspace_id: str = DEFAULT_WORKSPACE_ID, system_app: Any = None
    ) -> None:
        self._workspace_id = workspace_id or DEFAULT_WORKSPACE_ID
        self._system_app = system_app
        self._catalog_text: str = ""
        self._managed_assets_text: str = ""
        self._has_managed_db: bool = False
        self._status = ExecutorStatus.UNINITIALIZED

    @classmethod
    def from_config(cls, value: Any, system_app: Any = None) -> "ECPCapability":
        """从 ``AgentResource.value`` 构造。value 兼容 dict / JSON string / 裸 string。

        workspace_id 缺省 ``DEFAULT_WORKSPACE_ID``。scene 的 int workspace_id 由
        绑定方 ``str()`` 转换后传入。无 I/O。
        """
        import json

        ws: Any = DEFAULT_WORKSPACE_ID
        if isinstance(value, dict):
            ws = (
                value.get("workspace_id")
                or value.get("workspace")
                or DEFAULT_WORKSPACE_ID
            )
        elif isinstance(value, str) and value.strip():
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    ws = (
                        parsed.get("workspace_id")
                        or parsed.get("workspace")
                        or ws
                    )
                else:
                    ws = parsed
            except (json.JSONDecodeError, TypeError):
                ws = value
        return cls(workspace_id=str(ws), system_app=system_app)

    @property
    def executor_id(self) -> str:
        return self.capability_id

    def requires(self, config: Any = None) -> List[str]:
        # 不依赖共享底座(如 sandbox),与 MemoryCapability/WorkspaceSceneCapability 一致。
        return []

    async def prepare(self) -> None:
        """预载已确认目录文本(供 declare 注入)。I/O 步。

        declare 须纯函数,故目录查询在此完成存 ``self._catalog_text``。目录为空时置空
        (declare 仅注入行为约定,不制造噪音)。失败降级为空目录,不阻塞 Agent 启动。

        同载托管资产清单(asset_gate.build_managed_assets_text):直接绑定被门禁
        移除后,模型需从清单得知 DB 仍可达且统一走 ECP 工具。清单失败独立降级,
        不影响目录。
        """
        try:
            from gyra_serve.ecp.service.catalog import build_catalog_text

            self._catalog_text = build_catalog_text(
                self._workspace_id, max_objects=self._resolve_catalog_threshold()
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"[ecp-capability] load catalog for {self._workspace_id} failed: {e}"
            )
            self._catalog_text = ""
        try:
            from gyra_serve.ecp.service.asset_gate import (
                build_managed_assets_text,
                managed_db_datasource_ids,
            )

            self._managed_assets_text = build_managed_assets_text(self._workspace_id)
            self._has_managed_db = bool(
                managed_db_datasource_ids({self._workspace_id})
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"[ecp-capability] load managed assets for {self._workspace_id} failed: {e}"
            )
            self._managed_assets_text = ""
            self._has_managed_db = False
        self._status = ExecutorStatus.READY

    def _resolve_catalog_threshold(self) -> Optional[int]:
        """解析目录全量注入阈值(ServeConfig.catalog_inject_threshold)。

        兑现 ECP 5.2 分层披露:条目数超阈值时 build_catalog_text 降级为
        L0 摘要。返回 None 表示不限制——无 system_app(单测直构)或配置
        缺失/异常时均降级为全量注入,小目录场景零回归、不阻塞 prepare。
        """
        system_app = self._system_app
        if system_app is None:
            try:
                from gyra._private.config import Config

                system_app = Config().SYSTEM_APP
            except Exception:  # noqa: BLE001
                return None
        if system_app is None:
            return None
        try:
            from gyra_serve.ecp.config import SERVE_SERVICE_COMPONENT_NAME
            from gyra_serve.ecp.service.service import Service

            serve = system_app.get_component(SERVE_SERVICE_COMPONENT_NAME, Service)
            threshold = int(serve.config.catalog_inject_threshold)
            return threshold if threshold > 0 else None
        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"[ecp-capability] resolve catalog_inject_threshold failed: {e}"
            )
            return None

    def declare(self, config: Any = None) -> List[Contribution]:
        """注入目录摘要 + 行为约定(SYSTEM)+ ECP 工具集(TOOLS)。

        纯函数:目录文本已由 prepare 预载;工具对象构造无 I/O。
        """
        from gyra_serve.ecp.service.catalog import BEHAVIOR_GUIDE
        from gyra_serve.ecp.tools.ecp_tools import build_ecp_agent_tools

        contribs: List[Contribution] = []

        # SYSTEM: 目录摘要(若有)+ 托管资产清单(若有)+ 行为约定
        system_parts = []
        if self._catalog_text:
            system_parts.append(self._catalog_text)
        if self._managed_assets_text:
            system_parts.append(self._managed_assets_text)
        system_parts.append(BEHAVIOR_GUIDE)
        contribs.append(
            Contribution(
                capability_id=f"{self.capability_id}:system",
                slot=Slot.SYSTEM,
                content="\n\n".join(system_parts),
                lifetime=Lifetime.SESSION,
                cache_scope=CacheScope.USER,
                order=30,
            )
        )

        # TOOLS: ECP 工具集(workspace_id 闭包绑定,agent 无需传 workspace_id)
        for tool in build_ecp_agent_tools(self._workspace_id):
            contribs.append(
                Contribution(
                    capability_id=f"{self.capability_id}:tool:{tool.name}",
                    slot=Slot.TOOLS,
                    content=tool,
                    lifetime=Lifetime.CONFIG_STATIC,
                    cache_scope=CacheScope.NONE,
                    order=30,
                )
            )

        # TOOLS: app_card_preview -- AppCard 开发期取数预览。场景空间对话只绑
        # workspace_scene+ecp、不绑定 datasource/DBResource,base_agent 的
        # _inject_database_tools 不会经 DBResource 注入它,导致 app-card-generator
        # skill 要求的「用 hook 工具逐条验证取数」在开发对话里找不到工具。此处
        # 显式注入:闭包绑定本 ECP 的 workspace_id(与上面 ECP 工具集同构,agent
        # 无需传 workspace_id),仅暴露 op/params/query_key/queries 四个入参。
        contribs.append(
            Contribution(
                capability_id=f"{self.capability_id}:tool:app_card_preview",
                slot=Slot.TOOLS,
                content=_build_app_card_preview_tool(self._workspace_id),
                lifetime=Lifetime.CONFIG_STATIC,
                cache_scope=CacheScope.NONE,
                order=30,
            )
        )

        # TOOLS: 托管 db 资产的降级连带注入——只读 schema 工具(get_table_spec/
        # list_tables/search_tables)。ECP 托管的资源以降级形态出现:结构可查
        # (供 execute_raw_sql 兜底与提案理解物理表),数据查询只走 ECP 工具;
        # execute_sql 不连带,若经直接绑定注入则由 asset_gate 硬门禁拦截。
        # 只绑 ECP 也能读 schema。
        if self._has_managed_db:
            for tool in _load_db_schema_tools():
                contribs.append(
                    Contribution(
                        capability_id=f"{self.capability_id}:tool:{tool.name}",
                        slot=Slot.TOOLS,
                        content=tool,
                        lifetime=Lifetime.CONFIG_STATIC,
                        cache_scope=CacheScope.NONE,
                        order=31,
                    )
                )
        return contribs

    async def execute(self, call: ExecutorCall) -> Any:
        # ECP 工具走 Route A builtin(react_master 装配 TOOLS 槽),不走 Route B。
        raise NotImplementedError(
            "ECPCapability.execute 不走 Route B -- ECP 工具走 builtin Route A"
        )

    async def release(self, reason: ReleaseReason) -> None:
        self._status = ExecutorStatus.RELEASED


def _build_app_card_preview_tool(workspace_id: str) -> "FunctionTool":
    """把全局注册的 ``app_card_preview``(ToolBase)包装成闭包绑 ``workspace_id`` 的
    FunctionTool,供 ECP 场景 TOOLS 槽注入。

    背景:app 卡片开发对话(场景空间 lobby)只绑 ``workspace_scene``+``ecp``、不绑
    ``datasource``/``DBResource``,故 base_agent 的 ``_inject_database_tools`` 不会经
    DBResource 注入它。此处显式包装后注入,使 app-card-generator skill 要求的
    「用 hook 工具逐条验证取数」在开发对话真正可用。

    与 ECP 工具群一致:``workspace_id`` 闭包绑定,agent 只传 ``op``/``params``/
    ``query_key``/``queries`` 四个入参,不必知道 workspace_id。
    """
    import json as _json
    from typing import Dict, List, Optional

    from gyra.agent.resource.tool.base import FunctionTool
    from gyra.agent.tools.context import ToolContext
    from gyra.agent.tools.registry import tool_registry

    try:
        import gyra_serve.app_card.agent_tools  # noqa: F401  触发 @tool 注册
    except ImportError:
        pass
    preview = tool_registry.get("app_card_preview")

    if preview is None:
        # 注册缺失时优雅降级:返回一个明确报错工具,避免 declare 抛异常阻塞场景装配。
        async def _missing(*_args: Any, **_kwargs: Any) -> str:
            return _json.dumps(
                {
                    "trust": "none",
                    "error": "app_card_preview 工具不可用(未注册)",
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                },
                ensure_ascii=False,
            )

        return FunctionTool(
            "app_card_preview",
            _missing,
            description="AppCard 应用卡片开发期取数预览(暂不可用:工具未注册)",
            args={},
        )

    async def _invoke(
        op: str,
        params: Optional[Dict[str, Any]] = None,
        query_key: Optional[str] = None,
        queries: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        args = {
            "op": op,
            "params": params or {},
            "query_key": query_key,
            "queries": queries or [],
            "workspace_id": (
                int(workspace_id) if str(workspace_id).lstrip("-").isdigit() else workspace_id
            ),
        }
        result = await preview.execute(args, ToolContext())
        if result is None:
            return _json.dumps(
                {"trust": "none", "error": "空结果", "columns": [], "rows": [], "row_count": 0},
                ensure_ascii=False,
            )
        return result.output if result.output is not None else ""

    return FunctionTool(
        "app_card_preview",
        _invoke,
        description=(
            "AppCard 应用卡片开发期取数预览：按运行期同一派发路径执行 query.sql / "
            "query.metric，返回对象数组 rows + trust + row_count + elapsed_ms(性能基线)。"
            "开发应用卡片时用它验证 SQL/指标列名与取数、并评估/调优查询性能，"
            "避免用 execute_sql(二维数组 rows)写代码导致运行期渲染错乱。"
            "datasource_id 通过 params 传入(如 params={'sql': '...', 'datasource_id': 1})。"
        ),
        args={
            "op": {
                "type": "string",
                "description": "取值：query.sql / sql.preview / query.metric / metric.preview / sql.explain",
            },
            "params": {
                "type": "object",
                "description": (
                    "query.sql 传 {sql, datasource_id, bind_params?, limit?}；"
                    "query.metric 传 {metric_id, group_by?, filters?, time_range?}。"
                ),
                "required": False,
            },
            "query_key": {
                "type": "string",
                "description": "引用 queries 里已声明的命名查询(可选，与 params 二选一)",
                "required": False,
            },
            "queries": {
                "type": "array",
                "description": "命名查询契约(未落库也可)，配合 query_key 引用",
                "required": False,
            },
        },
    )


def _load_db_schema_tools() -> List[Any]:
    """取只读 schema 工具(get_table_spec/list_tables/search_tables)供托管资产降级连带注入。

    复用 tool_registry 中已注册的 DB 工具(与 _inject_database_tools 同源),
    执行期经 ConnectConfigDao/local_db_manager 解析连接,不依赖 agent 侧绑定
    DBCapability。与 asset_gate 的设计声明一致:只读 schema 工具不管控,
    数据查询直连(execute_sql)不连带,由门禁/ECP 工具接管。
    注册表缺失/未导入时返回空(不阻塞 declare)。
    """
    from gyra.agent.tools.registry import tool_registry

    try:
        import gyra_serve.agent.capabilities.db.tools._db_tools_impl  # noqa: F401
    except ImportError:
        return []
    tools: List[Any] = []
    for name in ("get_table_spec", "list_tables", "search_tables"):
        t = tool_registry.get(name)
        if t is not None:
            tools.append(t)
    return tools


def ecp_factory(value: Any, system_app: Any = None) -> Capability | None:
    """build_pack 调:type_key="ecp" 的 factory。

    value 是 ``AgentResource.value``(经 ``_normalize_value`` 规范化后的 dict 或原始
    string)。还原 ``ECPCapability``。返回 None 表示无法解析(被 build_pack 跳过,
    不阻塞其它资源)。
    """
    try:
        return ECPCapability.from_config(value, system_app=system_app)
    except Exception as e:  # noqa: BLE001
        logger.warning(
            f"ecp factory: failed to build from value {value!r}: {e}; skipping"
        )
        return None
