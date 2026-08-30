"""ECP miss 飞轮:兜底查询的聚类、学习标记与学习上下文。

execute_raw_sql 兜底(op="fallback" 的 op_log 记录)→ cluster_fallbacks
归一聚类 → miss_report 曝光 → 提案 agent 学习 → mark_miss_learned 落
ecp_miss_learn 不再重复曝光。召回飞轮(召回率是运营出来的资产)的核心。

本模块持有聚类纯函数与 MissFlywheel(无状态协作者,经 svc 门面访问 DAO)。
"""

import logging
from typing import Any, Dict, List, Optional

from ..api.schemas import (
    MissClusterSummaryVO,
    MissDetailVO,
    MissLearnEventVO,
    MissLearnVO,
    MissRecordVO,
)

logger = logging.getLogger(__name__)


def _normalize_sql_pattern(sql: str, max_len: int = 200) -> str:
    """SQL 归一化为聚类模式键:小写、去字符串/数字字面值、压缩空白、截断。"""
    import re

    s = (sql or "").lower()
    s = re.sub(r"'[^']*'", "?", s)  # 字符串字面值
    s = re.sub(r"\b\d+(\.\d+)?\b", "?", s)  # 数字字面值
    s = re.sub(r"\s*([=<>(),;])\s*", r"\1", s)  # 操作符周围空白(Store = 1 vs Store=1)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:max_len]


def cluster_fallbacks(entries: List[Any]) -> List[dict]:
    """把 op_log fallback 条目按归一化模式聚类(频次降序,全量)。

    kind 分流(db/doc,ECP-unstructured P0):
    - db 条目(detail.sql):按归一化 SQL 模式聚类
    - doc 条目(detail.question):按归一化问题模式聚类
    miss_report 与 get_miss_report 工具共用的聚类核心;截断由调用方做。
    """
    from .resolver import normalize_question

    clusters: dict = {}
    for e in entries:
        detail = e.detail or {}
        if detail.get("kind") == "doc" or "question" in detail:
            kind = "doc"
            pattern = normalize_question(detail.get("question") or "")
            example = detail.get("question") or ""
        else:
            kind = "db"
            pattern = _normalize_sql_pattern(detail.get("sql") or "")
            example = detail.get("sql") or ""
        key = (kind, detail.get("datasource_id"), pattern)
        c = clusters.setdefault(
            key,
            {
                "kind": kind,
                "datasource_id": detail.get("datasource_id"),
                "spaces": detail.get("spaces"),
                "pattern": pattern,
                "count": 0,
                "example_sql": example,
                "reasonings": [],
                "last_seen": e.ts,
            },
        )
        c["count"] += 1
        reasoning = detail.get("reasoning")
        if reasoning and reasoning not in c["reasonings"]:
            c["reasonings"].append(reasoning)
    return sorted(clusters.values(), key=lambda x: -x["count"])


def _entry_key(detail: dict) -> tuple:
    """op_log fallback 条目的归一化聚类键(与 cluster_fallbacks 同规则)。"""
    from .resolver import normalize_question

    if detail.get("kind") == "doc" or "question" in detail:
        return ("doc", detail.get("datasource_id"),
                normalize_question(detail.get("question") or ""))
    return ("db", detail.get("datasource_id"),
            _normalize_sql_pattern(detail.get("sql") or ""))


