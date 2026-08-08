"""Workspace service: business logic + member / resource management."""
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

from gyra.component import SystemApp
from gyra.storage.metadata import BaseDao
from gyra_serve.core import BaseService

from ..api.schemas import (
    WorkspaceListFilter,
    WorkspaceMemberRequest,
    WorkspaceMemberResponse,
    WorkspaceRequest,
    WorkspaceResourceRequest,
    WorkspaceResourceResponse,
    WorkspaceResponse,
)
from ..config import ServeConfig
from ..models.models import (
    WorkspaceConversationLinkDao,
    WorkspaceConversationLinkEntity,
    WorkspaceDao,
    WorkspaceEntity,
    WorkspaceMemberDao,
    WorkspaceMemberEntity,
    WorkspaceResourceDao,
    WorkspaceResourceEntity,
)

WORKSPACE_SERVICE_COMPONENT_NAME = "serve_workspace_service"

logger = logging.getLogger(__name__)


class WorkspaceService(BaseService[WorkspaceEntity, WorkspaceRequest, WorkspaceResponse]):
    """Workspace CRUD + member/resource orchestration"""

    name = WORKSPACE_SERVICE_COMPONENT_NAME

    def __init__(
        self,
        system_app: SystemApp,
        config: ServeConfig,
        dao: Optional[WorkspaceDao] = None,
        member_dao: Optional[WorkspaceMemberDao] = None,
        resource_dao: Optional[WorkspaceResourceDao] = None,
        conv_link_dao: Optional[WorkspaceConversationLinkDao] = None,
    ):
        self._system_app = None
        self._serve_config: ServeConfig = config
        self._dao: WorkspaceDao = dao
        self._member_dao: WorkspaceMemberDao = member_dao
        self._resource_dao: WorkspaceResourceDao = resource_dao
        self._conv_link_dao: WorkspaceConversationLinkDao = conv_link_dao
        super().__init__(system_app)

    def init_app(self, system_app: SystemApp) -> None:
        super().init_app(system_app)
        self._dao = self._dao or WorkspaceDao()
        self._member_dao = self._member_dao or WorkspaceMemberDao()
        self._resource_dao = self._resource_dao or WorkspaceResourceDao()
        self._conv_link_dao = self._conv_link_dao or WorkspaceConversationLinkDao()
        self._system_app = system_app

    @property
    def dao(self) -> BaseDao:
        return self._dao

    @property
    def member_dao(self) -> WorkspaceMemberDao:
        return self._member_dao

    @property
    def resource_dao(self) -> WorkspaceResourceDao:
        return self._resource_dao

    @property
    def conv_link_dao(self) -> WorkspaceConversationLinkDao:
        return self._conv_link_dao

    @property
    def config(self) -> ServeConfig:
        return self._serve_config

    # ---------------- Workspace CRUD ----------------
    def create(self, request: WorkspaceRequest) -> WorkspaceResponse:
        if not request.workspace_code:
            request.workspace_code = f"ws_{uuid.uuid4().hex[:12]}"
        existing = self._dao.get_one({"workspace_code": request.workspace_code})
        if existing:
            raise ValueError(f"workspace_code '{request.workspace_code}' already exists")
        if request.owner_user_id is None:
            raise ValueError("owner_user_id is required")

        response = self._dao.create(request)
        # auto add owner as a member with role=owner
        owner_request = WorkspaceMemberRequest(
            workspace_id=response.id,
            user_id=response.owner_user_id,
            role="owner",
        )
        try:
            self._member_dao.create(owner_request)
        except Exception as e:
            logger.warning(f"auto add owner member failed: {e}")
        # Auto bind scene workspace agent for new scenario workspaces if not set
        try:
            if not response.default_agent_app_code:
                self._dao.update(
                    {"workspace_code": response.workspace_code},
                    {"default_agent_app_code": "scene-workspace-agent"},
                    force_update=True,
                )
        except Exception as e:
            logger.warning(f"auto bind default scene agent failed: {e}")
        self._provision_ecp_workspace(response)
        return self.get_by_id(response.id)  # reload to get member_count

    def _provision_ecp_workspace(self, response: WorkspaceResponse) -> None:
        """供给派生 ECP workspace(best-effort,任一步失败不影响建空间)。

        - owner 写入确认白名单:收紧该空间的提案确认权限(空白名单=放行一切,
          见 ConfirmerDao.is_confirmer bootstrap 规则)。
        - 预建 ECP 软知识空间(get_or_create_space 幂等):异步,fire-and-forget。
        """
        import asyncio

        from gyra_serve.workspace.ecp_derive import derived_ecp_workspace_id

        ecp_ws = derived_ecp_workspace_id(response.workspace_code)
        owner_id = str(response.owner_user_id)
        try:
            from gyra_serve.ecp.models.models import ConfirmerDao

            ConfirmerDao().add(ecp_ws, owner_id)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"ecp confirmer provision failed for {ecp_ws}: {e}")
        try:
            from gyra_serve.ecp.config import (
                SERVE_SERVICE_COMPONENT_NAME as ECP_SERVICE,
            )
            from gyra_serve.ecp.service.service import Service as EcpService

            if not self._system_app:
                return
            ecp_service = self._system_app.get_component(ECP_SERVICE, EcpService)
            coro = ecp_service.get_or_create_space(ecp_ws, owner_id=owner_id)
            try:
                asyncio.get_running_loop().create_task(coro)
            except RuntimeError:  # 无运行中事件循环(脚本/测试上下文)
                asyncio.run(coro)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"ecp space provision failed for {ecp_ws}: {e}")

    def update(self, request: WorkspaceRequest) -> WorkspaceResponse:
        if not request.workspace_code:
            raise ValueError("workspace_code is required for update")
        existing = self._dao.get_one({"workspace_code": request.workspace_code})
        if not existing:
            raise ValueError(f"workspace '{request.workspace_code}' not found")
        update_dict: Dict[str, Any] = {}
        for k in ["name", "description", "type", "scenario_type", "scene_mode",
                  "default_agent_app_code", "is_archived"]:
            v = getattr(request, k, None)
            if v is not None:
                update_dict[k] = v
        if request.settings is not None:
            update_dict["settings_json"] = json.dumps(
                request.settings, ensure_ascii=False
            )
        self._dao.update(
            {"workspace_code": request.workspace_code}, update_dict, force_update=True
        )
        return self.get_by_id(existing.id)

    def archive(self, workspace_code: str) -> WorkspaceResponse:
        existing = self._dao.get_one({"workspace_code": workspace_code})
        if not existing:
            raise ValueError(f"workspace '{workspace_code}' not found")
        self._dao.update(
            {"workspace_code": workspace_code},
            {"is_archived": True},
            force_update=True,
        )
        return self.get_by_id(existing.id)

    def release(self, workspace_code: str) -> bool:
        """释放(软删除)场景空间 —— 危险操作,仅限空间拥有者。

        语义(与"归档"区分):
        - 将 workspace 标记为 ``is_deleted=True``,从而从所有列表隐藏。
        - 物理删除空间核心关联记录:成员、资源、会话关联(conv_link)。
        - 保留 workspace 底层记录,便于后续恢复;不清理任务/资产/ECP 派生空间等
          派生数据(避免产生破坏性级联)。
        """
        existing = self._dao.get_one({"workspace_code": workspace_code})
        if not existing:
            raise ValueError(f"workspace '{workspace_code}' not found")
        ws_id = existing.id
        self._dao.update(
            {"workspace_code": workspace_code},
            {"is_deleted": True},
            force_update=True,
        )
        # 清理核心关联记录(成员 / 资源 / 会话关联)
        for entity_cls in (
            WorkspaceMemberEntity,
            WorkspaceResourceEntity,
            WorkspaceConversationLinkEntity,
        ):
            session = self._dao.get_raw_session()
            try:
                session.query(entity_cls).filter(
                    entity_cls.workspace_id == ws_id
                ).delete(synchronize_session=False)
                session.commit()
            except Exception as e:  # noqa: BLE001
                session.rollback()
                logger.warning(f"release cleanup failed for {entity_cls.__name__} ws={ws_id}: {e}")
            finally:
                session.close()
        logger.info(f"workspace released(soft-deleted): code={workspace_code} id={ws_id}")
        return True

    def get_by_code(self, workspace_code: str) -> Optional[WorkspaceResponse]:
        entity = self._dao.get_raw_session().query(WorkspaceEntity).filter(
            WorkspaceEntity.workspace_code == workspace_code
        ).first()
        if not entity:
            return None
        return self._dao.to_response(
            entity, member_count=self._member_dao.count_by_workspace(entity.id)
        )

    def get_by_id(self, workspace_id: int) -> Optional[WorkspaceResponse]:
        entity = self._dao.get_raw_session().query(WorkspaceEntity).filter(
            WorkspaceEntity.id == workspace_id
        ).first()
        if not entity:
            return None
        return self._dao.to_response(
            entity, member_count=self._member_dao.count_by_workspace(entity.id)
        )

    def list_workspaces(
        self, user_id: Optional[int], scenario_type: Optional[str] = None,
        include_archived: bool = False,
    ) -> List[WorkspaceResponse]:
        return self._dao.filter_list(
            WorkspaceListFilter(
                user_id=user_id,
                scenario_type=scenario_type,
                include_archived=include_archived,
            )
        )

    # ---------------- Home workspace(首页默认空间) ----------------
    def get_or_create_home(self, user_id: int) -> WorkspaceResponse:
        """用户首页默认空间(幂等 get-or-create)。

        解析顺序(基于用户级 member.is_home,按用户隔离):
        1. 成员可见空间中有 member.is_home=True 的 -> 返回
        2. 兼容存量:有旧 settings.is_home 标记(空间级)的 -> 一次性提升为用户级主空间返回
        3. 无标记 -> 取最早创建(id 最小)的补用户级标记后返回(零迁移)
        4. 一个空间都没有 -> 新建"我的工作台"(create 的派生钩子全部生效:
        owner 成员/默认 agent/ECP workspace 供给)
        归档的空间不参与选择;用户归档首页空间后,下次访问自动选下一个或新建。
        """
        spaces = self.list_workspaces(user_id)
        if spaces:
            home_id = self._member_dao.get_home_workspace_id(user_id)
            if home_id is not None:
                home = next((s for s in spaces if s.id == home_id), None)
                if home:
                    return home
            # 存量数据兼容:旧空间级 settings.is_home 一次性提升为用户级主空间
            legacy = next(
                (s for s in spaces if (s.settings or {}).get("is_home")), None
            )
            if legacy:
                self._mark_home_member(legacy.id, user_id)
                return legacy
            home = min(spaces, key=lambda s: s.id)
            self._mark_home_member(home.id, user_id)
            return home
        return self.create(
            WorkspaceRequest(
                name="我的工作台",
                owner_user_id=user_id,
                settings={"is_home": True},
            )
        )

    def set_home(self, user_id: int, workspace_id: int) -> Optional[WorkspaceResponse]:
        """把某空间设为用户的默认(主)空间。

        仅当用户是该空间成员时生效;成功后返回该空间,否则返回 None。
        """
        ok = self._member_dao.set_home(workspace_id, user_id)
        if not ok:
            return None
        return self.get_by_id(workspace_id)

    def _mark_home_member(self, workspace_id: int, user_id: int) -> None:
        """给用户在该空间的成员关系打 is_home 标记(用户级)。"""
        try:
            self._member_dao.set_home(workspace_id, user_id)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"mark home member failed ws={workspace_id} user={user_id}: {e}")

    # ---------------- Member management ----------------
    def list_members(self, workspace_id: int) -> List[WorkspaceMemberResponse]:
        """List members with user names.

        Queries member entities and joins user table to get user names.
        """
        results = self._member_dao.list_by_workspace_with_user_info(workspace_id)
        return [self._member_dao.to_response(entity, user_name) for entity, user_name in results]

    def add_member(self, request: WorkspaceMemberRequest) -> WorkspaceMemberResponse:
        entities = self._member_dao.list_by_workspace(request.workspace_id)
        existing = next((e for e in entities if e.user_id == request.user_id), None)
        if existing:
            self._member_dao.update(
                {"workspace_id": request.workspace_id, "user_id": request.user_id},
                {"role": request.role},
                force_update=True,
            )
            refreshed = next(
                (
                    e for e in self._member_dao.list_by_workspace(request.workspace_id)
                    if e.user_id == request.user_id
                ),
                None,
            )
            return self._member_dao.to_response(refreshed) if refreshed else None
        return self._member_dao.create(request)

    def remove_member(self, workspace_id: int, user_id: int) -> bool:
        entities = self._member_dao.list_by_workspace(workspace_id)
        target = next((e for e in entities if e.user_id == user_id), None)
        if not target:
            return False
        if target.role == "owner":
            raise ValueError("cannot remove owner; transfer ownership first")
        self._member_dao.delete({"workspace_id": workspace_id, "user_id": user_id})
        return True

    def update_member_role(
        self, workspace_id: int, user_id: int, role: str
    ) -> WorkspaceMemberResponse:
        entities = self._member_dao.list_by_workspace(workspace_id)
        target = next((e for e in entities if e.user_id == user_id), None)
        if not target:
            raise ValueError("member not found")
        self._member_dao.update(
            {"workspace_id": workspace_id, "user_id": user_id},
            {"role": role},
            force_update=True,
        )
        refreshed = next(
            (e for e in self._member_dao.list_by_workspace(workspace_id) if e.user_id == user_id),
            None,
        )
        return self._member_dao.to_response(refreshed) if refreshed else None

    def check_membership(self, workspace_id: int, user_id: int) -> Optional[str]:
        return self._member_dao.get_role(workspace_id, user_id)

    # ---------------- Resource management ----------------
    def list_resources(
        self, workspace_id: int, type_filter: Optional[str] = None
    ) -> List[WorkspaceResourceResponse]:
        entities = self._resource_dao.list_by_workspace(workspace_id, type_filter)
        return [self._resource_dao.to_response(e) for e in entities]

    def add_resource(self, request: WorkspaceResourceRequest) -> WorkspaceResourceResponse:
        return self._resource_dao.create(request)

    def remove_resource(self, resource_id: int) -> bool:
        entity = self._resource_dao.get_raw_session().query(
            WorkspaceResourceEntity
        ).filter(WorkspaceResourceEntity.id == resource_id).first()
        if not entity:
            return False
        with self._resource_dao.session() as session:
            row = session.query(WorkspaceResourceEntity).filter(
                WorkspaceResourceEntity.id == resource_id
            ).first()
            if row:
                session.delete(row)
        return True

    def update_resource(
        self, resource_id: int, request: WorkspaceResourceRequest
    ) -> WorkspaceResourceResponse:
        update_dict = {
            "type": request.type,
            "name": request.name,
            "category": request.category,
            "physical_ref": request.physical_ref,
            "config_json": json.dumps(request.config or {}, ensure_ascii=False),
            "access_mode": request.access_mode,
            "is_active": request.is_active,
        }
        self._resource_dao.update({"id": resource_id}, update_dict, force_update=True)
        entity = self._resource_dao.get_raw_session().query(
            WorkspaceResourceEntity
        ).filter(WorkspaceResourceEntity.id == resource_id).first()
        return self._resource_dao.to_response(entity)

    # ---------------- Growth ----------------
    def get_growth(self, workspace_id: int) -> dict:
        """返回空间本月成长数据。

        P0 阶段演化提议数恒为 0（提议生成 P2 才做），知识图谱节点数 P1 才接入 llm-wiki。
        """
        from datetime import datetime, timedelta

        from gyra_serve.task.api.schemas import TaskListFilter
        from gyra_serve.task.service.service import (
            TASK_SERVICE_COMPONENT_NAME,
            TaskService,
        )
        from gyra_serve.workspace_asset.api.schemas import AssetListFilter
        from gyra_serve.workspace_asset.service.service import (
            ASSET_SERVICE_COMPONENT_NAME,
            AssetService,
        )

        now = datetime.now()
        month_ago = now - timedelta(days=30)

        try:
            asset_svc: AssetService = self._system_app.get_component(
                ASSET_SERVICE_COMPONENT_NAME, AssetService
            )
            assets = asset_svc.list_assets(
                AssetListFilter(workspace_id=workspace_id, limit=10000)
            ) or []
            assets_count = len(assets)
        except Exception as e:
            logger.warning(f"get_growth assets failed: {e}")
            assets_count = 0

        try:
            task_svc: TaskService = self._system_app.get_component(
                TASK_SERVICE_COMPONENT_NAME, TaskService
            )
            tasks = task_svc.list_tasks(
                TaskListFilter(workspace_id=workspace_id, limit=10000)
            ) or []
            trend_map: dict = {}
            for t in tasks:
                created_str = getattr(t, "gmt_created", None)
                if not created_str:
                    continue
                try:
                    created = datetime.fromisoformat(created_str)
                    if created >= month_ago:
                        key = created.strftime("%Y-%m-%d")
                        trend_map[key] = trend_map.get(key, 0) + 1
                except Exception:
                    continue
            tasks_trend = [
                {"date": k, "count": v}
                for k, v in sorted(trend_map.items())
            ]
        except Exception as e:
            logger.warning(f"get_growth tasks failed: {e}")
            tasks_trend = []

        return {
            "assets_count": assets_count,
            "evolution_proposals_count": 0,  # P0 占位，P2 才做生成
            "tasks_trend": tasks_trend,
            "knowledge_graph_nodes": 0,  # P0 占位，P1 接入 llm-wiki
        }

    # ---------------- Conversation link ----------------
    def link_conversation(
        self, workspace_id: int, conv_uid: str,
        task_id: Optional[int] = None, user_id: Optional[int] = None,
        title: Optional[str] = None,
    ) -> Dict[str, Any]:
        entity = self._conv_link_dao.link(
            workspace_id=workspace_id, conv_uid=conv_uid,
            task_id=task_id, user_id=user_id, title=title,
        )
        return self._conv_link_dao.to_response(entity)

    def list_conversations(
        self, workspace_id: int, user_id: Optional[int] = None, limit: int = 100,
    ) -> List[Dict[str, Any]]:
        rows = self._conv_link_dao.list_by_workspace(workspace_id, user_id, limit)
        result = []
        for r in rows:
            resp = self._conv_link_dao.to_response(r)
            # 空闲标题兜底:自动生成标题的机制(首条输入 / LLM 摘要)对历史会话可能缺失,
            # 这里用会话首条用户提问作为兜底标题,避免列表显示无意义的「会话 xxxx」。
            if not (resp.get("title") or "").strip():
                resp["title"] = self._derive_title_from_first_message(resp.get("conv_uid"))
            result.append(resp)
        return result

    def _derive_title_from_first_message(self, conv_uid: Optional[str]) -> Optional[str]:
        """从会话首条用户消息抽取纯文本作为兜底标题;无则返回 None。"""
        if not conv_uid:
            return None
        try:
            from gyra.storage.chat_history.chat_history_db import ChatHistoryMessageDao
            items = ChatHistoryMessageDao().get_messages_by_conv_uid(conv_uid)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[conv_title] fallback derive failed: {e}")
            return None
        for item in items:
            detail = item.message_detail or {}
            if detail.get("type") not in ("human", "user"):
                continue
            content = (detail.get("data") or {}).get("content", "")
            if isinstance(content, str):
                text = content.strip()
            elif isinstance(content, list):
                text = " ".join(
                    p.get("text", "") for p in content
                    if isinstance(p, dict) and p.get("type") == "text"
                ).strip()
            else:
                text = ""
            if text:
                return text[:60]
        return None

    def get_conversation_workspace(self, conv_uid: str) -> Optional[Dict[str, Any]]:
        row = self._conv_link_dao.get_by_conv(conv_uid)
        return self._conv_link_dao.to_response(row) if row else None

    def get_current_conversation(
        self, workspace_id: int, user_id: Optional[int]
    ) -> Optional[Dict[str, Any]]:
        row = self._conv_link_dao.get_current(
            workspace_id=workspace_id, user_id=user_id
        )
        return self._conv_link_dao.to_response(row) if row else None

    def set_current_conversation(
        self, workspace_id: int, user_id: Optional[int], conv_uid: str
    ) -> Dict[str, Any]:
        link = self._conv_link_dao.get_by_conv(conv_uid)
        if link is None or link.workspace_id != workspace_id:
            raise ValueError(
                f"Conversation {conv_uid} not linked to workspace {workspace_id}"
            )
        # 仅当 link 有归属用户时才校验;无主 link(user_id=None)对所有用户放行
        if (
            user_id is not None
            and link.user_id is not None
            and link.user_id != user_id
        ):
            raise ValueError(
                f"Conversation {conv_uid} not linked to workspace {workspace_id} "
                f"for user {user_id}"
            )
        self._conv_link_dao.set_current(workspace_id, user_id, conv_uid)
        current = self._conv_link_dao.get_current(
            workspace_id=workspace_id, user_id=user_id
        )
        if current is None:
            raise ValueError("Failed to set current conversation")
        return self._conv_link_dao.to_response(current)

    def rename_conversation(
        self, conv_uid: str, title: str
    ) -> Optional[Dict[str, Any]]:
        self._conv_link_dao.rename(conv_uid=conv_uid, title=title)
        entity = self._conv_link_dao.get_by_conv(conv_uid)
        return self._conv_link_dao.to_response(entity) if entity else None

    # ---------------- Conversation title (A: first input / B: LLM summary) ----
    def get_conversation_title(self, conv_uid: str) -> Optional[str]:
        """Return current conv_link title (None if not linked / no title)."""
        entity = self._conv_link_dao.get_by_conv(conv_uid)
        return entity.title if entity else None

    def set_initial_title_if_empty(
        self, conv_uid: str, user_input: str,
    ) -> Optional[str]:
        """A: 用用户首条输入截断作为初始标题(仅在 title 为空时设置)。

        - 已有标题(用户手动重命名 / B 已生成)则保留,不覆盖。
        - 截断到 60 字符避免超长;首尾空白裁剪;空输入不写。
        """
        text = (user_input or "").strip()
        if not text:
            return None
        title = text[:60]
        existing = self._conv_link_dao.get_by_conv(conv_uid)
        if existing and (existing.title or "").strip():
            return existing.title
        self._conv_link_dao.rename(conv_uid=conv_uid, title=title)
        return title

    async def generate_title_from_llm(
        self, conv_uid: str, user_input: str, ai_reply: str,
        previous_title: Optional[str] = None,
    ) -> Optional[str]:
        """B: 调 LLM 生成简短摘要标题并 rename。

        - 仅在当前 title 为空 或 等于 previous_title(A 设的初始标题)时覆盖,
          避免覆盖用户手动重命名。
        - LLM 失败 / 无配置 / 无模型时静默返回 None,不阻塞对话链路。
        """
        config = self._get_llm_config()
        if not config:
            return None
        import httpx

        system_prompt = (
            "你是会话标题生成器。根据用户提问与助手回答,生成一个简洁的中文标题,"
            "不超过 20 个字,不加引号、不加标点结尾,直接输出标题文本。"
        )
        user_prompt = (
            f"用户提问:{(user_input or '').strip()[:500]}\n"
            f"助手回答:{(ai_reply or '').strip()[:500]}\n"
            "生成标题:"
        )
        payload = {
            "model": config["model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 60,
        }
        headers = {"Content-Type": "application/json"}
        if config["api_key"]:
            headers["Authorization"] = f"Bearer {config['api_key']}"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{config['base_url']}/chat/completions",
                    json=payload, headers=headers,
                )
                resp.raise_for_status()
                choices = resp.json().get("choices", [])
                if not choices:
                    return None
                raw = choices[0].get("message", {}).get("content", "")
                title = (raw or "").strip().strip('"\'').strip()
                if not title:
                    return None
                title = title[:60]
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[conv_title] LLM title generation failed: {e}")
            return None

        existing = self._conv_link_dao.get_by_conv(conv_uid)
        if not existing:
            return None
        current = (existing.title or "").strip()
        if current and previous_title and current != previous_title:
            # 用户在 A 之后手动重命名过,B 不覆盖
            return None
        self._conv_link_dao.rename(conv_uid=conv_uid, title=title)
        return title

    _llm_config_cache: Optional[Dict[str, str]] = None

    def _get_llm_config(self) -> Optional[Dict[str, str]]:
        """Lazy-init LLM API config from ModelConfigCache (复用 ecp propose 模式)."""
        if self._llm_config_cache is not None:
            return self._llm_config_cache or None
        try:
            from gyra.agent.util.llm.model_config_cache import ModelConfigCache

            all_models = ModelConfigCache.get_all_models()
            if not all_models:
                self._llm_config_cache = {}
                return None
            config = ModelConfigCache.get_config(all_models[0]) or {}
            base_url = (config.get("base_url") or config.get("api_base") or "").rstrip("/")
            if not base_url:
                self._llm_config_cache = {}
                return None
            if "/v1" not in base_url:
                base_url += "/v1"
            self._llm_config_cache = {
                "base_url": base_url,
                "api_key": config.get("api_key", ""),
                "model": config.get("model") or all_models[0],
            }
            return self._llm_config_cache
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[conv_title] LLM config init failed: {e}")
            self._llm_config_cache = {}
            return None
