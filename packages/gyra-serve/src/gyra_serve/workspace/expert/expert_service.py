"""专家团队组装服务：成员名册 + 外挂资源的查询与编排。

供运行时（scene_resource_assembler / expert_runtime）与 API 层复用：
- list_team：空间团队视图（成员行 + 外挂摘要）
- get_member / get_member_by_app_code：单个成员
- list_equipment：成员外挂明细行
- assemble_team_summary：Leader 上下文注入的团队清单文本
"""
import logging
from typing import Any, Dict, List, Optional

from .expert_models import (
    WorkspaceExpertDao,
    WorkspaceExpertEntity,
    WorkspaceExpertEquipmentDao,
    WorkspaceExpertEquipmentEntity,
)

logger = logging.getLogger(__name__)


class WorkspaceExpertService:
    def __init__(self) -> None:
        self._expert_dao = WorkspaceExpertDao()
        self._equipment_dao = WorkspaceExpertEquipmentDao()

    # ---------- 成员名册 ----------

    def upsert_member(
        self,
        workspace_id: int,
        app_code: str,
        role_hint: Optional[str] = None,
        default_contract_id: Optional[int] = None,
        is_active: bool = True,
        icon: Optional[str] = None,
    ) -> WorkspaceExpertEntity:
        """icon 语义：None=保持不变（缺省），''=清除覆盖回落全局，非空=设置空间覆盖。"""
        fields: Dict[str, Any] = {
            "role_hint": role_hint,
            "default_contract_id": default_contract_id,
            "is_active": is_active,
        }
        if icon is not None:
            fields["icon"] = icon or None
        return self._expert_dao.upsert(
            workspace_id=workspace_id,
            app_code=app_code,
            **fields,
        )

    def get_member(self, expert_id: int) -> Optional[WorkspaceExpertEntity]:
        session = self._expert_dao.get_raw_session()
        try:
            return (
                session.query(WorkspaceExpertEntity)
                .filter(WorkspaceExpertEntity.id == expert_id)
                .first()
            )
        finally:
            session.close()

    def get_member_by_app_code(
        self, workspace_id: int, app_code: str
    ) -> Optional[WorkspaceExpertEntity]:
        return self._expert_dao.get_by_app_code(workspace_id, app_code)

    def list_members(
        self, workspace_id: int, active_only: bool = True
    ) -> List[WorkspaceExpertEntity]:
        return self._expert_dao.list_by_workspace(workspace_id, active_only=active_only)

    # ---------- 外挂资源 ----------

    def upsert_equipment(
        self,
        expert_id: int,
        resource_type: str,
        resource_ref: str,
        config: Optional[Dict[str, Any]] = None,
        is_active: bool = True,
    ) -> WorkspaceExpertEquipmentEntity:
        return self._equipment_dao.upsert(
            expert_id=expert_id,
            resource_type=resource_type,
            resource_ref=resource_ref,
            config_json=(
                None
                if config is None
                else __import__("json").dumps(config, ensure_ascii=False)
            ),
            is_active=is_active,
        )

    def list_equipment(
        self, expert_id: int, active_only: bool = True
    ) -> List[WorkspaceExpertEquipmentEntity]:
        return self._equipment_dao.list_by_expert(expert_id, active_only=active_only)

    # ---------- 团队视图 ----------

    def list_team(self, workspace_id: int) -> List[Dict[str, Any]]:
        """团队视图：成员行 + 外挂摘要列表。"""
        members = self.list_members(workspace_id)
        team: List[Dict[str, Any]] = []
        for m in members:
            equipment = self.list_equipment(m.id)
            team.append(
                {
                    "id": m.id,
                    "app_code": m.app_code,
                    "role_hint": m.role_hint,
                    "default_contract_id": m.default_contract_id,
                    "equipment": [
                        {
                            "resource_type": e.resource_type,
                            "resource_ref": e.resource_ref,
                            "config": __import__("json").loads(e.config_json)
                            if e.config_json
                            else {},
                        }
                        for e in equipment
                    ],
                }
            )
        return team

    def assemble_team_summary(self, workspace_id: int) -> str:
        """Leader 上下文注入的团队清单文本(含标准协作方式引导)。"""
        team = self.list_team(workspace_id)
        if not team:
            return ""
        lines = [
            "【本空间专家团队】协作方式:用标准 SubAgent 工具(agent_id=下方专家 app_code;"
            "mode=sync 同步等待结果,mode=async 后台独立运行完成后自动回传);"
            "需要合约/交付物/任务台账跟踪的正式派单改用 start_task(app_code=专家)。",
        ]
        for member in team:
            equipment_tags = "、".join(
                f"{e['resource_type']}:{e['resource_ref']}" for e in member["equipment"]
            )
            line = f"- {member['app_code']}"
            if member.get("role_hint"):
                line += f"（{member['role_hint']}）"
            if equipment_tags:
                line += f" 外挂：{equipment_tags}"
            lines.append(line)
        return "\n".join(lines)
