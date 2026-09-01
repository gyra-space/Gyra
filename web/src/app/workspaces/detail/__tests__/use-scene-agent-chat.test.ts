import { buildSceneAgentSendData, buildMediaImageInputs, type SceneAgentSendPayload } from '../scene-agent-send-data';
import { dedupOptimisticUser } from '../dedup-optimistic-user';
import type { WorkspaceExecutionStep } from '../agent-workspace-types';
import { parseSceneAgentWorkspaceString } from '../parse-scene-agent-workspace-string';
import { buildSkillLoadedExecutionSteps } from '../use-scene-agent-chat';

describe('buildSceneAgentSendData', () => {
  test('text + resources + model 构造多模态 user_input 与 chat_in_params', () => {
    const resources = [{ type: 'file_url', file_url: { url: 'u', file_name: 'f.txt' } }];
    const payload: SceneAgentSendPayload = { text: '你好', resources, model: 'gpt-4' };
    const data = buildSceneAgentSendData(payload, { workspaceId: 9, taskId: 3 }, 'c1');

    // user_input 多模态
    expect(data.user_input).toEqual({
      role: 'user',
      content: [...resources, { type: 'text', text: '你好' }],
    });
    // chat_in_params: resource + model
    expect(data.chat_in_params).toEqual([
      { param_type: 'resource', param_value: JSON.stringify(resources), sub_type: 'common_file' },
      { param_type: 'model', param_value: 'gpt-4' },
    ]);
    // model_name
    expect(data.model_name).toBe('gpt-4');
    // ext_info
    expect(data.ext_info).toMatchObject({ vis_render: 'scene_agent_workspace', workspace_id: 9, task_id: 3 });
  });

  test('playbookCommand 构造 playbook_command chat_in_params, user_input 为纯 topic 字符串', () => {
    const playbookCommand = { playbook_id: 7, playbook_name: '营收分析' };
    const payload: SceneAgentSendPayload = { text: '营收分析', playbookCommand };
    const data = buildSceneAgentSendData(payload, { workspaceId: 9 }, 'c1');

    // user_input 为纯字符串
    expect(data.user_input).toBe('营收分析');
    // chat_in_params 含 playbook_command
    expect(data.chat_in_params).toEqual([
      { param_type: 'playbook_command', sub_type: 'playbook', param_value: JSON.stringify(playbookCommand) },
    ]);
    // 无 model_name
    expect(data.model_name).toBeUndefined();
    // 显式命中剧本 -> ext_info 透传 playbook_id(后端回合前路由预建会话内任务)
    expect(data.ext_info).toMatchObject({ workspace_id: 9, playbook_id: 7 });
  });

  test('text-only: user_input 为纯字符串, 无 chat_in_params', () => {
    const payload: SceneAgentSendPayload = { text: '你好' };
    const data = buildSceneAgentSendData(payload, { workspaceId: 9 }, 'c1');

    expect(data.user_input).toBe('你好');
    expect(data.chat_in_params).toBeUndefined();
    expect(data.model_name).toBeUndefined();
    // ext_info 仍含 vis_render
    expect(data.ext_info).toMatchObject({ vis_render: 'scene_agent_workspace', workspace_id: 9 });
  });

  test('skills 构造 skill(gyra) chat_in_params, 每个技能一条', () => {
    const skills = [
      { skill_code: 'ppt-gen', name: 'PPT 生成' },
      { skill_code: 'data-analysis', name: '数据分析' },
    ];
    const payload: SceneAgentSendPayload = { text: '做份周报', skills };
    const data = buildSceneAgentSendData(payload, { workspaceId: 9 }, 'c1');

    expect(data.chat_in_params).toEqual([
      { param_type: 'resource', param_value: JSON.stringify(skills[0]), sub_type: 'skill(gyra)' },
      { param_type: 'resource', param_value: JSON.stringify(skills[1]), sub_type: 'skill(gyra)' },
    ]);
  });

  test('mcps 构造 mcp(gyra) chat_in_params, mcp_code 取 id/uuid/name', () => {
    const mcps = [
      { id: 'mcp-001', name: 'GitHub 连接器' },
      { uuid: 'uuid-abc', name: 'MySQL' },
      { name: 'Notion' },
    ];
    const payload: SceneAgentSendPayload = { text: '查一下', mcps };
    const data = buildSceneAgentSendData(payload, { workspaceId: 9 }, 'c1');

    expect(data.chat_in_params).toEqual([
      { param_type: 'resource', param_value: JSON.stringify({ mcp_code: 'mcp-001', name: 'GitHub 连接器' }), sub_type: 'mcp(gyra)' },
      { param_type: 'resource', param_value: JSON.stringify({ mcp_code: 'uuid-abc', name: 'MySQL' }), sub_type: 'mcp(gyra)' },
      { param_type: 'resource', param_value: JSON.stringify({ mcp_code: 'Notion', name: 'Notion' }), sub_type: 'mcp(gyra)' },
    ]);
  });

  test('permission 写入 ext_info.permission_mode; 未传时不含该字段', () => {
    const withPerm = buildSceneAgentSendData({ text: '你好', permission: 'auto' }, { workspaceId: 9 }, 'c1');
    expect(withPerm.ext_info).toMatchObject({ permission_mode: 'auto' });

    const withoutPerm = buildSceneAgentSendData({ text: '你好' }, { workspaceId: 9 }, 'c1');
    expect(withoutPerm.ext_info).not.toHaveProperty('permission_mode');
  });

  test('focusArtifactId 写入 ext_info.focus_artifact_id', () => {
    const payload: SceneAgentSendPayload = { text: '你好' };
    const data = buildSceneAgentSendData(payload, { workspaceId: 9, focusArtifactId: 42 }, 'c1');
    expect(data.ext_info).toMatchObject({ focus_artifact_id: 42 });
  });

  test('未传 focusArtifactId 时 ext_info 不含 focus_artifact_id', () => {
    const payload: SceneAgentSendPayload = { text: '你好' };
    const data = buildSceneAgentSendData(payload, { workspaceId: 9 }, 'c1');
    expect(data.ext_info).not.toHaveProperty('focus_artifact_id');
  });
});

