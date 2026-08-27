"""飞轮测试:resolution cache 回忆(读路径) + miss 聚类学习。

第一圈:execute_metric_query_tool 带 question 命中缓存 → replay 冻结参数;
第二圈:miss_report 聚类 op_log fallback + build_miss_context 构建提案素材。
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from gyra_serve.ecp.service import resolver
from gyra_serve.ecp.service.service import Service, _normalize_sql_pattern
from gyra_serve.ecp.tools import ecp_tools


# ---------------------------------------------------------------- 第一圈:回忆
class TestRecallPath:
    @pytest.mark.asyncio
    async def test_recall_hit_replays_frozen_params(self, monkeypatch):
        monkeypatch.setattr(
            resolver, "lookup",
            lambda q, ws: {
                "tool": "execute_metric_query",
                "params": {"metric_id": "mtr.a", "workspace_id": ws,
                           "group_by": ["dim.b"]},
            },
        )
        replay_result = {
            "trust": "verified", "columns": ["value"], "rows": [[42]],
            "row_count": 1, "sql": "SELECT ...", "cache_hit": True,
        }
        monkeypatch.setattr(resolver, "replay", lambda cached: replay_result)
        # ecp_tools 内部 from ..service.resolver import lookup/replay,
        # 绑定的是模块属性,故 patch resolver 模块即可
        out = await ecp_tools.execute_metric_query_tool(
            metric_id="mtr.a", question="各门店销售", workspace_id="default"
        )
        assert "cache_hit" in out or '"cache_hit":true' in out.replace(" ", "")

    @pytest.mark.asyncio
    async def test_recall_metric_mismatch_goes_live(self, monkeypatch):
        """缓存 metric 与调用不一致 → 走实时执行(agent 明确选择了别的指标)。"""
        monkeypatch.setattr(
            resolver, "lookup",
            lambda q, ws: {
                "tool": "execute_metric_query",
                "params": {"metric_id": "mtr.OTHER", "workspace_id": ws},
            },
        )
        replay_called = []
        monkeypatch.setattr(
            resolver, "replay", lambda c: replay_called.append(c) or {}
        )
        live_called = []
        # execute_metric_query_tool 在函数体内 from ..service.executor import,
        # 调用时从 executor 模块解析,故 patch executor 模块属性
        monkeypatch.setattr(
            "gyra_serve.ecp.service.executor.execute_metric_query",
            lambda **kw: live_called.append(kw) or {
                "trust": "verified", "rows": [], "columns": [], "row_count": 0,
            },
        )
        monkeypatch.setattr(resolver, "backfill", lambda *a, **k: None)
        await ecp_tools.execute_metric_query_tool(
            metric_id="mtr.a", question="问题", workspace_id="default"
        )
        assert not replay_called
        assert live_called and live_called[0]["metric_id"] == "mtr.a"


# --------------------------------------------------------------- 第二圈:miss
class TestNormalizeSqlPattern:
    def test_literals_normalized(self):
        a = _normalize_sql_pattern("SELECT * FROM t WHERE Store = 5 AND name = 'abc'")
        b = _normalize_sql_pattern("select * from t where Store=99 and name='xyz'")
        assert a == b

    def test_whitespace_collapsed(self):
        a = _normalize_sql_pattern("SELECT  *\nFROM   t")
        assert a == "select * from t"

    def test_truncated(self):
        assert len(_normalize_sql_pattern("x" * 500)) == 200


class TestMissReport:
    def _svc(self, entries, learned=None):
        svc = Service.__new__(Service)
        svc._oplog_dao = MagicMock()
        svc._oplog_dao.list.return_value = entries
        svc._miss_learn_dao = MagicMock()
        svc._miss_learn_dao.learned_keys.return_value = learned or set()
        return svc

    def test_clusters_by_pattern(self):
        entries = [
            SimpleNamespace(ts="2026-08-01", detail={
                "datasource_id": 1,
                "sql": "SELECT Store, SUM(sales) FROM t WHERE year = 2024",
                "reasoning": "缺指标",
            }),
            SimpleNamespace(ts="2026-08-01", detail={
                "datasource_id": 1,
                "sql": "SELECT Store, SUM(sales) FROM t WHERE year = 2025",
                "reasoning": "缺指标",
            }),
            SimpleNamespace(ts="2026-08-01", detail={
                "datasource_id": 1, "sql": "SELECT AVG(temp) FROM t2",
                "reasoning": "缺温度指标",
            }),
        ]
        svc = self._svc(entries)
        report = svc.miss_report()
        assert report["total_fallbacks"] == 3
        assert report["cluster_count"] == 2
        top = report["clusters"][0]
        assert top["count"] == 2  # 字面值不同的两条 SQL 聚为一类
        assert "缺指标" in top["reasonings"]

    def test_empty(self):
        svc = self._svc([])
        report = svc.miss_report()
        assert report["total_fallbacks"] == 0
        assert report["clusters"] == []

    def test_learned_clusters_excluded(self):
        entries = [
            SimpleNamespace(ts="2026-08-01", detail={
                "datasource_id": 1,
                "sql": "SELECT Store, SUM(sales) FROM t WHERE year = 2024",
                "reasoning": "缺指标",
            }),
            SimpleNamespace(ts="2026-08-01", detail={
                "datasource_id": 1,
                "sql": "SELECT Store, SUM(sales) FROM t WHERE year = 2025",
                "reasoning": "缺指标",
            }),
        ]
        # 该聚类(同 pattern)已被标记学习 → 被排除,learned_count=1
        pattern = _normalize_sql_pattern(
            "SELECT Store, SUM(sales) FROM t WHERE year = 2024"
        )
        learned = {("db", 1, pattern)}
        svc = self._svc(entries, learned=learned)
        report = svc.miss_report()
        assert report["clusters"] == []
        assert report["learned_count"] == 1


class TestBuildMissContext:
    def test_format(self):
        clusters = [{
            "datasource_id": 1, "count": 5, "example_sql": "SELECT 1",
            "reasonings": ["目录缺少门店指标"], "pattern": "select ?",
        }]
        ctx = Service.build_miss_context(clusters)
        assert "出现 5 次" in ctx
        assert "SELECT 1" in ctx
        assert "目录缺少门店指标" in ctx
        assert "execute_metric_query" in ctx

    def test_empty(self):
        assert Service.build_miss_context([]) == ""


class TestMissDetail:
    SQL_A = "SELECT Store, SUM(sales) FROM t WHERE year = 2024"
    SQL_B = "SELECT Store, SUM(sales) FROM t WHERE year = 2025"
    SQL_C = "SELECT AVG(temp) FROM t2"

    def _svc(self, fallbacks, oplog_extra=None, learned_get=None):
        svc = Service.__new__(Service)
        calls = {"fallback": fallbacks}
        calls.update(oplog_extra or {})

        def list_op(ws, op=None, page=1, page_size=50):
            return calls.get(op, [])

        svc._oplog_dao = MagicMock()
        svc._oplog_dao.list.side_effect = list_op
        svc._miss_learn_dao = MagicMock()
        svc._miss_learn_dao.get.return_value = learned_get
        return svc

    def test_records_filtered_and_summary(self):
        pattern = _normalize_sql_pattern(self.SQL_A)
        entries = [
            SimpleNamespace(ts="2026-08-03", detail={
                "datasource_id": 1, "sql": self.SQL_C, "reasoning": "缺温度",
            }),
            SimpleNamespace(ts="2026-08-01", detail={
                "datasource_id": 1, "sql": self.SQL_A, "reasoning": "缺指标",
            }),
            SimpleNamespace(ts="2026-08-02", detail={
                "datasource_id": 1, "sql": self.SQL_A, "reasoning": "缺指标v2",
            }),
            # 同一聚类、其他数据源 → 排除
            SimpleNamespace(ts="2026-08-02", detail={
                "datasource_id": 2, "sql": self.SQL_A, "reasoning": "缺指标",
            }),
        ]
        svc = self._svc(entries)
        detail = svc.miss_detail(kind="db", pattern=pattern, datasource_id=1)
        # 同 pattern(字面值不同)的两条聚为一类,其余排除
        assert detail.cluster.count == 2
        assert detail.cluster.first_seen == "2026-08-01"
        assert detail.cluster.last_seen == "2026-08-02"
        assert detail.cluster.reasonings == ["缺指标v2", "缺指标"]
        assert [r.ts for r in detail.records] == ["2026-08-02", "2026-08-01"]
        assert detail.learned is None

    def test_learned_marker_and_events(self):
        from gyra_serve.ecp.api.schemas import MissLearnVO

        pattern = _normalize_sql_pattern(self.SQL_A)
        other = _normalize_sql_pattern(self.SQL_C)
        entries = [
            SimpleNamespace(ts="2026-08-01", detail={
                "datasource_id": 1, "sql": self.SQL_A, "reasoning": "缺指标",
            }),
        ]
        learned = MissLearnVO(
            id=7, workspace_id="default", kind="db", datasource_id=1,
            pattern=pattern, example=self.SQL_A, proposal_ids=["obj.x"],
            trigger="agent", learned_at="2026-08-05T04:00:00",
        )
        oplog_extra = {
            "miss_learned": [
                SimpleNamespace(ts="2026-08-05", detail={
                    "trigger": "agent",
                    "proposals": ["obj.x"],
                    "mark": [
                        {"kind": "db", "pattern": pattern, "datasource_id": 1},
                        {"kind": "db", "pattern": other, "datasource_id": 1},
                    ],
                }),
            ],
            "miss_learn_clear": [
                SimpleNamespace(ts="2026-08-06", detail={
                    "removed": 1, "kind": "db", "pattern": pattern,
                    "datasource_id": 1,
                }),
                # 其他聚类的清除事件不混入
                SimpleNamespace(ts="2026-08-06", detail={
                    "removed": 1, "kind": "db", "pattern": other,
                    "datasource_id": 1,
                }),
            ],
        }
        svc = self._svc(entries, oplog_extra=oplog_extra, learned_get=learned)
        detail = svc.miss_detail(kind="db", pattern=pattern, datasource_id=1)
        assert detail.learned is learned
        assert [e.op for e in detail.learn_events] == [
            "miss_learned",
            "miss_learn_clear",
        ]
        assert detail.learn_events[0].proposals == ["obj.x"]

    def test_doc_question_key(self):
        from gyra_serve.ecp.service.resolver import normalize_question

        q = "各门店 2024 年销售额是多少"
        entries = [
            SimpleNamespace(ts="2026-08-01", detail={
                "kind": "doc", "question": q, "spaces": ["kb1"],
            }),
        ]
        svc = self._svc(entries)
        detail = svc.miss_detail(
            kind="doc", pattern=normalize_question(q), datasource_id=None
        )
        assert detail.cluster.count == 1
        assert detail.cluster.spaces == ["kb1"]
        assert detail.cluster.example_sql == q


# ------------------------------------------------------- execute_raw_sql 只读校验
class TestRawSqlReadOnlyGuard:
    @pytest.mark.asyncio
    async def test_comment_prefixed_select_allowed(self, monkeypatch):
        """带 -- 注释头的合法 SELECT 不应被误判(对话 1ad61a82 的 bug)。"""
        dao = MagicMock()
        monkeypatch.setattr(ecp_tools, "OpLogDao", lambda: dao)
        out = json.loads(
            await ecp_tools.execute_raw_sql(
                datasource_id=999,
                sql="-- 基础统计信息\nSELECT COUNT(*) FROM t",
                reasoning="探索",
            )
        )
        # 会通过只读校验,在连接阶段才失败(数据源不存在),而不是"只允许只读查询"
        assert "只允许只读查询" not in out.get("error", "")

    @pytest.mark.asyncio
    async def test_block_comment_prefixed_select_allowed(self, monkeypatch):
        dao = MagicMock()
        monkeypatch.setattr(ecp_tools, "OpLogDao", lambda: dao)
        out = json.loads(
            await ecp_tools.execute_raw_sql(
                datasource_id=999,
                sql="/* 统计 */ SELECT COUNT(*) FROM t",
                reasoning="探索",
            )
        )
        assert "只允许只读查询" not in out.get("error", "")

    @pytest.mark.asyncio
    async def test_comment_prefixed_insert_rejected(self, monkeypatch):
        out = json.loads(
            await ecp_tools.execute_raw_sql(
                datasource_id=1,
                sql="-- 小心\nINSERT INTO t VALUES (1)",
                reasoning="尝试",
            )
        )
        assert "只允许只读查询" in out.get("error", "")
        assert out.get("trust") == "none"
