import { act, render, renderHook, screen } from '@testing-library/react';

import {
  AttachmentPreviewHost,
  LocalFileThumb,
  makePreviewPayload,
  normalizeResourceItem,
  normalizeUploadingFile,
  openAttachmentPreview,
  useAttachmentPreview,
  useObjectUrl,
} from '../attachment-preview';

// 隔离预览器的重依赖（GPTVis / syntax-highlighter）：本文件只验证归一化与广播机制。
// PreviewFilePayload 是纯类型导出，运行时被擦除，不受 mock 影响。
jest.mock(
  '@/components/chat/chat-content-components/VisComponents/FilePreviewModal',
  () => ({
    __esModule: true,
    default: ({ visible, file }: { visible: boolean; file: { file_name?: string } | null }) =>
      visible && file ? <div data-testid="preview-modal">{file.file_name}</div> : null,
  })
);

const makeFile = (name = 'a.png', type = 'image/png') =>
  new File(['x'], name, { type });

describe('normalizeResourceItem', () => {
  it('非对象输入一律返回 null（防御脏数据）', () => {
    expect(normalizeResourceItem(null)).toBeNull();
    expect(normalizeResourceItem(undefined)).toBeNull();
    expect(normalizeResourceItem('str')).toBeNull();
    expect(normalizeResourceItem(42)).toBeNull();
    expect(normalizeResourceItem({})).toBeNull();
  });

  it('解析 image_url 嵌套结构（三处输入框的统一形态）', () => {
    const out = normalizeResourceItem({
      type: 'image_url',
      image_url: { url: 'https://x/a.png', file_name: 'a.png' },
    });
    expect(out).toMatchObject({ file_name: 'a.png', url: 'https://x/a.png' });
  });

  it('嵌套结构里 preview_url 优先于 url', () => {
    const out = normalizeResourceItem({
      type: 'image_url',
      image_url: { url: 'https://x/raw', preview_url: 'https://x/thumb', file_name: 'a.png' },
    });
    expect(out?.url).toBe('https://x/thumb');
  });

  it.each(['file_url', 'audio_url', 'video_url'])('解析 %s 嵌套结构', type => {
    const out = normalizeResourceItem({
      type,
      [type]: { url: 'https://x/f', file_name: `f.${type.replace('_url', '')}` },
    });
    expect(out?.url).toBe('https://x/f');
  });

  it('解析旧格式（file_name + file_path）', () => {
    const out = normalizeResourceItem({
      file_name: 'old.txt',
      file_path: '/uploads/old.txt',
    });
    expect(out).toMatchObject({ file_name: 'old.txt', url: '/uploads/old.txt' });
  });

  it('嵌套结构缺失时回退到平铺字段', () => {
    // type 标了 image_url 但没有 image_url 字段 —— 不应抛错，应回退平铺
    const out = normalizeResourceItem({ type: 'image_url', url: 'https://x/b.png', name: 'b.png' });
    expect(out).toMatchObject({ file_name: 'b.png', url: 'https://x/b.png' });
  });

  it('文件名缺失时兜底为「未命名文件」而不是空串', () => {
    const out = normalizeResourceItem({ url: 'https://x/c' });
    expect(out?.file_name).toBe('未命名文件');
  });

  it('图片扩展名推断 mime，非图片不推断', () => {
    expect(normalizeResourceItem({ url: 'https://x/a.JPG', name: 'a.JPG' })?.mime_type).toBe(
      'image/*'
    );
    expect(normalizeResourceItem({ url: 'https://x/a.pdf', name: 'a.pdf' })?.mime_type).toBeUndefined();
  });

  it('显式 mime_type 优先于扩展名推断', () => {
    const out = normalizeResourceItem({
      url: 'https://x/a.png',
      name: 'a.png',
      mime_type: 'image/webp',
    });
    expect(out?.mime_type).toBe('image/webp');
  });

  it('file_size 仅在为数字时透传', () => {
    expect(normalizeResourceItem({ url: 'u', name: 'n', file_size: 12 })?.file_size).toBe(12);
    expect(normalizeResourceItem({ url: 'u', name: 'n', file_size: 'x' })?.file_size).toBeUndefined();
  });

  // 注意 gyra-fs:// 的结构：<scheme>://<host>/<bucket>/<fileId>
  // 主机名也会被算进 path 分段，所以必须是三段而不是两段
  it('gyra-fs:// 协议会被转换（预览器不认这个协议）', () => {
    const out = normalizeResourceItem({
      url: 'gyra-fs://storage/bucket/file-id',
      name: 'a.png',
    });
    expect(out?.url).toContain('/api/v2/serve/file/files/bucket/file-id');
  });

  it('gyra-fs:// 分段不足时原样返回，不产出坏 URL', () => {
    const out = normalizeResourceItem({ url: 'gyra-fs://only-one', name: 'a.png' });
    expect(out?.url).toBe('gyra-fs://only-one');
  });
});

describe('normalizeUploadingFile', () => {
  it('带上 File 本体，预览时走 objectURL（上传中也能看）', () => {
    const file = makeFile();
    const out = normalizeUploadingFile(file);
    expect(out?.local_file).toBe(file);
    expect(out?.file_name).toBe('a.png');
    expect(out?.mime_type).toBe('image/png');
  });

  it('空输入返回 null，不抛错', () => {
    expect(normalizeUploadingFile(null as unknown as File)).toBeNull();
  });
});

