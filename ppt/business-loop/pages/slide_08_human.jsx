<Slide style={{ width: '1280px', height: '720px', background: '#0F172A', padding: '20px 64px', fontFamily: 'Noto Sans CJK SC, PingFang SC, Helvetica Neue, sans-serif' }}>
  {/* A 标题块 */}
  <Box style={{ height: 100, flexDirection: 'row', alignItems: 'center', gap: 16 }}>
    <Box style={{ width: 8, height: 48, background: 'linear-gradient(180deg, #3B82F6 0%, #22D3EE 100%)', borderRadius: 4 }} />
    <Box>
      <Text style={{ fontSize: 36, fontWeight: 'bold', color: '#F1F5F9' }}>人机分工：人在阀门上，不在流水线里</Text>
      <Text style={{ fontSize: 16, color: '#94A3B8', marginTop: 6 }}>Agent 自动跑，需要人时变成一条待办，出现在该出现的人面前</Text>
    </Box>
  </Box>
  {/* B 内容区：左标题 + 右内容 */}
  <Box style={{ height: 520, flexDirection: 'row', gap: 32 }}>
    {/* 左侧金句栏 */}
    <Box style={{ width: '32%', background: '#1E293B', borderRadius: 16, padding: 36, border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'column', justifyContent: 'space-between' }}>
      <Text style={{ fontSize: 28, fontWeight: 'bold', color: '#F1F5F9', lineHeight: 1.6 }}>「人不在<br />流水线里，<br />人在流水线的<br /><span style={{ color: '#F59E0B' }}>阀门</span>上。」</Text>
      <Box style={{ marginTop: 'auto', paddingTop: 20, borderTop: '1px solid rgba(148,163,184,0.25)' }}>
        <Text style={{ fontSize: 16, color: '#94A3B8', lineHeight: 1.7 }}>所有需要人的节点，汇入<span style={{ color: '#22D3EE' }}>同一个收件箱</span>。人处理完阀门，流水线继续自动跑。</Text>
      </Box>
    </Box>
    {/* 右侧阀门流程 */}
    <Box style={{ flex: 1, flexDirection: 'column', gap: 12 }}>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 12, padding: '14px 22px', border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'row', gap: 16, alignItems: 'center' }}>
        <FAIcon name="cog" style={{ fill: '#3B82F6', width: 26, height: 26 }} />
        <Box style={{ flex: 1 }}>
          <Text style={{ fontSize: 18, fontWeight: 'bold', color: '#F1F5F9' }}>Agent 自动执行</Text>
          <Text style={{ fontSize: 14, color: '#94A3B8', marginTop: 2 }}>触发、取数、分析、成稿，全程无需人盯</Text>
        </Box>
      </Box>
      <Box style={{ alignItems: 'center' }}><FAIcon name="arrow-down" style={{ fill: '#3B82F6', width: 18, height: 18 }} /></Box>
      <Box style={{ flex: 1, background: 'rgba(245,158,11,0.10)', borderRadius: 12, padding: '14px 22px', border: '1px solid rgba(245,158,11,0.45)', flexDirection: 'row', gap: 16, alignItems: 'center' }}>
        <FAIcon name="exclamation-circle" style={{ fill: '#F59E0B', width: 26, height: 26 }} />
        <Box style={{ flex: 1 }}>
          <Text style={{ fontSize: 18, fontWeight: 'bold', color: '#F1F5F9' }}>碰到阀门，自动挂起</Text>
          <Text style={{ fontSize: 14, color: '#94A3B8', marginTop: 2 }}>执行审批 · 语义确认 · 交付审批 · 异常复核，四类阀门</Text>
        </Box>
      </Box>
      <Box style={{ alignItems: 'center' }}><FAIcon name="arrow-down" style={{ fill: '#3B82F6', width: 18, height: 18 }} /></Box>
      <Box style={{ flex: 1, background: 'rgba(34,211,238,0.10)', borderRadius: 12, padding: '14px 22px', border: '1px solid rgba(34,211,238,0.45)', flexDirection: 'row', gap: 16, alignItems: 'center' }}>
        <FAIcon name="envelope" style={{ fill: '#22D3EE', width: 26, height: 26 }} />
        <Box style={{ flex: 1 }}>
          <Text style={{ fontSize: 18, fontWeight: 'bold', color: '#F1F5F9' }}>一条待办，进收件箱</Text>
          <Text style={{ fontSize: 14, color: '#94A3B8', marginTop: 2 }}>该谁处理就出现在谁的收件箱，附带上下文与建议</Text>
        </Box>
      </Box>
      <Box style={{ alignItems: 'center' }}><FAIcon name="arrow-down" style={{ fill: '#3B82F6', width: 18, height: 18 }} /></Box>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 12, padding: '14px 22px', border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'row', gap: 16, alignItems: 'center' }}>
        <FAIcon name="check-circle" style={{ fill: '#3B82F6', width: 26, height: 26 }} />
        <Box style={{ flex: 1 }}>
          <Text style={{ fontSize: 18, fontWeight: 'bold', color: '#F1F5F9' }}>人一确认，流程继续</Text>
          <Text style={{ fontSize: 14, color: '#94A3B8', marginTop: 2 }}>解除挂起，Agent 接着跑完剩下的路</Text>
        </Box>
      </Box>
      <Box style={{ background: 'rgba(245,158,11,0.08)', border: '1px dashed rgba(245,158,11,0.5)', borderRadius: 12, padding: '12px 20px', flexDirection: 'row', gap: 10, alignItems: 'center' }}>
        <FAIcon name="lock" style={{ fill: '#F59E0B', width: 18, height: 18 }} />
        <Text style={{ fontSize: 15, color: '#F1F5F9' }}><span style={{ color: '#F59E0B', fontWeight: 'bold' }}>红线</span>：改剧本、定口径、动真实系统——AI 只提议，人永远审批</Text>
      </Box>
    </Box>
  </Box>
  {/* C 页脚条 */}
  <Box style={{ height: 60, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
    <Text style={{ fontSize: 14, color: '#94A3B8' }}>Gyra · 业务场景 Loop</Text>
    <Text style={{ fontSize: 14, color: '#94A3B8' }}>08 / 12</Text>
  </Box>
</Slide>
