'use client';

import React, { FC, useMemo } from 'react';
import { Tag } from 'antd';
import {
  FolderOutlined,
  FileOutlined,
  FileMarkdownOutlined,
  CodeOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { GPTVisLite } from '@antv/gpt-vis';
import { markdownComponents } from '../../../config';
import type { ManusExecutionOutput } from '@/types/manus';
import SkillReadRenderer from './SkillReadRenderer';

interface IProps {
  outputs: ManusExecutionOutput[];
  skillName?: string;
}

interface SkillFileEntry {
  path: string;
  size?: string;
}

interface ParsedSkillContent {
  name?: string;
  description?: string;
  /** frontmatter 扩展字段（author / version / tags 等，不含 name/description） */
  meta: Record<string, string | string[]>;
  body: string;
  basePath?: string;
  files: SkillFileEntry[];
}

/** Unescape XML entities (attribute values) */
function unescapeXml(s: string): string {
  return s
    .replace(/&quot;/g, '"')
    .replace(/&gt;/g, '>')
    .replace(/&lt;/g, '<')
    .replace(/&amp;/g, '&');
}

/** Parse a raw YAML frontmatter block (lite): supports `key: value`,
 *  block scalars (| and >) and inline lists ([a, b]). */
function parseMetaBlock(block: string): Record<string, string | string[]> {
  const meta: Record<string, string | string[]> = {};
  const lines = block.split('\n');
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();
    i++;
    if (!trimmed || trimmed.startsWith('#')) continue;
    const colonIdx = trimmed.indexOf(':');
    if (colonIdx < 0) continue;
    const key = trimmed.slice(0, colonIdx).trim();
    let value = trimmed.slice(colonIdx + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    if (value.startsWith('[') && value.endsWith(']')) {
      meta[key] = value
        .slice(1, -1)
        .split(',')
        .map((s) => s.trim().replace(/^['"]|['"]$/g, ''));
    } else if (value === '|' || value === '>') {
      const blockLines: string[] = [];
      while (i < lines.length) {
        const nextLine = lines[i];
        if (nextLine.match(/^[ \t]/) || nextLine.trim() === '') {
          blockLines.push(nextLine.replace(/^[ \t]{1,2}/, ''));
          i++;
        } else {
          break;
        }
      }
      const joined = value === '|'
        ? blockLines.join('\n').trim()
        : blockLines.join(' ').replace(/\s+/g, ' ').trim();
      if (joined) meta[key] = joined;
    } else if (value) {
      meta[key] = value;
    }
  }
  return meta;
}

/** Parse the standard skill tool output:
 *  LLM 视角：
 *  <skill_content name="...">
 *  {SKILL.md body, no YAML frontmatter}
 *  <file_preview>
 *  base_path: /abs/path/to/skill-dir
 *    relative/file (4.2K)
 *  </file_preview>
 *  </skill_content>
 *  用户视角（VIS 标签，在 skill_content 之外）：
 *  <d-skill-meta>{raw YAML frontmatter}</d-skill-meta>
 */
function parseSkillContent(raw: string): ParsedSkillContent | null {
  const m = raw.match(/<skill_content([^>]*)>([\s\S]*?)<\/skill_content>/);
  if (!m) return null;

  const attrs: Record<string, string> = {};
  const attrRe = /([\w-]+)="([^"]*)"/g;
  let am: RegExpExecArray | null;
  while ((am = attrRe.exec(m[1])) !== null) {
    attrs[am[1]] = unescapeXml(am[2]);
  }

  // <d-skill-meta>：原始 YAML frontmatter（name / description / author /
  // version / 扩展字段）——用户视角可视化数据，位于 skill_content 之外
  let meta: Record<string, string | string[]> = {};
  const sm = raw.match(/<d-skill-meta>([\s\S]*?)<\/d-skill-meta>/);
  if (sm) {
    meta = parseMetaBlock(sm[1]);
  }

  let inner = m[2];
  let basePath: string | undefined;
  const files: SkillFileEntry[] = [];
  const fp = inner.match(/<file_preview>([\s\S]*?)<\/file_preview>/);
  if (fp) {
    inner = inner.replace(fp[0], '');
    for (const line of fp[1].split('\n')) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      if (trimmed.startsWith('base_path:')) {
        basePath = trimmed.slice('base_path:'.length).trim();
        continue;
      }
      // "path (size)" or bare "path"
      const sized = trimmed.match(/^(.*?)\s*\(([^()]*)\)$/);
      if (sized && !trimmed.startsWith('...')) {
        files.push({ path: sized[1], size: sized[2] });
      } else {
        files.push({ path: trimmed });
      }
    }
  }

  const metaName = typeof meta.name === 'string' ? meta.name : undefined;
  const metaDesc = typeof meta.description === 'string' ? meta.description : undefined;

  return {
    name: attrs.name || metaName,
    description: metaDesc,
    meta,
    body: inner.trim(),
    basePath,
    files,
  };
}

/** File icon by extension */
const getFileIcon = (path: string) => {
  const ext = path.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'md':
      return <FileMarkdownOutlined className="text-blue-500 text-xs" />;
    case 'py':
    case 'js':
    case 'ts':
    case 'sh':
    case 'json':
    case 'yaml':
    case 'yml':
    case 'sql':
      return <CodeOutlined className="text-amber-500 text-xs" />;
    default:
      return <FileOutlined className="text-slate-400 text-xs" />;
  }
};

