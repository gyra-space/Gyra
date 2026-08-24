# Define your Pydantic schemas here
from typing import Any, Dict, Optional

from gyra._private.pydantic import BaseModel, ConfigDict, Field, model_to_dict

from ..config import SERVE_APP_NAME_HUMP


class ServeRequest(BaseModel):
    """Conversation request model"""

    model_config = ConfigDict(title=f"ServeRequest for {SERVE_APP_NAME_HUMP}")

    # Just for query
    chat_mode: str = Field(
        default=None,
        description="The chat mode.",
        examples=[
            "chat_normal",
        ],
    )
    conv_uid: Optional[str] = Field(
        default=None,
        description="The conversation uid.",
        examples=[
            "5e7100bc-9017-11ee-9876-8fe019728d79",
        ],
    )
    user_name: Optional[str] = Field(
        default=None,
        description="The user name.",
        examples=[
            "zhangsan",
        ],
    )
    sys_code: Optional[str] = Field(
        default=None,
        description="The system code.",
        examples=[
            "gyra",
        ],
    )
    workspace_id: Optional[int] = Field(
        default=None,
        description="The workspace id this conversation belongs to (NULL for HomeChat).",
    )
    task_id: Optional[int] = Field(
        default=None,
        description="The task id this conversation belongs to.",
    )

    def to_dict(self, **kwargs) -> Dict[str, Any]:
        """Convert the model to a dictionary"""
        return model_to_dict(self, **kwargs)


class CallDetailVO(BaseModel):
    """单次模型调用详情（用于排查定位）。

    从 gpts_messages 还原一次模型调用的输入（system/user 提示词）、输出、
    工具列表、工具调用与性能指标。老版本 V1 chat_history 无这些字段时为空。
    """

    message_id: Optional[str] = Field(
        default=None, description="gpts message_id（用于定位到具体消息）"
    )
    round: Optional[int] = Field(default=None, description="对话轮次")
    role: Optional[str] = Field(default=None, description="消息角色（assistant/ai）")
    model_name: Optional[str] = Field(
        default=None, description="本次调用使用的模型名"
    )
    system_prompt: Optional[str] = Field(
        default=None, description="本次调用发送给模型的系统提示词"
    )
    user_prompt: Optional[str] = Field(
        default=None, description="本次调用发送给模型的用户提示词"
    )
    content: Optional[str] = Field(default=None, description="模型输出内容")
    thinking: Optional[str] = Field(default=None, description="模型推理过程")
    observation: Optional[str] = Field(default=None, description="观测/工具结果")
    input_tools: Optional[Any] = Field(
        default=None, description="本次调用传入的工具列表"
    )
    tool_calls: Optional[Any] = Field(
        default=None, description="本次调用发出的工具调用"
    )
    metrics: Optional[Dict] = Field(
        default=None, description="性能指标（llm_metrics：tokens/耗时/速度等）"
    )
    time_stamp: Optional[Any] = Field(default=None, description="消息时间戳")

    def to_dict(self, **kwargs) -> Dict[str, Any]:
        """Convert the model to a dictionary"""
        return model_to_dict(self, **kwargs)


class ServerResponse(BaseModel):
    """Conversation response model"""

    model_config = ConfigDict(
        title=f"ServerResponse for {SERVE_APP_NAME_HUMP}", protected_namespaces=()
    )

    conv_uid: str = Field(
        ...,
        description="The conversation uid.",
        examples=[
            "5e7100bc-9017-11ee-9876-8fe019728d79",
        ],
    )
    conv_session_id: Optional[str] = Field(
        default=None,
        description="The conversation session id (used to get all messages in a session).",
        examples=[
            "5e7100bc-9017-11ee-9876-8fe019728d79",
        ],
    )
    user_input: Optional[str] = Field(
        None,
        description="The user input, we return it as the summary the conversation.",
        examples=[
            "Hello world",
        ],
    )
    chat_mode: Optional[str] = Field(
        None,
        description="The chat mode.",
        examples=[
            "chat_normal",
        ],
    )
    app_code: Optional[str] = Field(
        default=None,
        description="The chat app code.",
        examples=[
            "app_code_xxx",
        ],
    )
    select_param: Optional[str] = Field(
        default=None,
        description="The select param.",
        examples=[
            "my_knowledge_space_name",
        ],
    )
    model_name: Optional[str] = Field(
        default=None,
        description="The model name.",
        examples=[
            "vicuna-13b-v1.5",
        ],
    )
    user_name: Optional[str] = Field(
        default=None,
        description="The user name.",
        examples=[
            "zhangsan",
        ],
    )
    sys_code: Optional[str] = Field(
        default=None,
        description="The system code.",
        examples=[
            "gyra",
        ],
    )
    workspace_id: Optional[int] = Field(
        default=None,
        description="The workspace id this conversation belongs to.",
    )
    task_id: Optional[int] = Field(
        default=None,
        description="The task id this conversation belongs to.",
    )
    workspace_name: Optional[str] = Field(
        default=None,
        description="The workspace display name (enriched from workspace table).",
    )
    workspace_code: Optional[str] = Field(
        default=None,
        description="The workspace code, used to navigate back into the workspace detail page.",
    )
    conv_type: Optional[str] = Field(
        default=None,
        description="Conversation type: agent(独立对话) / workspace(空间大厅) / task(任务会话).",
        examples=[
            "agent",
        ],
    )
    gmt_created: Optional[str] = Field(
        default=None,
        description="The record creation time.",
        examples=[
            "2023-01-07 09:00:00",
        ],
    )
    gmt_modified: Optional[str] = Field(
        default=None,
        description="The record update time.",
        examples=[
            "2023-01-07 09:00:00",
        ],
    )

    def to_dict(self, **kwargs) -> Dict[str, Any]:
        """Convert the model to a dictionary"""
        return model_to_dict(self, **kwargs)


class MessageVo(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    role: str = Field(
        ...,
        description="The role that sends out the current message.",
        examples=["human", "ai", "view"],
    )
    context: str = Field(
        ...,
        description="The current message content.",
        examples=[
            "Hello",
            "Hi, how are you?",
        ],
    )

    order: int = Field(
        ...,
        description="The current message order.",
        examples=[
            1,
            2,
        ],
    )

    message_id: Optional[str] = Field(
        default=None,
        description="The gpts message_id (uuid), used to match compression-segment boundaries.",
    )

    time_stamp: Optional[Any] = Field(
        default=None,
        description="The current message time stamp.",
        examples=[
            "2023-01-07 09:00:00",
        ],
    )

    model_name: Optional[str] = Field(
        default=None,
        description="The model name.",
        examples=[
            "vicuna-13b-v1.5",
        ],
    )

    feedback: Optional[Dict] = Field(
        default={},
        description="feedback info",
        examples=[
            "{}",
        ],
    )

    def to_dict(self, **kwargs) -> Dict[str, Any]:
        """Convert the model to a dictionary"""
        return model_to_dict(self, **kwargs)
