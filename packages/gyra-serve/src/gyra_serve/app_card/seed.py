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

DEMO_CODE = """
document.head.insertAdjacentHTML('beforeend',
 '<style>body{background:#0f172a;color:#e5e7eb;font-family:-apple-system,"PingFang SC",sans-serif;margin:0}'+
 '.ac{padding:14px}.bar{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}'+
 '.title{font-size:16px;font-weight:700;letter-spacing:.2px}.sub{font-size:11px;color:#94a3b8}'+
 '.pills{display:flex;gap:6px}.pill{background:#1e293b;color:#cbd5e1;border:1px solid #334155;border-radius:999px;padding:4px 10px;font-size:12px;cursor:pointer}'+
 '.pill.on{background:#2563eb;color:#fff;border-color:#2563eb}'+
 '.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;margin-bottom:12px}'+
 '.k{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:12px}.k .t{font-size:11px;color:#94a3b8}.k .v{font-size:24px;font-weight:700;margin-top:4px}'+
 '.chart{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:12px}.chart .h{font-size:12px;color:#94a3b8;margin-bottom:8px}'+
 '.svg{width:100%;height:180px}.tbl{width:100%;border-collapse:collapse;background:#1e293b;border-radius:12px;overflow:hidden}'+
 '.tbl th,.tbl td{padding:8px 10px;font-size:12px;border-bottom:1px solid #334155;text-align:left}'+
 '.tbl th{color:#94a3b8;background:#0b1220}.st{color:#94a3b8;font-size:12px}.st b{color:#e5e7eb}</style>');

var root = document.getElementById('root');
root.innerHTML =
 '<div class="ac">'+
  '<div class="bar"><div><div class="title">运行指标概览</div><div class="sub">Agent 生成的常驻子应用 · Demo</div></div><div class="pills" id="pills"></div></div>'+
  '<div class="grid" id="cards"></div>'+
  '<div class="chart"><div class="h">指标趋势</div><svg class="svg" id="svg" preserveAspectRatio="none"></svg><div class="st" id="note"></div></div>'+
  '<div class="tbl" id="tbl" style="margin-top:12px"></div>'+
 '</div>';

var state = { start: '2020-01-01' };
var pills = [['2020-01-01','显示全部'],['2026-08-26','今天'],['2026-08-01','近 7 天']];
function esc(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;'); }
function fmt(n){ return n==null?'\\u2014':Number(n).toFixed(2); }

function renderPills(){
  document.getElementById('pills').innerHTML = pills.map(function(p){
    return '<button class="pill'+(p[0]===state.start?' on':'')+'" data-s="'+p[0]+'">'+p[1]+'</button>';
  }).join('');
}
function draw(rows){
  var svg=document.getElementById('svg'), W=680, H=180, pad=22, w=W-pad*2, h=H-pad*2;
  var nums=(rows||[]).map(function(r){return Number(r.cpu)||0;});
  var max=Math.max.apply(null,nums.concat([1]));
  var pts=(rows||[]).map(function(r,i){
    return [pad+(i*(w/Math.max(1,(rows.length-1)))), pad+h-((Number(r.cpu)||0)/max)*h];
  });
  var line=pts.map(function(p,i){return (i?'L':'M')+p[0].toFixed(1)+','+p[1].toFixed(1);}).join(' ');
  var area=line+' L'+(pts.length?pts[pts.length-1][0].toFixed(1):pad)+','+(pad+h)+' L'+(pts.length?pts[0][0].toFixed(1):pad)+','+(pad+h)+' Z';
  var g='';
  for(var i=0;i<=4;i++){ var y=pad+h-(h*i/4); g+='<line x1="'+pad+'" y1="'+y+'" x2="'+(W-pad)+'" y2="'+y+'" stroke="#334155" stroke-width="1"/>'; }
  svg.innerHTML = g +
    (pts.length? '<path d="'+area+'" fill="rgba(37,99,235,0.18)"/>' : '') +
    (pts.length? '<path d="'+line+'" fill="none" stroke="#3b82f6" stroke-width="2.5"/>' : '') +
    pts.map(function(p){return '<circle cx="'+p[0].toFixed(1)+'" cy="'+p[1].toFixed(1)+'" r="3" fill="#3b82f6"/>';}).join('');
  document.getElementById('note').innerHTML = '峰值: <b>'+fmt(max)+'</b> \\u00b7 '+(rows||[]).length+' \\u4e2a\\u70b9';
}
function load(){
  var p = { bind_params: { start: state.start } };
  Promise.all([
    GyraAppCard.op('query.sql', p, 'q_totals'),
    GyraAppCard.op('query.sql', p, 'q_trend'),
    GyraAppCard.op('query.sql', p, 'q_metrics')
  ]).then(function(res){
    var total=(res[0]&&res[0].rows&&res[0].rows[0])||{};
    document.getElementById('cards').innerHTML =
      '<div class="k"><div class="t">\\u8bb0\\u5f55\\u6570</div><div class="v">'+fmt(total.n)+'</div></div>'+
      '<div class="k"><div class="t">\\u5e73\\u5747\\u503c</div><div class="v">'+fmt(total.avg)+'</div></div>'+
      '<div class="k"><div class="t">\\u6700\\u5927\\u503c</div><div class="v">'+fmt(total.max)+'</div></div>';
    draw(res[1]&&res[1].rows);
    var rows=(res[2]&&res[2].rows)||[];
    document.getElementById('tbl').innerHTML =
      '<table style="width:100%"><thead><tr><th>\\u670d\\u52a1</th><th>\\u6307\\u6807\\u503c</th><th>\\u65e5\\u671f</th></tr></thead><tbody>'+
      rows.map(function(r){return '<tr><td>'+esc(r.service)+'</td><td>'+fmt(r.cpu)+'</td><td>'+esc(r.day)+'</td></tr>';}).join('')+
      '</tbody></table>';
  }).catch(function(e){
    var c=document.getElementById('cards'); c.innerHTML='<div class="st">\\u53d6\\u6570\\u5931\\u8d25: '+esc(e.message)+'</div>';
  });
}
document.getElementById('pills').addEventListener('click', function(e){
  var b=e.target.closest('button'); if(!b) return;
  state.start=b.getAttribute('data-s'); renderPills(); load();
});
renderPills(); load();
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
            "key": "q_totals", "kind": "sql",
            "sql": "SELECT COUNT(*) AS n, AVG(value) AS avg, MAX(value) AS max FROM demo_table WHERE created_at >= :start",
            "datasource_id": datasource_id, "bind_params": {"start": "2020-01-01"}, "limit": 10,
        },
        {
            "key": "q_trend", "kind": "sql",
            "sql": "SELECT created_at AS day, AVG(value) AS cpu FROM demo_table WHERE created_at >= :start GROUP BY created_at ORDER BY created_at",
            "datasource_id": datasource_id, "bind_params": {"start": "2020-01-01"}, "limit": 120,
        },
        {
            "key": "q_metrics", "kind": "sql",
            "sql": "SELECT name AS service, value AS cpu, created_at AS day FROM demo_table WHERE created_at >= :start ORDER BY created_at DESC",
            "datasource_id": datasource_id, "bind_params": {"start": "2020-01-01"}, "limit": 50,
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
            icon="\U0001F4CA",
            permissions_json=json.dumps(["member", "owner"], ensure_ascii=False),
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
