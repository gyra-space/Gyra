"""Agent resource module."""

from .gyra_skill import (
    GyraSkillResource,
    GyraSkillResourceParameters,
    register_gyra_skill_resource,
)

__all__ = [
    "GyraSkillResource",
    "GyraSkillResourceParameters",
    "register_gyra_skill_resource",
]