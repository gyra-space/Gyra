import asyncio
import concurrent.futures
import json
import logging
import time
import uuid
import warnings
from datetime import datetime
from typing import Optional, Dict, Literal

from gyra.context.window import ContextWindow
from gyra.vis import SystemVisTag
from ... import GptsMemory, AgentContext, AgentResource, ConversableAgent, AgentMessage, AgentMemory
from ...core.action.base import ToolCall, Action, ActionOutput, AskUserType
from ...core.memory.gpts import GptsMessage
from ...core.reasoning.reasoning_action import AgentActionInput
from ...core.subagent_handle import MAX_SUBAGENT_DEPTH, SubagentDepthExceededError, SubAgentMode

from gyra.agent.resource import ToolParameter, FunctionTool
from gyra.agent.tools.context import ToolContext
from gyra.agent.resource.app import AppResource
from ...core.schema import Status, ActionInferenceMetrics

_AGENT_START_PROMPT = """\
代理(Agent)交互接口。用于使用其他代理(Agent)完成任务进入代理模式。
**注意事项:** * 指定的agent和你的上下文是隔离的，请传递准确、完整的任务描述。
**防御性原则**：在调用任何子 Agent 之前，必须严格评估该 Agent 的能力是否与当前任务目标**精确匹配**。如果收到的指令（如"查询某个监控表")在当前可用的子 Agent 工具集中没有直接对应的能力，**严禁**选择一个功能不相关的工具进行"尝试性"调用。此时，应将此情况作为发现记录在报告中，并重新评估计划，而不是执行错误的工具调用。
**参数说明**:
  - agent_id: 目标子 Agent 的唯一标识（必填，自模板 spawn 暂未实现）
  - input: 任务目标指令内容（必填）
  - mode: "sync"（默认，等待子 Agent 完成）或 "async"（后台运行，全完成后回调主 resume；单进程异步优先，分布式调度未来演进）
  - wait: 异步模式专用（默认 true）。true=阻塞等待：派发后本轮立即结束、主会话进入 WAITING，子 Agent 完成后自动触发主 resume；false=后台执行：你继续处理其他工作，结果经异步通知注入上下文。
  - **视频生成等长耗时任务必须用 mode="async"**（或传 media.kind="video" 自动走异步），避免主 Agent 被同步阻塞数分钟。
  - **同一任务请勿重复派发**：相同 agent + 相同任务的重复调用会被去重并复用在途任务（图片/视频生成按次计费）。
  - background: 相关背景知识（可选）
"""

logger = logging.getLogger(__name__)


def _subagent_call_params(action_input: AgentActionInput) -> Dict[str, object]:
    """抽取子 Agent 调用的关键参数（media/wait/background/mode），供看板展示。

    只保留可展示、可序列化的字段，避免把内部对象塞进 gpts_conversations.extra。
    """
    params: Dict[str, object] = {}
    mode = (action_input.mode or "sync")
    if mode:
        params["mode"] = mode
    extra = action_input.extra_info or {}
    if extra.get("media"):
        params["media"] = extra["media"]
    if "wait" in extra:
        params["wait"] = extra["wait"]
    if extra.get("background"):
        params["background"] = extra["background"]
    return params


