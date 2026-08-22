"""Spill seam — 超大对象（工具结果 / 用户输入）落盘与 locator 注入（对齐 DSH ``ctx.spillStore``）。

**问题**：工具结果（搜索结果、长文档、爬虫页等）经常超过 LLM 上下文窗口；
直接注入 tool 消息会撑爆 prompt 长度并把昂贵的 token 浪费在"已知结果"上。

**Spill 策略**：
  1. 大对象（超过 ``SpillPolicy.max_inline_chars``）落盘到 ``SpillStore``；
  2. 注入 LLM 的 tool 消息替换为 **locator**（"结果已 spill 到 spill://id；
     调用 spill_get(id) 可按需取回相关片段"）；
  3. 投影器把 spill 占位的 tool 消息折叠为短文本，模型按需取回时再注入全文。

**SpillStore** 接口：
  - ``put(content: str | bytes) -> spill_id``：落盘返回 id；
  - ``get(spill_id: str) -> str | bytes``：按 id 取回（O(1) 命中）；
  - ``exists(spill_id: str) -> bool``；
  - ``delete(spill_id: str) -> None``；
  - ``size_bytes(spill_id: str) -> int``。

**实现**：
  - ``FileSpillStore``：本地文件 spill（默认 ``{DATA_DIR}/v2_spill``）；
  - 业务可注入远端 spill（Redis / S3）实现 ``SpillStore`` 接口。

**SpillPolicy**：
  - ``max_inline_chars``：超过该值 spill（默认 20000 字符 ≈ 5000 token）；
  - ``max_summary_chars``：inline 时截断到该值（默认 2000 字符）；
  - ``keep_original_in_event_output``：是否在 event.output 同时保留原文（默认 False）。

用法::

    store = FileSpillStore(os.path.join(DATA_DIR, "v2_spill"))
    policy = SpillPolicy()
    sm = SpillManager(store, policy)

    # 投影前处理消息列表
    sm.compact_tool_results(messages)  # 替换超大 tool 消息为 locator

    # 模型按需取回全文
    full = sm.resolve_locator("spill://abcd1234")
"""
from __future__ import annotations

import hashlib
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Union


# ------------------------------------------------------------------
# SpillStore 接口
# ------------------------------------------------------------------

class SpillStore(Protocol):
    """Spill 存储后端协议（业务可换 Redis / S3 实现）。"""

    def put(self, content: Union[str, bytes], *, hint: str = "") -> str: ...
    def get(self, spill_id: str) -> Union[str, bytes]: ...
    def exists(self, spill_id: str) -> bool: ...
    def delete(self, spill_id: str) -> None: ...
    def size_bytes(self, spill_id: str) -> int: ...


# ------------------------------------------------------------------
# FileSpillStore：本地文件实现
# ------------------------------------------------------------------

class FileSpillStore:
    """本地文件 spill 存储。spill_id = content 的 sha256 + 时间戳后缀。"""

    SCHEME = "spill://"

    def __init__(self, data_dir: str) -> None:
        os.makedirs(data_dir, exist_ok=True)
        self._data_dir = data_dir

    def _path(self, spill_id: str) -> str:
        safe = spill_id.replace("..", "_").replace("/", "_")
        return os.path.join(self._data_dir, safe)

    def put(self, content: Union[str, bytes], *, hint: str = "") -> str:
        if isinstance(content, str):
            content = content.encode("utf-8")
        digest = hashlib.sha256(content).hexdigest()[:16]
        # 用 time.time_ns() 纳秒精度 + uuid4 short 保证高频 put 时 id 仍唯一
        ts = time.time_ns()
        unique = uuid.uuid4().hex[:8]
        suffix = ""
        if hint:
            # hint 仅用于区分语义（同名 content 可区分），如 "tool_result"、"file"；
            # 不会影响 id 唯一性
            suffix = ""
        spill_id = f"{digest}-{ts}-{unique}"
        path = self._path(spill_id)
        # 已存在则跳过（hash 一致 + 同 ts 概率极低）
        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(content)
        return f"{self.SCHEME}{spill_id}"

    def get(self, spill_id: str) -> Union[str, bytes]:
        if spill_id.startswith(self.SCHEME):
            spill_id = spill_id[len(self.SCHEME):]
        path = self._path(spill_id)
        if not os.path.exists(path):
            raise KeyError(f"spill not found: {spill_id}")
        with open(path, "rb") as f:
            return f.read()

    def exists(self, spill_id: str) -> bool:
        if spill_id.startswith(self.SCHEME):
            spill_id = spill_id[len(self.SCHEME):]
        return os.path.exists(self._path(spill_id))

    def delete(self, spill_id: str) -> None:
        if spill_id.startswith(self.SCHEME):
            spill_id = spill_id[len(self.SCHEME):]
        path = self._path(spill_id)
        if os.path.exists(path):
            os.remove(path)

    def size_bytes(self, spill_id: str) -> int:
        if spill_id.startswith(self.SCHEME):
            spill_id = spill_id[len(self.SCHEME):]
        path = self._path(spill_id)
        if not os.path.exists(path):
            return 0
        return os.path.getsize(path)


