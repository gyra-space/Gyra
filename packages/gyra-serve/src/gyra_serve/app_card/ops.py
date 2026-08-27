"""AppCard 统一 invoke 协议 —— op 注册表(扩展点)。

背景:原本 `_dispatch` 是一张硬编码的 op→handler 字典(仅 query.metric /
query.sql / assets.get),每接入一类新资源(知识库 / MCP / 数据空间等)都要改核心。
本模块把派发抽成**注册表**:任何资源模块只需调用 :func:`register_app_card_op`
声明自己的 op,即可被运行期 `invoke` 识别,无需改动 AppCardService。

Handler 统一签名:
    ``(service, entity, workspace_id, queries, params, query_key) -> dict``

op 命名空间约定:``<capability>.<action>``,如 ``query.sql`` / ``assets.get`` /
``store.insert`` / ``kv.put``。前缀即 capability,便于按资源分组扩展。
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

HANDLER_FN = Callable[..., Dict[str, Any]]

_OP_REGISTRY: Dict[str, HANDLER_FN] = {}


def register_app_card_op(op: str, handler: HANDLER_FN) -> None:
    """注册一个 op 到统一 invoke 协议。

    Args:
        op: 能力名,形如 ``store.insert`` / ``knowledge.search``。
        handler: ``(service, entity, workspace_id, queries, params, query_key)``。
    """
    _OP_REGISTRY[op] = handler


def resolve_app_card_op(op: str) -> Optional[HANDLER_FN]:
    """按 op 解析 handler;未注册返回 None(由调用方降级为「不支持的能力」)。"""
    return _OP_REGISTRY.get(op)


def registered_app_card_ops() -> list[str]:
    """返回已注册的全部 op(供 debug / 能力清单展示)。"""
    return sorted(_OP_REGISTRY.keys())