describe('buildMediaImageInputs', () => {
  test('按角色映射为首帧/尾帧/参考图,并返回标注明细', () => {
    const resources = [
      { type: 'image_url', image_url: { url: 'https://a/first.png', file_name: 'f.png' }, image_role: 'first_frame' as const },
      { type: 'image_url', image_url: { url: 'https://a/last.png', file_name: 'l.png' }, image_role: 'last_frame' as const },
      { type: 'image_url', image_url: { url: 'https://a/ref1.png', file_name: 'r1.png' }, image_role: 'reference' as const },
      { type: 'image_url', image_url: { url: 'https://a/ref2.png', file_name: 'r2.png' }, image_role: 'reference' as const },
      { type: 'image_url', image_url: { url: 'https://a/auto.png', file_name: 'a.png' } },
    ];
    const out = buildMediaImageInputs(resources as any);
    expect(out.image_url).toBe('https://a/first.png');
    expect(out.image_url_last).toBe('https://a/last.png');
    expect(out.reference_images).toEqual(['https://a/ref1.png', 'https://a/ref2.png']);
    // auto(未标注)不参与;明细含全部已标注图片
    expect(out.image_refs).toHaveLength(4);
    expect(out.image_refs?.map((r) => r.role)).toEqual(['first_frame', 'last_frame', 'reference', 'reference']);
  });

  test('无图片或全为未标注(auto) → 空对象', () => {
    expect(buildMediaImageInputs([])).toEqual({});
    expect(buildMediaImageInputs([{ type: 'file_url', file_url: { url: 'u', file_name: 'f.txt' } }] as any)).toEqual({});
    expect(buildMediaImageInputs([{ type: 'image_url', image_url: { url: 'u', file_name: 'f.png' } }] as any)).toEqual({});
  });

  test('本地服务相对路径预览地址解析为绝对 URL', () => {
    const out = buildMediaImageInputs([
      { type: 'image_url', image_url: { url: '/api/v2/serve/file/files/x', file_name: 'x.png' }, image_role: 'first_frame' as const },
    ] as any);
    // 无 NEXT_PUBLIC_API_BASE_URL 时,保持相对路径;有环境变量时补全为绝对
    expect(out.image_url).toBe(`${process.env.NEXT_PUBLIC_API_BASE_URL || ''}/api/v2/serve/file/files/x`);
  });
});

