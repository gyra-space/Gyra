"""ECP 资产引用注册与就绪检查。

ECP 不拥有任何原始资产(datasource/knowledge 各自持有),这里只登记
"本 workspace 的 ECP 关注哪些原资产"(ecp_asset_ref),作为 readiness
检查、Lint 漂移监控、证据溯源的统一锚点。

AssetOps 是无状态协作者,经 svc 门面访问 DAO。
"""

import logging
from typing import Any, List, Optional

from ..api.schemas import AssetRefVO, ReadinessCheckVO, ReadinessVO

logger = logging.getLogger(__name__)


class AssetOps:
    """资产注册协作者(无状态;经 svc 门面访问 DAO)。"""

    def __init__(self, svc: Any):
        self._svc = svc

    def register(
        self,
        kind: str,
        ref_id: str,
        workspace_id: Optional[str] = None,
        ref_meta: Optional[dict] = None,
    ) -> AssetRefVO:
        svc = self._svc
        ws = svc._ws(workspace_id)
        vo = svc._asset_dao.register(kind, ref_id, ws, ref_meta)
        svc._oplog_dao.append(
            "asset_register", ws, {"kind": kind, "ref_id": ref_id}
        )
        return vo

    def list(
        self, workspace_id: Optional[str] = None, kind: Optional[str] = None
    ) -> List[AssetRefVO]:
        svc = self._svc
        return svc._asset_dao.list(svc._ws(workspace_id), kind)

    def remove(
        self,
        asset_id: int,
        workspace_id: Optional[str] = None,
    ) -> bool:
        """Unregister an asset reference from a workspace.

        ECP owns only the reference, so this does NOT touch the original
        asset (DB / space / document). Used by the ECP asset list "delete"
        action. Returns True if a row was removed.
        """
        svc = self._svc
        ws = svc._ws(workspace_id)
        removed = svc._asset_dao.delete_in_workspace(asset_id, ws)
        if removed is None:
            return False
        svc._oplog_dao.append(
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

        svc = self._svc
        ws = svc._ws(workspace_id)
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
        doc_refs = [a for a in svc._asset_dao.list(ws) if a.kind in ("document", "space")]
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
