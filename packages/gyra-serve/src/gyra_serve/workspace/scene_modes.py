"""场景空间模式 — 对应4种业务形态。

P2 任务11: 业务形态扩展。在原有"任务执行"模式之上,扩展为4种场景空间模式,
每种模式定义了可用的 agent 工具集、产出资产类型、lobby 展示组件等。

模式列表:
- task_execution        任务执行(已有,默认)
- decision_discussion   决策讨论
- knowledge_curation    知识梳理
- continuous_monitoring 持续监控
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from .models.models import WorkspaceDao, WorkspaceEntity

logger = logging.getLogger(__name__)


class SceneMode(str, Enum):
    """场景空间模式——对应4种业务形态"""

    TASK_EXECUTION = "task_execution"  # 任务执行(已有)
    DECISION_DISCUSSION = "decision_discussion"  # 决策讨论
    KNOWLEDGE_CURATION = "knowledge_curation"  # 知识梳理
    CONTINUOUS_MONITORING = "continuous_monitoring"  # 持续监控


@dataclass
class SceneModeConfig:
    """场景模式配置"""

    mode: SceneMode
    name: str
    description: str
    agent_tools: List[str]  # 该模式可用的agent工具集
    output_asset_types: List[str]  # 产出的资产类型
    lobby_component: str  # lobby展示组件名
    requires_playbook: bool  # 是否需要Playbook
    allows_inline: bool  # 是否允许inline执行


SCENE_MODE_CONFIGS: Dict[SceneMode, SceneModeConfig] = {
    SceneMode.TASK_EXECUTION: SceneModeConfig(
        mode=SceneMode.TASK_EXECUTION,
        name="任务执行",
        description="agent按Playbook执行任务,产出artifact和delivery",
        agent_tools=["create_artifact", "deliver_file", "create_delivery", "query_ecp"],
        output_asset_types=["historical_artifact", "case"],
        lobby_component="ArtifactsList",
        requires_playbook=True,
        allows_inline=False,  # 已移除内联任务:start_task 一律分离(异步)执行
    ),
    SceneMode.DECISION_DISCUSSION: SceneModeConfig(
        mode=SceneMode.DECISION_DISCUSSION,
        name="决策讨论",
        description="多人多agent讨论决策,产出decision_log",
        agent_tools=["propose_decision", "vote", "summarize_discussion"],
        output_asset_types=["decision_log"],
        lobby_component="DecisionTimeline",
        requires_playbook=False,
        allows_inline=False,
    ),
    SceneMode.KNOWLEDGE_CURATION: SceneModeConfig(
        mode=SceneMode.KNOWLEDGE_CURATION,
        name="知识梳理",
        description="梳理知识结构,产出ECP提案和pattern",
        agent_tools=["extract_entity", "propose_metric", "merge_pattern"],
        output_asset_types=["pattern"],
        lobby_component="KnowledgeGraph",
        requires_playbook=False,
        allows_inline=False,
    ),
    SceneMode.CONTINUOUS_MONITORING: SceneModeConfig(
        mode=SceneMode.CONTINUOUS_MONITORING,
        name="持续监控",
        description="订阅数据源,持续监控并告警",
        agent_tools=["subscribe_source", "detect_anomaly", "send_alert"],
        output_asset_types=["historical_artifact"],
        lobby_component="MonitoringDashboard",
        requires_playbook=True,
        allows_inline=False,
    ),
}


class SceneModeService:
    """场景模式服务:读写 workspace 的 scene_mode,并提供模式相关的校验。

    直接复用 WorkspaceDao 的 raw session 读写 scene_mode 字段,
    避免侵入 WorkspaceService 的 CRUD 链路。workspace 未设置 scene_mode
    (含历史数据 NULL)时统一回落到默认 task_execution。
    """

    def __init__(self, dao: Optional[WorkspaceDao] = None):
        self._dao: WorkspaceDao = dao or WorkspaceDao()

    @staticmethod
    def get_config(mode: SceneMode) -> SceneModeConfig:
        """获取模式配置。"""
        if mode not in SCENE_MODE_CONFIGS:
            raise ValueError(f"unknown scene mode: {mode}")
        return SCENE_MODE_CONFIGS[mode]

    @classmethod
    def list_configs(cls) -> List[SceneModeConfig]:
        """列出所有可用模式配置(按枚举定义顺序)。"""
        return [SCENE_MODE_CONFIGS[m] for m in SceneMode]

    def get_mode(self, workspace_id: int) -> SceneMode:
        """获取 workspace 的模式,未设置则返回默认 task_execution。"""
        session = self._dao.get_raw_session()
        try:
            entity = (
                session.query(WorkspaceEntity)
                .filter(WorkspaceEntity.id == workspace_id)
                .first()
            )
            if not entity:
                raise ValueError(f"workspace {workspace_id} not found")
            raw = entity.scene_mode or SceneMode.TASK_EXECUTION.value
            try:
                return SceneMode(raw)
            except ValueError:
                # 兼容历史脏数据:未知值回落到默认
                logger.warning(
                    f"workspace {workspace_id} has unknown scene_mode '{raw}', "
                    f"fallback to task_execution"
                )
                return SceneMode.TASK_EXECUTION
        finally:
            session.close()

    def set_mode(self, workspace_id: int, mode: SceneMode) -> SceneMode:
        """设置 workspace 的模式。"""
        if not isinstance(mode, SceneMode):
            try:
                mode = SceneMode(mode)
            except ValueError:
                raise ValueError(f"unknown scene mode: {mode}")
        session = self._dao.get_raw_session()
        try:
            entity = (
                session.query(WorkspaceEntity)
                .filter(WorkspaceEntity.id == workspace_id)
                .first()
            )
            if not entity:
                raise ValueError(f"workspace {workspace_id} not found")
            entity.scene_mode = mode.value
            session.commit()
            return mode
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_allowed_tools(self, workspace_id: int) -> List[str]:
        """获取 workspace 当前模式可用的 agent 工具集。"""
        mode = self.get_mode(workspace_id)
        return list(self.get_config(mode).agent_tools)

    def validate_output(self, workspace_id: int, asset_type: str) -> bool:
        """校验产出资产类型是否匹配当前模式。"""
        mode = self.get_mode(workspace_id)
        allowed = self.get_config(mode).output_asset_types
        return asset_type in allowed
