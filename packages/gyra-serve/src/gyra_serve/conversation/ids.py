"""会话标识的统一术语与归一化工具。

## 术语表（统一名，2026-08-28 定稿）

| 维度 | 后端（Python） | 前端（TS） | 格式 | 语义 |
|---|---|---|---|---|
| 会话 | ``conv_session_id`` | ``conversationId`` | 纯 uuid | 一场对话，跨轮次不变 |
| 轮次 | ``conv_turn_id`` | ``turnId`` | ``{会话 uuid}_{n}`` | 一次提问，每提一次问 +1 |

- 后端会话名 ``conv_session_id`` 同时就是 DB 列名，直接使用；
  轮次在 ``AgentContext`` 上用只读别名 ``conv_turn_id``（底层字段/DB 列为
  ``conv_id``，Deprecated —— 名字看不出是轮次维度，是历史混淆的根源）。
- 前端 ``convUid`` 语义上就是会话 id ——
  见 ``web/src/app/workspaces/detail/use-scene-agent-chat.ts`` 里
  ``t.conv_session_id === convUid`` 的断言。

## 为什么需要这个模块

``conv_uid`` 一词两义：部分旧 API 前端传的是轮次 id（带 ``_N`` 后缀），
部分传的是会话 id。历史上各调用点各写一遍「剥离 ``_N``」的判断，
本项目内曾有 5 处重复实现（``conversation/service``、
``conversation/api``、``usage/models``），且写法不完全一致
（有的先判 ``"_" in x``，有的不判）。

**新代码一律调用本模块的函数，不要再手写 ``rsplit``。**

## 迁移姿态

DB 列名与 API 契约保持不动：``conv_session_id`` / ``conv_id`` / ``conv_uid``
继续可读可写，仅 ``conv_id`` 标注 deprecated 语义。
新代码：会话用 ``conv_session_id``，轮次用 ``conv_turn_id``（或本模块函数）。
"""

from __future__ import annotations

from typing import Optional, Tuple

__all__ = [
    "to_conversation_id",
    "is_turn_id",
    "split_turn_id",
]


def is_turn_id(value: Optional[str]) -> bool:
    """判断 *value* 是否为轮次 id（形如 ``{conversation_id}_{n}``）。

    会话 id 是纯 uuid（含 ``-`` 不含 ``_``），因此只有当最后一段是纯数字时
    才判定为轮次 id。uuid 中间的 ``-`` 不受影响。

    >>> is_turn_id("b63fbb0e-38d8-11f1-8578-b5920cfbee2e_2")
    True
    >>> is_turn_id("b63fbb0e-38d8-11f1-8578-b5920cfbee2e")
    False
    """
    if not value or "_" not in value:
        return False
    return value.rsplit("_", 1)[-1].isdigit()


def to_conversation_id(value: Optional[str]) -> Optional[str]:
    """把可能是轮次 id 的值归一化为会话 id（幂等，可重复调用）。

    ``b63fbb0e-...-b5920cfbee2e_2`` -> ``b63fbb0e-...-b5920cfbee2e``
    ``b63fbb0e-...-b5920cfbee2e``   -> 原样返回

    用于收敛「前端传来的 conv_uid 到底是会话 id 还是轮次 id」的历史歧义。
    """
    if not value:
        return value
    return value.rsplit("_", 1)[0] if is_turn_id(value) else value


def split_turn_id(value: Optional[str]) -> Tuple[Optional[str], Optional[int]]:
    """拆出 ``(conversation_id, round_no)``。

    非轮次 id 时 ``round_no`` 为 ``None``（此时第一个元素即会话 id）。
    """
    if not value or not is_turn_id(value):
        return (value, None)
    head, tail = value.rsplit("_", 1)
    return (head, int(tail))
