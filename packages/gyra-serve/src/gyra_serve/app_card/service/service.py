"""AppCard service — stores cards and dispatches the unified `invoke` protocol.

A card is an agent-generated artifact. The runtime NEVER re-invokes the agent:
the frontend sandbox calls `invoke(op, params)` and this service dispatches to a
whitelisted capability (query.metric / query.sql / assets.get / preview.*).
Each capability is a deterministic executor; data access is reused from the ECP
semantic layer (metric) and the workspace data sources (sql), keeping the same
「生成期 dry-run → 运行期冻结取数」契约 as the agent itself.
"""

import json
import logging
import secrets
from typing import Any, Callable, Dict, List, Optional

from gyra.component import SystemApp
from gyra_serve.core import BaseService
from gyra_serve.utils.auth import UserRequest

from ..api.schemas import (
    AppCardCreateRequest, AppCardInvokeRequest, AppCardListFilter,
    AppCardResponse, AppCardUpdateRequest, AppCardValidateResponse,
    AppCardValidateResult,
)
from ..models.models import (
    AppCardDao, AppCardEntity, AppCardVersionEntity, _dump_json, _load_json,
)

logger = logging.getLogger(__name__)

APP_CARD_SERVICE_COMPONENT_NAME = "serve_app_card_service"

# 只读 SQL 首关键字白名单(与 ECP execute_raw_sql 一致),作为 query.sql 的防线
_READONLY_KEYWORDS = {"SELECT", "WITH", "SHOW", "DESC", "DESCRIBE", "EXPLAIN"}


# --------------------------------------------------------------------------- #
# 只读 SQL 执行(带绑定参数, 替代 connector.run 的裸文本拼接)
# --------------------------------------------------------------------------- #
def _strip_sql_comments(sql: str) -> str:
    import re
    sql = re.sub(r"--.*?(\n|$)", "\n", sql)
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return sql


def _first_keyword(sql: str) -> str:
    stripped = _strip_sql_comments(sql.strip())
    tokens = [t for t in stripped.split() if t]
    return tokens[0].upper() if tokens else ""


def _is_readonly_sql(sql: str) -> bool:
    if not sql or not sql.strip():
        return False
    return _first_keyword(sql) in _READONLY_KEYWORDS


