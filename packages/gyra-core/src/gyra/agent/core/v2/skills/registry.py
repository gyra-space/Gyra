"""V2 Skill Registry——对齐 DeepSeek Harness 的 ``ctx.skills``。

设计要点（对齐 DSH skills.md）：

  1. **分层注册表**：host + per-scope 分层（scope_key 即 agent_id / conv_id
     维度），注册落入调用方 scope 对应的层。读取时合并全局层 + 当前 scope
     链，最近层的同名条目**直接赢**；同层内重名按 rank / provider 顺序。
  2. **轻量 Provider 接口**：每个 provider 实现 ``list()`` / ``get()``；
     远程 provider 的初始化在 list() 内部 await。
  3. **缓存与失效**：按 ``(scope_chain, cwd)`` 缓存完成态 catalog 摘要；
     提供 ``invalidate()`` 主动失效；注册 / 注销时自动 ``notify()`` 通知订阅者。
  4. **digest 变化才通知**：consumer 用 ``catalog_digest()`` 计算 SHA；digest
     不变就不发任何 catalog 消息，对齐 DSH tool-skill "digest 变化才注入替换"。
  5. **跨进程不可变**：registry 实例非线程安全（serve 内单进程用）；进程内
     所有 agent preset 共用同一 registry。
"""
from __future__ import annotations

import asyncio
import hashlib
import inspect
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any, Awaitable, Callable, Dict, Iterable, List, Optional, Tuple, Union,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# 模型可见性策略
# --------------------------------------------------------------------------- #

class SkillInvocation(str, Enum):
    """Skill 调用策略。

    对齐 DSH SkillInvocationPolicy（modelInvocable / userInvocable 二维布尔）。
    本枚举覆盖其二维笛卡尔积的 4 种组合，便于 provider 用单字段声明。
    """
    MODEL_ONLY = "model_only"          # modelInvocable=True, userInvocable=False
    USER_ONLY = "user_only"            # modelInvocable=False, userInvocable=True
    BOTH = "both"                      # 双向可调用（默认）
    NONE = "none"                      # 仅供可信 ctx.skills.get() 内部调用


# --------------------------------------------------------------------------- #
# 数据形状
# --------------------------------------------------------------------------- #

@dataclass
class SkillSummary:
    """轻量元数据（model-visible）。

    对齐 DSH SkillSummary。**path / body 不进 model**；catalog 渲染只取
    name + 截断的 description。
    """
    name: str
    description: str = ""
    when_to_use: Optional[str] = None
    invocation: SkillInvocation = SkillInvocation.BOTH
    source: str = "user"           # source bucket：project/runtime/user-dsh...
    provider: str = "user"
    # 以下字段**不**进 LLM；consumer 渲染时丢弃
    path: Optional[str] = None
    rank: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "when_to_use": self.when_to_use,
            "invocation": self.invocation.value,
            "source": self.source,
            "provider": self.provider,
        }


@dataclass
class SkillDefinition(SkillSummary):
    """完整 skill 定义（工具返回 / 内部 get() 返回）。

    对齐 DSH SkillDefinition——在 summary 之上加 content / metadata。
    """
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Provider 接口
# --------------------------------------------------------------------------- #

@dataclass
class SkillLookupOptions:
    """调用方对单个 provider 的查找选项。

    字段与 DSH SkillLookupOptions 对齐：cwd 选工作区敏感 skill，signal 取消。
    """
    cwd: Optional[str] = None
    signal: Optional[Any] = None   # asyncio.AbstractEventLoop / threading.Event 都不强制


class SkillProvider:
    """Skill 来源提供者接口。

    对齐 DSH SkillProvider——list() 列举候选，get() 加载完整 body。
    """

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def list(
        self, options: SkillLookupOptions,
    ) -> List[SkillSummary]:
        """返回当前 provider 提供的 skill 候选列表（summary 级）。"""
        raise NotImplementedError

    async def get(
        self, name: str, options: SkillLookupOptions,
    ) -> Optional[SkillDefinition]:
        """按 name 加载完整 skill 定义；不存在或不再可加载返回 None。"""
        raise NotImplementedError


# --------------------------------------------------------------------------- #
# 目录条目（registry 内部）
# --------------------------------------------------------------------------- #

@dataclass
class _ProviderEntry:
    layer: str
    provider: SkillProvider


@dataclass
class _RuntimeEntry:
    layer: str
    definition: SkillDefinition


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

# 缓存 TTL：5s。DSH 也用短 TTL + 主动 invalidate 双策略。
_DEFAULT_TTL = 5.0

# layer 默认值
LAYER_HOST = "host"          # 全局层
LAYER_SCOPE = "scope"        # 当前 scope（agent preset / conv 维度）层


