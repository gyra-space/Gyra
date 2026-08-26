"""AppCard seed — 建一张可用的 demo 应用卡片(含 SQL 查询模板)。

运行方式(在 gyra 后端进程外独立执行):
    # 可选 workspace_id, 默认 1
    python -m gyra_serve.app_card.seed [workspace_id]

它会:
  1. 确保元数据库(connect_config 所在库)已建表;
  2. 建一个 SQLite demo 数据源 + demo 表并写入示例行;
  3. 在 connect_config 里注册该数据源(幂等);
  4. 插入一张 app_card 卡片, 其 queries 引用该数据源的只读 SQL 查询模板。

卡片渲染在空间主页「应用卡片」区块, 运行期通过统一 invoke 协议( query.sql )
在 demo 数据源上取数 —— 真正做到「生成一次, 运行期冻结取数, 不再调 agent」。
"""
import os
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

# 1) 元数据库 + 实体注册(需先创建/确认元库)
from gyra.storage.metadata import db
from gyra_serve.app_card.models.models import (  # noqa: F401  注册 AppCard 表
    AppCardDao, AppCardEntity,
)
from gyra_serve.datasource.manages.connect_config_db import (  # noqa: F401
    ConnectConfigDao, ConnectConfigEntity,
)
from gyra_ext.datasource.rdbms.conn_sqlite import SQLiteConnector

ROOT = Path(__file__).resolve()
for _ in range(8):
    if (ROOT / "pilot").exists():
        break
    ROOT = ROOT.parent
METADATA_DB = ROOT / "pilot" / "meta_data" / "gyra.db"
DEMO_DB = ROOT / "pilot" / "data" / "app_card_demo.sqlite"
DB_NAME = "app_card_demo_sqlite"

DEMO_CARD_NAME = "运行指标概览（Demo）"
DEMO_SQL = (
    "SELECT name AS service, value AS cpu, created_at AS day "
    "FROM demo_table WHERE created_at >= :start ORDER BY created_at DESC"
)

DEMO_CODE = """
(function(){
  document.head.insertAdjacentHTML('beforeend','<style>.bd{font-family:-apple-system,sans-serif;padding:10px;color:#1f2328}.hd{font-size:13px;font-weight:700;margin-bottom:8px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:8px}.k{background:#fff;border:1px solid #eef0f3;border-radius:8px;padding:6px 8px}.k .t{font-size:11px;color:#6b7280}.k .v{font-size:18px;font-weight:700;margin-top:2px}.tbl{width:100%;border-collapse:collapse;margin-top:8px;font-size:12px}.tbl th,.tbl td{border:1px solid #eef0f3;padding:4px 6px;text-align:left}.lbl{color:#8c8c8c;font-size:12px;margin-top:8px}</style>');
  var root=document.getElementById('root');
  root.innerHTML='<div class="bd"><div class="hd">运行指标概览（Demo）</div><div class="grid" id="cards"></div><div id="tbl"><div class="lbl">加载中…</div></div></div>';
  function fmt(n){return (n==null?'\\u2014':Number(n).toFixed(2));}
  GyraAppCard.op('query.sql',{bind_params:{start:'2020-01-01'}}, 'q_metrics').then(function(res){
    var rows=(res&&res.rows)||[];
    var total=rows.reduce(function(a,r){return a+(Number(r.cpu)||0);},0);
    var avg=rows.length?(total/rows.length):0;
    var max=rows.length?Math.max.apply(null,rows.map(function(r){return Number(r.cpu)||0;})):0;
    document.getElementById('cards').innerHTML=
      '<div class="k"><div class="t">记录数</div><div class="v">'+rows.length+'</div></div>'+
      '<div class="k"><div class="t">平均值</div><div class="v">'+fmt(avg)+'</div></div>'+
      '<div class="k"><div class="t">最大值</div><div class="v">'+fmt(max)+'</div></div>';
    document.getElementById('tbl').innerHTML='<table class="tbl"><thead><tr><th>服务</th><th>指标值</th><th>日期</th></tr></thead><tbody>'+
      rows.map(function(r){return '<tr><td>'+r.service+'</td><td>'+fmt(r.cpu)+'</td><td>'+r.day+'</td></tr>';}).join('')+'</tbody></table>';
  }).catch(function(e){ document.getElementById('tbl').innerHTML='<div class="lbl">取数失败: '+e.message+'</div>'; });
})();
"""


