"""
多媒体 Agent 配置模型

多媒体 Agent 是一个「通用简单多媒体 GridAgent 模板」：它只使用多媒体生成模型，
不跑 LLM 推理循环，而是把任务描述 + 固定配置确定性映射到媒体生成 provider 调用。

本模块定义该模板的固定输入/输出设置、默认模型、预设风格/场景 prompt、交付方式等。
配置可来源于：
- 预设 agent 配置（YAML / 代码默认值）
- 应用（app）配置里的多媒体 Agent 模板配置（前端 agent 配置页编辑）
- 运行时覆盖（调用方传入的 context / args）
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ---- 图片尺寸档位（面向用户的标准档位名 → 具体像素尺寸） ----
# 用户期望图片尺寸按 720p/1080p/2k/4k 等标准档位区分，而不是只给一个裸分辨率。
# 这里维护档位名 → provider 实际使用的 size 字符串映射；未命中档位的值按原样透传
# （兼容旧配置里 "1024x1024" 等直接尺寸写法）。
IMAGE_SIZE_TIERS: Dict[str, str] = {
    "720p": "1280x720",
    "1080p": "1920x1080",
    "2k": "2560x1440",
    "4k": "3840x2160",
}


def resolve_image_size(value: Optional[str]) -> Optional[str]:
    """把图片尺寸档位名解析为具体像素尺寸；非档位名（或空）原样返回。

    Examples:
        resolve_image_size("1080p")  -> "1920x1080"
        resolve_image_size("1024x1024") -> "1024x1024"
        resolve_image_size("")       -> ""
    """
    if not value:
        return value
    return IMAGE_SIZE_TIERS.get(value.strip().lower(), value)


class MultimediaAgentConfig(BaseModel):
    """单个多媒体 Agent 模板的固定配置。"""

    # ---- 身份 ----
    name: str = Field(
        default="multimedia_agent", description="Agent 名称（供 spawn/寻址）"
    )
    description: str = Field(default="多媒体生成 Agent", description="Agent 描述")

    # ---- 能力类型（二选一） ----
    # 一个 MultimediaAgent 模板实例只承担一种媒体类型：图片 or 视频。运行时按该类型
    # 决定 kind 与模型池，避免"以为能生成视频实际生成图片"。需要两种能力时，配置两个
    # Agent 实例（app）分别选 image / video。
    capability: str = Field(
        default="image", description="能力类型：image 或 video（二选一）"
    )

    # ---- 能力开关（兼容旧配置，主控以 capability 为准） ----
    capability_image: bool = Field(default=True, description="是否启用图片生成能力")
    capability_video: bool = Field(default=True, description="是否启用视频生成能力")

    # ---- 模型（自管模型选择） ----
    # 可用模型候选池：该 Agent 可用的图片/视频模型白名单。任务不指定模型时，
    # 从候选池里按「默认模型 › 池内第一个可用」选择；候选池为空则回退全局
    # （系统默认 / 首个可用）。
    image_models: List[str] = Field(
        default_factory=list, description="可用图片模型候选池（白名单），空则用全局"
    )
    video_models: List[str] = Field(
        default_factory=list, description="可用视频模型候选池（白名单），空则用全局"
    )
    # 默认模型：候选池中默认选中的模型（需在对应候选池内）。
    default_image_model: str = Field(default="", description="默认图片模型名")
    default_video_model: str = Field(default="", description="默认视频模型名")

    # ---- 预设风格 / 场景 prompt 模板 ----
    # 风格 prompt：追加到任务描述前，固化视觉风格（如"赛博朋克""3D 卡通"）。
    style_prompt: str = Field(default="", description="预设风格 prompt（追加到任务前）")
    # 场景 prompt：追加到任务描述后，固化场景/构图/镜头等约束。
    scene_prompt: str = Field(default="", description="预设场景 prompt（追加到任务后）")
    # 反向提示词：传递给 provider 的负面约束。
    negative_prompt: str = Field(default="", description="预设反向提示词")

    # ---- 固定输出设置 ----
    default_image_size: str = Field(default="1024x1024", description="默认图片尺寸")
    default_video_resolution: str = Field(default="720p", description="默认视频分辨率")
    default_video_aspect_ratio: str = Field(
        default="16:9", description="默认视频宽高比"
    )
    default_video_duration: int = Field(default=5, description="默认视频时长(秒)")

    # ---- 交付方式 ----
    # 多媒体生成结果始终落盘 AFS 并产出 Artifact（强制交付，保证成果可追溯）。
    file_prefix: str = Field(default="generated_media", description="落盘文件名前缀")

    # ---- 执行 ----
    timeout: int = Field(default=1800, description="视频等长耗时任务的超时秒数")
    async_default: bool = Field(
        default=False, description="默认是否异步（后台执行 + 完成后自动通知）"
    )

    # ---- 固定参数覆盖：调用方未传时，用这里的值填充 provider 参数 ----
    # 例如 {"n": 1, "quality": "hd", "generate_audio": True}
    fixed_params: Dict[str, Any] = Field(
        default_factory=dict, description="固定 provider 参数覆盖"
    )

    def model_dict(self) -> Dict[str, Any]:
        """序列化为可存 JSON 的 dict（用于前端配置页 / 应用配置持久化）。"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "MultimediaAgentConfig":
        """从 dict / 应用配置重建配置。无效或空返回默认配置。"""
        if not data:
            return cls()
        try:
            return cls(**{k: v for k, v in data.items() if v is not None})
        except Exception:  # noqa: BLE001 - 容错：字段不合法时回退默认
            return cls()
