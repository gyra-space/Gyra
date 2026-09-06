"""Import all models to make sure they are registered with SQLAlchemy."""

from gyra.model.streaming.db_models import StreamingToolConfig
from gyra.storage.chat_history.chat_history_db import (
    ChatHistoryEntity,
    ChatHistoryMessageEntity,
)
from gyra_app.openapi.api_v1.feedback.feed_back_db import ChatFeedBackEntity
from gyra_serve.agent.app.recommend_question.recommend_question import (
    RecommendQuestionEntity,
)
from gyra_serve.channel.models import ChannelEntity

from gyra_serve.datasource.manages.connect_config_db import ConnectConfigEntity
from gyra_serve.file.models.models import ServeEntity as FileServeEntity
from gyra_serve.flow.models.models import ServeEntity as FlowServeEntity
from gyra_serve.flow.models.models import VariablesEntity as FlowVariableEntity
from gyra_serve.prompt.models.models import ServeEntity as PromptManageEntity
# TODO: rewire to new knowledge module (Task #9)
# Old rag DB models (DocumentChunkEntity, KnowledgeDocumentEntity, KnowledgeSpaceEntity)
# were removed along with gyra_serve.rag. New knowledge module will register its own.
from gyra_serve.config.models.models import ServeEntity as ConfigServeEntity
from gyra_serve.building.app.models.models import ServeEntity as AppServeEntity
from gyra_serve.building.app.models.models_details import AppDetailServeEntity
from gyra_serve.building.config.models.models import (
    ServeEntity as AppConfigServeEntity,
)
from gyra_serve.mcp.models.models import ServeEntity as MCPServeEntity
from gyra_serve.channel.models.models import ChannelEntity
from gyra_app.auth.user_service import UserEntity
from gyra_app.config_storage.oauth2_db_storage import OAuth2ConfigEntity
from gyra_app.feature_plugins.user_groups.models import (
    UserGroupEntity,
    UserGroupMemberEntity,
)
from gyra_app.feature_plugins.permissions.models import (
    RoleEntity,
    RolePermissionEntity,
    UserRoleEntity,
    GroupRoleEntity,
    PermissionDefinitionEntity,
    RolePermissionDefEntity,
)
from gyra_app.feature_plugins.system_config_model import SystemConfigEntity
from gyra_serve.ecp.models.models import (
    EcpAssetRefEntity,
    EcpConfirmerEntity,
    EcpMissLearnEntity,
    EcpOpLogEntity,
    EcpResolutionCacheEntity,
    EcpSemanticEdgeEntity,
    EcpSemanticObjectEntity,
    EcpWorkspaceConfigEntity,
)

from gyra_serve.app_card.models.models import AppCardEntity, AppCardVersionEntity

from gyra_serve.workspace.models.models import (
    WorkspaceConversationLinkEntity,
    WorkspaceEntity,
    WorkspaceMemberEntity,
    WorkspaceResourceEntity,
)
from gyra_serve.workspace.expert.expert_models import (
    WorkspaceExpertEntity,
    WorkspaceExpertEquipmentEntity,
)
from gyra_serve.workspace.agent_roles import WorkspaceAgentRoleEntity
from gyra_serve.workspace.inbox.models import InboxItemEntity
from gyra_serve.workspace.agent_maturity.models import AgentMaturityEntity

from gyra_serve.task.models.models import TaskEntity, TaskRelationEntity
from gyra_serve.artifact.models.models import ArtifactEntity, ArtifactVersionEntity
from gyra_serve.playbook.models.models import PlaybookEntity, PlaybookVersionEntity
from gyra_serve.playbook.trace.models import (
    PlaybookEvolutionProposalEntity,
    PlaybookTraceEntity,
)
from gyra_serve.delivery.models.models import DeliveryEntity
from gyra_serve.intervention.models.models import InterventionEntity
from gyra_serve.trigger.models.models import TriggerSourceEntity
from gyra_serve.skill.models.models import SkillEntity
from gyra_serve.skill.models.skill_sync_task_db import SkillSyncTaskEntity
from gyra_serve.workspace_asset.models.models import (
    AssetEntity,
    AssetMaturityLogEntity,
    AssetVersionEntity,
    TaskAssetLinkEntity,
)
from gyra_serve.workspace_asset.service.index_service import AssetIndexEntity
from gyra_serve.cron.models.models import CronJobEntity, CronJobLogEntity
from gyra_serve.job.models.models import JobEntity
from gyra_serve.usage.models.models import LLMUsageEntity
from gyra_serve.gyras.hub.models.models import ServeEntity as GyrasHubServeEntity
from gyra_serve.gyras.my.models.models import ServeEntity as GyrasMyServeEntity
from gyra_serve.app_card.store.models import AppCardKvEntity, AppCardRecordEntity
from gyra_serve.evaluate.models.models import ServeEntity as EvaluateServeEntity
from gyra_serve.sql_guard.masking.config_db import SensitiveColumnEntity
from gyra_serve.datasource.manages.db_spec_db import DbSpecEntity
from gyra_serve.datasource.manages.table_spec_db import TableSpecEntity
from gyra_serve.datasource.manages.learning_task_db import DbLearningTaskEntity
from gyra_serve.datasource.manages.learning_subtask_db import DbLearningSubtaskEntity
from gyra_serve.agent.db.async_task_db import AsyncTaskEntity
from gyra_serve.agent.db.gpts_conversations_db import GptsConversationsEntity
from gyra_serve.agent.db.gpts_messages_db import GptsMessagesEntity
from gyra_serve.agent.db.gpts_messages_system_db import GptsMessagesSystemEntity
from gyra_serve.agent.db.gpts_plans_db import GptsPlansEntity
from gyra_serve.agent.db.gpts_todos_db import GptsTodoEntity
from gyra_serve.agent.db.gpts_kanban_db import (
    GptsKanbanEntity,
    GptsPreKanbanLogEntity,
)
from gyra_serve.agent.db.gpts_worklog_db import GptsWorkLogEntity
from gyra_serve.agent.db.gpts_tool import GptsToolDetailEntity, GptsToolEntity
from gyra_serve.agent.db.gpts_tool_messages import GptsToolMessagesEntity
from gyra_serve.agent.db.gpts_cold_segment_db import GptsColdSegmentEntity
from gyra_serve.agent.db.gpts_file_metadata_db import (
    GptsFileCatalogEntity,
    GptsFileMetadataEntity,
)
from gyra_serve.agent.db.gpts_app import UserRecentAppsEntity
from gyra_serve.agent.db.authorization_audit_db import AuthorizationAuditLogEntity

