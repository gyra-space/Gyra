"""Database 资源目录 Provider：向 RBAC 提供数据源和表的可选列表。

支持两级级联：
- 第一级：数据源列表（resource_id = "{ds_id}"）
- 第二级：表列表（resource_id = "{ds_id}.{table_name}"，parent_id = "{ds_id}"）
"""

import logging
from typing import List, Optional

from gyra_serve.permissions.protocol import ResourceCatalogItem, ResourceCatalogProvider

logger = logging.getLogger(__name__)


class DatabaseCatalogProvider(ResourceCatalogProvider):
    """数据库资源目录。"""

    def resource_type(self) -> str:
        return "database"

    def supports_hierarchy(self) -> bool:
        return True

    def list_items(
        self,
        parent_id: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 100,
    ) -> List[ResourceCatalogItem]:
        if parent_id is None:
            return self._list_datasources(keyword, limit)
        if "." in parent_id:
            # parent_id = "{ds_id}.{table}" → 列级
            return self._list_columns(parent_id, keyword, limit)
        return self._list_tables(parent_id, keyword, limit)

    def _list_columns(
        self, table_rid: str, keyword: Optional[str], limit: int
    ) -> List[ResourceCatalogItem]:
        """列出指定表下的列(parent_id 格式 "{ds_id}.{table}")。

        列元数据来自 table spec(库表学习产物);未学习的表返回空,
        前端展开时显示无数据,不实时连库探测。
        """
        ds_part, _, table_name = table_rid.partition(".")
        try:
            ds_id_int = int(ds_part)
        except (TypeError, ValueError):
            return []
        if not table_name:
            return []

        try:
            from gyra_serve.datasource.service.spec_service import DbSpecService

            spec = DbSpecService().get_table_spec(ds_id_int, table_name)
            if not spec:
                return []

            items = []
            for col in spec.get("columns") or []:
                col_name = col.get("name", "")
                if not col_name:
                    continue
                if keyword and keyword.lower() not in col_name.lower():
                    continue
                comment = col.get("comment") or col.get("type") or col.get("data_type") or ""
                items.append(
                    ResourceCatalogItem(
                        id=f"{table_rid}.{col_name}",
                        name=col_name,
                        parent_id=table_rid,
                        description=comment[:100] if comment else None,
                        metadata={
                            "data_type": col.get("type") or col.get("data_type"),
                        },
                    )
                )
                if len(items) >= limit:
                    break
            return items
        except Exception as e:
            logger.debug(f"[DatabaseCatalogProvider] list columns failed: {e}")
            return []

    def _list_datasources(
        self, keyword: Optional[str], limit: int
    ) -> List[ResourceCatalogItem]:
        """列出所有数据源。"""
        try:
            from gyra_serve.datasource.manages.connect_config_db import ConnectConfigDao

            dao = ConnectConfigDao()
            session = dao.get_raw_session()
            try:
                from gyra_serve.datasource.manages.connect_config_db import ConnectConfigEntity

                q = session.query(ConnectConfigEntity)
                if keyword:
                    q = q.filter(ConnectConfigEntity.db_name.contains(keyword))
                entities = q.limit(limit).all()
            finally:
                session.close()

            items = []
            for e in entities:
                ds_id = str(e.id)
                db_name = e.db_name or f"datasource-{e.id}"
                items.append(
                    ResourceCatalogItem(
                        id=ds_id,
                        name=db_name,
                        parent_id=None,
                        description=f"{e.db_type} | {getattr(e, 'comment', '') or ''}".strip(" |"),
                        metadata={
                            "db_type": e.db_type,
                            "db_name": e.db_name,
                            "owner_workspace_id": getattr(e, "owner_workspace_id", None),
                        },
                    )
                )
            return items
        except Exception as e:
            logger.warning(f"[DatabaseCatalogProvider] list datasources failed: {e}")
            return []

    def _list_tables(
        self, ds_id: str, keyword: Optional[str], limit: int
    ) -> List[ResourceCatalogItem]:
        """列出指定数据源下的表。"""
        try:
            ds_id_int = int(ds_id)
        except (TypeError, ValueError):
            return []

        # 优先从 spec service 获取（带注释/分组等元数据）
        items = self._list_tables_from_spec(ds_id_int, ds_id, keyword, limit)
        if items:
            return items

        # 兜底：从 connector 实时拉取
        return self._list_tables_from_connector(ds_id_int, ds_id, keyword, limit)

    def _list_tables_from_spec(
        self, ds_id_int: int, ds_id: str, keyword: Optional[str], limit: int
    ) -> List[ResourceCatalogItem]:
        """从 DbSpecService 获取表列表。"""
        try:
            from gyra_serve.datasource.service.spec_service import DbSpecService

            spec_service = DbSpecService()
            if not spec_service.has_spec(ds_id_int):
                return []

            specs = spec_service.get_all_table_specs(ds_id_int)
            items = []
            for spec in specs:
                table_name = spec.get("table_name", "")
                if not table_name:
                    continue
                if keyword and keyword.lower() not in table_name.lower():
                    continue
                comment = spec.get("table_comment", "") or spec.get("comment", "")
                items.append(
                    ResourceCatalogItem(
                        id=f"{ds_id}.{table_name}",
                        name=table_name,
                        parent_id=ds_id,
                        description=comment[:100] if comment else None,
                        metadata={
                            "group": spec.get("group_name") or spec.get("group", ""),
                            "row_count": spec.get("row_count"),
                            "latest_data_time": spec.get("latest_data_time"),
                        },
                    )
                )
                if len(items) >= limit:
                    break
            return items
        except Exception as e:
            logger.debug(f"[DatabaseCatalogProvider] spec list failed: {e}")
            return []

    def _list_tables_from_connector(
        self, ds_id_int: int, ds_id: str, keyword: Optional[str], limit: int
    ) -> List[ResourceCatalogItem]:
        """从 connector 实时拉取表列表（无 spec 时的兜底）。"""
        try:
            from gyra._private.config import Config
            from gyra_serve.datasource.manages.connect_config_db import ConnectConfigDao

            entity = ConnectConfigDao().get_one({"id": ds_id_int})
            if not entity:
                return []

            CFG = Config()
            connector = CFG.local_db_manager.get_connector(entity.db_name)
            if not connector:
                return []

            tables = connector.get_table_names() or []
            items = []
            for t in tables:
                if keyword and keyword.lower() not in t.lower():
                    continue
                items.append(
                    ResourceCatalogItem(
                        id=f"{ds_id}.{t}",
                        name=t,
                        parent_id=ds_id,
                    )
                )
                if len(items) >= limit:
                    break
            return items
        except Exception as e:
            logger.debug(f"[DatabaseCatalogProvider] connector list failed: {e}")
            return []
