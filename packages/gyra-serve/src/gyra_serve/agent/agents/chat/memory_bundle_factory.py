"""Memory bundle assembly factory (mode-agnostic).

Extracted from ``AgentChat._build_agent_by_gpts`` so both the
SINGLE_AGENT/NATIVE_APP branch (resource_memory driven) and the AUTO_PLAN
branch (per-workspace memory driven) share the same
store/processor/manager/bundle construction and wiring logic.

Two entry points:

- ``build_memory_bundle``: create memory stores (knowledge-vault first,
  SimpleSQLite fallback), LLM processors, infra components, and the
  ``LongTermMemoryManager`` + ``MemoryIntegrationBundle``. Returns ``None``
  on total failure (caller degrades gracefully).
- ``wire_memory_bundle``: attach the bundle to the built agent —
  ``_memory_bundle`` attribute, read pipeline (dual-key: conv_session_id +
  conv_id), user.md injection, hook-dispatcher bundle registration, and the
  ``MemoryToolPack`` → ``MCPCapability`` injection.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MemorySpaceSpec:
    """One memory space to bind: id (store key) + optional vault slug."""

    memory_id: str
    space_slug: Optional[str] = None
    store_type: Optional[str] = None


def specs_from_memories(memory_config: Any) -> List[MemorySpaceSpec]:
    """Derive specs from ``LongTermMemoryConfig.memories`` (resource_memory path).

    Keeps the original slug-derivation semantics: explicit ``space_slug`` >
    slug-shaped ``memory_id`` > None (forces SQLite fallback).
    """
    specs: List[MemorySpaceSpec] = []
    for mem_item in getattr(memory_config, "memories", None) or []:
        mem_id = mem_item.get("memory_id")
        if not mem_id:
            continue
        specs.append(
            MemorySpaceSpec(
                memory_id=mem_id,
                space_slug=mem_item.get("space_slug")
                or (mem_id.startswith("memory-") and mem_id)
                or None,
                store_type=mem_item.get("store_type"),
            )
        )
    return specs


async def register_memory_curator_cron(system_app: Any, space_slug: str) -> None:
    """幂等注册 idle memory curator cron job（每天凌晨 3 点）。

    job_id 固定为 `memory-curator-{space_slug}`，重复调用时若 job 已存在则跳过。
    cron job 触发时派发 MemoryCurateAgent，message 为 `curate:{space_slug}`，
    agent 在 _run_memory_task 里识别该前缀走 curate_space 全量整理路径。

    注意：`cron.get_job` / `cron.add_job` 都是 async def，必须 await；早年缺 await
    会让 `get_job` 返回未启动的 coroutine（非 None），命中幂等早退分支，导致定时
    任务永不注册、且无任何日志（既不成功也不报错）。
    """
    try:
        from gyra.cron.types import (
            CronJobCreate,
            CronPayload,
            CronSchedule,
            PayloadKind,
            ScheduleKind,
            SessionMode,
        )
        from gyra_serve.cron.config import SERVE_SERVICE_COMPONENT_NAME
        from gyra_serve.cron.service.service import Service as CronService
    except Exception as e:  # noqa: BLE001
        logger.warning(
            f"[memory-factory] cron modules unavailable, skip curator cron: {e}"
        )
        return

    try:
        cron = system_app.get_component(SERVE_SERVICE_COMPONENT_NAME, CronService)
    except Exception as e:  # noqa: BLE001
        logger.warning(
            f"[memory-factory] cron service unavailable for slug={space_slug}: {e}"
        )
        return

    job_id = f"memory-curator-{space_slug}"
    try:
        existing = await cron.get_job(job_id)
        if existing is not None:
            return
    except Exception as e:  # noqa: BLE001
        logger.warning(
            f"[memory-factory] curator cron get_job failed for {job_id}, "
            f"will attempt add: {e}"
        )

    await cron.add_job(
        CronJobCreate(
            id=job_id,
            name=f"Memory Curator for {space_slug}",
            description="Daily idle curator: L1 umbrella merge + classification + backup",
            enabled=True,
            schedule=CronSchedule(
                kind=ScheduleKind.CRON, expr="0 3 * * *", tz="Asia/Shanghai"
            ),
            payload=CronPayload(
                kind=PayloadKind.AGENT_TURN,
                message=f"curate:{space_slug}",
                agent_id="MemoryCurateAgent",
                session_mode=SessionMode.ISOLATED,
                timeout_seconds=1800,
            ),
        )
    )
    logger.info(
        f"[memory-factory] registered memory curator cron job_id={job_id} (0 3 * * *)"
    )


async def build_memory_bundle(
    system_app: Any,
    llm_provider: Any,
    *,
    app_code: str,
    memory_config: Any,
    specs: Sequence[MemorySpaceSpec],
) -> Optional[Any]:
    """Build stores + processors + infra + manager/bundle. None on failure."""
    if not specs:
        return None
    try:
        from gyra.agent.core.memory.longterm_manager import (
            LongTermMemoryManager,
            MemoryIntegrationBundle,
            MemorySpaceStrategy,
        )
        from gyra.storage.memory import LLMMemoryProcessor
        from gyra_ext.storage.memory.knowledge_vault_store import (
            KnowledgeVaultMemoryConfig,
            KnowledgeVaultMemoryStore,
        )
        from gyra_serve.knowledge.service.service import (
            Service as KnowledgeService,
        )
    except Exception as dep_e:  # noqa: BLE001
        logger.warning(f"[memory-factory] memory deps unavailable: {dep_e}")
        return None

    memory_stores: Dict[str, Any] = {}
    strategies: Dict[str, Any] = {}
    ks = None
    try:
        ks = KnowledgeService.get_instance(system_app)
    except Exception as ks_e:
        logger.warning(f"[memory-factory] KnowledgeService unavailable: {ks_e}")

    for spec in specs:
        mem_id = spec.memory_id
        space_slug = spec.space_slug
        store_type = spec.store_type

        # Prefer the knowledge-vault path when we have a slug OR the
        # memory_id looks like a slug (migration: old apps without explicit
        # store_type but slug-shaped id).
        store = None
        if ks is not None and space_slug and (
            store_type == "knowledge_vault" or mem_id.startswith("memory-")
        ):
            try:
                vault = await ks.get_vault(space_slug)
                kv_cfg = KnowledgeVaultMemoryConfig(
                    space_slug=space_slug,
                    enable_kg=memory_config.enable_kg,
                )
                store = KnowledgeVaultMemoryStore(
                    config=kv_cfg,
                    vault=vault,
                    system_app=system_app,
                )
                logger.info(
                    f"[memory-factory] Created KnowledgeVaultMemoryStore "
                    f"for slug={space_slug}"
                )
                # 注册 idle curator cron job（幂等：job_id 固定，重复注册时
                # get_job 命中即跳过）
                try:
                    await register_memory_curator_cron(system_app, space_slug)
                except Exception as cron_e:
                    logger.warning(
                        f"[memory-factory] register memory curator cron "
                        f"for slug={space_slug} failed: {cron_e}"
                    )
            except Exception as kv_e:
                logger.warning(
                    f"[memory-factory] KnowledgeVault store creation failed "
                    f"for slug={space_slug}: {kv_e}; falling back to SimpleSQLite"
                )
                store = None

        if store is None:
            from gyra_ext.storage.memory.simple_sqlite_store import (
                SimpleSQLiteMemoryConfig,
                SimpleSQLiteMemoryStore,
            )

            fallback_cfg = SimpleSQLiteMemoryConfig(
                enable_kg=memory_config.enable_kg,
            )
            store = SimpleSQLiteMemoryStore(
                config=fallback_cfg,
                index_name=mem_id,
            )
            logger.info(f"[memory-factory] Created SimpleSQLite store for {mem_id}")

        memory_stores[mem_id] = store
        strategies[mem_id] = MemorySpaceStrategy(
            space_id=mem_id,
            auto_extraction=memory_config.auto_memory,
            kg_extraction=memory_config.enable_kg,
        )

    if not memory_stores:
        return None

    from gyra.storage.memory.hybrid_search import HybridSearchEngine
    from gyra.storage.memory.lifecycle import DefaultLifecycleHooks
    from gyra.storage.memory.promotion import MemoryPromotionEngine
    from gyra.storage.memory.recall_tracker import RecallTracker
    from gyra.storage.memory.snapshot import FrozenSnapshotManager
    from gyra_serve.memory.recall_stats_store import create_recall_stats_backend

    # 为每个 space 建 LLMMemoryProcessor。优先用传入的 llm_provider（chat 自己
    # 的 working LLM client）；生产路径下它是 None（controller.py 用
    # SimpleAgentChat(self.system_app) 实例化时不注入），此时从 ModelConfigCache
    # 取第一个可用模型，构造 AIWrapper 让它跑一遍 _init_provider 的
    # secrets/env/placeholder 解析，再取其 _provider。LLMProvider ABC 与
    # LLMClient 在 generate(req) / models() 上签名一致，可鸭子类型喂给
    # LLMMemoryProcessor。
    processors: Dict[str, Any] = {}
    llm_client = llm_provider
    if llm_client is None:
        try:
            from gyra.agent.core.llm_config import AgentLLMConfig
            from gyra.agent.util.llm.llm_client import AIWrapper
            from gyra.agent.util.llm.model_config_cache import ModelConfigCache

            all_models = ModelConfigCache.get_all_models()
            if all_models:
                model_name = all_models[0]
                cfg_dict = ModelConfigCache.get_config(model_name) or {}
                temp_llm_config = AgentLLMConfig.from_dict(cfg_dict)
                wrapper = AIWrapper(llm_config=temp_llm_config)
                llm_client = wrapper._provider
                if llm_client is not None:
                    logger.info(
                        f"[memory-factory] Built LLMProvider "
                        f"(provider={temp_llm_config.provider}, "
                        f"model={temp_llm_config.model}) "
                        f"via AIWrapper for memory processor"
                    )
                else:
                    logger.warning(
                        "[memory-factory] AIWrapper resolved no provider; "
                        "tier2/tier3 LLM extraction will be skipped"
                    )
            else:
                logger.warning(
                    "[memory-factory] ModelConfigCache empty; "
                    "tier2/tier3 LLM extraction will be skipped"
                )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[memory-factory] Failed to build LLMProvider via AIWrapper: {e}")
            llm_client = None

    if llm_client is not None:
        for mem_id in memory_stores.keys():
            try:
                processors[mem_id] = LLMMemoryProcessor(llm_client=llm_client)
            except Exception as proc_e:
                logger.warning(
                    f"[memory-factory] LLMMemoryProcessor creation failed "
                    f"for {mem_id}: {proc_e}"
                )
        logger.info(
            f"[memory-factory] Built {len(processors)} LLMMemoryProcessor(s) "
            f"for memory spaces"
        )
    else:
        logger.warning(
            "[memory-factory] no llm_provider and no ModelConfigCache fallback; "
            "tier2/tier3 LLM extraction will be skipped"
        )

    # 持久化召回统计：走主库（[service.web.database]），分布式部署下各节点
    # 共享同一份统计、重启 promotion 不冷启动；主库未初始化（如单测/工具态）
    # 时退化为纯内存追踪。
    recall_tracker = RecallTracker(backend=create_recall_stats_backend())
    promotion_engine = MemoryPromotionEngine(recall_tracker=recall_tracker)
    lifecycle_hooks = DefaultLifecycleHooks(
        memory_store=next(iter(memory_stores.values()), None)
    )
    snapshot_manager = FrozenSnapshotManager()
    hybrid_search = HybridSearchEngine()
    # 把全部组件注入 manager —— curate_session 通过
    # getattr(self, "_promotion_engine", None) 等读取，不注入则 tier3
    # promotion/snapshot 全是 None 而变成 0ms no-op。
    manager = LongTermMemoryManager(
        config=memory_config,
        memory_stores=memory_stores,
        processors=processors,
        strategies=strategies,
        recall_tracker=recall_tracker,
        hybrid_search_engine=hybrid_search,
        lifecycle_hooks=lifecycle_hooks,
        snapshot_manager=snapshot_manager,
        promotion_engine=promotion_engine,
    )
    memory_bundle = MemoryIntegrationBundle(
        config=memory_config,
        manager=manager,
        processors=processors,
        strategies=strategies,
        recall_tracker=recall_tracker,
        hybrid_search=hybrid_search,
        lifecycle_hooks=lifecycle_hooks,
        snapshot_manager=snapshot_manager,
        promotion_engine=promotion_engine,
    )
    logger.info(
        f"[memory-factory] Memory bundle created for {app_code} "
        f"with {len(memory_stores)} stores"
    )
    return memory_bundle


async def wire_memory_bundle(
    recipient: Any,
    bundle: Any,
    system_app: Any,
    *,
    user_id: Optional[str] = None,
    conv_id: Optional[str] = None,
    conv_session_id: Optional[str] = None,
    capability_pack: Any = None,
    default_wing: str = "default",
) -> None:
    """Attach the bundle to the built agent. Every step degrades on failure."""
    # Inject bundle to agent via private attribute
    recipient._memory_bundle = bundle
    # 装配读路径管线（prefetch/scrub/静态块）。按 conv_session_id 键控跨轮
    # 共享：serve 每轮换 conv_uid，按轮键控 prefetch 永远跨轮 miss。同时按
    # conv_id 补一把键 —— V1 react_master 用轮次 conv_id 查 pipeline
    # （react_master_agent._load_memory_static_block），查不到会 lazy 新建
    # 空 pipeline 导致 user.md/静态块丢失。
    try:
        from gyra.agent.core.memory.hook_dispatcher import (
            get_memory_pipeline as _get_session_pipeline,
        )
        from gyra.agent.core.memory.hook_dispatcher import (
            register_memory_pipeline as _register_session_pipeline,
        )
        from gyra.agent.core.memory.read_pipeline import MemoryReadPipeline

        _sess_id = conv_session_id or conv_id
        _pipeline = _get_session_pipeline(_sess_id) if _sess_id else None
        if _pipeline is None:
            _pipeline = MemoryReadPipeline()
            if _sess_id:
                _register_session_pipeline(_sess_id, _pipeline)
        if conv_id and conv_id != _sess_id:
            _register_session_pipeline(conv_id, _pipeline)
        # 注入当前用户 user.md 私有记忆块（跨空间共享），与 AGENTS.md 一起
        # 进入冻结的静态记忆块（失败仅降级）。
        if user_id:
            from gyra_serve.agent.agents.chat.agents_md_injection import (
                build_user_md_block,
            )

            block = await build_user_md_block(system_app, user_id)
            if block:
                _pipeline.set_user_md_block(block)
        bundle.pipeline = _pipeline
    except Exception as pipe_e:  # noqa: BLE001
        logger.warning(f"[memory-factory] Memory pipeline wiring failed: {pipe_e}")

    # Register the bundle with the conversation's HookManager so the memory
    # dispatcher can find it, and so the default memory hooks (tier 1/2/3)
    # get appended — either now (if HookManager already exists) or deferred
    # to init_hook_manager.
    try:
        if conv_id and getattr(recipient, "memory", None) is not None:
            recipient.memory.gpts_memory.register_memory_bundle(conv_id, bundle)
    except Exception as hook_e:
        logger.warning(f"[memory-factory] Memory hook registration failed: {hook_e}")

    # Inject memory tools so the agent can actively search/save memories and
    # query/edit the KG.
    try:
        if bundle.manager.has_stores():
            from gyra_serve.agent.resource.tool.memory_tool import MemoryToolPack

            # 解析当前用户的私有记忆空间 vault（user.md 写入通道）。
            user_vault = None
            if user_id:
                try:
                    from gyra_serve.knowledge.service.service import (
                        Service as KnowledgeService,
                    )

                    _ks = KnowledgeService.get_instance(system_app)
                    if _ks is not None:
                        user_vault = await _ks.get_or_create_user_space(user_id)
                except Exception as uv_e:  # noqa: BLE001
                    logger.warning(
                        f"[memory-factory] resolve user memory space failed: {uv_e}"
                    )

            memory_tool_pack = MemoryToolPack(
                memory_stores=bundle.manager.memory_stores,
                wing=getattr(bundle.config, "wing", None) or default_wing,
                user_vault=user_vault,
            )
            await memory_tool_pack.preload_resource()

            # Phase D: 记忆工具包包装为 MCPCapability（工具已 preload，纯
            # declare 投影），挂进 capability_pack 供 facade 渲染。
            from gyra.core.interface.resource.capability import CapabilityPack
            from gyra_serve.agent.capabilities.mcp import MCPCapability

            memory_cap = MCPCapability.from_tools(
                list(memory_tool_pack.sub_resources),
                name="memory_tools",
            )
            if capability_pack is not None:
                capability_pack.add(memory_cap)
            elif getattr(recipient, "capability_pack", None) is None:
                from gyra.core.interface.resource.capability import (
                    CapabilityPack as _CP,
                )

                recipient.capability_pack = _CP([memory_cap])
            else:
                recipient.capability_pack.add(memory_cap)
            logger.info(
                f"[memory-factory] Memory tools injected: "
                f"{len(bundle.manager.memory_stores)} stores"
            )
    except Exception as tool_e:
        logger.warning(f"[memory-factory] Memory tool injection failed: {tool_e}")

    logger.info(
        f"[memory-factory] Memory bundle wired ({len(bundle.manager.memory_stores)} stores)"
    )
