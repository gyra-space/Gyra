/** @jest-environment jsdom */
import { render, screen, fireEvent, act } from '@testing-library/react';
import { createRef } from 'react';
import { TriggerMenu } from '../trigger-menu';
import type { TriggerMenuHandle, TriggerMenuGroup } from '../trigger-menu';

const icon = <span data-testid="icon" />;

const item = (key: string, title: string, extra?: { description?: string; mono?: boolean }) => ({
  key,
  icon,
  title,
  description: extra?.description ?? `desc-${key}`,
  mono: extra?.mono,
  data: { id: key },
});

const group = (key: string, items: ReturnType<typeof item>[], loading?: boolean): TriggerMenuGroup => ({
  key,
  label: key,
  items,
  loading,
});

function setup(initial: Partial<React.ComponentProps<typeof TriggerMenu>> & {
  groups: TriggerMenuGroup[];
}) {
  const ref = createRef<TriggerMenuHandle>();
  const onSelect = jest.fn();
  const onClose = jest.fn();
  let props: React.ComponentProps<typeof TriggerMenu> = {
    open: true,
    query: '',
    triggerChar: '/',
    onSelect,
    onClose,
    ...initial,
  };
  const tree = (p: React.ComponentProps<typeof TriggerMenu>) => (
    <TriggerMenu ref={ref} {...p}>
      <input />
    </TriggerMenu>
  );
  const view = render(tree(props));

  /**
   * 模拟输入框把 keydown 转交给菜单;返回是否被菜单消费。
   * 必须包在 act 里:菜单高亮是 state,连续按键之间需要 flush 才能读到最新值
   * (真实交互中两次按键天然跨帧,测试里要手动 flush)。
   */
  const press = (key: string) => {
    let consumed = false;
    act(() => {
      const e = { key, preventDefault: jest.fn() } as unknown as React.KeyboardEvent;
      consumed = ref.current!.handleKey(e);
    });
    return consumed;
  };

  /** 保持同一个 ref 更新 props(用于验证过滤词变化后的高亮重置) */
  const rerenderWith = (patch: Partial<React.ComponentProps<typeof TriggerMenu>>) => {
    props = { ...props, ...patch };
    view.rerender(tree(props));
  };

  return { ref, onSelect, onClose, press, rerenderWith, ...view };
}

