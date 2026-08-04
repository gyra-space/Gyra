<Slide style={{ width: '1280px', height: '720px', background: '#0F172A', padding: '20px 64px', fontFamily: 'Noto Sans CJK SC, PingFang SC, Helvetica Neue, sans-serif' }}>
  {/* A 标题块 */}
  <Box style={{ height: 100, flexDirection: 'row', alignItems: 'center', gap: 16 }}>
    <Box style={{ width: 8, height: 48, background: 'linear-gradient(180deg, #3B82F6 0%, #22D3EE 100%)', borderRadius: 4 }} />
    <Box>
      <Text style={{ fontSize: 36, fontWeight: 'bold', color: '#F1F5F9' }}>数据学习：每一次执行都沉淀为资产</Text>
      <Text style={{ fontSize: 16, color: '#94A3B8', marginTop: 6 }}>强制沉淀机制，让产出物不会"用完即弃"，而是一层层垒厚</Text>
    </Box>
  </Box>
  {/* B 内容区：左大图 58% + 右侧文字 */}
  <Box style={{ height: 520, flexDirection: 'row', gap: 32 }}>
    {/* 左：资产分层结构图 */}
    <Box style={{ width: '58%', background: '#1E293B', borderRadius: 16, border: '1px solid rgba(148,163,184,0.25)', padding: 28, flexDirection: 'row', gap: 20 }}>
      {/* 左侧上升箭头 */}
      <Box style={{ width: 64, flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 10 }}>
        <FAIcon name="arrow-up" style={{ fill: '#F59E0B', width: 30, height: 30 }} />
        <Text style={{ fontSize: 16, fontWeight: 'bold', color: '#F59E0B', textAlign: 'center', lineHeight: 1.5 }}>沉<br />淀<br />厚<br />度</Text>
      </Box>
      {/* 分层堆叠 */}
      <Box style={{ flex: 1, flexDirection: 'column', justifyContent: 'flex-end', gap: 10 }}>
        <Box style={{ width: '62%', alignSelf: 'center', background: 'linear-gradient(135deg, #3B82F6 0%, #22D3EE 100%)', borderRadius: 10, padding: '11px 16px' }}><Text style={{ fontSize: 15, fontWeight: 'bold', color: '#0F172A', textAlign: 'center' }}>Template 模板</Text></Box>
        <Box style={{ width: '72%', alignSelf: 'center', background: 'rgba(34,211,238,0.30)', borderRadius: 10, padding: '11px 16px', border: '1px solid rgba(34,211,238,0.5)' }}><Text style={{ fontSize: 15, fontWeight: 'bold', color: '#F1F5F9', textAlign: 'center' }}>Metric 指标口径</Text></Box>
        <Box style={{ width: '82%', alignSelf: 'center', background: 'rgba(59,130,246,0.28)', borderRadius: 10, padding: '11px 16px', border: '1px solid rgba(59,130,246,0.5)' }}><Text style={{ fontSize: 15, fontWeight: 'bold', color: '#F1F5F9', textAlign: 'center' }}>Runbook 操作手册</Text></Box>
        <Box style={{ width: '91%', alignSelf: 'center', background: 'rgba(59,130,246,0.18)', borderRadius: 10, padding: '11px 16px', border: '1px solid rgba(59,130,246,0.4)' }}><Text style={{ fontSize: 15, fontWeight: 'bold', color: '#F1F5F9', textAlign: 'center' }}>Case 历史案例</Text></Box>
        <Box style={{ width: '100%', background: 'rgba(148,163,184,0.14)', borderRadius: 10, padding: '11px 16px', border: '1px solid rgba(148,163,184,0.35)' }}><Text style={{ fontSize: 15, fontWeight: 'bold', color: '#F1F5F9', textAlign: 'center' }}>Artifact 历史工件</Text></Box>
        <Text style={{ fontSize: 13, color: '#94A3B8', textAlign: 'center', marginTop: 4 }}>每次任务的产出 → 自动归类为五类资产，越垒越厚</Text>
      </Box>
    </Box>
    {/* 右：四个机制 */}
    <Box style={{ flex: 1, flexDirection: 'column', gap: 14 }}>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 14, padding: '16px 20px', border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'column', justifyContent: 'center' }}>
        <Box style={{ flexDirection: 'row', gap: 10, alignItems: 'center' }}><FAIcon name="shield" style={{ fill: '#F59E0B', width: 22, height: 22 }} /><Text style={{ fontSize: 19, fontWeight: 'bold', color: '#F1F5F9' }}>强制沉淀</Text></Box>
        <Text style={{ fontSize: 14.5, color: '#94A3B8', lineHeight: 1.6, marginTop: 8 }}>任务关闭前必须完成沉淀，没沉淀系统不放行——沉淀不是"好习惯"，是硬规则。</Text>
      </Box>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 14, padding: '16px 20px', border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'column', justifyContent: 'center' }}>
        <Box style={{ flexDirection: 'row', gap: 10, alignItems: 'center' }}><FAIcon name="book" style={{ fill: '#3B82F6', width: 22, height: 22 }} /><Text style={{ fontSize: 19, fontWeight: 'bold', color: '#F1F5F9' }}>资产自学习</Text></Box>
        <Text style={{ fontSize: 14.5, color: '#94A3B8', lineHeight: 1.6, marginTop: 8 }}>新资产自动做 spec 学习，理解结构与含义，进入语义确认流程，变成"可检索、可复用"的知识。</Text>
      </Box>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 14, padding: '16px 20px', border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'column', justifyContent: 'center' }}>
        <Box style={{ flexDirection: 'row', gap: 10, alignItems: 'center' }}><FAIcon name="sync" style={{ fill: '#22D3EE', width: 22, height: 22 }} /><Text style={{ fontSize: 19, fontWeight: 'bold', color: '#F1F5F9' }}>漂移检测</Text></Box>
        <Text style={{ fontSize: 14.5, color: '#94A3B8', lineHeight: 1.6, marginTop: 8 }}>数据口径发生变化时自动发现，生成修正提案，人确认后更新——资产始终与现实同步。</Text>
      </Box>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 14, padding: '16px 20px', border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'column', justifyContent: 'center' }}>
        <Box style={{ flexDirection: 'row', gap: 10, alignItems: 'center' }}><FAIcon name="plus" style={{ fill: '#F59E0B', width: 22, height: 22 }} /><Text style={{ fontSize: 19, fontWeight: 'bold', color: '#F1F5F9' }}>复用加速</Text></Box>
        <Text style={{ fontSize: 14.5, color: '#94A3B8', lineHeight: 1.6, marginTop: 8 }}>下次任务直接调用已沉淀资产，不用从零开始——执行一次，受益每次。</Text>
      </Box>
    </Box>
  </Box>
  {/* C 页脚条 */}
  <Box style={{ height: 60, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
    <Text style={{ fontSize: 14, color: '#94A3B8' }}>Gyra · 业务场景 Loop</Text>
    <Text style={{ fontSize: 14, color: '#94A3B8' }}>06 / 12</Text>
  </Box>
</Slide>
