"""
E2B Sandbox Configuration

E2B (https://e2b.dev) 是一个云端沙箱服务。本模块定义 E2B provider 的配置项，
支持从字典 / TOML 加载，并解析为 E2BSandbox 的初始化参数。
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


DEFAULT_E2B_API_KEY_ENV = "E2B_API_KEY"
DEFAULT_E2B_TEMPLATE = "base"
DEFAULT_E2B_TIMEOUT = 300  # 沙箱存活时间上限（分钟）


@dataclass
class E2BSandboxConfig:
    """E2B 云端沙箱配置。

    Attributes:
        api_key: E2B API Key。为空时回退到 ``E2B_API_KEY`` 环境变量。
        template: E2B 沙箱模板名或 ID，默认 ``base``。
        timeout: 沙箱最大存活时间（分钟），默认 300。
        work_dir: 沙箱内工作目录，默认 ``/home/user``。
        skill_dir: 沙箱内 skill 目录（默认 ``/home/user/skill``）。
        metadata: 附加到沙箱的元数据。
        env_vars: 注入沙箱的环境变量。
    """

    api_key: str = ""
    template: str = DEFAULT_E2B_TEMPLATE
    timeout: int = DEFAULT_E2B_TIMEOUT
    work_dir: str = "/home/user"
    skill_dir: str = "/home/user/skill"
    metadata: Dict[str, str] = field(default_factory=dict)
    env_vars: Dict[str, str] = field(default_factory=dict)

    def resolved_api_key(self) -> str:
        """返回实际使用的 API Key（配置值优先，其次环境变量）。"""
        return (self.api_key or "").strip() or os.getenv(DEFAULT_E2B_API_KEY_ENV, "")

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "E2BSandboxConfig":
        """从字典创建配置（兼容 TOML 解析结果）。"""
        return cls(
            api_key=config_dict.get("api_key", ""),
            template=config_dict.get("template", DEFAULT_E2B_TEMPLATE),
            timeout=config_dict.get("timeout", DEFAULT_E2B_TIMEOUT),
            work_dir=config_dict.get("work_dir", "/home/user"),
            skill_dir=config_dict.get("skill_dir", "/home/user/skill"),
            metadata=config_dict.get("metadata") or {},
            env_vars=config_dict.get("env_vars") or {},
        )