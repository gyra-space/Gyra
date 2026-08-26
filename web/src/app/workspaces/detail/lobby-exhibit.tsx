'use client';

/**
 * 大厅通用入驻内容渲染器(Lobby Exhibit Host)。
 *
 * 大厅容器是通用 Exhibit 宿主:任何内容(图片/视频/音频/表格/PPT/HTML/
 * PDF/Markdown/Code/Chart/JSON/文件)都抽象为 LobbyExhibit 描述符,
 * 这里按 kind 分发到对应渲染器。新增内容类型 = 加一个渲染器 + 注册进
 * EXHIBIT_RENDERERS,协议本身不变。
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { App, Button, Table, Tabs, Tag, Tooltip } from 'antd';
// xlsx 浏览器端解析(v9 走 Web Worker 后台解析,不阻塞 UI;旧版 xls 不支持,仍引导下载)
import readXlsxFile from 'read-excel-file/browser';
import {
  DownloadOutlined,
  ExportOutlined,
  FileOutlined,
  FilePdfOutlined,
  LoadingOutlined,
  PrinterOutlined,
  ShareAltOutlined,
} from '@ant-design/icons';
import MarkdownIt from 'markdown-it';
import { GPTVis } from '@antv/gpt-vis';
import html2canvas from 'html2canvas';
import { jsPDF } from 'jspdf';
import markdownComponents, { markdownPlugins, preprocessLaTeX } from '@/components/chat/chat-content-components/config';
import { GET, apiInterceptors } from '@/client/api';
import { createAppCard } from '@/client/api/app-card';
import { injectLocalLibsForReport, resolveFileDownloadUrl, transformFileUrl } from '@/utils';
import type { LobbyExhibit } from './agent-workspace-types';
import { isAppCardPayloadText, extractAppCardPayload } from './app-card/AppCardImportButton';
import './app-card/app-card.css';

/* ═══════════════════════════════════════════════════════════════
   公共辅助
   ═══════════════════════════════════════════════════════════════ */

/** 将 agent_files 直接下载路径路由到 preview 端点。
 * 直接下载端点(/files/agent_files/{id})恒返回 octet-stream+attachment,iframe 无法内联渲染
 * HTML 等可预览类型;preview 端点按文件名推断 MIME,对 text/html 等返回 inline 使其可渲染
 * (与对话侧交付文件预览行为保持一致)。 */
