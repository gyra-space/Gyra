/** @jest-environment jsdom */
import { render, fireEvent, screen } from '@testing-library/react';
import { AgentWorkspaceInput } from '../agent-workspace-input';

jest.mock('@/client/api', () => ({
  apiInterceptors: jest.fn(() => Promise.resolve([null, []])),
  getModelList: jest.fn(),
  getSkillList: jest.fn(),
  postChatModeParamsFileLoad: jest.fn(),
}));
jest.mock('ahooks', () => ({ useRequest: () => ({ loading: false }) }));

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
    fireEvent.click(screen.getByTitle('添加文件 / 剧本 / 技能'));
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
    fireEvent.click(screen.getByTitle('添加文件 / 剧本 / 技能'));
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