"""CJK-aware query segmentation for keyword retrieval.

FTS5 的 unicode61/porter 分词器把连续中文折叠成单个 token、verbatim 关键词
路径走 SQL LIKE——整句查询在两种索引上都只能精确子串命中，中文检索因此
几乎必空。检索前先把查询切成检索词（ASCII 词原样保留 + 中文词/二元组），
多词 OR 召回、按命中词覆盖度排序，让中文关键词检索真正可用。

jieba 可选：装了用精准分词；没装用正则二元组兜底（对 LIKE / 多词 OR
召回已足够；检索侧还有 rerank / LLM 扩展在上层兜精度）。
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import List, Optional

# CJK 统一表意文字 + 扩展A；ASCII 词含常见路径/版本号字符
_TOKEN = re.compile(
    r"[A-Za-z0-9_][A-Za-z0-9_\-./]*|[\u3400-\u4dbf\u4e00-\u9fff]+"
)
_ASCII_WORD = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_\-./]*")

# 单字虚词/助词不参与召回（LIKE OR 场景下纯噪音）
_CJK_STOPCHARS = set("的了在有是和与或及对于将为等个也不所按照从被把")


@lru_cache(maxsize=1)
def _get_jieba_lcut() -> Optional[object]:
    """可选加载 jieba.lcut；未安装返回 None（调用方走二元组兜底）。"""
    try:
        import jieba  # type: ignore

        jieba.setLogLevel(60)
        return jieba.lcut
    except Exception:  # noqa: BLE001
        return None


def segment_query(query: str, max_terms: int = 12) -> List[str]:
    """把检索查询切成检索词列表。

    规则：
    - ASCII 词原样保留（保持大小写，sqlite LIKE 对 ASCII 不区分大小写）
    - 中文 run：jieba 可用则精准分词；否则二元组切分
    - 过滤单字虚词，按原查询顺序去重，截断到 ``max_terms``
    - 空查询 / 纯符号返回 []
    """
    if not query or not query.strip():
        return []
    lcut = _get_jieba_lcut()
    terms: List[str] = []
    seen: set = set()

    def _add(t: str) -> None:
        t = t.strip()
        if not t or t in seen:
            return
        if len(t) == 1 and not t.isascii():
            return
        seen.add(t)
        terms.append(t)

    for m in _TOKEN.finditer(query):
        if len(terms) >= max_terms:
            break
        tok = m.group(0)
        if _ASCII_WORD.fullmatch(tok):
            _add(tok)
            continue
        if len(tok) <= 2:
            if tok not in _CJK_STOPCHARS:
                _add(tok)
            continue
        if lcut is not None:
            try:
                words = list(lcut(tok))  # type: ignore[operator]
            except Exception:  # noqa: BLE001
                words = []
            words = [w for w in words if w.strip()]
            if words and "".join(words) == tok:
                for w in words:
                    if len(terms) >= max_terms:
                        break
                    _add(w)
                continue
        for i in range(len(tok) - 1):
            if len(terms) >= max_terms:
                break
            bigram = tok[i : i + 2]
            if bigram[0] in _CJK_STOPCHARS and bigram[1] in _CJK_STOPCHARS:
                continue
            _add(bigram)
    return terms[:max_terms]


__all__ = ["segment_query"]
