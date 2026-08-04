<Slide style={{ width: '1280px', height: '720px', background: '#0F172A', padding: '20px 64px', fontFamily: 'Noto Sans CJK SC, PingFang SC, Helvetica Neue, sans-serif' }}>
  {/* A 标题块 */}
  <Box style={{ height: 100, flexDirection: 'row', alignItems: 'center', gap: 16 }}>
    <Box style={{ width: 8, height: 48, background: 'linear-gradient(180deg, #3B82F6 0%, #22D3EE 100%)', borderRadius: 4 }} />
    <Box>
      <Text style={{ fontSize: 36, fontWeight: 'bold', color: '#F1F5F9' }}>数据循环：场景不停，任务不断</Text>
      <Text style={{ fontSize: 16, color: '#94A3B8', marginTop: 6 }}>事件驱动触发 → 声明式剧本执行 → 四类真实交付，产出物各得其所</Text>
    </Box>
  </Box>
  {/* B 内容区：上部链路 55% + 下方四交付卡 */}
  <Box style={{ height: 520, flexDirection: 'column', gap: 20 }}>
    {/* 上部横向链路 */}
    <Box style={{ height: 268, background: '#1E293B', borderRadius: 16, border: '1px solid rgba(148,163,184,0.25)', padding: 24, flexDirection: 'row', alignItems: 'center', gap: 14 }}>
      {/* 触发源 */}
      <Box style={{ width: 240, flexDirection: 'column', gap: 8 }}>
        <Text style={{ fontSize: 17, fontWeight: 'bold', color: '#22D3EE', marginBottom: 4 }}>① 四种触发源</Text>
        <Box style={{ flexDirection: 'row', gap: 8, flexWrap: 'wrap' }}>
          <Box style={{ background: 'rgba(59,130,246,0.20)', borderRadius: 8, padding: '7px 12px', border: '1px solid rgba(59,130,246,0.5)', flexDirection: 'row', gap: 6, alignItems: 'center' }}><FAIcon name="clock" style={{ fill: '#3B82F6', width: 14, height: 14 }} /><Text style={{ fontSize: 14, color: '#F1F5F9' }}>定时</Text></Box>
          <Box style={{ background: 'rgba(59,130,246,0.20)', borderRadius: 8, padding: '7px 12px', border: '1px solid rgba(59,130,246,0.5)', flexDirection: 'row', gap: 6, alignItems: 'center' }}><FAIcon name="share" style={{ fill: '#3B82F6', width: 14, height: 14 }} /><Text style={{ fontSize: 14, color: '#F1F5F9' }}>Webhook</Text></Box>
          <Box style={{ background: 'rgba(59,130,246,0.20)', borderRadius: 8, padding: '7px 12px', border: '1px solid rgba(59,130,246,0.5)', flexDirection: 'row', gap: 6, alignItems: 'center' }}><FAIcon name="bell" style={{ fill: '#3B82F6', width: 14, height: 14 }} /><Text style={{ fontSize: 14, color: '#F1F5F9' }}>告警</Text></Box>
          <Box style={{ background: 'rgba(59,130,246,0.20)', borderRadius: 8, padding: '7px 12px', border: '1px solid rgba(59,130,246,0.5)', flexDirection: 'row', gap: 6, alignItems: 'center' }}><FAIcon name="hand-pointer" style={{ fill: '#3B82F6', width: 14, height: 14 }} /><Text style={{ fontSize: 14, color: '#F1F5F9' }}>手动</Text></Box>
        </Box>
        <Text style={{ fontSize: 13, color: '#94A3B8', lineHeight: 1.5, marginTop: 6 }}>Agent 持续监听场景事件，不是等人发指令</Text>
      </Box>
      <FAIcon name="arrow-right" style={{ fill: '#3B82F6', width: 26, height: 26 }} />
      {/* 任务 */}
      <Box style={{ width: 150, background: 'rgba(59,130,246,0.15)', borderRadius: 12, padding: 16, border: '1px solid rgba(59,130,246,0.5)', alignItems: 'center', gap: 8 }}>
        <FAIcon name="file-text" style={{ fill: '#3B82F6', width: 30, height: 30 }} />
        <Text style={{ fontSize: 17, fontWeight: 'bold', color: '#F1F5F9', textAlign: 'center' }}>② 任务创建</Text>
        <Text style={{ fontSize: 13, color: '#94A3B8', textAlign: 'center' }}>自动启动<br />不阻塞</Text>
      </Box>
      <FAIcon name="arrow-right" style={{ fill: '#3B82F6', width: 26, height: 26 }} />
      {/* 剧本 */}
      <Box style={{ flex: 1, background: 'rgba(34,211,238,0.10)', borderRadius: 12, padding: 16, border: '1px solid rgba(34,211,238,0.45)', flexDirection: 'column', gap: 6 }}>
        <Box style={{ flexDirection: 'row', gap: 8, alignItems: 'center' }}>
          <FAIcon name="clipboard" style={{ fill: '#22D3EE', width: 22, height: 22 }} />
          <Text style={{ fontSize: 17, fontWeight: 'bold', color: '#F1F5F9' }}>③ 剧本执行（声明式）</Text>
        </Box>
        <Text style={{ fontSize: 13.5, color: '#94A3B8', lineHeight: 1.55 }}>剧本只声明三件事：<span style={{ color: '#22D3EE' }}>能用什么资源</span>、<span style={{ color: '#22D3EE' }}>必须产出什么</span>、<span style={{ color: '#22D3EE' }}>什么情况必须人介入</span>。具体怎么做，交给 Agent 自主规划——模型越强，执行越好。</Text>
      </Box>
      <FAIcon name="arrow-right" style={{ fill: '#3B82F6', width: 26, height: 26 }} />
      {/* 交付 */}
      <Box style={{ width: 150, background: 'linear-gradient(135deg, #3B82F6 0%, #22D3EE 100%)', borderRadius: 12, padding: 16, alignItems: 'center', gap: 8 }}>
        <FAIcon name="check-circle" style={{ fill: '#0F172A', width: 30, height: 30 }} />
        <Text style={{ fontSize: 17, fontWeight: 'bold', color: '#0F172A', textAlign: 'center' }}>④ 产出交付</Text>
        <Text style={{ fontSize: 13, color: '#0F172A', textAlign: 'center' }}>真实交付物<br />而非聊天消息</Text>
      </Box>
    </Box>
    {/* 下方四类交付卡 */}
    <Box style={{ flex: 1, flexDirection: 'row', gap: 16 }}>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 14, padding: 20, border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'column' }}>
        <Box style={{ flexDirection: 'row', gap: 10, alignItems: 'center' }}><FAIcon name="envelope" style={{ fill: '#3B82F6', width: 24, height: 24 }} /><Text style={{ fontSize: 19, fontWeight: 'bold', color: '#F1F5F9' }}>Notify 通知</Text></Box>
        <Text style={{ fontSize: 14, color: '#94A3B8', lineHeight: 1.6, marginTop: 10 }}>报告邮件、群消息卡片，产出主动推到该看的人面前</Text>
        <Text style={{ fontSize: 13, color: '#22D3EE', marginTop: 'auto', paddingTop: 10 }}>例：月报邮件 / 告警播报</Text>
      </Box>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 14, padding: 20, border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'column' }}>
        <Box style={{ flexDirection: 'row', gap: 10, alignItems: 'center' }}><FAIcon name="upload" style={{ fill: '#22D3EE', width: 24, height: 24 }} /><Text style={{ fontSize: 19, fontWeight: 'bold', color: '#F1F5F9' }}>Publish 发布</Text></Box>
        <Text style={{ fontSize: 14, color: '#94A3B8', lineHeight: 1.6, marginTop: 10 }}>产出写入外部系统，成为正式记录而非一次性文件</Text>
        <Text style={{ fontSize: 13, color: '#22D3EE', marginTop: 'auto', paddingTop: 10 }}>例：报表入 BI / 代码入库</Text>
      </Box>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 14, padding: 20, border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'column' }}>
        <Box style={{ flexDirection: 'row', gap: 10, alignItems: 'center' }}><FAIcon name="cog" style={{ fill: '#F59E0B', width: 24, height: 24 }} /><Text style={{ fontSize: 19, fontWeight: 'bold', color: '#F1F5F9' }}>Execute 执行</Text></Box>
        <Text style={{ fontSize: 14, color: '#94A3B8', lineHeight: 1.6, marginTop: 10 }}>操作计划在真实世界落地，执行前必经人审批</Text>
        <Text style={{ fontSize: 13, color: '#22D3EE', marginTop: 'auto', paddingTop: 10 }}>例：重启服务 / 回滚版本</Text>
      </Box>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 14, padding: 20, border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'column' }}>
        <Box style={{ flexDirection: 'row', gap: 10, alignItems: 'center' }}><FAIcon name="home" style={{ fill: '#F59E0B', width: 24, height: 24 }} /><Text style={{ fontSize: 19, fontWeight: 'bold', color: '#F1F5F9' }}>Host 托管</Text></Box>
        <Text style={{ fontSize: 14, color: '#94A3B8', lineHeight: 1.6, marginTop: 10 }}>看板、站点在空间内长期托管运行，持续可查可用</Text>
        <Text style={{ fontSize: 13, color: '#22D3EE', marginTop: 'auto', paddingTop: 10 }}>例：运营看板 / 历史档案站</Text>
      </Box>
    </Box>
  </Box>
  {/* C 页脚条 */}
  <Box style={{ height: 60, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
    <Text style={{ fontSize: 14, color: '#94A3B8' }}>Gyra · 业务场景 Loop</Text>
    <Text style={{ fontSize: 14, color: '#94A3B8' }}>05 / 12</Text>
  </Box>
</Slide>
