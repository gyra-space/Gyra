"""Playbook service: CRUD + version + DSL validation + runtime context assembly."""
import json
import logging
from typing import Any, Dict, List, Optional

from gyra.component import SystemApp
from gyra.storage.metadata import BaseDao
from gyra_serve.core import BaseService

from ..api.schemas import (
    PlaybookListFilter, PlaybookRequest, PlaybookResponse,
    PlaybookValidateRequest, PlaybookVersionResponse,
)
from ..config import ServeConfig
from ..models.models import (
    PlaybookDao, PlaybookEntity, PlaybookVersionDao, PlaybookVersionEntity,
)

PLAYBOOK_SERVICE_COMPONENT_NAME = "serve_playbook_service"
logger = logging.getLogger(__name__)


class PlaybookService(BaseService[PlaybookEntity, PlaybookRequest, PlaybookResponse]):
    name = PLAYBOOK_SERVICE_COMPONENT_NAME

    def __init__(
        self, system_app: SystemApp, config: ServeConfig,
        dao: Optional[PlaybookDao] = None,
        version_dao: Optional[PlaybookVersionDao] = None,
    ):
        self._system_app = None
        self._serve_config: ServeConfig = config
        self._dao: PlaybookDao = dao
        self._version_dao: PlaybookVersionDao = version_dao
        super().__init__(system_app)

    def init_app(self, system_app: SystemApp) -> None:
        super().init_app(system_app)
        self._dao = self._dao or PlaybookDao()
        self._version_dao = self._version_dao or PlaybookVersionDao()
        self._system_app = system_app

    @property
    def dao(self) -> BaseDao:
        return self._dao

    @property
    def version_dao(self) -> PlaybookVersionDao:
        return self._version_dao

    @property
    def config(self) -> ServeConfig:
        return self._serve_config

    def validate_declaration(self, declaration: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the strategy declaration DSL.
        Returns {valid: bool, errors: [str]}.

        v2 schema:
        - text_content: optional dict with workflow/role_definition/goal/behavior_constraints/background
        - skills: list of strings (skill codes or refs)
        - context: {assets_required: [...], resources: [...]}
        - deliverables: list of {type, delivery: [...]}
        - distill: {forced: bool, produce: [...]}
        """
        errors = []
        if not isinstance(declaration, dict):
            return {"valid": False, "errors": ["declaration must be a dict"]}

        # Required blocks
        for key in ["skills", "deliverables", "distill"]:
            if key not in declaration:
                errors.append(f"missing required block: {key}")

        # Validate skills
        if "skills" in declaration and not isinstance(declaration["skills"], list):
            errors.append("skills must be a list")

        # Validate deliverables
        if "deliverables" in declaration:
            if not isinstance(declaration["deliverables"], list):
                errors.append("deliverables must be a list")
            else:
                for i, d in enumerate(declaration["deliverables"]):
                    if not isinstance(d, dict) or "type" not in d:
                        errors.append(f"deliverables[{i}] must have 'type'")

        # Validate distill
        if "distill" in declaration:
            distill = declaration["distill"]
            if not isinstance(distill, dict):
                errors.append("distill must be a dict")
            elif distill.get("forced") not in (True, False, None):
                errors.append("distill.forced must be bool")
            elif distill.get("forced") is True and not distill.get("produce"):
                errors.append("distill.forced=true requires non-empty produce list")

        # NEW: Validate text_content (RFC-005 剧本独立文本部分)
        if "text_content" in declaration:
            tc = declaration["text_content"]
            if not isinstance(tc, dict):
                errors.append("text_content must be a dict")
            else:
                valid_keys = {
                    "workflow",
                    "role_definition",
                    "goal",
                    "behavior_constraints",
                    "background",
                }
                for key, val in tc.items():
                    if key not in valid_keys:
                        errors.append(f"text_content has unknown key: {key}")
                    if not isinstance(val, str):
                        errors.append(f"text_content.{key} must be string")

        # NEW: Validate roles (P2 任务10 Agent 职能角色声明)
        # 结构: {fetcher: {skills: [...], maturity_min: novice}, ...}
        if "roles" in declaration:
            roles_block = declaration["roles"]
            if not isinstance(roles_block, dict):
                errors.append("roles must be a dict")
            else:
                # 延迟导入避免 playbook <-> workspace 循环依赖
                try:
                    from gyra_serve.workspace.agent_roles import AgentRole
                    valid_role_keys = {r.value for r in AgentRole}
                except Exception:
                    valid_role_keys = {
                        "fetcher", "analyzer", "reporter",
                        "coordinator", "reviewer",
                    }
                for role_key, role_decl in roles_block.items():
                    if role_key not in valid_role_keys:
                        errors.append(
                            f"roles has unknown role: {role_key} "
                            f"(valid: {sorted(valid_role_keys)})"
                        )
                    if role_decl is None:
                        continue
                    if not isinstance(role_decl, dict):
                        errors.append(f"roles.{role_key} must be a dict")
                        continue
                    if "skills" in role_decl and not isinstance(
                        role_decl["skills"], list
                    ):
                        errors.append(f"roles.{role_key}.skills must be a list")
                    if "maturity_min" in role_decl and not isinstance(
                        role_decl["maturity_min"], str
                    ):
                        errors.append(
                            f"roles.{role_key}.maturity_min must be a string"
                        )

        return {"valid": len(errors) == 0, "errors": errors}

    # ------------------------------------------------------------------ #
    # 引用完整性:剧本 = 空间池子集(空间=注册/治理池,剧本=选配/编排子集)
    # ------------------------------------------------------------------ #
    def _load_workspace_pool(self, workspace_id: int) -> Dict[str, Any]:
        """加载空间资源池,按引用键(physical_ref / name)索引。

        查询失败或取不到 service 时返回空 dict——校验降级为只提示不阻断,
        保证 create/update/seed 在任何异常下都不被误伤。
        """
        pool: Dict[str, Any] = {}
        try:
            from gyra_serve.workspace.service.service import (
                WorkspaceService, WORKSPACE_SERVICE_COMPONENT_NAME,
            )
            ws_service = self._system_app.get_component(
                WORKSPACE_SERVICE_COMPONENT_NAME, WorkspaceService, default=None,
            )
            records = ws_service.list_resources(workspace_id) if ws_service else []
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[playbook validate] load workspace pool failed: {e}")
            return pool
        for rec in records or []:
            if not getattr(rec, "is_active", True):
                continue
            for key in (getattr(rec, "physical_ref", None), getattr(rec, "name", None)):
                if key:
                    pool.setdefault(key, rec)
        return pool

    def _skill_exists(self, skill_code: str) -> Optional[bool]:
        """全局技能库是否存在该 skill_code(尽力校验)。返回 None 表示无法校验。"""
        try:
            from gyra_serve.skill.service.service import (
                Service, SKILL_SERVICE_COMPONENT_NAME,
            )
            skill_service = self._system_app.get_component(
                SKILL_SERVICE_COMPONENT_NAME, Service, default=None,
            )
            if skill_service is None:
                return None
            return skill_service.get_by_skill_code(skill_code) is not None
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[playbook validate] skill check failed: {e}")
            return None

    def _mcp_exists(self, mcp_code: str) -> Optional[bool]:
        """全局 MCP 注册表是否存在该 mcp_code(尽力校验)。返回 None 表示无法校验。"""
        try:
            from gyra_serve.agent.resource.tool.mcp_collect import get_mcp_info
            return get_mcp_info(mcp_code) is not None
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[playbook validate] mcp check failed: {e}")
            return None

    def validate_references(
        self, workspace_id: int, declaration: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """引用完整性校验:剧本引用的资产/能力应对齐空间资源池。

        规则(消除"空间与剧本都能挂资源"的误解,收敛为单向依赖):
        - 引用命中空间池(workspace_resource.physical_ref/name) -> OK;
        - 未命中但全局可解析(skill/mcp 可确定存在) -> warning(不阻断,兼容存量
          seed/历史剧本,提示绑定以获得空间治理与权限投影);
        - 未命中且全局确认不存在(skill/mcp) -> error(阻断保存,防悬空引用);
        - 其他类型(datasource/knowledge/app/llm_model/ecp)无法低成本核验全局
          -> 仅 warning 提示绑定。

        Returns {"errors": [...], "warnings": [...]}
        """
        errors: List[str] = []
        warnings: List[str] = []
        pool_by_ref = self._load_workspace_pool(workspace_id)

        def _check(ref: str, ref_type: Optional[str], label: str) -> None:
            if not ref or ref in pool_by_ref:
                return
            exists: Optional[bool] = None
            if ref_type in ("skill", "agent_skill"):
                exists = self._skill_exists(ref)
            elif ref_type == "mcp":
                exists = self._mcp_exists(ref)
            if exists is False:
                errors.append(
                    f"{label} '{ref}' 不存在或未绑定到当前空间:请先在全局注册,"
                    f"再到空间「能力/资源」页绑定"
                )
            else:
                warnings.append(
                    f"{label} '{ref}' 未绑定到当前空间:运行时可用,但无法获得"
                    f"空间治理/权限投影;建议到空间「能力/资源」页绑定"
                )

        for item in declaration.get("skills") or []:
            if isinstance(item, str):
                _check(item, "skill", "技能")
            elif isinstance(item, dict):
                ref = item.get("name") or item.get("skill_code") or item.get("ref")
                _check(ref, item.get("type") or "skill", "技能")

        ctx = declaration.get("context") or {}
        for res in ctx.get("resources") or []:
            if isinstance(res, str):
                _check(res, None, "资源")
            elif isinstance(res, dict):
                ref = res.get("name") or res.get("ref") or res.get("server_name")
                _check(ref, res.get("type"), "资源")

        return {"errors": errors, "warnings": warnings}

    def create(self, request: PlaybookRequest) -> PlaybookResponse:
        validation = self.validate_declaration(request.declaration or {})
        if not validation["valid"]:
            raise ValueError(f"invalid declaration DSL: {validation['errors']}")
        refs = self.validate_references(request.workspace_id, request.declaration or {})
        if refs["errors"]:
            raise ValueError(
                f"invalid declaration references: {'; '.join(refs['errors'])}"
            )
        for w in refs["warnings"]:
            logger.warning(f"[playbook create] {request.name}: {w}")
        response = self._dao.create(request)
        # record initial version
        self._version_dao.create_version(
            playbook_id=response.id,
            version=1,
            declaration=request.declaration or {},
            changelog="initial",
            created_by_user_id=request.id and None,
        )
        return response

    def update(self, request: PlaybookRequest) -> PlaybookResponse:
        if not request.id:
            raise ValueError("playbook id required for update")
        validation = self.validate_declaration(request.declaration or {})
        if not validation["valid"]:
            raise ValueError(f"invalid declaration DSL: {validation['errors']}")
        refs = self.validate_references(request.workspace_id, request.declaration or {})
        if refs["errors"]:
            raise ValueError(
                f"invalid declaration references: {'; '.join(refs['errors'])}"
            )
        for w in refs["warnings"]:
            logger.warning(f"[playbook update] {request.name}: {w}")
        # 必须用局部 session 变量:db._session 是 sessionmaker(非 scoped_session),
        # get_raw_session() 每次返回新 session。若写成 self._dao.get_raw_session()
        # .commit() 会 commit 到另一个空 session,existing 的改动从未提交 -> 返回的
        # 是内存新值但 DB 没落盘,页面重开就是旧数据。
        session = self._dao.get_raw_session()
        try:
            existing = session.query(PlaybookEntity).filter(
                PlaybookEntity.id == request.id
            ).first()
            if not existing:
                raise ValueError(f"playbook {request.id} not found")
            existing.name = request.name
            existing.scenario_type = request.scenario_type
            existing.task_type = request.task_type
            existing.trigger_json = json.dumps(request.trigger or {}, ensure_ascii=False)
            existing.declaration_dsl_json = json.dumps(
                request.declaration or {}, ensure_ascii=False
            )
            if request.is_active is not None:
                existing.is_active = request.is_active
            # bump version
            existing.current_version = (existing.current_version or 1) + 1
            session.commit()
            # commit 后属性 expire;close 前 refresh 防 to_response 读属性 DetachedInstanceError
            session.refresh(existing)
            response = self._dao.to_response(existing)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
        # record version(create_version 自管独立 session)
        self._version_dao.create_version(
            playbook_id=response.id,
            version=response.current_version,
            declaration=request.declaration or {},
            changelog="update",
        )
        return response

    def get_by_id(self, playbook_id: int) -> Optional[PlaybookResponse]:
        entity = self._dao.get_raw_session().query(PlaybookEntity).filter(
            PlaybookEntity.id == playbook_id
        ).first()
        return self._dao.to_response(entity) if entity else None

    def list_playbooks(self, f: PlaybookListFilter) -> List[PlaybookResponse]:
        return self._dao.list_by_filter(f)

    def delete(self, playbook_id: int) -> bool:
        session = self._dao.get_raw_session()
        try:
            entity = session.query(PlaybookEntity).filter(
                PlaybookEntity.id == playbook_id
            ).first()
            if not entity:
                return False
            session.delete(entity)
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_versions(self, playbook_id: int) -> List[PlaybookVersionResponse]:
        return self._version_dao.list_versions(playbook_id)

    def assemble_context(self, playbook: PlaybookResponse, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Assemble Agent execution context from Playbook declaration.

        Returns dict with: skills, assets_required, resources, deliverables, distill,
        plus task_input merged in. The runtime layer will use this to inject into Agent prompt.
        """
        declaration = playbook.declaration or {}
        return {
            "playbook_id": playbook.id,
            "playbook_name": playbook.name,
            "scenario_type": playbook.scenario_type,
            "task_type": playbook.task_type,
            "skills": declaration.get("skills", []),
            "context": declaration.get("context", {}),
            "deliverables": declaration.get("deliverables", []),
            "distill": declaration.get("distill", {}),
            "roles": declaration.get("roles", {}),
            "task_input": task_input or {},
        }
