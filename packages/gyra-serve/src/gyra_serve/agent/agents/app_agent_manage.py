import json
import logging
import uuid
from abc import ABC
from typing import List, Type, Optional

from gyra._private.config import Config
from gyra.agent import (
    AgentContext,
    AgentMemory,
    ConversableAgent,
    GptsMemory,
    LLMConfig,
    UserProxyAgent,
    get_agent_manager,
)
from gyra.agent.core.base_team import ManagerAgent
from gyra.agent.core.plan.react.team_react_plan import AutoTeamContext
from gyra.agent.resource import get_resource_manager
from gyra.agent.util.llm.llm import LLMStrategyType
from gyra.component import BaseComponent, ComponentType, SystemApp
from gyra.core import LLMClient, PromptTemplate
from gyra_serve.core import blocking_func_to_async
from gyra_serve.prompt.api.endpoints import get_service

from ..db import GptsMessagesDao

from ..db.gpts_conversations_db import GptsConversationsDao
from ..team.base import TeamMode
from .gyras_memory import MetaGyrasMessageMemory, MetaGyrasPlansMemory
from gyra_serve.building.app.service.service import Service as AppService
from ...building.app.api.schema_app import GptsAppQuery, GptsApp, GptsAppDetail

CFG = Config()
logger = logging.getLogger(__name__)


class AppManager(BaseComponent, ABC):
    name = "gyra_agent_app_manager"

    def __init__(self, system_app: SystemApp):
        self.gpts_conversations = GptsConversationsDao()
        self.gpts_messages_dao = GptsMessagesDao()

        self.memory = GptsMemory(
            plans_memory=MetaGyrasPlansMemory(),
            message_memory=MetaGyrasMessageMemory(),
        )
        self.agent_memory_map = {}

        super().__init__(system_app)
        self.system_app = system_app

    def init_app(self, system_app: SystemApp):
        self.system_app = system_app

    def get_gyras(self, query: Optional[str], user_code: Optional[str] = None, sys_code: Optional[str] = None):

        app_service = AppService.get_instance(CFG.SYSTEM_APP)

        apps = app_service.sync_app_list(GptsAppQuery(name_filter=query, user_code=user_code, sys_code=sys_code))
        if apps:
            ## 排除掉非Agent的无法进行链接对话应用，
            results = []
            for item in apps.app_list:
                if not item.team_mode == TeamMode.NATIVE_APP.value:
                    results.append(item)
            return results
        else:
            return []

    async def get_app(self, app_code) -> GptsApp:
        """get app"""
        app_service = AppService.get_instance(CFG.SYSTEM_APP)
        return await app_service.app_detail(app_code)

    async def create_app_agent(
            self,
            gpts_app: GptsApp,
            agent_memory: AgentMemory,
            context: AgentContext,
    ) -> ConversableAgent:
        # init default llm provider
        # LLM client is resolved by AIWrapper via ProviderRegistry at call
        # time (reading agent.llm config). Pass None here.
        llm_provider = None

        # init team employees
        # TODO employee has it own llm provider
        employees: List[ConversableAgent] = []
        # 多媒体子 Agent：把该 app 自身的 ext_config.multimedia_agent 绑定到实例，
        # 使同一 MULTIMEDIA 模板下不同 app 各自携带自己的名称/默认模型/风格 prompt，
        # 通过 app_code 寻址时互不覆盖。（多实例各自独立）
        multimedia_ext = getattr(gpts_app, "ext_config", None)
        if not isinstance(multimedia_ext, dict):
            multimedia_ext = None
        details = gpts_app.details
        if not details and TeamMode(gpts_app.team_mode) == TeamMode.SINGLE_AGENT:
            # v2 单 Agent 应用没有 app_detail 明细行，Agent 由应用自身配置
            # （app.agent / team_context.agent_name）描述。作为子 Agent 被调用时
            # （AppResource._start_app 路径）details 为空会导致 employees 为空、
            # create_agent_of_gpts_app 取 employees[0] 抛 IndexError，
            # 此处按应用自身配置合成一条明细，与直接对话路径（agent_chat）对齐。
            record = self._build_self_detail(gpts_app)
            if record is not None:
                details = [record]
        for record in details:
            agent = await create_agent_from_gpt_detail(
                record, llm_provider, context, agent_memory
            )
            if multimedia_ext:
                try:
                    from gyra.agent.multimedia import MultimediaAgent

                    if isinstance(agent, MultimediaAgent):
                        agent.bind_app_config(multimedia_ext)
                except Exception as e:  # noqa: BLE001 - 绑定失败不影响主流程
                    logger.warning(
                        f"[app-agent] bind multimedia config failed for {record.agent_name}: {e}"
                    )
            # agent.name_prefix = gpts_app.app_name
            employees.append(agent)

        app_agent: ConversableAgent = await create_agent_of_gpts_app(
            gpts_app, llm_provider, context, agent_memory, employees
        )
        # app_agent.name_prefix = gpts_app.app_name
        return app_agent

    @staticmethod
    def _build_self_detail(gpts_app: GptsApp) -> Optional[GptsAppDetail]:
        """为无明细行的单 Agent 应用，按应用自身配置合成一条 GptsAppDetail。

        Agent 名取 app.agent，缺省回退 team_context.agent_name（历史数据经
        resolve_agent_name 解析别名）；LLM 策略取 app.llm_config，缺省 Default。
        应用未声明 Agent 时返回 None。
        """
        from gyra.agent.core.agent_alias import resolve_agent_name

        agent_name = getattr(gpts_app, "agent", None)
        if not agent_name:
            tc = gpts_app.team_context
            if isinstance(tc, dict):
                agent_name = tc.get("agent_name")
            elif tc is not None:
                agent_name = getattr(tc, "agent_name", None)
        if not agent_name:
            logger.warning(
                f"[app-agent] single_agent app {gpts_app.app_code} 未声明 Agent，无法构建"
            )
            return None
        app_llm = getattr(gpts_app, "llm_config", None)
        return GptsAppDetail(
            app_code=gpts_app.app_code,
            app_name=gpts_app.app_name,
            type="agent",
            agent_name=resolve_agent_name(agent_name),
            agent_role=gpts_app.app_code,
            agent_icon=gpts_app.icon,
            agent_describe=gpts_app.app_describe,
            resources=gpts_app.all_resources or gpts_app.resources,
            llm_strategy=(
                getattr(app_llm, "llm_strategy", None) or LLMStrategyType.Default.value
            ),
            llm_strategy_value=getattr(app_llm, "llm_strategy_value", None),
        )

    async def create_agent_by_app_code(
            self,
            gpts_app: GptsApp,
            conv_uid: str = None,
            agent_memory: AgentMemory = None,
            context: AgentContext = None,
    ) -> ConversableAgent:
        """
        Create a conversable agent by application code.

        Parameters:
            gpts_app (str): The application.
            conv_uid (str, optional): The unique identifier of the conversation,
                default is None. If not provided, a new UUID will be generated.
            agent_memory (AgentMemory, optional): The memory object for the agent,
                default is None. If not provided, a default memory object will be
                created.
            context (AgentContext, optional): The context object for the agent, default
                is None. If not provided, a default context object will be created.

        Returns:
            ConversableAgent: The created conversable agent object.
        """
        conv_uid = str(uuid.uuid4()) if conv_uid is None else conv_uid

        from gyra.agent.core.memory.gpts import (
            DefaultGptsMessageMemory,
            DefaultGptsPlansMemory,
        )

        if agent_memory is None:
            gpt_memory = GptsMemory(
                plans_memory=DefaultGptsPlansMemory(),
                message_memory=DefaultGptsMessageMemory(),
            )
            await gpt_memory.init(conv_uid)
            agent_memory = AgentMemory(gpts_memory=gpt_memory)

        if context is None:
            context: AgentContext = AgentContext(
                conv_id=conv_uid,
                gpts_app_code=gpts_app.app_code,
                gpts_app_name=gpts_app.app_name,
                language=gpts_app.language,
                enable_vis_message=False,
            )
        context.gpts_app_code = gpts_app.app_code
        context.gpts_app_name = gpts_app.app_name
        context.language = gpts_app.language

        agent: ConversableAgent = await self.create_app_agent(
            gpts_app, agent_memory, context
        )
        return agent


