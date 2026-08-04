<Slide style={{ width: '1280px', height: '720px', background: '#0F172A', padding: '20px 64px', fontFamily: 'Noto Sans CJK SC, PingFang SC, Helvetica Neue, sans-serif' }}>
  {/* A 标题块 */}
  <Box style={{ height: 100, flexDirection: 'row', alignItems: 'center', gap: 16 }}>
    <Box style={{ width: 8, height: 48, background: 'linear-gradient(180deg, #3B82F6 0%, #22D3EE 100%)', borderRadius: 4 }} />
    <Box>
      <Text style={{ fontSize: 36, fontWeight: 'bold', color: '#F1F5F9' }}>数据稳定准确：数字只能来自"已确认"</Text>
      <Text style={{ fontSize: 16, color: '#94A3B8', marginTop: 6 }}>语义层统一口径 + 工具面硬门禁 + 人确认机制，让每个数字可追溯</Text>
    </Box>
  </Box>
  {/* B 内容区：非对称双栏 60:40 */}
  <Box style={{ height: 520, flexDirection: 'row', gap: 32 }}>
    {/* 左 60%：治理闭环流程 */}
    <Box style={{ width: '60%', background: '#1E293B', borderRadius: 16, border: '1px solid rgba(148,163,184,0.25)', padding: 28, flexDirection: 'column' }}>
      <Text style={{ fontSize: 20, fontWeight: 'bold', color: '#22D3EE' }}>治理闭环：数据可信的流水线</Text>
      <Box style={{ marginTop: 18, flexDirection: 'column', gap: 10, flex: 1 }}>
        <Box style={{ flexDirection: 'row', alignItems: 'center', gap: 14 }}>
          <Box style={{ width: 150, background: 'rgba(59,130,246,0.20)', borderRadius: 10, padding: '10px 14px', border: '1px solid rgba(59,130,246,0.5)' }}><Text style={{ fontSize: 16, fontWeight: 'bold', color: '#F1F5F9', textAlign: 'center' }}>资产登记</Text></Box>
          <Text style={{ fontSize: 15, color: '#94A3B8', flex: 1 }}>数据库、表、指标全部登记在册</Text>
        </Box>
        <Text style={{ fontSize: 16, color: '#3B82F6', marginLeft: 66 }}>↓</Text>
        <Box style={{ flexDirection: 'row', alignItems: 'center', gap: 14 }}>
          <Box style={{ width: 150, background: 'rgba(59,130,246,0.20)', borderRadius: 10, padding: '10px 14px', border: '1px solid rgba(59,130,246,0.5)' }}><Text style={{ fontSize: 16, fontWeight: 'bold', color: '#F1F5F9', textAlign: 'center' }}>spec 学习</Text></Box>
          <Text style={{ fontSize: 15, color: '#94A3B8', flex: 1 }}>AI 自动学习资产结构与含义</Text>
        </Box>
        <Text style={{ fontSize: 16, color: '#3B82F6', marginLeft: 66 }}>↓</Text>
        <Box style={{ flexDirection: 'row', alignItems: 'center', gap: 14 }}>
          <Box style={{ width: 150, background: 'rgba(34,211,238,0.18)', borderRadius: 10, padding: '10px 14px', border: '1px solid rgba(34,211,238,0.5)' }}><Text style={{ fontSize: 16, fontWeight: 'bold', color: '#F1F5F9', textAlign: 'center' }}>口径提案</Text></Box>
          <Text style={{ fontSize: 15, color: '#94A3B8', flex: 1 }}>指标怎么算，AI 给出声明式提案</Text>
        </Box>
        <Text style={{ fontSize: 16, color: '#3B82F6', marginLeft: 66 }}>↓</Text>
        <Box style={{ flexDirection: 'row', alignItems: 'center', gap: 14 }}>
          <Box style={{ width: 150, background: 'rgba(245,158,11,0.18)', borderRadius: 10, padding: '10px 14px', border: '1px solid rgba(245,158,11,0.5)' }}><Text style={{ fontSize: 16, fontWeight: 'bold', color: '#F59E0B', textAlign: 'center' }}>人确认</Text></Box>
          <Text style={{ fontSize: 15, color: '#94A3B8', flex: 1 }}>业务负责人点头，口径才生效</Text>
        </Box>
        <Text style={{ fontSize: 16, color: '#3B82F6', marginLeft: 66 }}>↓</Text>
        <Box style={{ flexDirection: 'row', alignItems: 'center', gap: 14 }}>
          <Box style={{ width: 150, background: 'linear-gradient(135deg, #3B82F6 0%, #22D3EE 100%)', borderRadius: 10, padding: '10px 14px' }}><Text style={{ fontSize: 16, fontWeight: 'bold', color: '#0F172A', textAlign: 'center' }}>语义目录</Text></Box>
          <Text style={{ fontSize: 15, color: '#F1F5F9', flex: 1 }}>verified：全公司唯一可信口径</Text>
        </Box>
      </Box>
      <Box style={{ marginTop: 'auto', background: 'rgba(245,158,11,0.08)', border: '1px dashed rgba(245,158,11,0.45)', borderRadius: 10, padding: '10px 16px', flexDirection: 'row', alignItems: 'center', gap: 10 }}>
        <FAIcon name="sync" style={{ fill: '#F59E0B', width: 18, height: 18 }} />
        <Text style={{ fontSize: 15, color: '#F1F5F9' }}><span style={{ color: '#F59E0B', fontWeight: 'bold' }}>漂移检测</span>：数据口径变了自动发现 → 生成新提案 → 人确认后更新</Text>
      </Box>
    </Box>
    {/* 右 40%：三个要点 */}
    <Box style={{ flex: 1, flexDirection: 'column', gap: 16 }}>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 16, padding: 22, border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'column' }}>
        <Box style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
          <FAIcon name="book" style={{ fill: '#3B82F6', width: 26, height: 26 }} />
          <Text style={{ fontSize: 20, fontWeight: 'bold', color: '#F1F5F9' }}>一套口径</Text>
        </Box>
        <Text style={{ fontSize: 15, color: '#94A3B8', lineHeight: 1.6, marginTop: 10 }}>实体、指标、关系在语义层统一声明。全公司看同一个"营收"，告别各说各话。</Text>
      </Box>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 16, padding: 22, border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'column' }}>
        <Box style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
          <FAIcon name="lock" style={{ fill: '#22D3EE', width: 26, height: 26 }} />
          <Text style={{ fontSize: 20, fontWeight: 'bold', color: '#F1F5F9' }}>硬门禁</Text>
        </Box>
        <Text style={{ fontSize: 15, color: '#94A3B8', lineHeight: 1.6, marginTop: 10 }}>数字只能来自已确认指标——从工具面直接限制，不靠 prompt"请自觉遵守"。</Text>
      </Box>
      <Box style={{ flex: 1, background: 'rgba(59,130,246,0.10)', borderRadius: 16, padding: 22, border: '1px solid rgba(148,163,184,0.25)', flexDirection: 'column' }}>
        <Box style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
          <FAIcon name="eye" style={{ fill: '#F59E0B', width: 26, height: 26 }} />
          <Text style={{ fontSize: 20, fontWeight: 'bold', color: '#F1F5F9' }}>持续保鲜</Text>
        </Box>
        <Text style={{ fontSize: 15, color: '#94A3B8', lineHeight: 1.6, marginTop: 10 }}>口径不是定义完就过时。漂移检测持续巡检，变化有人确认、有记录。</Text>
      </Box>
    </Box>
  </Box>
  {/* C 页脚条 */}
  <Box style={{ height: 60, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
    <Text style={{ fontSize: 14, color: '#94A3B8' }}>Gyra · 业务场景 Loop</Text>
    <Text style={{ fontSize: 14, color: '#94A3B8' }}>04 / 12</Text>
  </Box>
</Slide>
