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

模块结构(Service 为门面,各领域协作者均为无状态、持有 svc 引用):
- 本文件:提案生命周期(propose/confirm/reject/deprecate/add_from_sql)、
  契约 admin、读模型、确认人
- miss.py           miss 飞轮(聚类/学习标记/学习上下文)
- graph.py          资产全景图(写时物化 + 查询时实时投影)
- alignment_ops.py  语义对齐运营(LLM 候选固化/确认/手工兜底)
- assets.py         资产引用注册 + readiness
- workspace.py      软层 space 供给 + workspace 配置
- transfer.py       资产导出/导入
- knowledge_bridge.py  knowledge 软层只读桥梁(图谱/对齐共用)
"""

import logging
from typing import Any, Dict, List, Optional

from gyra.component import SystemApp
from gyra_serve.core import BaseService

from ..api.schemas import (
    AssetRefVO,
    CatalogEntryVO,
    ConfirmerVO,
    GraphVO,
    MissLearnVO,
    OpLogVO,
    ReadinessVO,
    SemanticAlignmentVO,
    SemanticObjectListVO,
    SemanticObjectVO,
    SpaceInfoVO,
    WorkspaceConfigVO,
)
from ..config import (
    DEFAULT_WORKSPACE_ID,
    OBJECT_TYPES,
    ORIGIN_MANUAL_SQL,
    SERVE_SERVICE_COMPONENT_NAME,
    STATUS_CONFIRMED,
    STATUS_DEPRECATED,
    STATUS_PROPOSED,
    STATUS_REJECTED,
    ServeConfig,
    carry_provenance,
    make_provenance,
)
from ..models.models import (
    AssetRefDao,
    ConfirmerDao,
    EcpSemanticObjectEntity,
    MissLearnDao,
    OpLogDao,
    ResolutionCacheDao,
    SemanticAlignmentDao,
    SemanticEdgeDao,
    SemanticObjectDao,
    WorkspaceConfigDao,
)
from .alignment_ops import AlignmentOps
from .assets import AssetOps
from .graph import GraphOps

# 兼容 re-export:聚类纯函数已迁至 miss.py,历史调用方(tests/tools)仍从这里 import
from .miss import MissFlywheel, _normalize_sql_pattern, cluster_fallbacks  # noqa: F401
from .transfer import TransferOps
from .workspace import WorkspaceOps

logger = logging.getLogger(__name__)


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
        self._miss_learn_dao = MissLearnDao()
        self._alignment_dao = SemanticAlignmentDao()

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

    @property
    def asset_dao(self) -> AssetRefDao:
        return self._asset_dao

    @staticmethod
    def _ws(workspace_id: Optional[str]) -> str:
        return workspace_id or DEFAULT_WORKSPACE_ID

    # -------------------------------------- collaborators(无状态,按需构造)
    @property
    def _miss(self) -> MissFlywheel:
        return MissFlywheel(self)

    @property
    def _graph(self) -> GraphOps:
        return GraphOps(self)

    @property
    def _alignment(self) -> AlignmentOps:
        return AlignmentOps(self)

    @property
    def _assets(self) -> AssetOps:
        return AssetOps(self)

    @property
    def _workspace(self) -> WorkspaceOps:
        return WorkspaceOps(self)

    @property
    def _transfer(self) -> TransferOps:
        return TransferOps(self)

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
        provenance: Optional[dict] = None,
        gate_level: Optional[str] = None,
    ) -> SemanticObjectVO:
        """Create a proposal. Write rule 1: always lands in `proposed`.

        唯一提案写入口(API/工具/批量管线/执行门禁全部汇聚于此):
        - ``gate_level="executable"``:入库前过可执行级契约校验(与 confirm
          晋升门禁同标准),不满足抛 ContractViolation——避免不可确认的
          "死提案"堆积进收件箱(Agent 工具路径用);None 则只做类型校验
          (批量管线已自行过 proposal 级契约)。
        - entity 确定性兜底(Oracle owner 补全 + 时间列 role=time)在此
          统一执行,三条写入路径质量拉齐(原仅在 ecp_tools 路径有)。
        """
        if obj_type not in OBJECT_TYPES:
            raise ValueError(
                f"Invalid obj_type '{obj_type}', must be one of {OBJECT_TYPES}"
            )
        ws = self._ws(workspace_id)
        if gate_level == "executable":
            from .contracts import (
                ContractViolation,
                normalize_payload,
                validate_payload,
            )

            payload = normalize_payload(obj_type, payload)
            self._normalize_entity_binding_fallback(payload, obj_type)
            problems = validate_payload(obj_type, payload, level="executable")
            if problems:
                raise ContractViolation(problems)
        vo = self._object_dao.create_proposal(
            object_id=object_id,
            obj_type=obj_type,
            payload=payload,
            workspace_id=ws,
            confidence=confidence,
            evidence=evidence,
            created_by=created_by,
            source=source,
            provenance=provenance,
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

    @staticmethod
    def _normalize_entity_binding_fallback(payload: dict, obj_type: str) -> None:
        """entity 提案确定性兜底(就地修改,best-effort 不阻塞提案)。

        Oracle 多 schema 表名 owner 补全 + 时间列 role=time——LLM 提案的
        系统性缺陷(见 propose.normalize_entity_binding)。
        """
        if obj_type != "entity":
            return
        try:
            from .propose import normalize_entity_binding

            ds_id = (payload.get("binding") or {}).get("datasource_id")
            specs = None
            if ds_id:
                from gyra_serve.datasource.manages.table_spec_db import TableSpecDao

                specs = TableSpecDao().get_all_by_datasource(ds_id) or []
            normalize_entity_binding(payload, specs)
        except Exception:  # noqa: BLE001 兜底失败不阻塞提案(契约校验仍生效)
            pass

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
                        provenance=make_provenance(
                            ORIGIN_MANUAL_SQL,
                            actor=f"user:{user_id}",
                            origin_sql=[sql],
                            note=description,
                            derived_from=f"sql_proposal:{pid}",
                        ),
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
            "duplicate_existing": [],
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
                provenance=carry_provenance(
                    getattr(target, "provenance", None), f"edit_of:{object_id}@v{version}"
                ),
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
                    provenance=carry_provenance(
                        getattr(proposed, "provenance", None), f"normalize_of:{object_id}@v{version}"
                    ),
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
            "deprecate",
            ws,
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
                provenance=carry_provenance(
                    getattr(vo, "provenance", None), "admin:normalize_confirmed"
                ),
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

    # -------------------------------------------------------------------- reads
    def inbox(
        self,
        workspace_id: Optional[str] = None,
        obj_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        include_view: bool = False,
    ) -> SemanticObjectListVO:
        """Confirmation inbox: latest proposed versions."""
        result = self._object_dao.list_latest(
            workspace_id=self._ws(workspace_id),
            obj_type=obj_type,
            status=STATUS_PROPOSED,
            page=page,
            page_size=page_size,
        )
        return self._attach_views(result, "brief") if include_view else result

    def list_objects(
        self,
        workspace_id: Optional[str] = None,
        obj_type: Optional[str] = None,
        status: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        include_view: bool = False,
    ) -> SemanticObjectListVO:
        result = self._object_dao.list_latest(
            workspace_id=self._ws(workspace_id),
            obj_type=obj_type,
            status=status,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )
        return self._attach_views(result, "brief") if include_view else result

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

    # ------------------------------------------------------- proposal view(业务视图)
    @staticmethod
    def _ds_name_resolver():
        """datasource_id → 数据源名(带请求级缓存;基础设施不可用降级 None)。"""
        cache: Dict[Any, Optional[str]] = {}

        def resolve(ds_id: Any) -> Optional[str]:
            if ds_id not in cache:
                name = None
                try:
                    from gyra_serve.datasource.manages.connect_config_db import (
                        ConnectConfigDao,
                    )

                    cfg = ConnectConfigDao().get_one({"id": ds_id})
                    name = getattr(cfg, "db_name", None) or getattr(cfg, "name", None)
                except Exception:  # noqa: BLE001
                    name = None
                cache[ds_id] = name
            return cache[ds_id]

        return resolve

    def _attach_views(
        self, list_vo: SemanticObjectListVO, level: str = "brief"
    ) -> SemanticObjectListVO:
        """为列表各项挂业务视图(读时派生;单项失败不阻塞列表)。"""
        from .proposal_view import build_proposal_view

        resolver = self._ds_name_resolver()
        for item in list_vo.items or []:
            try:
                item.view = build_proposal_view(
                    item,
                    objects=self._object_dao,
                    ds_name_resolver=resolver,
                    level=level,
                )
            except Exception:  # noqa: BLE001
                logger.debug("build view failed for %s", item.id, exc_info=True)
        return list_vo

    def get_proposal_view(
        self, object_id: str, version: int, workspace_id: Optional[str] = None
    ):
        """单个对象版本的完整业务视图(含静态 SQL 预览),详情页数据源。"""
        from .proposal_view import build_proposal_view

        ws = self._ws(workspace_id)
        vo = self._object_dao.get_version(object_id, version, ws)
        if not vo:
            raise ValueError(f"Object {object_id}@v{version} not found")
        return build_proposal_view(
            vo,
            objects=self._object_dao,
            ds_name_resolver=self._ds_name_resolver(),
            level="full",
        )

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
        resolved: List[ConfirmerVO] = []
        for v in vos:
            try:
                user_name = names.get(int(v.user_id))
            except (TypeError, ValueError):
                user_name = None
            resolved.append(
                ConfirmerVO(
                    id=v.id,
                    workspace_id=v.workspace_id,
                    user_id=v.user_id,
                    scope=v.scope,
                    user_name=user_name,
                )
            )
        return resolved

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

    # ====================================== 领域协作者委托(门面 API 保持不变)
    # ------------------------------------------------------- admin(miss 飞轮)
    def miss_report(
        self,
        workspace_id: Optional[str] = None,
        limit: int = 20,
        scan_size: int = 500,
    ) -> dict:
        return self._miss.report(workspace_id, limit, scan_size)

    def _learned_cluster_keys(self, workspace_id: str) -> set:
        return self._miss.learned_cluster_keys(workspace_id)

    def miss_detail(
        self,
        kind: str,
        pattern: str,
        datasource_id: Optional[int] = None,
        workspace_id: Optional[str] = None,
        scan_size: int = 500,
    ):
        return self._miss.detail(kind, pattern, datasource_id, workspace_id, scan_size)

    def mark_miss_learned(
        self,
        clusters: List[dict],
        workspace_id: Optional[str] = None,
        proposal_ids: Optional[List[str]] = None,
        trigger: str = "agent",
    ) -> List[MissLearnVO]:
        return self._miss.mark_learned(clusters, workspace_id, proposal_ids, trigger)

    def list_miss_learned(
        self, workspace_id: Optional[str] = None, kind: Optional[str] = None
    ) -> List[MissLearnVO]:
        return self._miss.list_learned(workspace_id, kind)

    def clear_miss_learned(
        self,
        workspace_id: Optional[str] = None,
        kind: Optional[str] = None,
        pattern: Optional[str] = None,
        datasource_id: Optional[int] = None,
    ) -> int:
        return self._miss.clear_learned(workspace_id, kind, pattern, datasource_id)

    @staticmethod
    def build_miss_context(clusters: List[dict], max_items: int = 10) -> str:
        """把 miss 聚类构建成提案 agent 的领域上下文(问题驱动的提案素材)。"""
        return MissFlywheel.build_context(clusters, max_items)

    # -------------------------------------------------------------------- graph
    def _refresh_edges(self, vo: SemanticObjectVO, ws: str) -> None:
        self._graph.refresh_edges(vo, ws)

    def rebuild_edges(self, workspace_id: Optional[str] = None) -> dict:
        return self._graph.rebuild_edges(workspace_id)

    async def _knowledge_subgraph(self, ws, registered, referenced, alignment_index=None):
        return await self._graph.knowledge_subgraph(
            ws, registered, referenced, alignment_index
        )

    async def graph(
        self, workspace_id: Optional[str] = None, entity: Optional[str] = None
    ) -> GraphVO:
        return await self._graph.graph(workspace_id, entity)

    @staticmethod
    def _graph_focus(
        vo: GraphVO, entity: str, semantic_index: Dict[str, List[str]]
    ) -> GraphVO:
        return GraphOps.focus(vo, entity, semantic_index)

    # ------------------------------------------------- semantic alignment
    async def _entity_graph_context(self, slug_entities):
        from .knowledge_bridge import entity_graph_context

        return await entity_graph_context(self, slug_entities)

    async def _kn_entity_names(self, ws: str):
        from .knowledge_bridge import kn_entity_names

        return await kn_entity_names(self, ws)

    async def align_entities(
        self, workspace_id: Optional[str] = None, user_id: Optional[str] = None
    ) -> dict:
        return await self._alignment.run(workspace_id, user_id)

    def list_alignments(
        self, workspace_id: Optional[str] = None, status: Optional[str] = None
    ) -> List[SemanticAlignmentVO]:
        return self._alignment.list(workspace_id, status)

    def confirm_alignment(
        self, alignment_id: int, user_id: Optional[str] = None
    ) -> SemanticAlignmentVO:
        return self._alignment.confirm(alignment_id, user_id)

    def reject_alignment(
        self, alignment_id: int, user_id: Optional[str] = None
    ) -> SemanticAlignmentVO:
        return self._alignment.reject(alignment_id, user_id)

    async def add_alignment(
        self,
        workspace_id: Optional[str] = None,
        entity_name: str = "",
        object_id: str = "",
        user_id: Optional[str] = None,
    ) -> SemanticAlignmentVO:
        return await self._alignment.add_manual(
            workspace_id, entity_name, object_id, user_id
        )

    def remove_alignment(self, alignment_id: int) -> bool:
        return self._alignment.remove(alignment_id)

    # -------------------------------------------------------------- asset refs
    def register_asset(
        self,
        kind: str,
        ref_id: str,
        workspace_id: Optional[str] = None,
        ref_meta: Optional[dict] = None,
    ) -> AssetRefVO:
        return self._assets.register(kind, ref_id, workspace_id, ref_meta)

    def list_assets(
        self, workspace_id: Optional[str] = None, kind: Optional[str] = None
    ) -> List[AssetRefVO]:
        return self._assets.list(workspace_id, kind)

    def remove_asset(
        self,
        asset_id: int,
        workspace_id: Optional[str] = None,
    ) -> bool:
        return self._assets.remove(asset_id, workspace_id)

    def readiness(
        self, datasource_id: int, workspace_id: Optional[str] = None
    ) -> ReadinessVO:
        return self._assets.readiness(datasource_id, workspace_id)

    # ------------------------------------------------------------- ECP space
    async def get_or_create_space(
        self, workspace_id: Optional[str] = None, owner_id: Optional[str] = None
    ) -> SpaceInfoVO:
        return await self._workspace.get_or_create_space(workspace_id, owner_id)

    def _ensure_default_proposal_agent(self, workspace_id: str) -> None:
        self._workspace.ensure_default_proposal_agent(workspace_id)

    # ------------------------------------------------------ workspace config
    def get_workspace_config(
        self, workspace_id: Optional[str] = None
    ) -> WorkspaceConfigVO:
        return self._workspace.get_config(workspace_id)

    def save_workspace_config(
        self,
        workspace_id: Optional[str] = None,
        proposal_agent_id: Optional[str] = None,
    ) -> WorkspaceConfigVO:
        return self._workspace.save_config(workspace_id, proposal_agent_id)

    # -------------------------------------------------- 资产迁移(导出 / 导入)
    @staticmethod
    def _object_to_export_dict(vo: SemanticObjectVO) -> Dict[str, Any]:
        return TransferOps.object_to_export_dict(vo)

    @staticmethod
    def _asset_to_export_dict(vo: AssetRefVO) -> Dict[str, Any]:
        return TransferOps.asset_to_export_dict(vo)

    def export_workspace(self, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        return self._transfer.export_workspace(workspace_id)

    def import_workspace(
        self,
        data: Dict[str, Any],
        workspace_id: Optional[str] = None,
        datasource_map: Optional[Dict[str, Any]] = None,
        user_id: str = "system",
    ) -> Dict[str, Any]:
        return self._transfer.import_workspace(
            data, workspace_id, datasource_map, user_id
        )
