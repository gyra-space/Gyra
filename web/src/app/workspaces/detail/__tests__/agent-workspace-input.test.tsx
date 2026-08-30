/** @jest-environment jsdom */
import { render, fireEvent, screen, waitFor, cleanup } from '@testing-library/react';
import { AgentWorkspaceInput } from '../agent-workspace-input';
import { getPendingResources, setPendingResources } from '../scene-agent-send-data';

jest.mock('@/client/api', () => ({
  apiInterceptors: jest.fn(() => Promise.resolve([null, []])),
  getModelList: jest.fn(),
  getSkillList: jest.fn(),
  getMCPList: jest.fn(),
  postChatModeParamsFileLoad: jest.fn(),
  listResources: jest.fn(),
  listArtifacts: jest.fn(),
  listAssets: jest.fn(),
}));
jest.mock('ahooks', () => ({
  // 依据调用的异步函数体粗略分流:各数据源各返回一条样本,其余返回空
  useRequest: (fn: any) => {
    const src = String(fn);
    if (src.includes('getSkillList')) {
      return { loading: false, data: [{ skill_code: 'code-review', name: '代码审查', description: '审查代码质量' }] };
    }
    if (src.includes("type: 'command'")) {
      return {
        loading: false,
        data: [{ id: 9, type: 'command', name: '开启深度思考', physical_ref: 'deep-think', is_active: true, config: { kind: 'toggle', description: '更深度的推理', payload: { deep_think: true } } }],
      };
    }
    if (src.includes('listResources')) {
      return { loading: false, data: [{ resource_id: 1, name: '数据分析专家', physical_ref: 'app-analyst', description: '擅长报表分析' }] };
    }
    if (src.includes('listArtifacts')) {
      return { loading: false, data: [{ artifact_id: 11, title: '月度报告.html', content_ref: '/files/11.html' }] };
    }
    if (src.includes('listAssets')) {
      return { loading: false, data: [{ asset_id: 21, name: '客户分群规则', description: '已确认口径', maturity: 'confirmed' }] };
    }
    return { loading: false };
  },
}));