describe('buildSceneAgentSendData 图片角色标注', () => {
  test('标注角色合并进单条 media chat_in_param,覆盖用户面板同类字段', () => {
    const resources = [
      { type: 'image_url', image_url: { url: 'https://a/day.png', file_name: 'day.png' }, image_role: 'first_frame' as const },
      { type: 'image_url', image_url: { url: 'https://a/night.png', file_name: 'night.png' }, image_role: 'last_frame' as const },
    ];
    const payload: SceneAgentSendPayload = { text: '从白天到夜晚', resources, media: { kind: 'video', duration: 5 } };
    const data = buildSceneAgentSendData(payload, { workspaceId: 9 }, 'c1');

    const mediaParam = (data.chat_in_params || []).find((p) => p.param_type === 'media');
    expect(mediaParam).toBeDefined();
    // 只输出一条 media,且合并后含确定性透传字段
    expect((data.chat_in_params || []).filter((p) => p.param_type === 'media')).toHaveLength(1);
    const val = JSON.parse(mediaParam!.param_value);
    expect(val.kind).toBe('video');
    expect(val.duration).toBe(5);
    expect(val.image_url).toBe('https://a/day.png');
    expect(val.image_url_last).toBe('https://a/night.png');
    expect(val.image_refs).toHaveLength(2);
  });

  test('仅标注角色、无面板设置时,默认 kind=video 并透传', () => {
    const resources = [
      { type: 'image_url', image_url: { url: 'https://a/ref.png', file_name: 'ref.png' }, image_role: 'reference' as const },
    ];
    const payload: SceneAgentSendPayload = { text: '参考这个图生成视频', resources };
    const data = buildSceneAgentSendData(payload, { workspaceId: 9 }, 'c1');

    const mediaParam = (data.chat_in_params || []).find((p) => p.param_type === 'media');
    expect(mediaParam).toBeDefined();
    const val = JSON.parse(mediaParam!.param_value);
    expect(val.kind).toBe('video');
    expect(val.reference_images).toEqual(['https://a/ref.png']);
  });

  test('无图片角色标注时不产生额外的 media 参数', () => {
    const resources = [{ type: 'file_url', file_url: { url: 'u', file_name: 'f.txt' } }];
    const payload: SceneAgentSendPayload = { text: '你好', resources, model: 'gpt-4' };
    const data = buildSceneAgentSendData(payload, { workspaceId: 9 }, 'c1');
    expect((data.chat_in_params || []).filter((p) => p.param_type === 'media')).toHaveLength(0);
  });
});

describe('parseSceneAgentWorkspaceString', () => {
  test('fenced scene_agent_workspace string → parsed object', () => {
    const body = '{"render_name":"scene_agent_workspace","planning":null,"execution":[],"summary":null}';
    const fenced = '```scene_agent_workspace\n' + body + '\n```';
    const parsed = parseSceneAgentWorkspaceString(fenced);
    expect(parsed).toEqual({
      render_name: 'scene_agent_workspace',
      planning: null,
      execution: [],
      summary: null,
    });
  });

  test('bare JSON string (no fence) → parsed object (fallback)', () => {
    const s = '{"render_name":"scene_agent_workspace","execution":[]}';
    const parsed = parseSceneAgentWorkspaceString(s);
    expect(parsed).toEqual({ render_name: 'scene_agent_workspace', execution: [] });
  });

  test('normal markdown string → null', () => {
    expect(parseSceneAgentWorkspaceString('**hello**')).toBeNull();
  });

  test('fenced string with malformed JSON body → null (no throw)', () => {
    const fenced = '```scene_agent_workspace\n{not valid json\n```';
    expect(() => parseSceneAgentWorkspaceString(fenced)).not.toThrow();
    expect(parseSceneAgentWorkspaceString(fenced)).toBeNull();
  });

  test('non-string or empty → null', () => {
    expect(parseSceneAgentWorkspaceString(null as unknown as string)).toBeNull();
    expect(parseSceneAgentWorkspaceString(undefined as unknown as string)).toBeNull();
    expect(parseSceneAgentWorkspaceString(123 as unknown as string)).toBeNull();
    expect(parseSceneAgentWorkspaceString('')).toBeNull();
    expect(parseSceneAgentWorkspaceString('   ')).toBeNull();
  });

  test('execution payload is preserved through fence parse', () => {
    const obj = {
      render_name: 'scene_agent_workspace',
      planning: { goal: 'x' },
      execution: [{ id: 's1', title: 't', type: 'tool_call', status: 'done' }],
      summary: 'done',
    };
    const fenced = '```scene_agent_workspace\n' + JSON.stringify(obj) + '\n```';
    const parsed = parseSceneAgentWorkspaceString(fenced);
    expect(parsed).toEqual(obj);
  });

  test('fence embedded in surrounding markdown → still parsed (regex is not anchored)', () => {
    const body = '{"render_name":"scene_agent_workspace","execution":[]}';
    const md = 'some prefix\n```scene_agent_workspace\n' + body + '\n```\ntail';
    expect(parseSceneAgentWorkspaceString(md)).toEqual({
      render_name: 'scene_agent_workspace',
      execution: [],
    });
  });

  test('bare JSON that is not an object (e.g. array or number string) → null for non-object', () => {
    expect(parseSceneAgentWorkspaceString('[1,2,3]')).toBeNull();
    expect(parseSceneAgentWorkspaceString('"a string"')).toBeNull();
  });
});


