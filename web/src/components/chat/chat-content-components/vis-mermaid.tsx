'use client';

import { ChatContext } from '@/contexts';
import {
  CheckOutlined,
  CodeOutlined,
  CopyOutlined,
  EditOutlined,
  EyeOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import React, { useCallback, useContext, useEffect, useRef, useState } from 'react';
import { CodePreview } from './code-preview';

interface VisMermaidProps {
  code: string;
}

let uidCounter = 0;

/**
 * 中文字体栈：mermaid 默认用西文字体估算文本宽度，CJK 字符宽度被低估会导致
 * 文字溢出被节点边框裁剪（"最后一个字被遮挡一半"）。显式指定字体让测量与
 * 实际渲染使用同一字体，并等待 document.fonts.ready 后再渲染，确保测量准确。
 */
const CJK_FONT_FAMILY = [
  'PingFang SC',
  'Hiragino Sans GB',
  'Microsoft YaHei',
  'Noto Sans SC',
  'Helvetica Neue',
  'Arial',
  'sans-serif',
].join(', ');

/** 浅色主题：现代扁平风格（蓝紫主色 + 圆角 + 渐变） */
const LIGHT_THEME: Record<string, string | number | boolean> = {
  background: 'transparent',
  fontFamily: CJK_FONT_FAMILY,
  fontSize: '16px',
  primaryColor: '#eef2ff',
  primaryTextColor: '#1e293b',
  primaryBorderColor: '#c7d2fe',
  lineColor: '#94a3b8',
  secondaryColor: '#f0fdf4',
  secondaryBorderColor: '#bbf7d0',
  tertiaryColor: '#fff7ed',
  tertiaryBorderColor: '#fed7aa',
  noteBkgColor: '#fef9c3',
  noteTextColor: '#713f12',
  noteBorderColor: '#fde047',
  clusterBkg: '#f8fafc',
  clusterBorder: '#e2e8f0',
  edgeLabelBackground: '#ffffff',
  nodeTextColor: '#1e293b',
  textColor: '#334155',
  titleColor: '#0f172a',
  actorBkg: '#eef2ff',
  actorBorder: '#c7d2fe',
  actorTextColor: '#1e293b',
  labelBoxBkgColor: '#ffffff',
  labelBoxBorderColor: '#e2e8f0',
  labelTextColor: '#334155',
  signalColor: '#6366f1',
  signalTextColor: '#ffffff',
  labelBackgroundColor: '#ffffff',
  errorBkgColor: '#fee2e2',
  errorTextColor: '#b91c1c',
  gridColor: '#e2e8f0',
  arrowheadColor: '#94a3b8',
  useGradient: true,
  gradientStart: '#eef2ff',
  gradientStop: '#e0e7ff',
  dropShadow: 'rgba(15, 23, 42, 0.08)',
  radius: 10,
};

/** 深色主题 */
const DARK_THEME: Record<string, string | number | boolean> = {
  background: 'transparent',
  fontFamily: CJK_FONT_FAMILY,
  fontSize: '16px',
  primaryColor: '#1e293b',
  primaryTextColor: '#e2e8f0',
  primaryBorderColor: '#334155',
  lineColor: '#64748b',
  secondaryColor: '#0f172a',
  secondaryBorderColor: '#334155',
  tertiaryColor: '#1e293b',
  tertiaryBorderColor: '#334155',
  noteBkgColor: '#422006',
  noteTextColor: '#fde68a',
  noteBorderColor: '#78350f',
  clusterBkg: '#111827',
  clusterBorder: '#374151',
  edgeLabelBackground: '#1e293b',
  nodeTextColor: '#e2e8f0',
  textColor: '#cbd5e1',
  titleColor: '#f1f5f9',
  actorBkg: '#1e293b',
  actorBorder: '#475569',
  actorTextColor: '#e2e8f0',
  labelBoxBkgColor: '#1e293b',
  labelBoxBorderColor: '#374151',
  labelTextColor: '#cbd5e1',
  signalColor: '#818cf8',
  signalTextColor: '#0f172a',
  labelBackgroundColor: '#1e293b',
  errorBkgColor: '#450a0a',
  errorTextColor: '#fca5a5',
  gridColor: '#334155',
  arrowheadColor: '#64748b',
  useGradient: true,
  gradientStart: '#1e293b',
  gradientStop: '#273449',
  dropShadow: 'rgba(0, 0, 0, 0.35)',
  radius: 10,
};

/** 布局：更宽松的间距 + 平滑曲线 + 充足 padding（兜底防文字裁剪） */
const FLOWCHART_OPTIONS = {
  curve: 'basis' as const,
  nodeSpacing: 50,
  rankSpacing: 60,
  padding: 14,
  useMaxWidth: true,
};

const getMermaidConfig = (mode: string) => ({
  startOnLoad: false,
  theme: 'base' as const,
  themeVariables: mode === 'dark' ? DARK_THEME : LIGHT_THEME,
  htmlLabels: true,
  fontFamily: CJK_FONT_FAMILY,
  flowchart: FLOWCHART_OPTIONS,
  sequence: { mirrorActors: false },
});

const TOOLBAR_BTN =
  'flex items-center gap-1 rounded px-1.5 py-0.5 text-xs text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-theme-dark dark:hover:text-gray-200';

const ICON_STYLE: React.CSSProperties = { fontSize: 12 };

/**
 * 使用 mermaid v11 渲染 mermaid 代码块。
 *
 * - 动态 import：避免 SSR 阶段加载 mermaid（其依赖 document），同时按需代码分割，只有出现
 *   mermaid 代码块时才加载对应 chunk。
 * - 渲染前等待 document.fonts.ready，确保字体已加载、宽度测量准确（修复中文被裁剪）。
 * - 防抖渲染：LLM 流式输出时 code 会逐 token 变化，语法未完整时渲染必然失败。
 *   对 code 做 400ms 防抖，输出停顿后再渲染，避免中途失败；渲染成功时清空 error，
 *   保证输出结束后能自动渲染出最终图（不再需要刷新）。
 * - 工具栏：图表/源码切换、复制源码、编辑源码后重新渲染、失败重试。
 */
const VisMermaid = ({ code }: VisMermaidProps) => {
  const { mode } = useContext(ChatContext);
  const containerRef = useRef<HTMLDivElement>(null);
  const renderSeqRef = useRef(0);
  const idRef = useRef<string>(`gyra-mermaid-${Date.now()}-${uidCounter++}`);

  /** 当前实际渲染用的源码（编辑保存后变化） */
  const [sourceCode, setSourceCode] = useState(code);
  /** 防抖后的渲染输入 */
  const [debouncedCode, setDebouncedCode] = useState(code);
  /** 视图：图 / 源码 */
  const [view, setView] = useState<'diagram' | 'code'>('diagram');
  /** 源码编辑模式 */
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(code);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  /** 重试计数：递增触发渲染 effect 重跑 */
  const [retryTick, setRetryTick] = useState(0);

  // 外部 code 变化（LLM 流式输出）同步到 sourceCode
  useEffect(() => {
    setSourceCode(code);
  }, [code]);

  // 防抖：输出停顿 400ms 后才更新渲染输入，避免流式中途用不完整语法渲染
  useEffect(() => {
    setLoading(true);
    const t = setTimeout(() => setDebouncedCode(sourceCode), 400);
    return () => clearTimeout(t);
  }, [sourceCode]);

  // 渲染
  useEffect(() => {
    const seq = ++renderSeqRef.current;
    let cancelled = false;
    let bindFn: ((el: Element) => void) | undefined;

    const render = async () => {
      try {
        // 等待字体加载完成，避免字体未就绪时宽度测量偏差导致文字被裁剪
        if (typeof document !== 'undefined' && 'fonts' in document) {
          await document.fonts.ready;
        }
        const mermaid = (await import('mermaid')).default;
        mermaid.initialize(getMermaidConfig(mode));
        const container = containerRef.current;
        const { svg, bindFunctions } = await mermaid.render(
          `${idRef.current}-${seq}`,
          debouncedCode,
          container ?? undefined,
        );
        if (cancelled || seq !== renderSeqRef.current || !containerRef.current) return;
        containerRef.current.innerHTML = svg;
        bindFn = bindFunctions;
        bindFn?.(containerRef.current);
        // 关键：渲染成功必须清空 error，否则流式期间失败的错误会永久卡住
        setError(null);
        setLoading(false);
      } catch (e) {
        if (cancelled || seq !== renderSeqRef.current) return;
        setError(e instanceof Error ? e.message : String(e));
        setLoading(false);
      }
    };

    render();

    return () => {
      cancelled = true;
      if (containerRef.current) {
        bindFn?.(containerRef.current);
        containerRef.current.innerHTML = '';
      }
    };
  }, [debouncedCode, mode, retryTick]);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(sourceCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // 剪贴板不可用时静默失败
    }
  }, [sourceCode]);

  const handleApplyEdit = useCallback(() => {
    setSourceCode(draft);
    setEditing(false);
    setView('diagram');
  }, [draft]);

  const handleRetry = useCallback(() => {
    setError(null);
    setLoading(true);
    setRetryTick(t => t + 1);
  }, []);

  return (
    <div className='mermaid-container my-3 overflow-hidden rounded-lg border border-gray-100 bg-white shadow-card dark:border-theme-dark dark:bg-theme-dark-container dark:shadow-none'>
      {/* 工具栏 */}
      <div className='flex items-center justify-between border-b border-gray-100 px-3 py-1.5 dark:border-theme-dark'>
        <span className='text-xs font-medium text-gray-400 dark:text-gray-500'>mermaid</span>
        <div className='flex items-center gap-1'>
          {view === 'diagram' ? (
            <button className={TOOLBAR_BTN} onClick={() => setView('code')} title='查看源码'>
              <CodeOutlined style={ICON_STYLE} />
              源码
            </button>
          ) : (
            <button className={TOOLBAR_BTN} onClick={() => setView('diagram')} title='查看图表'>
              <EyeOutlined style={ICON_STYLE} />
              图表
            </button>
          )}
          {!editing && (
            <button className={TOOLBAR_BTN} onClick={() => setEditing(true)} title='编辑源码并重新渲染'>
              <EditOutlined style={ICON_STYLE} />
              编辑
            </button>
          )}
          <button className={TOOLBAR_BTN} onClick={handleCopy} title='复制源码'>
            {copied ? <CheckOutlined style={{ ...ICON_STYLE, color: '#22c55e' }} /> : <CopyOutlined style={ICON_STYLE} />}
            {copied ? '已复制' : '复制'}
          </button>
        </div>
      </div>

      {/* 图表视图：常驻 DOM（hidden 控制显隐），保证切换视图期间后台渲染仍能注入 SVG */}
      <div className={view === 'diagram' ? '' : 'hidden'}>
        <div className='p-3'>
          {loading && (
            <div className='py-3 text-xs text-gray-400 dark:text-gray-500'>
              <span className='mr-1'>mermaid</span>渲染中...
            </div>
          )}
          {error && (
            <div className='my-1 rounded border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-400'>
              <div className='mb-1 font-medium'>图渲染失败</div>
              <div className='mb-2 break-all font-mono text-red-400 dark:text-red-500'>{error}</div>
              <div className='flex gap-2'>
                <button
                  className='flex items-center gap-1 rounded border border-red-200 px-2 py-0.5 transition-colors hover:bg-red-100 dark:border-red-900 dark:hover:bg-red-900/40'
                  onClick={handleRetry}
                >
                  <ReloadOutlined style={ICON_STYLE} />
                  重试
                </button>
                <button
                  className='flex items-center gap-1 rounded border border-red-200 px-2 py-0.5 transition-colors hover:bg-red-100 dark:border-red-900 dark:hover:bg-red-900/40'
                  onClick={() => setView('code')}
                >
                  <CodeOutlined style={ICON_STYLE} />
                  查看源码
                </button>
              </div>
            </div>
          )}
          <div ref={containerRef} className='gyra-mermaid-svg' />
        </div>
      </div>

      {/* 源码视图 */}
      {view === 'code' && (
        <div className='p-3'>
          {editing ? (
            <div>
              <textarea
                value={draft}
                onChange={e => setDraft(e.target.value)}
                spellCheck={false}
                className='w-full rounded border border-gray-200 bg-white p-2 font-mono text-xs leading-5 text-gray-700 outline-none focus:border-indigo-400 dark:border-theme-dark dark:bg-theme-dark dark:text-gray-200'
                rows={Math.max(6, Math.min(20, draft.split('\n').length + 1))}
              />
              <div className='mt-2 flex gap-2'>
                <button
                  className='rounded bg-indigo-500 px-3 py-1 text-xs text-white transition-colors hover:bg-indigo-600'
                  onClick={handleApplyEdit}
                >
                  应用并渲染
                </button>
                <button
                  className='rounded border border-gray-200 px-3 py-1 text-xs text-gray-500 transition-colors hover:bg-gray-50 dark:border-theme-dark dark:text-gray-400 dark:hover:bg-theme-dark'
                  onClick={() => {
                    setEditing(false);
                    setDraft(sourceCode);
                    setView('diagram');
                  }}
                >
                  取消
                </button>
              </div>
            </div>
          ) : (
            <CodePreview code={sourceCode} language='mermaid' />
          )}
        </div>
      )}
    </div>
  );
};

export default VisMermaid;
