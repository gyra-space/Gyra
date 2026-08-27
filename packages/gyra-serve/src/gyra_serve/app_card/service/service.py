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
from typing import Any, Dict, List, Optional

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
from ..ops import register_app_card_op, resolve_app_card_op
from ..store.store_service import AppCardStoreService

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
        self._store_service: Optional[AppCardStoreService] = None
        super().__init__(system_app)

    def init_app(self, system_app: SystemApp) -> None:
        super().init_app(system_app)
        self._system_app = system_app
        self._dao = self._dao or AppCardDao()
        self._store_service = AppCardStoreService(system_app)

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

    @staticmethod
    def _show_in_launcher(card) -> bool:
        """是否在应用卡片启动条展示: 读 config.show_in_launcher, 缺省为 True。"""
        conf = getattr(card, "config", None) or {}
        if not isinstance(conf, dict):
            return True
        v = conf.get("show_in_launcher")
        return True if v is None else bool(v)

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
        resp.show_in_launcher = self._show_in_launcher(resp)
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
        session = self.dao.get_raw_session()
        try:
            existing = (
                session.query(AppCardEntity)
                .filter(
                    AppCardEntity.workspace_id == request.workspace_id,
                    AppCardEntity.name == request.name,
                    AppCardEntity.status != "archived",
                )
                .order_by(AppCardEntity.id.desc())
                .first()
            )
            if existing is not None:
                # 幂等更新: 同 workspace 下同名即视为同一卡片, 更新内容并快照新版本, 不产生重复记录
                if request.description is not None:
                    existing.description = request.description
                if request.kind is not None:
                    existing.kind = request.kind
                existing.code = request.code
                existing.config_json = _dump_json(request.config)
                existing.queries_json = _dump_json(request.queries)
                if request.icon is not None:
                    existing.icon = request.icon
                if request.permissions is not None:
                    existing.permissions_json = _dump_json(request.permissions)
                if request.source_task_id is not None:
                    existing.source_task_id = request.source_task_id
                if validate_result and validate_result.ok:
                    existing.status = "validated"
                existing.current_version = (existing.current_version or 1) + 1
                self._snapshot_version(session, existing, existing.current_version, request.created_by or "agent")
                session.commit()
                # 在 session 关闭前物化响应:commit 后(expire_on_commit=True)实体已过期,
                # 若在 close 之后再访问属性会触发 detached 实体刷新报错
                resp = self.dao.to_response(existing)
            else:
                entity = self.dao.from_request(request)
                entity.status = "validated" if (validate_result and validate_result.ok) else "draft"
                session.add(entity)
                session.flush()
                self._snapshot_version(session, entity, 1, request.created_by or "agent")
                session.commit()
                # 同上:commit 后实体已过期, 需在 session 仍打开时物化响应
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
            # 展示开关: 写入 config.show_in_launcher(False 隐藏启动条入口, 不删除应用)
            if request.show_in_launcher is not None:
                conf = _load_json(entity.config_json) or {}
                conf["show_in_launcher"] = bool(request.show_in_launcher)
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
                # 展示开关: 关闭的卡片对非维护者隐藏启动条入口(便于维护者随后重新开启);
                # 分享链接/直接取数不受影响。
                if not resp.show_in_launcher and not resp.can_manage:
                    continue
                visible.append(self._decorate_share(resp))
        return visible

    def _snapshot_version(self, session, entity: AppCardEntity, version: int, created_by: str) -> None:
        session.add(AppCardVersionEntity(
            app_card_id=entity.id, version=version, code=entity.code,
            config_json=entity.config_json, queries_json=entity.queries_json,
            created_by=created_by,
        ))

    # ---------------------------------------------------------- invoke 协议
    def preview_invoke(self, workspace_id: int, queries: List[Dict[str, Any]],
                       req: AppCardInvokeRequest) -> Dict[str, Any]:
        """开发期预览取数: 用「编辑器里(未落库)的查询契约」直接走运行期 dispatch。

        与运行期 invoke 走的同一派发(_invoke_*),使开发阶段「JSON 写完后先预览
        真实效果/取数」与最终运行完全一致;不要求卡片已落库。补 ``elapsed_ms``
        供 agent 在开发期评估查询性能。
        """
        import time as _time
        started = _time.perf_counter()
        entity = {"preview": True}  # _dispatch 的三个 handler 都不读 entity, 占位即可
        result = self._dispatch(entity, workspace_id, list(queries or []), req)
        if isinstance(result, dict):
            result.setdefault("row_count", len(result.get("rows") or []))
            result["elapsed_ms"] = int((_time.perf_counter() - started) * 1000)
        return result

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
        handler = resolve_app_card_op(req.op)
        if handler is None:
            return {"trust": "none", "error": f"不支持的能力 {req.op}"}
        return handler(self, entity, workspace_id, queries, req.params or {}, req.query_key)

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
    def _validate_one(self, workspace_id: int, queries: List[Dict[str, Any]], q: Dict[str, Any]) -> AppCardValidateResult:
        """对单个声明查询做「运行时同路径」校验。

        复用 _dispatch → _invoke_* 派发, 使开发期校验与运行期 invoke 完全一致:
        - sql: 走 _invoke_sql, 复现 query_key 解析 + bind 参数合并 + 只读白名单
        - metric: 走 _invoke_metric → execute_metric_query(与运行期相同, confirmed-only)
        - 同时复现查询体真正执行, 返回 trust / row_count。
        全部查询校验通过, 才说明「所有数据在运行期都能正常获取」。
        """
        key = q.get("key", "")
        kind = q.get("kind")
        if kind == "metric":
            req = AppCardInvokeRequest(
                op="query.metric", query_key=key,
                params={
                    "metric_id": q.get("metric_id", ""),
                    "group_by": q.get("group_by"),
                    "filters": q.get("filters"),
                    "time_range": q.get("time_range"),
                },
            )
        elif kind == "sql":
            req = AppCardInvokeRequest(
                op="query.sql", query_key=key,
                params={
                    "datasource_id": q.get("datasource_id"),
                    "sql": q.get("sql", ""),
                    "bind_params": q.get("bind_params") or {},
                },
            )
        else:
            return AppCardValidateResult(ok=False, item_key=key, kind=kind or "unknown", trust="none", error="未知查询类型")
        try:
            # _dispatch 的三个 handler(_invoke_*)都不读取 entity, 传 queries 占位即可
            res = self._dispatch(queries, workspace_id, queries, req)
        except Exception as e:  # noqa: BLE001
            logger.exception("app_card validate invoke failed")
            return AppCardValidateResult(ok=False, item_key=key, kind=kind or "unknown", trust="none", error=str(e))
        ok = res.get("trust") not in (None, "none")
        note = ""
        if ok and not res.get("row_count"):
            note = "取数成功但无返回行"
        return AppCardValidateResult(
            ok=ok, item_key=key, kind=kind or "unknown",
            trust=res.get("trust", "none"),
            error=(res.get("error") or note) or None,
        )

    def validate_queries(self, workspace_id: int, queries: List[Dict[str, Any]]) -> AppCardValidateResponse:
        items: List[AppCardValidateResult] = [self._validate_one(workspace_id, queries, q) for q in (queries or [])]
        return AppCardValidateResponse(ok=all(i.ok for i in items), items=items)