# ------------------------------------------------------------------
# SpillPolicy
# ------------------------------------------------------------------

@dataclass
class SpillPolicy:
    """Spill 策略。"""
    max_inline_chars: int = 20000  # ≈ 5000 token（gpt-4 等多数模型 1 token ≈ 4 chars）
    max_summary_chars: int = 2000  # inline 截断后展示给模型的摘要
    # inline 摘要前缀（拼到 spill 占位消息前）
    locator_template: str = (
        "[内容已 spill 到 {spill_id}，共 {size_bytes} 字符。"
        "前 {summary_chars} 字符：\n{summary}\n\n"
        "如需全文，可调用 spill_get('{spill_id}') 取回]"
    )
    # 强制不 spill 的角色（如 system 消息）
    skip_roles: tuple = ("system",)

    def should_spill(self, content: str) -> bool:
        return len(content) > self.max_inline_chars


# ------------------------------------------------------------------
# SpillManager
# ------------------------------------------------------------------

class SpillManager:
    """Spill 总入口：管理 store + policy + 消息预处理。"""

    SCHEME = "spill://"

    def __init__(self, store: SpillStore, policy: Optional[SpillPolicy] = None) -> None:
        self._store = store
        self._policy = policy or SpillPolicy()

    @property
    def store(self) -> SpillStore:
        return self._store

    @property
    def policy(self) -> SpillPolicy:
        return self._policy

    def put(self, content: Union[str, bytes], *, hint: str = "") -> str:
        """落盘并返回 spill://id。"""
        return self._store.put(content, hint=hint)

    def get(self, spill_id: str) -> Union[str, bytes]:
        return self._store.get(spill_id)

    def resolve_locator(self, locator: str) -> Union[str, bytes]:
        """取回 spill://... 对应原文。"""
        return self._store.get(locator)

    def maybe_spill_string(self, text: str) -> str:
        """若超过阈值则 spill 并返回 locator；否则返回原文。"""
        if not self._policy.should_spill(text):
            return text
        return self._store.put(text, hint="inline_spill")

    def compact_tool_results(
        self,
        messages: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """把超大 tool 消息折叠为 spill locator + 摘要。

        修改后的 messages 是新列表（不修改原 list）。
        """
        out: List[Dict[str, Any]] = []
        for msg in messages:
            role = msg.get("role")
            if role in self._policy.skip_roles:
                out.append(msg)
                continue
            content = msg.get("content")
            if not isinstance(content, str):
                out.append(msg)
                continue
            if not self._policy.should_spill(content):
                # 截断到 max_summary_chars 以做硬降级
                if len(content) > self._policy.max_summary_chars:
                    msg = dict(msg)
                    msg["content"] = content[: self._policy.max_summary_chars] + (
                        "...[truncated]"
                    )
                out.append(msg)
                continue
            # spill
            spill_id = self._store.put(content, hint=f"role={role}")
            summary = content[: self._policy.max_summary_chars]
            msg = dict(msg)
            msg["content"] = self._policy.locator_template.format(
                spill_id=spill_id,
                size_bytes=len(content),
                summary_chars=len(summary),
                summary=summary + ("...[truncated]" if len(content) > len(summary) else ""),
            )
            msg["_spill_locator"] = spill_id
            out.append(msg)
        return out

    def compact_event_output(self, event_output: dict) -> dict:
        """处理单个 StepEvent.output：把 tool result 的大 content spill。

        返回新 dict（不修改入参）。
        """
        if not isinstance(event_output, dict):
            return event_output
        content = event_output.get("content")
        if not isinstance(content, str):
            return event_output
        if not self._policy.should_spill(content):
            return event_output
        spill_id = self._store.put(content, hint="tool_result")
        new_output = dict(event_output)
        new_output["content"] = self._policy.locator_template.format(
            spill_id=spill_id,
            size_bytes=len(content),
            summary_chars=self._policy.max_summary_chars,
            summary=content[: self._policy.max_summary_chars] + "...",
        )
        new_output["_spill_locator"] = spill_id
        return new_output


# ------------------------------------------------------------------
# 工厂
# ------------------------------------------------------------------

def create_default_spill_manager(data_dir: Optional[str] = None) -> SpillManager:
    """创建默认文件 SpillManager（V2Agent 装配入口）。"""
    if not data_dir:
        try:
            from gyra.configs.model_config import DATA_DIR
        except Exception:  # noqa: BLE001
            DATA_DIR = os.path.join(str(os.path.expanduser("~")), ".gyra")
        data_dir = os.path.join(DATA_DIR, "v2_spill")
    store = FileSpillStore(data_dir)
    return SpillManager(store)