describe('makePreviewPayload', () => {
  it('空名字兜底、空 url 不生成', () => {
    expect(makePreviewPayload('', 'https://x/a').file_name).toBe('未命名文件');
    expect(makePreviewPayload('a', '').url).toBeUndefined();
  });

  it('透传 mimeType 与 size', () => {
    expect(makePreviewPayload('a.pdf', 'https://x/a', { mimeType: 'application/pdf', size: 99 })).toEqual({
      file_name: 'a.pdf',
      url: 'https://x/a',
      mime_type: 'application/pdf',
      file_size: 99,
    });
  });
});

describe('openAttachmentPreview 广播', () => {
  it('无宿主时不抛错（消息流可能先于宿主挂载渲染）', () => {
    expect(() => openAttachmentPreview(makePreviewPayload('a', 'https://x/a'))).not.toThrow();
    expect(() => openAttachmentPreview(null)).not.toThrow();
  });

  it('宿主收到广播并打开弹窗，关闭后卸载', async () => {
    const { unmount } = render(<AttachmentPreviewHost />);
    expect(screen.queryByTestId('preview-modal')).not.toBeInTheDocument();

    act(() => {
      openAttachmentPreview(makePreviewPayload('photo.png', 'https://x/photo.png'));
    });
    expect(screen.getByTestId('preview-modal')).toHaveTextContent('photo.png');

    unmount();
  });

  it('多个宿主同时挂载时都会收到（广播语义）', () => {
    render(<AttachmentPreviewHost />);
    render(<AttachmentPreviewHost />);
    act(() => {
      openAttachmentPreview(makePreviewPayload('shared.png', 'https://x/s.png'));
    });
    expect(screen.getAllByTestId('preview-modal')).toHaveLength(2);
  });
});

describe('useAttachmentPreview', () => {
  // hook 只负责广播，必须有宿主挂载才能观察到效果
  beforeEach(() => {
    render(<AttachmentPreviewHost />);
  });

  it('openResource 归一化后广播', () => {
    const { result } = renderHook(() => useAttachmentPreview());
    act(() => {
      result.current.openResource({ type: 'image_url', image_url: { url: 'https://x/r.png', file_name: 'r.png' } });
    });
    expect(screen.getByTestId('preview-modal')).toHaveTextContent('r.png');
  });

  it('openLocalFile 走本地文件通道', () => {
    const { result } = renderHook(() => useAttachmentPreview());
    act(() => {
      result.current.openLocalFile(makeFile('local.png'));
    });
    expect(screen.getByTestId('preview-modal')).toHaveTextContent('local.png');
  });

  it('脏数据不触发弹窗（避免点空白区域弹个空窗）', () => {
    const { result } = renderHook(() => useAttachmentPreview());
    act(() => {
      result.current.openResource({});
    });
    expect(screen.queryByTestId('preview-modal')).not.toBeInTheDocument();
  });
});

describe('useObjectUrl / LocalFileThumb', () => {
  // 修复前的写法是 URL.createObjectURL 内联进 <img src>，每次 render 新建且从不 revoke
  const createSpy = jest.fn(() => 'blob:mock-url');
  const revokeSpy = jest.fn();

  beforeAll(() => {
    Object.defineProperty(URL, 'createObjectURL', { writable: true, value: createSpy });
    Object.defineProperty(URL, 'revokeObjectURL', { writable: true, value: revokeSpy });
  });

  beforeEach(() => {
    createSpy.mockClear();
    revokeSpy.mockClear();
  });

  // File 引用必须稳定：放在 render 回调里每次 render 都会新建一个 File，
  // 导致 effect 依赖漂移、反复 create/revoke（见下方专门记录该行为的用例）
  it('挂载时为 File 创建 objectURL', () => {
    const file = makeFile();
    const { result } = renderHook(() => useObjectUrl(file));
    expect(result.current).toBe('blob:mock-url');
    expect(createSpy).toHaveBeenCalledWith(file);
    expect(createSpy).toHaveBeenCalledTimes(1);
  });

  it('卸载时 revoke，不泄漏', () => {
    const file = makeFile();
    const { unmount } = renderHook(() => useObjectUrl(file));
    expect(revokeSpy).not.toHaveBeenCalled();
    unmount();
    expect(revokeSpy).toHaveBeenCalledTimes(1);
  });

  it('切换文件时先 revoke 旧的', () => {
    const first = makeFile('1.png');
    const second = makeFile('2.png');
    const { rerender } = renderHook(({ f }) => useObjectUrl(f), {
      initialProps: { f: first as File | null },
    });
    rerender({ f: second });
    expect(revokeSpy).toHaveBeenCalledTimes(1);
    expect(createSpy).toHaveBeenCalledTimes(2);
  });

  it('引用不稳定时会反复 create/revoke（调用方须传稳定 File）', () => {
    // 记录现状，防止有人误以为 useObjectUrl 内部做了引用无关的缓存。
    // 输入框场景的 File 来自 state，引用天然稳定，不受影响。
    renderHook(() => useObjectUrl(makeFile()));
    expect(createSpy.mock.calls.length).toBeGreaterThan(1);
    expect(revokeSpy.mock.calls.length).toBeGreaterThan(0);
  });

  it('file 为 null 时不创建也不报错', () => {
    const { result } = renderHook(() => useObjectUrl(null));
    expect(result.current).toBeNull();
    expect(createSpy).not.toHaveBeenCalled();
  });

  it('LocalFileThumb 渲染出带 alt 的 img', () => {
    render(<LocalFileThumb file={makeFile('thumb.png')} className="cls" />);
    const img = screen.getByAltText('thumb.png');
    expect(img).toHaveAttribute('src', 'blob:mock-url');
    expect(img).toHaveClass('cls');
  });

  it('LocalFileThumb 支持自定义 alt', () => {
    render(<LocalFileThumb file={makeFile('thumb.png')} alt="自定义" />);
    expect(screen.getByAltText('自定义')).toBeInTheDocument();
  });
});