describe('TriggerMenu', () => {
  test('按分组渲染条目与分组标题', () => {
    setup({
      groups: [
        group('剧本', [item('p1', '营收分析')]),
        group('技能', [item('s1', '代码审查')]),
      ],
    });
    expect(screen.getByText('剧本')).toBeInTheDocument();
    expect(screen.getByText('技能')).toBeInTheDocument();
    expect(screen.getByText('营收分析')).toBeInTheDocument();
    expect(screen.getByText('代码审查')).toBeInTheDocument();
  });

  test('query 过滤:保留命中项、剔除未命中项', () => {
    setup({
      query: '审查',
      groups: [group('技能', [item('s1', '代码审查'), item('s2', '单元测试')])],
    });
    expect(screen.getByText('代码审查')).toBeInTheDocument();
    expect(screen.queryByText('单元测试')).not.toBeInTheDocument();
  });

  test('query 同时匹配描述字段', () => {
    setup({
      query: 'lint',
      groups: [group('技能', [item('s1', '静态检查', { description: 'run lint' })])],
    });
    expect(screen.getByText('静态检查')).toBeInTheDocument();
  });

  test('query 匹配隐藏关键词 keywords(别名/英文命中但不上屏)', () => {
    setup({
      query: 'upload',
      groups: [
        group('文件', [
          {
            key: 'addFile',
            icon: <span />,
            title: '添加文件',
            description: '上传本地文件作为上下文',
            keywords: ['file', 'upload'],
          },
        ]),
      ],
    });
    expect(screen.getByText('添加文件')).toBeInTheDocument();
  });

  test('无匹配项时展示空态文案', () => {
    setup({ query: 'zzz', groups: [group('技能', [item('s1', '代码审查')])] });
    expect(screen.getByText('无匹配项')).toBeInTheDocument();
  });

  test('空态文案可自定义', () => {
    setup({
      query: 'zzz',
      emptyText: '暂无可用子 Agent',
      groups: [group('子 Agent', [item('a1', '分析专家')])],
    });
    expect(screen.getByText('暂无可用子 Agent')).toBeInTheDocument();
  });

  test('分组 loading 且无数据时显示加载中', () => {
    setup({ groups: [group('MCP', [], true)] });
    expect(screen.getByText(/加载中/)).toBeInTheDocument();
  });

  test('Enter 选中首项并回传 data,同时触发 onClose', () => {
    const { press, onSelect, onClose } = setup({
      groups: [group('剧本', [item('p1', '营收分析'), item('p2', '故障排查')])],
    });
    expect(press('Enter')).toBe(true);
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect.mock.calls[0][0]).toMatchObject({ key: 'p1', title: '营收分析' });
    expect(onSelect.mock.calls[0][0].data).toEqual({ id: 'p1' });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  test('↓ 移动高亮,Enter 选中第二项', () => {
    const { press, onSelect } = setup({
      groups: [group('剧本', [item('p1', '营收分析'), item('p2', '故障排查')])],
    });
    press('ArrowDown');
    press('Enter');
    expect(onSelect.mock.calls[0][0].key).toBe('p2');
  });

  test('↑ 从首项回环到末项', () => {
    const { press, onSelect } = setup({
      groups: [group('剧本', [item('p1', 'A'), item('p2', 'B'), item('p3', 'C')])],
    });
    press('ArrowUp');
    press('Enter');
    expect(onSelect.mock.calls[0][0].key).toBe('p3');
  });

  test('↓ 越过末项回环到首项', () => {
    const { press, onSelect } = setup({
      groups: [group('剧本', [item('p1', 'A'), item('p2', 'B')])],
    });
    press('ArrowDown');
    press('ArrowDown');
    press('Enter');
    expect(onSelect.mock.calls[0][0].key).toBe('p1');
  });

  test('键盘导航跨分组连续(分组间不重置序号)', () => {
    const { press, onSelect } = setup({
      groups: [group('剧本', [item('p1', 'A')]), group('技能', [item('s1', 'B')])],
    });
    press('ArrowDown');
    press('Enter');
    expect(onSelect.mock.calls[0][0].key).toBe('s1');
  });

  test('过滤词变化后高亮重置到首项', () => {
    const { press, onSelect, rerenderWith } = setup({
      groups: [group('技能', [item('s1', 'A'), item('s2', 'B'), item('s3', 'C')])],
    });
    // 先移到第三项
    press('ArrowDown');
    press('ArrowDown');
    // 过滤后只剩两项,高亮应回到首项而非停留在漂移位置
    rerenderWith({
      query: 'A',
      groups: [group('技能', [item('s1', 'A'), item('s3', 'C')])],
    });
    press('Enter');
    expect(onSelect.mock.calls[0][0].key).toBe('s1');
  });

  test('Esc 触发关闭且不选中', () => {
    const { press, onSelect, onClose } = setup({ groups: [group('技能', [item('s1', 'A')])] });
    expect(press('Escape')).toBe(true);
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(onSelect).not.toHaveBeenCalled();
  });

  test('未消费的按键返回 false(交还输入框处理)', () => {
    const { press } = setup({ groups: [group('技能', [item('s1', 'A')])] });
    expect(press('a')).toBe(false);
    expect(press('Tab')).toBe(false);
  });

  test('open=false 时 handleKey 一律返回 false', () => {
    const { press } = setup({ open: false, groups: [group('技能', [item('s1', 'A')])] });
    expect(press('Enter')).toBe(false);
    expect(press('ArrowDown')).toBe(false);
  });

  test('鼠标点击条目直接选中', () => {
    const { onSelect, onClose } = setup({
      groups: [group('剧本', [item('p1', '营收分析'), item('p2', '故障排查')])],
    });
    fireEvent.click(screen.getByText('故障排查'));
    expect(onSelect.mock.calls[0][0].key).toBe('p2');
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  test('搜索提示展示 trigger 字符 + 过滤词', () => {
    setup({ query: 'comp', triggerChar: '/', groups: [group('命令', [item('c1', '/compact', { mono: true })])] });
    expect(screen.getByText('/comp')).toBeInTheDocument();
  });

  test('无过滤词时展示占位提示', () => {
    setup({ query: '', placeholder: '输入关键词检索资源', groups: [group('资源', [item('r1', 'A')])] });
    expect(screen.getByText('输入关键词检索资源')).toBeInTheDocument();
  });
});
