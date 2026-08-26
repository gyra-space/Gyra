'use client';

import { apiInterceptors } from '@/client/api';
import { getOrCreateEcpSpace } from '@/client/api/ecp';
import {
  editDoc,
  getRawTree,
  getWikiTree,
  listIngestJobs,
  readDoc,
  readRawFile,
  uploadFile,
} from '@/client/api/knowledge-vault';
import type { IngestJob, TreeNode } from '@/types/knowledge-vault';
import MarkdownEditor from '@/components/knowledge-vault/MarkdownEditor';
import RawCreateModal from '@/components/knowledge-vault/RawCreateModal';
import WikiCreateModal from '@/components/knowledge-vault/WikiCreateModal';
import {
  EditOutlined,
  FileMarkdownOutlined,
  FileTextOutlined,
  InboxOutlined,
  ReloadOutlined,
  SaveOutlined,
} from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { App, Button, Segmented, Spin, Tree } from 'antd';
import {
  type DragEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import rehypeRaw from 'rehype-raw';
import remarkBreaks from 'remark-breaks';
import remarkGfm from 'remark-gfm';

import { EcpEmpty } from './common';

const STATUS_LABEL: Record<string, string> = {
  pending: '排队中',
  extracting: '抽取中',
  embedding: '向量化',
  generating_wiki: '生成 wiki',
  done: '完成',
  failed: '失败',
};

type SideView = 'wiki' | 'raw';

interface TreeChildNode {
  key: string;
  title: string;
  isLeaf: boolean;
  children?: TreeChildNode[];
  icon?: ReactNode;
}

function toTreeData(nodes: TreeNode[], isDirIcon?: (n: TreeNode) => boolean): TreeChildNode[] {
  return (nodes ?? []).map(n => ({
    key: n.path,
    title: n.name,
    isLeaf: !n.is_dir,
    children: n.children ? toTreeData(n.children, isDirIcon) : undefined,
    icon: n.is_dir ? undefined : (isDirIcon?.(n) ? <FileTextOutlined /> : <FileMarkdownOutlined />),
  }));
}

function countTree(nodes: TreeChildNode[] | undefined): number {
  if (!nodes) return 0;
  return nodes.reduce((acc, n) => acc + (n.isLeaf ? 1 : countTree(n.children)), 0);
}

/**
 * 知识资产：ECP 专属软知识空间（ecp-<workspace>）的直接维护入口。
 * 无需再跳转知识库模块——在这里即可浏览、新建、编辑 wiki 文档，上传原始文件触发 ingest。
 */
export default function KnowledgeTab({ workspaceId }: { workspaceId: string }) {
  const { message } = App.useApp();
  const [side, setSide] = useState<SideView>('wiki');
  const [selectedDoc, setSelectedDoc] = useState<string>();
  const [selectedRaw, setSelectedRaw] = useState<string>();
  const [wikiOpen, setWikiOpen] = useState(false);
  const [rawOpen, setRawOpen] = useState(false);
  const [draft, setDraft] = useState('');
  const [dirty, setDirty] = useState(false);
  const [editing, setEditing] = useState(false);
  const [dragDepth, setDragDepth] = useState(0);
  const fileRef = useRef<HTMLInputElement>(null);

  const { data: space, loading: spaceLoading } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(getOrCreateEcpSpace(workspaceId));
      if (err) throw err;
      return res;
    },
    { refreshDeps: [workspaceId] },
  );
  const slug = space?.slug;

  const [jobs, setJobs] = useState<IngestJob[]>([]);
  const pollJobs = useCallback(async () => {
    if (!slug) return;
    const [err, res] = await apiInterceptors(listIngestJobs(slug, 30));
    if (!err && res) setJobs(res?.items ?? []);
    const hasPending = (res?.items ?? []).some(
      j => j.status !== 'done' && j.status !== 'failed',
    );
    if (hasPending) {
      setTimeout(pollJobs, 2500);
    }
  }, [slug]);

  useEffect(() => {
    if (slug) pollJobs();
  }, [slug, pollJobs]);

  const { data: wikiTree, loading: wikiLoading, refresh: refreshWiki } = useRequest(
    async () => {
      if (!slug) return [];
      const [err, res] = await apiInterceptors(getWikiTree(slug));
      return err ? [] : res ?? [];
    },
    { ready: !!slug, refreshDeps: [slug] },
  );

  const { data: rawTree, loading: rawLoading, refresh: refreshRaw } = useRequest(
    async () => {
      if (!slug) return [];
      const [err, res] = await apiInterceptors(getRawTree(slug));
      return err ? [] : res ?? [];
    },
    { ready: !!slug, refreshDeps: [slug] },
  );

  const { data: doc, loading: docLoading, refresh: refreshDoc } = useRequest(
    async () => {
      if (!slug || !selectedDoc) return null;
      const [err, res] = await apiInterceptors(readDoc(slug, selectedDoc));
      return err ? null : res;
    },
    { ready: !!slug && !!selectedDoc, refreshDeps: [selectedDoc, slug] },
  );

  const { data: rawContent, loading: rawLoadingFile } = useRequest(
    async () => {
      if (!slug || !selectedRaw) return null;
      const [err, res] = await apiInterceptors(readRawFile(slug, selectedRaw));
      return err ? null : res;
    },
    { ready: !!slug && !!selectedRaw, refreshDeps: [selectedRaw, slug] },
  );

  const { run: saveDoc, loading: saving } = useRequest(
    async () => {
      if (!slug || !selectedDoc) return;
      const [err] = await apiInterceptors(editDoc(slug, selectedDoc, draft));
      if (err) throw err;
      message.success('文档已保存');
      setDirty(false);
      setEditing(false);
      refreshDoc();
      refreshWiki();
    },
    { manual: true },
  );

  const { runAsync: doUpload } = useRequest(
    async (file: File) => {
      if (!slug) return;
      const [err] = await apiInterceptors(uploadFile({ slug, file }));
      if (err) throw err;
      message.success(`已上传「${file.name}」，解析中…`);
      refreshRaw();
      pollJobs();
    },
    { manual: true },
  );

  const handleDragEnter = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (Array.from(e.dataTransfer?.types ?? []).includes('Files')) {
      setDragDepth(d => d + 1);
    }
  };
  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };
  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragDepth(d => Math.max(0, d - 1));
  };
  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragDepth(0);
    Array.from(e.dataTransfer?.files ?? []).forEach(f => {
      doUpload(f).catch(err => message.error(String(err)));
    });
  };

  const treeData = useMemo(() => toTreeData(wikiTree ?? []), [wikiTree]);
  const rawTreeData = useMemo(() => toTreeData(rawTree ?? [], () => true), [rawTree]);

  // 文档加载后构建编辑草稿（frontmatter + 正文）
  useEffect(() => {
    if (doc) {
      const fm = doc.frontmatter || {};
      const fmLines = Object.entries(fm).map(([k, v]) => {
        const value =
          Array.isArray(v) || (typeof v === 'object' && v !== null)
            ? JSON.stringify(v)
            : String(v);
        return `${k}: ${value}`;
      });
      setDraft(`---\n${fmLines.join('\n')}\n---\n\n${doc.content}`);
      setDirty(false);
    }
  }, [doc]);

  const pendingJobs = jobs.filter(j => j.status !== 'done' && j.status !== 'failed');

  if (spaceLoading) return <Spin style={{ display: 'block', margin: '64px auto' }} />;
  if (!slug) return <EcpEmpty title="知识空间未就绪" desc="创建 ECP 软知识空间失败，请刷新重试" />;

  return (
    <>
      <div
        className="ecp-kn"
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {dragDepth > 0 && (
          <div className="ecp-kn__drop-overlay">
            <div className="ecp-kn__drop-inner">
              <div className="ecp-kn__drop-icon">
                <InboxOutlined />
              </div>
              <div className="ecp-kn__drop-title">松手即可上传文档</div>
              <div className="ecp-kn__drop-hint">
                支持 pdf / docx / pptx / txt / md / xlsx / 图片 / 音频 / 视频，自动解析生成词条
              </div>
            </div>
          </div>
        )}
        <header className="ecp-kn__toolbar">
          <div className="ecp-kn__head">
            <div className="ecp-kn__heading">
              <h2 className="ecp-kn__title">知识资产</h2>
              <code className="ecp-kn__space">{slug}</code>
            </div>
            <p className="ecp-kn__sub">
              拖拽文件到任意位置即可上传，也可手动新建 / 编辑 wiki 文档。
            </p>
          </div>
          <div className="ecp-kn__actions">
            <Button type="primary" icon={<InboxOutlined />} onClick={() => fileRef.current?.click()}>
              上传文档
            </Button>
            <Button icon={<EditOutlined />} onClick={() => setWikiOpen(true)}>
              新建词条
            </Button>
            <Button icon={<FileTextOutlined />} onClick={() => setRawOpen(true)}>
              新建原始文件
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => {
                refreshWiki();
                refreshRaw();
                pollJobs();
              }}
            />
          </div>
        </header>

        {pendingJobs.length > 0 && (
          <div className="ecp-kn__jobs">
            <span className="ecp-kn__jobs-dot" />
            <span>
              正在解析 {pendingJobs.length} 个文档（
              {STATUS_LABEL[pendingJobs[0].status] ?? pendingJobs[0].status}），完成后可在「wiki
              词条」中查看
            </span>
          </div>
        )}

        <div className="ecp-kn__workbench">
          <aside className="ecp-kn__explorer">
            <Segmented
              size="small"
              block
              value={side}
              onChange={v => setSide(v as SideView)}
              options={[
                { label: 'wiki 词条', value: 'wiki' },
                { label: '原始文件', value: 'raw' },
              ]}
            />
            <div className="ecp-kn__explorer-body">
              {side === 'wiki' ? (
                wikiLoading ? (
                  <Spin style={{ display: 'block', margin: '40px auto' }} />
                ) : treeData.length ? (
                  <Tree
                    className="ecp-kn__tree"
                    showIcon
                    blockNode
                    treeData={treeData}
                    selectedKeys={selectedDoc ? [selectedDoc] : []}
                    onSelect={(keys, info) => {
                      if (info.node?.isLeaf === false) return;
                      const k = keys[0] as string | undefined;
                      if (k && k.endsWith('.md')) {
                        setSelectedDoc(k);
                        setEditing(false);
                        setDirty(false);
                      }
                    }}
                  />
                ) : (
                  <EcpEmpty title="暂无词条" desc="上传文档或点「新建词条」创建" />
                )
              ) : rawLoading ? (
                <Spin style={{ display: 'block', margin: '40px auto' }} />
              ) : rawTreeData.length ? (
                <Tree
                  className="ecp-kn__tree"
                  showIcon
                  blockNode
                  treeData={rawTreeData}
                  selectedKeys={selectedRaw ? [selectedRaw] : []}
                  onSelect={keys => {
                    const k = keys[0] as string | undefined;
                    if (k && !k.endsWith('/')) setSelectedRaw(k);
                  }}
                />
              ) : (
                <EcpEmpty title="暂无原始文件" desc="点「新建原始文件」添加" />
              )}
            </div>
            <div className="ecp-kn__explorer-foot">
              {side === 'wiki'
                ? `${countTree(treeData)} 篇词条`
                : `${countTree(rawTreeData)} 个文件`}
              <span className="ecp-kn__explorer-tip">点击条目浏览</span>
            </div>
          </aside>

          <section className="ecp-kn__reader">
            {side === 'wiki' ? (
              !selectedDoc ? (
                <EcpEmpty title="从左侧选择一篇词条" desc="选中后即可预览或编辑，支持 Markdown 排版" />
              ) : docLoading ? (
                <Spin style={{ display: 'block', margin: '64px auto' }} />
              ) : doc ? (
                <>
                  <div className="ecp-kn__doc-top">
                    <span className="ecp-kn__doc-path">{selectedDoc}</span>
                    <div className="ecp-kn__doc-actions">
                      <Button
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => setEditing(e => !e)}
                      >
                        {editing ? '取消编辑' : '编辑'}
                      </Button>
                      {editing && (
                        <Button
                          size="small"
                          type="primary"
                          icon={<SaveOutlined />}
                          loading={saving}
                          disabled={!dirty}
                          onClick={() => saveDoc()}
                        >
                          保存
                        </Button>
                      )}
                    </div>
                  </div>
                  <h1 className="ecp-kn__doc-title">{doc.title}</h1>
                  {!!doc.frontmatter?.ref && (
                    <div className="ecp-kn__doc-ref">ref → {String(doc.frontmatter.ref)}</div>
                  )}
                  <div className="ecp-kn__doc-body" style={{ height: editing ? 480 : 'auto' }}>
                    {editing ? (
                      <div
                        style={{
                          height: 480,
                          border: '1px solid var(--line-soft)',
                          borderRadius: 8,
                          overflow: 'hidden',
                        }}
                      >
                        <MarkdownEditor
                          value={draft}
                          onChange={t => {
                            setDraft(t);
                            setDirty(true);
                          }}
                        />
                      </div>
                    ) : (
                      <div className="ecp-kn__md">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm, remarkBreaks]}
                          rehypePlugins={[rehypeRaw, rehypeHighlight]}
                        >
                          {doc.content}
                        </ReactMarkdown>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <EcpEmpty title="读取失败" />
              )
            ) : !selectedRaw ? (
              <EcpEmpty title="从左侧选择原始文件" desc="原始文件为只读，上传解析后生成 wiki 词条" />
            ) : rawLoadingFile ? (
              <Spin style={{ display: 'block', margin: '64px auto' }} />
            ) : rawContent ? (
              <>
                <div className="ecp-kn__doc-top">
                  <span className="ecp-kn__doc-path">{selectedRaw}</span>
                </div>
                <h1 className="ecp-kn__doc-title">{selectedRaw.split('/').pop()}</h1>
                <div className="ecp-kn__doc-body ecp-kn__raw">
                  <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13, fontFamily: 'inherit', margin: 0 }}>
                    {rawContent.content}
                  </pre>
                </div>
              </>
            ) : (
              <EcpEmpty title="读取失败" />
            )}
          </section>
        </div>
      </div>

      <input
        ref={fileRef}
        type="file"
        multiple
        hidden
        onChange={e => {
          Array.from(e.target.files ?? []).forEach(f => {
            doUpload(f).catch(err => message.error(String(err)));
          });
          e.target.value = '';
        }}
      />

      <WikiCreateModal
        slug={slug}
        open={wikiOpen}
        onClose={() => setWikiOpen(false)}
        onCreated={() => {
          refreshWiki();
        }}
      />
      <RawCreateModal
        slug={slug}
        open={rawOpen}
        onClose={() => setRawOpen(false)}
        onCreated={() => {
          refreshRaw();
        }}
      />
    </>
  );
}
