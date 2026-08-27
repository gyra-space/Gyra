#!/usr/bin/env python3
"""App Card payload 合法性校验脚本（随 app-card-generator skill 分发）。

用法:
    python validate.py <payload.json>
    cat <payload.json> | python validate.py
    python validate.py            # 默认读取 ./app_card_payload.json

校验通过：打印 “[OK] ...” 并以 0 退出。
校验失败：打印具体问题清单并以非 0 退出（便于 agent 对症修复后再交付）。
"""

import json
import os
import re
import sys

SCHEMA_NAME = "gyra_app_card"
SQL_PREFIXES = ("SELECT", "WITH", "SHOW", "DESC", "DESCRIBE", "EXPLAIN")

_FAILS = []


def _fail(msg: str) -> None:
    _FAILS.append(msg)


def _load_text() -> str:
    if len(sys.argv) > 1:
        path = sys.argv[1]
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except OSError as e:
            print(f"[FAIL] 无法读取文件 {path}: {e}")
            sys.exit(2)
    if os.path.exists("app_card_payload.json"):
        with open("app_card_payload.json", "r", encoding="utf-8") as f:
            return f.read()
    raw = sys.stdin.read()
    return raw


def _check_code(code: str) -> None:
    """对 code 做轻量 JS 语法平衡检查（括号/花括号配对 + 字符串闭合）。"""
    pairs = {")": "(", "}": "{", "]": "["}
    opens = set("({[")
    stack = []
    in_str = None
    esc = False
    for ch in code:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == in_str:
                in_str = None
            continue
        if ch in "\"'`":
            in_str = ch
        elif ch in opens:
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                _fail("code 内括号/花括号不配对，可能为非法 JS")
                return
    if in_str:
        _fail("code 内存在未闭合的字符串引号")
    if stack:
        _fail("code 内存在未闭合的括号/花括号")


def _check_queries(queries: list) -> None:
    seen = set()
    for i, q in enumerate(queries):
        if not isinstance(q, dict):
            _fail(f"queries[{i}] 不是对象")
            continue
        key = q.get("key")
        if not isinstance(key, str) or not key.strip():
            _fail(f"queries[{i}] 缺少 key")
            key = f"queries[{i}]"
        elif key in seen:
            _fail(f"queries key 重复: {key!r}")
            continue
        else:
            seen.add(key)

        kind = q.get("kind")
        if kind == "sql":
            sql = q.get("sql")
            if not isinstance(sql, str) or not sql.strip():
                _fail(f"query {key!r}: sql 缺失或为空")
            else:
                first = sql.lstrip().upper().split(None, 1)[0] if sql.lstrip() else ""
                if first not in SQL_PREFIXES:
                    _fail(
                        f"query {key!r}: sql 应以 {SQL_PREFIXES} 之一开头，实际为 {first!r}"
                    )
            if q.get("datasource_id") is None:
                _fail(f"query {key!r}: 缺 datasource_id")
            bind = q.get("bind_params")
            if isinstance(bind, dict) and isinstance(sql, str):
                for p in re.findall(r":([A-Za-z_][A-Za-z0-9_]*)", sql):
                    if p not in bind:
                        _fail(f"query {key!r}: sql 占位符 :{p} 未在 bind_params 提供")
        elif kind == "metric":
            if not q.get("metric_id"):
                _fail(f"query {key!r}: metric 缺 metric_id")
        else:
            _fail(f"query {key!r}: kind 应为 metric/sql，实际为 {kind!r}")


def main() -> int:
    raw = _load_text()
    if not raw or not raw.strip():
        print("[FAIL] 内容为空")
        return 1

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[FAIL] 非法 JSON 无法解析——第 {e.lineno} 行 第 {e.colno} 列: {e.msg}")
        print("       常见原因：JSON 被截断、混入说明文字、code/字段内引号未转义。")
        return 1

    if not isinstance(data, dict):
        print("[FAIL] JSON 顶层应为对象")
        return 1

    meta = data.get("meta")
    if not isinstance(meta, dict):
        _fail("meta 缺失或不是对象")
    else:
        if meta.get("schema_name") != SCHEMA_NAME:
            _fail(f"meta.schema_name 应为 '{SCHEMA_NAME}'，实际为 {meta.get('schema_name')!r}")
        for k in ("schema_version", "generated_by", "generated_at"):
            if k not in meta:
                _fail(f"meta 缺少 {k}")

    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        _fail("name 缺失或为空")

    if data.get("kind") not in ("dashboard", "board", "custom"):
        _fail(f"kind 应为 dashboard/board/custom，实际为 {data.get('kind')!r}")

    code = data.get("code")
    if not isinstance(code, str) or not code.strip():
        _fail("code 缺失或为空")
    else:
        _check_code(code)

    if not isinstance(data.get("config"), dict):
        _fail("config 应为对象")

    queries = data.get("queries")
    if not isinstance(queries, list):
        _fail("queries 应为数组")
    else:
        _check_queries(queries)

    if not isinstance(data.get("icon"), (str, type(None))):
        _fail("icon 应为字符串或省略")
    if not isinstance(data.get("permissions", []), list):
        _fail("permissions 应为数组")

    if _FAILS:
        print(f"[FAIL] 共 {len(_FAILS)} 处问题：")
        for i, m in enumerate(_FAILS, 1):
            print(f"  {i}. {m}")
        return 1

    qn = len(data.get("queries") or [])
    print(f"[OK] name={name} queries={qn} code={len(code)}chars")
    return 0


if __name__ == "__main__":
    sys.exit(main())