class AgentAction(Action[AgentActionInput]):
    name = "Agent"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.action_view_tag = SystemVisTag.VisPlans.value

    async def _action_init_push(self, gpts_memory: GptsMemory, agent: "ConversableAgent", current_message: AgentMessage,
                                agent_context: AgentContext, start_time):
        init_action_outs = [ActionOutput(
            name=self.name,
            content=f"### {agent.name}Agent运行中\n** {self.action_input.content} **",
            start_time=start_time,
            action_id=self.action_uid,
            thoughts=self.action_input.thought,
            action=self.action_input.agent_name,
            action_input=self.action_input.to_dict(),
            state=Status.RUNNING.value,
        )]

        ## 展示工具任务基础信息
        await gpts_memory.push_message(conv_id=agent.agent_context.conv_id, stream_msg={
            "uid": current_message.message_id,
            "type": "all",
            "sender": agent.name or agent.role,
            "sender_role": agent.role,
            "message_id": current_message.message_id,
            "goal_id": current_message.goal_id,
            "conv_id": agent_context.conv_id,
            "conv_session_uid": agent_context.conv_session_id,
            "app_code": agent_context.gpts_app_code,
            "start_time": start_time,
            "action_report": init_action_outs
        }, )

    def _resolve_app_code(self, sender, agent_name: str) -> Optional[str]:
        """在 sender 的 app 资源中按名称或 code 解析目标子 Agent 的 app_code。

        优先新协议 capability_pack（AppCapability），fallback 旧 resource_map
        （GptAppResource/AppResource）。单 Agent（BAIZE）无 `.agents` 团队成员，
        子 Agent 以此派发。找不到返回 None。
        """
        # 新协议：capability_pack.sub_resources 中的 AppCapability
        pack = getattr(sender, "capability_pack", None)
        if pack is not None and hasattr(pack, "sub_resources"):
            for cap in pack.sub_resources:
                cid = getattr(cap, "capability_id", "") or ""
                if not cid.startswith("app"):
                    continue
                code = getattr(cap, "_app_code", "") or ""
                name = getattr(cap, "_app_name", "") or ""
                if agent_name in (code, name):
                    return code
        # 旧协议：resource_map 中的 AppResource
        for resources in (getattr(sender, "resource_map", None) or {}).values():
            for res in resources or []:
                if not isinstance(res, AppResource):
                    continue
                code = getattr(res, "app_code", "") or ""
                name = getattr(res, "app_name", "") or getattr(res, "name", "") or ""
                if agent_name in (code, name):
                    return code
        return None

    async def _dispatch_to_app(
        self,
        *,
        sender,
        agent_context,
        memory,
        current_message,
        message,
        app_code: str,
        action_input,
        metrics,
        action_id,
    ) -> ActionOutput:
        """单 Agent 场景下经 GptAppResource 同步派发到子 Agent app。

        与 async 分支的 GptAppResource._start_app 路径一致：创建目标 app 的 agent
        实例并 generate_reply（含 subagent_depth 传播），返回归一化 ActionOutput。
        """
        try:
            from gyra_serve.agent.resource.app import GptAppResource

            parent_depth = 0
            if agent_context is not None:
                parent_extra = agent_context.extra or {}
                parent_depth = parent_extra.get("subagent_depth", 0) or 0

            app_resource = GptAppResource(name=app_code, app_code=app_code)
            answer = await app_resource._start_app(
                user_input=message.content,
                sender=sender,
                parent_depth=parent_depth,
                extra_info=action_input.extra_info,
            )

            metrics.end_time_ms = time.time_ns() // 1_000_000
            content = answer.content if answer else "Not Have Answer！"
            logger.info(
                f"[ACTION]---------->   Agent Action [{sender.name}] --> [{app_code}] (app resource): {content}"
            )
            return ActionOutput.from_dict({
                "action_id": action_id or self.action_uid,
                "is_exe_success": True,
                "thoughts": action_input.thought,
                "action": self.name,
                "name": self.name,
                "state": Status.TODO.value,
                "action_input": action_input.to_dict(),
                "content": content,
                "observations": content,
                "ask_user": False,
                "ask_type": AskUserType.NESTED_AGENT,
                "metrics": metrics,
            })
        except Exception as e:
            logger.exception(f"Agent Action (app resource) Run Failed!{e}")
            metrics.end_time_ms = time.time_ns() // 1_000_000
            return ActionOutput.from_dict({
                "action_id": self.action_uid,
                "is_exe_success": False,
                "thoughts": action_input.thought,
                "action": action_input.agent_name,
                "name": self.name,
                "state": Status.FAILED.value,
                "action_input": action_input.content,
                "content": f"Agent启动异常！{str(e)}",
                "metrics": metrics,
            })

    async def run(
        self,
        ai_message: str = None,
        resource: Optional[AgentResource] = None,
        rely_action_out: Optional[ActionOutput] = None,
        need_vis_render: bool = True,
        **kwargs,
    ) -> ActionOutput:
        """Perform the action."""
        action_input = self.action_input or AgentActionInput.model_validate_json(
            json_data=ai_message
        )
        metrics = ActionInferenceMetrics()
        metrics.start_time_ms = time.time_ns() // 1_000_000
        try:

            action_id = kwargs.get("action_id", None)
            sender: ConversableAgent = kwargs["agent"]
            agent_context: AgentContext = kwargs.get('agent_context')

            # 子 agent 深度守卫（早于 recipient lookup，fail-fast）
            parent_extra = (agent_context.extra or {}) if agent_context else {}
            parent_depth = parent_extra.get("subagent_depth", 0) or 0
            if parent_depth >= MAX_SUBAGENT_DEPTH:
                raise SubagentDepthExceededError(parent_depth, MAX_SUBAGENT_DEPTH)

            # 团队成员（V1 团队派发）。单 Agent（如 BAIZE/ReActMasterAgent）没有
            # .agents 属性，子 Agent 以 app 资源形式存在，下方走 app 资源派发兜底。
            teammates = getattr(sender, "agents", None) or []
            logger.warning(
                f"[AgentAction] sender.agents: {[f'{a.name}({a.agent_context.agent_app_code})' for a in teammates]}")
            logger.warning(f"[AgentAction] Looking for agent with agent_name={action_input.agent_name}")
            recipient = next(
                (agent for agent in teammates if
                 agent.name == action_input.agent_name or agent.agent_context.agent_app_code == action_input.agent_name),
                None,
            )
            # 团队成员未命中时，尝试从 sender 的 app 资源（capability_pack / resource_map）解析
            target_app_code = (
                None if recipient else self._resolve_app_code(sender, action_input.agent_name)
            )
            if not recipient and not target_app_code:
                logger.error(
                    f"[AgentAction] recipient can't be empty! sender.agents={[(a.name, a.agent_context.agent_app_code) for a in teammates]}, trying to find={action_input.agent_name}")
                raise RuntimeError("recipient can't be empty")

            received_message = (
                kwargs["message"] if "message" in kwargs else AgentMessage.init_new()
            )
            start_time = datetime.now()
            memory: AgentMemory = kwargs.get('memory')
            agent: ConversableAgent = kwargs.get('agent')
            message_id: str = kwargs.get('message_id')
            current_message: AgentMessage = kwargs.get('current_message')
            self._render = kwargs.get("render_protocol") or self._render

            if memory:
                logger.info("任务分派前先记录当前agent启动消息！")
                ## agent 转发消息 需要提前记录，否则等子agent返回再记录会导致显示混乱
                await memory.gpts_memory.append_message(conv_id=agent_context.conv_id,
                                                        message=GptsMessage.from_agent_message(current_message,
                                                                                               sender=agent,
                                                                                               receiver=agent),
                                                        save_db=False)

            # 初始化AgentAction的展示
            await self._action_init_push(gpts_memory=memory.gpts_memory, agent=agent, current_message=current_message,
                                         agent_context=agent_context, start_time=start_time)
            #  构建转发给Agent的新消息
            # 注意：这里使用 self.action_uid 作为 goal_id，让子Agent的任务节点挂载到agent_start动作下
            # 形成正确的层级关系：A Agent -> agent_start -> B Agent -> B的工具
            message = AgentMessage.init_new(
                content=(
                    action_input.content
                    + "\n\n"
                    + json.dumps(action_input.extra_info, ensure_ascii=False)
                ),
                context=(received_message.context or {}) | (action_input.extra_info or {}),
                rounds=await sender.memory.gpts_memory.next_message_rounds(sender.not_null_agent_context.conv_id),
                name=sender.name,
                role=sender.role,
                show_message=False,
                observation=action_input.content,
                current_goal=action_input.content,
                goal_id=current_message.message_id,
            )
            # message.goal_id = kwargs["action_id"] if "action_id" in kwargs else ""
            # message.current_goal = action_input.content
            # 合并context 且action_input.extra_info优先级更高
            # 注意：不修改 message_id，让它保持 init_new 生成的唯一 ID
            # 这样 B Agent 的任务节点会有唯一的 node_id，且不同于 parent_id (goal_id)
            message.context = (message.context or {}) | (action_input.extra_info or {})

            # 单 Agent（BAIZE）场景：无团队成员，子 Agent 以 app 资源派发（等价 async 分支）
            if not recipient and target_app_code:
                return await self._dispatch_to_app(
                    sender=sender,
                    agent_context=agent_context,
                    memory=memory,
                    current_message=current_message,
                    message=message,
                    app_code=target_app_code,
                    action_input=action_input,
                    metrics=metrics,
                    action_id=action_id,
                )

            logger.info(f"[ACTION]---------->   Agent Action [{sender.name}] --> [{recipient.name}]")

            # 深度传播：把 parent_depth+1 写入 recipient.agent_context.extra
            if recipient.agent_context is not None:
                child_extra = recipient.agent_context.extra or {}
                child_extra["subagent_depth"] = parent_depth + 1
                recipient.agent_context.extra = child_extra

            # B Agent 应该使用 agent_start 的 action_uid 作为父节点
            # 但 message_id 应该保持自动生成，确保 B Agent 的任务节点有唯一的 ID
            # 并且 parent_id (goal_id) ≠ node_id，避免被判定为根节点
            await ContextWindow.create(agent=recipient, task_id=message.message_id)
            answer: AgentMessage = await sender.send(message=message, recipient=recipient, request_reply=True,
                                                     request_sender_reply=False)

            from gyra.agent.core.scheduled_agent import ScheduledAgent
            if isinstance(recipient, ScheduledAgent) and recipient.scheduler and recipient.scheduler.running():
                # ScheduledAgent由scheduler驱动，其他Agent由send/receive/generate_reply的loop驱动
                # ScheduledAgent receive后直接就return了，再异步act
                # 因此这里不能直接return，而需要确保所有异步act都执行完成了
                await recipient.scheduler.schedule()

            metrics.end_time_ms = time.time_ns() // 1_000_000
            ask_user = True if answer and answer.action_report and any(
                [act_out.ask_user for act_out in answer.action_report]) else False
            ## 终止状态要排除正常返回的报告Agent
            # terminate = True if answer and answer.action_report and any([act_out.terminate for act_out in answer.action_report]) else False
            ask_type = AskUserType.NESTED_AGENT if ask_user else None
            logger.info(f"[ACTION]---------->   Agent Action [{sender.name}] --> answer: {answer}")
            return ActionOutput.from_dict({
                "action_id": action_id or self.action_uid,
                "is_exe_success": True,
                "thoughts": action_input.thought,
                "action": self.name,
                "name": self.name,
                "state": Status.TODO.value,
                "action_input": action_input.to_dict(),
                "content": answer.content if answer else "Not Have Answer！",
                "observations": answer.content if answer else "Not Have Answer！",
                "ask_user": ask_user,
                "ask_type": ask_type,
                "metrics": metrics,
            })

        except SubagentDepthExceededError:
            # 安全守卫违规不掩盖为普通 action 失败，向上抛
            raise
        except Exception as e:
            logger.exception(f"Agent Action Run Failed!{str(e)}")
            metrics.end_time_ms = time.time_ns() // 1_000_000
            return ActionOutput.from_dict({
                "action_id": self.action_uid,
                "is_exe_success": False,
                "thoughts": action_input.thought,
                "action": action_input.agent_name,
                "name": self.name,
                "state": Status.FAILED.value,
                "action_input": action_input.content,
                "content": f"Agent启动异常！{str(e)}",
                "metrics": metrics,
            })


