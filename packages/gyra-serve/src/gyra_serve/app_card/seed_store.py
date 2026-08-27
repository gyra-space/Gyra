"""AppCard store seed — 建「问卷收集」演示子应用卡片。

与 ``seed.py``(外部数据源 query.sql)不同,本卡片使用**子应用自身数据空间**
(``store.*`` / ``kv.*``,存储在元数据库),展示「问卷收集 → 提交答卷 → 汇总查看」的
端到端读写能力,无需配置任何外部数据源。

运行方式(在 gyra 后端进程外独立执行):
    # 可选 workspace_id, 默认 1
    python -m gyra_serve.app_card.seed_store [workspace_id]

它会:
  1. 确保元数据库已建表(含 AppCard / store 数据空间表);
  2. 幂等插入一张 ``问卷收集`` 卡片, 其 config 声明 data_space 字段契约,
     运行期子应用通过统一 invoke 协议( store.insert / store.query )读写自身数据。
"""
import json
import sys
from pathlib import Path

from gyra.storage.metadata import db

from gyra_serve.app_card.models.models import (  # noqa: F401  注册 AppCard 表
    AppCardDao, AppCardEntity,
)
from gyra_serve.app_card.store.models import (  # noqa: F401  注册 store 数据空间表
    AppCardKvEntity, AppCardRecordEntity,
)

ROOT = Path(__file__).resolve()
for _ in range(8):
    if (ROOT / "pilot").exists():
        break
    ROOT = ROOT.parent
METADATA_DB = ROOT / "pilot" / "meta_data" / "gyra.db"

DEMO_CARD_NAME = "问卷收集（Demo）"


DEMO_STORE_CODE = """document.head.insertAdjacentHTML('beforeend',
 '<style>body{background:#0f172a;color:#e5e7eb;font-family:-apple-system,"PingFang SC",sans-serif;margin:0}'+
 '.ac{padding:16px;max-width:720px;margin:0 auto}.title{font-size:18px;font-weight:700}.sub{font-size:12px;color:#94a3b8;margin-bottom:16px}'+
 '.card{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:16px;margin-bottom:12px}'+
 'label{font-size:12px;color:#94a3b8;display:block;margin:10px 0 4px}'+
 'input,textarea,select{width:100%;background:#0b1220;border:1px solid #334155;border-radius:8px;color:#e5e7eb;padding:8px;font-size:14px;box-sizing:border-box}'+
 'button{background:#2563eb;color:#fff;border:none;border-radius:8px;padding:10px 16px;font-size:14px;cursor:pointer;margin-top:12px}'+
 'button:disabled{opacity:.5}.tbl{width:100%;border-collapse:collapse}.tbl th,.tbl td{padding:8px 10px;font-size:12px;border-bottom:1px solid #334155;text-align:left}'+
 '.tbl th{color:#94a3b8;background:#0b1220}.hint{font-size:12px;color:#34d399;margin-top:8px}.err{font-size:12px;color:#f87171;margin-top:8px}'+
 '.count{font-size:12px;color:#94a3b8;margin-top:12px}</style>');

var root = document.getElementById('root');
root.innerHTML =
 '<div class="ac">'+
  '<div class="title">问卷收集</div><div class="sub">子应用自身数据空间 · 演示 store.* 读写</div>'+
  '<div class="card"><div class="sub">填写并提交一份反馈</div>'+
   '<label>姓名</label><input id="name" placeholder="必填" />'+
   '<label>评分</label><select id="rating"><option value="5">5 分</option><option value="4">4 分</option><option value="3">3 分</option><option value="2">2 分</option><option value="1">1 分</option></select>'+
   '<label>建议</label><textarea id="message" rows="3" placeholder="选填"></textarea>'+
   '<div><button id="submit">提交</button></div><div id="hint" class="hint"></div>'+
  '</div>'+
  '<div class="card"><div class="sub">已收集的反馈</div>'+
   '<table class="tbl"><thead><tr><th>姓名</th><th>评分</th><th>建议</th></tr></thead><tbody id="list"></tbody></table>'+
   '<div id="count" class="count"></div>'+
  '</div>'+
 '</div>';

(function(){
  var clientId = 'qn-' + Date.now() + '-' + Math.floor(Math.random()*1e6);
  function esc(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;'); }
  function refresh(){
    GyraAppCard.store.query({page:1, page_size:50}).then(function(res){
      var rows = (res && res.rows) || [];
      document.getElementById('list').innerHTML = rows.map(function(r){
        return '<tr><td>'+esc(r.name)+'</td><td>'+esc(r.rating)+'</td><td>'+esc(r.message||'')+'</td></tr>';
      }).join('') || '<tr><td colspan="3">暂无提交</td></tr>';
      document.getElementById('count').innerHTML = '共 ' + ((res && res.total) || 0) + ' 条 · 当前 ' + rows.length + ' 条';
    }).catch(function(e){
      document.getElementById('list').innerHTML = '<tr><td colspan="3">加载失败: '+esc(e.message)+'</td></tr>';
    });
  }
  document.getElementById('submit').addEventListener('click', function(){
    var btn = document.getElementById('submit');
    var name = document.getElementById('name').value.trim();
    if(!name){ document.getElementById('hint').className='err'; document.getElementById('hint').textContent='请填写姓名'; return; }
    var record = { name:name, rating:Number(document.getElementById('rating').value), message:document.getElementById('message').value.trim() };
    btn.disabled = true; document.getElementById('hint').className='hint'; document.getElementById('hint').textContent='提交中…';
    GyraAppCard.store.insert({ record:record, dedupe_key:clientId }).then(function(){
      document.getElementById('hint').textContent='提交成功';
      document.getElementById('name').value=''; document.getElementById('message').value='';
      clientId = 'qn-' + Date.now() + '-' + Math.floor(Math.random()*1e6);
      refresh();
    }).catch(function(e){
      document.getElementById('hint').className='err'; document.getElementById('hint').textContent='提交失败: '+esc(e.message);
      btn.disabled = false;
    });
  });
  refresh();
})();
"""


def _init_metadata_db() -> None:
    db.init_db(f"sqlite:///{METADATA_DB}")
    db.create_all()


def _upsert_app_card(workspace_id: int) -> int:
    config = {
        "tabs": [{"key": "collect", "title": "问卷收集"}],
        "params": [],
        "default_params": {},
        "data_space": {
            "fields": {
                "name": {"type": "string", "required": True},
                "rating": {"type": "number"},
                "message": {"type": "string", "required": False},
            },
            "writable": True,
        },
    }
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
            workspace_id=workspace_id, name=DEMO_CARD_NAME,
            description="问卷收集 demo(使用子应用自身数据空间 store.* 读写)",
            kind="dashboard", status="validated", code=DEMO_STORE_CODE,
            config_json=json.dumps(config, ensure_ascii=False),
            queries_json=json.dumps([], ensure_ascii=False),
            icon="\U0001F4DD",
            permissions_json=json.dumps(["member", "owner"], ensure_ascii=False),
            current_version=1, source_task_id=None, created_by="seed_store",
        )
        session.add(card)
        session.commit()
        return int(card.id)
    finally:
        session.close()


def main(argv) -> int:
    workspace_id = int(argv[1]) if len(argv) > 1 else 1
    _init_metadata_db()
    card_id = _upsert_app_card(workspace_id)
    print(f"OK 已创建 store 演示卡片(问卷收集) id={card_id} workspace_id={workspace_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
