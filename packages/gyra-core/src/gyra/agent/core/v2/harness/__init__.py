"""Harness —— V2 引擎统一服务总线。

对齐 DeepSeek Harness 的 ``ctx`` 服务总线 + 能力缝（seam）设计：
run_loop / run_step / V2AgentRuntime 只消费 :class:`HarnessContext`，
每个 harness 能力（storage / events / tools / approval / subagents / jobs /
hooks / skills）是可选 seam，可注入不同 provider 替换行为。
"""
from gyra.agent.core.v2.harness.context import HarnessContext
from gyra.agent.core.v2.harness.seams import (
    JobRegistry,
    SkillSeam,
    SubagentSeam,
)
from gyra.agent.core.v2.harness.vis_bridge import VisBridge

__all__ = [
    "HarnessContext",
    "JobRegistry",
    "SkillSeam",
    "SubagentSeam",
    "VisBridge",
]
