<Slide style={{ width: '1280px', height: '720px', background: '#0F172A', padding: '20px 64px', fontFamily: 'Noto Sans CJK SC, PingFang SC, Helvetica Neue, sans-serif' }}>
  {/* A 标题块 */}
  <Box style={{ height: 100, flexDirection: 'row', alignItems: 'center', gap: 16 }}>
    <Box style={{ width: 8, height: 48, background: 'linear-gradient(180deg, #3B82F6 0%, #22D3EE 100%)', borderRadius: 4 }} />
    <Box>
      <Text style={{ fontSize: 36, fontWeight: 'bold', color: '#F1F5F9' }}>一图看懂：业务 Loop 六步飞轮</Text>
      <Text style={{ fontSize: 16, color: '#94A3B8', marginTop: 6 }}>事件驱动、持续运转，飞轮中心是北极星指标"沉淀厚度"</Text>
    </Box>
  </Box>
  {/* B 内容区：左大图 62% + 右侧六步 */}
  <Box style={{ height: 520, flexDirection: 'row', gap: 32, alignItems: 'center' }}>
    <Box style={{ width: '62%', flexDirection: 'column', gap: 16 }}>
      <Image src="resources/images/l3_loop.jpg" style={{ width: '100%', height: 356, objectFit: 'cover', borderRadius: 16, border: '1px solid rgba(148,163,184,0.25)' }} />
      <Box style={{ background: 'rgba(245,158,11,0.10)', border: '1px solid rgba(245,158,11,0.35)', borderRadius: 12, padding: '12px 20px', flexDirection: 'row', alignItems: 'center', gap: 12 }}>
        <FAIcon name="star" style={{ fill: '#F59E0B', width: 20, height: 20 }} />
        <Text style={{ fontSize: 16, color: '#F1F5F9' }}>飞轮不是转一圈就停——<span style={{ color: '#F59E0B', fontWeight: 'bold' }}>每转一圈，场景空间就厚一层</span></Text>
      </Box>
    </Box>
    <Box style={{ flex: 1, flexDirection: 'column', gap: 12 }}>
      <Box style={{ flexDirection: 'row', gap: 14, alignItems: 'center' }}>
        <Box style={{ width: 34, height: 34, borderRadius: 17, background: '#3B82F6', justifyContent: 'center', alignItems: 'center' }}><Text style={{ fontSize: 16, fontWeight: 'bold', color: '#F1F5F9' }}>1</Text></Box>
        <Box><Text style={{ fontSize: 19, fontWeight: 'bold', color: '#F1F5F9' }}>触发 · 持续监听</Text><Text style={{ fontSize: 14, color: '#94A3B8' }}>定时 / 告警 / Webhook / 手动，不等指令</Text></Box>
      </Box>
      <Box style={{ flexDirection: 'row', gap: 14, alignItems: 'center' }}>
        <Box style={{ width: 34, height: 34, borderRadius: 17, background: '#3B82F6', justifyContent: 'center', alignItems: 'center' }}><Text style={{ fontSize: 16, fontWeight: 'bold', color: '#F1F5F9' }}>2</Text></Box>
        <Box><Text style={{ fontSize: 19, fontWeight: 'bold', color: '#F1F5F9' }}>任务 · 自动创建</Text><Text style={{ fontSize: 14, color: '#94A3B8' }}>事件一到，任务即刻生成并启动</Text></Box>
      </Box>
      <Box style={{ flexDirection: 'row', gap: 14, alignItems: 'center' }}>
        <Box style={{ width: 34, height: 34, borderRadius: 17, background: '#22D3EE', justifyContent: 'center', alignItems: 'center' }}><Text style={{ fontSize: 16, fontWeight: 'bold', color: '#0F172A' }}>3</Text></Box>
        <Box><Text style={{ fontSize: 19, fontWeight: 'bold', color: '#F1F5F9' }}>剧本 · 声明执行</Text><Text style={{ fontSize: 14, color: '#94A3B8' }}>只定约束与产出，怎么做 Agent 自己定</Text></Box>
      </Box>
      <Box style={{ flexDirection: 'row', gap: 14, alignItems: 'center' }}>
        <Box style={{ width: 34, height: 34, borderRadius: 17, background: '#22D3EE', justifyContent: 'center', alignItems: 'center' }}><Text style={{ fontSize: 16, fontWeight: 'bold', color: '#0F172A' }}>4</Text></Box>
        <Box><Text style={{ fontSize: 19, fontWeight: 'bold', color: '#F1F5F9' }}>产出 · 真实交付物</Text><Text style={{ fontSize: 14, color: '#94A3B8' }}>报告、看板、操作计划，不是聊天消息</Text></Box>
      </Box>
      <Box style={{ flexDirection: 'row', gap: 14, alignItems: 'center' }}>
        <Box style={{ width: 34, height: 34, borderRadius: 17, background: '#F59E0B', justifyContent: 'center', alignItems: 'center' }}><Text style={{ fontSize: 16, fontWeight: 'bold', color: '#0F172A' }}>5</Text></Box>
        <Box><Text style={{ fontSize: 19, fontWeight: 'bold', color: '#F1F5F9' }}>交付 · 四种命运</Text><Text style={{ fontSize: 14, color: '#94A3B8' }}>通知 / 发布 / 执行 / 托管，各得其所</Text></Box>
      </Box>
      <Box style={{ flexDirection: 'row', gap: 14, alignItems: 'center' }}>
        <Box style={{ width: 34, height: 34, borderRadius: 17, background: '#F59E0B', justifyContent: 'center', alignItems: 'center' }}><Text style={{ fontSize: 16, fontWeight: 'bold', color: '#0F172A' }}>6</Text></Box>
        <Box><Text style={{ fontSize: 19, fontWeight: 'bold', color: '#F1F5F9' }}>沉淀 · 反哺下一轮</Text><Text style={{ fontSize: 14, color: '#94A3B8' }}>产出变资产，驱动飞轮继续加速</Text></Box>
      </Box>
    </Box>
  </Box>
  {/* C 页脚条 */}
  <Box style={{ height: 60, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
    <Text style={{ fontSize: 14, color: '#94A3B8' }}>Gyra · 业务场景 Loop</Text>
    <Text style={{ fontSize: 14, color: '#94A3B8' }}>03 / 12</Text>
  </Box>
</Slide>
