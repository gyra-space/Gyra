"""Agent 职能角色 —— 把多 Agent 协作从"裸 app_code"抽象为职能角色。

P2 任务10: materializer 里 extra_agents 直接是 app_code,缺少职能抽象。
本模块定义五种职能角色及其技能/成熟度要求,并提供:
- 持久化 agent→role 分配(WorkspaceAgentRoleEntity)
- 角色技能查询
- 成熟度校验(联动 AgentMaturityService,角色要求最低成熟度)
- 团队装配(按 Playbook declaration 的 roles 块产出角色蓝图 + prompt)

五种角色:
    FETCHER    数据获取(novice)
    ANALYZER   分析判断(proficient)
    REPORTER   报告生成(novice)
    COORDINATOR 协调主导(expert)
    REVIEWER   审核校验(expert)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, Index, Integer, String

from gyra.component import SystemApp
from gyra.storage.metadata import BaseDao, Model
from gyra_serve.core import BaseService

from .agent_maturity.service import (
    AGENT_MATURITY_SERVICE_COMPONENT_NAME,
    AgentMaturityService,
    AgentStage,
)
from .config import SERVER_APP_TABLE_NAME, ServeConfig

AGENT_ROLE_SERVICE_COMPONENT_NAME = "serve_workspace_agent_role_service"
AGENT_ROLE_TABLE_NAME = f"{SERVER_APP_TABLE_NAME}_agent_role"

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    """Agent 职能角色。"""

    FETCHER = "fetcher"        # 数据获取
    ANALYZER = "analyzer"      # 分析判断
    REPORTER = "reporter"      # 报告生成
    COORDINATOR = "coordinator"  # 协调主导(必须 expert)
    REVIEWER = "reviewer"      # 审核校验(必须 expert)


# 角色要求:技能 / 最低成熟度 / 描述
ROLE_REQUIREMENTS: Dict[AgentRole, Dict[str, Any]] = {
    AgentRole.FETCHER: {
        "skills": ["db_query", "file_read"],
        "maturity_min": "novice",
        "description": "数据获取",
    },
    AgentRole.ANALYZER: {
        "skills": ["anomaly_detect", "statistical_analysis"],
        "maturity_min": "proficient",
        "description": "分析判断",
    },
    AgentRole.REPORTER: {
        "skills": ["report", "chart_generate"],
        "maturity_min": "novice",
        "description": "报告生成",
    },
    AgentRole.COORDINATOR: {
        "skills": [],
        "maturity_min": "expert",
        "description": "协调主导(必须expert)",
    },
    AgentRole.REVIEWER: {
        "skills": ["validate", "cross_check"],
        "maturity_min": "expert",
        "description": "审核校验(必须expert)",
    },
}


# 成熟度阶段排名(用于角色成熟度校验比较)
_STAGE_RANK: Dict[AgentStage, int] = {
    AgentStage.NOVICE: 0,
    AgentStage.PROFICIENT: 1,
    AgentStage.EXPERT: 2,
    AgentStage.MASTER: 3,
}


# 角色默认 prompt 模板(按角色装配不同 prompt)
_ROLE_PROMPT_TEMPLATES: Dict[AgentRole, str] = {
    AgentRole.FETCHER: (
        "你是数据获取专员(FETCHER)。负责按需查询数据源、读取文件,"
        "为分析与报告环节提供原始数据。只做获取与清洗,不做判断。"
    ),
    AgentRole.ANALYZER: (
        "你是分析判断专员(ANALYZER)。负责对获取到的数据进行异常检测、"
        "统计分析与归因,给出结论性判断。"
    ),
    AgentRole.REPORTER: (
        "你是报告生成专员(REPORTER)。负责将分析结论整理为结构化报告,"
        "并生成图表,输出可交付给人的最终文档。"
    ),
    AgentRole.COORDINATOR: (
        "你是协调主导(COORDINATOR)。负责拆解任务、分派其他角色、"
        "汇总结果并把控整体质量与进度。"
    ),
    AgentRole.REVIEWER: (
        "你是审核校验专员(REVIEWER)。负责对产出进行交叉校验与合规审核,"
        "发现问题需打回重做,通过后方可发布。"
    ),
}


@dataclass
class AgentRoleAssignment:
    """agent → role 的分配记录。"""

    agent_id: str
    role: AgentRole
    workspace_id: int


# --------------------------------------------------------------------------- #
# 持久化实体与 DAO
# --------------------------------------------------------------------------- #
class WorkspaceAgentRoleEntity(Model):
    """agent 职能角色分配表 —— 一个 (workspace_id, agent_id) 一条记录。"""

    __tablename__ = AGENT_ROLE_TABLE_NAME

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, nullable=False, index=True)
    agent_id = Column(String(128), nullable=False, index=True)
    role = Column(String(32), nullable=False, comment="fetcher/analyzer/reporter/coordinator/reviewer")

    gmt_created = Column(DateTime, name="gmt_create", default=datetime.now)
    gmt_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index(
            "uk_workspace_agent_role",
            "workspace_id", "agent_id", unique=True,
        ),
    )


class WorkspaceAgentRoleDao(BaseDao[WorkspaceAgentRoleEntity, Dict[str, Any], Dict[str, Any]]):
    """agent 职能角色 DAO。"""

    def from_request(self, request):
        raise NotImplementedError

    def to_request(self, entity):
        raise NotImplementedError

    def to_response(self, entity: WorkspaceAgentRoleEntity) -> Dict[str, Any]:
        return {
            "id": entity.id,
            "workspace_id": entity.workspace_id,
            "agent_id": entity.agent_id,
            "role": entity.role,
            "gmt_created": (
                entity.gmt_created.isoformat() if entity.gmt_created else ""
            ),
            "gmt_modified": (
                entity.gmt_modified.isoformat() if entity.gmt_modified else ""
            ),
        }

    def get_by_agent(
        self, agent_id: str, workspace_id: int
    ) -> Optional[WorkspaceAgentRoleEntity]:
        session = self.get_raw_session()
        try:
            return (
                session.query(WorkspaceAgentRoleEntity)
                .filter(
                    WorkspaceAgentRoleEntity.agent_id == agent_id,
                    WorkspaceAgentRoleEntity.workspace_id == workspace_id,
                )
                .first()
            )
        finally:
            session.close()

    def list_by_workspace(
        self, workspace_id: int
    ) -> List[WorkspaceAgentRoleEntity]:
        session = self.get_raw_session()
        try:
            return (
                session.query(WorkspaceAgentRoleEntity)
                .filter(WorkspaceAgentRoleEntity.workspace_id == workspace_id)
                .all()
            )
        finally:
            session.close()

    def upsert(
        self, agent_id: str, role: str, workspace_id: int
    ) -> WorkspaceAgentRoleEntity:
        """分配/更新角色(幂等)。"""
        session = self.get_raw_session()
        try:
            entity = (
                session.query(WorkspaceAgentRoleEntity)
                .filter(
                    WorkspaceAgentRoleEntity.agent_id == agent_id,
                    WorkspaceAgentRoleEntity.workspace_id == workspace_id,
                )
                .first()
            )
            if entity is None:
                entity = WorkspaceAgentRoleEntity(
                    agent_id=agent_id,
                    workspace_id=workspace_id,
                    role=role,
                )
                session.add(entity)
            else:
                entity.role = role
            session.commit()
            session.refresh(entity)
            return entity
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# --------------------------------------------------------------------------- #
# 服务
# --------------------------------------------------------------------------- #
class AgentRoleService(BaseService[WorkspaceAgentRoleEntity, Dict[str, Any], Dict[str, Any]]):
    """Agent 职能角色服务 —— 分配 / 查询 / 成熟度校验 / 团队装配。"""

    name = AGENT_ROLE_SERVICE_COMPONENT_NAME

    def __init__(
        self,
        system_app: SystemApp,
        config: ServeConfig,
        dao: Optional[WorkspaceAgentRoleDao] = None,
    ):
        self._system_app: Optional[SystemApp] = None
        self._serve_config: ServeConfig = config
        self._dao: WorkspaceAgentRoleDao = dao
        super().__init__(system_app)

    def init_app(self, system_app: SystemApp) -> None:
        super().init_app(system_app)
        self._dao = self._dao or WorkspaceAgentRoleDao()
        self._system_app = system_app

    @property
    def dao(self) -> WorkspaceAgentRoleDao:
        return self._dao

    @property
    def config(self) -> ServeConfig:
        return self._serve_config

    # ------------------------------------------------------------------ #
    # 角色分配 / 查询
    # ------------------------------------------------------------------ #
    def assign_role(
        self, agent_id: str, role: AgentRole, workspace_id: int
    ) -> AgentRoleAssignment:
        """分配角色给 agent(幂等 upsert)。"""
        entity = self._dao.upsert(
            agent_id=agent_id,
            role=role.value,
            workspace_id=workspace_id,
        )
        return AgentRoleAssignment(
            agent_id=entity.agent_id,
            role=AgentRole(entity.role),
            workspace_id=entity.workspace_id,
        )

    def get_role(
        self, agent_id: str, workspace_id: int
    ) -> Optional[AgentRole]:
        """查询 agent 在 workspace 中的角色,未分配返回 None。"""
        entity = self._dao.get_by_agent(agent_id, workspace_id)
        if entity is None:
            return None
        try:
            return AgentRole(entity.role)
        except ValueError:
            logger.warning(
                f"unknown agent role '{entity.role}' for agent={agent_id} "
                f"ws={workspace_id}"
            )
            return None

    # ------------------------------------------------------------------ #
    # 角色要求查询
    # ------------------------------------------------------------------ #
    def get_skills_for_role(self, role: AgentRole) -> List[str]:
        """获取角色需要的技能列表。"""
        req = ROLE_REQUIREMENTS.get(role) or {}
        return list(req.get("skills") or [])

    def get_role_prompt(self, role: AgentRole) -> str:
        """获取角色默认 prompt 模板。"""
        return _ROLE_PROMPT_TEMPLATES.get(role, "")

    # ------------------------------------------------------------------ #
    # 成熟度校验(联动 AgentMaturityService)
    # ------------------------------------------------------------------ #
    def validate_maturity(
        self, agent_id: str, role: AgentRole, workspace_id: int
    ) -> Dict[str, Any]:
        """校验 agent 成熟度是否满足角色要求。

        返回 {valid: bool, agent_stage: str, required: str, reason: str}。
        """
        required_min = (ROLE_REQUIREMENTS.get(role) or {}).get("maturity_min", "novice")
        try:
            required_stage = AgentStage(required_min)
        except ValueError:
            required_stage = AgentStage.NOVICE

        agent_stage = AgentStage.NOVICE
        if self._system_app is not None:
            try:
                maturity_service = self._system_app.get_component(
                    AGENT_MATURITY_SERVICE_COMPONENT_NAME,
                    AgentMaturityService,
                )
                maturity = maturity_service.get_maturity(agent_id, workspace_id)
                if maturity:
                    try:
                        agent_stage = AgentStage(maturity.get("stage") or "novice")
                    except ValueError:
                        agent_stage = AgentStage.NOVICE
            except Exception as e:
                logger.warning(
                    f"validate_maturity: get maturity failed for agent={agent_id}: {e}"
                )

        valid = _STAGE_RANK.get(agent_stage, 0) >= _STAGE_RANK.get(required_stage, 0)
        return {
            "valid": valid,
            "agent_stage": agent_stage.value,
            "required": required_stage.value,
            "reason": (
                ""
                if valid
                else f"agent stage {agent_stage.value} below required {required_stage.value}"
            ),
        }

    # ------------------------------------------------------------------ #
    # 团队装配(按 Playbook declaration 的 roles 块)
    # ------------------------------------------------------------------ #
    def assemble_team(
        self,
        playbook_declaration: Optional[Dict[str, Any]],
        workspace_id: int,
    ) -> List[Dict[str, Any]]:
        """根据 Playbook 声明的 roles 块装配团队蓝图。

        declaration.roles 结构:
            roles:
              fetcher:
                skills: [db_query]
                maturity_min: novice
              analyzer:
                skills: [anomaly_detect]
                maturity_min: proficient

        返回团队清单,每项含: role / skills / maturity_min / description / prompt。
        声明缺省时使用 ROLE_REQUIREMENTS 默认值;无 roles 块时返回 []。
        """
        if not playbook_declaration:
            return []
        roles_block = playbook_declaration.get("roles") or {}
        if not isinstance(roles_block, dict) or not roles_block:
            return []

        team: List[Dict[str, Any]] = []
        for role_key, role_decl in roles_block.items():
            try:
                role = AgentRole(role_key)
            except ValueError:
                logger.warning(
                    f"assemble_team: unknown role '{role_key}' in declaration, skip"
                )
                continue
            defaults = ROLE_REQUIREMENTS.get(role) or {}
            role_decl = role_decl if isinstance(role_decl, dict) else {}
            skills = list(role_decl.get("skills") or defaults.get("skills") or [])
            maturity_min = (
                role_decl.get("maturity_min") or defaults.get("maturity_min") or "novice"
            )
            description = role_decl.get("description") or defaults.get("description") or ""
            team.append({
                "role": role.value,
                "skills": skills,
                "maturity_min": maturity_min,
                "description": description,
                "prompt": self.get_role_prompt(role),
                "workspace_id": workspace_id,
            })
        return team
