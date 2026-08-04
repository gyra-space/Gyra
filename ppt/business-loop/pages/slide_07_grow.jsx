<Slide style={{ width: '1280px', height: '720px', background: '#0F172A', padding: '20px 64px', fontFamily: 'Noto Sans CJK SC, PingFang SC, Helvetica Neue, sans-serif' }}>
  {/* A 标题块 */}
  <Box style={{ height: 100, flexDirection: 'row', alignItems: 'center', gap: 16 }}>
    <Box style={{ width: 8, height: 48, background: 'linear-gradient(180deg, #3B82F6 0%, #22D3EE 100%)', borderRadius: 4 }} />
    <Box>
      <Text style={{ fontSize: 36, fontWeight: 'bold', color: '#F1F5F9' }}>成长飞轮：Agent 越用越准</Text>
      <Text style={{ fontSize: 16, color: '#94A3B8', marginTop: 6 }}>跑过的任务，变成下次的加速——像人一样，边工作边长经验</Text>
    </Box>
  </Box>
  {/* B 内容区：非对称双栏 65:35 */}
  <Box style={{ height: 520, flexDirection: 'row', gap: 32 }}>
    {/* 左 65%：记忆进化循环 2x2 */}
    <Box style={{ width: '65%', background: '#1E293B', borderRadius: 16, border: '1px solid rgba(148,163,184,0.25)', padding: 28, flexDirection: 'column' }}>
      <Text style={{ fontSize: 20, fontWeight: 'bold', color: '#22D3EE' }}>记忆进化：三级节奏，边跑边沉淀</Text>
      <Box style={{ flex: 1, marginTop: 20, flexDirection: 'column', gap: 14 }}>
        <Box style={{ flex: 1, flexDirection: 'row', gap: 14 }}>
          <Box style={{ flex: 1, background: 'rgba(59,130,246,0.16)', borderRadius: 12, padding: 18, border: '1px solid rgba(59,130,246,0.45)', flexDirection: 'column', justifyContent: 'center' }}>
            <Text style={{ fontSize: 15, color: '#3B82F6', fontWeight: 'bold' }}>每一轮</Text>
            <Text style={{ fontSize: 19, fontWeight: 'bold', color: '#F1F5F9', marginTop: 4 }}>随手记录</Text>
            <Text style={{ fontSize: 13.5, color: '#94A3B8', lineHeight: 1.5, marginTop: 6 }}>工作中的关键发现，轻量级随手记下，不打断干活</Text>
          </Box>
          <Box style={{ justifyContent: 'center' }}><FAIcon name="arrow-right" style={{ fill: '#3B82F6', width: 22, height: 22 }} /></Box>
          <Box style={{ flex: 1, background: 'rgba(59,130,246,0.16)', borderRadius: 12, padding: 18, border: '1px solid rgba(59,130,246,0.45)', flexDirection: 'column', justifyContent: 'center' }}>
            <Text style={{ fontSize: 15, color: '#3B82F6', fontWeight: 'bold' }}>每 10 轮</Text>
            <Text style={{ fontSize: 19, fontWeight: 'bold', color: '#F1F5F9', marginTop: 4 }}>反思整合</Text>
            <Text style={{ fontSize: 13.5, color: '#94A3B8', lineHeight: 1.5, marginTop: 6 }}>定期回头整理：去重、精炼，把碎片连成经验</Text>
          </Box>
        </Box>
        <Box style={{ flexDirection: 'row' }}>
          <Box style={{ flex: 1, alignItems: 'center' }}><FAIcon name="arrow-up" style={{ fill: '#F59E0B', width: 20, height: 20 }} /></Box>
          <Box style={{ width: 36 }} />
          <Box style={{ flex: 1, alignItems: 'center' }}><FAIcon name="arrow-down" style={{ fill: '#3B82F6', width: 20, height: 20 }} /></Box>
        </Box>
        <Box style={{ flex: 1, flexDirection: 'row', gap: 14 }}>
          <Box style={{ flex: 1, background: 'rgba(34,211,238,0.14)', borderRadius: 12, padding: 18, border: '1px solid rgba(34,211,238,0.45)', flexDirection: 'column', justifyContent: 'center' }}>
            <Text style={{ fontSize: 15, color: '#22D3EE', fontWeight: 'bold' }}>下次任务</Text>
            <Text style={{ fontSize: 19, fontWeight: 'bold', color: '#F1F5F9', marginTop: 4 }}>检索加速</Text>
            <Text style={{ fontSize: 13.5, color: '#94A3B8', lineHeight: 1.5, marginTop: 6 }}>带着过去 N 次任务的经验上场，起步就是熟手</Text>
          </Box>
          <Box style={{ justifyContent: 'center' }}><FAIcon name="arrow-left" style={{ fill: '#F59E0B', width: 22, height: 22 }} /></Box>
          <Box style={{ flex: 1, background: 'rgba(245,158,11,0.14)', borderRadius: 12, padding: 18, border: '1px solid rgba(245,158,11,0.5)', flexDirection: 'column', justifyContent: 'center' }}>
            <Text style={{ fontSize: 15, color: '#F59E0B', fontWeight: 'bold' }}>会话结束</Text>
            <Text style={{ fontSize: 19, fontWeight: 'bold', color: '#F1F5F9', marginTop: 4 }}>晋升长期记忆</Text>
            <Text style={{ fontSize: 13.5, color: '#94A3B8', lineHeight: 1.5, marginTop: 6 }}>真正有用的经验固化下来，无用的自然沉底</Text>
          </Box>
        </Box>
      </Box>
    </Box>
    {/* 右 35%：大数字锚点 + 评测驱动 */}
    <Box style={{ flex: 1, flexDirection: 'column', gap: 18 }}>
      <Box style={{ background: '#1E293B', borderRadius: 16, border: '1px solid rgba(245,158,11,0.4)', padding: 26, flexDirection: 'column', alignItems: 'center' }}>
        <Text style={{ fontSize: 84, fontWeight: 'bold', color: '#F59E0B', lineHeight: 1.0 }}>6<span style={{ fontSize: 36 }}>维</span></Text>
        <Text style={{ fontSize: 17, color: '#F1F5F9', fontWeight: 'bold', marginTop: 8 }}>评测评分模型</Text>
        <Text style={{ fontSize: 14, color: '#94A3B8', textAlign: 'center', lineHeight: 1.6, marginTop: 8 }}>相关度 · 频次 · 多样性<br />时效 · 持续有用 · 概念广度</Text>
      </Box>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 16, border: '1px solid rgba(148,163,184,0.25)', padding: 24, flexDirection: 'column', justifyContent: 'center' }}>
        <Text style={{ fontSize: 19, fontWeight: 'bold', color: '#F1F5F9' }}>用真实使用数据说话</Text>
        <Text style={{ fontSize: 15, color: '#94A3B8', lineHeight: 1.7, marginTop: 12 }}>哪些经验被反复召回、跨很多天仍然有用，哪些就固化；晋升有门槛、每轮限量——<span style={{ color: '#22D3EE' }}>不是凭感觉，是凭数据</span>。Agent 不再是"每次从零开始"。</Text>
      </Box>
    </Box>
  </Box>
  {/* C 页脚条 */}
  <Box style={{ height: 60, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
    <Text style={{ fontSize: 14, color: '#94A3B8' }}>Gyra · 业务场景 Loop</Text>
    <Text style={{ fontSize: 14, color: '#94A3B8' }}>07 / 12</Text>
  </Box>
</Slide>
