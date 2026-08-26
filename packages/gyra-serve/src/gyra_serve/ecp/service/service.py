"""ECP semantic object service: enforces the write rules of the protocol.

Write rules (docs/ECP.md 3.4), enforced here at a single point:
1. LLM writes are always `proposed`.
2. proposed -> confirmed is restricted to the confirmer list (empty list =
   open bootstrap).
3. Modification = new version + supersedes; no version is mutable or deletable.
4. Queries consume confirmed only (list_catalog); proposed consumption must be
   flagged by callers.
5. Cross-entity queries without a confirmed relation are rejected (enforced in
   the executor, P1).
"""

import copy
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from gyra.component import SystemApp
from gyra_serve.core import BaseService

from ..api.schemas import (
    AssetRefVO,
    CatalogEntryVO,
    ConfirmerVO,
    GraphLinkVO,
    GraphNodeVO,
    GraphVO,
    OpLogVO,
    ReadinessCheckVO,
    ReadinessVO,
    SemanticObjectListVO,
    SemanticObjectVO,
    SpaceInfoVO,
    WorkspaceConfigVO,
)
from ..config import (
    DEFAULT_WORKSPACE_ID,
    OBJECT_TYPES,
    SERVE_SERVICE_COMPONENT_NAME,
    STATUS_DEPRECATED,
    STATUS_PROPOSED,
    STATUS_REJECTED,
    ServeConfig,
)
from ..models.models import (
    AssetRefDao,
    ConfirmerDao,
    EcpSemanticObjectEntity,
    OpLogDao,
    ResolutionCacheDao,
    SemanticEdgeDao,
    SemanticObjectDao,
    WorkspaceConfigDao,
)

logger = logging.getLogger(__name__)


def _normalize_sql_pattern(sql: str, max_len: int = 200) -> str:
    """SQL 归一化为聚类模式键:小写、去字符串/数字字面值、压缩空白、截断。"""
    import re

    s = (sql or "").lower()
    s = re.sub(r"'[^']*'", "?", s)  # 字符串字面值
    s = re.sub(r"\b\d+(\.\d+)?\b", "?", s)  # 数字字面值
    s = re.sub(r"\s*([=<>(),;])\s*", r"\1", s)  # 操作符周围空白(Store = 1 vs Store=1)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:max_len]


def cluster_fallbacks(entries: List[Any]) -> List[dict]:
    """把 op_log fallback 条目按归一化模式聚类(频次降序,全量)。

    kind 分流(db/doc,ECP-unstructured P0):
    - db 条目(detail.sql):按归一化 SQL 模式聚类
    - doc 条目(detail.question):按归一化问题模式聚类
    Service.miss_report 与 get_miss_report 工具共用的聚类核心;截断由调用方做。
    """
    from .resolver import normalize_question

    clusters: dict = {}
    for e in entries:
        detail = e.detail or {}
        if detail.get("kind") == "doc" or "question" in detail:
            kind = "doc"
            pattern = normalize_question(detail.get("question") or "")
            example = detail.get("question") or ""
        else:
            kind = "db"
            pattern = _normalize_sql_pattern(detail.get("sql") or "")
            example = detail.get("sql") or ""
        key = (kind, detail.get("datasource_id"), pattern)
        c = clusters.setdefault(
            key,
            {
                "kind": kind,
                "datasource_id": detail.get("datasource_id"),
                "spaces": detail.get("spaces"),
                "pattern": pattern,
                "count": 0,
                "example_sql": example,
                "reasonings": [],
                "last_seen": e.ts,
            },
        )
        c["count"] += 1
        reasoning = detail.get("reasoning")
        if reasoning and reasoning not in c["reasonings"]:
            c["reasonings"].append(reasoning)
    return sorted(clusters.values(), key=lambda x: -x["count"])


