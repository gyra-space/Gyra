import React from 'react';
import {
  CodeOutlined,
  FileTextOutlined,
  FileImageOutlined,
  FilePdfOutlined,
  FileUnknownOutlined,
  GlobalOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons';

/**
 * 文件预览类型判定 —— FilePreviewModal 与输入框附件预览共用。
 */
export const FILE_TYPES = {
  IMAGE: 'image',
  PDF: 'pdf',
  HTML: 'html',
  CODE: 'code',
  MARKDOWN: 'markdown',
  TEXT: 'text',
  VIDEO: 'video',
  UNKNOWN: 'unknown',
} as const;

export type FileType = (typeof FILE_TYPES)[keyof typeof FILE_TYPES];

const IMAGE_EXTS = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'avif', 'heic', 'ico'];
const HTML_EXTS = ['html', 'htm', 'xhtml'];
const CODE_EXTS = [
  'js', 'jsx', 'ts', 'tsx', 'py', 'java', 'go', 'rs', 'c', 'cpp', 'h', 'hpp',
  'css', 'scss', 'less', 'xml', 'json', 'yaml', 'yml', 'sql', 'sh', 'bash',
  'zsh', 'php', 'rb', 'swift', 'kt', 'scala', 'ini', 'toml', 'env', 'proto',
];
const MARKDOWN_EXTS = ['md', 'markdown', 'mdx'];
const VIDEO_EXTS = ['mp4', 'mov', 'webm', 'avi', 'mkv', 'm4v'];
const PDF_EXTS = ['pdf'];

/** 无扩展名或冷门扩展名的纯文本（Dockerfile / LICENSE / .env / 日志等） */
const TEXT_EXTS = [
  'txt', 'text', 'log', 'csv', 'tsv', 'rtf', 'conf', 'config', 'cfg',
  'properties', 'gitignore', 'dockerignore', 'npmrc', 'nvmrc', 'editorconfig',
  'lock', 'sum', 'mod', 'gradle', 'sbt', 'cmake', 'mk', 'rst', 'tex',
  'bib', 'org', 'nfo', 'asc', 'pem', 'crt', 'key', 'pub', 'csv2',
];

/**
 * 已知二进制／归档格式。这些走 text 分支会被 fetch().text() 读成一屏乱码，
 * 必须识别出来走 UNKNOWN 分支提示"不支持预览"。
 */
const BINARY_EXTS = [
  // 压缩包
  'zip', 'rar', '7z', 'gz', 'tgz', 'tar', 'bz2', 'xz', 'z', 'lz', 'lzma', 'dmg', 'iso',
  // 可执行文件 / 二进制产物
  'exe', 'dll', 'so', 'dylib', 'bin', 'o', 'a', 'lib', 'obj', 'wasm',
  'class', 'jar', 'war', 'apk', 'ipa', 'deb', 'rpm', 'msi', 'pyc', 'pyo', 'pyd',
  // Office（OOXML 本质是 zip）
  'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'docm', 'xlsm', 'pptm',
  'odt', 'ods', 'odp', 'odg', 'odf', 'rtf2',
  // 字体 / 设计稿 / 媒体工程
  'ttf', 'otf', 'woff', 'woff2', 'eot', 'psd', 'ai', 'sketch', 'fig', 'xd',
  'blend', 'fbx', 'obj2', 'glb', 'gltf', 'eps',
  // 数据库 / 数据文件
  'db', 'sqlite', 'sqlite3', 'mdb', 'accdb', 'dat', 'pak', 'sav', 'parquet', 'avro',
];

/** 已知二进制 mime 前缀/全等匹配（扩展名认不出来时的第二道防线） */
const BINARY_MIME_EXACT = new Set([
  'application/zip',
  'application/x-zip-compressed',
  'application/gzip',
  'application/x-gzip',
  'application/x-tar',
  'application/x-7z-compressed',
  'application/x-rar-compressed',
  'application/x-bzip2',
  'application/x-xz',
  'application/msword',
  'application/vnd.ms-excel',
  'application/vnd.ms-powerpoint',
  'application/x-msdownload',
  'application/x-executable',
  'application/x-apple-diskimage',
  'application/wasm',
  'application/x-sqlite3',
  'application/vnd.apache.parquet',
]);

const BINARY_MIME_PREFIX = [
  'application/vnd.openxmlformats-officedocument.',
  'application/vnd.oasis.opendocument.',
  'application/vnd.ms-',
  'font/',
  'application/font-',
  'application/x-font-',
];

export function getFileExtension(fileName: string): string {
  const parts = fileName.split('.');
  return parts.length > 1 ? parts.pop()!.toLowerCase() : '';
}

/**
 * 判定顺序：强特征 mime（image/video/pdf）→ 扩展名 → mime 细分 → text 兜底。
 *
 * 两条铁律：
 * 1. pdf / 已知二进制绝不能落到 text 分支，否则会 fetch().text() 读成乱码。
 * 2. 兜底仍是 text 而不是 unknown —— Dockerfile / LICENSE / .env / Makefile 这类
 *    无扩展名文件是真文本，判成 unknown 会让它们完全没法预览（体验倒退）。
 *    unknown 只给"确知是二进制"的情况，漏网之鱼由 isBinaryContent() 按内容兜。
 */
