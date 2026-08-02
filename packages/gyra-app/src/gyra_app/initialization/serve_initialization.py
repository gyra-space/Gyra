from typing import TYPE_CHECKING, Dict, Optional, Type, TypeVar

import gyra_serve.datasource.serve
from gyra.component import SystemApp
from gyra_app.config import ApplicationConfig

if TYPE_CHECKING:
    from gyra_serve.core import BaseServeConfig

T = TypeVar("T", bound="BaseServeConfig")


def scan_serve_configs():
    """Scan serve configs."""
    from gyra.util.module_utils import ModelScanner, ScannerConfig
    from gyra_serve.core import BaseServeConfig

    modules = [
        "gyra_serve.agent.chat",
        "gyra_serve.conversation",
        "gyra_serve.cron",
        "gyra_serve.datasource",
        "gyra_serve.gyras.hub",
        "gyra_serve.gyras.my",
        "gyra_serve.evaluate",
        "gyra_serve.feedback",
        "gyra_serve.file",
        "gyra_serve.flow",
        "gyra_serve.mcp",
        "gyra_serve.multimodal",
        "gyra_serve.prompt",
        "gyra_serve.skill",
        "gyra_serve.workspace",
        "gyra_serve.task",
        "gyra_serve.playbook",
        "gyra_serve.artifact",
        "gyra_serve.workspace_asset",
        "gyra_serve.delivery",
        "gyra_serve.intervention",
        "gyra_serve.trigger",
        # TODO: rewire to new knowledge module (Task #9)
        # "gyra_serve.rag",
        "gyra_serve.building.app",
        "gyra_serve.building.config",
        "gyra_serve.building.recommend_question",
        "gyra_serve.asset",
        "gyra_serve.config",
        "gyra_serve.version",
        "gyra_serve.channel",
        "gyra_serve.usage",
        "gyra_serve.ecp",
    ]

    scanner = ModelScanner[BaseServeConfig]()
    registered_items = {}
    for module in modules:
        config = ScannerConfig(
            module_path=module,
            base_class=BaseServeConfig,
            specific_files=["config"],
        )
        items = scanner.scan_and_register(config)
        registered_items[module] = items
    return registered_items


def get_config(
    serve_configs: Dict[str, T], serve_name: str, config_type: Type[T], **default_config
) -> T:
    """
    Get serve config with specific type

    Args:
        serve_configs: Dictionary of serve configs
        serve_name: Name of the serve config to get
        config_type: The specific config type to return
        **default_config: Default values for config attributes

    Returns:
        Config instance of type T
    """
    if hasattr(config_type, "__type__"):
        # Use the type name as the serve name
        serve_name = config_type.__type__

    config = serve_configs.get(serve_name)
    if not config:
        config = config_type(**default_config)
    else:
        if default_config:
            for k, v in default_config.items():
                if hasattr(config, k) and getattr(config, k) is None:
                    setattr(config, k, v)
    return config


