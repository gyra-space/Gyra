<Slide style={{ width: '1280px', height: '720px', background: '#0F172A', padding: '20px 64px', fontFamily: 'Noto Sans CJK SC, PingFang SC, Helvetica Neue, sans-serif' }}>
  {/* A 标题块 */}
  <Box style={{ height: 100, flexDirection: 'row', alignItems: 'center', gap: 16 }}>
    <Box style={{ width: 8, height: 48, background: 'linear-gradient(180deg, #3B82F6 0%, #22D3EE 100%)', borderRadius: 4 }} />
    <Box>
      <Text style={{ fontSize: 36, fontWeight: 'bold', color: '#F1F5F9' }}>三个闭环咬合：数据飞轮如何自转</Text>
      <Text style={{ fontSize: 16, color: '#94A3B8', marginTop: 6 }}>工作、治理、记忆三个闭环互相喂养，形成自驱动的飞轮系统</Text>
    </Box>
  </Box>
  {/* B 内容区：左咬合图 + 右解释 */}
  <Box style={{ height: 520, flexDirection: 'row', gap: 32 }}>
    {/* 左：三闭环咬合图 */}
    <Box style={{ width: '58%', background: '#1E293B', borderRadius: 16, border: '1px solid rgba(148,163,184,0.25)', padding: 28, flexDirection: 'column', justifyContent: 'space-between' }}>
      {/* 工作闭环（上） */}
      <Box style={{ alignItems: 'center', flexDirection: 'column', gap: 10 }}>
        <Box style={{ width: '72%', background: 'linear-gradient(135deg, #3B82F6 0%, #22D3EE 100%)', borderRadius: 14, padding: '16px 24px', alignItems: 'center', flexDirection: 'column', gap: 4 }}>
          <Text style={{ fontSize: 20, fontWeight: 'bold', color: '#0F172A' }}>工作闭环</Text>
          <Text style={{ fontSize: 13.5, color: '#0F172A' }}>触发 → 执行 → 产出 → 交付 → 沉淀</Text>
        </Box>
      </Box>
      {/* 中部咬合箭头 */}
      <Box style={{ flexDirection: 'row', justifyContent: 'space-between', paddingLeft: 40, paddingRight: 40, alignItems: 'center' }}>
        <Box style={{ flexDirection: 'column', alignItems: 'center', gap: 2 }}>
          <FAIcon name="arrow-down" style={{ fill: '#F59E0B', width: 20, height: 20 }} />
          <Text style={{ fontSize: 12.5, color: '#F59E0B' }}>产出喂养</Text>
        </Box>
        <Box style={{ flexDirection: 'column', alignItems: 'center', gap: 2 }}>
          <FAIcon name="arrow-up" style={{ fill: '#22D3EE', width: 20, height: 20 }} />
          <Text style={{ fontSize: 12.5, color: '#22D3EE' }}>经验反哺</Text>
        </Box>
      </Box>
      {/* 治理 + 记忆（下） */}
      <Box style={{ flexDirection: 'row', gap: 16 }}>
        <Box style={{ flex: 1, background: 'rgba(245,158,11,0.14)', borderRadius: 14, padding: '16px 20px', border: '1px solid rgba(245,158,11,0.5)', flexDirection: 'column', gap: 4, alignItems: 'center' }}>
          <Text style={{ fontSize: 19, fontWeight: 'bold', color: '#F59E0B' }}>治理闭环</Text>
          <Text style={{ fontSize: 13, color: '#94A3B8', textAlign: 'center', lineHeight: 1.5 }}>资产登记 → spec 学习<br />→ 人确认 → 可信目录</Text>
        </Box>
        <Box style={{ flex: 1, background: 'rgba(34,211,238,0.12)', borderRadius: 14, padding: '16px 20px', border: '1px solid rgba(34,211,238,0.5)', flexDirection: 'column', gap: 4, alignItems: 'center' }}>
          <Text style={{ fontSize: 19, fontWeight: 'bold', color: '#22D3EE' }}>记忆闭环</Text>
          <Text style={{ fontSize: 13, color: '#94A3B8', textAlign: 'center', lineHeight: 1.5 }}>每轮记录 → 反思整合<br />→ 晋升 → 下次加速</Text>
        </Box>
      </Box>
      <Box style={{ flexDirection: 'row', justifyContent: 'center', alignItems: 'center', gap: 8 }}>
        <FAIcon name="shield" style={{ fill: '#F59E0B', width: 16, height: 16 }} />
        <Text style={{ fontSize: 13.5, color: '#94A3B8' }}>治理闭环横贯其中：保证另外两个闭环里的<span style={{ color: '#F1F5F9' }}>每一份数据都可信</span></Text>
      </Box>
    </Box>
    {/* 右：三条解释 */}
    <Box style={{ flex: 1, flexDirection: 'column', gap: 14 }}>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 14, padding: '16px 22px', border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'column', justifyContent: 'center' }}>
        <Text style={{ fontSize: 19, fontWeight: 'bold', color: '#F1F5F9' }}>工作闭环 · 让场景持续运转</Text>
        <Text style={{ fontSize: 14.5, color: '#94A3B8', lineHeight: 1.6, marginTop: 8 }}>触发器不停、任务不断、产出不息——这是飞轮的主驱动，场景 7×24 在场。</Text>
      </Box>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 14, padding: '16px 22px', border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'column', justifyContent: 'center' }}>
        <Text style={{ fontSize: 19, fontWeight: 'bold', color: '#F1F5F9' }}>治理闭环 · 让数据可信</Text>
        <Text style={{ fontSize: 14.5, color: '#94A3B8', lineHeight: 1.6, marginTop: 8 }}>数字只能来自已确认口径，治理落在工具面硬门禁——这是飞轮的可信底座。</Text>
      </Box>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 14, padding: '16px 22px', border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'column', justifyContent: 'center' }}>
        <Text style={{ fontSize: 19, fontWeight: 'bold', color: '#F1F5F9' }}>记忆闭环 · 让 Agent 成长</Text>
        <Text style={{ fontSize: 14.5, color: '#94A3B8', lineHeight: 1.6, marginTop: 8 }}>工作闭环的产出喂养记忆，记忆晋升反哺执行——这是飞轮的进化引擎。</Text>
      </Box>
      <Box style={{ background: 'linear-gradient(135deg, rgba(59,130,246,0.25) 0%, rgba(34,211,238,0.20) 100%)', borderRadius: 14, padding: '14px 22px', border: '1px solid rgba(59,130,246,0.5)' }}>
        <Text style={{ fontSize: 15.5, color: '#F1F5F9', lineHeight: 1.6 }}>三环咬合的结果：<span style={{ fontWeight: 'bold', color: '#22D3EE' }}>业务数据越跑，飞轮转得越快</span></Text>
      </Box>
    </Box>
  </Box>
  {/* C 页脚条 */}
  <Box style={{ height: 60, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
    <Text style={{ fontSize: 14, color: '#94A3B8' }}>Gyra · 业务场景 Loop</Text>
    <Text style={{ fontSize: 14, color: '#94A3B8' }}>09 / 12</Text>
  </Box>
</Slide>
