"""查询理解：LLM 优先的检索词扩展。

ECP 检索入口(search_semantics / explore_docs)把用户自然语言查询先过
expand_query_terms：本地 CJK 分词(gyra_ext.knowledge.cjk)保底，再叠加
一轮 LLM 语义扩展(同义词/别名/上下位概念/中英对照)。LLM 不可用时静默
降级为纯本地分词——扩展只提升召回，永不阻断检索。
"""

import json
import logging
import re
from typing import List, Optional

from gyra_ext.knowledge.cjk import segment_query

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "你是检索查询扩展器。给定一个用户的检索查询，输出与查询语义相关的"
    "扩展检索词，用于知识库关键词检索。要求：\n"
    "1. 包含同义词、常见别名、上下位概念、中英文对照写法。\n"
    "2. 只输出 JSON 对象，格式：{\"terms\": [\"词1\", \"词2\", ...]}\n"
    "3. 最多 8 个词，按与查询的相关度降序。\n"
    "不要输出任何解释性文字。"
)


async def expand_query_terms(
    query: str, max_terms: int = 10, model: Optional[str] = None
) -> List[str]:
    """本地分词 + LLM 语义扩展合并的检索词列表。

    LLM 失败/未配置时降级为纯本地分词；结果按本地词在前、扩展词在后
    去重排列，截断到 max_terms * 2。
    """
    if not query or not query.strip():
        return []
    local = segment_query(query, max_terms=max_terms)
    try:
        llm_terms = await _llm_expand_terms(query, model)
    except Exception as e:  # noqa: BLE001
        logger.debug("LLM query expansion failed, local terms only: %s", e)
        llm_terms = []
    merged = list(local)
    for t in llm_terms:
        if t and t not in merged:
            merged.append(t)
    return merged[: max_terms * 2]


async def _llm_expand_terms(query: str, model: Optional[str] = None) -> List[str]:
    """与 alignment.py 同源的 httpx 直调模式：ModelConfigCache 取模型配置。"""
    import httpx

    from gyra.agent.util.llm.model_config_cache import ModelConfigCache

    models = ModelConfigCache.get_all_models()
    if not models:
        return []
    name = model or models[0]
    config = ModelConfigCache.get_config(name) or {}
    base_url = (config.get("base_url") or config.get("api_base") or "").rstrip("/")
    if not base_url:
        return []
    if "/v1" not in base_url:
        base_url += "/v1"
    headers = {"Content-Type": "application/json"}
    api_key = config.get("api_key", "")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "model": config.get("model") or name,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        "temperature": 0.2,
        "max_tokens": 300,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{base_url}/chat/completions", json=payload, headers=headers
        )
        resp.raise_for_status()
        choices = resp.json().get("choices", [])
        if not choices:
            return []
        text = choices[0].get("message", {}).get("content", "") or ""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except (ValueError, TypeError):
        return []
    terms = data.get("terms") if isinstance(data, dict) else None
    if not isinstance(terms, list):
        return []
    return [t.strip() for t in terms if isinstance(t, str) and t.strip()]


__all__ = ["expand_query_terms"]
