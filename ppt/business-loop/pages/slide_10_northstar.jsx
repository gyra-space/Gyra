<Slide style={{ width: '1280px', height: '720px', background: '#0F172A', padding: '20px 64px', fontFamily: 'Noto Sans CJK SC, PingFang SC, Helvetica Neue, sans-serif' }}>
  {/* A 标题块 */}
  <Box style={{ height: 100, flexDirection: 'row', alignItems: 'center', gap: 16 }}>
    <Box style={{ width: 8, height: 48, background: 'linear-gradient(180deg, #3B82F6 0%, #22D3EE 100%)', borderRadius: 4 }} />
    <Box>
      <Text style={{ fontSize: 36, fontWeight: 'bold', color: '#F1F5F9' }}>北极星指标：沉淀厚度</Text>
      <Text style={{ fontSize: 16, color: '#94A3B8', marginTop: 6 }}>怎么衡量飞轮真的转起来了？五个可度量的指标</Text>
    </Box>
  </Box>
  {/* B 内容区：左标题 + 右内容 */}
  <Box style={{ height: 520, flexDirection: 'row', gap: 32 }}>
    {/* 左侧定义栏 */}
    <Box style={{ width: '34%', background: '#1E293B', borderRadius: 16, padding: 36, border: '1px solid rgba(245,158,11,0.35)', flexDirection: 'column', justifyContent: 'space-between' }}>
      <Box>
        <FAIcon name="star" style={{ fill: '#F59E0B', width: 44, height: 44 }} />
        <Text style={{ fontSize: 30, fontWeight: 'bold', color: '#F59E0B', marginTop: 18 }}>沉淀厚度</Text>
        <Text style={{ fontSize: 18, color: '#F1F5F9', lineHeight: 1.7, marginTop: 16 }}>一个新成员（人或 Agent）进入空间，<span style={{ color: '#22D3EE' }}>多快能达到"老师傅"的工作水平</span>。</Text>
      </Box>
      <Text style={{ marginTop: 'auto', fontSize: 15, color: '#94A3B8', lineHeight: 1.7, paddingTop: 20, borderTop: '1px solid rgba(148,163,184,0.25)' }}>沉淀越厚，上手越快；<br />上手越快，沉淀又越多。</Text>
    </Box>
    {/* 右侧五指标纵向列表 */}
    <Box style={{ flex: 1, flexDirection: 'column', gap: 12 }}>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 12, padding: '12px 22px', border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'row', alignItems: 'center', gap: 18 }}>
        <Text style={{ fontSize: 26, fontWeight: 'bold', color: '#3B82F6', width: 40 }}>01</Text>
        <Box style={{ flex: 1 }}>
          <Text style={{ fontSize: 18, fontWeight: 'bold', color: '#F1F5F9' }}>资产就绪率</Text>
          <Text style={{ fontSize: 14, color: '#94A3B8', marginTop: 2 }}>完成学习与口径确认的资产占比——资产是不是"能用"状态</Text>
        </Box>
      </Box>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 12, padding: '12px 22px', border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'row', alignItems: 'center', gap: 18 }}>
        <Text style={{ fontSize: 26, fontWeight: 'bold', color: '#3B82F6', width: 40 }}>02</Text>
        <Box style={{ flex: 1 }}>
          <Text style={{ fontSize: 18, fontWeight: 'bold', color: '#F1F5F9' }}>语义覆盖率</Text>
          <Text style={{ fontSize: 14, color: '#94A3B8', marginTop: 2 }}>查询走"已确认口径"与"直连数据库"之比——数字有多少是可信的</Text>
        </Box>
      </Box>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 12, padding: '12px 22px', border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'row', alignItems: 'center', gap: 18 }}>
        <Text style={{ fontSize: 26, fontWeight: 'bold', color: '#22D3EE', width: 40 }}>03</Text>
        <Box style={{ flex: 1 }}>
          <Text style={{ fontSize: 18, fontWeight: 'bold', color: '#F1F5F9' }}>剧本复用率</Text>
          <Text style={{ fontSize: 14, color: '#94A3B8', marginTop: 2 }}>自动触发的任务占比（而非一次性手动发起）——循环有没有自转</Text>
        </Box>
      </Box>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 12, padding: '12px 22px', border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'row', alignItems: 'center', gap: 18 }}>
        <Text style={{ fontSize: 26, fontWeight: 'bold', color: '#22D3EE', width: 40 }}>04</Text>
        <Box style={{ flex: 1 }}>
          <Text style={{ fontSize: 18, fontWeight: 'bold', color: '#F1F5F9' }}>待办响应时长</Text>
          <Text style={{ fontSize: 14, color: '#94A3B8', marginTop: 2 }}>人的阀门是否成为瓶颈——自动化卡在哪里一目了然</Text>
        </Box>
      </Box>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 12, padding: '12px 22px', border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'row', alignItems: 'center', gap: 18 }}>
        <Text style={{ fontSize: 26, fontWeight: 'bold', color: '#F59E0B', width: 40 }}>05</Text>
        <Box style={{ flex: 1 }}>
          <Text style={{ fontSize: 18, fontWeight: 'bold', color: '#F1F5F9' }}>沉淀增速</Text>
          <Text style={{ fontSize: 14, color: '#94A3B8', marginTop: 2 }}>资产条目数随时间的增长曲线——空间变厚的速度</Text>
        </Box>
      </Box>
    </Box>
  </Box>
  {/* C 页脚条 */}
  <Box style={{ height: 60, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
    <Text style={{ fontSize: 14, color: '#94A3B8' }}>Gyra · 业务场景 Loop</Text>
    <Text style={{ fontSize: 14, color: '#94A3B8' }}>10 / 12</Text>
  </Box>
</Slide>