export function getFileType(fileName: string, mimeType?: string): FileType {
  const mime = mimeType?.toLowerCase() || '';

  // 1. 强特征 mime 优先，避免扩展名缺失/错误时误判
  if (mime.startsWith('image/')) return FILE_TYPES.IMAGE;
  if (mime.startsWith('video/')) return FILE_TYPES.VIDEO;
  if (mime === 'application/pdf' || mime === 'application/x-pdf') return FILE_TYPES.PDF;

  // 2. 扩展名
  const ext = getFileExtension(fileName);
  if (IMAGE_EXTS.includes(ext)) return FILE_TYPES.IMAGE;
  if (PDF_EXTS.includes(ext)) return FILE_TYPES.PDF;
  if (HTML_EXTS.includes(ext)) return FILE_TYPES.HTML;
  if (MARKDOWN_EXTS.includes(ext)) return FILE_TYPES.MARKDOWN;
  if (VIDEO_EXTS.includes(ext)) return FILE_TYPES.VIDEO;
  if (CODE_EXTS.includes(ext)) return FILE_TYPES.CODE;
  if (TEXT_EXTS.includes(ext)) return FILE_TYPES.TEXT;
  if (BINARY_EXTS.includes(ext)) return FILE_TYPES.UNKNOWN;

  // 3. mime 细分
  if (mime === 'text/html' || mime.includes('html')) return FILE_TYPES.HTML;
  if (mime.includes('markdown') || mime.includes('md')) return FILE_TYPES.MARKDOWN;
  if (
    mime.includes('json') ||
    mime.includes('javascript') ||
    mime.includes('typescript') ||
    mime.includes('python') ||
    mime.includes('sql')
  ) {
    return FILE_TYPES.CODE;
  }
  if (BINARY_MIME_EXACT.has(mime) || BINARY_MIME_PREFIX.some((p) => mime.startsWith(p))) {
    return FILE_TYPES.UNKNOWN;
  }
  if (mime.startsWith('text/')) return FILE_TYPES.TEXT;

  // 4. 兜底：既无扩展名、服务器又明确说是二进制流 —— 这是很强的二进制信号
  if (!ext && mime === 'application/octet-stream') return FILE_TYPES.UNKNOWN;

  return FILE_TYPES.TEXT;
}

/**
 * 按内容兜底识别二进制：扩展名和 mime 都认不出来的漏网之鱼（无扩展名的二进制文件）
 * 在 text 分支被读成字符串后，用这里判断是否该改显"不支持预览"。
 *
 * 两个信号：
 * - NUL 字符（\0）：文本文件里出现即基本可判定为二进制
 * - 连续 U+FFFD 替换字符：UTF-8 解码失败的产物
 */
export function isBinaryContent(text: string): boolean {
  if (!text) return false;
  const sample = text.slice(0, 4096);
  for (let i = 0; i < sample.length; i += 1) {
    if (sample.charCodeAt(i) === 0) return true;
  }
  return /\uFFFD{4,}/.test(sample);
}

const LANGUAGE_MAP: Record<string, string> = {
  js: 'javascript', jsx: 'jsx', ts: 'typescript', tsx: 'tsx',
  py: 'python', java: 'java', go: 'go', rs: 'rust',
  c: 'c', cpp: 'cpp', h: 'c', hpp: 'cpp', css: 'css',
  scss: 'scss', less: 'less', xml: 'xml', json: 'json',
  yaml: 'yaml', yml: 'yaml', sql: 'sql', sh: 'bash',
  bash: 'bash', zsh: 'bash', php: 'php', rb: 'ruby',
  swift: 'swift', kt: 'kotlin', scala: 'scala',
  md: 'markdown', markdown: 'markdown', mdx: 'markdown',
  txt: 'text', html: 'html', htm: 'html', ini: 'ini',
  toml: 'toml', proto: 'protobuf',
};

export function getLanguage(fileName: string): string {
  const ext = getFileExtension(fileName);
  return LANGUAGE_MAP[ext] || ext || 'text';
}

export function getFileTypeIcon(fileType: FileType): React.ReactNode {
  switch (fileType) {
    case FILE_TYPES.IMAGE:
      return <FileImageOutlined />;
    case FILE_TYPES.PDF:
      return <FilePdfOutlined />;
    case FILE_TYPES.HTML:
      return <GlobalOutlined />;
    case FILE_TYPES.CODE:
      return <CodeOutlined />;
    case FILE_TYPES.MARKDOWN:
      return <FileTextOutlined />;
    case FILE_TYPES.VIDEO:
      return <VideoCameraOutlined />;
    case FILE_TYPES.UNKNOWN:
      return <FileUnknownOutlined />;
    default:
      return <FileTextOutlined />;
  }
}
