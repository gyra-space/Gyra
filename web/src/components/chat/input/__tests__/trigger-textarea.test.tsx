/** @jest-environment jsdom */
import { render, screen, fireEvent, act } from '@testing-library/react';
import { TriggerTextArea } from '../trigger-textarea';
import type { ResourceRef } from '../trigger-types';

jest.mock('@/client/api', () => ({
  apiInterceptors: jest.fn(() => Promise.resolve([null, []])),
  listArtifacts: jest.fn(),
  listAssets: jest.fn(),
}));
jest.mock('ahooks', () => ({
  useRequest: (fn: any) => {
    const src = String(fn);
    if (src.includes('listArtifacts')) {
      return { loading: false, data: [{ artifact_id: 11, title: '月度报告.html', content_ref: '/files/11.html' }] };
    }
    if (src.includes('listAssets')) {
      return { loading: false, data: [{ asset_id: 21, name: '客户分群规则', maturity: 'confirmed' }] };
    }
    return { loading: false };
  },
}));

function setup(extra: Partial<React.ComponentProps<typeof TriggerTextArea>> = {}) {
  const onRefsChange = jest.fn();
  const view = render(
    <TriggerTextArea
      workspaceId={1}
      refs={[]}
      onRefsChange={onRefsChange}
      placeholder="输入指令"
      {...extra}
    />,
  );
  return { onRefsChange, ...view };
}

describe('TriggerTextArea', () => {
  test('输入 # 唤起资源菜单(与对话输入框同一面板)', () => {
    setup();
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '#' } });
    expect(screen.getByText('月度报告.html')).toBeInTheDocument();
    expect(screen.getByText('客户分群规则')).toBeInTheDocument();
  });

  test('默认只开 #,/ 与 @ 不唤起(剧本已定能力、任务已定执行者)', () => {
    setup();
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '/' } });
    expect(screen.queryByText('↑↓ 选择')).not.toBeInTheDocument();
    fireEvent.change(textarea, { target: { value: '@' } });
    expect(screen.queryByText('↑↓ 选择')).not.toBeInTheDocument();
  });

  test('选中 artifact 后经 onRefsChange 回传结构化引用', () => {
    const { onRefsChange } = setup();
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '分析 #' } });
    act(() => {
      fireEvent.keyDown(textarea, { key: 'Enter' });
    });
    expect(onRefsChange).toHaveBeenCalledTimes(1);
    const refs = onRefsChange.mock.calls[0][0] as ResourceRef[];
    expect(refs).toEqual([
      expect.objectContaining({ kind: 'artifact', ref_id: 11, label: '月度报告.html' }),
    ]);
  });

  test('已选引用渲染为可移除的 chip', () => {
    const onRefsChange = jest.fn();
    render(
      <TriggerTextArea
        workspaceId={1}
        refs={[
          { id: 'artifact:11', kind: 'artifact', label: '月度报告.html', ref_id: 11, start: 0, end: 0 },
        ]}
        onRefsChange={onRefsChange}
      />,
    );
    expect(screen.getByText('月度报告.html')).toBeInTheDocument();
    fireEvent.click(screen.getByTitle('移除引用'));
    expect(onRefsChange).toHaveBeenCalledWith([]);
  });

  test('选中后清掉 trigger token 且不误删前文', () => {
    const onChange = jest.fn();
    // 受控组件:value 必须留空,否则 fireEvent.change 设同值不会触发 onChange
    render(
      <TriggerTextArea workspaceId={1} value="" onChange={onChange} refs={[]} onRefsChange={jest.fn()} />,
    );
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '分析这份 #' } });
    act(() => {
      fireEvent.keyDown(textarea, { key: 'Enter' });
    });
    // 最后一次 onChange 只清掉 `#` token,前文与前置空格保留
    expect(onChange).toHaveBeenLastCalledWith('分析这份 ');
  });
});