def register_serve_apps(
    system_app: SystemApp,
    app_config: ApplicationConfig,
    webserver_host: str,
    webserver_port: int,
):
    """Register serve apps"""
    serve_configs = {s.get_type_value(): s for s in app_config.serves}

    system_app.config.set("gyra.app.global.language", app_config.system.language)
    global_api_keys: Optional[str] = None
    if app_config.system.api_keys:
        global_api_keys = ",".join(app_config.system.api_keys)
        system_app.config.set("gyra.app.global.api_keys", global_api_keys)
    if app_config.system.encrypt_key:
        system_app.config.set(
            "gyra.app.global.encrypt_key", app_config.system.encrypt_key
        )

    # ################################ Prompt Serve Register Begin ####################
    from gyra_serve.prompt.serve import (
        Serve as PromptServe,
    )

    # Register serve app
    system_app.register(
        PromptServe,
        api_prefix="/prompt",
        config=get_config(
            serve_configs,
            PromptServe.name,
            gyra_serve.prompt.serve.ServeConfig,
            default_user="gyra",
            default_sys_code="gyra",
            api_keys=global_api_keys,
        ),
    )
    # ################################ Prompt Serve Register End ######################

    # ################################ Conversation Serve Register Begin ##############
    from gyra_serve.conversation.serve import Serve as ConversationServe

    # Register serve app
    system_app.register(
        ConversationServe,
        api_prefix="/api/v1/chat/dialogue",
        config=get_config(
            serve_configs,
            ConversationServe.name,
            gyra_serve.conversation.serve.ServeConfig,
            default_model=app_config.models.default_llm,
            api_keys=global_api_keys,
        ),
    )
    # ################################ Conversation Serve Register End ################

    # AWEL暂未使用 暂时注掉
    # # ################################ AWEL Flow Serve Register Begin #################
    # from gyra_serve.flow.serve import Serve as FlowServe
    #
    # # Register serve app
    # system_app.register(
    #     FlowServe,
    #     config=get_config(
    #         serve_configs,
    #         FlowServe.name,
    #         gyra_serve.flow.serve.ServeConfig,
    #         encrypt_key=app_config.system.encrypt_key,
    #         api_keys=global_api_keys,
    #     ),
    # )
    #
    # # ################################ AWEL Flow Serve Register End ###################

    # ################################ Rag Serve Register Begin #######################
    # TODO: rewire to new knowledge module (Task #9)
    # Old RagServe module was physically removed along with gyra_serve.rag.
    # The new knowledge module will be re-registered here once it ships a Serve.
    #
    # from gyra_serve.rag.serve import Serve as RagServe
    #
    # rag_config = app_config.rag
    # llm_configs = app_config.models
    #
    # # Register serve app
    # system_app.register(
    #     RagServe,
    #     config=get_config(
    #         serve_configs,
    #         RagServe.name,
    #         gyra_serve.rag.serve.ServeConfig,
    #         embedding_model=llm_configs.default_embedding,
    #         rerank_model=llm_configs.default_reranker,
    #         chunk_size=rag_config.chunk_size,
    #         chunk_overlap=rag_config.chunk_overlap,
    #         similarity_top_k=rag_config.similarity_top_k,
    #         query_rewrite=rag_config.query_rewrite,
    #         max_chunks_once_load=rag_config.max_chunks_once_load,
    #         max_threads=rag_config.max_threads,
    #         rerank_top_k=rag_config.rerank_top_k,
    #         api_keys=global_api_keys,
    #     ),
    # )

    # ################################ Rag Serve Register End #########################

    # ################################ Datasource Serve Register Begin ################

    from gyra_serve.datasource.serve import Serve as DatasourceServe

    # Register serve app
    system_app.register(
        DatasourceServe,
        config=get_config(
            serve_configs,
            DatasourceServe.name,
            gyra_serve.datasource.serve.ServeConfig,
            api_keys=global_api_keys,
        ),
    )

    # ################################ Datasource Serve Register End ##################

    # ################################ Chat Feedback Serve Register End ###############
    from gyra_serve.feedback.serve import Serve as FeedbackServe

    # Register serve feedback
    system_app.register(
        FeedbackServe,
        config=get_config(
            serve_configs,
            FeedbackServe.name,
            gyra_serve.feedback.serve.ServeConfig,
            api_keys=global_api_keys,
        ),
    )
    # ################################ Chat Feedback Register End #####################

    # ################################ gyras Register Begin ##########################
    # Register serve gyrashub
    from gyra_serve.gyras.hub.serve import Serve as gyrasHubServe

    system_app.register(
        gyrasHubServe,
        config=get_config(
            serve_configs,
            gyrasHubServe.name,
            gyra_serve.gyras.hub.serve.ServeConfig,
            api_keys=global_api_keys,
        ),
    )
    # Register serve gyrasmy
    from gyra_serve.gyras.my.serve import Serve as gyrasMyServe

    system_app.register(
        gyrasMyServe,
        config=get_config(
            serve_configs,
            gyrasMyServe.name,
            gyra_serve.gyras.my.serve.ServeConfig,
            api_keys=global_api_keys,
        ),
    )
    # ################################ gyras Register End ############################

    # ################################ File Serve Register Begin ######################

    from gyra.configs.model_config import FILE_SERVER_LOCAL_STORAGE_PATH
    from gyra_serve.file.serve import Serve as FileServe

    local_storage_path = f"{FILE_SERVER_LOCAL_STORAGE_PATH}_{webserver_port}"
    # Register serve app
    system_app.register(
        FileServe,
        config=get_config(
            serve_configs,
            FileServe.name,
            gyra_serve.file.serve.ServeConfig,
            host=webserver_host,
            port=webserver_port,
            local_storage_path=local_storage_path,
            api_keys=global_api_keys,
        ),
    )

    # ################################ File Serve Register End ########################

    # ################################ Knowledge Serve Register Begin ##################
    from gyra_serve.knowledge.serve import Serve as KnowledgeServe

    system_app.register(
        KnowledgeServe,
        config=get_config(
            serve_configs,
            KnowledgeServe.name,
            gyra_serve.knowledge.serve.ServeConfig,
            api_keys=global_api_keys,
        ),
    )

    # ################################ Knowledge Serve Register End ####################

    # ################################ Multimodal Serve Register Begin ##############
    from gyra_serve.multimodal.serve import Serve as MultimodalServe

    # Register serve app
    system_app.register(
        MultimodalServe,
        config=get_config(
            serve_configs,
            MultimodalServe.name,
            gyra_serve.multimodal.serve.ServeConfig,
            api_keys=global_api_keys,
        ),
    )
    # ################################ Multimodal Serve Register End ################

    # ################################ Evaluate Serve Register Begin ##################
    from gyra_serve.evaluate.serve import Serve as EvaluateServe

    rag_config = app_config.rag
    llm_configs = app_config.models
    # Register serve Evaluate
    system_app.register(
        EvaluateServe,
        config=get_config(
            serve_configs,
            EvaluateServe.name,
            gyra_serve.evaluate.serve.ServeConfig,
            embedding_model=llm_configs.default_embedding,
            similarity_top_k=rag_config.similarity_top_k,
            api_keys=global_api_keys,
        ),
    )
    # ################################ Evaluate Serve Register End ####################

    # ################################ Model Serve Removed ###########################
    # Old cluster-based model serve module was physically removed.
    # New model management only handles AgentLLM provider configuration.
    # ################################ Model Serve Removed ###########################

    # ################################ App Building Serve Register Begin #####################
    from gyra_serve.building.app.serve import Serve as AppServe
    from gyra_serve.building.config.serve import Serve as AppConfigServe
    from gyra_serve.building.recommend_question.serve import (
        Serve as RecommendQuestionServe,
    )

    # Register serve model
    system_app.register(
        AppServe,
        config=get_config(
            serve_configs,
            AppServe.name,
            gyra_serve.building.app.serve.ServeConfig,
            api_keys=global_api_keys,
        ),
    )
    system_app.register(
        AppConfigServe,
        config=get_config(
            serve_configs,
            AppConfigServe.name,
            gyra_serve.building.config.serve.ServeConfig,
            api_keys=global_api_keys,
        ),
    )
    system_app.register(
        RecommendQuestionServe,
        config=get_config(
            serve_configs,
            RecommendQuestionServe.name,
            gyra_serve.building.recommend_question.serve.ServeConfig,
            api_keys=global_api_keys,
        ),
    )
    # ################################ App Building Serve Register End #####################

    # ################################ Datasource Serve Register Begin ################

    from gyra_serve.asset.serve import Serve as AssetServe

    # Register serve app
    system_app.register(
        AssetServe,
        config=get_config(
            serve_configs,
            AssetServe.name,
            gyra_serve.asset.serve.ServeConfig,
            api_keys=global_api_keys,
        ),
    )

    # ################################ Config Serve Register Begin ################
    from gyra_serve.config.serve import Serve as ConfigServe

    system_app.register(
        ConfigServe,
        config=get_config(
            serve_configs,
            ConfigServe.name,
            gyra_serve.config.serve.ServeConfig,
            api_keys=global_api_keys,
        ),
    )

    # ################################ Config Serve Register End   ################

    # ################################ MCP Serve Register Begin ################
    from gyra_serve.mcp.serve import Serve as McpServe

    system_app.register(
        McpServe,
        config=get_config(
            serve_configs,
            McpServe.name,
            gyra_serve.mcp.serve.ServeConfig,
            api_keys=global_api_keys,
        ),
    )

    # ################################ MCP Serve Register End   ################

    # ################################ Skill Serve Register Begin ################
    from gyra_serve.skill.serve import Serve as SkillServe

    system_app.register(
        SkillServe,
        config=get_config(
            serve_configs,
            SkillServe.name,
            gyra_serve.skill.serve.ServeConfig,
            api_keys=global_api_keys,
        ),
    )

    # ################################ Skill Serve Register End   ################

    # ################################ Workspace Serve Register Begin ################
    from gyra_serve.workspace.serve import Serve as WorkspaceServe

    system_app.register(
        WorkspaceServe,
        config=get_config(
            serve_configs,
            WorkspaceServe.name,
            gyra_serve.workspace.serve.ServeConfig,
            api_keys=global_api_keys,
        ),
    )

    # ################################ Workspace Serve Register End   ################

    # ################################ Task Serve Register Begin ################
    from gyra_serve.task.serve import Serve as TaskServe

    system_app.register(
        TaskServe,
        config=get_config(
            serve_configs,
            TaskServe.name,
            gyra_serve.task.serve.ServeConfig,
            api_keys=global_api_keys,
        ),
    )

    # ################################ Task Serve Register End   ################

    # ################################ Playbook Serve Register Begin ################
    from gyra_serve.playbook.serve import Serve as PlaybookServe

    system_app.register(
        PlaybookServe,
        config=get_config(
            serve_configs,
            PlaybookServe.name,
            gyra_serve.playbook.serve.ServeConfig,
            api_keys=global_api_keys,
        ),
    )

    # ################################ Playbook Serve Register End   ################

    # ################################ Artifact Serve Register Begin ################
    from gyra_serve.artifact.serve import Serve as ArtifactServe

    system_app.register(
        ArtifactServe,
        config=get_config(
            serve_configs,
            ArtifactServe.name,
            gyra_serve.artifact.serve.ServeConfig,
            api_keys=global_api_keys,
        ),
    )

    # ################################ Artifact Serve Register End   ################

    # ################################ WorkspaceAsset Serve Register Begin ################
    from gyra_serve.workspace_asset.serve import Serve as WorkspaceAssetServe

    system_app.register(
        WorkspaceAssetServe,
        config=get_config(
            serve_configs,
            WorkspaceAssetServe.name,
            gyra_serve.workspace_asset.serve.ServeConfig,
            api_keys=global_api_keys,
        ),
    )

    # ################################ WorkspaceAsset Serve Register End   ################

    # ################################ Delivery Serve Register Begin ################
    from gyra_serve.delivery.serve import Serve as DeliveryServe

    system_app.register(
        DeliveryServe,
        config=get_config(
            serve_configs,
            DeliveryServe.name,
            gyra_serve.delivery.serve.ServeConfig,
            api_keys=global_api_keys,
        ),
    )

    # ################################ Delivery Serve Register End   ################

    # ################################ Intervention Serve Register Begin ################
    from gyra_serve.intervention.serve import Serve as InterventionServe

    system_app.register(
        InterventionServe,
        config=get_config(
            serve_configs,
            InterventionServe.name,
            gyra_serve.intervention.serve.ServeConfig,
            api_keys=global_api_keys,
        ),
    )

    # ################################ Intervention Serve Register End   ################

    # ################################ Trigger Serve Register Begin ################
    from gyra_serve.trigger.serve import Serve as TriggerServe

    system_app.register(
        TriggerServe,
        config=get_config(
            serve_configs,
            TriggerServe.name,
            gyra_serve.trigger.serve.ServeConfig,
            api_keys=global_api_keys,
        ),
    )

    # ################################ Trigger Serve Register End   ################

    # ################################ Version Serve Register Begin ####################
    from gyra_serve.version.serve import Serve as VersionServe

    system_app.register(
        VersionServe,
        api_prefix="/api/v1/version",
        config=get_config(
            serve_configs,
            VersionServe.name,
            gyra_serve.version.serve.ServeConfig,
        ),
    )
    # ################################ Version Serve Register End ######################

    # ################################ Cron Serve Register Begin ################
    from gyra_serve.cron.serve import Serve as CronServe

    system_app.register(
        CronServe,
        config=get_config(
            serve_configs,
            CronServe.name,
            gyra_serve.cron.serve.ServeConfig,
            api_keys=global_api_keys,
        ),
    )

    # ################################ Cron Serve Register End   ################

    # ################################ Usage Serve Register Begin ################
    from gyra_serve.usage.serve import Serve as UsageServe

    system_app.register(
        UsageServe,
        config=get_config(
            serve_configs,
            UsageServe.name,
            gyra_serve.usage.serve.ServeConfig,
            api_keys=global_api_keys,
        ),
    )
    # ################################ Usage Serve Register End   ################

    # ################################ ECP Serve Register Begin ################
    from gyra_serve.ecp.serve import Serve as EcpServe

    system_app.register(
        EcpServe,
        config=get_config(
            serve_configs,
            EcpServe.name,
            gyra_serve.ecp.serve.ServeConfig,
            api_keys=global_api_keys,
        ),
    )
    # ################################ ECP Serve Register End   ################

    # ################################ Channel Serve Register Begin ################
    from gyra_serve.channel.serve import Serve as ChannelServe

    system_app.register(
        ChannelServe,
        config=get_config(
            serve_configs,
            ChannelServe.name,
            gyra_serve.channel.serve.ServeConfig,
            api_keys=global_api_keys,
        ),
    )

    # ################################ Channel Serve Register End   ################

    # ################################ Scene Serve Register Begin ################
    from gyra_serve.scene.serve import Serve as SceneServe

    system_app.register(
        SceneServe,
        config=get_config(
            serve_configs,
            SceneServe.name,
            gyra_serve.scene.serve.ServeConfig,
            api_keys=global_api_keys,
        ),
    )

    # ################################ Scene Serve Register End   ################

    # ################################ Streaming Config Serve Register Begin ################
    from gyra_serve.streaming.serve import Serve as StreamingConfigServe

    system_app.register(
        StreamingConfigServe,
        config=get_config(
            serve_configs,
            StreamingConfigServe.name,
            gyra_serve.streaming.serve.ServeConfig,
            api_keys=global_api_keys,
        ),
    )

    # ################################ Streaming Config Serve Register End   ################
