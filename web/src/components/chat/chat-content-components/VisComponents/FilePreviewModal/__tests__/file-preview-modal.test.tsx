import { render, screen } from '@testing-library/react';

import FilePreviewModal from '..';

// 预览器会拉进 GPTVis / syntax-highlighter / remark 全家桶，这里按类型分发已被
// 单独覆盖，本文件只关心"哪些类型不该走文本分支"，所以把重渲染依赖打桩。
jest.mock(
  '@/components/chat/chat-content-components/code-preview',
  () => ({
    __esModule: true,
    CodePreview: ({ code }: { code: string }) => <pre data-testid="code-preview">{code}</pre>,
  })
);

jest.mock('@antv/gpt-vis', () => ({
  __esModule: true,
  GPTVis: ({ children }: { children: React.ReactNode }) => <div data-testid="gpt-vis">{children}</div>,
}));

const renderPreview = (file: Parameters<typeof FilePreviewModal>[0]['file']) =>
  render(<FilePreviewModal visible file={file} onClose={jest.fn()} />);

// 全部断言走 findBy*：组件内有 30ms 动画定时器会异步 setState，
// 同步断言既可能漏读、又会触发 React 的 act 警告。
describe('FilePreviewModal 二进制类型不再走文本分支', () => {
  it.each([
    ['data.xlsx', undefined],
    ['report.docx', undefined],
    ['bundle.zip', undefined],
    ['archive.tar.gz', undefined],
    ['font.ttf', undefined],
    ['app.db', undefined],
    ['export', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
  ])('%s 显示「不支持预览」而不是乱码文本', async (name, mime) => {
    renderPreview({ file_name: name, mime_type: mime, url: `https://x/${name}` });

    expect(await screen.findByText('该文件格式暂不支持在线预览')).toBeInTheDocument();
    // 关键回归点：不能出现文本/代码渲染容器
    expect(screen.queryByTestId('code-preview')).not.toBeInTheDocument();
    expect(screen.queryByTestId('gpt-vis')).not.toBeInTheDocument();
  });

  it('不支持预览时给出下载出口，无地址则禁用', async () => {
    const { unmount } = renderPreview({ file_name: 'data.xlsx', url: 'https://x/data.xlsx' });
    expect(await screen.findByRole('button', { name: /下载文件/ })).toBeEnabled();
    unmount();

    renderPreview({ file_name: 'data.xlsx' });
    expect(await screen.findByRole('button', { name: /下载文件/ })).toBeDisabled();
  });
});

describe('FilePreviewModal PDF 渲染', () => {
  it('PDF 走 iframe，不会去 fetch 文本内容', async () => {
    // jsdom 不提供 fetch，需手动注入才能断言"没去读文本"
    const fetchSpy = jest.fn();
    const original = global.fetch;
    global.fetch = fetchSpy as unknown as typeof fetch;

    try {
      renderPreview({ file_name: 'report.pdf', url: 'https://x/report.pdf' });

      const frame = await screen.findByTitle('report.pdf');
      expect(frame.tagName).toBe('IFRAME');
      expect(frame).toHaveAttribute('src', 'https://x/report.pdf');
      expect(fetchSpy).not.toHaveBeenCalled();
      expect(screen.queryByTestId('code-preview')).not.toBeInTheDocument();
    } finally {
      global.fetch = original;
    }
  });
});

/** 注入 fetch mock：jsdom 不提供 fetch，而文本分支依赖它 */
const withFetch = async (
  impl: jest.Mock,
  body: () => Promise<void>
): Promise<void> => {
  const original = global.fetch;
  global.fetch = impl as unknown as typeof fetch;
  try {
    await body();
  } finally {
    global.fetch = original;
  }
};

const okResponse = (text: string) =>
  jest.fn().mockResolvedValue({ ok: true, text: async () => text });

describe('FilePreviewModal 文本类类型仍正常渲染', () => {
  it('无扩展名的 Dockerfile 仍走文本渲染容器（防误杀）', async () => {
    await withFetch(okResponse('FROM node:20\nWORKDIR /app'), async () => {
      renderPreview({ file_name: 'Dockerfile', url: 'https://x/Dockerfile' });

      const code = await screen.findByTestId('code-preview');
      expect(code).toHaveTextContent('FROM node:20');
      expect(screen.queryByText('该文件格式暂不支持在线预览')).not.toBeInTheDocument();
    });
  });

  it('markdown 走 GPTVis 而不是代码渲染', async () => {
    await withFetch(okResponse('# 标题\n- 列表项'), async () => {
      renderPreview({ file_name: 'doc.md', url: 'https://x/doc.md' });

      const vis = await screen.findByTestId('gpt-vis');
      expect(vis).toHaveTextContent('标题');
      expect(screen.queryByTestId('code-preview')).not.toBeInTheDocument();
    });
  });
});

/**
 * 回归：远程文本读取成功后必须收尾 loading。
 * 修复前成功路径是裸 return，漏了 setLoading(false)，
 * 导致所有远程 markdown / 代码 / 文本预览永久停在"加载中"。
 */
describe('FilePreviewModal loading 收尾', () => {
  it('加载成功后不再停留在「加载中」', async () => {
    await withFetch(okResponse('hello content'), async () => {
      renderPreview({ file_name: 'a.txt', url: 'https://x/a.txt' });

      expect(await screen.findByTestId('code-preview')).toHaveTextContent('hello content');
      expect(screen.queryByText('加载中...')).not.toBeInTheDocument();
    });
  });

  it('HTTP 失败时显示错误而不是永久转圈', async () => {
    const failing = jest.fn().mockResolvedValue({ ok: false, status: 404 });
    await withFetch(failing, async () => {
      renderPreview({ file_name: 'a.txt', url: 'https://x/a.txt' });

      expect(await screen.findByText(/无法读取文件内容/)).toBeInTheDocument();
      expect(screen.queryByText('加载中...')).not.toBeInTheDocument();
    });
  });

  it('网络异常时显示错误而不是永久转圈', async () => {
    const throwing = jest.fn().mockRejectedValue(new Error('Network Error'));
    await withFetch(throwing, async () => {
      renderPreview({ file_name: 'a.txt', url: 'https://x/a.txt' });

      expect(await screen.findByText(/无法读取文件内容/)).toBeInTheDocument();
      expect(screen.queryByText('加载中...')).not.toBeInTheDocument();
    });
  });

  it('读到的内容若嗅探为二进制，改显「不支持预览」', async () => {
    const binary = jest.fn().mockResolvedValue({
      ok: true,
      text: async () => `PK${String.fromCharCode(0)}${String.fromCharCode(0)}junk`,
    });
    await withFetch(binary, async () => {
      renderPreview({ file_name: 'mystery', url: 'https://x/mystery' });

      expect(await screen.findByText('该文件格式暂不支持在线预览')).toBeInTheDocument();
      expect(screen.queryByTestId('code-preview')).not.toBeInTheDocument();
    });
  });
});
