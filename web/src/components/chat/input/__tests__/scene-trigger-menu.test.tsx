/** @jest-environment jsdom */
import { render, screen, act, fireEvent } from '@testing-library/react';
import { createRef } from 'react';
import { SceneTriggerMenu } from '../scene-trigger-menu';
import type { SceneTriggerMenuHandle, SceneTriggerSelection } from '../scene-trigger-menu';
import type { TriggerState } from '../trigger-detect';

const ts = (char: TriggerState['char'], query = ''): TriggerState => ({
  char,
  start: 0,
  end: query.length + 1,
  query,
});

const subAgent = { resource_id: 1, name: '数据分析专家', physical_ref: 'app-analyst', description: '擅长报表分析' };
const artifact = { artifact_id: 11, title: '月度报告.html', content_ref: '/files/11.html' };
const asset = { asset_id: 21, name: '客户分群规则', description: '已确认的分群口径', maturity: 'confirmed' };

function setup(trigger: TriggerState | null, extra: Partial<React.ComponentProps<typeof SceneTriggerMenu>> = {}) {
  const ref = createRef<SceneTriggerMenuHandle>();
  const onSelect = jest.fn();
  const onClose = jest.fn();
  const view = render(
    <SceneTriggerMenu
      ref={ref}
      trigger={trigger}
      subAgents={[subAgent]}
      artifacts={[artifact]}
      assets={[asset]}
      playbooks={[{ playbook_id: 1, playbook_name: '营收分析' }]}
      commands={[{ command: '规划模式', name: '规划模式', description: '本回合使用规划能力', action: 'plan' }]}
      onSelect={onSelect}
      onClose={onClose}
      {...extra}
    >
      <input />
    </SceneTriggerMenu>,
  );
  const press = (key: string) => {
    let consumed = false;
    act(() => {
      const e = { key, preventDefault: jest.fn() } as unknown as React.KeyboardEvent;
      consumed = ref.current!.handleKey(e);
    });
    return consumed;
  };
  return { ref, onSelect, onClose, press, ...view };
}

describe('SceneTriggerMenu', () => {
  test('trigger 为 null 时不渲染菜单内容', () => {
    setup(null);
    expect(screen.queryByText('数据分析专家')).not.toBeInTheDocument();
    expect(press0()).toBe(false);
  });

  test('@ 只展示子 Agent 分组,不混入剧本/技能', () => {
    setup(ts('@'));
    expect(screen.getByText('子 Agent')).toBeInTheDocument();
    expect(screen.getByText('数据分析专家')).toBeInTheDocument();
    expect(screen.queryByText('剧本')).not.toBeInTheDocument();
    expect(screen.queryByText('营收分析')).not.toBeInTheDocument();
  });

  test('# 展示交付产物与空间资产两个分组', () => {
    setup(ts('#'));
    expect(screen.getByText('交付产物')).toBeInTheDocument();
    expect(screen.getByText('空间资产')).toBeInTheDocument();
    expect(screen.getByText('月度报告.html')).toBeInTheDocument();
    expect(screen.getByText('客户分群规则')).toBeInTheDocument();
  });

  test('/ 展示命令分组,无剧本组(剧本已收敛到 @)', () => {
    setup(ts('/'));
    expect(screen.getByText('命令')).toBeInTheDocument();
    expect(screen.getByText('/规划模式')).toBeInTheDocument();
    expect(screen.queryByText('剧本')).not.toBeInTheDocument();
  });

  test('选中子 Agent 回传 trigger=@ 与原始引用', () => {
    const { press, onSelect } = setup(ts('@'));
    press('Enter');
    const sel = onSelect.mock.calls[0][0] as SceneTriggerSelection;
    expect(sel).toMatchObject({ trigger: '@', type: 'subAgent' });
    expect((sel as any).subAgent).toEqual(subAgent);
  });

  test('选中 artifact 回传 trigger=# 与 artifact_id', () => {
    const { press, onSelect } = setup(ts('#'));
    press('Enter');
    const sel = onSelect.mock.calls[0][0] as SceneTriggerSelection;
    expect(sel).toMatchObject({ trigger: '#', type: 'artifact' });
    expect((sel as any).artifact.artifact_id).toBe(11);
  });

  test('@ 过滤词可检索子 Agent', () => {
    setup(ts('@', '报表'));
    expect(screen.getByText('数据分析专家')).toBeInTheDocument();
  });

  test('@ 无可用子 Agent 时展示引导型空态', () => {
    setup(ts('@'), { subAgents: [] });
    expect(screen.getByText('当前空间暂无可用子 Agent')).toBeInTheDocument();
  });

  test('# 无资源时展示空态', () => {
    setup(ts('#'), { artifacts: [], assets: [] });
    expect(screen.getByText('暂无可引用的资源')).toBeInTheDocument();
  });

  test('@ 加载中显示 loading 占位而非空态', () => {
    setup(ts('@'), { subAgents: [], subAgentsLoading: true });
    expect(screen.getByText(/加载中/)).toBeInTheDocument();
    expect(screen.queryByText('当前空间暂无可用子 Agent')).not.toBeInTheDocument();
  });

  test('三个 trigger 共用同一套键盘导航', () => {
    const { press, onSelect } = setup(ts('#'));
    press('ArrowDown'); // 交付产物 → 空间资产
    press('Enter');
    expect((onSelect.mock.calls[0][0] as any).type).toBe('asset');
  });

  test('点击选中与键盘选中结果一致', () => {
    const { onSelect } = setup(ts('@'));
    fireEvent.click(screen.getByText('数据分析专家'));
    expect((onSelect.mock.calls[0][0] as any).type).toBe('subAgent');
  });

  test('搜索框回显当前过滤词', () => {
    setup(ts('@', '分析'));
    expect(screen.getByDisplayValue('分析')).toBeInTheDocument();
  });
});

/** trigger 为 null 的场景下直接构造一个独立 ref 验证 handleKey 返回 false */
function press0(): boolean {
  const ref = createRef<SceneTriggerMenuHandle>();
  render(
    <SceneTriggerMenu
      ref={ref}
      trigger={null}
      onSelect={jest.fn()}
      onClose={jest.fn()}
    >
      <input />
    </SceneTriggerMenu>,
  );
  const e = { key: 'Enter', preventDefault: jest.fn() } as unknown as React.KeyboardEvent;
  return ref.current!.handleKey(e);
}
