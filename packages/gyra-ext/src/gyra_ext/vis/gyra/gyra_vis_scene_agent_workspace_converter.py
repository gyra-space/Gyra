"""场景空间 AgentWorkspace 可视化转换器。

产出结构化 vis 产物 {render_name, planning, execution[], summary, deliverable_files[], task_files[], panel_view},前端 AgentWorkspaceRenderer 消费。
注册靠子类扫描(render_name = scene_agent_workspace)。

数据契约(与运行时核实):
- stream_msg LLM 流式: {message_id, sender, content(累计文本), thinking, status:"running"}
- stream_msg 工具调用: {type:"all"|"incr", action_report:[ActionOutput]} (pydantic 对象,属性访问)
- gpt_msg: GptsMessage,.content 为 assistant 文本,.action_report 为 List[dict](DB 序列化形态)
- messages: List[GptsMessage] 全量历史(每次调用都传入,用于幂等重建)
- plans_map: Dict[str, GptsPlan] 计划(可能为空)

交付文件展示(类似 vis manus):
- deliverable_files: Agent 运行期间通过 deliver_file / create_file 标记的交付文件
- task_files: 所有任务文件(含交付文件)
- panel_view: 任务结束时自动切换到交付文件视图(deliverable)或摘要视图(summary)
"""
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union

from gyra_ext.vis.gyra.gyra_vis_manus_converter import (
    GyraIncrVisManusConverter,
)

logger = logging.getLogger(__name__)

# 单步输出截断上限,避免超大工具结果撑爆 SSE / 前端渲染
_MAX_OUTPUT_CHARS = 4000
# 工具执行中占位文案,不作为有效 output
_RUNNING_PLACEHOLDERS = {"执行中", "执行中..", "执行中..."}
# 人类角色标识(GptsMessage.role / sender 上的人类侧取值)
_HUMAN_ROLES = {"Human", "user", "human", "UserProxy"}
# 最终回答的占位 action,不作为工具步骤展示(其内容即 summary)
_SKIP_TOOL_NAMES = {"blank"}

# 文件 render_type → 大厅 Exhibit kind 映射(与前端 RENDER_TYPE_TO_KIND 对齐)
_RENDER_TYPE_TO_KIND = {
    "iframe": "html",
    "image": "image",
    "video": "video",
    "audio": "audio",
    "pdf": "pdf",
    "markdown": "markdown",
    "code": "code",
    "text": "text",
    "table": "table",
    "slides": "slides",
    "chart": "chart",
    "archive": "file",
}


