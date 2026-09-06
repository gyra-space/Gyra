import React, { FC, useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { Modal, Typography, Tabs, Button, ConfigProvider, Tooltip } from 'antd';
import {
  CodeOutlined,
  EyeOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
  DownloadOutlined,
  FileTextOutlined,
  CloseOutlined,
  FormatPainterOutlined,
} from '@ant-design/icons';
import { CodePreview } from '../../code-preview';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { GPTVis } from '@antv/gpt-vis';
import { injectLocalLibsForReport, resolveFileDownloadUrl, safeApiBase, transformFileUrl } from '@/utils';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import ZoomableImage from './ZoomableImage';
import {
  FILE_TYPES,
  getFileType,
  getLanguage,
  getFileTypeIcon,
  isBinaryContent,
  type FileType,
} from './file-types';
import { formatFileSize } from '../VisDAttach/utils';
import styles from './FilePreviewModal.module.css';

const { Text } = Typography;

export interface PreviewFilePayload {
  file_name: string;
  file_type?: string;
  object_path?: string;
  oss_url?: string;
  preview_url?: string;
  mime_type?: string;
  /** 本地文件（上传中或尚未上传），存在时优先于所有远程 URL */
  local_file?: File | null;
  /** 可直接访问的远程 URL（输入框附件场景） */
  url?: string;
  /** 字节数，仅用于 header 展示 */
  file_size?: number;
}

interface FilePreviewModalProps {
  visible: boolean;
  file: PreviewFilePayload | null;
  onClose: () => void;
}

const FilePreviewModal: FC<FilePreviewModalProps> = ({ visible, file, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [content, setContent] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [urlIndex, setUrlIndex] = useState(0);
  const [localUrl, setLocalUrl] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [activeTab, setActiveTab] = useState<'preview' | 'code'>('preview');
  const [animating, setAnimating] = useState(false);
  const [closing, setClosing] = useState(false);
  const [shouldRender, setShouldRender] = useState(false);
  const [jsonFormatted, setJsonFormatted] = useState(true);
  // 扩展名/mime 都认不出来的漏网二进制，按内容二次判定后改显"不支持预览"
  const [binaryDetected, setBinaryDetected] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const localFile = file?.local_file ?? null;

  // 关闭时父组件通常立即把 file 置空，但弹窗还有 250ms 退场动画。
  // 记住最后一份非空 payload，避免动画期间内容/尺寸闪变成空壳。
  const lastFileRef = useRef<PreviewFilePayload | null>(null);
  if (file) lastFileRef.current = file;
  const activeFile = file ?? lastFileRef.current;

  useEffect(() => {
    if (!shouldRender) lastFileRef.current = null;
  }, [shouldRender]);

  const fileType = useMemo<FileType>(() => {
    if (!activeFile) return FILE_TYPES.UNKNOWN;
    return getFileType(activeFile.file_name, activeFile.mime_type || localFile?.type);
  }, [activeFile, localFile]);

  const needsTextContent =
    fileType === FILE_TYPES.HTML ||
    fileType === FILE_TYPES.MARKDOWN ||
    fileType === FILE_TYPES.CODE ||
    fileType === FILE_TYPES.TEXT;

  // gyra-fs:// 走 /files/preview（支持 inline）；object_path 走 legacy 接口；其余按原样/拼 apiBase
  const buildPreviewUrl = (fileUri: string): string => {
    const apiBaseUrl = safeApiBase();
    if (fileUri.startsWith('gyra-fs://')) {
      return transformFileUrl(
        `${apiBaseUrl}/api/v2/serve/file/files/preview?uri=${encodeURIComponent(fileUri)}`
      );
    }
    if (fileUri.startsWith('/')) {
      return `${apiBaseUrl}${fileUri}`;
    }
    // Absolute URLs may embed a non-routable bind address (e.g. http://172.22.x.x)
    // that the browser blocks as mixed content behind an HTTPS reverse proxy.
    // Rewrite them to a same-origin (relative) URL via transformFileUrl.
    return transformFileUrl(fileUri);
  };

  const buildObjectPathUrl = (objectPath: string): string => {
    const apiBaseUrl = safeApiBase();
    return transformFileUrl(
      `${apiBaseUrl}/api/oss/getFileByFileName?fileName=${encodeURIComponent(objectPath)}`
    );
  };

  /** 远程候选 URL，按优先级排列；前一个加载失败时自动顺延到下一个 */
  const remoteCandidates = useMemo(() => {
    if (!file) return [] as string[];
    const list: string[] = [];
    if (file.oss_url) list.push(buildPreviewUrl(file.oss_url));
    if (file.object_path) list.push(buildObjectPathUrl(file.object_path));
    if (file.url) list.push(buildPreviewUrl(file.url));
    if (file.preview_url) list.push(buildPreviewUrl(file.preview_url));
    return Array.from(new Set(list));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [file?.oss_url, file?.object_path, file?.url, file?.preview_url]);

  // 本地文件：创建 objectURL 并在关闭/切换时释放，避免内存泄漏
  useEffect(() => {
    if (!visible || !localFile) {
      setLocalUrl(null);
      return;
    }
    const url = URL.createObjectURL(localFile);
    setLocalUrl(url);
    return () => {
      URL.revokeObjectURL(url);
      setLocalUrl(null);
    };
  }, [visible, localFile]);

  const candidates = useMemo(
    () => (localUrl ? [localUrl] : remoteCandidates),
    [localUrl, remoteCandidates]
  );

  const resolvedUrl = candidates[Math.min(urlIndex, Math.max(candidates.length - 1, 0))] || '';

  useEffect(() => {
    setUrlIndex(0);
  }, [file, visible, localUrl]);

  /** 图片/PDF/视频加载失败时顺延下一个候选；全部失败则提示 */
  const handleUrlError = useCallback(() => {
    if (urlIndex < candidates.length - 1) {
      setUrlIndex(urlIndex + 1);
    } else {
      setError('文件加载失败，请检查链接或稍后重试');
    }
  }, [urlIndex, candidates.length]);

  // 拉取文本内容（markdown / code / text / html）。本地文件走 FileReader。
  useEffect(() => {
    if (!visible || !file) {
      setContent('');
      setError('');
      setBinaryDetected(false);
      setLoading(false);
      return;
    }
    if (!needsTextContent) return;

    let cancelled = false;

    /** 统一写入文本内容，顺带按内容兜底识别二进制（见 isBinaryContent） */
    const applyText = (text: string) => {
      if (cancelled) return;
      setContent(text);
      setBinaryDetected(isBinaryContent(text));
    };

    const readLocalText = (target: File) =>
      new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result ?? ''));
        reader.onerror = () => reject(new Error('读取本地文件失败'));
        reader.readAsText(target);
      });

    const run = async () => {
      setLoading(true);
      setError('');

      if (localFile) {
        try {
          const text = await readLocalText(localFile);
          applyText(text);
        } catch (err) {
          if (!cancelled) setError(err instanceof Error ? err.message : '读取本地文件失败');
        } finally {
          if (!cancelled) setLoading(false);
        }
        return;
      }

      if (candidates.length === 0) {
        if (!cancelled) {
          setError('无可用的文件地址');
          setLoading(false);
        }
        return;
      }

      let lastError = '';
      try {
        for (const url of candidates) {
          try {
            const response = await fetch(url);
            if (!response.ok) {
              lastError = `HTTP ${response.status}`;
              continue;
            }
            const text = await response.text();
            applyText(text);
            return;
          } catch (err) {
            lastError = err instanceof Error ? err.message : '网络错误';
          }
        }

        if (!cancelled) {
          setError(`无法读取文件内容${lastError ? `（${lastError}）` : ''}`);
        }
      } finally {
        // 成功路径此前是裸 return，漏了收尾 —— 远程文本内容会永久停在"加载中"。
        // 放在 finally 里，成功/失败/异常三条路径都能收尾。
        if (!cancelled) setLoading(false);
      }
    };

    run();

    return () => {
      cancelled = true;
      setLoading(false);
    };
  }, [visible, file, localFile, needsTextContent, candidates]);

  const parsedHtmlContent = useMemo(() => {
    if (!content || fileType !== FILE_TYPES.HTML) return '';

    if (content.includes('<!DOCTYPE') || content.includes('<html')) {
      return content;
    }

    return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      line-height: 1.6;
      padding: 24px;
      margin: 0;
      color: #1e293b;
      background: #ffffff;
    }
    pre, code {
      background: #f1f5f9;
      padding: 2px 6px;
      border-radius: 4px;
      font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
    }
    pre { padding: 16px; overflow-x: auto; }
    a { color: #6366f1; }
    img { max-width: 100%; height: auto; border-radius: 8px; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #e2e8f0; padding: 8px 12px; }
    th { background: #f8fafc; }
  </style>
</head>
<body>
${content}
</body>
</html>`;
  }, [content, fileType]);

  const toggleFullscreen = () => {
    if (!iframeRef.current) return;

    if (!isFullscreen) {
      iframeRef.current.requestFullscreen?.();
    } else {
      document.exitFullscreen?.();
    }
  };

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  useEffect(() => {
    if (visible && !shouldRender) {
      setShouldRender(true);
      setClosing(false);
    }
  }, [visible, shouldRender]);

  useEffect(() => {
    if (shouldRender && !animating && !closing) {
      const timer = setTimeout(() => {
        setAnimating(true);
      }, 30);
      return () => clearTimeout(timer);
    }
  }, [shouldRender, animating, closing]);

  const handleClose = useCallback(() => {
    setClosing(true);
    setAnimating(false);
    setTimeout(() => {
      setShouldRender(false);
      setClosing(false);
      setContent('');
      setError('');
      setBinaryDetected(false);
      setUrlIndex(0);
      setIsFullscreen(false);
      setActiveTab('preview');
      onClose();
    }, 250);
  }, [onClose]);

  useEffect(() => {
    if (!visible && shouldRender && animating && !closing) {
      handleClose();
    }
  }, [visible, shouldRender, animating, closing, handleClose]);

  const handleDownload = () => {
    if (!activeFile) return;
    const anchor = document.createElement('a');
    anchor.href = resolveFileDownloadUrl(resolvedUrl || candidates[0] || '');
    anchor.download = activeFile.file_name || 'download';
    anchor.rel = 'noreferrer';
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
  };

  const handleDownloadHtml = () => {
    if (!content) return;
    const blob = new Blob([parsedHtmlContent], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = activeFile?.file_name || 'preview.html';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const renderLoadingState = () => (
    <div className={styles.loadingContainer}>
      <div className={styles.loadingContent}>
        <div className={styles.loadingIcon}>
          <FileTextOutlined />
        </div>
        <div className={styles.loadingText}>加载中...</div>
        <div className={styles.loadingProgress}>
          <div className={styles.loadingBar} />
        </div>
      </div>
    </div>
  );

  /** 二进制 / 不支持预览的类型：给下载出口，别让用户对着一屏乱码 */
  const renderUnsupported = () => (
    <div className={styles.unsupportedContainer}>
      <div className={styles.unsupportedIcon}>{getFileTypeIcon(FILE_TYPES.UNKNOWN)}</div>
      <Text strong className={styles.unsupportedTitle}>
        该文件格式暂不支持在线预览
      </Text>
      <Text type="secondary" className={styles.unsupportedHint}>
        {activeFile?.file_name || '当前文件'} 为二进制格式，可下载后用本地应用打开
      </Text>
      <Button
        type="primary"
        icon={<DownloadOutlined />}
        onClick={handleDownload}
        disabled={!candidates.length}
        className={styles.unsupportedButton}
      >
        下载文件
      </Button>
    </div>
  );

  const renderContent = () => {
    if (!activeFile) return null;

    // 不支持预览的两种情况在这里一次性拦掉，所以下面的 switch 里没有 UNKNOWN 分支
    // （否则 TS 会因类型收窄报「unknown 不可比较」，那是个死分支）：
    //   1. 扩展名/mime 判定为二进制
    //   2. 判定为文本，但读出来的内容经嗅探仍是二进制（漏网之鱼）
    if (fileType === FILE_TYPES.UNKNOWN || binaryDetected) return renderUnsupported();

    if (error) {
      return (
        <div className={styles.errorContainer}>
          <div className={styles.errorIcon}>⚠️</div>
          <Text type="danger">{error}</Text>
          {resolvedUrl && (
            <a className={styles.errorLink} href={resolvedUrl} target="_blank" rel="noreferrer">
              在新窗口打开
            </a>
          )}
        </div>
      );
    }

    if (loading) {
      return renderLoadingState();
    }

    switch (fileType) {
      case FILE_TYPES.IMAGE: {
        if (!resolvedUrl) return null;
        return (
          <ZoomableImage
            key={resolvedUrl}
            src={resolvedUrl}
            alt={activeFile.file_name}
            onError={handleUrlError}
          />
        );
      }

      case FILE_TYPES.PDF: {
        if (!resolvedUrl) return null;
        return (
          <div className={styles.pdfContainer}>
            <iframe
              key={resolvedUrl}
              src={resolvedUrl}
              className={styles.pdfFrame}
              title={activeFile.file_name || 'PDF Preview'}
              onError={handleUrlError}
            />
          </div>
        );
      }

      case FILE_TYPES.VIDEO: {
        if (!resolvedUrl) return null;
        return (
          <div className={styles.imageContainer}>
            <video
              key={resolvedUrl}
              src={resolvedUrl}
              controls
              autoPlay
              className={styles.previewVideo}
              onError={handleUrlError}
            />
          </div>
        );
      }

      case FILE_TYPES.HTML: {
        const htmlTabItems = [
          {
            key: 'preview',
            label: (
              <span className={styles.tabLabel}>
                <EyeOutlined /> 预览
              </span>
            ),
            children: content ? (
              <div className={styles.htmlPreviewContainer}>
                <iframe
                  ref={iframeRef}
                  srcDoc={injectLocalLibsForReport(parsedHtmlContent)}
                  className={styles.htmlPreviewFrame}
                  sandbox="allow-scripts allow-same-origin"
                  title="HTML Preview"
                />
                <div className={styles.htmlActions}>
                  <Button
                    size="small"
                    icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
                    onClick={toggleFullscreen}
                    className={styles.actionButton}
                  >
                    {isFullscreen ? '退出全屏' : '全屏'}
                  </Button>
                  <Button
                    size="small"
                    icon={<DownloadOutlined />}
                    onClick={handleDownloadHtml}
                    className={styles.actionButton}
                  >
                    下载
                  </Button>
                </div>
              </div>
            ) : (
              <div className={styles.htmlPreviewContainer}>
                <iframe
                  src={resolvedUrl}
                  className={styles.htmlPreviewFrame}
                  sandbox="allow-scripts allow-same-origin"
                  title="HTML Preview"
                />
              </div>
            ),
          },
          {
            key: 'code',
            label: (
              <span className={styles.tabLabel}>
                <CodeOutlined /> 源码
              </span>
            ),
            children: (
              <div className={styles.codeContainer}>
                <CodePreview code={content} language="html" />
              </div>
            ),
          },
        ];

        return (
          <Tabs
            activeKey={activeTab}
            onChange={(key) => setActiveTab(key as 'preview' | 'code')}
            items={htmlTabItems}
            className={styles.previewTabs}
          />
        );
      }

      case FILE_TYPES.MARKDOWN:
        return (
          <div className={styles.markdownContainer}>
            <GPTVis
              remarkPlugins={[remarkGfm, remarkMath]}
              rehypePlugins={[rehypeRaw, rehypeKatex]}
            >
              {content}
            </GPTVis>
          </div>
        );

      case FILE_TYPES.CODE:
      case FILE_TYPES.TEXT:
      default: {
        const lang = getLanguage(activeFile.file_name);
        let isJson = false;
        let formattedContent = content;
        if (lang === 'json' || lang === 'text') {
          try {
            const parsed = JSON.parse(content);
            formattedContent = JSON.stringify(parsed, null, 2);
            isJson = true;
          } catch {
            // 不是合法 JSON，按原文展示
          }
        }
        const displayContent = isJson && jsonFormatted ? formattedContent : content;
        const displayLang = isJson ? 'json' : lang;

        return (
          <div>
            <div className={styles.codeToolbar}>
              {isJson && (
                <Tooltip title={jsonFormatted ? '显示原始内容' : '格式化 JSON'}>
                  <Button
                    type="text"
                    size="small"
                    icon={<FormatPainterOutlined />}
                    onClick={() => setJsonFormatted(!jsonFormatted)}
                    className={`${styles.toolbarBtn} ${jsonFormatted ? styles.toolbarBtnActive : ''}`}
                  >
                    格式化
                  </Button>
                </Tooltip>
              )}
            </div>
            <CodePreview
              code={displayContent}
              language={displayLang}
              light={oneLight}
            />
          </div>
        );
      }
    }
  };

  const sizeText = activeFile?.file_size ?? localFile?.size;

  return (
    <ConfigProvider
      theme={{
        token: {
          borderRadiusLG: 12,
        },
      }}
    >
      <Modal
        open={shouldRender}
        onCancel={handleClose}
        width={
          fileType === FILE_TYPES.IMAGE ||
          fileType === FILE_TYPES.HTML ||
          fileType === FILE_TYPES.VIDEO ||
          fileType === FILE_TYPES.PDF
            ? '90%'
            : 900
        }
        footer={null}
        destroyOnClose
        closable={false}
        className={styles.previewModal}
        centered
        maskClosable
        transitionName=""
        maskTransitionName=""
      >
        <div
          className={`${styles.modalWrapper} ${animating ? styles.animateIn : ''} ${
            closing ? styles.animateOut : ''
          }`}
        >
          <div className={styles.modalHeader}>
            <div className={styles.headerLeft}>
              <span className={styles.fileIconWrap}>{getFileTypeIcon(fileType)}</span>
              <div className={styles.headerInfo}>
                <Text strong className={styles.fileName}>
                  {activeFile?.file_name || '文件预览'}
                </Text>
                <Text type="secondary" className={styles.fileType}>
                  {[activeFile?.file_type, sizeText != null ? formatFileSize(sizeText) : null]
                    .filter(Boolean)
                    .join(' · ')}
                </Text>
              </div>
            </div>
            <div className={styles.headerRight}>
              <Tooltip title={localFile ? '下载本地文件' : '下载'}>
                <Button
                  type="text"
                  icon={<DownloadOutlined />}
                  onClick={handleDownload}
                  disabled={!candidates.length}
                  className={styles.closeButton}
                />
              </Tooltip>
              <Button
                type="text"
                icon={<CloseOutlined />}
                onClick={handleClose}
                className={styles.closeButton}
              />
            </div>
          </div>

          <div className={styles.modalBody}>{renderContent()}</div>
        </div>
      </Modal>
    </ConfigProvider>
  );
};

export { FILE_TYPES, getFileType, getLanguage } from './file-types';
export type { FileType } from './file-types';
export default FilePreviewModal;