class MissFlywheel:
    """miss 飞轮协作者(无状态;经 svc 门面访问 DAO 与 system_app)。"""

    def __init__(self, svc: Any):
        self._svc = svc

    # ------------------------------------------------------------- report
    def report(
        self,
        workspace_id: Optional[str] = None,
        limit: int = 20,
        scan_size: int = 500,
    ) -> dict:
        """聚类 op_log fallback miss(execute_raw_sql 兜底记录)。

        按归一化 SQL 模式分组(忽略字面值/空白差异),按频次排序——
        "大家在裸查什么"的可见化,learn_from_misses 的输入。

        已学习的聚类(ecp_miss_learn 中有对应标记)会被排除,避免每天重复
        喂给提案 agent 已经覆盖过的概念;learned 字段返回被过滤的标记数量。
        """
        svc = self._svc
        ws = svc._ws(workspace_id)
        entries = svc._oplog_dao.list(ws, op="fallback", page=1, page_size=scan_size)
        all_clusters = cluster_fallbacks(entries)
        learned = svc._miss_learn_dao.learned_keys(ws)
        open_clusters = [
            c
            for c in all_clusters
            if (c.get("kind"), c.get("datasource_id"), c.get("pattern")) not in learned
        ]
        return {
            "workspace_id": ws,
            "total_fallbacks": len(entries),
            "cluster_count": len(open_clusters),
            "learned_count": len(all_clusters) - len(open_clusters),
            "clusters": open_clusters[:limit],
        }

    def learned_cluster_keys(self, workspace_id: str) -> set:
        svc = self._svc
        return svc._miss_learn_dao.learned_keys(svc._ws(workspace_id))

    def detail(
        self,
        kind: str,
        pattern: str,
        datasource_id: Optional[int] = None,
        workspace_id: Optional[str] = None,
        scan_size: int = 500,
    ) -> "MissDetailVO":
        """单个 miss 聚类的学习档案(飞轮视图点击聚类行展开详情)。

        聚合四类数据,还原"这条问题从兜底到沉淀"的完整轨迹:
        - cluster: 摘要(频次/首末时间/未命中原因)
        - records: 原始兜底记录(op_log fallback 按同一归一化键过滤,时间倒序)
        - learned: 已学习标记(ecp_miss_learn,可为空=待学习)
        - learn_events: 标记生命周期事件(op_log miss_learned/miss_learn_clear)
        """
        svc = self._svc
        ws = svc._ws(workspace_id)
        key = (kind, datasource_id, pattern)

        records: List[MissRecordVO] = []
        for e in svc._oplog_dao.list(ws, op="fallback", page=1, page_size=scan_size):
            detail = e.detail or {}
            if _entry_key(detail) != key:
                continue
            records.append(
                MissRecordVO(
                    ts=e.ts,
                    sql=detail.get("sql"),
                    question=detail.get("question"),
                    reasoning=detail.get("reasoning"),
                    datasource_id=detail.get("datasource_id"),
                    spaces=detail.get("spaces"),
                )
            )
        records.sort(key=lambda r: r.ts or "", reverse=True)

        reasonings: List[str] = []
        for r in records:
            if r.reasoning and r.reasoning not in reasonings:
                reasonings.append(r.reasoning)
        newest = records[0] if records else None
        cluster = MissClusterSummaryVO(
            kind=kind,
            datasource_id=datasource_id,
            pattern=pattern,
            count=len(records),
            example_sql=(
                (newest.question if kind == "doc" else newest.sql) if newest else None
            ),
            reasonings=reasonings,
            spaces=newest.spaces if newest else None,
            first_seen=records[-1].ts if records else None,
            last_seen=newest.ts if newest else None,
        )

        learned = svc._miss_learn_dao.get(ws, kind, pattern, datasource_id)

        events: List[MissLearnEventVO] = []
        for op in ("miss_learned", "miss_learn_clear"):
            for e in svc._oplog_dao.list(ws, op=op, page=1, page_size=50):
                d = e.detail or {}
                if op == "miss_learned":
                    marks = d.get("mark") or []
                    if any(
                        m.get("kind") == kind
                        and m.get("pattern") == pattern
                        and m.get("datasource_id") == datasource_id
                        for m in marks
                    ):
                        events.append(
                            MissLearnEventVO(
                                ts=e.ts,
                                op=op,
                                trigger=d.get("trigger"),
                                proposals=d.get("proposals") or [],
                            )
                        )
                elif (
                    d.get("kind") == kind
                    and d.get("pattern") == pattern
                    and d.get("datasource_id") == datasource_id
                ):
                    events.append(MissLearnEventVO(ts=e.ts, op=op))
        events.sort(key=lambda x: x.ts or "")

        return MissDetailVO(
            workspace_id=ws,
            cluster=cluster,
            records=records,
            learned=learned,
            learn_events=events,
        )

    # ------------------------------------------------------------- learn
    def mark_learned(
        self,
        clusters: List[dict],
        workspace_id: Optional[str] = None,
        proposal_ids: Optional[List[str]] = None,
        trigger: str = "agent",
    ) -> List[MissLearnVO]:
        """把 miss 聚类标记为"已学习"(幂等),下一次报告不再曝光。

        ``clusters`` 是 miss_report/get_miss_report 返回的聚类对象列表(含
        kind/pattern/datasource_id)。提案 agent 在成功为某个 miss 聚类提案后
        调用 mark_miss_learned 落盘,飞轮的学习侧才有持久记忆。
        """
        svc = self._svc
        ws = svc._ws(workspace_id)
        marked: List[MissLearnVO] = []
        for c in clusters or []:
            kind = c.get("kind")
            pattern = c.get("pattern")
            if not kind or not pattern:
                continue
            vo = svc._miss_learn_dao.mark_learned(
                ws,
                kind,
                pattern,
                datasource_id=c.get("datasource_id"),
                example=(c.get("example_sql") or c.get("example")),
                proposal_ids=proposal_ids,
                trigger=trigger,
            )
            marked.append(vo)
        if marked:
            svc._oplog_dao.append(
                "miss_learned",
                ws,
                {
                    "mark": [{"kind": v.kind, "pattern": v.pattern,
                              "datasource_id": v.datasource_id}
                             for v in marked],
                    "trigger": trigger,
                    "proposals": proposal_ids or [],
                },
            )
        return marked

    def list_learned(
        self, workspace_id: Optional[str] = None, kind: Optional[str] = None
    ) -> List[MissLearnVO]:
        """列出工作空间所有已学习的 miss 标记(按学习时间倒序)。"""
        svc = self._svc
        return svc._miss_learn_dao.list(svc._ws(workspace_id), kind)

    def clear_learned(
        self,
        workspace_id: Optional[str] = None,
        kind: Optional[str] = None,
        pattern: Optional[str] = None,
        datasource_id: Optional[int] = None,
    ) -> int:
        """清除已学习标记(允许对应 miss 重新曝光)。返回清除数。"""
        svc = self._svc
        ws = svc._ws(workspace_id)
        removed = svc._miss_learn_dao.clear(ws, kind, pattern, datasource_id)
        if removed:
            svc._oplog_dao.append(
                "miss_learn_clear",
                ws,
                {
                    "removed": removed,
                    "kind": kind,
                    "pattern": pattern,
                    "datasource_id": datasource_id,
                },
            )
        return removed

    @staticmethod
    def build_context(clusters: List[dict], max_items: int = 10) -> str:
        """把 miss 聚类构建成提案 agent 的领域上下文(问题驱动的提案素材)。"""
        if not clusters:
            return ""
        lines = [
            "【未覆盖的真实问题(miss 聚类,按频次排序)】",
            "以下是用户真实问过、但语义目录无法覆盖而走了 execute_raw_sql 兜底的查询。",
            "请优先为这些高频问题提炼可确认的语义资产(指标/维度/值字典),",
            "使后续同类问题能走 execute_metric_query 可信路径:",
            "为某个聚类提案时必须带回溯源(确认人要核对原始 SQL):",
            "miss_ref={kind, pattern, datasource_id}(取自该聚类), origin_sql=[该聚类的 SQL 示例]。",
        ]
        for i, c in enumerate(clusters[:max_items], 1):
            kind = c.get("kind", "db")
            if kind == "doc":
                lines.append(
                    f"\n{i}. [出现 {c['count']} 次] 文档问题(空间: "
                    f"{','.join(c.get('spaces') or ['?'])})"
                )
                example = (c.get("example_sql") or "").strip()
                if example:
                    lines.append(f"   问题: {example[:300]}")
            else:
                lines.append(
                    f"\n{i}. [出现 {c['count']} 次] 数据源 #{c.get('datasource_id')}"
                )
                example = (c.get("example_sql") or "").strip()
                if example:
                    lines.append(f"   SQL: {example[:400]}")
            for r in (c.get("reasonings") or [])[:3]:
                lines.append(f"   未命中原因: {r}")
        return "\n".join(lines)
