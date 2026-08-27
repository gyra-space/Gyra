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
]
