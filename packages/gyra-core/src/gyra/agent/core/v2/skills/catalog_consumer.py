"""SkillCatalogConsumer——把 skill 目录以 user-role reminder 注入 LLM。

对齐 DSH tool-skill 设计（[skills.zh.md:228-235]）：

  - **首次** ``agent/pre-step`` 注入持久 user-role ``<system-reminder>``；
  - 目录只含 sorted ``name`` + 截断 ``description``；不含 body / path / 路由提示；
  - **digest 变化**时通过 ``agent.inject()`` 追加一条**完整替换**；digest
    不变 / 空目录 / 已被压缩隐藏：保持上一份可用视图（不重发）；
  - 删空（显式 empty）：追加一条空替换让模型知道目录清空。

不在 scope 内：
  - 不负责把 catalog 拼到 system prompt（DSH 强调 user-role 分离，避免污染
    KV-cache 静态前缀）；
  - 不负责 skill 加载正文——由 :class:`SkillTool` 接管（model 调 ``skill({name})``）。
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from gyra.agent.core.v2.skills.registry import (
    SkillInvocation,
    SkillRegistry,
    SkillSummary,
)

logger = logging.getLogger(__name__)


# 默认 description 截断长度（对齐 DSH 默认 500）
DEFAULT_DESCRIPTION_MAX = 500


# --------------------------------------------------------------------------- #
# 渲染辅助
# --------------------------------------------------------------------------- #

def _xml_escape(s: str) -> str:
    """XML 转义——DSH 强制。

    避免 description 里出现 ``<`` / ``&`` 破坏 ``<skill>`` 标签。"""
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace("\"", "&quot;")
    )


def render_catalog_xml(
    summaries: Iterable[SkillSummary],
    *,
    description_max: int = DEFAULT_DESCRIPTION_MAX,
) -> str:
    """渲染 ``<available_skills>`` XML 段。

    严格只含 ``name`` + 截断转义的 ``description``；按 name 排序。
    对齐 DSH 描述：*catalog contains sorted skill name and normalized,
    XML-escaped description only; it omits bodies, paths, sources,
    providers, and routing hints*。"""
    rows: List[str] = []
    for s in summaries:
        # model-invocable 之外的 skill 不进 catalog（DSH 行为）
        if s.invocation in (SkillInvocation.USER_ONLY, SkillInvocation.NONE):
            continue
        desc = (s.description or "").strip()
        if len(desc) > description_max:
            desc = desc[: description_max - 1] + "…"
        rows.append(
            f"  <skill>\n"
            f"    <name>{_xml_escape(s.name)}</name>\n"
            f"    <description>{_xml_escape(desc)}</description>\n"
            f"  </skill>"
        )
    if not rows:
        return ""
    return "<available_skills>\n" + "\n".join(rows) + "\n</available_skills>"


def build_initial_reminder(
    summaries: Iterable[SkillSummary],
    *,
    description_max: int = DEFAULT_DESCRIPTION_MAX,
) -> Optional[Dict[str, str]]:
    """构造"首次目录注入"的 user-role reminder 消息（DSH 风格）。"""
    xml = render_catalog_xml(summaries, description_max=description_max)
    if not xml:
        return None
    return {
        "role": "user",
        "content": (
            "<system-reminder>\n"
            f"{xml}\n\n"
            "Skills are optional capabilities. Use the `skill({ name })` tool to load "
            "the full instructions for a skill before following them.\n"
            "</system-reminder>"
        ),
    }


def build_replacement_reminder(
    summaries: Iterable[SkillSummary],
    *,
    description_max: int = DEFAULT_DESCRIPTION_MAX,
) -> Dict[str, str]:
    """构造"目录 digest 变化时"的完整替换消息（DSH 风格）。

    即使为空也返回（空替换让模型知道目录被清空）。
    """
    xml = render_catalog_xml(summaries, description_max=description_max)
    return {
        "role": "user",
        "content": (
            "<system-reminder>\n"
            f"{xml}\n\n"
            "Skills are optional capabilities. Use the `skill({ name })` tool to load "
            "the full instructions for a skill before following them.\n"
            "</system-reminder>"
        ),
    }


# --------------------------------------------------------------------------- #
# Consumer（拉模式 + digest 跟踪）
# --------------------------------------------------------------------------- #

@dataclass
class SkillCatalogConsumer:
    """Catalog 消费方——跟踪上次发布 digest，按需产出 user-role reminder。

    用法（与 run_loop / agent runtime 集成）::

        consumer = SkillCatalogConsumer(
            registry, layer_chain=["scope", "host"], cwd=None,
        )
        # 1. 首步：若 catalog 非空，注入初始 reminder
        msg = await consumer.initial()
        if msg is not None:
            await agent.inject(msg)

        # 2. 每步：catalog 变化才追加完整替换
        msg = await consumer.refresh()
        if msg is not None:
            await agent.inject(msg)

    注意：consumer 内部 digest 与 registry 的 digest 计算保持一致；
    任何对 registry 的 ``register`` / ``register_provider`` / ``invalidate``
    都会自增 generation 触发订阅；consumer 选择用 pull 模式（每次
    ``initial`` / ``refresh`` 自检），不依赖 push，与 DSH 文档行为一致。
    """

    registry: SkillRegistry
    layer_chain: List[str]
    cwd: Optional[str] = None
    description_max: int = DEFAULT_DESCRIPTION_MAX
    # 内部状态：上次发布 digest；未发布过为 None
    _last_published_digest: Optional[str] = None
    _last_published_generation: int = -1

    async def initial(self) -> Optional[Dict[str, str]]:
        """首次发布——若 catalog 非空返回 user-role reminder；否则 None。"""
        summaries = await self.registry.list(self.layer_chain, self.cwd)
        self._last_published_digest = await self.registry.catalog_digest(
            self.layer_chain, self.cwd,
        )
        self._last_published_generation = self.registry.generation
        return build_initial_reminder(summaries, description_max=self.description_max)

    async def refresh(self) -> Optional[Dict[str, str]]:
        """基于 digest 变化发布完整替换。

        行为：
          - generation 未变（catalog 无变化）→ 返回 None；
          - digest 未变（即便 generation 变了，候选内容也未变）→ 返回 None；
          - 否则返回完整替换（空目录也是合法替换）。"""
        cur_gen = self.registry.generation
        cur_digest = await self.registry.catalog_digest(self.layer_chain, self.cwd)
        if self._last_published_digest is None:
            # 未发布过；调 initial()
            return await self.initial()
        if cur_gen == self._last_published_generation:
            return None
        if cur_digest == self._last_published_digest:
            # generation 变了但内容未变（极少见，如 provider 替换但 list 结果相同）
            self._last_published_generation = cur_gen
            return None
        summaries = await self.registry.list(self.layer_chain, self.cwd)
        self._last_published_digest = cur_digest
        self._last_published_generation = cur_gen
        return build_replacement_reminder(summaries, description_max=self.description_max)

    def reset(self) -> None:
        """清空状态（新 session / 显式重置）。"""
        self._last_published_digest = None
        self._last_published_generation = -1