describe('AgentWorkspaceInput', () => {
  test('输入 / 且有 playbooks 时显示剧本列表', () => {
    const onSend = jest.fn();
    render(
      <AgentWorkspaceInput
        conversationId="c1"
        onSend={onSend}
        playbooks={[{ playbook_id: 1, playbook_name: '营收分析' }]}
      />,
    );
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '/' } });
    expect(screen.getByText('营收分析')).toBeInTheDocument();
  });

  test('输入 / 唤起统一命令菜单,按类型分组展示剧本项与键盘提示', () => {
    const onSend = jest.fn();
    render(
      <AgentWorkspaceInput
        conversationId="c1"
        onSend={onSend}
        playbooks={[{ playbook_id: 1, playbook_name: '营收分析' }]}
      />,
    );
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '/' } });
    // 菜单打开:分组标题(文件/剧本/命令) + 剧本项 + 键盘提示
    expect(screen.getByText('剧本')).toBeInTheDocument();
    expect(screen.getByText('营收分析')).toBeInTheDocument();
    expect(screen.getByText('↑↓ 选择')).toBeInTheDocument();
    expect(screen.getByText('Enter 确认')).toBeInTheDocument();
  });

  test('/ 后输入关键词实时过滤菜单项', () => {
    const onSend = jest.fn();
    render(
      <AgentWorkspaceInput
        conversationId="c1"
        onSend={onSend}
        playbooks={[
          { playbook_id: 1, playbook_name: '营收分析' },
          { playbook_id: 2, playbook_name: '日志巡检' },
        ]}
      />,
    );
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '/营收' } });
    expect(screen.getByText('营收分析')).toBeInTheDocument();
    expect(screen.queryByText('日志巡检')).not.toBeInTheDocument();
  });

  test('/ 菜单键盘导航:Enter 选中高亮剧本', () => {
    const onSend = jest.fn();
    render(
      <AgentWorkspaceInput
        conversationId="c1"
        onSend={onSend}
        playbooks={[{ playbook_id: 1, playbook_name: '营收分析' }]}
      />,
    );
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '/' } });
    // ArrowDown 高亮第一项,Enter 选中(消费事件,不触发发送)
    fireEvent.keyDown(textarea, { key: 'ArrowDown' });
    fireEvent.keyDown(textarea, { key: 'Enter' });
    expect(screen.getByTitle('移除剧本')).toBeInTheDocument();
    expect(onSend).not.toHaveBeenCalled();
  });

  test('/ 菜单选中后生成剧本 chip', () => {
    const onSend = jest.fn();
    render(
      <AgentWorkspaceInput
        conversationId="c1"
        onSend={onSend}
        playbooks={[{ playbook_id: 1, playbook_name: '营收分析' }]}
      />,
    );
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '/' } });
    expect(screen.getByText('营收分析')).toBeInTheDocument();
    fireEvent.click(screen.getByText('营收分析'));
    // 选中生成 chip
    expect(screen.getByTitle('移除剧本')).toBeInTheDocument();
  });

  test('/ 菜单命令组包含内置与空间自定义命令', () => {
    render(<AgentWorkspaceInput conversationId="c1" workspaceId={1} onSend={jest.fn()} />);
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '/' } });
    expect(screen.getByText('/规划模式')).toBeInTheDocument(); // 内置种子
    expect(screen.getByText('/deep-think')).toBeInTheDocument(); // 空间自定义
  });

  test('自定义命令选中成 chip,再次选中即取消', () => {
    render(<AgentWorkspaceInput conversationId="c1" workspaceId={1} onSend={jest.fn()} />);
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '/deep' } });
    fireEvent.keyDown(textarea, { key: 'Enter' });
    expect(screen.getByText('开启深度思考')).toBeInTheDocument();
    // 再选中一次 = 关闭
    fireEvent.change(textarea, { target: { value: '/deep' } });
    fireEvent.keyDown(textarea, { key: 'Enter' });
    expect(screen.queryByText('开启深度思考')).not.toBeInTheDocument();
  });

  test('自定义命令开启后发送携带 commandPayload', () => {
    const onSend = jest.fn();
    render(<AgentWorkspaceInput conversationId="c1" workspaceId={1} onSend={onSend} />);
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '/deep' } });
    fireEvent.keyDown(textarea, { key: 'Enter' });
    fireEvent.change(textarea, { target: { value: '这个问题怎么解' } });
    fireEvent.keyDown(textarea, { key: 'Enter' });
    expect(onSend.mock.calls[0][0].commandPayload).toEqual({ deep_think: true });
  });

  test('前置非空白的 / 不唤起菜单(路径/网址不误触发)', () => {
    const onSend = jest.fn();
    render(
      <AgentWorkspaceInput
        conversationId="c1"
        onSend={onSend}
        playbooks={[{ playbook_id: 1, playbook_name: '营收分析' }]}
      />,
    );
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: 'a/b' } });
    expect(screen.queryByText('↑↓ 选择')).not.toBeInTheDocument();
  });

  test('句中 / 前置空白时可唤起菜单(不再要求行首)', () => {
    const onSend = jest.fn();
    render(
      <AgentWorkspaceInput
        conversationId="c1"
        onSend={onSend}
        playbooks={[{ playbook_id: 1, playbook_name: '营收分析' }]}
      />,
    );
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '帮我看下 /' } });
    expect(screen.getByText('营收分析')).toBeInTheDocument();
  });

  test('@ 唤起子 Agent 菜单并接管,发送时携带 subAgent', () => {
    const onSend = jest.fn();
    render(<AgentWorkspaceInput conversationId="c1" workspaceId={1} onSend={onSend} />);
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '@' } });
    expect(screen.getByText('数据分析专家')).toBeInTheDocument();
    // 菜单消费 Enter 完成选中,不应触发发送
    fireEvent.keyDown(textarea, { key: 'Enter' });
    expect(onSend).not.toHaveBeenCalled();
    expect(screen.getByText(/当前由/)).toBeInTheDocument();
    // 接管态是会话级:后续发送持续携带
    fireEvent.change(textarea, { target: { value: '看下报表' } });
    fireEvent.keyDown(textarea, { key: 'Enter' });
    expect(onSend).toHaveBeenCalledTimes(1);
    expect(onSend.mock.calls[0][0].subAgent).toMatchObject({ physical_ref: 'app-analyst' });
  });

  test('接管态可退出,退出后发送不再携带 subAgent', () => {
    const onSend = jest.fn();
    render(<AgentWorkspaceInput conversationId="c1" workspaceId={1} onSend={onSend} />);
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '@' } });
    fireEvent.keyDown(textarea, { key: 'Enter' });
    expect(screen.getByText(/当前由/)).toBeInTheDocument();
    fireEvent.click(screen.getByTitle('退出接管,恢复空间默认 Agent'));
    expect(screen.queryByText(/当前由/)).not.toBeInTheDocument();
    fireEvent.change(textarea, { target: { value: '普通提问' } });
    fireEvent.keyDown(textarea, { key: 'Enter' });
    expect(onSend.mock.calls[0][0].subAgent).toBeUndefined();
  });

  test('# 唤起资源菜单,选中后发送携带 resourceRefs', () => {
    const onSend = jest.fn();
    render(<AgentWorkspaceInput conversationId="c1" workspaceId={1} onSend={onSend} />);
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '#' } });
    expect(screen.getByText('月度报告.html')).toBeInTheDocument();
    expect(screen.getByText('客户分群规则')).toBeInTheDocument();
    fireEvent.keyDown(textarea, { key: 'Enter' });
    fireEvent.change(textarea, { target: { value: '帮我分析' } });
    fireEvent.keyDown(textarea, { key: 'Enter' });
    expect(onSend.mock.calls[0][0].resourceRefs).toEqual([
      expect.objectContaining({ kind: 'artifact', ref_id: 11, label: '月度报告.html' }),
    ]);
  });

  test('选中剧本后 onSend 携带 playbookCommand 与主题文本', () => {
    const onSend = jest.fn();
    render(
      <AgentWorkspaceInput
        conversationId="c1"
        onSend={onSend}
        playbooks={[{ playbook_id: 1, playbook_name: '营收分析' }]}
      />,
    );
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    // 开头 / 弹出剧本列表,选中后清掉 / 再输入主题
    fireEvent.change(textarea, { target: { value: '/' } });
    fireEvent.click(screen.getByText('营收分析'));
    fireEvent.change(textarea, { target: { value: '本月营收' } });
    fireEvent.keyDown(textarea, { key: 'Enter' });
    expect(onSend).toHaveBeenCalledWith(
      expect.objectContaining({
        text: '本月营收',
        playbookCommand: { playbook_id: 1, playbook_name: '营收分析' },
      }),
    );
  });

  test('focus 存在时渲染当前关注 chip, 点 × 调 onClearFocus', () => {
    const onSend = jest.fn();
    const onClearFocus = jest.fn();
    render(
      <AgentWorkspaceInput
        conversationId="c1"
        onSend={onSend}
        focus={{ id: 42, title: '周报' }}
        onClearFocus={onClearFocus}
      />,
    );
    expect(screen.getByText('周报')).toBeInTheDocument();
    expect(screen.getByText('当前关注')).toBeInTheDocument();
    fireEvent.click(screen.getByTitle('取消带入当前关注'));
    expect(onClearFocus).toHaveBeenCalled();
  });

  test('focus 为 null 时不渲染关注 chip', () => {
    const onSend = jest.fn();
    render(
      <AgentWorkspaceInput conversationId="c1" onSend={onSend} focus={null} />,
    );
    expect(screen.queryByText('当前关注')).not.toBeInTheDocument();
  });

  test('+ 号菜单展开显示 添加文件/剧本/技能 入口', () => {
    const onSend = jest.fn();
    render(
      <AgentWorkspaceInput
        conversationId="c1"
        onSend={onSend}
        playbooks={[{ playbook_id: 1, playbook_name: '营收分析' }]}
      />,
    );
    fireEvent.click(screen.getByTitle('添加文件 / 剧本 / 技能 / MCP / 命令'));
    expect(screen.getByText('添加文件')).toBeInTheDocument();
    expect(screen.getByText('剧本')).toBeInTheDocument();
    expect(screen.getByText('技能')).toBeInTheDocument();
  });

  test('+ 号菜单进入剧本面板, 选中后 chip 上屏且 onSend 携带 playbookCommand', () => {
    const onSend = jest.fn();
    render(
      <AgentWorkspaceInput
        conversationId="c1"
        onSend={onSend}
        playbooks={[{ playbook_id: 1, playbook_name: '营收分析' }]}
      />,
    );
    fireEvent.click(screen.getByTitle('添加文件 / 剧本 / 技能 / MCP / 命令'));
    fireEvent.click(screen.getByText('剧本'));
    fireEvent.click(screen.getByText('营收分析'));
    // chip 上屏
    expect(screen.getByTitle('移除剧本')).toBeInTheDocument();
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '本月营收' } });
    fireEvent.keyDown(textarea, { key: 'Enter' });
    expect(onSend).toHaveBeenCalledWith(
      expect.objectContaining({
        text: '本月营收',
        playbookCommand: { playbook_id: 1, playbook_name: '营收分析' },
      }),
    );
  });

  test('选中剧本 chip 带 / 前缀', () => {
    const onSend = jest.fn();
    render(
      <AgentWorkspaceInput
        conversationId="c1"
        onSend={onSend}
        playbooks={[{ playbook_id: 1, playbook_name: '营收分析' }]}
      />,
    );
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '/' } });
    fireEvent.click(screen.getByText('营收分析'));
    const chip = screen.getByTitle('移除剧本').closest('span');
    // 剧本 chip 以 / 前缀标识
    expect(chip?.textContent).toContain('/');
    expect(chip?.textContent).toContain('营收分析');
  });

  test('选中技能 chip 带「技能」前缀,发送时携带 skills', () => {
    const onSend = jest.fn();
    render(
      <AgentWorkspaceInput conversationId="c1" onSend={onSend} playbooks={[]} />,
    );
    // + 菜单 → 技能面板 → 选中技能(数据来自被 mock 的 useRequest)
    fireEvent.click(screen.getByTitle('添加文件 / 剧本 / 技能 / MCP / 命令'));
    fireEvent.click(screen.getByText('技能'));
    fireEvent.click(screen.getByText('代码审查'));
    // 技能 chip 上屏,带「技能」前缀
    const chip = screen.getByTitle('移除技能').closest('span');
    expect(chip?.textContent).toContain('技能');
    expect(chip?.textContent).toContain('代码审查');
    // 主输入框按 placeholder 精确定位(菜单内还有搜索框)
    const textarea = screen.getByPlaceholderText(/输入指令给 Agent/) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '看下这个' } });
    fireEvent.keyDown(textarea, { key: 'Enter' });
    expect(onSend).toHaveBeenCalledWith(
      expect.objectContaining({
        text: '看下这个',
        skills: [expect.objectContaining({ skill_code: 'code-review' })],
      }),
    );
  });

  test('/ 菜单展示会话命令分组(压缩上下文/清理会话/规划模式)', () => {
    const onSend = jest.fn();
    render(<AgentWorkspaceInput conversationId="c1" onSend={onSend} playbooks={[]} />);
    const textarea = screen.getByPlaceholderText(/输入指令给 Agent/) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '/' } });
    // 命令组
    expect(screen.getByText('命令')).toBeInTheDocument();
    expect(screen.getByText('/压缩上下文')).toBeInTheDocument();
    expect(screen.getByText('/清理会话')).toBeInTheDocument();
    expect(screen.getByText('/规划模式')).toBeInTheDocument();
  });

  test('/规划模式 选中后生成「规划」chip,发送携带 plan 权限', () => {
    const onSend = jest.fn();
    render(<AgentWorkspaceInput conversationId="c1" onSend={onSend} playbooks={[]} />);
    const textarea = screen.getByPlaceholderText(/输入指令给 Agent/) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '/' } });
    fireEvent.click(screen.getByText('/规划模式'));
    // 规划 chip 上屏
    const chip = screen.getByTitle('退出规划模式').closest('span');
    expect(chip?.textContent).toContain('规划');
    // 输入主题发送,携带 plan 权限档
    fireEvent.change(textarea, { target: { value: '帮我规划一下' } });
    fireEvent.keyDown(textarea, { key: 'Enter' });
    expect(onSend).toHaveBeenCalledWith(
      expect.objectContaining({ text: '帮我规划一下', permission: 'plan' }),
    );
  });

  test('/清理会话 选中即调 onClearContext', () => {
    const onSend = jest.fn();
    const onClearContext = jest.fn();
    render(
      <AgentWorkspaceInput conversationId="c1" onSend={onSend} playbooks={[]} onClearContext={onClearContext} />,
    );
    const textarea = screen.getByPlaceholderText(/输入指令给 Agent/) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '/' } });
    fireEvent.click(screen.getByText('/清理会话'));
    expect(onClearContext).toHaveBeenCalled();
  });

  test('/压缩上下文 选中后生成「压缩」chip,发送携带 forceCompress', () => {
    const onSend = jest.fn();
    render(<AgentWorkspaceInput conversationId="c1" onSend={onSend} playbooks={[]} />);
    const textarea = screen.getByPlaceholderText(/输入指令给 Agent/) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '/' } });
    fireEvent.click(screen.getByText('/压缩上下文'));
    // 压缩 chip 上屏
    const chip = screen.getByTitle('取消压缩').closest('span');
    expect(chip?.textContent).toContain('压缩');
    // 发送携带 forceCompress
    fireEvent.change(textarea, { target: { value: '继续' } });
    fireEvent.keyDown(textarea, { key: 'Enter' });
    expect(onSend).toHaveBeenCalledWith(
      expect.objectContaining({ text: '继续', forceCompress: true }),
    );
  });

  test('有 usageMetrics 时渲染上下文空间环形图', () => {
    const onSend = jest.fn();
    render(
      <AgentWorkspaceInput
        conversationId="c1"
        onSend={onSend}
        usageMetrics={{ total: 12300, prompt: 12000, completion: 300, context_window: 128000, ratio: 0.096 }}
      />,
    );
    expect(screen.getByRole('img', { name: /上下文空间使用率/ })).toBeInTheDocument();
  });

  test('无 usageMetrics 时不渲染环形图', () => {
    const onSend = jest.fn();
    render(<AgentWorkspaceInput conversationId="c1" onSend={onSend} usageMetrics={null} />);
    expect(screen.queryByRole('img', { name: /上下文空间使用率/ })).not.toBeInTheDocument();
  });

  test('点击上下文空间环形图打开详情抽屉', () => {
    const onSend = jest.fn();
    render(
      <AgentWorkspaceInput
        conversationId="c1"
        onSend={onSend}
        usageMetrics={{ total: 12300, prompt: 12000, completion: 300, context_window: 128000, ratio: 0.096 }}
      />,
    );
    fireEvent.click(screen.getByRole('img', { name: /上下文空间使用率/ }));
    expect(screen.getByText('上下文空间占用明细')).toBeInTheDocument();
  });
});