/* ═══════════════════════════════════════════════════════════════
   Sub-components
   ═══════════════════════════════════════════════════════════════ */

/** YAML header card — name + description + 扩展字段（author / version / tags 等） */
const HeaderCard: FC<{
  name: string;
  description?: string;
  meta: Record<string, string | string[]>;
}> = ({ name, description, meta }) => {
  const displayFields = Object.entries(meta).filter(
    ([k]) => !['name', 'description'].includes(k)
  );

  return (
    <div className="rounded-lg border border-violet-200 bg-gradient-to-r from-violet-50 to-purple-50 p-4">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center text-white text-lg shadow-sm flex-shrink-0">
          &#129513;
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-slate-800">{name}</h4>
          {description && (
            <p className="text-xs text-slate-500 mt-0.5 leading-relaxed whitespace-pre-wrap">
              {description}
            </p>
          )}
        </div>
      </div>

      {displayFields.length > 0 && (
        <div className="mt-3 pt-3 border-t border-violet-200/60 flex flex-wrap gap-x-4 gap-y-1.5">
          {displayFields.map(([key, value]) => (
            <div key={key} className="flex items-center gap-1 text-xs">
              <span className="text-slate-400 font-medium">{key}:</span>
              {Array.isArray(value) ? (
                <span className="flex gap-1">
                  {value.map((v, i) => (
                    <Tag key={i} color="purple" className="text-[10px] leading-tight m-0">
                      {v}
                    </Tag>
                  ))}
                </span>
              ) : (
                <span className="text-slate-600">{String(value)}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

/** Body markdown content area */
const ContentBody: FC<{ content: string }> = ({ content }) => (
  <div className="rounded-lg border border-slate-200 bg-white p-4">
    <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-3">
      <FileMarkdownOutlined />
      <span>Skill Instructions</span>
    </div>
    <div className="whitespace-normal prose-sm prose-slate max-w-none">
      <GPTVisLite components={markdownComponents}>{content}</GPTVisLite>
    </div>
  </div>
);

/** file_preview — available file dependencies */
const FilePreview: FC<{ basePath?: string; files: SkillFileEntry[] }> = ({
  basePath,
  files,
}) => (
  <div className="rounded-lg border border-slate-200 overflow-hidden">
    <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-100 text-xs text-slate-500 border-b border-slate-200">
      <FolderOutlined />
      <span>文件依赖 ({files.length})</span>
      {basePath && (
        <span className="ml-auto font-mono text-[10px] text-slate-400 truncate max-w-[60%]" title={basePath}>
          {basePath}
        </span>
      )}
    </div>
    <div className="p-2 bg-white font-mono text-xs space-y-0.5 max-h-[240px] overflow-y-auto">
      {files.map((f, i) => (
        <div key={i} className="flex items-center gap-1.5 px-1 py-0.5 rounded hover:bg-slate-50">
          {getFileIcon(f.path)}
          <span className="text-slate-600 truncate">{f.path}</span>
          {f.size && (
            <span className="ml-auto text-slate-400 flex-shrink-0">{f.size}</span>
          )}
        </div>
      ))}
    </div>
  </div>
);

/* ═══════════════════════════════════════════════════════════════
   Main renderer
   ═══════════════════════════════════════════════════════════════ */

const SkillContentRenderer: FC<IProps> = ({ outputs, skillName }) => {
  const parsed = useMemo(() => {
    const allContent = outputs
      .map((o) => (typeof o.content === 'string' ? o.content : JSON.stringify(o.content ?? '')))
      .join('\n');
    return parseSkillContent(allContent);
  }, [outputs]);

  // Legacy fallback: 历史消息（裸 SKILL.md 原文等）走旧 SkillReadRenderer
  if (!parsed) {
    return <SkillReadRenderer outputs={outputs} skillName={skillName} />;
  }

  const name = parsed.name || skillName || 'Skill';

  if (!parsed.body && !parsed.description && parsed.files.length === 0 && Object.keys(parsed.meta).length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-32 text-slate-400">
        <InfoCircleOutlined className="text-2xl text-slate-300 mb-2" />
        <div className="text-xs">Skill 内容加载中...</div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <HeaderCard
        name={name}
        description={parsed.description}
        meta={parsed.meta}
      />
      {parsed.body && <ContentBody content={parsed.body} />}
      {parsed.files.length > 0 && (
        <FilePreview basePath={parsed.basePath} files={parsed.files} />
      )}
    </div>
  );
};

export default SkillContentRenderer;
