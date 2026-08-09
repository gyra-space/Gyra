"""AsyncTaskCoordinator: 异步任务完成监听与主会话自动恢复。

与 SubagentCoordinator 同理，但针对 AsyncTaskManager 系任务：
- media 模式：generate_video 传 wait=false 时后台生成的媒体任务（有 conv_id）。
- subagent 模式：spawn_agent_task 启动的后台子 Agent 任务。

职责：
1. 跟踪每个会话的 pending 异步任务（写入 gpts_conversations.extra["pending_async_tasks"]，
   供跨进程/重启恢复使用）。
2. 后台 watch_loop 轮询已注册的 AsyncTaskManager，发现已完成未消费任务时，
   若主会话处于 WAITING，则合成「异步任务完成通知」并触发主 resume
   （调 aggregation_chat(gpts_conversations=[conv])，走 is_retry_chat 恢复路径）。
3. recover_all / recover_main：重启后扫 WAITING 会话，按台账/内存状态恢复未完成任务。

消费去重：watch_loop 与 react_master_agent._collect_background_notifications 共用
get_completed_results(consume=True) 的 consumed 标记，二者互斥，避免重复注入。
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

from gyra_serve.agent.heartbeat import acquire_lease, is_lease_expired, is_stale

logger = logging.getLogger(__name__)

# 终止态（与 AsyncTaskStatus 对齐）
_TERMINAL = {"completed", "failed", "timeout", "cancelled"}


class AsyncTaskCoordinator:
    """异步任务完成监听器：跟踪 pending 任务，全部终态则触发主 resume。"""

    def __init__(self, agent_chat: Optional[Any] = None):
        """Args:
            agent_chat: AgentChat 实例，提供 gpts_conversations / aggregation_chat 等依赖。
                可为 None（dry-run 模式，只 log 不实际恢复）。
        """
        self._agent_chat = agent_chat
        self._managers: List[Any] = []
        self._watch_task: Optional[asyncio.Task] = None
        self._watch_interval = 1.0

    # ---------------- manager 注册与后台 watch ----------------

    def add_manager(self, mgr: Any) -> None:
        """注册一个 AsyncTaskManager 实例进入轮询（media 单例 + 各 agent 的 subagent 管理器）。"""
        if mgr is not None and mgr not in self._managers:
            self._managers.append(mgr)

    def start_watch(self) -> None:
        """启动后台完成监听循环（幂等）。"""
        if self._watch_task is not None and not self._watch_task.done():
            return
        try:
            self._watch_task = asyncio.create_task(self._watch_loop())
        except RuntimeError:
            logger.debug(
                "[async-task-coordinator] no running event loop, watch deferred"
            )

    async def _watch_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(self._watch_interval)
                # 先把 manager 里新出现的任务同步进会话 pending 台账（供 #2 WAITING / #4 恢复），
                # 再轮询已完成任务触发 resume。
                await self._sync_pending_from_managers()
                await self._poll_completed()
            except asyncio.CancelledError:
                logger.info("[async-task-coordinator] watch loop cancelled")
                break
            except Exception as e:  # noqa: BLE001 - 循环必须存活
                logger.warning(f"[async-task-coordinator] watch loop error: {e}")

    async def _sync_pending_from_managers(self) -> None:
        """把已注册 manager 中带 conv_id 的任务同步进会话 pending 台账。

        media 工具（gyra-core）与 spawn_agent_task 提交任务时不依赖 gyra-serve 的
        coordinator，因此这里主动扫 manager 的活跃任务，把还没记录的任务补写进
        ``gpts_conversations.extra["pending_async_tasks"]``，保证轮次结束 (#2) 与
        跨进程恢复 (#4) 都能感知到这些任务。
        """
        for mgr in list(self._managers):
            try:
                statuses = mgr.get_all_status()
            except Exception as e:  # noqa: BLE001
                logger.debug(
                    f"[async-task-coordinator] sync get_all_status failed: {e}"
                )
                continue
            for tid, summary in statuses.items():
                cid = summary.get("conv_id", "")
                if not cid:
                    continue
                items = await self._read_pending(cid)
                if any(i.get("task_id") == tid for i in items):
                    continue
                await self.track_task(
                    conv_id=cid,
                    task_id=tid,
                    kind=summary.get("kind", ""),
                    label=summary.get("model") or summary.get("agent_name") or "",
                    status=summary.get("status", "running"),
                )

    async def _poll_completed(self) -> None:
        """扫描所有 manager 的已完成未消费任务，对处于 WAITING 的会话触发 resume。"""
        for mgr in list(self._managers):
            try:
                # 不消费：先探查，只有真正要 resume 时才置 consumed，
                # 避免抢走 react_master_agent think-time 注入的机会。
                completed = mgr.get_completed_results(consume=False, conv_id="")
            except Exception as e:  # noqa: BLE001
                logger.debug(
                    f"[async-task-coordinator] poll manager failed: {e}"
                )
                continue

            by_conv: Dict[str, List[Any]] = {}
            for st in completed:
                # 外部镜像任务（SubAgent async 经 register_external 登记）只作状态
                # 查询，resume 由 SubagentCoordinator 回调驱动，这里跳过避免双重 resume。
                ctx = getattr(getattr(st, "spec", None), "context", None) or {}
                if ctx.get("external"):
                    continue
                cid = getattr(st, "spec", None) and getattr(st.spec, "conv_id", "") or ""
                if cid:
                    by_conv.setdefault(cid, []).append(st)

            for cid, states in by_conv.items():
                if not await self._should_resume(cid):
                    continue
                # 准备 resume：把这一批任务标记已消费，并更新台账
                for st in states:
                    st.consumed = True
                await self._update_pending_terminal(cid, states)
                await self._resume_conv(cid, states)

    async def _should_resume(self, conv_id: str) -> bool:
        """只有主会话处于 WAITING（agent 已结束本轮、正在等后台任务）才自动恢复。"""
        if not self._agent_chat:
            return False
        try:
            conv = self._agent_chat.gpts_conversations.get_by_conv_id(conv_id)
            if not conv:
                return False
            from gyra.agent.core.schema import Status
            return getattr(conv, "state", "") == Status.WAITING.value
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[async-task-coordinator] should_resume check failed: {e}")
            return False

    # ---------------- pending 任务持久化（跨进程/重启恢复用） ----------------

    async def _read_pending(self, conv_id: str) -> List[Dict[str, Any]]:
        if not self._agent_chat:
            return []
        conv = self._agent_chat.gpts_conversations.get_by_conv_id(conv_id)
        if not conv or not getattr(conv, "extra", None):
            return []
        try:
            extra = json.loads(conv.extra) if isinstance(conv.extra, str) else conv.extra
        except (json.JSONDecodeError, TypeError):
            return []
        pending = extra.get("pending_async_tasks", []) if isinstance(extra, dict) else []
        return [i for i in pending if isinstance(i, dict)]

    async def _write_pending(self, conv_id: str, items: List[Dict[str, Any]]) -> None:
        if not self._agent_chat:
            return
        try:
            conv = self._agent_chat.gpts_conversations.get_by_conv_id(conv_id)
            if not conv:
                return
            extra = json.loads(conv.extra) if isinstance(conv.extra, str) else (conv.extra or {})
            if not isinstance(extra, dict):
                extra = {}
            # 保留其他 extra 字段（如 pending_subagents）
            extra["pending_async_tasks"] = items
            session = self._agent_chat.gpts_conversations.get_raw_session()
            from gyra_serve.agent.db.gpts_conversations_db import GptsConversationsEntity
            session.query(GptsConversationsEntity).filter(
                GptsConversationsEntity.conv_id == conv_id
            ).update(
                {GptsConversationsEntity.extra: json.dumps(extra, ensure_ascii=False)},
                synchronize_session="fetch",
            )
            session.commit()
            session.close()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[async-task-coordinator] write_pending failed for {conv_id}: {e}")

    def _is_terminal(self, status: str) -> bool:
        return status in _TERMINAL

    async def track_task(
        self,
        conv_id: str,
        task_id: str,
        kind: str = "",
        label: str = "",
        status: str = "running",
    ) -> None:
        """记录一个刚提交的异步任务到会话 pending 列表（供 #2 WAITING / #4 恢复）。"""
        if not conv_id:
            return
        items = [i for i in await self._read_pending(conv_id) if i.get("task_id") != task_id]
        items.append(
            {
                "task_id": task_id,
                "kind": kind,
                "label": label,
                "status": status,
                "created_at": time.time(),
            }
        )
        await self._write_pending(conv_id, items)

    async def has_pending_tasks(self, conv_id: str) -> bool:
        """是否存在未完成（非终态）的异步任务。用于轮次结束把会话置 WAITING。"""
        # 优先看内存态（同一进程，最准）
        for mgr in list(self._managers):
            try:
                if mgr.has_active_tasks_for_conv(conv_id):
                    return True
            except Exception:  # noqa: BLE001
                continue
        # 兜底看台账
        items = await self._read_pending(conv_id)
        # 交叉校验自愈：台账里的非终态条目若在 manager 中已到终态（如任务
        # conv_id 缺失导致 _poll_completed 漏消费），就地回写终态，避免
        # 台账永久卡 running 使会话永远 WAITING、后续追问全走 resume 路径。
        changed = False
        for it in items:
            if self._is_terminal(it.get("status", "")):
                continue
            status = self._find_task_status(it.get("task_id", ""))
            if status and self._is_terminal(status):
                it["status"] = status
                it["finished_at"] = time.time()
                changed = True
        if changed:
            await self._write_pending(conv_id, items)
        return any(not self._is_terminal(i.get("status", "")) for i in items)

    def _find_task_status(self, task_id: str) -> str:
        """跨已注册 manager 按 task_id 查任务状态；未找到返回 ""。"""
        if not task_id:
            return ""
        for mgr in list(self._managers):
            try:
                statuses = mgr.get_all_status()
            except Exception:  # noqa: BLE001
                continue
            summary = statuses.get(task_id)
            if summary:
                return summary.get("status", "")
        return ""

    def _find_state(self, task_id: str) -> Optional[Any]:
        """跨已注册 manager 按 task_id 查完整任务状态对象；未找到返回 None。"""
        if not task_id:
            return None
        for mgr in list(self._managers):
            try:
                st = mgr.get_status(task_id)
            except Exception:  # noqa: BLE001
                continue
            if st is not None:
                return st
        return None

    # ---------------- 看板项（dock 帧渲染） ----------------

    async def list_board_items(self, conv_id: str) -> List[Dict[str, Any]]:
        """合成 async 任务看板卡片项（供 dock 帧 subagent_board widget 渲染）。

        与 SubagentCoordinator.list_subagent_items 同构，但数据源为
        ``gpts_conversations.extra.pending_async_tasks``（spawn_agent_task /
        media wait=false 后台任务）。用 manager 内存态/台账补全 agent 名、
        任务描述与产物，使刷新/恢复后主对话页仍能看到异步子任务看板。

        外部镜像任务（SubAgent 工具经 register_external 登记、由
        SubagentCoordinator 负责看板）在此跳过，避免与 subagent_board 重复。
        """
        items = await self._read_pending(conv_id)
        if not items:
            return []
        # AsyncTaskStatus -> 前端看板状态
        status_map = {
            "completed": "done",
            "failed": "failed",
            "timeout": "failed",
            "cancelled": "failed",
            "running": "running",
            "pending": "pending",
        }
        board: List[Dict[str, Any]] = []
        for it in items:
            tid = it.get("task_id", "")
            label = it.get("label", "") or ""
            st = self._find_state(tid)
            if st is not None:
                ctx = getattr(getattr(st, "spec", None), "context", None) or {}
                external = ctx.get("external") or ctx.get("source") == "subagent_coordinator"
                if external:
                    continue
            agent_name = label
            if st is not None:
                agent_name = st.spec.agent_name or st.spec.model or label
            task = it.get("summary", "")
            artifacts: List[Dict[str, Any]] = []
            params: Dict[str, Any] = {}
            if st is not None:
                if not task:
                    task = getattr(st.spec, "task_description", "") or ""
                # 媒体档位（时长/分辨率/宽高比等）透传给前端看板展示
                provider_params = (ctx or {}).get("params") or {}
                if provider_params:
                    params["media"] = provider_params
                try:
                    rec = st.to_record()
                    art = rec.get("artifact")
                    if isinstance(art, dict) and art.get("url"):
                        artifacts.append(art)
                except Exception:  # noqa: BLE001
                    pass
            status = it.get("status", "running") or "running"
            board.append(
                {
                    "sub_conv_id": tid,
                    "agent_name": agent_name,
                    "agent_display_name": agent_name,
                    "task": task,
                    "status": status_map.get(status, status),
                    "mode": "async",
                    "params": params,
                    "artifacts": artifacts,
                    "result": it.get("summary", "") or "",
                }
            )
        return board

    async def _update_pending_terminal(
        self, conv_id: str, states: List[Any]
    ) -> None:
        """把已完成任务的状态回写到台账（供 #4 恢复读取）。"""
        try:
            items = await self._read_pending(conv_id)
            if not items:
                return
            for st in states:
                tid = st.spec.task_id
                for it in items:
                    if it.get("task_id") == tid and not self._is_terminal(it.get("status", "")):
                        it["status"] = st.status.value
                        it["summary"] = (st.result_text() or "")[:500]
                        it["finished_at"] = time.time()
            await self._write_pending(conv_id, items)
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[async-task-coordinator] update_pending_terminal: {e}")

    # ---------------- 主会话恢复 ----------------

    async def _resume_conv(self, conv_id: str, states: Optional[List[Any]] = None) -> None:
        """合成「异步任务完成通知」并触发主 resume（is_retry_chat 恢复路径）。

        aggregation_chat 是异步生成器（yield task/chunk/conv_id），需以
        ``async for`` 消费才会真正跑起来，因此这里把它放进独立后台 task 执行，
        不阻塞 coordinator 的 watch 循环。
        """
        if not self._agent_chat:
            logger.info(f"[async-task-coordinator] dry-run resume for {conv_id}")
            return
        try:
            conv = self._agent_chat.gpts_conversations.get_by_conv_id(conv_id)
            if not conv:
                logger.warning(
                    f"[async-task-coordinator] conv {conv_id} not found; skip resume"
                )
                return
            synthesized = self._build_notification(states or [])
            logger.info(
                f"[async-task-coordinator] triggering main resume for {conv_id}"
            )
            # 把异步任务产物注册为主会话交付文件,使主对话文件信息面板可见
            try:
                await self._deliver_artifacts_to_main(
                    conv_id, conv.conv_session_id
                )
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    f"[async-task-coordinator] deliver artifacts to main "
                    f"{conv_id} failed: {e}"
                )
            # 确保会话处于 WAITING（aggregation_chat 内据此走 retry 恢复路径）
            from gyra.agent.core.schema import Status
            await self._safe_set_waiting(conv_id)

            async def _run():
                try:
                    async for _task, _chunk, _new_convid in (
                        self._agent_chat.aggregation_chat(
                            # conv_id 是会话级 id（conv_session_id），agent_conv_id 才是本轮
                            # agent 会话 id；两者都传 agent_conv_id 会导致恢复轮消息的
                            # conv_session_id 被写成 agent_conv_id，造成会话级查询漏消息。
                            conv_id=conv.conv_session_id,
                            agent_conv_id=conv_id,
                            gpts_name=conv.gpts_name,
                            user_query=synthesized,
                            user_code=conv.user_code,
                            sys_code=conv.sys_code,
                            gpts_conversations=[conv],
                        )
                    ):
                        pass
                except Exception as e:  # noqa: BLE001
                    logger.exception(
                        f"[async-task-coordinator] resume run failed for {conv_id}: {e}"
                    )

            try:
                asyncio.create_task(_run())
            except RuntimeError:
                logger.warning(
                    f"[async-task-coordinator] no event loop to schedule resume for {conv_id}"
                )
        except Exception as e:  # noqa: BLE001
            logger.exception(
                f"[async-task-coordinator] resume failed for {conv_id}: {e}"
            )

    async def _safe_set_waiting(self, conv_id: str) -> None:
        """把会话置 WAITING（幂等，忽略状态机守卫告警）并持久化等待原因。"""
        try:
            from gyra.agent.core.schema import Status
            self._agent_chat.gpts_conversations.update(conv_id, Status.WAITING.value)
            # 异步任务等待：resume 由 AsyncTaskCoordinator 注入完成通知驱动，
            # 明确记为 await_async_tasks，供 base_agent._update_recovering 决策
            # （非工具授权 → 不重放，走 LLM 处理完成通知）。
            await self._set_waiting_reason(conv_id, "await_async_tasks")
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[async-task-coordinator] set WAITING skip: {e}")

    async def _set_waiting_reason(self, conv_id: str, waiting_reason: str) -> None:
        """在 gpts_conversations.extra 写入等待原因（保留其他 extra 字段）。

        必须从 DB 读取最新 extra 再合并写入，而不是用内存中的 conv 对象：
        recover_main / _update_pending_terminal 刚把 pending 任务置为终态写入 DB，
        若这里回读内存里的旧 extra（状态仍为 running）再整段写回，会把终态覆盖成
        running，导致台账卡非终态、后续 check_tasks/has_pending_tasks 误判任务未完成，
        进而引发 LLM 反复轮询同一任务（消息循环）。
        """
        try:
            session = self._agent_chat.gpts_conversations.get_raw_session()
            from gyra_serve.agent.db.gpts_conversations_db import GptsConversationsEntity
            row = session.query(GptsConversationsEntity).filter(
                GptsConversationsEntity.conv_id == conv_id
            ).first()
            if row is None:
                return
            extra = json.loads(row.extra) if isinstance(row.extra, str) else (row.extra or {})
            if not isinstance(extra, dict):
                extra = {}
            extra["waiting_reason"] = waiting_reason
            session.query(GptsConversationsEntity).filter(
                GptsConversationsEntity.conv_id == conv_id
            ).update(
                {GptsConversationsEntity.extra: json.dumps(extra, ensure_ascii=False)},
                synchronize_session="fetch",
            )
            session.commit()
            session.close()
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[async-task-coordinator] set waiting_reason skip: {e}")

    @staticmethod
    def _build_notification(states: List[Any]) -> str:
        if not states:
            return "[异步任务完成通知] 后台任务已完成，请根据结果继续。"
        lines = ["[异步任务完成通知] 以下后台任务已完成，请根据结果继续工作："]
        # 按 main_conv_id 聚合子 Agent 媒体产物(图片/视频 URL),注入通知使主对话页
        # 能直接看到产物,而非仅"图片生成成功"文本。轮询任务以 sub_conv 隔离,但其
        # context.main_conv_id 指回主会话(见 MultimediaExecutor)。
        main_conv_ids = {
            st.spec.conv_id for st in states if getattr(st.spec, "conv_id", "")
        }
        artifacts: List[Dict[str, Any]] = []
        if main_conv_ids:
            try:
                from gyra.agent.util.async_task_manager import AsyncTaskManager

                mgr = AsyncTaskManager.media_instance()
                for mc in main_conv_ids:
                    artifacts.extend(mgr.collect_artifacts_for_main_conv(mc))
            except Exception as e:  # noqa: BLE001
                logger.debug(f"[async-task-coordinator] collect artifacts failed: {e}")
        for st in states:
            label = (
                st.spec.model
                or st.spec.agent_name
                or st.spec.kind
                or "?"
            )
            lines.append(f"### Task {st.spec.task_id} ({label})")
            lines.append(f"状态: {st.status.value}")
            text = st.result_text()
            if text:
                lines.append(f"结果:\n{text}")
            if st.error:
                lines.append(f"错误: {st.error}")
            lines.append("")
        if artifacts:
            lines.append("### 生成产物")
            for a in artifacts:
                name = a.get("name") or "产物"
                url = a.get("url") or ""
                mt = a.get("mime_type") or ""
                if url and mt.startswith("image/"):
                    # markdown 图片:聊天渲染器直接展示缩略图
                    lines.append(f"![{name}]({url})")
                elif url:
                    lines.append(f"- [{name}]({url})")
            lines.append("")
        return "\n".join(lines)

    async def _deliver_artifacts_to_main(
        self, conv_id: str, conv_session_id: str
    ) -> int:
        """把异步任务(子 Agent/媒体生成)产物注册为主会话交付文件元数据。

        与 SubagentCoordinator._deliver_child_artifacts_to_main 同理:主会话文件信息
        面板(vis_final 的 deliverable_files)通过 gpts_memory.list_files(conv_id) 读取,
        而异步任务产物只存在于 AsyncTaskManager 台账。这里按主会话聚合产物并以
        DELIVERABLE 类型落库,使主对话文件信息/交付面板可见。幂等:已存在 url 跳过。
        """
        try:
            from gyra.agent.util.async_task_manager import AsyncTaskManager

            mgr = AsyncTaskManager.media_instance()
            artifacts = mgr.collect_artifacts_for_main_conv(conv_id)
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[async-task-coordinator] collect artifacts failed: {e}")
            return 0
        if not artifacts:
            return 0
        try:
            import mimetypes
            import uuid
            from datetime import datetime

            from gyra.agent.core.memory.gpts import AgentFileMetadata, FileType
            from gyra_serve.agent.agents.gyras_memory import (
                MetaGyrasFileMetadataStorage,
            )

            storage = MetaGyrasFileMetadataStorage()
            existing = await storage.list_files(conv_id)
            existing_urls = {
                (f.oss_url or f.preview_url or f.download_url or "").strip()
                for f in existing
            }
            saved = 0
            for a in artifacts:
                url = (a.get("url") or "").strip()
                if not url or url in existing_urls:
                    continue
                name = a.get("name") or url.rstrip("/").rsplit("/", 1)[-1] or "产物"
                mime = a.get("mime_type") or mimetypes.guess_type(name)[0]
                file_meta = AgentFileMetadata(
                    file_id=uuid.uuid4().hex,
                    conv_id=conv_id,
                    conv_session_id=conv_session_id,
                    file_key=f"async_task/{uuid.uuid4().hex}",
                    file_name=name,
                    file_type=FileType.DELIVERABLE.value,
                    local_path=url,
                    file_size=0,
                    oss_url=url,
                    preview_url=url,
                    download_url=url,
                    status="completed",
                    created_by="async_task",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    metadata={"source": "async_task_artifact", "mime_type": mime},
                    mime_type=mime,
                )
                await storage.save_file_metadata(file_meta)
                saved += 1
            if saved:
                logger.info(
                    f"[async-task-coordinator] delivered {saved} artifacts "
                    f"to main conv {conv_id} file panel"
                )
            return saved
        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"[async-task-coordinator] deliver artifacts to main "
                f"{conv_id} failed: {e}"
            )
            return 0

    # ---------------- 跨进程 / 重启恢复 ----------------

    async def recover_main(self, conv_id: str, stale_conv: bool = False) -> None:
        """恢复单个会话：读 pending 任务，按内存/台账判定终态，全部终态则 resume。

        Args:
            conv_id: 会话 ID
            stale_conv: 主会话是否已陈旧（原进程已死）。为 True 时，台账里仍显示
                running 的媒体任务实际已随原进程消亡，无法续跑，直接标记失败，
                避免主会话永久 WAITING。
        """
        items = await self._read_pending(conv_id)
        if not items:
            return
        states: List[Any] = []
        all_terminal = True
        for it in items:
            tid = it.get("task_id", "")
            status = it.get("status", "")
            if self._is_terminal(status):
                continue
            # 非终态：尝试从内存态 / 台账取最新状态
            st = None
            for mgr in list(self._managers):
                try:
                    st = mgr.get_status(tid)
                    if st:
                        break
                except Exception:  # noqa: BLE001
                    continue
            if st is None:
                # 跨进程：查 media 台账
                try:
                    from gyra.agent.util.async_task_manager import AsyncTaskManager
                    rec = AsyncTaskManager.media_instance().get_job(tid)
                    if rec:
                        it["status"] = rec.get("status", "running")
                        it["summary"] = (rec.get("result_preview") or "")[:500]
                        it["finished_at"] = time.time()
                        if not self._is_terminal(it["status"]):
                            if stale_conv:
                                # 原进程已死，媒体协程随之消亡，无法续跑 → 标记失败
                                it["status"] = "failed"
                                it["summary"] = (
                                    "任务在原进程崩溃时丢失，无法恢复生成结果"
                                )
                            else:
                                all_terminal = False
                        continue
                except Exception:  # noqa: BLE001
                    pass
                # 进程重启后内存态丢失且无台账 → 标记失败，避免主会话永久 WAITING
                it["status"] = "failed"
                it["summary"] = "任务在进程重启时丢失，无法恢复结果"
                it["finished_at"] = time.time()
                continue
            it["status"] = st.status.value
            it["summary"] = (st.result_text() or "")[:500]
            it["finished_at"] = time.time()
            states.append(st)

        await self._write_pending(conv_id, items)

        if all_terminal and items:
            await self._resume_conv(conv_id, states)

    async def recover_all(self) -> dict:
        """重启后扫描所有 WAITING 会话（含 pending_async_tasks），恢复未完成任务。

        Returns:
            统计字典：{scanned, resumed, errors}
        """
        stats = {"scanned": 0, "resumed": 0, "errors": 0}
        if not self._agent_chat:
            return stats
        try:
            from gyra_serve.agent.db.gpts_conversations_db import GptsConversationsDao
            dao = GptsConversationsDao()
            waiting_convs = await asyncio.to_thread(dao.get_waiting_convs)
        except Exception as e:  # noqa: BLE001
            logger.exception(f"[async-task-coordinator] recover_all scan failed: {e}")
            stats["errors"] += 1
            return stats

        for conv in waiting_convs:
            conv_id = conv.conv_id
            stats["scanned"] += 1
            try:
                items = await self._read_pending(conv_id)
                if not items:
                    continue
                # 心跳新鲜 + lease 未过期 → 会话在另一进程跑，跳过
                stale_conv = is_stale(
                    getattr(conv, "last_heartbeat", None)
                ) or is_lease_expired(getattr(conv, "lease_expires_at", None))
                if not stale_conv:
                    continue
                acquired = await acquire_lease(conv_id)
                if not acquired:
                    continue
                await self.recover_main(conv_id, stale_conv=True)
                stats["resumed"] += 1
            except Exception as e:  # noqa: BLE001
                logger.exception(
                    f"[async-task-coordinator] recover conv={conv_id} failed: {e}"
                )
                stats["errors"] += 1
        return stats


# ---------------- 全局单例 ----------------

_global_coordinator: Optional[AsyncTaskCoordinator] = None


def set_async_task_coordinator(coordinator: Optional[AsyncTaskCoordinator]) -> None:
    """注册全局 coordinator（由 AgentChat 启动时调用）。"""
    global _global_coordinator
    _global_coordinator = coordinator


def get_async_task_coordinator() -> Optional[AsyncTaskCoordinator]:
    """获取全局 coordinator。未注册返回 None。"""
    return _global_coordinator


__all__ = [
    "AsyncTaskCoordinator",
    "set_async_task_coordinator",
    "get_async_task_coordinator",
]