class Service(BaseService[EcpSemanticObjectEntity, None, None]):
    """ECP hard semantic layer service."""

    name = SERVE_SERVICE_COMPONENT_NAME

    def __init__(self, system_app: SystemApp, config: ServeConfig):
        self._config = config
        super().__init__(system_app)

    def init_app(self, system_app: SystemApp) -> None:
        super().init_app(system_app)
        self._object_dao = SemanticObjectDao()
        self._cache_dao = ResolutionCacheDao()
        self._edge_dao = SemanticEdgeDao()
        self._confirmer_dao = ConfirmerDao()
        self._oplog_dao = OpLogDao()
        self._asset_dao = AssetRefDao()
        self._ws_config_dao = WorkspaceConfigDao()

    @property
    def config(self) -> ServeConfig:
        return self._config

    @property
    def dao(self) -> SemanticObjectDao:
        """Returns the internal DAO (primary object DAO for BaseService)."""
        return self._object_dao

    @property
    def object_dao(self) -> SemanticObjectDao:
        return self._object_dao

    @property
    def cache_dao(self) -> ResolutionCacheDao:
        return self._cache_dao

    @property
    def edge_dao(self) -> SemanticEdgeDao:
        return self._edge_dao

    @property
    def oplog_dao(self) -> OpLogDao:
        return self._oplog_dao

    @staticmethod
    def _ws(workspace_id: Optional[str]) -> str:
        return workspace_id or DEFAULT_WORKSPACE_ID

    # ---------------------------------------------------------------- proposals
    def propose(
        self,
        object_id: str,
        obj_type: str,
        payload: dict,
        workspace_id: Optional[str] = None,
        confidence: Optional[float] = None,
        evidence: Optional[list] = None,
        created_by: str = "llm",
        source: Optional[str] = None,
    ) -> SemanticObjectVO:
        """Create a proposal. Write rule 1: always lands in `proposed`."""
        if obj_type not in OBJECT_TYPES:
            raise ValueError(
                f"Invalid obj_type '{obj_type}', must be one of {OBJECT_TYPES}"
            )
        ws = self._ws(workspace_id)
        vo = self._object_dao.create_proposal(
            object_id=object_id,
            obj_type=obj_type,
            payload=payload,
            workspace_id=ws,
            confidence=confidence,
            evidence=evidence,
            created_by=created_by,
            source=source,
        )
        # 去重命中时 create_proposal 返回已有 confirmed VO(status=confirmed),
        # 不记 propose oplog(实际未产生新提案)。
        if vo.status == STATUS_PROPOSED:
            self._oplog_dao.append(
                "propose",
                ws,
                {"id": object_id, "version": vo.version, "type": obj_type,
                 "created_by": created_by, "source": source},
            )
        self._refresh_edges(vo, ws)
        return vo

    async def add_from_sql(
        self,
        sql: str,
        workspace_id: Optional[str] = None,
        description: Optional[str] = None,
        user_id: str = "user",
        confirm: bool = True,
    ) -> dict:
        """给一条用户写的 SQL 直接添加语义(添加即确认)。

        用户只需提供 SQL,其余(type/id/payload)由已配置的提案 Agent 提炼;提炼结果
        直接落库为 confirmed,不经待确认收件箱(手动显式添加即认定)。

        走不了 Agent 的场景(未配置 proposal_agent_id)抛 ValueError 提示先去治理配置;
        Agent 提炼的提案若不可执行契约不满足,不强制确认(避免"已确认但不可执行"),
        记入 errors(仍留在收件箱供人工编辑确认)。
        """
        from .contracts import normalize_payload, validate_payload

        ws = self._ws(workspace_id)
        cfg = self.get_workspace_config(ws)
        agent_id = getattr(cfg, "proposal_agent_id", None) if cfg else None
        if not agent_id:
            raise ValueError(
                "工作空间未配置提案 Agent(proposal_agent_id),"
                "请先在 ECP「治理」中配置提案 Agent 后再「给 SQL 添加语义」"
            )

        from ..service.proposal_runner import run_sql_proposal

        run = await run_sql_proposal(
            system_app=self._system_app,
            app_code=agent_id,
            workspace_id=ws,
            sql=sql,
            description=description,
        )
        confirmed_ids: List[str] = []
        errors: List[str] = list(run.errors or [])

        if run.proposal_ids and confirm:
            latest = self._object_dao.list_latest(
                workspace_id=ws, status=STATUS_PROPOSED,
                page=1, page_size=1000,
            )
            proposed_by_id = {it.id: it for it in (latest.items or [])}
            for pid in run.proposal_ids:
                vo = proposed_by_id.get(pid)
                if not vo:
                    continue
                try:
                    # 手动添加即确认:绕过确认人列表(用户显式以这条 SQL 完成添加),
                    # 但仍过可执行契约校验,不合格对象不混入 confirmed。
                    normalized = normalize_payload(vo.obj_type, vo.payload or {})
                    problems = validate_payload(
                        vo.obj_type, normalized, level="executable"
                    )
                    if problems:
                        errors.append(
                            f"{pid} 暂不可执行未确认(留在收件箱): "
                            f"{'; '.join(problems)}"
                        )
                        continue
                    confirmed_vo = self._object_dao.create_confirmed_version(
                        object_id=pid,
                        obj_type=vo.obj_type,
                        payload=normalized,
                        workspace_id=ws,
                        user_id=user_id,
                        evidence=vo.evidence,
                        source=f"sql_manual:{ws}",
                    )
                    confirmed_ids.append(confirmed_vo.id)
                    self._cache_dao.invalidate_referencing(pid, ws)
                    self._refresh_edges(confirmed_vo, ws)
                except Exception as e:  # noqa: BLE001
                    errors.append(f"{pid} 确认失败: {e}")

        if confirmed_ids:
            self._oplog_dao.append(
                "sql_add_confirm",
                ws,
                {"confirmed": confirmed_ids, "by": user_id, "proposed": run.proposal_ids},
            )

        # 去重/无产出说明:agent 对已存在口径调用 propose_semantic 命中去重时
        # 不会产生新提案,run.proposal_ids 为空则说明无新增语义。
        return {
            "workspace_id": ws,
            "added": len(confirmed_ids),
            "confirmed_ids": confirmed_ids,
            "duplicate_existing": [] if run.proposal_ids else [],
            "errors": errors,
        }

    # ------------------------------------------------------------------ confirm
    def confirm(
        self,
        object_id: str,
        version: int,
        user_id: str,
        workspace_id: Optional[str] = None,
        edited_payload: Optional[dict] = None,
    ) -> SemanticObjectVO:
        """Confirm a proposal. Write rules 2 & 3.

        With edited_payload: create a new version from the edit and confirm it
        (edit-then-confirm). The confirmed version supersedes older confirmed
        versions and invalidates resolution cache entries referencing the id.

        晋升门禁:confirmed = 可执行状态,确认前必须过 contracts 可执行级校验,
        不合格拒绝并返回问题列表(机器背书人类确认,防止"已确认但不可执行"
        对象入库——execute_metric_query 全线 PAYLOAD_INVALID 的根因)。
        校验前先 normalize:机械形态问题(entity_bindings→entity、code→codes
        等)自愈后以归一化 payload 写新版本确认,不折腾用户手改。
        """
        from .contracts import normalize_payload, validate_payload

        ws = self._ws(workspace_id)
        if not self._confirmer_dao.is_confirmer(ws, user_id):
            raise PermissionError(
                f"User '{user_id}' is not a confirmer of workspace '{ws}'"
            )
        if edited_payload is not None:
            target = self._object_dao.get_version(object_id, version, ws)
            if not target:
                raise ValueError(f"Object {object_id}@v{version} not found")
            normalized = normalize_payload(target.obj_type, edited_payload)
            problems = validate_payload(
                target.obj_type, normalized, level="executable"
            )
            if problems:
                raise ValueError(
                    f"payload 不满足可执行契约: {'; '.join(problems)}"
                )
            vo = self._object_dao.create_confirmed_version(
                object_id=object_id,
                obj_type=target.obj_type,
                payload=normalized,
                workspace_id=ws,
                user_id=user_id,
                supersedes=None,
                evidence=target.evidence,
                source=f"edit_of:{object_id}@v{version}",
            )
        else:
            proposed = self._object_dao.get_version(object_id, version, ws)
            if not proposed:
                raise ValueError(
                    f"Object {object_id}@v{version} not found or not in proposed"
                )
            normalized = normalize_payload(
                proposed.obj_type, proposed.payload or {}
            )
            problems = validate_payload(
                proposed.obj_type, normalized, level="executable"
            )
            if problems:
                raise ValueError(
                    f"对象 {object_id}@v{version} 不满足可执行契约,"
                    f"请编辑补全后再确认: {'; '.join(problems)}"
                )
            if normalized != (proposed.payload or {}):
                # 归一化有改动 → 以归一化 payload 写新版本确认(自愈)
                vo = self._object_dao.create_confirmed_version(
                    object_id=object_id,
                    obj_type=proposed.obj_type,
                    payload=normalized,
                    workspace_id=ws,
                    user_id=user_id,
                    supersedes=None,
                    evidence=proposed.evidence,
                    source=f"normalize_of:{object_id}@v{version}",
                )
            else:
                vo = self._object_dao.confirm_version(object_id, version, ws, user_id)
            if not vo:
                raise ValueError(
                    f"Object {object_id}@v{version} not found or not in proposed"
                )
        invalidated = self._cache_dao.invalidate_referencing(object_id, ws)
        self._oplog_dao.append(
            "confirm",
            ws,
            {"id": object_id, "version": vo.version, "by": user_id,
             "edited": edited_payload is not None,
             "cache_invalidated": invalidated},
        )
        self._refresh_edges(vo, ws)
        return vo

    def reject(
        self,
        object_id: str,
        version: int,
        user_id: str,
        workspace_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> SemanticObjectVO:
        ws = self._ws(workspace_id)
        if not self._confirmer_dao.is_confirmer(ws, user_id):
            raise PermissionError(
                f"User '{user_id}' is not a confirmer of workspace '{ws}'"
            )
        vo = self._object_dao.update_status(object_id, version, ws, STATUS_REJECTED)
        if not vo:
            raise ValueError(f"Object {object_id}@v{version} not found")
        self._oplog_dao.append(
            "reject", ws,
            {"id": object_id, "version": version, "by": user_id, "reason": reason},
        )
        return vo

    def deprecate(
        self,
        object_id: str,
        user_id: str,
        workspace_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> SemanticObjectVO:
        """Deprecate the confirmed version of an object (manual offlining)."""
        ws = self._ws(workspace_id)
        if not self._confirmer_dao.is_confirmer(ws, user_id):
            raise PermissionError(
                f"User '{user_id}' is not a confirmer of workspace '{ws}'"
            )
        confirmed = self._object_dao.get_confirmed(object_id, ws)
        if not confirmed:
            raise ValueError(f"Object {object_id} has no confirmed version")
        vo = self._object_dao.update_status(
            object_id, confirmed.version, ws, STATUS_DEPRECATED
        )
        invalidated = self._cache_dao.invalidate_referencing(object_id, ws)
        self._oplog_dao.append(
            "deprecate", ws,
            {"id": object_id, "version": confirmed.version, "by": user_id,
             "reason": reason, "cache_invalidated": invalidated},
        )
        return vo

    # ------------------------------------------------------------- admin(契约)
    def contract_check(self, workspace_id: Optional[str] = None) -> dict:
        """扫描 confirmed 对象的契约合规性(只读)。

        返回不合规清单(对象 id + 问题列表),供管理界面/启动 lint 使用。
        """
        from .contracts import validate_payload

        ws = self._ws(workspace_id)
        entries = self._object_dao.list_catalog(ws)
        non_compliant = []
        for e in entries:
            vo = self._object_dao.get_confirmed(e.id, ws)
            if not vo:
                continue
            problems = validate_payload(e.obj_type, vo.payload or {}, level="executable")
            if problems:
                non_compliant.append(
                    {"id": e.id, "obj_type": e.obj_type, "version": vo.version,
                     "problems": problems}
                )
        return {
            "workspace_id": ws,
            "total": len(entries),
            "non_compliant_count": len(non_compliant),
            "non_compliant": non_compliant,
        }

    def normalize_confirmed(
        self, workspace_id: Optional[str] = None, user_id: str = "system"
    ) -> dict:
        """一键修复不合规 confirmed 对象(契约归一化)。

        对每个 normalize 后可消除不合规项的对象,经 create_confirmed_version
        写**新版本**(版本不可变设计的正确姿势;不是 in-place 改 payload)——
        走应用自己的 DAO/连接,规避外部直写 WAL 竞态(2026-08-01 两次迁移
        被重启窗口回退的根治)。normalize 后仍不合规的对象跳过并列出(需人工
        编辑补全,如缺 entity 引用)。
        """
        from .contracts import normalize_payload, validate_payload

        ws = self._ws(workspace_id)
        check = self.contract_check(ws)
        fixed, skipped = [], []
        for item in check["non_compliant"]:
            vo = self._object_dao.get_confirmed(item["id"], ws)
            if not vo:
                continue
            normalized = normalize_payload(vo.obj_type, dict(vo.payload or {}))
            problems = validate_payload(vo.obj_type, normalized, level="executable")
            if problems:
                skipped.append({"id": item["id"], "problems": problems})
                continue
            new_vo = self._object_dao.create_confirmed_version(
                object_id=vo.id,
                obj_type=vo.obj_type,
                payload=normalized,
                workspace_id=ws,
                user_id=user_id,
                supersedes=None,
                evidence=vo.evidence,
                source="admin:normalize_confirmed",
            )
            self._refresh_edges(new_vo, ws)
            fixed.append({"id": vo.id, "version": new_vo.version})
        if fixed:
            self._oplog_dao.append(
                "normalize", ws,
                {"fixed": len(fixed), "skipped": len(skipped), "by": user_id},
            )
        return {
            "workspace_id": ws,
            "checked": check["total"],
            "fixed": fixed,
            "skipped": skipped,
        }

    # ------------------------------------------------------- admin(miss 飞轮)
    def miss_report(
        self,
        workspace_id: Optional[str] = None,
        limit: int = 20,
        scan_size: int = 500,
    ) -> dict:
        """聚类 op_log fallback miss(execute_raw_sql 兜底记录)。

        按归一化 SQL 模式分组(忽略字面值/空白差异),按频次排序——
        "大家在裸查什么"的可见化,learn_from_misses 的输入。
        """
        ws = self._ws(workspace_id)
        entries = self._oplog_dao.list(ws, op="fallback", page=1, page_size=scan_size)
        all_clusters = cluster_fallbacks(entries)
        return {
            "workspace_id": ws,
            "total_fallbacks": len(entries),
            "cluster_count": len(all_clusters),
            "clusters": all_clusters[:limit],
        }

    @staticmethod
    def build_miss_context(clusters: List[dict], max_items: int = 10) -> str:
        """把 miss 聚类构建成提案 agent 的领域上下文(问题驱动的提案素材)。"""
        if not clusters:
            return ""
        lines = [
            "【未覆盖的真实问题(miss 聚类,按频次排序)】",
            "以下是用户真实问过、但语义目录无法覆盖而走了 execute_raw_sql 兜底的查询。",
            "请优先为这些高频问题提炼可确认的语义资产(指标/维度/值字典),",
            "使后续同类问题能走 execute_metric_query 可信路径:",
        ]
        for i, c in enumerate(clusters[:max_items], 1):
            kind = c.get("kind", "db")
            if kind == "doc":
                lines.append(
                    f"\n{i}. [出现 {c['count']} 次] 文档问题(空间: "
                    f"{','.join(c.get('spaces') or ['?'])})"
                )
                example = (c.get("example_sql") or "").strip()
                if example:
                    lines.append(f"   问题: {example[:300]}")
            else:
                lines.append(
                    f"\n{i}. [出现 {c['count']} 次] 数据源 #{c.get('datasource_id')}"
                )
                example = (c.get("example_sql") or "").strip()
                if example:
                    lines.append(f"   SQL: {example[:400]}")
            for r in (c.get("reasonings") or [])[:3]:
                lines.append(f"   未命中原因: {r}")
        return "\n".join(lines)

    # -------------------------------------------------------------------- reads
    def inbox(
        self,
        workspace_id: Optional[str] = None,
        obj_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> SemanticObjectListVO:
        """Confirmation inbox: latest proposed versions."""
        return self._object_dao.list_latest(
            workspace_id=self._ws(workspace_id),
            obj_type=obj_type,
            status=STATUS_PROPOSED,
            page=page,
            page_size=page_size,
        )

    def list_objects(
        self,
        workspace_id: Optional[str] = None,
        obj_type: Optional[str] = None,
        status: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> SemanticObjectListVO:
        return self._object_dao.list_latest(
            workspace_id=self._ws(workspace_id),
            obj_type=obj_type,
            status=status,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )

    def get_object(
        self, object_id: str, workspace_id: Optional[str] = None
    ) -> Optional[SemanticObjectVO]:
        """Latest confirmed version; falls back to latest proposed for inbox UI."""
        ws = self._ws(workspace_id)
        vo = self._object_dao.get_confirmed(object_id, ws)
        if vo:
            return vo
        history = self._object_dao.version_history(object_id, ws)
        return history[0] if history else None

    def get_version(
        self, object_id: str, version: int, workspace_id: Optional[str] = None
    ) -> Optional[SemanticObjectVO]:
        """Fetch one exact version (any status) — for the debug preview dispatch."""
        return self._object_dao.get_version(
            object_id, version, self._ws(workspace_id)
        )

    # ------------------------------------------------------- debug preview(试跑)
    def preview_query(
        self,
        object_id: str,
        version: int,
        workspace_id: Optional[str] = None,
        filters: Optional[List[dict]] = None,
        group_by: Optional[List[str]] = None,
        time_range: Optional[dict] = None,
        limit: int = 20,
    ) -> dict:
        """确认页调试验证(DB 类):按提案版本只读 dry-run,返回 real data + SQL。

        纯读、不落库、不改状态;结果 trust=preview(永不 verified)——仅供确认人
        在确认前核对真实数据,不产生可信数字。
        """
        from .executor import preview_query as _preview_query

        return _preview_query(
            object_id, version, self._ws(workspace_id),
            filters=filters, group_by=group_by, time_range=time_range, limit=limit,
        )

    async def preview_canon(
        self,
        object_id: str,
        version: int,
        workspace_id: Optional[str] = None,
    ) -> dict:
        """确认页调试验证(文档类:claim/terminology/policy):anchor 回放校验出处。"""
        from .executor import preview_canon as _preview_canon

        return await _preview_canon(object_id, version, self._ws(workspace_id))

    def version_history(
        self, object_id: str, workspace_id: Optional[str] = None
    ) -> List[SemanticObjectVO]:
        return self._object_dao.version_history(object_id, self._ws(workspace_id))

    def catalog(
        self, workspace_id: Optional[str] = None, keyword: Optional[str] = None
    ) -> List[CatalogEntryVO]:
        """Write rule 4: the catalog exposes confirmed objects only."""
        return self._object_dao.list_catalog(self._ws(workspace_id), keyword)

    # ---------------------------------------------------------------- confirmers
    def list_confirmers(self, workspace_id: Optional[str] = None) -> List[ConfirmerVO]:
        vos = self._confirmer_dao.list(self._ws(workspace_id))
        return self._enrich_confirmer_names(vos)

    def _enrich_confirmer_names(
        self, vos: List[ConfirmerVO]
    ) -> List[ConfirmerVO]:
        """补充确认人用户名(设置页展示用);用户已删除/非数字 id 时为 None。"""
        if not vos:
            return vos
        user_ids: set = set()
        for v in vos:
            try:
                user_ids.add(int(v.user_id))
            except (TypeError, ValueError):
                continue
        names: Dict[int, str] = {}
        if user_ids:
            from gyra_app.auth.user_service import UserEntity

            with self._confirmer_dao.session(commit=False) as session:
                rows = (
                    session.query(UserEntity)
                    .filter(UserEntity.id.in_(list(user_ids)))
                    .all()
                )
                names = {u.id: u.name for u in rows}
        return [
            ConfirmerVO(
                id=v.id,
                workspace_id=v.workspace_id,
                user_id=v.user_id,
                scope=v.scope,
                user_name=names.get(int(v.user_id)),
            )
            for v in vos
        ]

    def add_confirmer(
        self, user_id: str, workspace_id: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> None:
        ws = self._ws(workspace_id)
        self._confirmer_dao.add(ws, user_id, scope)
        self._oplog_dao.append(
            "confirmer_add", ws, {"user_id": user_id, "scope": scope}
        )

    def remove_confirmer(self, confirmer_id: int) -> bool:
        return self._confirmer_dao.remove(confirmer_id)

    # -------------------------------------------------------------------- op log
    def list_op_log(
        self,
        workspace_id: Optional[str] = None,
        op: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> List[OpLogVO]:
        return self._oplog_dao.list(self._ws(workspace_id), op, page, page_size)

    # -------------------------------------------------------------- asset refs
    @property
    def asset_dao(self) -> AssetRefDao:
        return self._asset_dao

    def register_asset(
        self,
        kind: str,
        ref_id: str,
        workspace_id: Optional[str] = None,
        ref_meta: Optional[dict] = None,
    ) -> AssetRefVO:
        ws = self._ws(workspace_id)
        vo = self._asset_dao.register(kind, ref_id, ws, ref_meta)
        self._oplog_dao.append(
            "asset_register", ws, {"kind": kind, "ref_id": ref_id}
        )
        return vo

    def list_assets(
        self, workspace_id: Optional[str] = None, kind: Optional[str] = None
    ) -> List[AssetRefVO]:
        return self._asset_dao.list(self._ws(workspace_id), kind)

    def remove_asset(
        self,
        asset_id: int,
        workspace_id: Optional[str] = None,
    ) -> bool:
        """Unregister an asset reference from a workspace.

        ECP owns only the reference, so this does NOT touch the original
        asset (DB / space / document). Used by the ECP asset list "delete"
        action. Returns True if a row was removed.
        """
        ws = self._ws(workspace_id)
        removed = self._asset_dao.delete_in_workspace(asset_id, ws)
        if removed is None:
            return False
        self._oplog_dao.append(
            "asset_remove", ws, {"kind": removed.kind, "ref_id": removed.ref_id}
        )
        return True

    def readiness(
        self, datasource_id: int, workspace_id: Optional[str] = None
    ) -> ReadinessVO:
        """Check whether a DB asset is ready for proposal generation.

        Assets arrive incrementally (DB configured -> schema learned -> docs
        ingested); proposals must not run on incomplete material.
        """
        from gyra_serve.datasource.manages.connect_config_db import (
            ConnectConfigDao,
        )
        from gyra_serve.datasource.manages.table_spec_db import TableSpecDao

        ws = self._ws(workspace_id)
        checks: List[ReadinessCheckVO] = []

        config = ConnectConfigDao().get_one({"id": datasource_id})
        ds_ok = config is not None
        checks.append(
            ReadinessCheckVO(
                item="datasource_exists",
                ready=ds_ok,
                detail=getattr(config, "db_name", None) if ds_ok else "数据源不存在",
            )
        )

        spec_count = 0
        if ds_ok:
            spec_count = len(TableSpecDao().get_all_by_datasource(datasource_id))
        checks.append(
            ReadinessCheckVO(
                item="schema_learned",
                ready=spec_count > 0,
                detail=f"已学习 {spec_count} 张表"
                if spec_count
                else "尚未完成 Schema 学习，请先在数据源管理中执行学习",
            )
        )

        # Document assets are optional but recommended (industry knowledge
        # feeds proposal quality and confirmation evidence).
        doc_refs = [a for a in self._asset_dao.list(ws) if a.kind in ("document", "space")]
        checks.append(
            ReadinessCheckVO(
                item="documents",
                ready=True,
                detail=f"已登记 {len(doc_refs)} 个文档资产"
                if doc_refs
                else "未登记文档资产（可选；行业口径文档可提升提案质量）",
            )
        )

        ready = all(c.ready for c in checks if c.item != "documents")
        return ReadinessVO(
            kind="db", ref_id=str(datasource_id), ready=ready, checks=checks
        )

    # -------------------------------------------------------------------- graph
    def _refresh_edges(self, vo: SemanticObjectVO, ws: str) -> None:
        """写时物化:重算该对象的**对象→对象**出边进边表。

        挂在所有产生新版本的写路径上(propose / confirm / normalize_confirmed),
        replace_out_edges 删旧插新,天然增量;reject/deprecate 只改 status,
        边不动(状态由节点渲染)。资产边不进物化表(ref_id 可达 256 字符,
        超出边表 String(128);资产边只服务可视化,由 graph() 实时投影)。
        Best-effort:投影失败不阻塞业务写入(边表不是 source of truth,
        rebuild_edges 可全量重建)。
        """
        try:
            from .graph_projection import project_edges

            edges, _refs = project_edges(vo.obj_type, vo.payload or {})
            obj_edges = [
                e for e in edges if not e["dst"].startswith("asset:")
            ]
            self._edge_dao.replace_out_edges(vo.id, ws, vo.version, obj_edges)
        except Exception:  # noqa: BLE001
            logger.exception("edge projection failed for %s@v%s", vo.id, vo.version)

    def rebuild_edges(self, workspace_id: Optional[str] = None) -> dict:
        """幂等全量重建 workspace 的物化边投影(对象→对象边)。

        物化投影不是 source of truth:边永远可以从对象 payload 重算,
        丢了大不了重建。投影规则升级后一次调用即可对存量生效。
        (graph() 已改为查询时实时投影,本方法服务边表消费方——
        Agent 图遍历 / lint 影响分析。)
        """
        ws = self._ws(workspace_id)
        from .graph_projection import project_edges

        total_edges = 0
        objects = 0
        page = 1
        while True:
            result = self._object_dao.list_latest(
                workspace_id=ws, page=page, page_size=500
            )
            if not result.items:
                break
            for o in result.items:
                edges, _refs = project_edges(o.obj_type, o.payload or {})
                obj_edges = [
                    e for e in edges if not e["dst"].startswith("asset:")
                ]
                self._edge_dao.replace_out_edges(o.id, ws, o.version, obj_edges)
                total_edges += len(obj_edges)
                objects += 1
            if len(result.items) < 500:
                break
            page += 1
        self._oplog_dao.append(
            "graph_rebuild", ws, {"objects": objects, "edges": total_edges}
        )
        return {"workspace_id": ws, "objects": objects, "edges": total_edges}

    async def _knowledge_subgraph(
        self,
        ws: str,
        registered: Dict[tuple, AssetRefVO],
        referenced: Dict[tuple, None],
    ) -> tuple[List[GraphNodeVO], List[GraphLinkVO]]:
        """聚合知识空间 L2 图(wiki/doc/跨文档实体)为 kn 节点与边。

        查询时聚合路线:不落边表、零同步任务——vault 的边自带 valid_to
        时间有效性,文档重 ingest 旧边自动失效,聚合永远拿到当前有效图。

        端点映射(三层连通的关键):

        - ``verbat:<id>`` → 若 ``{slug}:{id}`` 是已知资产(已登记或被
          claim 引用),映射到**稳定资产节点 id**(与 claim 的 ref 边
          指向同一节点——资源层与知识层在此连通);否则降级为 kn 节点。
        - ``doc:<id>`` → kn 节点(wiki 页)。
        - 其他端点(实体名等裸标识) → kn 实体节点(``kn:<slug>:entity:<name>``)。

        节点来自 ``graph_query().nodes ∪ edges 端点``:孤立文档/实体
        (没有任何 L2 边)也会成为 kn 节点——刚 ingest 完还没建边的
        空间在全景图里立即可见。

        聚合空间来源(不依赖资产登记完整性):ECP 软层(ecp-<ws>) +
        已登记 space/document 资产 + 被 claim 引用的空间 + 场景空间
        派生的文档空间(workspace_id 形如 ecp_<code> → docs-<code>)。
        """
        from ..api.schemas import GraphLinkVO
        from .graph_projection import asset_node_id

        slugs = {f"ecp-{ws}"}
        for kind, ref_id in list(registered) + list(referenced):
            if kind == "space":
                slugs.add(ref_id)
            elif kind == "document" and ":" in ref_id:
                slugs.add(ref_id.split(":", 1)[0])
        # 场景空间派生:ECP workspace_id = ecp_<workspace_code>,
        # 文档空间 slug 约定 docs-<workspace_code>(workspace 模块上传入口)
        if ws.startswith("ecp_"):
            slugs.add(f"docs-{ws[len('ecp_') :]}")

        known_docs = set(registered) | set(referenced)
        nodes: Dict[str, GraphNodeVO] = {}
        links: List[GraphLinkVO] = []
        seen: set = set()

        try:
            from gyra_serve.knowledge.config import (
                SERVE_SERVICE_COMPONENT_NAME as KNOWLEDGE_SERVICE,
            )
            from gyra_serve.knowledge.service.service import (
                Service as KnowledgeService,
            )

            ks = self._system_app.get_component(KNOWLEDGE_SERVICE, KnowledgeService)
        except Exception:  # noqa: BLE001
            return [], []

        for slug in sorted(slugs):
            try:
                vault = await ks.get_vault(slug)
                sub = await vault.graph_query()
            except Exception:  # noqa: BLE001
                continue  # 空间不存在或暂不可达:跳过,不阻塞全景图

            def _map(endpoint: str) -> Optional[str]:
                if not endpoint:
                    return None
                if endpoint.startswith("verbat:"):
                    vid = endpoint.split(":", 1)[1]
                    if ("document", f"{slug}:{vid}") in known_docs:
                        return asset_node_id("document", f"{slug}:{vid}")
                if endpoint.startswith(("doc:", "verbat:")):
                    ep_type, ep_id = endpoint.split(":", 1)
                    kn_id = f"kn:{slug}:{endpoint}"
                    if kn_id not in nodes:
                        nodes[kn_id] = GraphNodeVO(
                            id=kn_id,
                            obj_type="wiki" if ep_type == "doc" else "verbat",
                            name=ep_id,
                            status="confirmed",
                            node_kind="kn",
                        )
                    return kn_id
                # 实体名等裸标识端点(如 curation 的实体名) → kn 实体节点
                kn_id = f"kn:{slug}:entity:{endpoint}"
                if kn_id not in nodes:
                    nodes[kn_id] = GraphNodeVO(
                        id=kn_id,
                        obj_type="entity",
                        name=endpoint,
                        status="confirmed",
                        node_kind="kn",
                    )
                return kn_id

            # 孤立节点(不在任何边上的 doc/verbat/实体)也纳入全景图
            for n in sub.nodes or []:
                _map(n)

            for e in sub.edges:
                src = _map(e.subject)
                dst = _map(e.object)
                if not src or not dst or src == dst:
                    continue
                key = (src, e.predicate, dst)
                if key in seen:
                    continue
                seen.add(key)
                links.append(
                    GraphLinkVO(source=src, target=dst, edge_type=e.predicate)
                )
        return list(nodes.values()), links

    async def graph(self, workspace_id: Optional[str] = None) -> GraphVO:
        """Asset-panorama graph view for one workspace.

        边**查询时实时投影**(纯函数,单空间 ≤ 千对象成本可忽略)——图
        永远反映当前对象/资产状态,不依赖物化边表是否跟上(存量数据
        冷启动也有连线)。物化边表只服务 Agent 图遍历/lint。

        节点三类(实时查询,零同步):硬层对象 + 资产节点(已登记 enrich
        名称/状态,被引用未登记 → 虚拟节点 status=unregistered) +
        知识层 kn 节点(L2 图聚合涌现)。
        """
        from .graph_projection import asset_node_id, project_edges

        ws = self._ws(workspace_id)
        objects = self._object_dao.list_latest(
            workspace_id=ws, page=1, page_size=1000
        ).items

        # ---- 实时投影:对象→对象边 + 对象→资产边(稳定资产节点 id)
        links: List[GraphLinkVO] = []
        seen: set = set()
        referenced: Dict[tuple, None] = {}
        for o in objects:
            edges, refs = project_edges(o.obj_type, o.payload or {})
            for key in refs:
                referenced[key] = None
            for e in edges:
                key = (o.id, e["edge_type"], e["dst"])
                if key in seen:
                    continue
                seen.add(key)
                links.append(
                    GraphLinkVO(
                        source=o.id, target=e["dst"], edge_type=e["edge_type"]
                    )
                )

        # ---- 资产节点:已登记(enrich) ∪ 被引用(未登记 → 虚拟节点)
        registered = {
            (a.kind, a.ref_id): a for a in self._asset_dao.list(ws)
        }
        nodes = [
            GraphNodeVO(
                id=o.id, obj_type=o.obj_type, name=o.name,
                status=o.status, version=o.version,
            )
            for o in objects
        ]
        for key in {**registered, **referenced}:
            kind, ref_id = key
            a = registered.get(key)
            nodes.append(
                GraphNodeVO(
                    id=asset_node_id(kind, ref_id),
                    obj_type=kind,
                    name=(
                        (a.ref_meta or {}).get("name") or ref_id if a else ref_id
                    ),
                    status=(a.status or "active") if a else "unregistered",
                    version=0,
                    node_kind="asset",
                )
            )

        # ---- knowledge 层聚合(kn 节点 + L2 边),best-effort 不阻塞
        try:
            kn_nodes, kn_links = await self._knowledge_subgraph(
                ws, registered, referenced
            )
            nodes.extend(kn_nodes)
            for lk in kn_links:
                key = (lk.source, lk.edge_type, lk.target)
                if key not in seen:
                    seen.add(key)
                    links.append(lk)
        except Exception:  # noqa: BLE001
            pass
        return GraphVO(nodes=nodes, links=links)

    # ------------------------------------------------------------- ECP space
    async def get_or_create_space(
        self, workspace_id: Optional[str] = None, owner_id: Optional[str] = None
    ) -> SpaceInfoVO:
        """Get-or-create the ECP soft-layer knowledge space for a workspace.

        The soft layer IS a knowledge space (llm-wiki); ECP only customizes
        its schema.md (P3). Slug convention: ecp-<workspace_id>.
        """
        ws = self._ws(workspace_id)
        slug = f"ecp-{ws}"
        from gyra_serve.knowledge.config import (
            SERVE_SERVICE_COMPONENT_NAME as KNOWLEDGE_SERVICE,
        )
        from gyra_serve.knowledge.service.service import Service as KnowledgeService

        ks = self._system_app.get_component(KNOWLEDGE_SERVICE, KnowledgeService)
        created = False
        try:
            await ks.get_space_config(slug)
        except Exception:  # noqa: BLE001
            await ks.create_space(slug, owner_id=owner_id, space_type="personal")
            created = True
            self._oplog_dao.append("space_create", ws, {"slug": slug})
        self._asset_dao.register("space", slug, ws, ref_meta={"name": slug})
        return SpaceInfoVO(slug=slug, workspace_id=ws, created=created)

    # ------------------------------------------------------ workspace config
    def get_workspace_config(
        self, workspace_id: Optional[str] = None
    ) -> WorkspaceConfigVO:
        return self._ws_config_dao.get(self._ws(workspace_id))

    def save_workspace_config(
        self,
        workspace_id: Optional[str] = None,
        proposal_agent_id: Optional[str] = None,
    ) -> WorkspaceConfigVO:
        ws = self._ws(workspace_id)
        vo = self._ws_config_dao.upsert(ws, proposal_agent_id)
        self._oplog_dao.append(
            "config_update", ws, {"proposal_agent_id": proposal_agent_id}
        )
        return vo

    # -------------------------------------------------- 资产迁移(导出 / 导入)
    # 语义资产是一份可携带的 JSON 快照;跨系统迁移时只需把 payload 里的
    # binding.datasource_id 换成目标系统的 datasource_id,其余(对象 id/
    # 版本链/状态/口径)原样保留,即可"点了就能用"。

    @staticmethod
    def _object_to_export_dict(vo: SemanticObjectVO) -> Dict[str, Any]:
        return {
            "id": vo.id,
            "version": vo.version,
            "workspace_id": vo.workspace_id,
            "obj_type": vo.obj_type,
            "status": vo.status,
            "name": vo.name,
            "payload": dict(vo.payload or {}),
            "confidence": vo.confidence,
            "evidence": vo.evidence,
            "created_by": vo.created_by,
            "created_at": vo.created_at,
            "confirmed_by": vo.confirmed_by,
            "confirmed_at": vo.confirmed_at,
            "source": vo.source,
            "supersedes": vo.supersedes,
        }

    @staticmethod
    def _asset_to_export_dict(vo: AssetRefVO) -> Dict[str, Any]:
        return {
            "id": vo.id,
            "workspace_id": vo.workspace_id,
            "kind": vo.kind,
            "ref_id": vo.ref_id,
            "ref_meta": dict(vo.ref_meta or {}),
            "status": vo.status,
            "last_checked_at": vo.last_checked_at,
        }

    @staticmethod
    def _coerce_datasource_id(value: Any) -> Any:
        """Coerce a datasource mapping value to int when possible.

        DB executor resolves connections by ``datasource_id`` (int column); a
        stray string "99" from the import UI would still usually coerce, but we
        normalise here so the imported payload is strictly well-typed.
        """
        if value is None:
            return value
        try:
            return int(value)
        except (TypeError, ValueError):
            return value

    @staticmethod
    def _collect_datasource_refs(
        objects: List[Dict[str, Any]], assets: List[Dict[str, Any]]
    ) -> Dict[str, dict]:
        """Collect the DB datasource ids referenced by an export snapshot.

        Returns ``{str(datasource_id): {datasource_id, tables?, db_name?, db_type?}}``
        so the import UI can offer an old→new mapping per datasource.
        """
        refs: Dict[str, dict] = {}
        for o in objects:
            payload = o.get("payload") or {}
            if o.get("obj_type") == "entity":
                binding = payload.get("binding") or {}
                if binding.get("kind", "db") != "db":
                    continue
                ds = binding.get("datasource_id")
                if ds is None:
                    continue
                info = refs.setdefault(
                    str(ds), {"datasource_id": str(ds), "tables": []}
                )
                table = binding.get("table")
                if table and table not in info["tables"]:
                    info["tables"].append(table)
        for a in assets:
            if a.get("kind") != "db":
                continue
            ds = a.get("ref_id")
            info = refs.setdefault(
                str(ds), {"datasource_id": str(ds), "tables": []}
            )
            meta = a.get("ref_meta") or {}
            if meta.get("db_name"):
                info["db_name"] = meta["db_name"]
            if meta.get("db_type"):
                info["db_type"] = meta["db_type"]
        return refs

    def export_workspace(self, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """Dump a workspace's semantic assets to a portable JSON snapshot."""
        ws = self._ws(workspace_id)
        object_dicts = [
            self._object_to_export_dict(o) for o in self._object_dao.list_all_versions(ws)
        ]
        asset_dicts = [self._asset_to_export_dict(a) for a in self._asset_dao.list(ws)]
        refs = self._collect_datasource_refs(object_dicts, asset_dicts)
        self._oplog_dao.append("export", ws, {"objects": len(object_dicts),
                                              "assets": len(asset_dicts)})
        return {
            "format_version": 1,
            "exported_at": datetime.now().isoformat(),
            "source_workspace_id": ws,
            "datasource_refs": list(refs.values()),
            "objects": object_dicts,
            "assets": asset_dicts,
        }

    def import_workspace(
        self,
        data: Dict[str, Any],
        workspace_id: Optional[str] = None,
        datasource_map: Optional[Dict[str, Any]] = None,
        user_id: str = "system",
    ) -> Dict[str, Any]:
        """Merge an exported snapshot into a workspace (default: the target).

        ``datasource_map`` maps ``str(old_datasource_id) -> new_datasource_id``;
        every ``entity.binding.datasource_id`` and ``db`` asset ref is rewritten
        through it so the imported assets bind to the target system's DBs and can
        be used directly.
        """
        ws = self._ws(workspace_id)
        map_ = datasource_map or {}
        objects = data.get("objects") or []
        assets = data.get("assets") or []
        imported, skipped, errors = 0, 0, []

        for o in objects:
            obj_type = o.get("obj_type")
            try:
                if obj_type not in OBJECT_TYPES:
                    raise ValueError(f"未知对象类型 {obj_type}")
                payload = copy.deepcopy(o.get("payload") or {})
                if obj_type == "entity":
                    binding = payload.get("binding") or {}
                    ds = binding.get("datasource_id")
                    if ds is not None:
                        binding["datasource_id"] = self._coerce_datasource_id(
                            map_.get(str(ds), ds)
                        )
                    if binding:
                        payload["binding"] = binding
                vo = self._object_dao.import_object(
                    object_id=o.get("id") or "",
                    version=int(o.get("version") or 1),
                    obj_type=obj_type,
                    workspace_id=ws,
                    status=o.get("status", STATUS_PROPOSED),
                    name=o.get("name"),
                    payload=payload,
                    confidence=o.get("confidence"),
                    evidence=o.get("evidence"),
                    created_by=o.get("created_by") or "import",
                    created_at=o.get("created_at"),
                    confirmed_by=o.get("confirmed_by"),
                    confirmed_at=o.get("confirmed_at"),
                    source=o.get("source"),
                    supersedes=o.get("supersedes"),
                )
                if vo:
                    imported += 1
                    self._refresh_edges(vo, ws)
                else:
                    skipped += 1
            except Exception as e:  # noqa: BLE001
                errors.append(f"{o.get('id')}: {e}")

        assets_imported = 0
        for a in assets:
            try:
                kind = a.get("kind")
                if kind == "db":
                    old = a.get("ref_id")
                    new = map_.get(str(old), old)
                    self._asset_dao.register(
                        "db", str(new), ws, ref_meta=a.get("ref_meta") or {}
                    )
                elif kind in ("document", "space", "api"):
                    self._asset_dao.register(
                        kind,
                        a.get("ref_id") or "",
                        ws,
                        ref_meta=a.get("ref_meta") or {},
                    )
                else:
                    continue
                assets_imported += 1
            except Exception as e:  # noqa: BLE001
                errors.append(f"asset:{a.get('kind')}:{a.get('ref_id')}: {e}")

        self._oplog_dao.append(
            "import", ws,
            {"imported": imported, "skipped": skipped,
             "assets_imported": assets_imported, "errors": errors[:20],
             "by": user_id},
        )
        return {
            "workspace_id": ws,
            "imported": imported,
            "skipped": skipped,
            "assets_imported": assets_imported,
            "errors": errors,
        }
