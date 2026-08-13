"""Proposal tools for the ECP proposal Agent (standard BAIZE paradigm).

These differ from the 6 query tools in ``ecp_tools.py`` (which answer business
questions). The proposal Agent explores a datasource's table specs + samples
dimension columns, then writes proposals via ``propose_semantic`` -- the single
write entry, validated by the DAO.

For the auto miss-learning cron (``auto_learn.py``) the Agent additionally needs
``get_miss_report`` (clustered uncovered queries) and ``search_semantics``
(confirmed catalog lookup to avoid duplicate proposals) -- both re-implemented
by delegating to ``ecp_tools.py`` so there is a single source of truth.

Built as attachable ``FunctionTool``s (mirrors ``build_ecp_agent_tools``) so an
``EcpProposalCapability`` can contribute them to a BAIZE agent's TOOLS slot.
``workspace_id`` is closure-bound (same workspace as the injected catalog);
``datasource_id`` is a tool parameter the Agent passes per task (one agent can
serve multiple datasources).
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from gyra.agent.resource.tool.base import FunctionTool

from ..config import DEFAULT_WORKSPACE_ID, OBJECT_TYPES, STATUS_PROPOSED
from ..models.models import OpLogDao, SemanticObjectDao

logger = logging.getLogger(__name__)

_MAX_DISTINCT = 31  # LIMIT 31 -> keep as dimension candidate if <= 30 distinct


def _get_connector(datasource_id: int):
    from gyra._private.config import Config
    from gyra_serve.datasource.manages.connect_config_db import ConnectConfigDao

    config = ConnectConfigDao().get_one({"id": datasource_id})
    db_name = getattr(config, "db_name", None)
    if not db_name:
        raise RuntimeError(f"数据源 {datasource_id} 不存在")
    return Config().local_db_manager.get_connector(db_name)


# --------------------------------------------------------------- tool builder
def build_proposal_tools() -> List[FunctionTool]:
    """Build ECP-specific proposal tools (sample_distinct_values / search_semantics /
    get_miss_report / propose_semantic).

    NOTE: get_table_spec is provided by DBCapability (db tools), not redefined here.
    DBCapability's get_table_spec now accepts both datasource_id (integer) and db_name (string).

    ``datasource_id`` and ``workspace_id`` are both tool parameters the Agent
    passes per task -- a code-template agent (EcpProposalAgent) doesn't know the
    workspace at class-definition time, so it passes workspace_id from the task
    message. Returned as ``FunctionTool`` for injection into available_system_tools.
    """

    async def _sample_distinct_values(
        datasource_id: int, table_name: str, column: str
    ) -> str:
        try:
            connector = _get_connector(datasource_id)
        except Exception as e:  # noqa: BLE001
            return json.dumps({"error": f"connector unavailable: {e}"}, ensure_ascii=False)
        sql = f"SELECT DISTINCT {column} FROM {table_name} LIMIT {_MAX_DISTINCT}"
        try:
            rows = await asyncio.to_thread(connector.run, sql)
        except Exception as e:  # noqa: BLE001
            return json.dumps({"error": f"sample failed: {e}"}, ensure_ascii=False)
        values = [str(r[0]) for r in (rows or []) if r and r[0] is not None]
        return json.dumps(
            {"column": column, "distinct_values": values, "count": len(values)},
            ensure_ascii=False,
        )

    async def _propose_semantic(
        object_id: str,
        obj_type: str,
        payload: Dict[str, Any],
        confidence: Optional[float] = None,
        workspace_id: str = DEFAULT_WORKSPACE_ID,
    ) -> str:
        from ..service.contracts import normalize_payload, validate_payload

        if obj_type not in OBJECT_TYPES:
            return json.dumps(
                {"error": f"obj_type 必须是 {OBJECT_TYPES} 之一"}, ensure_ascii=False
            )
        # 入库前归一 + 可执行级契约校验(与 confirm 晋升门禁同标准):不满足则拒绝入库,
        # 避免不可确认的"死提案"堆积进收件箱。agent 拿到 contract_gaps 后补全重提即可。
        normalized = normalize_payload(obj_type, payload)
        problems = validate_payload(obj_type, normalized, level="executable")
        if problems:
            return json.dumps(
                {
                    "error": "提案不满足可执行契约,未入库;请补全后重提",
                    "contract_gaps": problems,
                },
                ensure_ascii=False,
            )
        vo = SemanticObjectDao().create_proposal(
            object_id=object_id,
            obj_type=obj_type,
            payload=normalized,
            workspace_id=workspace_id,
            confidence=confidence,
            created_by="llm",
            source="agent:propose_semantic",
        )
        if vo.status == STATUS_PROPOSED:
            OpLogDao().append(
                "propose", workspace_id,
                {"id": object_id, "version": vo.version, "type": obj_type,
                 "source": "agent:propose_semantic"},
            )
            note = "提案已进入确认收件箱，确认前不影响任何查询"
        else:
            # 去重命中:返回已有 confirmed VO,未产生新提案
            note = "已存在相同的已确认版本,未重复提案"
        return json.dumps(
            {
                "proposal_id": f"{vo.id}@v{vo.version}",
                "status": vo.status,
                "note": note,
            },
            ensure_ascii=False,
        )

    async def _search_semantics(
        query: str, workspace_id: str = DEFAULT_WORKSPACE_ID
    ) -> str:
        from ..tools.ecp_tools import search_semantics as _impl

        return await _impl(query=query, workspace_id=workspace_id)

    async def _miss_report(
        min_count: int = 2,
        limit: int = 20,
        workspace_id: str = DEFAULT_WORKSPACE_ID,
    ) -> str:
        from ..tools.ecp_tools import get_miss_report as _impl

        return await _impl(
            min_count=min_count, limit=limit, workspace_id=workspace_id
        )

    return [
        FunctionTool(
            "sample_distinct_values",
            _sample_distinct_values,
            description="采样某表某列的 DISTINCT 真实值(最多30个)，用于猜测维度 label<->code 映射。仅对低基数文本列有意义。",
            args={
                "datasource_id": {"type": "integer", "description": "数据源 id"},
                "table_name": {"type": "string", "description": "表名"},
                "column": {"type": "string", "description": "列名"},
            },
        ),
        FunctionTool(
            "search_semantics",
            _search_semantics,
            description="搜索已确认的语义对象(指标/实体/维度/关系)。自动 miss 学习时,对照已确认目录,避免重复提案已有概念。",
            args={
                "query": {"type": "string", "description": "关键词(名称/别名/id)"},
                "workspace_id": {
                    "type": "string",
                    "description": "ECP 工作空间 id(默认 default)",
                    "required": False,
                },
            },
        ),
        FunctionTool(
            "get_miss_report",
            _miss_report,
            description="获取按频次聚类的未覆盖查询(execute_raw_sql 兜底记录)。自动 miss 学习入口:对高频且目录确实缺失的概念用 propose_semantic 提案。",
            args={
                "min_count": {
                    "type": "integer",
                    "description": "只返回出现次数>=此值的聚类,默认 2",
                    "required": False,
                },
                "limit": {
                    "type": "integer",
                    "description": "最多返回聚类数,默认 20",
                    "required": False,
                },
                "workspace_id": {
                    "type": "string",
                    "description": "ECP 工作空间 id(默认 default)",
                    "required": False,
                },
            },
        ),
        FunctionTool(
            "propose_semantic",
            _propose_semantic,
            description="落地一个语义资产提案(唯一写入口)。提案进入确认收件箱(status=proposed)，确认前不影响查询。",
            args={
                "object_id": {"type": "string", "description": "对象 id(ent./mtr./dim./rel. 前缀)"},
                "obj_type": {
                    "type": "string",
                    "description": "entity | metric | relation | dimension",
                },
                "payload": {"type": "object", "description": "类型对应的 payload 定义"},
                "confidence": {
                    "type": "number",
                    "description": "置信度 0-1",
                    "required": False,
                },
                "workspace_id": {
                    "type": "string",
                    "description": "ECP 工作空间 id(默认 default)",
                    "required": False,
                },
            },
        ),
    ]