# --------------------------------------------------------------------------- #
# invoke 协议 op 注册(Option B: 各资源模块贡献自己的 op, 零改核心)
# --------------------------------------------------------------------------- #
def _entity_id(entity) -> Optional[int]:
    """读取卡片 id:兼容 entity 为对象或 dict(preview 占位 dict 无 id)。"""
    if isinstance(entity, dict):
        return entity.get("id")
    return getattr(entity, "id", None)


def _entity_config(entity) -> Dict[str, Any]:
    """读取卡片 config:兼容对象或 dict。"""
    raw = entity.get("config") if isinstance(entity, dict) else getattr(entity, "config", None)
    return raw or {}


def _make_store_handler(method: str):
    """构造一个 store 能力 handler: 校验 store 服务就绪 + 卡片已落库, 再委派给 store_service。"""

    def _handler(svc, entity, workspace_id, queries, params, query_key) -> Dict[str, Any]:
        if getattr(svc, "_store_service", None) is None:
            return {"trust": "none", "error": "store 服务未初始化"}
        app_card_id = _entity_id(entity)
        if app_card_id is None:
            return {"trust": "none", "error": "store 能力需要已落库的卡片, 预览模式不可用"}
        method_fn = getattr(svc._store_service, method)
        return method_fn(app_card_id, workspace_id, params, _entity_config(entity))

    return _handler


def _make_kv_handler(method: str):
    """构造一个 kv 能力 handler(KV 不需要 config, 只需卡片 id)。"""

    def _handler(svc, entity, workspace_id, queries, params, query_key) -> Dict[str, Any]:
        if getattr(svc, "_store_service", None) is None:
            return {"trust": "none", "error": "store 服务未初始化"}
        app_card_id = _entity_id(entity)
        if app_card_id is None:
            return {"trust": "none", "error": "kv 能力需要已落库的卡片, 预览模式不可用"}
        method_fn = getattr(svc._store_service, method)
        return method_fn(app_card_id, workspace_id, params)

    return _handler


def _register_app_card_ops() -> None:
    """注册统一 invoke 协议的全部 op。

    内置取数(query.metric / query.sql / assets.get / preview.*)迁移到注册表;
    store.* / kv.*(子应用自身数据空间读写)作为新能力接入。
    """
    register_app_card_op("query.metric", lambda svc, entity, ws, qs, params, qk: svc._invoke_metric(entity, ws, qs, params, qk))
    register_app_card_op("metric.preview", lambda svc, entity, ws, qs, params, qk: svc._invoke_metric(entity, ws, qs, params, qk))
    register_app_card_op("query.sql", lambda svc, entity, ws, qs, params, qk: svc._invoke_sql(entity, ws, qs, params, qk))
    register_app_card_op("sql.preview", lambda svc, entity, ws, qs, params, qk: svc._invoke_sql(entity, ws, qs, params, qk))
    register_app_card_op("assets.get", lambda svc, entity, ws, qs, params, qk: svc._invoke_assets(entity, ws, qs, params, qk))

    register_app_card_op("store.insert", _make_store_handler("insert_record"))
    register_app_card_op("store.query", _make_store_handler("query_records"))
    register_app_card_op("store.update", _make_store_handler("update_record"))
    register_app_card_op("store.delete", _make_store_handler("delete_record"))
    register_app_card_op("kv.get", _make_kv_handler("kv_get"))
    register_app_card_op("kv.put", _make_kv_handler("kv_put"))
    register_app_card_op("kv.del", _make_kv_handler("kv_del"))


_register_app_card_ops()

