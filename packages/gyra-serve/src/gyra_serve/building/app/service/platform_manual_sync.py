"""内置平台手册同步服务 — 启动时把代码库里的分模块手册同步进知识空间。

设计目标(对应需求"文随代码更新,文档更新即助手能力更新"):
- 手册文档以 markdown 形式内置在代码库
  ``gyra_app_define/platform_manual/`` 目录,随版本发布。
- 服务启动时检测:
    * 知识空间不存在 → 创建并全量导入;
    * 已存在 → 按 ``source_file``(文件名)比对内容哈希做增量合并,
      内容变更的文档废弃旧 verbat 后灌入新版本,未变的跳过(content_hash
      去重天然幂等)。
- 文档身份标识 = 文件名(manifest 里的 ``file`` 字段);新增文件即新增文档,
  删除文件不强行删除空间内历史文档(保留演进历史,由 wiki 的 supersedes
  版本链表达新旧)。

L0/L1/L2 三层都要落:
- L0 verbat:检索的事实来源(``search_knowledge`` 直接搜它)。
- L1 wiki 文档:由 IngestOrchestrator._generate_wiki 生成,填充 wiki 视图。
- L2 实体关系图:由同一管线的实体归并步骤产出,填充 graph 视图。

wiki/实体的生成依赖 LLM,因此**只能在服务运行时(LLM 可用)执行**;
本同步在启动后台异步触发,不阻塞启动,逐个文档的成败计入统计与日志。
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MANIFEST_NAME = "manifest.json"


def _manual_dir() -> Path:
    return (
        Path(os.path.dirname(os.path.abspath(__file__)))
        / "gyra_app_define"
        / "platform_manual"
    )


def _load_manifest() -> Optional[Dict[str, Any]]:
    path = _manual_dir() / MANIFEST_NAME
    if not path.exists():
        logger.warning("[manual-sync] manifest 不存在: %s", path)
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        logger.warning("[manual-sync] manifest 解析失败: %s", e)
        return None


async def sync_platform_manual(system_app: Any) -> Dict[str, Any]:
    """把内置手册同步到知识空间(L0),并后台触发 L1/L2 生成。返回统计。

    幂等:重复执行不产生重复内容(content_hash 去重 + 文件名级变更检测)。
    任何单点失败只记录日志,不阻断启动。
    """
    manifest = _load_manifest()
    if not manifest:
        return {"ok": False, "reason": "manifest_missing"}

    slug = manifest.get("space_slug") or "platform-manual"
    stats: Dict[str, Any] = {
        "ok": True, "space": slug, "created": False,
        "imported": 0, "updated": 0, "skipped": 0, "failed": 0,
        "wiki_scheduled": 0,
    }

    try:
        from gyra_serve.knowledge.service.service import Service as KnowledgeService
        from gyra.knowledge.types import ExtractMode, Verbat, new_space_id
    except Exception as e:  # noqa: BLE001
        logger.warning("[manual-sync] 知识服务模块不可用: %s", e)
        return {"ok": False, "reason": f"import_error: {e}"}

    ks = KnowledgeService.get_instance(system_app)
    if ks is None:
        logger.warning("[manual-sync] 知识服务未就绪,跳过手册同步")
        return {"ok": False, "reason": "knowledge_service_unavailable"}

    manual_root = _manual_dir()
    docs: List[Dict[str, str]] = manifest.get("docs") or []

    # 确保空间存在并拿到真实 Space 对象与 vault。
    try:
        await _ensure_space(ks, manifest, slug, stats)
        vault = await ks.get_vault(slug)
        space = getattr(ks, "_spaces", {}).get(slug)
        if space is None:
            # get_vault 必定填充 _spaces;防御性保底。
            space = await _resolve_space(ks, slug)
    except Exception as e:  # noqa: BLE001
        logger.warning("[manual-sync] 知识空间就绪失败: %s", e, exc_info=True)
        return {"ok": False, "reason": f"space_error: {e}"}

    # 现有 verbat 按 source_file 建索引(仅未废弃)。
    try:
        existing = await vault.verbat_list(limit=10000)
        by_file = {v.source_file: v for v in existing if not v.deprecated}
    except Exception as e:  # noqa: BLE001
        logger.warning("[manual-sync] 读取现有文档失败: %s", e)
        by_file = {}

    new_verbat_ids: List[Any] = []
    active_ids: List[Any] = []  # 所有活跃手册 verbat(含未变更的),用于 wiki 补偿
    for doc in docs:
        fname = doc.get("file")
        if not fname:
            continue
        fpath = manual_root / fname
        if not fpath.exists():
            logger.warning("[manual-sync] 文档缺失,跳过: %s", fname)
            stats["failed"] += 1
            continue
        try:
            content = fpath.read_text(encoding="utf-8")
            res, vid = await _sync_one(
                vault, space, fname, content, by_file,
                ExtractMode, Verbat, new_space_id,
            )
            stats[res] += 1
            # 活跃的 verbat id(skipped 时取已有的;imported/updated 时取新的)
            active_vid = vid if vid is not None else (
                by_file.get(fname).id if by_file.get(fname) is not None else None
            )
            if active_vid is not None:
                active_ids.append(active_vid)
            if vid is not None and res in ("imported", "updated"):
                new_verbat_ids.append(vid)
        except Exception as e:  # noqa: BLE001
            logger.warning("[manual-sync] 同步文档失败 %s: %s", fname, e)
            stats["failed"] += 1

    # 后台异步触发 L1/L2 生成(wiki + 实体),不阻塞启动。
    # _generate_wiki 幂等(已有 wiki 的 verbat 会跳过),因此对所有活跃手册
    # verbat 都调度一次——既覆盖新/更新文档,也补偿"verbat 已存在但 wiki
    # 尚未生成"的历史空间(例如早期只落了 L0 的空间)。
    if active_ids and space is not None:
        scheduled = _schedule_wiki_generation(ks, vault, space, active_ids)
        stats["wiki_scheduled"] = scheduled

    logger.info(
        "[manual-sync] 完成 space=%s created=%s imported=%d updated=%d "
        "skipped=%d failed=%d wiki_scheduled=%d",
        slug, stats["created"], stats["imported"], stats["updated"],
        stats["skipped"], stats["failed"], stats["wiki_scheduled"],
    )
    return stats


async def _resolve_space(ks: Any, slug: str) -> Any:
    """从知识服务解析 Space 对象(保底路径)。"""
    try:
        spaces = getattr(ks, "_spaces", {})
        if slug in spaces:
            return spaces[slug]
    except Exception:  # noqa: BLE001
        pass
    return None


async def _ensure_space(ks: Any, manifest: Dict[str, Any], slug: str,
                        stats: Dict[str, Any]) -> None:
    """确保知识空间存在;不存在则创建。create_space 内部会经 get_vault 填充
    ks._spaces[slug],因此调用后空间对象立即可取。"""
    existing = getattr(ks, "_spaces", {}).get(slug)
    if existing is not None:
        return
    try:
        await ks.create_space(
            slug=slug,
            backend="local",
            visibility="shared",  # 登录用户可读,便于所有用户使用帮助
        )
        stats["created"] = True
    except Exception as e:  # noqa: BLE001
        # 已存在或并发创建时忽略,后续 get_vault 会解析到既有空间。
        logger.info("[manual-sync] create_space 跳过(可能已存在): %s", e)


async def _sync_one(vault: Any, space: Any, fname: str, content: str,
                    by_file: Dict[str, Any], ExtractMode: Any, Verbat: Any,
                    new_space_id: Any) -> "tuple[str, Optional[Any]]":
    """同步单个文档的 L0 verbat。返回 (结果, 新 verbat_id 或 None)。

    边界处理:当内容"改回某个历史版本"时,新 hash 与一条已废弃的 verbat
    相同。``verbat_add`` 的去重只查 deprecated=0,检测不到它,直接插入会撞
    ``(space_id, content_hash)`` 唯一约束。此时退化为"复活"那条历史记录
    (deprecated 置回 0),而不是新建。
    """
    import hashlib

    new_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    old = by_file.get(fname)

    if old is not None and old.content_hash == new_hash:
        return "skipped", None  # 内容未变,幂等跳过

    space_id = old.space_id if old is not None else (
        getattr(space, "id", None) or new_space_id()
    )

    # 内容变更:废弃旧 verbat 再灌新版(保留演进历史)。
    if old is not None:
        try:
            await vault.verbat_deprecate(old.id)
        except Exception as e:  # noqa: BLE001
            logger.warning("[manual-sync] 废弃旧文档失败 %s: %s", fname, e)

    v = Verbat.create(
        space_id=space_id,
        content=content,
        source_file=fname,
        extract_mode=ExtractMode.UPLOAD,
    )
    try:
        vid = await vault.verbat_add(v)
    except Exception as e:  # noqa: BLE001
        # 唯一约束冲突 = 内容命中了一条已废弃的历史版本 → 复活它。
        revived = await _resurrect_by_hash(vault, space_id, new_hash)
        if revived is None:
            raise
        logger.info("[manual-sync] 命中历史版本,已复活: %s (%s)", fname, revived)
        return ("updated" if old is not None else "imported"), revived
    return ("updated" if old is not None else "imported"), vid


async def _resurrect_by_hash(vault: Any, space_id: Any,
                             content_hash: str) -> Optional[Any]:
    """把指定 content_hash 的已废弃 verbat 复活(deprecated 置 0)。

    返回复活的 verbat_id;找不到或不支持时返回 None。仅本地 SQLite 后端
    需要该兜底(distributed 后端 verbat_add 的去重逻辑不同)。
    """
    try:
        db = getattr(vault, "_db", None)
        if db is None:
            return None
        cursor = await db.execute(
            "SELECT id FROM verbats WHERE space_id=? AND content_hash=? "
            "AND deprecated=1 ORDER BY filed_at DESC LIMIT 1",
            (space_id, content_hash),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        vid = row[0]
        await db.execute(
            "UPDATE verbats SET deprecated=0 WHERE id=?", (vid,)
        )
        await db.commit()
        return vid
    except Exception as e:  # noqa: BLE001
        logger.warning("[manual-sync] 复活历史版本失败: %s", e)
        return None


def _schedule_wiki_generation(ks: Any, vault: Any, space: Any,
                              verbat_ids: List[Any]) -> int:
    """后台异步为新/更新的 verbat 生成 L1 wiki + L2 实体,返回成功调度数。

    用 asyncio.create_task 后台跑,不阻塞启动;每个文档独立 try,单点失败
    不影响其它文档。强引用 task 集合防止被 GC 提前回收。
    """
    orch = getattr(ks, "orchestrator", None)
    gen = getattr(orch, "_generate_wiki", None) if orch is not None else None
    if gen is None:
        logger.warning("[manual-sync] ingest orchestrator 不可用,跳过 wiki 生成")
        return 0

    scheduled = 0
    for vid in verbat_ids:
        try:
            task = asyncio.create_task(_gen_one_wiki(gen, space, vault, vid))
            _BG_TASKS.add(task)
            task.add_done_callback(_BG_TASKS.discard)
            scheduled += 1
        except Exception as e:  # noqa: BLE001
            logger.warning("[manual-sync] 调度 wiki 生成失败 %s: %s", vid, e)
    return scheduled


# 强引用后台任务,防止 GC 回收导致任务静默丢失(对齐 serve.py 的做法)。
_BG_TASKS: "set[asyncio.Task]" = set()


async def _gen_one_wiki(gen: Any, space: Any, vault: Any, verbat_id: Any) -> None:
    """生成单个 verbat 的 wiki(幂等:已存在则跳过),失败仅记录。"""
    try:
        await gen(space, vault, verbat_id, llm_model=None)
        logger.info("[manual-sync] wiki 已生成: verbat=%s", verbat_id)
    except Exception as e:  # noqa: BLE001
        logger.warning("[manual-sync] wiki 生成失败 verbat=%s: %s",
                       verbat_id, e)