def _init_metadata_db() -> None:
    db.init_db(f"sqlite:///{METADATA_DB}")
    db.create_all()


def _ensure_demo_datasource() -> int:
    """创建 demo 表 + 示例行; 并注册/更新 connect_config 行, 返回数据源 id。"""
    DEMO_DB.parent.mkdir(parents=True, exist_ok=True)
    connector = SQLiteConnector.from_file_path(str(DEMO_DB))
    with connector.session_scope(commit=True) as session:
        session.execute(text(
            "CREATE TABLE IF NOT EXISTS demo_table ("
            "id INTEGER PRIMARY KEY, name TEXT NOT NULL, "
            "value REAL, created_at TEXT)"
        ))
        session.execute(text("DELETE FROM demo_table"))
        session.execute(
            text("INSERT INTO demo_table (id, name, value, created_at) "
                 "VALUES (:id, :name, :value, :created_at)"),
            [
                {"id": 1, "name": "api-gateway", "value": 63.2, "created_at": "2026-08-24"},
                {"id": 2, "name": "order-service", "value": 91.5, "created_at": "2026-08-25"},
                {"id": 3, "name": "auth-service", "value": 45.7, "created_at": "2026-08-26"},
            ],
        )

    # 幂等注册数据源
    dao = ConnectConfigDao()
    if dao.get_by_names(DB_NAME) is not None:
        dao.delete_db(DB_NAME)
    dao.add_file_db(
        db_name=DB_NAME, db_type="sqlite", db_path=str(DEMO_DB),
        comment="AppCard demo datasource", user_id="",
    )
    row = dao.get_by_names(DB_NAME)
    if row is None:
        raise RuntimeError("demo datasource not registered")
    return int(row.id)


def _insert_app_card(workspace_id: int, datasource_id: int) -> int:
    import json
    code = DEMO_CODE.replace("</script", "<\\/script")
    config = {
        "tabs": [{"key": "overview", "title": "总览"}],
        "params": [
            {"key": "time_range", "label": "时间范围", "type": "daterange", "default_value": "LAST_7D"},
        ],
        "default_params": {},
    }
    queries = [
        {
            "key": "q_metrics", "kind": "sql", "sql": DEMO_SQL,
            "datasource_id": datasource_id,
            "bind_params": {"start": "2020-01-01"}, "limit": 50,
        },
    ]
    dao = AppCardDao()
    session = dao.get_raw_session()
    try:
        existing = (
            session.query(AppCardEntity)
            .filter(AppCardEntity.workspace_id == workspace_id,
                    AppCardEntity.name == DEMO_CARD_NAME)
            .all()
        )
        for e in existing:
            session.delete(e)
        session.flush()
        card = AppCardEntity(
            workspace_id=workspace_id, name=DEMO_CARD_NAME, description="Agent 生成的 demo 应用卡片",
            kind="dashboard", status="validated", code=code,
            config_json=json.dumps(config, ensure_ascii=False),
            queries_json=json.dumps(queries, ensure_ascii=False),
            current_version=1, source_task_id=None, created_by="seed",
        )
        session.add(card)
        session.commit()
        return int(card.id)
    finally:
        session.close()


def main(argv) -> int:
    workspace_id = int(argv[1]) if len(argv) > 1 else 1
    _init_metadata_db()
    datasource_id = _ensure_demo_datasource()
    card_id = _insert_app_card(workspace_id, datasource_id)
    print(f"OK 已创建 app_card id={card_id} workspace_id={workspace_id} datasource_id={datasource_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