describe('dedupOptimisticUser', () => {
  test('后端回显同文本 user 步骤后移除乐观步骤', () => {
    const exec: WorkspaceExecutionStep[] = [
      { id: 'user-optimistic-1', type: 'user', title: '我', status: 'done', output: '你好' },
      { id: 'user-msg-1', type: 'user', title: '我', status: 'done', output: '你好' },
    ];
    expect(dedupOptimisticUser(exec).map(e => e.id)).toEqual(['user-msg-1']);
  });

  test('服务端 output 截断时用前缀匹配去重(乐观文本以后端回显开头)', () => {
    const exec: WorkspaceExecutionStep[] = [
      { id: 'user-optimistic-1', type: 'user', title: '我', status: 'done', output: '这是一段很长的提问内容' },
      { id: 'user-msg-1', type: 'user', title: '我', status: 'done', output: '这是一段' },
    ];
    expect(dedupOptimisticUser(exec).map(e => e.id)).toEqual(['user-msg-1']);
  });

  test('无后端回显时保留乐观步骤', () => {
    const exec: WorkspaceExecutionStep[] = [
      { id: 'user-optimistic-1', type: 'user', title: '我', status: 'done', output: '你好' },
    ];
    expect(dedupOptimisticUser(exec).map(e => e.id)).toEqual(['user-optimistic-1']);
  });

  test('不同文本的乐观步骤不去重', () => {
    const exec: WorkspaceExecutionStep[] = [
      { id: 'user-optimistic-1', type: 'user', title: '我', status: 'done', output: '问题A' },
      { id: 'user-msg-1', type: 'user', title: '我', status: 'done', output: '问题B' },
    ];
    expect(dedupOptimisticUser(exec).map(e => e.id).sort()).toEqual(['user-msg-1', 'user-optimistic-1']);
  });

  test('历史轮次用户消息(时间戳早于乐观步骤且为其前缀)不得误删当前乐观气泡', () => {
    // 追问「帮我看看这周的数据情况」,后端尚未回显;历史「帮我看看这周」只是前缀,
    // 不应据此提前删除乐观气泡(否则用户消息要等 AI 输出才显示)
    const exec: WorkspaceExecutionStep[] = [
      { id: 'user-msg-1', type: 'user', title: '我', status: 'done', output: '帮我看看这周', ts: '2026-08-22T09:00:00' },
      { id: 'user-optimistic-2', type: 'user', title: '我', status: 'done', output: '帮我看看这周的数据情况', ts: '2026-08-22T09:05:00' },
    ];
    expect(dedupOptimisticUser(exec).map(e => e.id)).toEqual(['user-msg-1', 'user-optimistic-2']);
  });

  test('当前追问已被后端回显(时间戳不早于乐观步骤)时,才移除乐观气泡', () => {
    const exec: WorkspaceExecutionStep[] = [
      { id: 'user-msg-1', type: 'user', title: '我', status: 'done', output: '帮我看看这周', ts: '2026-08-22T09:00:00' },
      { id: 'user-optimistic-2', type: 'user', title: '我', status: 'done', output: '帮我看看这周的数据情况', ts: '2026-08-22T09:05:00' },
      { id: 'user-msg-2', type: 'user', title: '我', status: 'done', output: '帮我看看这周的数据情况', ts: '2026-08-22T09:05:10' },
    ];
    expect(dedupOptimisticUser(exec).map(e => e.id)).toEqual(['user-msg-1', 'user-msg-2']);
  });
});


describe('buildSkillLoadedExecutionSteps', () => {
  const xml = (name: string) =>
    `<skill_content name="${name}">\n# 指令\n正文内容\n</skill_content>`;

  test('XML 列表转 skill_loaded 步骤:name 从 XML 属性解析,透传完整 XML', () => {
    const steps = buildSkillLoadedExecutionSteps([xml('data-analysis'), xml('docx')]);
    expect(steps).toHaveLength(2);
    expect(steps[0]).toMatchObject({
      type: 'skill_loaded',
      title: 'data-analysis',
      status: 'done',
      action: 'preload',
    });
    expect(steps[0].skill_xml).toContain('data-analysis');
    expect(steps[0].id).toBe('skill-loaded-data-analysis');
  });

  test('同名技能去重(与已有标题比较)', () => {
    const steps = buildSkillLoadedExecutionSteps(
      [xml('data-analysis'), xml('data-analysis')],
      ['data-analysis'],
    );
    expect(steps).toHaveLength(0);
  });

  test('非法输入跳过(空串/非字符串)', () => {
    const steps = buildSkillLoadedExecutionSteps(['', 'x' as unknown as string]);
    expect(steps).toHaveLength(1); // 仅 'x' 无 name 属性 -> 默认名 Skill
    expect(steps[0].title).toBe('Skill');
  });
});
