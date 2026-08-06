"""
多媒体 Agent 模板（通用简单多媒体 agent）

提供「只使用多媒体生成模型」的轻量 Agent 的完整实现：
- ``MultimediaAgentConfig``：固定输入/输出设置、默认模型、预设风格/场景 prompt、交付方式
- ``MultimediaExecutor``：可复用的生成执行器（模型解析→provider→轮询/下载→AFS 交付）
- ``MultimediaAgent``：继承 ``ConversableAgent`` 的一等公民主 Agent 模板（注册进 AgentManager）

与工具范式（generate_image / generate_video）并存，可随意选用。
"""

from .agent import MultimediaAgent
from .config import MultimediaAgentConfig
from .executor import (
    KIND_IMAGE,
    KIND_VIDEO,
    MultimediaExecutor,
    MultimediaRequest,
)

__all__ = [
    "MultimediaAgentConfig",
    "KIND_IMAGE",
    "KIND_VIDEO",
    "MultimediaExecutor",
    "MultimediaRequest",
    "MultimediaAgent",
]