_MODELS = [
    FileServeEntity,
    PromptManageEntity,
    # TODO: rewire to new knowledge module (Task #9)
    # KnowledgeSpaceEntity,
    # KnowledgeDocumentEntity,
    # DocumentChunkEntity,
    ChatFeedBackEntity,
    ConnectConfigEntity,
    ChatHistoryEntity,
    ChatHistoryMessageEntity,
    FlowServeEntity,
    RecommendQuestionEntity,
    FlowVariableEntity,
    ConfigServeEntity,
    AppServeEntity,
    AppDetailServeEntity,
    AppConfigServeEntity,
    MCPServeEntity,
    ChannelEntity,
    StreamingToolConfig,
    UserEntity,
    UserGroupEntity,
    UserGroupMemberEntity,
    OAuth2ConfigEntity,
    RoleEntity,
    RolePermissionEntity,
    UserRoleEntity,
    GroupRoleEntity,
    PermissionDefinitionEntity,
    RolePermissionDefEntity,
    SystemConfigEntity,
    EcpSemanticObjectEntity,
    EcpResolutionCacheEntity,
    EcpSemanticEdgeEntity,
    EcpConfirmerEntity,
    EcpOpLogEntity,
    EcpAssetRefEntity,
    EcpWorkspaceConfigEntity,
    EcpMissLearnEntity,
    AppCardEntity,
    AppCardVersionEntity,
    WorkspaceEntity,
    WorkspaceMemberEntity,
    WorkspaceResourceEntity,
    WorkspaceConversationLinkEntity,
    WorkspaceExpertEntity,
    WorkspaceExpertEquipmentEntity,
    WorkspaceAgentRoleEntity,
    InboxItemEntity,
    AgentMaturityEntity,
    TaskEntity,
    TaskRelationEntity,
    ArtifactEntity,
    ArtifactVersionEntity,
    PlaybookEntity,
    PlaybookVersionEntity,
    PlaybookTraceEntity,
    PlaybookEvolutionProposalEntity,
    DeliveryEntity,
    InterventionEntity,
    TriggerSourceEntity,
    SkillEntity,
    SkillSyncTaskEntity,
    AssetEntity,
    AssetVersionEntity,
    AssetMaturityLogEntity,
    TaskAssetLinkEntity,
    AssetIndexEntity,
    CronJobEntity,
    CronJobLogEntity,
    JobEntity,
    LLMUsageEntity,
    GyrasHubServeEntity,
    GyrasMyServeEntity,
    AppCardRecordEntity,
    AppCardKvEntity,
    EvaluateServeEntity,
    SensitiveColumnEntity,
    DbSpecEntity,
    TableSpecEntity,
    DbLearningTaskEntity,
    DbLearningSubtaskEntity,
    AsyncTaskEntity,
    GptsConversationsEntity,
    GptsMessagesEntity,
    GptsMessagesSystemEntity,
    GptsPlansEntity,
    GptsTodoEntity,
    GptsKanbanEntity,
    GptsPreKanbanLogEntity,
    GptsWorkLogEntity,
    GptsToolEntity,
    GptsToolDetailEntity,
    GptsToolMessagesEntity,
    GptsColdSegmentEntity,
    GptsFileMetadataEntity,
    GptsFileCatalogEntity,
    UserRecentAppsEntity,
    AuthorizationAuditLogEntity,
]
