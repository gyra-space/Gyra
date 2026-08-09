// Gyra 推广文档图表 —— 记忆晋升六维评分模型
(function () {
  var style = getComputedStyle(document.documentElement);
  var accent = style.getPropertyValue('--accent').trim();
  var accent2 = style.getPropertyValue('--accent2').trim();
  var ink = style.getPropertyValue('--ink').trim();
  var muted = style.getPropertyValue('--muted').trim();
  var rule = style.getPropertyValue('--rule').trim();
  var green = style.getPropertyValue('--green').trim();
  var magenta = style.getPropertyValue('--magenta').trim();

  var root = document.getElementById('chart-memory');
  if (!root) return;

  var chart = echarts.init(root);

  var option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(15,21,36,0.95)',
      borderColor: rule,
      textStyle: { color: ink, fontSize: 12 }
    },
    legend: {
      bottom: 0,
      textStyle: { color: muted, fontFamily: 'WorkSans, sans-serif' },
      itemWidth: 14,
      itemHeight: 14
    },
    radar: {
      indicator: [
        { name: '复用度', max: 100 },
        { name: '价值度', max: 100 },
        { name: '时效性', max: 100 },
        { name: '相关性', max: 100 },
        { name: '完整性', max: 100 },
        { name: '可信度', max: 100 }
      ],
      radius: '62%',
      center: ['50%', '46%'],
      splitNumber: 4,
      axisName: { color: '#c6d3ea', fontSize: 12, fontFamily: 'WorkSans, sans-serif' },
      splitArea: { areaStyle: { color: ['rgba(0,212,255,0.02)', 'rgba(0,212,255,0.04)'] } },
      splitLine: { lineStyle: { color: 'rgba(0,212,255,0.18)' } },
      axisLine: { lineStyle: { color: 'rgba(0,212,255,0.18)' } }
    },
    series: [
      {
        name: '晋升阈值',
        type: 'radar',
        symbol: 'none',
        lineStyle: { color: accent2, width: 2, type: 'dashed' },
        areaStyle: { color: 'rgba(77,124,255,0.10)' },
        data: [{ value: [70, 70, 70, 70, 70, 70], name: '晋升阈值' }]
      },
      {
        name: '实际评分',
        type: 'radar',
        symbol: 'circle',
        symbolSize: 5,
        itemStyle: { color: accent },
        lineStyle: { color: accent, width: 2 },
        areaStyle: { color: 'rgba(0,212,255,0.22)' },
        data: [{ value: [88, 82, 64, 91, 76, 85], name: '实际评分' }]
      }
    ]
  };

  chart.setOption(option);
  window.addEventListener('resize', function () { chart.resize(); });
})();