/** @jest-environment jsdom */
import { render, fireEvent, screen } from '@testing-library/react';
import { AgentWorkspaceInput } from '../agent-workspace-input';

jest.mock('@/client/api', () => ({
  apiInterceptors: jest.fn(() => Promise.resolve([null, []])),
  getModelList: jest.fn(),
  getSkillList: jest.fn(),
  getMCPList: jest.fn(),
  postChatModeParamsFileLoad: jest.fn(),
}));
jest.mock('ahooks', () => ({
  // 依据调用的异步函数体粗略分流:技能列表返回一条技能,其余返回空
  useRequest: (fn: any) => {
    const src = String(fn);
    if (src.includes('getSkillList')) {
      return { loading: false, data: [{ skill_code: 'code-review', name: '代码审查', description: '审查代码质量' }] };
    }
    return { loading: false };
  },
}));

describe('AgentWorkspaceInput', () => {
  test('输入 / 且有 playbooks 时显示剧本列表', () => {
    const onSend = jest.fn();
    render(
      <AgentWorkspaceInput
        convUid="c1"
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
        convUid="c1"
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
        convUid="c1"
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
        convUid="c1"
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
        convUid="c1"
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

  test('文本中间的 / 不唤起菜单', () => {
    const onSend = jest.fn();
    render(
      <AgentWorkspaceInput
        convUid="c1"
        onSend={onSend}
        playbooks={[{ playbook_id: 1, playbook_name: '营收分析' }]}
      />,
    );
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: 'a/b' } });
    expect(screen.queryByText('↑↓ 选择')).not.toBeInTheDocument();
  });

  test('选中剧本后 onSend 携带 playbookCommand 与主题文本', () => {
    const onSend = jest.fn();
    render(
      <AgentWorkspaceInput
        convUid="c1"
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
        convUid="c1"
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
      <AgentWorkspaceInput convUid="c1" onSend={onSend} focus={null} />,
    );
    expect(screen.queryByText('当前关注')).not.toBeInTheDocument();
  });

  test('+ 号菜单展开显示 添加文件/剧本/技能 入口', () => {
    const onSend = jest.fn();
    render(
      <AgentWorkspaceInput
        convUid="c1"
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
        convUid="c1"
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
        convUid="c1"
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
      <AgentWorkspaceInput convUid="c1" onSend={onSend} playbooks={[]} />,
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
    render(<AgentWorkspaceInput convUid="c1" onSend={onSend} playbooks={[]} />);
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
    render(<AgentWorkspaceInput convUid="c1" onSend={onSend} playbooks={[]} />);
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
      <AgentWorkspaceInput convUid="c1" onSend={onSend} playbooks={[]} onClearContext={onClearContext} />,
    );
    const textarea = screen.getByPlaceholderText(/输入指令给 Agent/) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '/' } });
    fireEvent.click(screen.getByText('/清理会话'));
    expect(onClearContext).toHaveBeenCalled();
  });

  test('/压缩上下文 选中后生成「压缩」chip,发送携带 forceCompress', () => {
    const onSend = jest.fn();
    render(<AgentWorkspaceInput convUid="c1" onSend={onSend} playbooks={[]} />);
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
        convUid="c1"
        onSend={onSend}
        usageMetrics={{ total: 12300, prompt: 12000, completion: 300, context_window: 128000, ratio: 0.096 }}
      />,
    );
    expect(screen.getByRole('img', { name: /上下文空间使用率/ })).toBeInTheDocument();
  });

  test('无 usageMetrics 时不渲染环形图', () => {
    const onSend = jest.fn();
    render(<AgentWorkspaceInput convUid="c1" onSend={onSend} usageMetrics={null} />);
    expect(screen.queryByRole('img', { name: /上下文空间使用率/ })).not.toBeInTheDocument();
  });

  test('点击上下文空间环形图打开详情抽屉', () => {
    const onSend = jest.fn();
    render(
      <AgentWorkspaceInput
        convUid="c1"
        onSend={onSend}
        usageMetrics={{ total: 12300, prompt: 12000, completion: 300, context_window: 128000, ratio: 0.096 }}
      />,
    );
    fireEvent.click(screen.getByRole('img', { name: /上下文空间使用率/ }));
    expect(screen.getByText('上下文空间占用明细')).toBeInTheDocument();
  });
});