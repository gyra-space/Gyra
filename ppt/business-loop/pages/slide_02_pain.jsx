<Slide style={{ width: '1280px', height: '720px', background: '#0F172A', padding: '20px 64px', fontFamily: 'Noto Sans CJK SC, PingFang SC, Helvetica Neue, sans-serif' }}>
  {/* A 标题块 */}
  <Box style={{ height: 100, flexDirection: 'row', alignItems: 'center', gap: 16 }}>
    <Box style={{ width: 8, height: 48, background: 'linear-gradient(180deg, #3B82F6 0%, #22D3EE 100%)', borderRadius: 4 }} />
    <Box>
      <Text style={{ fontSize: 36, fontWeight: 'bold', color: '#F1F5F9' }}>为什么 AI 总是"用完即弃"？</Text>
      <Text style={{ fontSize: 16, color: '#94A3B8', marginTop: 6 }}>企业引入 AI 后最常见的三个困境</Text>
    </Box>
  </Box>
  {/* B 内容区：左标题 + 右内容 */}
  <Box style={{ height: 520, flexDirection: 'row', gap: 32 }}>
    {/* 左侧标题栏 32% */}
    <Box style={{ width: '32%', background: '#1E293B', borderRadius: 16, padding: 36, border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'column', justifyContent: 'space-between' }}>
      <Box>
        <Text style={{ fontSize: 26, fontWeight: 'bold', color: '#F1F5F9', lineHeight: 1.5 }}>AI 能干活，<br />但干得<span style={{ color: '#F59E0B' }}>不长久</span>、<br />留得<span style={{ color: '#F59E0B' }}>不下来</span></Text>
        <Text style={{ fontSize: 18, color: '#94A3B8', lineHeight: 1.7, marginTop: 24 }}>绝大多数 AI 产品的循环，止于"任务完成"——而不是止于"场景沉淀"。</Text>
      </Box>
      <Box style={{ marginTop: 'auto', paddingTop: 20, borderTop: '1px solid rgba(148,163,184,0.25)' }}>
        <Text style={{ fontSize: 16, color: '#22D3EE', lineHeight: 1.6 }}>业务 Loop 要解决的，<br />正是这三个"不闭环"。</Text>
      </Box>
    </Box>
    {/* 右侧三痛点纵向列表 */}
    <Box style={{ flex: 1, flexDirection: 'column', gap: 20 }}>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 16, padding: '24px 32px', border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'row', gap: 24, alignItems: 'center' }}>
        <Box style={{ width: 64, height: 64, borderRadius: 16, background: 'rgba(245,158,11,0.15)', justifyContent: 'center', alignItems: 'center' }}>
          <FAIcon name="exclamation-circle" style={{ fill: '#F59E0B', width: 32, height: 32 }} />
        </Box>
        <Box style={{ flex: 1 }}>
          <Text style={{ fontSize: 24, fontWeight: 'bold', color: '#F1F5F9' }}>数据不敢信</Text>
          <Text style={{ fontSize: 17, color: '#94A3B8', lineHeight: 1.6, marginTop: 8 }}>同一份报表两个数字，口径谁也说不清。AI 给的数据没有出处，不敢直接拿去汇报、更不敢拿来决策。</Text>
        </Box>
      </Box>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 16, padding: '24px 32px', border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'row', gap: 24, alignItems: 'center' }}>
        <Box style={{ width: 64, height: 64, borderRadius: 16, background: 'rgba(59,130,246,0.18)', justifyContent: 'center', alignItems: 'center' }}>
          <FAIcon name="times-circle" style={{ fill: '#3B82F6', width: 32, height: 32 }} />
        </Box>
        <Box style={{ flex: 1 }}>
          <Text style={{ fontSize: 24, fontWeight: 'bold', color: '#F1F5F9' }}>任务一次性</Text>
          <Text style={{ fontSize: 17, color: '#94A3B8', lineHeight: 1.6, marginTop: 8 }}>每次对话从零开始，任务结束一切蒸发。月报这个月做完了，下个月还得重新教一遍。</Text>
        </Box>
      </Box>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 16, padding: '24px 32px', border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'row', gap: 24, alignItems: 'center' }}>
        <Box style={{ width: 64, height: 64, borderRadius: 16, background: 'rgba(34,211,238,0.15)', justifyContent: 'center', alignItems: 'center' }}>
          <FAIcon name="folder-open" style={{ fill: '#22D3EE', width: 32, height: 32 }} />
        </Box>
        <Box style={{ flex: 1 }}>
          <Text style={{ fontSize: 24, fontWeight: 'bold', color: '#F1F5F9' }}>经验不沉淀</Text>
          <Text style={{ fontSize: 17, color: '#94A3B8', lineHeight: 1.6, marginTop: 8 }}>老师傅的经验在人脑里，AI 做好的方案留在聊天记录里。人一走、窗一关，团队资产毫无变厚。</Text>
        </Box>
      </Box>
    </Box>
  </Box>
  {/* C 页脚条 */}
  <Box style={{ height: 60, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
    <Text style={{ fontSize: 14, color: '#94A3B8' }}>Gyra · 业务场景 Loop</Text>
    <Text style={{ fontSize: 14, color: '#94A3B8' }}>02 / 12</Text>
  </Box>
</Slide>
