# 复杂范例（可直接模仿）

对应工作流「步骤 4：编写代码」。多 tab + 深色主题 + 指标卡 + 内联 SVG 趋势图 + 时间范围交互 + 三态，并演示「布局先渲 + 分区块异步取数」。`queries` 提供 `q_totals`（总指标）、`q_trend`（趋势）、`q_metrics`（明细）。

```js
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

var root = el('root');
root.innerHTML =
 '<div class="ac">'+
  '<div class="bar"><div><div class="title">容量巡检核心看板</div><div class="sub">Agent 生成的常驻子应用</div></div><div class="pills" id="pills"></div></div>'+
  '<div class="grid" id="cards"></div>'+
  '<div class="chart"><div class="h">CPU 使用率趋势</div><svg class="svg" id="svg" preserveAspectRatio="none"></svg><div class="st" id="note"></div></div>'+
  '<div class="tbl" id="tbl" style="margin-top:12px"></div>'+
 '</div>';

var state = { start: '2020-01-01' };
var pills = [['2020-01-01','显示全部'],['2026-08-26','今天'],['2026-08-01','近 7 天']];
function esc(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;'); }
function fmt(n){ return n==null?'—':Number(n).toFixed(2); }
/* —— DOM 安全辅助: 任何 getElementById 的写入都必须判空, 否则元素不存在时
 * 会抛 "Cannot set properties of null (setting 'textContent')" 把整屏弄崩。 — */
function el(id){ return document.getElementById(id); }
function take(id, fn){ var e=el(id); if(e) fn(e); }       // 元素存在才操作
function setH(id, html){ take(id, function(e){ e.innerHTML=html; }); }

function renderPills(){
  setH('pills', pills.map(function(p){
    return '<button class="pill'+(p[0]===state.start?' on':'')+'" data-s="'+p[0]+'">'+p[1]+'</button>';
  }).join(''));
}
function draw(rows){
  var svg=el('svg'), W=680, H=180, pad=22, w=W-pad*2, h=H-pad*2;
  var nums=(rows||[]).map(function(r){return Number(r.cpu)||0;});
  var max=Math.max.apply(null,nums.concat([1]));
  var pts=(rows||[]).map(function(r,i){
    return [pad+(i*(w/Math.max(1,(rows.length-1)))), pad+h-((Number(r.cpu)||0)/max)*h];
  });
  var line=pts.map(function(p,i){return (i?'L':'M')+p[0].toFixed(1)+','+p[1].toFixed(1);}).join(' ');
  var area=line+' L'+(pts.length?pts[pts.length-1][0].toFixed(1):pad)+','+(pad+h)+' L'+(pts.length?pts[0][0].toFixed(1):pad)+','+(pad+h)+' Z';
  var g='';
  for(var i=0;i<=4;i++){ var y=pad+h-(h*i/4); g+='<line x1="'+pad+'" y1="'+y+'" x2="'+(W-pad)+'" y2="'+y+'" stroke="#334155" stroke-width="1"/>'; }
  if(svg){ svg.innerHTML = g +
    (pts.length? '<path d="'+area+'" fill="rgba(37,99,235,0.18)"/>' : '') +
    (pts.length? '<path d="'+line+'" fill="none" stroke="#3b82f6" stroke-width="2.5"/>' : '') +
    pts.map(function(p){return '<circle cx="'+p[0].toFixed(1)+'" cy="'+p[1].toFixed(1)+'" r="3" fill="#3b82f6"/>';}).join('');
  }
  setH('note', '峰值: <b>'+fmt(max)+'</b> · '+(rows||[]).length+' 个点');
}
/* —— 基础规范: 布局先渲 + 分区块异步取数。每个数据区块一个 query_key、
 * 各自独立 loading/empty/error 三态、独立渲染; 各区块并行发出、先到先渲。 — */
function kSkeleton(){ return '<div class="k"><div class="t">…</div><div class="v" style="opacity:.4">‥‥</div></div>'; }
function loadTotals(){                                   // 指标卡区 (q_totals)
  setH('cards', kSkeleton()+kSkeleton()+kSkeleton());    // 各自先上骨架
  GyraAppCard.op('query.sql', { bind_params: { start: state.start } }, 'q_totals').then(function(res){
    if(!res || res.trust==='none' || !res.rows || !res.rows[0]){ setH('cards','<div class="st">指标加载失败或无数据</div>'); return; }
    var t=res.rows[0];
    setH('cards',
      '<div class="k"><div class="t">记录数</div><div class="v">'+fmt(t.n)+'</div></div>'+
      '<div class="k"><div class="t">平均值</div><div class="v">'+fmt(t.avg)+'</div></div>'+
      '<div class="k"><div class="t">最大值</div><div class="v">'+fmt(t.max)+'</div></div>');
  }).catch(function(){ setH('cards','<div class="st">指标加载失败</div>'); });
}
function loadTrend(){                                     // 趋势图区 (q_trend)
  setH('note','加载中…');
  GyraAppCard.op('query.sql', { bind_params: { start: state.start } }, 'q_trend').then(function(res){
    if(!res || res.trust==='none'){ setH('note','趋势加载失败'); return; }
    var rows=(res.rows)||[];
    if(!rows.length){ setH('note','暂无趋势数据'); return; }
    draw(rows);
  }).catch(function(){ setH('note','趋势加载失败'); });
}
function loadMetrics(){                                   // 明细表区 (q_metrics)
  setH('tbl','<div class="st">加载中…</div>');
  GyraAppCard.op('query.sql', { bind_params: { start: state.start } }, 'q_metrics').then(function(res){
    if(!res || res.trust==='none'){ setH('tbl','<div class="st">明细加载失败</div>'); return; }
    var rows=(res.rows)||[];
    if(!rows.length){ setH('tbl','<div class="st">暂无数据</div>'); return; }
    setH('tbl',
      '<table style="width:100%"><thead><tr><th>服务</th><th>指标值</th><th>日期</th></tr></thead><tbody>'+
      rows.map(function(r){return '<tr><td>'+esc(r.service)+'</td><td>'+fmt(r.cpu)+'</td><td>'+esc(r.day)+'</td></tr>';}).join('')+
      '</tbody></table>');
  }).catch(function(){ setH('tbl','<div class="st">明细加载失败</div>'); });
}
function load(){                                          // 骨架已在首屏布局写死
  renderPills();
  loadTotals();                                           // 三个区块并行发出、各自渲染
  loadTrend();
  loadMetrics();
}
take('pills', function(e){ e.addEventListener('click', function(ev){
  var b=ev.target.closest('button'); if(!b) return;
  state.start=b.getAttribute('data-s'); load();
}); });
load();
```

> 上面代码可直接作为模板。把它替换成任何更复杂的布局、主题、图表都可。