class SceneAgentWorkspaceConverter(GyraIncrVisManusConverter):
    """场景空间 AgentWorkspace 转换器。

    不复用 manus 的 VIS tag 输出,改为维护一份累积的结构化状态
    (工具步骤 / 阶段回复 / 思考 / 计划),每次推送全量输出,
    前端按 id 合并。
    """

    SCENE_TAG = "scene_agent_workspace"

    # opt-in:vis_messages/vis_final 的消息合并默认屏蔽 Human 消息,
    # 本转换器需要用户消息(渲染用户气泡),故声明保留。
    include_user_messages = True

    def __init__(self, paths: Optional[str] = None, **kwargs):
        super().__init__(paths, **kwargs)
        # key 前缀区分来源: tool-{action_id} / think-{message_id} / narr-{message_id}
        # value = (step_dict, ts_str);ts 用于跨来源按时间交错排序
        self._scene_items: Dict[str, Tuple[Dict[str, Any], str]] = {}
        # message_id -> (assistant 文本, ts_str);最新一条进 summary,其余凝固为步骤
        self._scene_narrations: Dict[str, Tuple[str, str]] = {}
        # 交付文件 / 任务文件(类似 vis manus,任务结束时从 gpts_memory 或 messages 收集)
        self._deliverable_files: List[Dict[str, Any]] = []
        self._task_files: List[Dict[str, Any]] = []
        self._panel_view: str = "execution"
        # 大厅入驻内容(通用 Exhibit 协议):交付文件 + 工具产出文件按 exhibit_id 幂等入驻
        self._lobby_exhibits: List[Dict[str, Any]] = []

    @property
    def reuse_name(self):
        # 通用页(/chat 历史会话、应用详情)不认识 scene_agent_workspace 协议,
        # 声明回退到 vis_manus 布局:通用页用 manus converter 实时组装同一份消息数据
        return "vis_manus"

    @property
    def render_name(self):
        return "scene_agent_workspace"

    @property
    def web_use(self) -> bool:
        return True

    @property
    def description(self) -> str:
        return "场景空间 AgentWorkspace 结构化可视化布局"

    # ------------------------------------------------------------------
    # 解析辅助
    # ------------------------------------------------------------------
    @staticmethod
    def _safe_json_loads(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return value
        if not isinstance(value, str):
            return None
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _report_get(report: Any, key: str) -> Any:
        """兼容 ActionOutput(pydantic 对象)与 dict 两种形态。"""
        if isinstance(report, dict):
            return report.get(key)
        return getattr(report, key, None)

    @staticmethod
    def _ts_str(value: Any) -> str:
        """归一化时间戳为可比较字符串(datetime / str / None)。"""
        if value is None:
            return ""
        iso = getattr(value, "isoformat", None)
        if callable(iso):
            try:
                return iso()
            except Exception:  # noqa: BLE001 - 时间戳异常不影响主流程
                return ""
        return str(value)

    def _tool_name_from_view(self, view: Any) -> Optional[str]:
        """从 d-tool vis fence 中提取 tool_name 兜底。"""
        if not isinstance(view, str) or "```" not in view:
            return None
        try:
            body = view.split("\n", 1)[1].rsplit("```", 1)[0]
            data = json.loads(body)
            return data.get("tool_name")
        except (IndexError, ValueError, TypeError):
            return None

    @staticmethod
    def _determine_render_type(file_name: str, mime_type: Optional[str] = None) -> str:
        """扩展父类推定:补音频/表格/幻灯片类型(仅场景空间协议认识,不影响 vis manus)。"""
        name_lower = (file_name or "").lower()
        mime_lower = (mime_type or "").lower()
        # Audio
        if any(name_lower.endswith(ext) for ext in (".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac")):
            return "audio"
        if mime_lower.startswith("audio/"):
            return "audio"
        # Table(csv 可前端解析;xlsx 等二进制表格前端引导下载/新窗口)
        if any(name_lower.endswith(ext) for ext in (".csv", ".xlsx", ".xls", ".numbers")):
            return "table"
        if "text/csv" in mime_lower or "spreadsheet" in mime_lower:
            return "table"
        # Slides(pptx 引导下载;单文件 HTML 幻灯片走父类 iframe)
        if any(name_lower.endswith(ext) for ext in (".pptx", ".ppt", ".key")):
            return "slides"
        if "presentation" in mime_lower:
            return "slides"
        # staticmethod 内零参 super() 无实例可用,显式调用父类静态方法
        return GyraIncrVisManusConverter._determine_render_type(file_name, mime_type)

    # ------------------------------------------------------------------
    # 大厅入驻内容(Exhibit)构建
    # ------------------------------------------------------------------
    def _upsert_lobby_exhibit(self, exhibit: Dict[str, Any]) -> None:
        """按 exhibit_id 幂等入驻(同 ID 覆盖,保证可重复推送)。"""
        eid = exhibit.get("exhibit_id")
        if not eid:
            return
        for i, existing in enumerate(self._lobby_exhibits):
            if existing.get("exhibit_id") == eid:
                self._lobby_exhibits[i] = exhibit
                return
        self._lobby_exhibits.append(exhibit)

    def _file_info_to_exhibit(
        self, file_info: Dict[str, Any], step_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """工具产出文件(output_files 项)→ 大厅 Exhibit 描述符。"""
        file_id = file_info.get("file_id", "")
        if not file_id:
            return None
        file_name = file_info.get("file_name", "") or f"file_{file_id}"
        mime_type = file_info.get("mime_type")
        oss_url = file_info.get("oss_url")
        preview_url = file_info.get("preview_url")
        if oss_url and str(oss_url).startswith("gyra-fs://"):
            url = oss_url
        else:
            url = preview_url or oss_url or file_info.get("download_url")
        render_type = self._determine_render_type(file_name, mime_type)
        kind = _RENDER_TYPE_TO_KIND.get(render_type, "file")
        provenance: Dict[str, Any] = {}
        if step_id:
            provenance["step_id"] = step_id
        return {
            "exhibit_id": f"file_{file_id}",
            "kind": kind,
            "title": file_name,
            "source": {
                "url": url,
                "mime_type": mime_type,
                "file_size": file_info.get("file_size", 0),
            },
            "provenance": provenance or None,
            "actions": ["preview", "download"],
        }

    def _deliverable_dict_to_exhibit(self, f: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """交付文件 dict → 大厅 Exhibit 描述符(与步骤产出共用 file_<id> 命名,天然去重)。"""
        file_id = f.get("file_id", "")
        if not file_id:
            return None
        kind = _RENDER_TYPE_TO_KIND.get(str(f.get("render_type") or ""), "file")
        return {
            "exhibit_id": f"file_{file_id}",
            "kind": kind,
            "title": f.get("file_name") or f"file_{file_id}",
            "source": {
                "url": f.get("content_url") or f.get("download_url"),
                "mime_type": f.get("mime_type"),
                "file_size": f.get("file_size", 0),
            },
            "provenance": None,
            "actions": ["preview", "download"],
        }

    def _upsert_tool_step(self, report: Any) -> None:
        action_id = self._report_get(report, "action_id")
        if not action_id:
            return
        key = f"tool-{action_id}"

        state = str(self._report_get(report, "state") or "").lower()
        success = self._report_get(report, "is_exe_success")
        if success is False or state in ("failed", "error", "blocked"):
            status = "failed"
        elif state in ("running", "pending", "executing", "todo", "waiting", "retrying"):
            status = "running"
        else:
            status = "done"

        tool = (
            self._report_get(report, "action")
            or self._tool_name_from_view(self._report_get(report, "view"))
            or self._report_get(report, "action_name")
            or self._report_get(report, "name")
            or "工具调用"
        )
        if str(tool).lower() in _SKIP_TOOL_NAMES:
            return

        raw_input = self._report_get(report, "action_input")
        action_input = raw_input if isinstance(raw_input, dict) else self._safe_json_loads(raw_input)

        content = self._report_get(report, "content")
        output = None
        if isinstance(content, str) and content.strip() and content.strip() not in _RUNNING_PLACEHOLDERS:
            output = content.strip()[:_MAX_OUTPUT_CHARS]

        existing = self._scene_items.get(key)
        step = existing[0] if existing else {
            "id": str(action_id),
            "type": "tool_call",
            "title": str(tool),
            "status": "running",
            "action": str(tool),
            "action_input": None,
            "output": None,
            "artifact": None,
            "vis": None,
            "exhibit": None,
        }
        step["title"] = str(tool)
        step["action"] = str(tool)
        step["status"] = status
        if action_input is not None:
            step["action_input"] = action_input
        if output is not None:
            step["output"] = output
        # 工具产出文件 → 大厅 Exhibit:首个挂到步骤上(点击步骤大厅打开),全部入驻大厅
        output_files = self._report_get(report, "output_files")
        if isinstance(output_files, (list, tuple)):
            for file_info in output_files:
                if not isinstance(file_info, dict):
                    continue
                exhibit = self._file_info_to_exhibit(file_info, step_id=str(action_id))
                if exhibit is None:
                    continue
                if step.get("exhibit") is None:
                    step["exhibit"] = exhibit
                self._upsert_lobby_exhibit(exhibit)
        ts = self._ts_str(self._report_get(report, "start_time")) or (existing[1] if existing else "")
        self._scene_items[key] = (step, ts)

    def _ingest_assistant_text(
        self, message_id: Optional[str], content: Any, ts: Any = None, append: bool = False
    ) -> None:
        """登记 assistant 文本(阶段回复/最终回答候选,最新一条进 summary)。

        append=True 用于 LLM 流式:stream_msg.content 是增量 delta,需追加;
        来自持久化消息的全量文本则整体替换。
        """
        if not isinstance(content, str) or not content:
            return
        mid = message_id or "unknown"
        prev_text, prev_ts = self._scene_narrations.get(mid, ("", ""))
        text = (prev_text + content) if append else content
        self._scene_narrations[mid] = (text.strip() if not append else text, self._ts_str(ts) or prev_ts)

    def _ingest_thinking(self, message_id: Optional[str], thinking: Any, live: bool, ts: Any = None) -> None:
        if not isinstance(thinking, str) or not thinking.strip():
            return
        mid = message_id or "unknown"
        key = f"think-{mid}"
        prev_step, prev_ts = self._scene_items.get(key, ({}, ""))
        # 流式 thinking 同样是增量 delta,追加而非替换
        prev_output = prev_step.get("output", "") if isinstance(prev_step, dict) else ""
        output = (prev_output + thinking) if live else thinking.strip()
        self._scene_items[key] = ({
            "id": key,
            "type": "thinking",
            "title": "深度思考",
            "status": "running" if live else "done",
            "action": None,
            "action_input": None,
            "output": output[:_MAX_OUTPUT_CHARS],
            "artifact": None,
            "vis": None,
        }, self._ts_str(ts) or prev_ts)

    def _ingest_user_message(self, msg: Any) -> None:
        """用户消息 → user 步骤(展示用户问题,气泡渲染)。"""
        content = getattr(msg, "content", None)
        text = ""
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            # 多模态:拼接 text 片段
            parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text") or ""))
            text = " ".join(p for p in parts if p)
        if not text.strip():
            return
        mid = getattr(msg, "message_id", None) or uuid.uuid4().hex
        key = f"user-{mid}"
        self._scene_items[key] = ({
            "id": key,
            "type": "user",
            "title": "我",
            "status": "done",
            "action": None,
            "action_input": None,
            "output": text.strip()[:_MAX_OUTPUT_CHARS],
            "artifact": None,
            "vis": None,
        }, self._ts_str(getattr(msg, "created_at", None)))

    def _ingest_message(self, msg: Any) -> None:
        """从一条 GptsMessage(已完成)摄取步骤 / 思考 / 回复。"""
        role = str(getattr(msg, "role", "") or "")
        sender = str(getattr(msg, "sender", "") or "")
        if role in _HUMAN_ROLES or sender in _HUMAN_ROLES:
            self._ingest_user_message(msg)
            return
        if role == "tool":
            return
        message_id = getattr(msg, "message_id", None)
        ts = getattr(msg, "created_at", None)

        reports = getattr(msg, "action_report", None)
        if isinstance(reports, (list, tuple)):
            for report in reports:
                self._upsert_tool_step(report)

        self._ingest_thinking(message_id, getattr(msg, "thinking", None), live=False, ts=ts)
        self._ingest_assistant_text(message_id, getattr(msg, "content", None), ts=ts)

    def _ingest_stream_msg(self, stream_msg: Union[Dict, str]) -> None:
        if not isinstance(stream_msg, dict):
            return
        message_id = stream_msg.get("message_id") or stream_msg.get("uid")
        ts = stream_msg.get("start_time")

        reports = stream_msg.get("action_report")
        if isinstance(reports, (list, tuple)):
            for report in reports:
                self._upsert_tool_step(report)

        if stream_msg.get("thinking"):
            self._ingest_thinking(message_id, stream_msg.get("thinking"), live=True, ts=ts)
        if stream_msg.get("content"):
            # stream content 是增量 delta,追加
            self._ingest_assistant_text(message_id, stream_msg.get("content"), ts=ts, append=True)

    def _build_planning(self, plans_map: Optional[Dict[str, Any]], messages: List[Any]) -> Optional[Dict[str, Any]]:
        if not plans_map:
            return None
        plans = sorted(
            plans_map.values(),
            key=lambda p: (getattr(p, "conv_round", 0) or 0, getattr(p, "sub_task_num", 0) or 0),
        )
        if not plans:
            return None

        status_map = {"todo": "pending", "running": "running", "complete": "done", "failed": "failed"}
        steps = []
        for p in plans:
            state = str(getattr(p, "state", "") or "").lower()
            steps.append({
                "id": str(getattr(p, "task_uid", None) or getattr(p, "sub_task_id", "") or uuid.uuid4().hex),
                "title": str(getattr(p, "sub_task_title", None) or getattr(p, "sub_task_content", "") or "子任务"),
                "status": status_map.get(state, "pending"),
            })

        goal = getattr(plans[0], "task_round_title", None) or ""
        if not goal:
            for msg in messages:
                sender = str(getattr(msg, "sender", "") or "")
                role = str(getattr(msg, "role", "") or "")
                if sender in _HUMAN_ROLES or role in _HUMAN_ROLES:
                    content = getattr(msg, "content", None)
                    if isinstance(content, str) and content.strip():
                        goal = content.strip()[:200]
                        break
        return {"goal": goal or "任务计划", "steps": steps}

    def _build_view(self, plans_map: Optional[Dict[str, Any]], messages: List[Any]) -> Dict[str, Any]:
        # 最新一条 assistant 文本 → summary;之前的阶段回复凝固为 execution 步骤
        narr_ids = list(self._scene_narrations.keys())
        summary: Optional[str] = None
        frozen_narr: List[Tuple[str, str]] = []  # (text, ts)
        if narr_ids:
            summary = self._scene_narrations[narr_ids[-1]][0]
            frozen_narr = [self._scene_narrations[mid] for mid in narr_ids[:-1]]

        execution: List[Tuple[Dict[str, Any], str]] = list(self._scene_items.values())
        for text, ts in frozen_narr:
            execution.append(({
                "id": f"narr-{uuid.uuid5(uuid.NAMESPACE_URL, text[:64]).hex[:12]}",
                "type": "thinking",
                "title": "阶段回复",
                "status": "done",
                "action": None,
                "action_input": None,
                "output": text[:_MAX_OUTPUT_CHARS],
                "artifact": None,
                "vis": None,
            }, ts))

        # 按时间交错排序(无 ts 的排后,稳定)
        execution.sort(key=lambda item: item[1] or "￿")
        # ts 透出给前端:跨轮次(agent conv)合并时按时间交错
        ordered_steps = [{**step, "ts": ts or None} for step, ts in execution]

        return {
            "render_name": "scene_agent_workspace",
            "planning": self._build_planning(plans_map, messages),
            "execution": ordered_steps,
            "summary": summary,
            "deliverable_files": self._deliverable_files,
            "task_files": self._task_files,
            "panel_view": self._panel_view,
            "lobby_exhibits": self._lobby_exhibits,
        }

    def _render(self, plans_map: Optional[Dict[str, Any]], messages: List[Any]) -> str:
        body = json.dumps(self._build_view(plans_map, messages), ensure_ascii=False)
        return f"```{self.SCENE_TAG}\n{body}\n```"

    # ------------------------------------------------------------------
    # 交付文件收集(复用父类 manus converter 的文件收集能力)
    # ------------------------------------------------------------------
    async def _collect_scene_files(
        self,
        messages: List[Any],
        senders_map: Optional[Dict[str, Any]] = None,
        main_agent_name: Optional[str] = None,
        conv_id: Optional[str] = None,
        is_working: bool = True,
    ) -> None:
        """收集交付文件和任务文件,更新 self._deliverable_files / self._task_files。

        策略(与 manus converter 一致):
        - 任务结束(is_working=False):优先从 gpts_memory 获取完整文件列表
        - 增量推送(is_working=True)或 gpts_memory 兜底:从 messages 收集
        """
        task_files: List[Any] = []
        deliverable_files: List[Any] = []

        # 任务结束时优先从 gpts_memory 获取完整文件列表
        if not is_working and conv_id and senders_map and main_agent_name:
            try:
                task_files, deliverable_files = await self._collect_files_from_gpts_memory(
                    conv_id, senders_map, main_agent_name
                )
                logger.info(
                    f"[SceneWorkspace] collected {len(deliverable_files)} deliverable files from gpts_memory"
                )
            except Exception as e:
                logger.warning(f"[SceneWorkspace] gpts_memory collection failed: {e}")

        # 兜底 / 增量:从 messages 收集
        if not deliverable_files and messages:
            try:
                task_files, deliverable_files = self._collect_files_from_messages(messages)
                logger.info(
                    f"[SceneWorkspace] collected {len(deliverable_files)} deliverable files from messages"
                )
            except Exception as e:
                logger.warning(f"[SceneWorkspace] message fallback collection failed: {e}")

        self._task_files = [self._task_file_to_dict(f) for f in task_files]
        self._deliverable_files = [self._deliverable_file_to_dict(f) for f in deliverable_files]

        # 交付文件入驻大厅(与步骤产出共用 file_<id>,幂等去重)
        for f in self._deliverable_files:
            exhibit = self._deliverable_dict_to_exhibit(f)
            if exhibit is not None:
                self._upsert_lobby_exhibit(exhibit)

        # 确定 panel_view:交付文件优先 > 摘要 > 执行
        if self._deliverable_files:
            self._panel_view = "deliverable"
        elif self._scene_narrations:
            self._panel_view = "summary"
        else:
            self._panel_view = "execution"

    @staticmethod
    def _task_file_to_dict(f: Any) -> Dict[str, Any]:
        """ManusTaskFileItem(pydantic) → dict。"""
        if isinstance(f, dict):
            return f
        to_dict = getattr(f, "to_dict", None)
        if callable(to_dict):
            return to_dict()
        return {
            "file_id": getattr(f, "file_id", ""),
            "file_name": getattr(f, "file_name", ""),
            "file_type": getattr(f, "file_type", ""),
            "file_size": getattr(f, "file_size", 0),
            "mime_type": getattr(f, "mime_type", None),
            "oss_url": getattr(f, "oss_url", None),
            "preview_url": getattr(f, "preview_url", None),
            "download_url": getattr(f, "download_url", None),
            "description": getattr(f, "description", None),
            "created_at": getattr(f, "created_at", None),
            "object_path": getattr(f, "object_path", None),
        }

    @staticmethod
    def _deliverable_file_to_dict(f: Any) -> Dict[str, Any]:
        """ManusDeliverableFile(pydantic) → dict。"""
        if isinstance(f, dict):
            return f
        to_dict = getattr(f, "to_dict", None)
        if callable(to_dict):
            return to_dict()
        return {
            "file_id": getattr(f, "file_id", ""),
            "file_name": getattr(f, "file_name", ""),
            "mime_type": getattr(f, "mime_type", None),
            "file_size": getattr(f, "file_size", 0),
            "content_url": getattr(f, "content_url", None),
            "download_url": getattr(f, "download_url", None),
            "object_path": getattr(f, "object_path", None),
            "render_type": getattr(f, "render_type", "iframe"),
        }

    # ------------------------------------------------------------------
    # 入口:运行期增量推送 + 历史最终视图
    # ------------------------------------------------------------------
    async def visualization(
        self,
        messages: List[Any],
        plans_map: Optional[Dict[str, Any]] = None,
        gpt_msg: Any = None,
        stream_msg: Optional[Union[Dict, str]] = None,
        new_plans: Optional[List[Any]] = None,
        is_first_chunk: bool = False,
        incremental: bool = False,
        senders_map: Optional[Dict[str, Any]] = None,
        main_agent_name: Optional[str] = None,
        is_first_push: bool = False,
        **kwargs,
    ) -> str:
        """产出结构化 vis tag 包裹的 JSON(每次全量,前端按 id 合并)。"""
        for msg in messages or []:
            self._ingest_message(msg)
        if gpt_msg is not None:
            self._ingest_message(gpt_msg)
        if stream_msg:
            self._ingest_stream_msg(stream_msg)

        # 收集交付文件(类似 vis manus)
        conv_id = kwargs.get("conv_id") or kwargs.get("cache")
        if conv_id and hasattr(conv_id, "conv_id"):
            conv_id = conv_id.conv_id
        is_working = await self._detect_running(senders_map)
        await self._collect_scene_files(
            messages=messages or [],
            senders_map=senders_map,
            main_agent_name=main_agent_name,
            conv_id=conv_id,
            is_working=is_working,
        )

        return self._render(plans_map, messages or [])

    async def final_view(
        self,
        messages: List[Any],
        plans_map: Optional[Dict[str, Any]] = None,
        senders_map: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> str:
        """历史查询路径(query_chat → vis_final):从持久化消息重建完整视图。"""
        self._scene_items = {}
        self._scene_narrations = {}
        self._deliverable_files = []
        self._task_files = []
        self._lobby_exhibits = []
        self._panel_view = "execution"
        for msg in messages or []:
            self._ingest_message(msg)

        # 收集交付文件:final_view 是历史重建,视为任务已结束
        main_agent_name = kwargs.get("main_agent_name")
        conv_id = kwargs.get("conv_id") or kwargs.get("cache")
        if conv_id and hasattr(conv_id, "conv_id"):
            conv_id = conv_id.conv_id
        await self._collect_scene_files(
            messages=messages or [],
            senders_map=senders_map,
            main_agent_name=main_agent_name,
            conv_id=conv_id,
            is_working=False,
        )

        return self._render(plans_map, messages or [])

    @staticmethod
    async def _detect_running(senders_map: Optional[Dict[str, Any]]) -> bool:
        """检测是否有 agent 仍在运行。"""
        if not senders_map:
            return True  # 未知状态,保守视为运行中(走 messages 路径)
        try:
            from gyra.agent.core.schema import Status
            for v in senders_map.values():
                agent_state = await v.agent_state()
                if agent_state == Status.RUNNING:
                    return True
            return False
        except Exception:
            return True  # 检测失败,保守视为运行中