async def create_agent_from_gpt_detail(
        record: GptsAppDetail,
        llm_client: LLMClient,
        agent_context: AgentContext,
        agent_memory: AgentMemory,
) -> ConversableAgent:
    """
    Get the agent object from the GPTsAppDetail object.
    """
    agent_manager = get_agent_manager()
    agent_cls: Type[ConversableAgent] = agent_manager.get_by_name(record.agent_name)
    llm_config = LLMConfig(
        llm_client=llm_client,
        llm_strategy=LLMStrategyType(record.llm_strategy),
        strategy_context=record.llm_strategy_value,
    )
    prompt_template = None
    if record.prompt_template:
        prompt_template: PromptTemplate = get_service().get_template(
            prompt_code=record.prompt_template
        )

    depend_resource = await blocking_func_to_async(
        CFG.SYSTEM_APP, get_resource_manager().build_resource, record.resources
    )

    agent = (
        await agent_cls()
        .bind(agent_context)
        .bind(agent_memory)
        .bind(llm_config)
        .bind(depend_resource)
        .bind(prompt_template)
        .build()
    )

    return agent


async def create_agent_of_gpts_app(
        gpts_app: GptsApp,
        llm_client: LLMClient,
        context: AgentContext,
        memory: AgentMemory,
        employees: List[ConversableAgent],
) -> ConversableAgent:
    llm_config = LLMConfig(
        llm_client=llm_client,
        llm_strategy=LLMStrategyType.Default,
    )

    team_mode = TeamMode(gpts_app.team_mode)
    if team_mode == TeamMode.SINGLE_AGENT:
        if not employees:
            raise ValueError(
                f"APP {gpts_app.app_code}({gpts_app.app_name}) 没有可用的 Agent！"
            )
        agent_of_app: ConversableAgent = employees[0]
    else:
        if TeamMode.AUTO_PLAN == team_mode:
            agent_manager = get_agent_manager()
            # team_context 可能是 dict（sync_app_detail 序列化后）、
            # AutoTeamContext 对象或 JSON 字符串，统一解析后访问 teamleader
            tc = gpts_app.team_context
            if isinstance(tc, dict):
                auto_team_ctx = AutoTeamContext(**tc)
            elif isinstance(tc, AutoTeamContext):
                auto_team_ctx = tc
            else:
                auto_team_ctx = AutoTeamContext(**json.loads(tc))
            manager_cls: Type[ManagerAgent] = agent_manager.get_team_leader_by_name(
                auto_team_ctx.teamleader
            )
            manager = manager_cls()


            if not gpts_app.details or len(gpts_app.details) < 0:
                raise ValueError("APP exception no available agent！")
            llm_config = employees[0].llm_config

        else:
            raise ValueError(f"Unknown Agent Team Mode!{team_mode}")
        manager = await manager.bind(context).bind(memory).bind(llm_config).build()
        manager.hire(employees)
        agent_of_app: ConversableAgent = manager

    return agent_of_app


def get_app_manager() -> AppManager:
    return app_manager


app_manager = AppManager(CFG.SYSTEM_APP)
