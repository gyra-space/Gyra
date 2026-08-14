"""Skill capability —— 技能自管目录(RFC-005 Step B / RFC-006 Stage 7)。

技能是纯声明类:declare 渲染 skill 列表进 SYSTEM,无 I/O、无 executor。
config→SkillCapability 经 CapabilityFactoryRegistry(register_capability_to)构造。
"""

from .capability import SkillCapability  # noqa: F401

__all__ = ["SkillCapability"]


def register(registry) -> None:
    """被 CapabilityRegistry.discover() 调用(占位,符合 capability 目录约定)。"""
    pass


def build_capability(value, system_app=None):
    """RFC-006 Stage 7:从 config dict 构造 SkillCapability(若 config 带 name/path 则纯配置态)。"""
    return SkillCapability.from_config(value, system_app)


# RFC-006 Phase A:供 CapabilityFactoryRegistry 构造期 build_pack 用。
CAPABILITY_TYPE_KEY = "skill(gyra)"


def register_capability_to(registry) -> None:
    registry.register(CAPABILITY_TYPE_KEY, build_capability)
    # Phase D:旧 AgentSkillResource.type() 为 "skill"(沙箱技能),同走 SkillCapability。
    registry.register("skill", build_capability)