def run_readonly_sql(
    datasource_id: int,
    sql: str,
    bind_params: Optional[Dict[str, Any]] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """执行一条只读 SQL, 参数走绑定(防注入), 返回 {trust:inferred, columns, rows, ...}."""
    from sqlalchemy import text

    from gyra._private.config import Config
    from gyra_serve.datasource.manages.connect_config_db import ConnectConfigDao

    if not _is_readonly_sql(sql):
        return {"trust": "none", "error": "仅允许只读查询(SELECT/WITH/SHOW/DESC/EXPLAIN)",
                "columns": [], "rows": [], "row_count": 0, "sql": sql}

    config = ConnectConfigDao().get_one({"id": datasource_id})
    db_name = None
    if config is not None:
        if isinstance(config, dict):
            db_name = config.get("db_name")
        else:
            db_name = getattr(config, "db_name", None)
    if not db_name:
        return {"trust": "none", "error": f"数据源 {datasource_id} 不存在",
                "columns": [], "rows": [], "row_count": 0, "sql": sql}

    connector = Config().local_db_manager.get_connector(db_name)
    bind_params = bind_params or {}
    try:
        with connector.session_scope(commit=False) as session:
            result = session.execute(text(sql), bind_params)
            columns = list(result.keys())
            rows = [dict(zip(columns, r)) for r in result.fetchall()]
    except Exception as e:  # noqa: BLE001
        logger.exception("app_card sql execute failed")
        return {"trust": "none", "error": str(e), "columns": [], "rows": [], "row_count": 0, "sql": sql}

    if limit is not None:
        rows = rows[:limit]
    return {"trust": "inferred", "warnings": ["未验证口径: 此结果未经语义层确认"],
            "columns": columns, "rows": rows, "row_count": len(rows), "sql": sql}


# --------------------------------------------------------------------------- #
# Capability 引擎
# --------------------------------------------------------------------------- #
def _find_query(queries: List[Dict[str, Any]], query_key: Optional[str]) -> Optional[Dict[str, Any]]:
    if not query_key:
        return None
    for q in queries:
        if q.get("key") == query_key:
            return q
    return None


class AppCardService(BaseService[AppCardEntity, AppCardCreateRequest, AppCardResponse]):
    name = APP_CARD_SERVICE_COMPONENT_NAME

    def __init__(self, system_app: SystemApp, config, dao: Optional[AppCardDao] = None):
        self._system_app = None
        self._serve_config = config
        self._dao: AppCardDao = dao or AppCardDao()
        super().__init__(system_app)

    def init_app(self, system_app: SystemApp) -> None:
        super().init_app(system_app)
        self._system_app = system_app
        self._dao = self._dao or AppCardDao()

    @property
    def dao(self) -> AppCardDao:
        return self._dao

    @property
    def config(self):
        return self._serve_config

    # ---------------------------------------------------- 卡片级权限判定
    @staticmethod
    def _user_identifiers(user: UserRequest) -> List[str]:
        """当前用户的标识字符串集合(用于与 created_by 比对开发者)。"""
        ids = []
        for k in ("user_id", "user_no", "user_name"):
            v = getattr(user, k, None)
            if v is not None:
                ids.append(str(v))
        return list(dict.fromkeys(ids))

    @staticmethod
    def _is_privileged(user: UserRequest) -> bool:
        """平台/空间管理员(可查看并维护空间内所有应用卡片)。"""
        if getattr(user, "role", None) == "admin":
            return True
        return any(r in ("admin", "superadmin") for r in (user.roles or []))

    @staticmethod
    def _card_permissions(card) -> List[str]:
        """统一读取卡片权限列表(兼容 entity.permissions_json 与 response.permissions)。"""
        perms = getattr(card, "permissions", None)
        if perms is None:
            raw = getattr(card, "permissions_json", None)
            if isinstance(raw, str):
                try:
                    perms = json.loads(raw) or []
                except Exception:
                    perms = []
            else:
                perms = raw or []
        return list(perms or [])

    def is_developer(self, user: UserRequest, card) -> bool:
        created_by = getattr(card, "created_by", None)
        if not created_by:
            return False
        return created_by in self._user_identifiers(user)

    def can_view(self, user: UserRequest, card) -> bool:
        """判断当前用户可否查看该卡片。

        - 管理员: 全部可见
        - 开发者本人: 始终可见
        - 显式授权(permissions 非空): all→所有人; member→空间成员(能进空间即可);
          无授权(默认)→仅开发者
        """
        if self._is_privileged(user) or self.is_developer(user, card):
            return True
        perms = self._card_permissions(card)
        if not perms:
            return False
        return "all" in perms or "member" in perms

    def can_manage(self, user: UserRequest, card) -> bool:
        """判断当前用户可否维护(改/删)该卡片。

        管理员或开发者本人可维护; 显式授权 owner/admin 的卡片其可见用户同样可维护。
        """
        if self._is_privileged(user) or self.is_developer(user, card):
            return True
        perms = self._card_permissions(card)
        return "owner" in perms or "admin" in perms

    def _decorate_perms(self, resp: AppCardResponse, user: UserRequest) -> AppCardResponse:
        resp.is_owner = self.is_developer(user, resp)
        resp.can_manage = self.can_manage(user, resp)
        return resp

    # ------------------------------------------------------------ 分享配置
    @staticmethod
    def _share_conf(config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """读取卡片配置中的分享项。config.share = {"mode": login|anonymous, "token": ...}"""
        conf = config or {}
        share = conf.get("share")
        if not isinstance(share, dict):
            share = {}
        mode = share.get("mode")
        if mode not in ("anonymous", "login"):
            mode = "login"
        return {"mode": mode, "token": share.get("token")}

    def _decorate_share(self, resp: AppCardResponse) -> AppCardResponse:
        """把 config.share 回填到响应字段。分享令牌仅维护者可读(can_manage)。"""
        share = self._share_conf(resp.config)
        resp.share_mode = share["mode"]
        resp.share_token = share["token"] if resp.can_manage else None
        return resp

    def _anon_ok(self, entity, token: Optional[str]) -> bool:
        """匿名分享校验: 卡片开启 anonymous 且令牌一致(恒定时间比较)。"""
        if not token:
            return False
        share = self._share_conf(getattr(entity, "config", None))
        if share["mode"] != "anonymous" or not share["token"]:
            return False
        return secrets.compare_digest(str(share["token"]), str(token))

    # ------------------------------------------------------------------ CRUD
    def create(self, request: AppCardCreateRequest) -> AppCardResponse:
        validate_result = self.validate_queries(request.workspace_id, request.queries) if request.dry_run else None
        entity = self.dao.from_request(request)
        entity.status = "validated" if (validate_result and validate_result.ok) else "draft"
        session = self.dao.get_raw_session()
        try:
            session.add(entity)
            session.flush()
            self._snapshot_version(session, entity, 1, request.created_by or "agent")
            session.commit()
            # 在 session 关闭前物化响应:commit 后(expire_on_commit=True)实体已过期,
            # 若在 close 之后再访问属性会触发 detached 实体刷新报错
            resp = self.dao.to_response(entity)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
        return self._decorate_share(resp)

    def update(self, request: AppCardUpdateRequest, user: UserRequest) -> Optional[AppCardResponse]:
        session = self.dao.get_raw_session()
        try:
            entity = session.query(AppCardEntity).filter(AppCardEntity.id == request.id).first()
            if not entity:
                return None
            if not self.can_manage(user, entity):
                raise PermissionError("无权维护该应用卡片(仅开发者或管理员/被授权者)")
            if request.name is not None:
                entity.name = request.name
            if request.description is not None:
                entity.description = request.description
            if request.kind is not None:
                entity.kind = request.kind
            if request.code is not None:
                entity.code = request.code
            if request.config is not None:
                entity.config_json = _dump_json(request.config)
            if request.queries is not None:
                entity.queries_json = _dump_json(request.queries)
            if request.icon is not None:
                entity.icon = request.icon
            if request.permissions is not None:
                entity.permissions_json = _dump_json(request.permissions)
            # 分享设置: 写入 config.share(mode + token)。anonymous 且无 token(或要求重置)时生成新令牌
            if request.share_mode is not None:
                conf = _load_json(entity.config_json) or {}
                share = self._share_conf(conf)
                mode = request.share_mode if request.share_mode in ("anonymous", "login") else share["mode"]
                token = share["token"]
                if mode == "anonymous":
                    if not token or request.share_token_refresh:
                        token = secrets.token_urlsafe(32)
                else:
                    token = None
                conf["share"] = {"mode": mode, "token": token}
                entity.config_json = _dump_json(conf)
            entity.current_version = (entity.current_version or 1) + 1
            self._snapshot_version(session, entity, entity.current_version, request.created_by or "agent")
            session.commit()
            # 同 create:commit 后实体会过期,必须在 session 仍打开时物化响应
            resp = self.dao.to_response(entity)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
        resp = self._decorate_perms(resp, user)
        return self._decorate_share(resp)

    def get_by_id(self, card_id: int, user: UserRequest) -> Optional[AppCardResponse]:
        resp = self.dao.get_one({"id": card_id})
        if not resp:
            return None
        if not self.can_view(user, resp):
            return None
        resp = self._decorate_perms(resp, user)
        return self._decorate_share(resp)

    def delete(self, card_id: int, workspace_id: int, user: UserRequest) -> bool:
        session = self.dao.get_raw_session()
        try:
            entity = (
                session.query(AppCardEntity)
                .filter(AppCardEntity.id == card_id,
                        AppCardEntity.workspace_id == workspace_id)
                .first()
            )
            if not entity:
                return False
            if not self.can_manage(user, entity):
                raise PermissionError("无权删除该应用卡片(仅开发者或管理员/被授权者)")
            session.delete(entity)
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_by_workspace(self, f: AppCardListFilter, user: UserRequest) -> List[AppCardResponse]:
        visible = []
        for resp in self.dao.list_by_workspace(f):
            if self.can_view(user, resp):
                resp = self._decorate_perms(resp, user)
                visible.append(self._decorate_share(resp))
        return visible

    def _snapshot_version(self, session, entity: AppCardEntity, version: int, created_by: str) -> None:
        session.add(AppCardVersionEntity(
            app_card_id=entity.id, version=version, code=entity.code,
            config_json=entity.config_json, queries_json=entity.queries_json,
            created_by=created_by,
        ))

    # ---------------------------------------------------------- invoke 协议
    def invoke(self, card_id: int, workspace_id: int, req: AppCardInvokeRequest, user: UserRequest) -> Dict[str, Any]:
        entity = self.dao.get_one({"id": card_id})
        if not entity:
            return {"trust": "none", "error": f"app_card {card_id} not found"}
        if entity.workspace_id != workspace_id:
            return {"trust": "none", "error": "workspace mismatch"}
        if not self.can_view(user, entity):
            return {"trust": "none", "error": "无权访问该应用卡片"}
        return self._dispatch(entity, workspace_id, entity.queries, req)

    def _dispatch(self, entity, workspace_id, queries, req: AppCardInvokeRequest) -> Dict[str, Any]:
        # queries: get_one 返回 AppCardResponse(已解析); 程序化取数尽量用已声明的查询契约
        queries = list(queries or [])
        dispatch: Dict[str, Callable] = {
            "query.metric": self._invoke_metric,
            "query.sql": self._invoke_sql,
            "assets.get": self._invoke_assets,
            "metric.preview": self._invoke_metric,
            "sql.preview": self._invoke_sql,
        }
        handler = dispatch.get(req.op)
        if handler is None:
            return {"trust": "none", "error": f"不支持的能力 {req.op}"}
        return handler(entity, workspace_id, queries, req.params or {}, req.query_key)

    # ------------------------------------------------------ 匿名公开分享
    def get_render_anonymous(self, card_id: int, token: Optional[str]) -> Optional[Dict[str, Any]]:
        """匿名模式取渲染信息(不含分享令牌), 供未登录用户加载子应用。"""
        entity = self.dao.get_one({"id": card_id})
        if not entity or not self._anon_ok(entity, token):
            return None
        conf = dict(entity.config or {})
        conf["share"] = {"mode": "anonymous"}  # 不暴露 token
        return {
            "id": entity.id,
            "workspace_id": entity.workspace_id,
            "name": entity.name,
            "icon": entity.icon,
            "kind": entity.kind,
            "code": entity.code,
            "config": conf,
            "queries": list(entity.queries or []),
        }

    def get_render_share_login(self, card_id: int, user: UserRequest) -> Optional[Dict[str, Any]]:
        """登录分享取渲染信息: 已登录且可查看即返回, 但剥离一切维护能力字段(只读)。"""
        resp = self.get_by_id(card_id, user)
        if resp is None:
            return None
        resp.is_owner = False
        resp.can_manage = False
        resp.share_token = None
        return resp

    def invoke_anonymous(self, card_id: int, token: Optional[str], req: AppCardInvokeRequest) -> Dict[str, Any]:
        """匿名模式取数: 校验令牌后走统一 dispatch, 不受登录/can_view 约束。"""
        entity = self.dao.get_one({"id": card_id})
        if not entity:
            return {"trust": "none", "error": f"app_card {card_id} not found"}
        if not self._anon_ok(entity, token):
            return {"trust": "none", "error": "无效的分享令牌或未开启匿名分享"}
        return self._dispatch(entity, entity.workspace_id, entity.queries, req)

    def invoke_login(self, card_id: int, req: AppCardInvokeRequest, user: UserRequest) -> Dict[str, Any]:
        """登录分享取数: 复用 invoke 的校验(登录 + 卡片查看权限), workspace 取自卡片本身。"""
        entity = self.dao.get_one({"id": card_id})
        if not entity:
            return {"trust": "none", "error": f"app_card {card_id} not found"}
        if not self.can_view(user, entity):
            return {"trust": "none", "error": "无权访问该应用卡片"}
        return self._dispatch(entity, entity.workspace_id, entity.queries, req)

    def _invoke_metric(self, entity, workspace_id, queries, params, query_key) -> Dict[str, Any]:
        from gyra_serve.ecp.service.executor import GateError, execute_metric_query

        metric_id = params.get("metric_id")
        q = _find_query(queries, query_key)
        if q and q.get("kind") == "metric":
            metric_id = metric_id or q.get("metric_id")
        if not metric_id:
            return {"trust": "none", "error": "缺少 metric_id"}
        try:
            return execute_metric_query(
                metric_id=metric_id,
                workspace_id=str(workspace_id),
                group_by=params.get("group_by"),
                filters=params.get("filters"),
                time_range=params.get("time_range"),
            )
        except GateError as e:
            return {"trust": "none", "error": str(e), "code": getattr(e, "code", "GATE_REJECTED")}

    def _invoke_sql(self, entity, workspace_id, queries, params, query_key) -> Dict[str, Any]:
        q = _find_query(queries, query_key)
        sql = params.get("sql")
        datasource_id = params.get("datasource_id")
        bind_params = params.get("bind_params") or {}
        if q and q.get("kind") == "sql":
            sql = sql or q.get("sql")
            datasource_id = datasource_id or q.get("datasource_id")
            bind_params = {**q.get("bind_params", {}), **bind_params}
        if not sql or not datasource_id:
            return {"trust": "none", "error": "缺少 sql 或 datasource_id"}
        limit = params.get("limit") if not q else q.get("limit")
        return run_readonly_sql(int(datasource_id), sql, bind_params, limit)

    def _invoke_assets(self, entity, workspace_id, queries, params, query_key) -> Dict[str, Any]:
        from gyra_serve.workspace_asset.api.schemas import AssetSearchRequest
        from gyra_serve.workspace_asset.service.service import (
            ASSET_SERVICE_COMPONENT_NAME, AssetService,
        )

        asset_service = self._system_app.get_component(ASSET_SERVICE_COMPONENT_NAME, AssetService)
        req = AssetSearchRequest(
            workspace_id=workspace_id,
            query=params.get("query"),
            type=params.get("type"),
            tags=params.get("tags"),
            limit=int(params.get("limit", 10)),
        )
        try:
            items = asset_service.search(req)
            return {"trust": "inferred", "rows": [i.model_dump() for i in items], "row_count": len(items)}
        except Exception as e:  # noqa: BLE001
            logger.exception("app_card assets.get failed")
            return {"trust": "none", "error": str(e), "rows": [], "row_count": 0}

    # ------------------------------------------------------ 生成期 dry-run 校验
    def validate_queries(self, workspace_id: int, queries: List[Dict[str, Any]]) -> AppCardValidateResponse:
        from gyra_serve.ecp.service.executor import preview_query

        items: List[AppCardValidateResult] = []
        ok_all = True
        for q in queries or []:
            key = q.get("key", "")
            kind = q.get("kind")
            try:
                if kind == "metric":
                    trust = "preview"
                    preview = preview_query(
                        object_id=q.get("metric_id", ""),
                        version=int(q.get("version", 1)),
                        workspace_id=str(workspace_id),
                        group_by=q.get("group_by"),
                        filters=q.get("filters"),
                        time_range=q.get("time_range"),
                        limit=5,
                    )
                    if not preview.get("ok", False):
                        ok_all = False
                        trust = preview.get("trust", "none")
                    items.append(AppCardValidateResult(ok=bool(preview.get("ok")), item_key=key, kind=kind, trust=trust, error=preview.get("error")))
                elif kind == "sql":
                    res = run_readonly_sql(
                        int(q.get("datasource_id", 0)), q.get("sql", ""), q.get("bind_params"), limit=5,
                    )
                    ok = res.get("trust") != "none"
                    ok_all = ok_all and ok
                    items.append(AppCardValidateResult(ok=ok, item_key=key, kind=kind, trust=res.get("trust", "none"), error=res.get("error")))
                else:
                    items.append(AppCardValidateResult(ok=False, item_key=key, kind=kind or "unknown", trust="none", error="未知查询类型"))
                    ok_all = False
            except Exception as e:  # noqa: BLE001
                ok_all = False
                items.append(AppCardValidateResult(ok=False, item_key=key, kind=kind or "unknown", trust="none", error=str(e)))
        return AppCardValidateResponse(ok=ok_all, items=items)