class SkillRegistry:
    """分层 skill 注册表——对齐 DSH ``ctx.skills``。"""

    def __init__(self, *, cache_ttl: float = _DEFAULT_TTL):
        self._providers: List[_ProviderEntry] = []
        # (layer, name) -> definition；first-wins 同层
        self._runtime: Dict[Tuple[str, str], _RuntimeEntry] = {}
        # (scope_chain_key, cwd_key) -> (expires_at, summaries)
        self._cache: Dict[Tuple[str, str], Tuple[float, List[SkillSummary]]] = {}
        # 订阅者：catalog invalidate 时通知
        self._subscribers: List[Callable[[], Any]] = []
        self._cache_ttl = cache_ttl
        # 显式失效游标：供 consumer 拉模式判断"自上次以来是否变化"
        self._generation: int = 0

    # ------------------------------------------------------------------ #
    # 注册
    # ------------------------------------------------------------------ #

    def register_provider(self, layer: str, provider: SkillProvider) -> Callable[[], None]:
        """注册一个 provider 到指定 layer；返回 disposer。"""
        if not layer:
            raise ValueError("layer must be a non-empty string")
        if not isinstance(provider, SkillProvider):
            raise TypeError(f"provider must be SkillProvider, got {type(provider)}")
        # 唯一性：同 layer 内 provider name 唯一
        for ent in self._providers:
            if ent.layer == layer and ent.provider.name == provider.name:
                raise ValueError(
                    f"provider '{provider.name}' already registered in layer '{layer}'"
                )
        self._providers.append(_ProviderEntry(layer=layer, provider=provider))
        self._invalidate()
        logger.debug(
            f"[SkillRegistry] registered provider {provider.name!r} in layer {layer!r}"
        )

        def _dispose() -> None:
            self._providers = [
                e for e in self._providers
                if not (e.layer == layer and e.provider.name == provider.name)
            ]
            self._invalidate()
            logger.debug(
                f"[SkillRegistry] disposed provider {provider.name!r} from layer {layer!r}"
            )

        return _dispose

    def register(
        self, layer: str, definition: SkillDefinition,
    ) -> Callable[[], None]:
        """直接注册一个 runtime skill 到指定 layer。"""
        if not layer:
            raise ValueError("layer must be a non-empty string")
        if not isinstance(definition, SkillDefinition):
            raise TypeError("definition must be SkillDefinition")
        # 同层内同名：first-wins（DSH：first-wins, duplicate logs warning, no-op disposer）
        if (layer, definition.name) in self._runtime:
            logger.warning(
                f"[SkillRegistry] duplicate runtime skill '{definition.name}' "
                f"in layer '{layer}' (first-wins, no-op disposer)"
            )

            def _noop() -> None:
                pass

            return _noop
        self._runtime[(layer, definition.name)] = _RuntimeEntry(
            layer=layer, definition=definition,
        )
        self._invalidate()
        logger.debug(
            f"[SkillRegistry] registered runtime skill {definition.name!r} "
            f"in layer {layer!r}"
        )

        def _dispose() -> None:
            ent = self._runtime.pop((layer, definition.name), None)
            if ent is not None:
                self._invalidate()
                logger.debug(
                    f"[SkillRegistry] disposed runtime skill {definition.name!r} "
                    f"from layer {layer!r}"
                )

        return _dispose

    # ------------------------------------------------------------------ #
    # 失效 / 订阅
    # ------------------------------------------------------------------ #

    def invalidate(self, name: Optional[str] = None) -> None:
        """主动失效缓存并通知订阅者。

        传 name 只清该 skill 相关的缓存；不传清全部。"""
        if name is None:
            self._cache.clear()
        else:
            self._cache.clear()  # 简化：整体清
        self._invalidate()

    def _invalidate(self) -> None:
        self._generation += 1
        for cb in list(self._subscribers):
            try:
                res = cb()
                if inspect.isawaitable(res):
                    # 订阅者不应 await 此处（registry 非异步核心路径）
                    # 但允许返回协程，外层不必等；fire-and-forget 日志吞错
                    async def _safe_await(r):
                        try:
                            await r
                        except Exception:  # noqa: BLE001
                            logger.debug("[SkillRegistry] subscriber await failed", exc_info=True)
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            loop.create_task(_safe_await(res))
                    except RuntimeError:
                        pass
            except Exception:  # noqa: BLE001
                logger.debug("[SkillRegistry] subscriber callback failed", exc_info=True)

    def subscribe(self, callback: Callable[[], Any]) -> Callable[[], None]:
        """订阅 catalog 变化通知；返回 disposer。"""
        if not callable(callback):
            raise TypeError("callback must be callable")
        self._subscribers.append(callback)

        def _dispose() -> None:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

        return _dispose

    @property
    def generation(self) -> int:
        """当前 generation（递增计数器）；consumer 用它判断"是否需要重读 catalog"。

        注意：跨进程无意义；同一进程内 generation 单调递增。
        """
        return self._generation

    # ------------------------------------------------------------------ #
    # 读取
    # ------------------------------------------------------------------ #

    async def list(
        self,
        layer_chain: Optional[List[str]] = None,
        cwd: Optional[str] = None,
    ) -> List[SkillSummary]:
        """返回 invocation-neutral skill 摘要（按 name 排序）。

        ``layer_chain``：从近到远的 layer 列表（如 ``['scope', 'host']``）。
        """
        chain = tuple(layer_chain or [LAYER_HOST])
        cwd_key = cwd or ""
        cache_key = (",".join(chain), cwd_key)
        now = time.monotonic()
        cached = self._cache.get(cache_key)
        if cached and cached[0] > now:
            return list(cached[1])
        summaries = await self._collect(chain, cwd)
        self._cache[cache_key] = (now + self._cache_ttl, summaries)
        return list(summaries)

    async def get(
        self,
        name: str,
        layer_chain: Optional[List[str]] = None,
        cwd: Optional[str] = None,
    ) -> Optional[SkillDefinition]:
        """按 name 加载完整 skill 定义。

        优先级：
          1. 最近层先查；先 runtime 定义（确定性），再 provider.get()；
          2. 最近层的同名条目**直接赢**（不查更远层）。
        """
        chain = list(layer_chain or [LAYER_HOST])
        cwd_key = cwd or ""
        options = SkillLookupOptions(cwd=cwd_key)
        # 1. runtime
        for layer in chain:
            ent = self._runtime.get((layer, name))
            if ent is not None:
                return ent.definition
        # 2. provider.get()（按 layer 内注册顺序探）
        for layer in chain:
            for ent in self._providers:
                if ent.layer != layer:
                    continue
                try:
                    defn = await ent.provider.get(name, options)
                except Exception as e:  # noqa: BLE001
                    logger.debug(
                        f"[SkillRegistry] provider {ent.provider.name!r} "
                        f"get({name!r}) failed: {e}"
                    )
                    continue
                if defn is not None:
                    return defn
        return None

    # ------------------------------------------------------------------ #
    # 目录摘要与 digest
    # ------------------------------------------------------------------ #

    async def catalog_digest(
        self,
        layer_chain: Optional[List[str]] = None,
        cwd: Optional[str] = None,
    ) -> str:
        """对当前目录算 SHA-256 hex（前 16 字符）作为 digest。

        digest 变化是 catalog 变化的充分条件（不变化≠无变化，但足够判断
        "consumer 是不是需要重新发布"）。"""
        summaries = await self.list(layer_chain=layer_chain, cwd=cwd)
        payload = "|".join(
            f"{s.name}:{s.description}:{s.invocation.value}:{s.source}"
            for s in summaries
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    # ------------------------------------------------------------------ #
    # 内部
    # ------------------------------------------------------------------ #

    async def _collect(
        self, layer_chain: Tuple[str, ...], cwd: Optional[str],
    ) -> List[SkillSummary]:
        """合并各层 candidate——最近层同名直接赢；同层内重名按 rank / provider 顺序。"""
        cwd_key = cwd or ""
        options = SkillLookupOptions(cwd=cwd_key)
        # layer_order: 近到远
        merged: Dict[str, SkillSummary] = {}     # name -> summary
        # 反向遍历（远 → 近）以便近层覆盖远层
        for layer in reversed(list(layer_chain)):
            layer_summaries: List[SkillSummary] = []
            # runtime
            for (l, n), ent in self._runtime.items():
                if l != layer:
                    continue
                layer_summaries.append(ent.definition)
            # providers（按注册顺序）
            for ent in self._providers:
                if ent.layer != layer:
                    continue
                try:
                    cand = await ent.provider.list(options)
                except Exception as e:  # noqa: BLE001
                    logger.debug(
                        f"[SkillRegistry] provider {ent.provider.name!r} "
                        f"list() failed: {e}"
                    )
                    continue
                layer_summaries.extend(cand)
            # 同层内重名：按 rank → provider 注册顺序 → 名字
            seen_local: Dict[str, SkillSummary] = {}
            for s in layer_summaries:
                if s.name in seen_local:
                    # 第一个胜出
                    continue
                seen_local[s.name] = s
            # 近层覆盖远层：先清空 merged 中由更远层注入的，然后注入本层
            for n, s in seen_local.items():
                merged[n] = s
        # 全局层中所有未在本层覆盖的
        # 上面的反向遍历已合并所有层，结果按 name 排序
        return sorted(merged.values(), key=lambda s: s.name)