export function resolveAgentFilePreviewUrl(raw: string): string {
  const m = raw.match(/\/api\/v2\/serve\/file\/files\/agent_files\/([^?#]+)/);
  if (!m) return '';
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || '';
  return `${apiBaseUrl}/api/v2/serve/file/files/preview?bucket=agent_files&file_id=${encodeURIComponent(m[1])}`;
}

/** 解析 Exhibit 来源为可访问 URL(inline 内容无 URL,返回 '') */
export function resolveExhibitUrl(exhibit: LobbyExhibit): string {
  const { uri, url } = exhibit.source;
  const raw = url || uri || '';
  if (!raw) return '';
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || '';
  if (raw.startsWith('gyra-fs://')) {
    return `${apiBaseUrl}/api/v2/serve/file/files/preview?uri=${encodeURIComponent(raw)}`;
  }
  // agent_files 直接下载路径 → 走 preview 端点(返回 inline,HTML 可内联渲染)
  const agentFilePreview = resolveAgentFilePreviewUrl(raw);
  if (agentFilePreview) return agentFilePreview;
  // 普通下载端点 /files/{bucket}/{file_id}(返回 attachment)→ 转 preview 端点
  // (返回 inline,iframe 才能内联展示 html/图片/PDF 等可预览类型)
  const dl = raw.match(/\/serve\/file\/files\/([^/?#]+)\/([^/?#]+)/);
  if (dl) {
    return `${apiBaseUrl}/api/v2/serve/file/files/preview?bucket=${encodeURIComponent(dl[1])}&file_id=${encodeURIComponent(dl[2])}`;
  }
  if (raw.startsWith('/')) return `${apiBaseUrl}${raw}`;
  return transformFileUrl(raw);
}

/** 解析 Exhibit 的真实下载地址:落到 attachment 下载端点而非 inline 预览端点。
 * 预览端点对 text/html 等返回 inline,浏览器只会"打开"而不会保存文件,
 * 因此下载必须使用 /files/{bucket}/{file_id}(返回 attachment)。 */
export function resolveExhibitDownloadUrl(exhibit: LobbyExhibit): string {
  const { uri, url } = exhibit.source;
  const raw = url || uri || '';
  if (!raw) return '';
  return resolveFileDownloadUrl(raw);
}

/** 解析 Exhibit 的内部文件 URI(供 /files/public_url 生成公开分享链接) */
function resolveExhibitUri(exhibit: LobbyExhibit): string {
  const { uri, url } = exhibit.source;
  if (uri) return uri;
  if (!url) return '';
  if (url.startsWith('gyra-fs://')) return url;
  const m = url.match(/[?&]uri=([^&]+)/);
  return m ? decodeURIComponent(m[1]) : '';
}

function fmtSize(bytes?: number): string {
  if (!bytes) return '';
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${bytes} B`;
}

function downloadFile(url: string, fileName: string) {
  const a = document.createElement('a');
  a.href = url;
  a.download = fileName || 'download';
  a.style.display = 'none';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

/* ═══════════════════════════════════════════════════════════════
   打印 / 导出 PDF:源文本 → 干净排版文档 → 隐藏 iframe 打印
   (浏览器打印对话框中选择"另存为 PDF"即导出;iframe 标题即默认文件名)
   ═══════════════════════════════════════════════════════════════ */

const mdIt = new MarkdownIt({ html: false, linkify: true, breaks: false });

/** 导出文档排版样式(GitHub 风,打印友好) */
const DOC_STYLES = `
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    font-size: 15px; line-height: 1.7; color: #1f2328; padding: 40px; max-width: 860px; margin: 0 auto; }
  h1, h2 { font-weight: 600; line-height: 1.3; margin: 24px 0 12px; padding-bottom: 6px; border-bottom: 1px solid #d0d7de; }
  h1 { font-size: 28px; } h2 { font-size: 22px; } h3 { font-size: 18px; margin: 20px 0 10px; }
  p { margin: 0 0 14px; }
  code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 13px;
    padding: 2px 6px; background: rgba(175,184,193,.2); border-radius: 6px; }
  pre { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 13px;
    padding: 14px; overflow-x: auto; background: #f6f8fa; border-radius: 8px; margin: 0 0 14px; }
  pre code { background: transparent; padding: 0; }
  blockquote { margin: 0 0 14px; padding: 0 14px; border-left: 3px solid #d0d7de; color: #57606a; }
  ul, ol { margin: 0 0 14px; padding-left: 28px; }
  table { border-collapse: collapse; margin: 0 0 14px; width: 100%; }
  table th, table td { padding: 6px 12px; border: 1px solid #d0d7de; }
  table th { background: #f6f8fa; font-weight: 600; }
  img { max-width: 100%; }
  hr { border: 0; border-top: 1px solid #d0d7de; margin: 20px 0; }
  @media print { body { padding: 16px; } pre { white-space: pre-wrap; } h1, h2, h3 { page-break-after: avoid; } }
`;

/** 源文本按 kind 渲染为可打印 HTML 文档 */
function renderExhibitDoc(kind: LobbyExhibit['kind'], raw: string, title: string): string {
  let body: string;
  if (kind === 'markdown') {
    body = mdIt.render(raw);
  } else if (kind === 'data' || kind === 'chart') {
    let pretty = raw;
    try { pretty = JSON.stringify(JSON.parse(raw), null, 2); } catch { /* 原样 */ }
    body = `<pre><code>${mdIt.utils.escapeHtml(pretty)}</code></pre>`;
  } else {
    // text / code 等:等宽预排
    body = `<pre><code>${mdIt.utils.escapeHtml(raw)}</code></pre>`;
  }
  return `<!doctype html><html><head><meta charset="utf-8"><title>${mdIt.utils.escapeHtml(title)}</title><style>${DOC_STYLES}</style></head><body>${body}</body></html>`;
}

/** 隐藏 iframe 加载文档并触发其打印对话框 */
function printHtmlDocument(html: string) {
  const iframe = document.createElement('iframe');
  iframe.style.position = 'fixed';
  iframe.style.right = '0';
  iframe.style.bottom = '0';
  iframe.style.width = '0';
  iframe.style.height = '0';
  iframe.style.border = '0';
  document.body.appendChild(iframe);
  const win = iframe.contentWindow;
  const doc = win?.document;
  if (!win || !doc) {
    document.body.removeChild(iframe);
    return;
  }
  doc.open();
  doc.write(html);
  doc.close();
  win.focus();
  setTimeout(() => {
    win.print();
    setTimeout(() => { try { document.body.removeChild(iframe); } catch { /* 已移除 */ } }, 1000);
  }, 250);
}

/** 所见即所得打印:仅打印指定容器内容(临时 print 样式表) */
function printElement(el: HTMLElement) {
  const printId = 'ws-exhibit-print-area';
  el.setAttribute('id', printId);
  const style = document.createElement('style');
  style.textContent = `
    @media print {
      body * { visibility: hidden !important; }
      #${printId}, #${printId} * { visibility: visible !important; overflow: visible !important; max-height: none !important; height: auto !important; }
      #${printId} { position: absolute; left: 0; top: 0; width: 100%; }
      html, body { height: auto !important; overflow: visible !important; }
    }
  `;
  document.head.appendChild(style);
  window.print();
  document.head.removeChild(style);
  el.removeAttribute('id');
}

function Markdown({ text }: { text: string }) {
  return (
    // @ts-ignore rehypePlugins type mismatch is pre-existing repo-wide (see chat-detail-content.tsx)
    <GPTVis components={markdownComponents} {...markdownPlugins}>
      {preprocessLaTeX(text)}
    </GPTVis>
  );
}

/** 远程拉取文本内容(inline 优先,无需拉取);skipFetch 用于二进制内容(如 xlsx)跳过文本拉取 */
function useExhibitText(exhibit: LobbyExhibit, skipFetch = false): { text: string | null; loading: boolean; error: string | null } {
  const inline = exhibit.source.inline;
  const url = useMemo(() => resolveExhibitUrl(exhibit), [exhibit]);
  const [text, setText] = useState<string | null>(inline ?? null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (inline != null) {
      setText(inline);
      return;
    }
    if (skipFetch || !url) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.text();
      })
      .then((t) => {
        if (!cancelled) setText(t);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [inline, url]);

  return { text, loading, error };
}

function FetchState({ loading, error, url }: { loading: boolean; error: string | null; url: string }) {
  if (loading) {
    return (
      <div className="ws-exhibit__state">
        <LoadingOutlined spin style={{ fontSize: 20 }} />
        <span>加载内容…</span>
      </div>
    );
  }
  if (error) {
    return (
      <div className="ws-exhibit__state">
        <span>加载失败: {error}</span>
        {url && (
          <a href={url} target="_blank" rel="noopener noreferrer" className="ws-renderer__download-btn">
            在新窗口打开
          </a>
        )}
      </div>
    );
  }
  return null;
}

/** 带加载态的 iframe 宿主:iframe 未触发 onLoad 前显示 loading,避免大页长时间空白 */
function IframeHost({
  src,
  srcDoc,
  sandbox,
  title,
  className,
  style,
}: {
  src?: string;
  srcDoc?: string;
  sandbox?: string;
  title: string;
  className?: string;
  style?: React.CSSProperties;
}) {
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    setLoaded(false);
  }, [src, srcDoc]);
  return (
    <div className="ws-exhibit__iframe-wrap">
      {!loaded && (
        <div className="ws-exhibit__iframe-loading">
          <LoadingOutlined spin style={{ fontSize: 20 }} />
          <span>加载内容…</span>
        </div>
      )}
      <iframe
        src={src}
        srcDoc={srcDoc}
        sandbox={sandbox}
        title={title}
        className={`${className ?? ''}${loaded ? '' : ' ws-exhibit__iframe--loading'}`}
        style={style}
        onLoad={() => setLoaded(true)}
      />
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   各 kind 渲染器
   ═══════════════════════════════════════════════════════════════ */

function ImageR({ exhibit }: { exhibit: LobbyExhibit }) {
  const [failed, setFailed] = useState(false);
  const url = resolveExhibitUrl(exhibit);
  // data URI / 内联 base64 也支持
  const src = url || exhibit.source.inline || '';
  if (!src || failed) {
    return <FetchState loading={false} error={failed ? '图片加载失败' : '无图片地址'} url={url} />;
  }
  return (
    <div className="ws-renderer__deliverable-image-wrap">
      <img
        src={src}
        alt={exhibit.title}
        className="ws-renderer__deliverable-image"
        onError={() => setFailed(true)}
      />
    </div>
  );
}

function VideoR({ exhibit }: { exhibit: LobbyExhibit }) {
  const [failed, setFailed] = useState(false);
  const url = resolveExhibitUrl(exhibit);
  if (!url || failed) {
    return <FetchState loading={false} error={failed ? '视频加载失败' : '无视频地址'} url={url} />;
  }
  return (
    <div className="ws-renderer__deliverable-video-wrap">
      {/* 不带 autoPlay:浏览器会拦截未静音自动播放 */}
      <video
        src={url}
        controls
        preload="metadata"
        className="ws-renderer__deliverable-video"
        onError={() => setFailed(true)}
      />
    </div>
  );
}

function AudioR({ exhibit }: { exhibit: LobbyExhibit }) {
  const [failed, setFailed] = useState(false);
  const url = resolveExhibitUrl(exhibit);
  if (!url || failed) {
    return <FetchState loading={false} error={failed ? '音频加载失败' : '无音频地址'} url={url} />;
  }
  return (
    <div className="ws-exhibit__audio">
      <audio src={url} controls preload="metadata" style={{ width: '100%' }} onError={() => setFailed(true)} />
    </div>
  );
}

function HtmlR({ exhibit }: { exhibit: LobbyExhibit }) {
  const url = resolveExhibitUrl(exhibit);
  const inline = exhibit.source.inline;
  const height = exhibit.render_hints?.height;
  const style = height ? { minHeight: height, height } : undefined;
  const [doc, setDoc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  // 非 inline 的远程报告:拉取内容、把外部 CDN 改写成本地库后经 srcdoc 渲染;
  // 拉取失败则回退为 iframe 原样加载,不改变既有行为。
  useEffect(() => {
    if (inline || !url) return;
    let cancelled = false;
    setDoc(null);
    setFailed(false);
    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.text();
      })
      .then((t) => {
        if (!cancelled) setDoc(injectLocalLibsForReport(t));
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [inline, url]);

  if (inline) {
    return (
      <IframeHost
        srcDoc={inline}
        sandbox="allow-same-origin"
        title={exhibit.title}
        className="ws-preview__html"
        style={height ? { minHeight: height } : undefined}
      />
    );
  }
  if (!url) return <FetchState loading={false} error="无页面地址" url="" />;
  if (doc != null) {
    return (
      <IframeHost
        srcDoc={doc}
        sandbox="allow-scripts allow-same-origin"
        title={exhibit.title}
        className="ws-renderer__deliverable-iframe"
        style={style}
      />
    );
  }
  // 拉取失败或已知无内容时,回退为 iframe 原样加载远程报告
  if (failed) {
    return (
      <IframeHost
        src={url}
        sandbox="allow-scripts allow-same-origin"
        title={exhibit.title}
        className="ws-renderer__deliverable-iframe"
        style={style}
      />
    );
  }
  return <FetchState loading error={null} url={url} />;
}

function PdfR({ exhibit }: { exhibit: LobbyExhibit }) {
  const url = resolveExhibitUrl(exhibit);
  if (!url) return <FetchState loading={false} error="无 PDF 地址" url="" />;
  return <IframeHost src={url} title={exhibit.title} className="ws-renderer__deliverable-iframe" />;
}

function MarkdownR({ exhibit }: { exhibit: LobbyExhibit }) {
  const { text, loading, error } = useExhibitText(exhibit);
  const url = resolveExhibitUrl(exhibit);
  if (loading || error) return <FetchState loading={loading} error={error} url={url} />;
  return (
    <div className="ws-preview__markdown">
      <Markdown text={text || ''} />
    </div>
  );
}

function CodeR({ exhibit }: { exhibit: LobbyExhibit }) {
  const { text, loading, error } = useExhibitText(exhibit);
  const url = resolveExhibitUrl(exhibit);
  if (loading || error) return <FetchState loading={loading} error={error} url={url} />;
  return (
    <div className="ws-renderer__code">
      <div className="ws-renderer__code-header">{exhibit.title}</div>
      <pre className="ws-renderer__code-pre">
        <code>{text || ''}</code>
      </pre>
    </div>
  );
}

function TextR({ exhibit }: { exhibit: LobbyExhibit }) {
  const { text, loading, error } = useExhibitText(exhibit);
  const url = resolveExhibitUrl(exhibit);
  if (loading || error) return <FetchState loading={loading} error={error} url={url} />;
  return (
    <div className="ws-renderer__text">
      <pre className="ws-renderer__text-pre">{text || ''}</pre>
    </div>
  );
}

/** 最小 CSV 解析(支持引号包裹与转义逗号) */
function parseCsv(text: string): Record<string, string>[] {
  const rows: string[][] = [];
  let field = '';
  let row: string[] = [];
  let inQuotes = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i += 1;
        } else {
          inQuotes = false;
        }
      } else {
        field += ch;
      }
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ',') {
      row.push(field);
      field = '';
    } else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && text[i + 1] === '\n') i += 1;
      row.push(field);
      field = '';
      if (row.some((c) => c !== '')) rows.push(row);
      row = [];
    } else {
      field += ch;
    }
  }
  row.push(field);
  if (row.some((c) => c !== '')) rows.push(row);
  if (rows.length < 2) return [];
  const headers = rows[0];
  return rows.slice(1).map((cells) => {
    const obj: Record<string, string> = {};
    headers.forEach((h, idx) => {
      obj[h || `col_${idx}`] = cells[idx] ?? '';
    });
    return obj;
  });
}

interface TableData {
  columns: { title: string; dataIndex: string; key: string }[];
  rows: Record<string, unknown>[];
}

/** 从 inline/url 文本解析表格数据:优先 JSON(对象数组),兜底 CSV */
function parseTableData(text: string, hints?: LobbyExhibit['render_hints']): TableData | null {
  const trimmed = text.trim();
  let rows: Record<string, unknown>[] = [];
  if (trimmed.startsWith('[')) {
    try {
      const arr = JSON.parse(trimmed);
      if (Array.isArray(arr) && arr.length && typeof arr[0] === 'object') {
        rows = arr;
      }
    } catch {
      // 非 JSON,走 CSV
    }
  }
  if (!rows.length) {
    rows = parseCsv(text);
  }
  if (!rows.length) return null;

  const hintCols = hints?.table?.columns;
  const columns = hintCols?.length
    ? hintCols.map((c) => ({ title: c.title || c.key, dataIndex: c.key, key: c.key }))
    : Object.keys(rows[0]).map((k) => ({ title: k, dataIndex: k, key: k }));
  return { columns, rows };
}

/** Excel 单元格值 → 显示文本(Date 格式化为本地日期时间) */
function cellText(v: unknown): string {
  if (v == null) return '';
  if (v instanceof Date) {
    return v.toLocaleString('zh-CN', { hour12: false });
  }
  return String(v);
}

/** xlsx 工作表数据 → TableData(首行作表头,列数按最宽行对齐) */
function xlsxSheetToTableData(rows: unknown[][]): TableData | null {
  if (!rows || !rows.length) return null;
  const width = rows.reduce((max, r) => Math.max(max, r.length), 0);
  const headers: string[] = [];
  for (let i = 0; i < width; i += 1) {
    headers.push(cellText(rows[0][i]) || `列 ${i + 1}`);
  }
  const body = rows.slice(1).map((cells) => {
    const obj: Record<string, string> = {};
    headers.forEach((h, idx) => {
      obj[h] = cellText(cells[idx]);
    });
    return obj;
  });
  return { columns: headers.map((h) => ({ title: h, dataIndex: h, key: h })), rows: body };
}

/** xlsx 二进制表格:ArrayBuffer 拉取 → 客户端解析 → 按 sheet 渲染 antd 表格 */
function XlsxR({ exhibit }: { exhibit: LobbyExhibit }) {
  const url = resolveExhibitUrl(exhibit);
  const [sheets, setSheets] = useState<{ name: string; data: TableData }[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!url) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.arrayBuffer();
      })
      .then((buf) => readXlsxFile(buf))
      .then((all) => {
        if (cancelled) return;
        const parsed: { name: string; data: TableData }[] = [];
        for (const s of all) {
          const data = xlsxSheetToTableData(s.data as unknown[][]);
          if (data) parsed.push({ name: s.sheet, data });
        }
        setSheets(parsed.length ? parsed : null);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : '解析失败');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [url]);

  if (loading) return <FetchState loading error={null} url={url} />;
  if (error) return <FetchState loading={false} error={`Excel 解析失败: ${error}`} url={url} />;
  if (!sheets) {
    return <FetchState loading={false} error="未解析到表格内容(文件可能为空或格式不受支持)" url={url} />;
  }
  const renderTable = (data: TableData) => (
    <Table
      columns={data.columns}
      dataSource={data.rows.map((r, i) => ({ key: i, ...r }))}
      size="small"
      pagination={data.rows.length > 20 ? { pageSize: 20, showSizeChanger: false } : false}
      scroll={{ x: true }}
    />
  );
  if (sheets.length === 1) {
    return <div className="ws-exhibit__table">{renderTable(sheets[0].data)}</div>;
  }
  return (
    <div className="ws-exhibit__table">
      <Tabs
        size="small"
        items={sheets.map((s) => ({ key: s.name, label: s.name, children: renderTable(s.data) }))}
      />
    </div>
  );
}

function TableR({ exhibit }: { exhibit: LobbyExhibit }) {
  const mime = (exhibit.source.mime_type || '').toLowerCase();
  // xlsx 等二进制表格无法纯前端解析:引导下载 / 新窗口预览
  const isBinarySheet =
    mime.includes('spreadsheet') || /\.(xlsx|xls|numbers)$/i.test(exhibit.title);
  // .xlsx 可客户端解析内联展示;旧版 .xls / .numbers 保持下载引导
  const isXlsxSheet =
    mime.includes('spreadsheetml') || /\.xlsx$/i.test(exhibit.title);
  const { text, loading, error } = useExhibitText(exhibit, isBinarySheet);
  const url = resolveExhibitUrl(exhibit);

  if (isBinarySheet && !exhibit.source.inline) {
    if (isXlsxSheet && url) {
      return <XlsxR exhibit={exhibit} />;
    }
    return (
      <div className="ws-exhibit__state">
        <span style={{ fontSize: 32 }}>📊</span>
        <span>{exhibit.title}(二进制表格,请下载或在新窗口查看)</span>
        {url && (
          <a href={url} target="_blank" rel="noopener noreferrer" className="ws-renderer__download-btn">
            在新窗口打开
          </a>
        )}
      </div>
    );
  }
  if (loading || error) return <FetchState loading={loading} error={error} url={url} />;
  const data = text ? parseTableData(text, exhibit.render_hints) : null;
  if (!data) {
    return <FetchState loading={false} error="无法解析表格数据(支持 CSV 文本或 JSON 对象数组)" url={url} />;
  }
  return (
    <div className="ws-exhibit__table">
      <Table
        columns={data.columns}
        dataSource={data.rows.map((r, i) => ({ key: i, ...r }))}
        size="small"
        pagination={data.rows.length > 20 ? { pageSize: 20, showSizeChanger: false } : false}
        scroll={{ x: true }}
      />
    </div>
  );
}

function SlidesR({ exhibit }: { exhibit: LobbyExhibit }) {
  const mode = exhibit.render_hints?.slides?.mode || 'html';
  const url = resolveExhibitUrl(exhibit);
  const inline = exhibit.source.inline;
  // 二进制 PPT/Key 无法被浏览器内联渲染
  const isBinarySlides = /\.(ppt|pptx|key)$/i.test(exhibit.title || '');

  if (mode === 'pdf') {
    if (!url) return <FetchState loading={false} error="无幻灯片地址" url="" />;
    return <IframeHost src={url} title={exhibit.title} className="ws-renderer__deliverable-iframe" />;
  }
  if (mode === 'images') {
    // inline 为图片 URL 的 JSON 数组
    let images: string[] = [];
    try {
      const arr = inline ? JSON.parse(inline) : [];
      if (Array.isArray(arr)) images = arr.filter((u) => typeof u === 'string');
    } catch {
      // 忽略,走空态
    }
    if (!images.length) return <FetchState loading={false} error="无幻灯片图片" url="" />;
    return (
      <div className="ws-exhibit__slides-images">
        {images.map((u, i) => (
          <img key={i} src={u} alt={`${exhibit.title} - ${i + 1}`} className="ws-renderer__deliverable-image" />
        ))}
      </div>
    );
  }
  // html:单文件幻灯片(内联 srcDoc 或远程 iframe),允许脚本以驱动翻页交互
  if (inline) {
    return (
      <IframeHost
        srcDoc={inline}
        sandbox="allow-scripts allow-same-origin"
        title={exhibit.title}
        className="ws-renderer__deliverable-iframe"
      />
    );
  }
  // 二进制 PPT/Key 无内联渲染:避免空白 iframe,给"下载/新窗口"兜底
  if (isBinarySlides) {
    return <FileR exhibit={exhibit} />;
  }
  if (!url) return <FetchState loading={false} error="无幻灯片地址" url="" />;
  return (
    <IframeHost
      src={url}
      sandbox="allow-scripts allow-same-origin"
      title={exhibit.title}
      className="ws-renderer__deliverable-iframe"
    />
  );
}

function ChartR({ exhibit }: { exhibit: LobbyExhibit }) {
  const { text, loading, error } = useExhibitText(exhibit);
  const url = resolveExhibitUrl(exhibit);
  const spec = exhibit.render_hints?.chart;
  const body = spec ? JSON.stringify(spec) : (text || '').trim();
  if (!spec && (loading || error)) return <FetchState loading={loading} error={error} url={url} />;
  if (!body) return <FetchState loading={false} error="无图表 spec" url="" />;
  return (
    <div className="ws-preview__markdown">
      <Markdown text={'```vis-chart\n' + body + '\n```'} />
    </div>
  );
}

function DataR({ exhibit }: { exhibit: LobbyExhibit }) {
  const { text, loading, error } = useExhibitText(exhibit);
  const url = resolveExhibitUrl(exhibit);
  if (loading || error) return <FetchState loading={loading} error={error} url={url} />;
  let pretty = text || '';
  try {
    pretty = JSON.stringify(JSON.parse(pretty), null, 2);
  } catch {
    // 非 JSON,原样展示
  }
  return (
    <div className="ws-preview__markdown">
      <Markdown text={'```json\n' + pretty + '\n```'} />
    </div>
  );
}

function FileR({ exhibit }: { exhibit: LobbyExhibit }) {
  return (
    <div className="ws-renderer__empty-panel">
      <FileOutlined style={{ fontSize: 28, color: '#d1d5db', marginBottom: 8 }} />
      <span className="ws-renderer__empty-hint">{exhibit.title}</span>
      <span className="ws-renderer__empty-hint">此类型暂不支持内联预览,可使用右上角图标下载或在新窗口打开</span>
    </div>
  );
}

/** kind → 渲染器注册表:新增内容类型在此注册 */
const EXHIBIT_RENDERERS: Record<LobbyExhibit['kind'], React.ComponentType<{ exhibit: LobbyExhibit }>> = {
  image: ImageR,
  video: VideoR,
  audio: AudioR,
  table: TableR,
  slides: SlidesR,
  html: HtmlR,
  pdf: PdfR,
  markdown: MarkdownR,
  code: CodeR,
  text: TextR,
  chart: ChartR,
  data: DataR,
  file: FileR,
};

const KIND_LABEL: Record<LobbyExhibit['kind'], string> = {
  image: '图片',
  video: '视频',
  audio: '音频',
  table: '表格',
  slides: '幻灯片',
  html: '页面',
  pdf: 'PDF',
  markdown: '文档',
  code: '代码',
  text: '文本',
  chart: '图表',
  data: '数据',
  file: '文件',
};

/* ═══════════════════════════════════════════════════════════════
   宿主:标题栏(类型/大小/功能图标) + 内容区
   ═══════════════════════════════════════════════════════════════ */

/** 头部功能图标按钮:幽灵风格,hover 淡底色 */
function HeadTool({ tip, icon, onClick, disabled }: { tip: string; icon: React.ReactNode; onClick: () => void; disabled?: boolean }) {
  return (
    <Tooltip title={tip}>
      <button type="button" className="ws-exhibit__tool" onClick={onClick} disabled={disabled} aria-label={tip}>
        {icon}
      </button>
    </Tooltip>
  );
}

/** 可从源文本生成文档(打印/导出 PDF)的内容类型 */
const DOC_KINDS: ReadonlySet<LobbyExhibit['kind']> = new Set(['markdown', 'text', 'code', 'chart', 'data', 'html']);
/** 支持打印的内容类型(html 走临时 iframe 打印,其余走所见即所得) */
const PRINT_KINDS: ReadonlySet<LobbyExhibit['kind']> = new Set(['markdown', 'text', 'code', 'chart', 'data', 'table', 'image', 'html']);

/** 导出文件名:去掉可识别扩展名,避免 report.html.pdf 这类叠加 */
function stripExt(name: string): string {
  return name.replace(/\.(md|markdown|txt|log|json|csv|py|js|ts|sql|html?|htm)$/i, '') || 'report';
}

export function ExhibitHost({ exhibit, workspaceId }: { exhibit: LobbyExhibit; workspaceId?: number }) {
  const { message } = App.useApp();
  const url = resolveExhibitUrl(exhibit);
  const downloadUrl = resolveExhibitDownloadUrl(exhibit);
  const actions = exhibit.actions || ['preview', 'download'];
  const Renderer = EXHIBIT_RENDERERS[exhibit.kind] || FileR;
  const size = fmtSize(exhibit.source.file_size);
  const bodyRef = useRef<HTMLDivElement>(null);
  const [docBusy, setDocBusy] = useState(false);
  const [appCardBusy, setAppCardBusy] = useState(false);
  // 文本类文件(code/data/text)可尝试作为 App Card payload 一键导入
  const isTextKind = exhibit.kind === 'code' || exhibit.kind === 'data' || exhibit.kind === 'text';
  const canImportAppCard = workspaceId != null && isTextKind;

  /** 一键导入为场景空间子应用:实时拉取 inline/url 文本,校验 app card payload 后落库。
   *  用 message.open 的全局 loading 文案,让"导入中/完成/失败"全程可见。 */
  const handleImportAppCard = async () => {
    if (workspaceId == null) return;
    const msgKey = `appcard-import-${exhibit.exhibit_id}`;
    setAppCardBusy(true);
    message.open({ key: msgKey, type: 'loading', content: '正在导入为场景空间子应用…', duration: 0 });
    try {
      let raw = exhibit.source.inline ?? '';
      if (!raw && url) {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        raw = await res.text();
      }
      if (!isAppCardPayloadText(raw)) {
        message.open({ key: msgKey, type: 'warning', content: '该文件不是有效的 App Card payload（需含 meta.schema_name 或 name+code）' });
        return;
      }
      const payload = extractAppCardPayload(raw, workspaceId);
      if (!payload) {
        message.open({ key: msgKey, type: 'warning', content: 'App Card 内容解析失败' });
        return;
      }
      const [err] = await apiInterceptors(createAppCard(payload));
      if (err) {
        message.open({ key: msgKey, type: 'error', content: (err as Error).message || '导入失败' });
        return;
      }
      message.open({ key: msgKey, type: 'success', content: `已导入子应用「${payload.name}」` });
    } catch (e) {
      message.open({ key: msgKey, type: 'error', content: (e as Error).message || '内容获取失败，无法导入' });
    } finally {
      setAppCardBusy(false);
    }
  };

  const canDoc = DOC_KINDS.has(exhibit.kind) && !!(url || exhibit.source.inline);
  const canPrint = PRINT_KINDS.has(exhibit.kind);

  /** 拉取源内容(inline 优先) */
  const fetchRaw = async (): Promise<string> => {
    let raw = exhibit.source.inline ?? '';
    if (!raw && url) {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      raw = await res.text();
    }
    if (!raw) throw new Error('empty');
    return raw;
  };

  /** 将任意 HTML 渲染到离屏 iframe(打印 / 导出 PDF 共用) */
  const renderOffscreen = async (html: string): Promise<HTMLIFrameElement> => {
    const frame = document.createElement('iframe');
    frame.style.cssText = 'position:fixed;left:-9999px;top:0;width:1200px;height:auto;border:none;';
    document.body.appendChild(frame);
    const doc = frame.contentDocument;
    if (doc) {
      doc.open();
      doc.write(html);
      doc.close();
    }
    // 等待资源 / 脚本渲染完成(与 VisManusRightPanel 导出策略一致)
    await new Promise((r) => setTimeout(r, 1500));
    return frame;
  };

  /** 打印:html 用原始文档临时 iframe,其余走所见即所得(渲染 DOM 直接打印) */
  const handlePrint = async () => {
    if (exhibit.kind === 'html') {
      setDocBusy(true);
      try {
        const raw = await fetchRaw();
        const frame = await renderOffscreen(raw);
        const doc = frame.contentDocument;
        if (doc) {
          const style = doc.createElement('style');
          style.textContent = `
            @media print {
              html, body { height: auto !important; overflow: visible !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
              h1, h2, h3, h4, h5, h6 { page-break-after: avoid; }
              table, figure, img, pre { page-break-inside: avoid; }
            }`;
          doc.head.appendChild(style);
        }
        await new Promise((r) => setTimeout(r, 200));
        frame.contentWindow?.print();
        setTimeout(() => {
          try { document.body.removeChild(frame); } catch { /* 已移除 */ }
        }, 1000);
      } catch {
        message.error('内容获取失败,无法打印');
      } finally {
        setDocBusy(false);
      }
      return;
    }
    if (bodyRef.current) printElement(bodyRef.current);
  };

  /** 导出 PDF:html 走 jsPDF 真实导出,其余走打印对话框另存为 PDF */
  const handleExportPdf = async () => {
    setDocBusy(true);
    try {
      const raw = await fetchRaw();
      const title = stripExt(exhibit.title);
      if (exhibit.kind === 'html') {
        const frame = await renderOffscreen(raw);
        const body = frame.contentDocument?.body;
        if (!body) throw new Error('empty doc');
        const canvas = await html2canvas(body, { useCORS: true, scale: 2, backgroundColor: '#ffffff', width: 1200 });
        const imgData = canvas.toDataURL('image/png');
        const pdf = new jsPDF('p', 'mm', 'a4');
        const imgWidth = pdf.internal.pageSize.getWidth() - 20;
        const pageHeight = pdf.internal.pageSize.getHeight() - 20;
        const imgHeight = (canvas.height * imgWidth) / canvas.width;
        const totalPages = Math.ceil(imgHeight / pageHeight);
        for (let i = 0; i < totalPages; i += 1) {
          if (i > 0) pdf.addPage();
          pdf.addImage(imgData, 'PNG', 10, -pageHeight * i + 10, imgWidth, imgHeight);
        }
        pdf.save(`${title}.pdf`);
        message.success('PDF 导出成功');
        try { document.body.removeChild(frame); } catch { /* 已移除 */ }
        return;
      }
      printHtmlDocument(renderExhibitDoc(exhibit.kind, raw, title));
    } catch {
      message.error('内容获取失败,无法导出 PDF');
    } finally {
      setDocBusy(false);
    }
  };

  const handleShare = async () => {
    const copy = async (text: string): Promise<boolean> => {
      try {
        await navigator.clipboard.writeText(text);
        return true;
      } catch {
        // 降级:非安全上下文等场景 clipboard API 不可用时,用 execCommand 兜底
        try {
          const ta = document.createElement('textarea');
          ta.value = text;
          ta.style.position = 'fixed';
          ta.style.opacity = '0';
          document.body.appendChild(ta);
          ta.select();
          const ok = document.execCommand('copy');
          document.body.removeChild(ta);
          return ok;
        } catch {
          return false;
        }
      }
    };
    // 优先生成无需登录即可访问的公开分享链接(/files/public_url 返回 HMAC 签名 + 过期地址)
    const uri = resolveExhibitUri(exhibit);
    if (uri) {
      try {
        const res = await GET('/api/v2/serve/file/files/public_url', { uri, expire: 3600 });
        const publicUrl = res.data?.data;
        if (typeof publicUrl === 'string' && publicUrl) {
          // 后端返回相对路径时补全 origin,保证分享出去的链接可被他人直接访问
          const shareUrl = publicUrl.startsWith('/')
            ? `${process.env.NEXT_PUBLIC_API_BASE_URL || ''}${publicUrl}`
            : publicUrl;
          if (await copy(shareUrl)) {
            message.success('公开分享链接已复制(1 小时内有效)');
          } else {
            message.warning('复制失败,请在新窗口打开后手动复制地址栏链接');
          }
          return;
        }
      } catch {
        // 公开链接生成失败,回退到当前(需鉴权的)预览地址
      }
    }
    if (!url) {
      message.warning('内联内容暂不支持分享链接');
      return;
    }
    if (await copy(url)) {
      message.success('链接已复制到剪贴板');
    } else {
      message.warning('复制失败,请在新窗口打开后手动复制地址栏链接');
    }
  };

  return (
    <div className="ws-exhibit">
      <div className="ws-exhibit__head">
        <span className="ws-preview__title">{exhibit.title}</span>
        <Tag color="blue">{KIND_LABEL[exhibit.kind] || exhibit.kind}</Tag>
        {size && <Tag>{size}</Tag>}
        <span className="ws-exhibit__head-actions">
          {canImportAppCard && (
            <Button
              type="primary"
              size="small"
              ghost
              icon={appCardBusy ? <LoadingOutlined spin /> : <DownloadOutlined />}
              loading={appCardBusy}
              disabled={appCardBusy}
              onClick={handleImportAppCard}
            >
              {appCardBusy ? '导入中…' : '导入为场景空间子应用'}
            </Button>
          )}
          <HeadTool tip="分享(复制链接)" icon={<ShareAltOutlined />} onClick={handleShare} disabled={!url} />
          {canPrint && (
            <HeadTool
              tip="打印"
              icon={docBusy ? <LoadingOutlined spin /> : <PrinterOutlined />}
              onClick={handlePrint}
              disabled={docBusy}
            />
          )}
          {canDoc && (
            <HeadTool
              tip="导出 PDF"
              icon={docBusy ? <LoadingOutlined spin /> : <FilePdfOutlined />}
              onClick={handleExportPdf}
              disabled={docBusy}
            />
          )}
          {actions.includes('preview') && url && (
            <HeadTool tip="新窗口打开" icon={<ExportOutlined />} onClick={() => window.open(url, '_blank')} />
          )}
          {actions.includes('download') && downloadUrl && (
            <HeadTool tip="下载" icon={<DownloadOutlined />} onClick={() => downloadFile(downloadUrl, exhibit.title)} />
          )}
        </span>
      </div>
      <div className="ws-exhibit__body" ref={bodyRef}>
        <Renderer exhibit={exhibit} />
      </div>
    </div>
  );
}
