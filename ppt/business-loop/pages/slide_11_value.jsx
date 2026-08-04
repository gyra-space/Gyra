<Slide style={{ width: '1280px', height: '720px', background: '#0F172A', padding: '20px 64px', fontFamily: 'Noto Sans CJK SC, PingFang SC, Helvetica Neue, sans-serif' }}>
  {/* A 标题块 */}
  <Box style={{ height: 100, flexDirection: 'row', alignItems: 'center', gap: 16 }}>
    <Box style={{ width: 8, height: 48, background: 'linear-gradient(180deg, #3B82F6 0%, #22D3EE 100%)', borderRadius: 4 }} />
    <Box>
      <Text style={{ fontSize: 36, fontWeight: 'bold', color: '#F1F5F9' }}>对客户意味着什么</Text>
      <Text style={{ fontSize: 16, color: '#94A3B8', marginTop: 6 }}>一个 7×24 在场、越用越懂你们团队的 AI 队友</Text>
    </Box>
  </Box>
  {/* B 内容区：巨型数字 + 三行洞察 */}
  <Box style={{ height: 520, flexDirection: 'column', gap: 20 }}>
    {/* 巨型数字锚点行 */}
    <Box style={{ flexDirection: 'row', alignItems: 'center', gap: 40, paddingLeft: 12 }}>
      <Text style={{ fontSize: 110, fontWeight: 'bold', lineHeight: 1.0, backgroundImage: 'linear-gradient(135deg, #3B82F6 0%, #22D3EE 100%)', backgroundClip: 'text', color: 'transparent' }}>7×24</Text>
      <Box style={{ flex: 1 }}>
        <Text style={{ fontSize: 24, fontWeight: 'bold', color: '#F1F5F9', lineHeight: 1.4 }}>场景空间始终在线</Text>
        <Text style={{ fontSize: 17, color: '#94A3B8', lineHeight: 1.6, marginTop: 6 }}>触发器持续监听，告警来了有人看、月报到了有人出——AI 不是"被调用时才存在"，而是始终在场。</Text>
      </Box>
    </Box>
    {/* 三行价值洞察 */}
    <Box style={{ flex: 1, flexDirection: 'column', gap: 14 }}>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 14, padding: '16px 28px', border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'row', gap: 22, alignItems: 'center' }}>
        <Box style={{ width: 56, height: 56, borderRadius: 14, background: 'rgba(59,130,246,0.18)', justifyContent: 'center', alignItems: 'center' }}><FAIcon name="check-circle" style={{ fill: '#3B82F6', width: 28, height: 28 }} /></Box>
        <Box style={{ flex: 1 }}>
          <Text style={{ fontSize: 21, fontWeight: 'bold', color: '#F1F5F9' }}>数据敢用了</Text>
          <Text style={{ fontSize: 15.5, color: '#94A3B8', lineHeight: 1.55, marginTop: 4 }}>每个数字都有口径、有出处、有人确认过。汇报和决策，可以直接引用。</Text>
        </Box>
      </Box>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 14, padding: '16px 28px', border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'row', gap: 22, alignItems: 'center' }}>
        <Box style={{ width: 56, height: 56, borderRadius: 14, background: 'rgba(34,211,238,0.15)', justifyContent: 'center', alignItems: 'center' }}><FAIcon name="users" style={{ fill: '#22D3EE', width: 28, height: 28 }} /></Box>
        <Box style={{ flex: 1 }}>
          <Text style={{ fontSize: 21, fontWeight: 'bold', color: '#F1F5F9' }}>活有人干了</Text>
          <Text style={{ fontSize: 15.5, color: '#94A3B8', lineHeight: 1.55, marginTop: 4 }}>巡检、对账、月报、应急响应自动跑，人只需要在关键阀门上做决策。</Text>
        </Box>
      </Box>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 14, padding: '16px 28px', border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'row', gap: 22, alignItems: 'center' }}>
        <Box style={{ width: 56, height: 56, borderRadius: 14, background: 'rgba(245,158,11,0.15)', justifyContent: 'center', alignItems: 'center' }}><FAIcon name="chart-line" style={{ fill: '#F59E0B', width: 28, height: 28 }} /></Box>
        <Box style={{ flex: 1 }}>
          <Text style={{ fontSize: 21, fontWeight: 'bold', color: '#F1F5F9' }}>经验留得下了</Text>
          <Text style={{ fontSize: 15.5, color: '#94A3B8', lineHeight: 1.55, marginTop: 4 }}>每次执行都沉淀为团队资产。新人进场就是熟手水平，AI 也越用越懂你们。</Text>
        </Box>
      </Box>
    </Box>
  </Box>
  {/* C 页脚条 */}
  <Box style={{ height: 60, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
    <Text style={{ fontSize: 14, color: '#94A3B8' }}>Gyra · 业务场景 Loop</Text>
    <Text style={{ fontSize: 14, color: '#94A3B8' }}>11 / 12</Text>
  </Box>
</Slide>