describe('AgentWorkspaceInput 附件暂存(跨重挂载)', () => {
  const SCOPE = 'ws-t';
  const xlsResource = {
    type: 'file_url',
    file_url: { url: 'gyra-fs://local/gyra_app_file/abc', preview_url: 'http://x/f', file_name: '数据.xlsx' },
  };

  afterEach(() => {
    setPendingResources(SCOPE, []);
    cleanup();
  });

  test('挂载时从暂存域恢复已上传未发送的附件 chip', () => {
    setPendingResources(SCOPE, [xlsResource]);
    render(<AgentWorkspaceInput conversationId="c1" onSend={jest.fn()} attachmentScopeKey={SCOPE} />);
    expect(screen.getByText('数据.xlsx')).toBeInTheDocument();
  });

  test('发送携带暂存附件,发送后清空暂存(重挂载不再恢复)', () => {
    setPendingResources(SCOPE, [xlsResource]);
    const onSend = jest.fn();
    const { unmount } = render(
      <AgentWorkspaceInput conversationId="c1" onSend={onSend} attachmentScopeKey={SCOPE} />,
    );
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '这个文件有啥内容' } });
    fireEvent.keyDown(textarea, { key: 'Enter' });
    expect(onSend).toHaveBeenCalledWith(
      expect.objectContaining({
        text: '这个文件有啥内容',
        resources: [expect.objectContaining({ type: 'file_url' })],
      }),
    );
    expect(getPendingResources(SCOPE)).toHaveLength(0);
    // 重挂载(模拟欢迎态→运行态分支切换)后不再出现已发送的附件
    unmount();
    render(<AgentWorkspaceInput conversationId="c1" onSend={jest.fn()} attachmentScopeKey={SCOPE} />);
    expect(screen.queryByText('数据.xlsx')).not.toBeInTheDocument();
  });

  test('无会话且无懒创建回调时上传被拦截并提示', async () => {
    const { postChatModeParamsFileLoad } = require('@/client/api');
    const warnSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    render(<AgentWorkspaceInput onSend={jest.fn()} />);
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [new File(['x'], 'a.txt')] } });
    await new Promise((r) => setTimeout(r, 0));
    expect(postChatModeParamsFileLoad).not.toHaveBeenCalled();
    warnSpy.mockRestore();
  });

  test('无会话时经懒创建回调取得会话后正常上传,附件进入暂存域', async () => {
    const { postChatModeParamsFileLoad } = require('@/client/api');
    const onEnsure = jest.fn(async () => 'c-new');
    const onSend = jest.fn();
    render(
      <AgentWorkspaceInput onSend={onSend} attachmentScopeKey={SCOPE} onEnsureConversation={onEnsure} />,
    );
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [new File(['x'], 'a.txt')] } });
    await waitFor(() => expect(screen.getByText('a.txt')).toBeInTheDocument());
    expect(onEnsure).toHaveBeenCalledTimes(1);
    expect(postChatModeParamsFileLoad).toHaveBeenCalledWith(
      expect.objectContaining({ conversationId: 'c-new', chatMode: 'chat_normal' }),
    );
    // 暂存域已有该附件:重挂载后恢复
    expect(getPendingResources(SCOPE)).toHaveLength(1);
    cleanup();
    render(<AgentWorkspaceInput conversationId="c1" onSend={onSend} attachmentScopeKey={SCOPE} />);
    expect(screen.getByText('a.txt')).toBeInTheDocument();
  });
});