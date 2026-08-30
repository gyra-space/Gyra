"""ECP serve configuration."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from gyra.core.awel.flow import (
    TAGS_ORDER_HIGH,
    ResourceCategory,
    auto_register_resource,
)
from gyra.util.i18n_utils import _
from gyra_serve.core import BaseServeConfig

APP_NAME = "ecp"
SERVE_APP_NAME = "gyra_serve_ecp"
SERVE_APP_NAME_HUMP = "gyra_serve_Ecp"
SERVE_CONFIG_KEY_PREFIX = "gyra.serve.ecp."
SERVE_SERVICE_COMPONENT_NAME = f"{SERVE_APP_NAME}_service"

# Database table names
TABLE_SEMANTIC_OBJECT = "gyra_serve_ecp_semantic_object"
TABLE_RESOLUTION_CACHE = "gyra_serve_ecp_resolution_cache"
TABLE_SEMANTIC_EDGE = "gyra_serve_ecp_semantic_edge"
TABLE_CONFIRMER = "gyra_serve_ecp_confirmer"
TABLE_OP_LOG = "gyra_serve_ecp_op_log"
TABLE_ASSET_REF = "gyra_serve_ecp_asset_ref"
TABLE_WORKSPACE_CONFIG = "gyra_serve_ecp_workspace_config"
TABLE_MISS_LEARN = "gyra_serve_ecp_miss_learn"
TABLE_SEMANTIC_ALIGNMENT = "gyra_serve_ecp_semantic_alignment"

# Semantic object types
# 结构化(DB): entity/metric/relation/dimension
# 非结构化(文档,ECP-unstructured-design P0): claim/terminology/policy
OBJECT_TYPES = (
    "entity",
    "metric",
    "relation",
    "dimension",
    "claim",
    "terminology",
    "policy",
)

# Status state machine:
#   proposed --confirm--> confirmed --new version confirmed--> old version superseded
#   proposed --reject--> rejected
#   confirmed --deprecate--> deprecated
STATUS_PROPOSED = "proposed"
STATUS_CONFIRMED = "confirmed"
STATUS_REJECTED = "rejected"
STATUS_DEPRECATED = "deprecated"
STATUS_SUPERSEDED = "superseded"

DEFAULT_WORKSPACE_ID = "default"


def ecp_import_dir() -> str:
    """上传报表文件的落盘目录(提案 Agent 用 read_report_file 分段读取)。

    与 datasource 上传文件同约定:~/.cache/gyra/<module>/。
    """
    path = str(Path.home() / ".cache" / "gyra" / "ecp_import")
    os.makedirs(path, exist_ok=True)
    return path

# ---------------------------------------------------------------- 提案来源
# provenance.origin 枚举(结构化溯源,取代 source 自由文本——source 保留兼容,
# 新写入由 provenance 派生)。历史 source 字符串经 origin_from_source 映射。
ORIGIN_DISCOVERY = "discovery"      # 初始扫描(批量提案管线 ingest)
ORIGIN_MISS_LEARN = "miss_learn"    # MISS 学习(兜底查询聚类 → 提案)
ORIGIN_MANUAL_SQL = "manual_sql"    # 手工 SQL 添加(添加即确认)
ORIGIN_RULE5_GATE = "rule5_gate"    # 自动补关系(执行门禁规则5触发的 relation 提案)
ORIGIN_EDIT = "edit"                # 人工编辑/归一化派生的新版本
ORIGIN_AGENT = "agent"              # 提案 Agent 主动提案(非 miss 上下文)
ORIGIN_IMPORT = "import"            # 资产快照导入
ORIGIN_LEGACY = "legacy"            # 历史数据(仅有 source 字符串,无法归类)

ORIGIN_LABELS = {
    ORIGIN_DISCOVERY: "初始扫描",
    ORIGIN_MISS_LEARN: "MISS 学习",
    ORIGIN_MANUAL_SQL: "手工 SQL",
    ORIGIN_RULE5_GATE: "自动补关系",
    ORIGIN_EDIT: "人工编辑",
    ORIGIN_AGENT: "Agent 提案",
    ORIGIN_IMPORT: "导入",
    ORIGIN_LEGACY: "历史数据",
}

# 历史 source 前缀 → origin(前缀匹配,按序;自由文本协议见 models/source 注释)
_LEGACY_SOURCE_ORIGINS = (
    ("discovery:", ORIGIN_DISCOVERY),
    ("sql_manual", ORIGIN_MANUAL_SQL),
    ("gate:rule5", ORIGIN_RULE5_GATE),
    ("edit_of:", ORIGIN_EDIT),
    ("normalize_of:", ORIGIN_EDIT),
    ("admin:", ORIGIN_EDIT),
    ("import", ORIGIN_IMPORT),
    ("agent:", ORIGIN_AGENT),
)


def origin_from_source(source: Optional[str]) -> str:
    """把历史 source 自由文本映射为 origin 枚举(老数据视图降级用)。"""
    s = source or ""
    for prefix, origin in _LEGACY_SOURCE_ORIGINS:
        if s.startswith(prefix):
            return origin
    return ORIGIN_LEGACY if s else ORIGIN_LEGACY


def make_provenance(
    origin: str,
    actor: Optional[str] = None,
    origin_sql: Optional[list] = None,
    miss_ref: Optional[dict] = None,
    note: Optional[str] = None,
    derived_from: Optional[str] = None,
) -> dict:
    """构造结构化 provenance(写入时快照;空字段省略,保持 JSON 紧凑)。"""
    prov: dict = {"origin": origin}
    if actor:
        prov["actor"] = actor
    if origin_sql:
        prov["origin_sql"] = [s for s in origin_sql if s]
    if miss_ref:
        prov["miss_ref"] = miss_ref
    if note:
        prov["note"] = note
    if derived_from:
        prov["derived_from"] = derived_from
    return prov


def carry_provenance(prev: Optional[dict], derived_from: str) -> dict:
    """编辑/确认派生新版本时携带原 provenance 并记录派生链。

    origin 保留最初来源(如 miss_learn)——"它是怎么来的"不因编辑改变;
    derived_from 记录本次派生点(如 edit_of:ent.x@v2)。无历史时按 edit 计。
    """
    prov = dict(prev or {})
    if "origin" not in prov:
        prov["origin"] = ORIGIN_EDIT
    prov["derived_from"] = derived_from
    return prov

# 内置默认提案 Agent(GptsApp app_code)。定义文件:building/app/service/
# gyra_app_define/ecp-proposal-agent.json,启动时经 load_define_app 播种发布,
# 基于 EcpProposalAgent 代码模板。工作空间未显式配置 proposal_agent_id 时,
# get_or_create_space 自动绑定该 app(见 service._ensure_default_proposal_agent)。
DEFAULT_PROPOSAL_AGENT_APP_CODE = "ecp-proposal-agent"


@auto_register_resource(
    label=_("ECP Serve Configurations"),
    category=ResourceCategory.COMMON,
    tags={"order": TAGS_ORDER_HIGH},
    description=_("Configuration for the ECP (enterprise semantic layer) serve module."),
    show_in_ui=False,
)
@dataclass
class ServeConfig(BaseServeConfig):
    """Configuration for the ECP serve module."""

    __type__ = APP_NAME

    enabled: bool = field(
        default=True,
        metadata={"help": _("Enable the ECP semantic layer serve")},
    )
    api_keys: Optional[str] = field(
        default=None,
        metadata={"help": _("Comma-separated API keys; empty means no auth")},
    )
    catalog_inject_threshold: int = field(
        default=500,
        metadata={
            "help": _(
                "Max confirmed objects injected into prompts as catalog; "
                "beyond this agents use search_semantics instead"
            )
        },
    )
