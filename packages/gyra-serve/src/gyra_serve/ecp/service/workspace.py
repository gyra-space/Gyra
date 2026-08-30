"""ECP 工作空间治理:软层 space 供给、提案 Agent 绑定、workspace 配置。

WorkspaceOps 是无状态协作者,经 svc 门面访问 DAO 与 system_app。
"""

import logging
from typing import Any, Optional

from ..api.schemas import SpaceInfoVO, WorkspaceConfigVO
from ..config import DEFAULT_PROPOSAL_AGENT_APP_CODE

logger = logging.getLogger(__name__)


class WorkspaceOps:
    """工作空间治理协作者(无状态;经 svc 门面访问 DAO 与 system_app)。"""

    def __init__(self, svc: Any):
        self._svc = svc

    # ------------------------------------------------------------- ECP space
    async def get_or_create_space(
        self, workspace_id: Optional[str] = None, owner_id: Optional[str] = None
    ) -> SpaceInfoVO:
        """Get-or-create the ECP soft-layer knowledge space for a workspace.

        The soft layer IS a knowledge space (llm-wiki); ECP only customizes
        its schema.md (P3). Slug convention: ecp-<workspace_id>.
        """
        svc = self._svc
        ws = svc._ws(workspace_id)
        slug = f"ecp-{ws}"
        from gyra_serve.knowledge.config import (
            SERVE_SERVICE_COMPONENT_NAME as KNOWLEDGE_SERVICE,
        )
        from gyra_serve.knowledge.service.service import Service as KnowledgeService

        ks = svc._system_app.get_component(KNOWLEDGE_SERVICE, KnowledgeService)
        created = False
        try:
            await ks.get_space_config(slug)
        except Exception:  # noqa: BLE001
            await ks.create_space(slug, owner_id=owner_id, space_type="personal")
            created = True
            svc._oplog_dao.append("space_create", ws, {"slug": slug})
        svc._asset_dao.register("space", slug, ws, ref_meta={"name": slug})
        # 经 svc 门面调用(跨协作者调用走门面,保持 Service 级钩子/ patch 点有效)
        svc._ensure_default_proposal_agent(ws)
        return SpaceInfoVO(slug=slug, workspace_id=ws, created=created)

    def ensure_default_proposal_agent(self, workspace_id: str) -> None:
        """Seed the default proposal agent binding for a workspace.

        New workspaces start with an empty ``proposal_agent_id``, which forces
        users to hand-build an app in the agent editor before ECP proposals
        work. Bind the built-in ``ecp-proposal-agent`` app (seeded & published
        at startup from gyra_app_define) so the flow works out of the box.
        Idempotent: any existing binding (e.g. user-configured) is kept.
        Best-effort: failures never block space access.
        """
        svc = self._svc
        try:
            config = svc._ws_config_dao.get(workspace_id)
            if config.proposal_agent_id:
                return
            svc._ws_config_dao.upsert(workspace_id, DEFAULT_PROPOSAL_AGENT_APP_CODE)
            logger.info(
                "workspace %s: bound default proposal agent %s",
                workspace_id,
                DEFAULT_PROPOSAL_AGENT_APP_CODE,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "bind default proposal agent for workspace %s failed: %s",
                workspace_id,
                e,
            )

    # ------------------------------------------------------ workspace config
    def get_config(
        self, workspace_id: Optional[str] = None
    ) -> WorkspaceConfigVO:
        svc = self._svc
        return svc._ws_config_dao.get(svc._ws(workspace_id))

    def save_config(
        self,
        workspace_id: Optional[str] = None,
        proposal_agent_id: Optional[str] = None,
    ) -> WorkspaceConfigVO:
        svc = self._svc
        ws = svc._ws(workspace_id)
        vo = svc._ws_config_dao.upsert(ws, proposal_agent_id)
        svc._oplog_dao.append(
            "config_update", ws, {"proposal_agent_id": proposal_agent_id}
        )
        return vo
