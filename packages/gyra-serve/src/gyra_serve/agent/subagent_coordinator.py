"""SubagentCoordinator: 子 Agent 完成监听器。

跟踪 pending_subagents，全 done 则触发主 resume。
设计成可插拔 backend：LocalSubagentBackend（单进程 asyncio.create_task），
未来加 DistributedSubagentBackend（RPC 队列派发到其他机器）。
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

from gyra.agent.core.subagent_handle import (
    SubAgentHandle,
    SubAgentMode,
    SubAgentStatus,
)

logger = logging.getLogger(__name__)


class SubagentCoordinator:
    """子 Agent 完成监听器：跟踪 pending_subagents，全 done 则触发主 resume。

    Usage:
        coordinator = SubagentCoordinator(agent_chat=self)
        await coordinator.register_subagent(main_conv_id, sub_conv_id, mode)
        # ... 子 agent 跑完后 ...
        await coordinator.on_subagent_done(main_conv_id, sub_conv_id, result)
    """

    def __init__(self, agent_chat: Any):
        """Args:
            agent_chat: AgentChat 实例，提供 gpts_conversations / aggregation_chat 等依赖。
        """
        self._agent_chat = agent_chat

    # ---- pending_subagents 持久化（gpts_conversations.extra JSON）----

    async def _read_pending(self, main_conv_id: str) -> List[SubAgentHandle]:
        """从 gpts_conversations.extra 读取 pending_subagents 列表。"""
        conv = self._agent_chat.gpts_conversations.get_by_conv_id(main_conv_id)
        if not conv or not getattr(conv, "extra", None):
            return []
        try:
            extra = json.loads(conv.extra) if isinstance(conv.extra, str) else conv.extra
        except (json.JSONDecodeError, TypeError):
            return []
        pending_list = extra.get("pending_subagents", []) if isinstance(extra, dict) else []
        return [SubAgentHandle.from_dict(item) for item in pending_list]

    async def _write_pending(
        self, main_conv_id: str, handles: List[SubAgentHandle]
    ) -> None:
        """写入 pending_subagents 列表到 gpts_conversations.extra。"""
        conv = self._agent_chat.gpts_conversations.get_by_conv_id(main_conv_id)
        if not conv:
            logger.warning(f"[subagent-coordinator] conv {main_conv_id} not found")
            return
        try:
            extra = json.loads(conv.extra) if isinstance(conv.extra, str) else (conv.extra or {})
        except (json.JSONDecodeError, TypeError):
            extra = {}
        if not isinstance(extra, dict):
            extra = {}
        extra["pending_subagents"] = [h.to_dict() for h in handles]
        # 直接 update extra 字段
        session = self._agent_chat.gpts_conversations.get_raw_session()
        from gyra_serve.agent.db.gpts_conversations_db import GptsConversationsEntity
        session.query(GptsConversationsEntity).filter(
            GptsConversationsEntity.conv_id == main_conv_id
        ).update(
            {GptsConversationsEntity.extra: json.dumps(extra, ensure_ascii=False)},
            synchronize_session="fetch",
        )
        session.commit()
        session.close()

    async def _read_extra(self, main_conv_id: str) -> Dict[str, Any]:
        """读取 gpts_conversations.extra 字典（不存在/损坏时返回空 dict）。"""
        conv = self._agent_chat.gpts_conversations.get_by_conv_id(main_conv_id)
        if not conv or not getattr(conv, "extra", None):
            return {}
        try:
            extra = json.loads(conv.extra) if isinstance(conv.extra, str) else conv.extra
        except (json.JSONDecodeError, TypeError):
            return {}
        return extra if isinstance(extra, dict) else {}

    async def _write_extra(self, main_conv_id: str, extra: Dict[str, Any]) -> None:
        """写回 gpts_conversations.extra。"""
        conv = self._agent_chat.gpts_conversations.get_by_conv_id(main_conv_id)
        if not conv:
            logger.warning(f"[subagent-coordinator] conv {main_conv_id} not found")
            return
        session = self._agent_chat.gpts_conversations.get_raw_session()
        from gyra_serve.agent.db.gpts_conversations_db import GptsConversationsEntity
        session.query(GptsConversationsEntity).filter(
            GptsConversationsEntity.conv_id == main_conv_id
        ).update(
            {GptsConversationsEntity.extra: json.dumps(extra, ensure_ascii=False)},
            synchronize_session="fetch",
        )
        session.commit()
        session.close()

    # ---- 公开接口 ----

    async def register_subagent(
        self,
        main_conv_id: str,
        sub_conv_id: str,
        mode: SubAgentMode,
        agent_name: Optional[str] = None,
        task: Optional[str] = None,
        agent_display_name: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> "tuple[SubAgentHandle, bool]":
        """注册一个子 agent 到 pending 列表。

        防重复提交：同 main_conv 下已有同 (agent_name, 归一化 task) 的非终态
        handle 时，直接返回该 handle 且 created=False，不新建子任务——图片/视频
        生成等昂贵任务不允许 LLM 因误判"任务丢失"而反复重试扣费。

        Returns:
            (handle, created)：created=False 表示复用了在途任务。
        """
        from gyra.agent.util.async_task_manager import normalize_task_text

        norm_task = normalize_task_text(task or "")
        if agent_name and norm_task:
            for h in await self._read_pending(main_conv_id):
                if (
                    not h.is_terminal()
                    and (h.agent_name or "") == agent_name
                    and normalize_task_text(h.task or "") == norm_task
                ):
                    logger.info(
                        f"[subagent-coordinator] dedup: reuse in-flight subagent "
                        f"{h.sub_conv_id} (agent={agent_name}) for main {main_conv_id}"
                    )
                    return h, False

        display_name = agent_display_name or await self._resolve_app_display_name(agent_name) or agent_name
        handle = SubAgentHandle(
            sub_conv_id=sub_conv_id,
            main_conv_id=main_conv_id,
            mode=mode,
            status=SubAgentStatus.RUNNING,
            started_at=time.time(),
            agent_name=agent_name,
            task=task,
            agent_display_name=display_name,
            params=params or {},
        )
        handles = await self._read_pending(main_conv_id)
        handles.append(handle)
        await self._write_pending(main_conv_id, handles)
        await self._emit_board_event(main_conv_id, handles)
        logger.info(
            f"[subagent-coordinator] registered subagent {sub_conv_id} "
            f"(mode={mode.value}, agent={agent_name}) for main {main_conv_id}"
        )
        # 状态镜像到 AsyncTaskManager：check_tasks/wait_tasks 可用 sub_conv_id 查询
        await self._mirror_register(main_conv_id, handle)
        return handle, True

    async def _mirror_register(
        self, main_conv_id: str, handle: SubAgentHandle
    ) -> None:
        """把子 agent 任务镜像登记进 AsyncTaskManager（仅状态，不含执行体）。"""
        try:
            from gyra.agent.util.async_task_manager import (
                AsyncTaskManager,
                AsyncTaskSpec,
            )

            manager = AsyncTaskManager.media_instance()
            await manager.register_external(
                AsyncTaskSpec(
                    task_id=handle.sub_conv_id,
                    agent_name=handle.agent_name or "",
                    task_description=handle.task or "",
                    conv_id=main_conv_id,
                    kind="subagent",
                    context={"source": "subagent_coordinator"},
                )
            )
        except Exception as e:  # noqa: BLE001 - 镜像失败不影响主流程
            logger.warning(
                f"[subagent-coordinator] mirror register failed for "
                f"{handle.sub_conv_id}: {e}"
            )

    def _mirror_complete(
        self, sub_conv_id: str, result: Optional[str] = None, error: Optional[str] = None
    ) -> None:
        """把子 agent 终态同步到 AsyncTaskManager 镜像任务。"""
        try:
            from gyra.agent.util.async_task_manager import AsyncTaskManager

            AsyncTaskManager.media_instance().complete_external(
                sub_conv_id, result=result, error=error
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"[subagent-coordinator] mirror complete failed for {sub_conv_id}: {e}"
            )

    async def _resolve_app_display_name(self, app_code: Optional[str]) -> Optional[str]:
        """把 app_code 解析为可读的 app_name（利于展示目标 Agent）。

        解析失败时返回 None，交由调用方拿 app_code 兜底展示。
        """
        if not app_code:
            return None
        try:
            from gyra_serve.agent.agents.chat.agent_chat import get_app_service

            app_service = get_app_service()
            resp = await app_service.app_detail(app_code, building_mode=False)
            name = getattr(resp, "app_name", None) or getattr(resp, "agent_name", None)
            return name or None
        except Exception as e:  # noqa: BLE001
            logger.debug(
                f"[subagent-coordinator] resolve display name for {app_code} failed: {e}"
            )
            return None

    async def on_subagent_done(
        self, main_conv_id: str, sub_conv_id: str, result: str
    ) -> None:
        """子 agent 成功完成：标记 DONE，若全部完成则触发主 resume。"""
        handles = await self._read_pending(main_conv_id)
        for h in handles:
            if h.sub_conv_id == sub_conv_id:
                h.status = SubAgentStatus.DONE
                h.result = result
                h.finished_at = time.time()
                break
        await self._write_pending(main_conv_id, handles)
        await self._emit_board_event(main_conv_id, handles)
        self._mirror_complete(sub_conv_id, result=result)
        logger.info(
            f"[subagent-coordinator] subagent {sub_conv_id} done for main {main_conv_id}"
        )
        if all(h.is_terminal() for h in handles):
            await self._trigger_main_resume(main_conv_id, handles)

    async def on_subagent_failed(
        self, main_conv_id: str, sub_conv_id: str, error: str
    ) -> None:
        """子 agent 失败：标记 FAILED，若全部完成则触发主 resume（带错误）。"""
        handles = await self._read_pending(main_conv_id)
        for h in handles:
            if h.sub_conv_id == sub_conv_id:
                h.status = SubAgentStatus.FAILED
                h.error = error
                h.finished_at = time.time()
                break
        await self._write_pending(main_conv_id, handles)
        await self._emit_board_event(main_conv_id, handles)
        self._mirror_complete(sub_conv_id, error=error)
        logger.warning(
            f"[subagent-coordinator] subagent {sub_conv_id} failed for main {main_conv_id}: {error}"
        )
        if all(h.is_terminal() for h in handles):
            await self._trigger_main_resume(main_conv_id, handles)

    async def list_subagent_items(self, main_conv_id: str) -> List[Dict[str, Any]]:
        """返回子任务看板卡片项（供场景空间 vis / 其他协议复用）。

        从 gpts_conversations.extra.pending_subagents 读取当前所有子任务状态，
        合成与 d-subagent-board 看板同构的卡片项列表（含待授权态）。
        """
        handles = await self._read_pending(main_conv_id)
        items = []
        for h in handles:
            board_status = "awaiting_authorization" if h.authorization else h.status.value
            items.append(
                {
                    "sub_conv_id": h.sub_conv_id,
                    "agent_name": h.agent_name,
                    "agent_display_name": h.agent_display_name or h.agent_name,
                    "task": h.task,
                    "status": board_status,
                    "mode": h.mode.value,
                    "authorization": h.authorization,
                    "params": h.params or {},
                    "progress": h.progress,
                    "steps": h.steps,
                }
            )
        return items

    async def persist_board(
        self, main_conv_id: str, items: List[Dict[str, Any]]
    ) -> None:
        """把终态子任务看板持久化到 extra（key=subagent_board）。

        pending_subagents 在 resume 时会被清空，若只靠 pending 回放，子任务
        全部完成后看板会从对话页消失。这里单独持久化一份终态看板，供
        _build_dock_frame 在 pending 为空时回退渲染，保证恢复/刷新后仍可见。
        """
        try:
            extra = await self._read_extra(main_conv_id)
            extra["subagent_board"] = items
            await self._write_extra(main_conv_id, extra)
        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"[subagent-coordinator] persist board failed for main={main_conv_id}: {e}"
            )

    async def list_persistent_board(
        self, main_conv_id: str
    ) -> List[Dict[str, Any]]:
        """读取持久化的终态子任务看板（pending 清空后回放用）。"""
        try:
            extra = await self._read_extra(main_conv_id)
            items = extra.get("subagent_board")
            return items if isinstance(items, list) else []
        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"[subagent-coordinator] list persistent board failed for "
                f"main={main_conv_id}: {e}"
            )
            return []

    async def update_progress(
        self,
        main_conv_id: str,
        sub_conv_id: str,
        progress: int,
        steps: Optional[list] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """更新某个子 agent 进度并推送 board 事件（供子 Agent 执行中上报）。"""
        handles = await self._read_pending(main_conv_id)
        for h in handles:
            if h.sub_conv_id == sub_conv_id:
                h.progress = progress
                if steps is not None:
                    h.steps = steps
                if params is not None:
                    h.params = {**(h.params or {}), **params}
                break
        await self._write_pending(main_conv_id, handles)
        await self._emit_board_event(main_conv_id, handles)

    async def _emit_board_event(
        self, main_conv_id: str, handles: List[SubAgentHandle]
    ) -> None:
        """状态变更时推 subagent_board dock widget 到主会话（全量重写）。

        在 register/done/failed 的 _write_pending 之后调用，把当前所有子任务状态
        合成一个 subagent_board dock widget，经 gpts_memory.push_dock_widget
        推送到主会话，前端按 type 注册表渲染（Composer Dock 协议）。
        """
        try:
            items = await self.list_subagent_items(main_conv_id)
            if not self._agent_chat.memory:
                return
            widget = build_subagent_board_widget(items, main_conv_id)
            await self._agent_chat.memory.push_dock_widget(
                conv_id=main_conv_id, widget=widget
            )
        except Exception as e:
            logger.warning(
                f"[subagent-coordinator] emit board event failed for main={main_conv_id}: {e}"
            )

    async def emit_authorization_needed(
        self, main_conv_id: str, sub_conv_id: str, question: str
    ) -> None:
        """子 agent 需要用户授权时通知主 agent。

        置 handle.authorization + 推 d-subagent-board 围栏标"待授权"，让主会话顶部
        面板对应子任务高亮待授权态。用户审批后由 intervention service 或 tool_action
        回调清除 authorization 并触发主 resume。
        """
        handles = await self._read_pending(main_conv_id)
        for h in handles:
            if h.sub_conv_id == sub_conv_id:
                h.authorization = question
                break
        await self._write_pending(main_conv_id, handles)
        await self._emit_board_event(main_conv_id, handles)
        logger.info(
            f"[subagent-coordinator] subagent {sub_conv_id} awaiting authorization "
            f"for main {main_conv_id}: {question[:80]}"
        )

    async def _rebuild_subagent_transcript(
        self, sub_conv_id: str, max_messages: int = 5
    ) -> str:
        """Tier 3.3: 扫描子 agent 的 gpts_messages，重建崩溃前的 thinking chain。

        提取最近 N 条消息的 thinking + action_report，合成为可读的进展摘要，
        让主 agent resume 时能拿到子 agent 崩溃前的部分成果。

        Args:
            sub_conv_id: 子 agent 会话 ID
            max_messages: 最多回溯多少条消息（避免超长摘要）

        Returns:
            重建的 transcript 字符串；无消息返回空字符串。
        """
        try:
            from gyra_serve.agent.db.gpts_messages_db import GptsMessagesDao
            dao = GptsMessagesDao()
            messages = await dao.get_by_conv_id(sub_conv_id)
        except Exception as e:
            logger.warning(
                f"[subagent-coordinator] failed to load transcript for sub={sub_conv_id}: {e}"
            )
            return ""

        if not messages:
            return ""

        # 取最近 N 条，按时间正序输出
        recent = list(messages)[-max_messages:]
        lines = []
        for msg in recent:
            sender = getattr(msg, "sender_name", None) or "?"
            thinking = getattr(msg, "thinking", None) or ""
            content = getattr(msg, "content", None) or ""
            # action_report 是 JSON 字符串，含 tool 调用结果
            action_report_raw = getattr(msg, "action_report", None)

            # 提取 thinking（截断到 200 字符避免超长）
            if thinking:
                t = thinking.strip()[:200]
                lines.append(f"    [{sender} think] {t}")

            # 提取 action_report 里的 tool 调用
            if action_report_raw:
                try:
                    if isinstance(action_report_raw, str):
                        reports = json.loads(action_report_raw)
                    else:
                        reports = action_report_raw
                    if isinstance(reports, list):
                        for r in reports:
                            tool_name = r.get("name") or r.get("action") or "?"
                            success = r.get("is_exe_success", True)
                            content_short = (r.get("content") or "")[:150]
                            mark = "✓" if success else "✗"
                            lines.append(
                                f"    [{sender} tool {mark} {tool_name}] {content_short}"
                            )
                except (json.JSONDecodeError, TypeError, AttributeError):
                    pass
            elif content and not thinking:
                # 没有 thinking 也没有 action_report，用 content 兜底
                c = content.strip()[:150]
                if c:
                    lines.append(f"    [{sender}] {c}")

        return "\n".join(lines)

    async def _trigger_main_resume(
        self, main_conv_id: str, handles: List[SubAgentHandle]
    ) -> None:
        """所有子 agent 完成：把结果作为 user message 注入，触发主 resume。

        主会话此时应在 WAITING 状态（由 agent_chat turn-end 决策写入）。
        调 aggregation_chat 时传 gpts_conversations=[entity]，让 aggregation_chat
        内部检测到 WAITING → is_retry_chat=True，走 _inner_chat 的 retry 恢复路径。

        Tier 3.3: 对 FAILED 且无 result 的子 agent，扫描其 gpts_messages 重建
        thinking chain，让主 agent 拿到崩溃前的部分进展。
        """
        results_lines = []
        for h in handles:
            if h.status == SubAgentStatus.DONE:
                results_lines.append(f"  - 子对话 {h.sub_conv_id} 完成：\n{h.result or '(空结果)'}")
            elif h.status == SubAgentStatus.FAILED:
                # Tier 3.3: 尝试重建崩溃前的 transcript
                transcript = await self._rebuild_subagent_transcript(h.sub_conv_id)
                if transcript:
                    results_lines.append(
                        f"  - 子对话 {h.sub_conv_id} 崩溃前部分进展：\n{transcript}\n"
                        f"    失败原因：{h.error or '(未知错误)'}"
                    )
                else:
                    results_lines.append(f"  - 子对话 {h.sub_conv_id} 失败：{h.error or '(未知错误)'}")
        synthesized = "子 agent 全部完成：\n" + "\n".join(results_lines)

        logger.info(
            f"[subagent-coordinator] triggering main resume for {main_conv_id} "
            f"({len(handles)} subagents)"
        )
        # 清空 pending 列表（resume 后不再 pending）
        await self._write_pending(main_conv_id, [])
        # 用最后一次 handles 状态合成终态 items
        terminal_items = []
        for h in handles:
            terminal_items.append(
                {
                    "sub_conv_id": h.sub_conv_id,
                    "agent_name": h.agent_name,
                    "agent_display_name": h.agent_display_name or h.agent_name,
                    "task": h.task,
                    "status": h.status.value,
                    "mode": h.mode.value,
                    "authorization": h.authorization,
                    "params": h.params or {},
                    "progress": h.progress,
                    "steps": h.steps,
                }
            )
        # 持久化终态看板：pending 清空后，恢复/刷新对话页仍能看到子任务完成情况
        await self.persist_board(main_conv_id, terminal_items)
        # 补发终态 board 事件：让前端子任务看板同步为全部完成态，避免残留「运行中」
        try:
            if self._agent_chat.memory:
                widget = build_subagent_board_widget(terminal_items, main_conv_id)
                await self._agent_chat.memory.push_dock_widget(
                    conv_id=main_conv_id, widget=widget
                )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"[subagent-coordinator] emit terminal board failed for main={main_conv_id}: {e}"
            )

        # 读 main conv entity，拿 gpts_name(app_code) 与 state
        try:
            conv = self._agent_chat.gpts_conversations.get_by_conv_id(main_conv_id)
            if not conv:
                logger.warning(
                    f"[subagent-coordinator] main conv {main_conv_id} not found; cannot resume"
                )
                return
            await self._safe_set_waiting(main_conv_id)

            # aggregation_chat 是异步生成器（yield task/chunk/conv_id），必须 async for
            # 消费才会真正执行（直接 await 会抛 TypeError）。放进独立后台 task，
            # 不阻塞子 agent 完成回调。
            async def _run():
                try:
                    async for _task, _chunk, _new_convid in (
                        self._agent_chat.aggregation_chat(
                            conv_id=main_conv_id,
                            agent_conv_id=main_conv_id,
                            gpts_name=conv.gpts_name,
                            user_query=synthesized,
                            user_code=conv.user_code,
                            sys_code=conv.sys_code,
                            # 让 aggregation_chat 内部检测 WAITING → is_retry_chat=True
                            gpts_conversations=[conv],
                        )
                    ):
                        pass
                except Exception as e:  # noqa: BLE001
                    logger.exception(
                        f"[subagent-coordinator] resume run failed for {main_conv_id}: {e}"
                    )

            try:
                asyncio.create_task(_run())
            except RuntimeError:
                logger.warning(
                    f"[subagent-coordinator] no event loop to schedule resume "
                    f"for {main_conv_id}"
                )
        except Exception as e:
            logger.exception(
                f"[subagent-coordinator] failed to trigger main resume for {main_conv_id}: {e}"
            )

    async def _safe_set_waiting(self, conv_id: str) -> None:
        """把会话置 WAITING（幂等，忽略状态机守卫告警）。

        aggregation_chat 内据此走 retry 恢复路径。
        """
        try:
            from gyra.agent.core.schema import Status
            self._agent_chat.gpts_conversations.update(conv_id, Status.WAITING.value)
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[subagent-coordinator] set WAITING skip: {e}")

    async def recover_main(self, main_conv_id: str) -> None:
        """启动恢复：扫 main 的 pending_subagents，按子状态 + 心跳决策。

        用于 PR 4 的 RecoveryDaemon 启动时恢复。

        Tier 3.2/3.3: 对 RUNNING 状态的子 agent，按 lease 状态判断：
        - lease 已过期 → 子 agent 真死 → 标记 FAILED + 重建 transcript → 触发 main resume
        - lease 未过期 → 子 agent 在另一进程跑 → 注册监听等子完成
        """
        handles = await self._read_pending(main_conv_id)
        if not handles:
            return

        # Tier 3.2: 对 RUNNING 子 agent 检查 lease 是否过期
        from gyra_serve.agent.heartbeat import is_lease_expired
        from gyra_serve.agent.db.gpts_conversations_db import GptsConversationsDao
        dao = GptsConversationsDao()
        modified = False
        for h in handles:
            if h.status != SubAgentStatus.RUNNING:
                continue
            try:
                wid, expires_at = await asyncio.to_thread(dao.get_lease_holder, h.sub_conv_id)
                if is_lease_expired(expires_at):
                    # 子 agent 真死（lease 过期）→ 标记 FAILED
                    logger.warning(
                        f"[subagent-coordinator] recover_main: sub={h.sub_conv_id} "
                        f"lease expired (holder={wid}), marking FAILED"
                    )
                    h.status = SubAgentStatus.FAILED
                    h.error = f"subagent crashed (lease expired, last holder={wid})"
                    h.finished_at = time.time()
                    modified = True
            except Exception as e:
                logger.warning(
                    f"[subagent-coordinator] recover_main: failed to check lease for "
                    f"sub={h.sub_conv_id}: {e}"
                )

        if modified:
            await self._write_pending(main_conv_id, handles)

        all_done = all(h.is_terminal() for h in handles)
        if all_done:
            await self._trigger_main_resume(main_conv_id, handles)
            return

        # 还有未完成的子 agent（lease 仍新鲜，在另一进程跑）→ 注册监听等子完成
        logger.info(
            f"[subagent-coordinator] recover_main: {main_conv_id} has "
            f"{sum(1 for h in handles if not h.is_terminal())} still-running subagents"
        )


# ---- PR 2 Tier 1.4: 全局 coordinator 单例（供 SubAgent 工具访问）----

_global_coordinator: Optional["SubagentCoordinator"] = None


def set_subagent_coordinator(coordinator: Optional["SubagentCoordinator"]) -> None:
    """注册全局 coordinator（由 AgentChat 启动时调用）。"""
    global _global_coordinator
    _global_coordinator = coordinator


def get_subagent_coordinator() -> Optional["SubagentCoordinator"]:
    """获取全局 coordinator。未注册返回 None。"""
    return _global_coordinator


def build_subagent_board_widget(items: List[Dict[str, Any]], main_conv_id: str) -> dict:
    """构建输入区 Dock 的 subagent_board widget（Composer Dock 协议）。

    取代旧的 d-subagent-board 围栏字符串：生产者直接调 gpts_memory.push_dock_widget
    投递本 widget，前端按 type 注册表渲染，不再需要字符串拦截。
    """
    completed = sum(1 for it in items if it["status"] in ("done", "failed"))
    return {
        "id": f"subagent_board_{main_conv_id}",
        "type": "subagent_board",
        "kind": "replace",
        "payload": {
            "uid": f"subagent_board_{main_conv_id}",
            "type": "all",
            "items": items,
            "total_count": len(items),
            "completed_count": completed,
        },
    }