class SubAgent(AgentAction, FunctionTool):
    name = "SubAgent"  # 子 Agent 派发工具。曾用名 agent_start（parse_action 仍兼容旧名），类名 SubAgent，AgentStart 作 deprecated 别名
    """Sub-agent dispatch tool.

    Spawns or dispatches to a sub-agent. Supports sync mode (wait for result)
    and async mode (background, main resumes when all subagents done).

    Note: 自模板 spawn (agent_id=None → 用当前 agent 的 app_code) 与 async 模式的
    完整实现在 V1 架构治理 PR 2 中作为 API surface 落地，完整路径需要跨包
    (gyra-core ↔ gyra-serve GptAppResource) 协作，作为后续 PR 推进。
    当前 BAIZE 路径下：sync 模式按 V1 AgentAction 逻辑（dispatch to team member）
    工作；async 模式暂以 warning + 同步降级处理。
    """

    @classmethod
    def get_action_description(cls) -> str:
        return _AGENT_START_PROMPT

    @property
    def description(self):
        return self.get_action_description()

    @property
    def args(self):
        return {
            "agent_id": ToolParameter(
                type="string",
                name="agent_id",
                description="目标子Agent的唯一标识，必须为系统中已注册的Agent。",
                required=True
            ),
            "input": ToolParameter(
                type="string",
                name="input",
                description="需要完成的任务目标指令内容。",
                required=True
            ),
            "sync": ToolParameter(
                type="bool",
                name="sync",
                description="[deprecated] 旧参数，等价于 mode='sync'。请优先使用 mode 参数。",
                required=False,
                default=True
            ),
            "mode": ToolParameter(
                type="string",
                name="mode",
                description='执行模式: "sync" (默认, 等待子 Agent 完成) 或 "async" (后台运行, 全完成后触发主 resume)。旧参数 sync=True 等价于 mode="sync"。',
                required=False,
                default="sync"
            ),
            "wait": ToolParameter(
                type="bool",
                name="wait",
                description=(
                    '异步(mode="async")时是否需要等待子 Agent 结果（默认 true）。'
                    'true=阻塞等待: 派发后本轮立即结束, 子 Agent 完成后自动恢复继续; '
                    'false=后台执行: 你继续处理其他工作, 结果经异步通知注入上下文。'
                    '仅当结果与后续工作完全无关时才用 false。'
                ),
                required=False,
                default=True
            ),
            "background": ToolParameter(
                type="string",
                name="background",
                description="和目标任务相关的背景知识信息。",
                required=False
            ),
            "media": ToolParameter(
                type="object",
                name="media",
                description=(
                    "可选的多媒体生成参数（仅当目标子 Agent 是多媒体 Agent 时生效）。"
                    "当任务要求生成视频/图片时，若有明确档位要求（如时长、分辨率、宽高比），"
                    "必须在此显式声明，否则会使用子 Agent 配置的默认值（可能不符合要求）。"
                    "支持字段：kind('image'|'video')、model(模型名)、size(图片尺寸，如 1024x1024)、"
                    "resolution(视频分辨率，如 1080p)、aspect_ratio(视频宽高比，如 16:9)、"
                    "duration(视频时长，秒，如 15)、quality、reference_images(参考图 URL 列表)、"
                    "image_url(首帧/参考图)、image_url_last(尾帧) 及其它 provider 参数。"
                ),
                required=False
            ),
        }

    def execute(self, *args, **kwargs):
        # V2 路径: 从 ToolContext 获取 app_resource（V2 dispatch 已在 PR 0 关闭，此处保留以兼容 V2 单元测试资产）
        context = kwargs.get("context")
        if isinstance(context, ToolContext):
            app_resource = context.get_resource("app_resource")
            if app_resource is not None:
                return self._execute_with_app_resource(app_resource, args, kwargs)
            return f"sub_agent: no app_resource in context, args={args}"
        # BAIZE 回退
        raise RuntimeError("当前工具需要转AgentAction执行, 不能直接作为工具调用！")

    async def async_execute(self, *args, **kwargs):
        # V2 路径: 从 ToolContext 获取 app_resource
        context = kwargs.get("context")
        if isinstance(context, ToolContext):
            app_resource = context.get_resource("app_resource")
            if app_resource is not None:
                return await self._async_execute_with_app_resource(app_resource, args, kwargs)
            return self.execute(*args, **kwargs)
        return self.execute(*args, **kwargs)

    def _execute_with_app_resource(self, app_resource, args, kwargs):
        """V2 路径: 使用 app_resource 执行 sub_agent。"""
        tool_input = args[0] if args else kwargs
        user_input = tool_input.get("input", "")

        def _run():
            return asyncio.run(app_resource.async_execute(user_input=user_input))

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            result = executor.submit(_run).result()

        return str(result)

    async def _async_execute_with_app_resource(self, app_resource, args, kwargs):
        """V2 异步路径: 使用 app_resource 执行 sub_agent。"""
        tool_input = args[0] if args else kwargs
        user_input = tool_input.get("input", "")
        result = await app_resource.async_execute(user_input=user_input)
        return str(result)

    @classmethod
    def parse_action(
        cls,
        tool_call: ToolCall,
        default_action: Optional["Action"] = None,
        resource: Optional["Resource"] = None,
        **kwargs,
    ) -> Optional["Action"]:
        """Parse the action from the message.

        If you want skip the action, return None.
        """
        # 兼容历史名：当前 cls.name == "SubAgent"，旧名 "agent_start"/"sub_agent" 仍接受
        accepted_names = {cls.name, "agent_start", "sub_agent"}
        if tool_call.name in accepted_names:
            if not tool_call.args:
                raise ValueError("Agent转发任务异常，没有转发参数！")
            else:
                if not tool_call.args.get("agent_id"):
                    raise ValueError("没有可委派转发的AgentId信息！")
                if not tool_call.args.get("input"):
                    raise ValueError("没有给委派Agent指定任务目标！")
            extra_info = None
            if tool_call.args.get("background"):
                extra_info: Dict = {
                    "background": tool_call.args.get("background")
                }
            if tool_call.args.get("media"):
                extra_info = extra_info or {}
                extra_info["media"] = tool_call.args.get("media")
            if "wait" in tool_call.args:
                extra_info = extra_info or {}
                extra_info["wait"] = tool_call.args.get("wait")

            # 解析 mode：优先 mode 参数，回退到 deprecated sync 参数
            explicit_mode = tool_call.args.get("mode")
            sync_flag = tool_call.args.get("sync")
            if explicit_mode:
                mode = explicit_mode
            elif sync_flag is False:
                mode = "async"
            else:
                mode = "sync"

            # 视频生成耗时长：调用方未显式指定 mode/sync 时，传 media.kind="video"
            # 自动走异步，避免主 Agent 同步阻塞（主会话 WAITING，子 Agent 后台完成后 resume）
            if not explicit_mode and sync_flag is None:
                media = tool_call.args.get("media") or {}
                if isinstance(media, dict) and media.get("kind") == "video":
                    mode = "async"

            return cls(action_uid=tool_call.tool_call_id,
                       action_input=AgentActionInput(agent_name=tool_call.args.get("agent_id"),
                                                     content=tool_call.args.get("input"),
                                                     extra_info=extra_info,
                                                     mode=mode))
        else:
            return None

    async def run(
        self,
        ai_message: str = None,
        resource: Optional[AgentResource] = None,
        rely_action_out: Optional[ActionOutput] = None,
        need_vis_render: bool = True,
        **kwargs,
    ) -> ActionOutput:
        """Dispatch to sub-agent. Sync mode delegates to V1 team dispatch;
        async mode spawns a new conversation in the background and returns immediately.

        Async mode requires gyra_serve SubagentCoordinator to be registered globally
        (via ``set_subagent_coordinator``) and ``GptAppResource`` to be importable. If
        either is unavailable, async degrades to sync with a warning.
        """
        action_input = self.action_input or AgentActionInput.model_validate_json(
            json_data=ai_message
        )
        mode_str = (action_input.mode or "sync").lower()
        if mode_str != "async":
            return await super().run(
                ai_message=ai_message,
                resource=resource,
                rely_action_out=rely_action_out,
                need_vis_render=need_vis_render,
                **kwargs,
            )

        # ---- async branch ----
        metrics = ActionInferenceMetrics()
        metrics.start_time_ms = time.time_ns() // 1_000_000
        try:
            sender: ConversableAgent = kwargs["agent"]
            agent_context: AgentContext = kwargs.get("agent_context")
            main_conv_id = agent_context.conv_id if agent_context else None
            if not main_conv_id:
                logger.warning(
                    "[SubAgent.async] missing main_conv_id; degrading to sync"
                )
                return await super().run(
                    ai_message=ai_message,
                    resource=resource,
                    rely_action_out=rely_action_out,
                    need_vis_render=need_vis_render,
                    **kwargs,
                )

            # 拿全局 coordinator（gyra_serve 启动时注册）
            try:
                from gyra_serve.agent.subagent_coordinator import (
                    get_subagent_coordinator,
                )
            except ImportError:
                get_subagent_coordinator = None  # type: ignore[assignment]
            coordinator = get_subagent_coordinator() if get_subagent_coordinator else None
            if coordinator is None:
                logger.warning(
                    "[SubAgent.async] no global coordinator registered; degrading to sync"
                )
                return await super().run(
                    ai_message=ai_message,
                    resource=resource,
                    rely_action_out=rely_action_out,
                    need_vis_render=need_vis_render,
                    **kwargs,
                )

            # 构造 GptAppResource，用 action_input.agent_name 当 app_code
            try:
                from gyra_serve.agent.resource.app import GptAppResource
            except ImportError as ie:
                logger.warning(
                    f"[SubAgent.async] gyra_serve not importable ({ie}); degrading to sync"
                )
                return await super().run(
                    ai_message=ai_message,
                    resource=resource,
                    rely_action_out=rely_action_out,
                    need_vis_render=need_vis_render,
                    **kwargs,
                )
            # 解析真实 app_code（与 sync 分支一致）：优先按名称从 capability_pack /
            # resource_map 解析目标子 Agent 应用的真实 app_code，避免把 app_name 当
            # app_code 查询失败（"应用不存在[xxx]"）。解析不到时回退 agent_name。
            target_app_code = (
                self._resolve_app_code(sender, action_input.agent_name)
                or action_input.agent_name
            )
            app_resource = GptAppResource(
                name=action_input.agent_name,
                app_code=target_app_code,
            )

            # 前置校验：目标 app 必须存在。此处同步失败并返回 is_exe_success=False，
            # 而不是在后台任务里吞掉错误（后台失败只回调 pending_subagents，
            # 主 loop 感知不到、无法让 Agent 重新生成参数）。
            try:
                from gyra_serve.agent.agents.app_agent_manage import get_app_manager

                await get_app_manager().get_app(target_app_code)
            except Exception as ve:
                logger.warning(
                    f"[SubAgent.async] target app not found: {ve}"
                )
                metrics.end_time_ms = time.time_ns() // 1_000_000
                return ActionOutput.from_dict({
                    "action_id": self.action_uid,
                    "is_exe_success": False,
                    "thoughts": action_input.thought,
                    "action": self.name,
                    "name": self.name,
                    "state": Status.FAILED.value,
                    "action_input": action_input.to_dict(),
                    "content": f"子 Agent 启动失败: {ve}",
                    "observations": f"async subagent validation failed: {ve}",
                    "metrics": metrics,
                })

            # 深度守卫（与 sync 路径一致）
            parent_extra = (agent_context.extra or {}) if agent_context else {}
            parent_depth = parent_extra.get("subagent_depth", 0) or 0
            if parent_depth >= MAX_SUBAGENT_DEPTH:
                raise SubagentDepthExceededError(parent_depth, MAX_SUBAGENT_DEPTH)

            # 新 sub_conv_id
            sub_conv_id = str(uuid.uuid4())

            # 注册到 coordinator（持久化 pending_subagents）；同 agent 同任务的
            # 在途子 agent 会被去重复用（created=False），避免昂贵任务重复扣费
            handle, created = await coordinator.register_subagent(
                main_conv_id=main_conv_id,
                sub_conv_id=sub_conv_id,
                mode=SubAgentMode.ASYNC,
                agent_name=action_input.agent_name,
                task=action_input.content,
                params=_subagent_call_params(action_input),
            )

            metrics.end_time_ms = time.time_ns() // 1_000_000
            # 阻塞等待（默认）：跳出本轮 loop、会话 WAITING，子 agent 完成后 resume；
            # wait=False = fire-and-forget：继续 loop，结果经异步通知注入上下文
            wait_flag = (action_input.extra_info or {}).get("wait", True)
            wait_flag = bool(wait_flag) if wait_flag is not None else True
            if not created:
                logger.info(
                    f"[SubAgent.async] dedup: reuse in-flight sub_conv="
                    f"{handle.sub_conv_id} for main={main_conv_id}"
                )
                return ActionOutput.from_dict({
                    "action_id": self.action_uid,
                    "is_exe_success": True,
                    "thoughts": action_input.thought,
                    "action": self.name,
                    "name": self.name,
                    "state": Status.WAITING.value if wait_flag else Status.RUNNING.value,
                    "wait_async": wait_flag,
                    "action_input": action_input.to_dict(),
                    "content": (
                        f"相同任务已有子 Agent 在后台执行中 "
                        f"(sub_conv_id={handle.sub_conv_id})，已复用该任务、未重复提交。\n"
                        f"请勿再次提交相同任务（图片/视频生成按次计费）。"
                        + (
                            "本轮将结束等待，子 Agent 完成后会自动恢复继续。"
                            if wait_flag
                            else "结果完成后会经异步通知注入上下文。"
                        )
                    ),
                    "observations": (
                        f"async subagent dedup: reuse sub_conv_id={handle.sub_conv_id}"
                    ),
                    "metrics": metrics,
                })

            # 后台跑子 agent，不 await
            asyncio.create_task(
                self._run_subagent_background(
                    app_resource=app_resource,
                    user_input=action_input.content,
                    sender=sender,
                    sub_conv_id=sub_conv_id,
                    main_conv_id=main_conv_id,
                    parent_depth=parent_depth,
                    extra_info=action_input.extra_info,
                )
            )

            logger.info(
                f"[SubAgent.async] spawned sub_conv={sub_conv_id} for main={main_conv_id}"
            )
            return ActionOutput.from_dict({
                "action_id": self.action_uid,
                "is_exe_success": True,
                "thoughts": action_input.thought,
                "action": self.name,
                "name": self.name,
                "state": Status.WAITING.value if wait_flag else Status.RUNNING.value,
                "wait_async": wait_flag,
                "action_input": action_input.to_dict(),
                "content": (
                    f"子 Agent 已后台启动 (sub_conv_id={sub_conv_id})。\n"
                    f"请勿重复提交相同任务（图片/视频生成按次计费）。"
                    + (
                        "本轮将在此结束并等待子 Agent 完成，完成后会自动恢复继续（无需轮询）。"
                        if wait_flag
                        else "你可以继续其他工作，结果完成后会经异步通知注入上下文；"
                             "可用 check_tasks/wait_tasks 以该 sub_conv_id 查询进度。"
                    )
                ),
                "observations": (
                    f"async subagent spawned: sub_conv_id={sub_conv_id}"
                ),
                "metrics": metrics,
            })

        except SubagentDepthExceededError:
            raise
        except Exception as e:
            logger.exception(f"[SubAgent.async] failed: {e}")
            metrics.end_time_ms = time.time_ns() // 1_000_000
            return ActionOutput.from_dict({
                "action_id": self.action_uid,
                "is_exe_success": False,
                "thoughts": action_input.thought,
                "action": action_input.agent_name,
                "name": self.name,
                "state": Status.FAILED.value,
                "action_input": action_input.content,
                "content": f"async SubAgent 启动异常！{str(e)}",
                "metrics": metrics,
            })

    async def _run_subagent_background(
        self,
        app_resource,
        user_input: str,
        sender: ConversableAgent,
        sub_conv_id: str,
        main_conv_id: str,
        parent_depth: int,
        extra_info: Optional[Dict] = None,
    ) -> None:
        """后台跑子 agent，完成后回调 coordinator.on_subagent_done/failed。

        Runs in a fire-and-forget asyncio task. Any exception is routed to the
        coordinator as a sub-agent failure — never raised to the caller.
        """
        try:
            # 深度传播：parent_depth → child AgentContext.extra["subagent_depth"] = parent_depth+1
            answer = await app_resource._start_app(
                user_input=user_input,
                sender=sender,
                conv_uid=sub_conv_id,
                parent_depth=parent_depth,
                extra_info=extra_info,
            )
            content = getattr(answer, "content", None) or ""
            try:
                from gyra_serve.agent.subagent_coordinator import (
                    get_subagent_coordinator,
                )
                coordinator = get_subagent_coordinator()
                if coordinator is not None:
                    await coordinator.on_subagent_done(
                        main_conv_id=main_conv_id,
                        sub_conv_id=sub_conv_id,
                        result=content,
                        # 结构化失败标记:MultimediaAgent 生成失败时 success=False
                        # (见 multimedia/agent.py correctness_check),优先于前缀匹配
                        success=getattr(answer, "success", None),
                    )
            except Exception as cb_err:
                logger.warning(
                    f"[SubAgent.async] on_done callback failed for sub={sub_conv_id}: {cb_err}"
                )
        except Exception as run_err:
            logger.exception(
                f"[SubAgent.async] background run failed for sub={sub_conv_id}: {run_err}"
            )
            try:
                from gyra_serve.agent.subagent_coordinator import (
                    get_subagent_coordinator,
                )
                coordinator = get_subagent_coordinator()
                if coordinator is not None:
                    await coordinator.on_subagent_failed(
                        main_conv_id=main_conv_id,
                        sub_conv_id=sub_conv_id,
                        error=str(run_err),
                    )
            except Exception as cb_err:
                logger.warning(
                    f"[SubAgent.async] on_failed callback failed for sub={sub_conv_id}: {cb_err}"
                )


# Deprecated alias — 1 个版本后删除
AgentStart = SubAgent
