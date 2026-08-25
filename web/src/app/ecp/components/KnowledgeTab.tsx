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
import { App, Button, Segmented, Spin, Tree, Upload } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { EcpEmpty } from './common';

const { Dragger } = Upload;

const STATUS_LABEL: Record<string, string> = {
  pending: '排队中',
  extracting: '抽取中',
  embedding: '向量化',
  generating_wiki: '生成 wiki',
  done: '完成',
  failed: '失败',
};

type SideView = 'wiki' | 'raw';

function toTreeData(nodes: TreeNode[], isDirIcon?: (n: TreeNode) => boolean): any[] {
  return (nodes ?? []).map(n => ({
    key: n.path,
    title: n.name,
    isLeaf: !n.is_dir,
    children: n.children ? toTreeData(n.children, isDirIcon) : undefined,
    icon: n.is_dir ? undefined : (isDirIcon?.(n) ? <FileTextOutlined /> : <FileMarkdownOutlined />),
  }));
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

  const { run: doUpload } = useRequest(
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
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 12,
          flexWrap: 'wrap',
          gap: 10,
        }}
      >
        <span style={{ fontSize: 13, color: 'var(--ink-500)', maxWidth: 560 }}>
          在这里直接维护业务知识资产——拖拽上传原始文档自动生成词条，也可手动新建 / 编辑 wiki
          文档，无需跳转知识库模块。
        </span>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => {
              refreshWiki();
              refreshRaw();
              pollJobs();
            }}
          />
          <Button icon={<EditOutlined />} onClick={() => setWikiOpen(true)}>
            新建词条
          </Button>
          <Button icon={<FileTextOutlined />} onClick={() => setRawOpen(true)}>
            新建原始文件
          </Button>
        </div>
      </div>

      <Dragger
        multiple
        showUploadList={false}
        beforeUpload={file => {
          doUpload(file as File).catch(e => message.error(String(e)));
          return false;
        }}
        className="ecp-knowledge-dragger"
      >
        <p className="ant-upload-drag-icon" style={{ marginBottom: 4 }}>
          <InboxOutlined style={{ color: '#4f46e5', fontSize: 24 }} />
        </p>
        <p className="ant-upload-text" style={{ fontSize: 13, color: 'var(--ink-700)' }}>
          拖拽文件到此处批量上传，或点击选择
        </p>
        <p className="ant-upload-hint" style={{ fontSize: 12, color: 'var(--ink-400)' }}>
          pdf / docx / pptx / txt / md / xlsx / 图片 / 音频 / 视频
        </p>
      </Dragger>

      {pendingJobs.length > 0 && (
        <div
          style={{
            marginTop: 10,
            fontSize: 12,
            color: 'var(--brand)',
            background: 'var(--bg-fill)',
            padding: '6px 12px',
            borderRadius: 8,
          }}
        >
          {pendingJobs.length} 个文档解析任务进行中（
          {STATUS_LABEL[pendingJobs[0].status] ?? pendingJobs[0].status}），完成后可在「wiki
          词条」中查看
        </div>
      )}

      <div className="ecp-wiki">
        <div className="ecp-wiki__side">
          <div className="ecp-wiki__side-title">
            <span>知识资产</span>
            <code style={{ fontSize: 11 }}>{slug}</code>
          </div>
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
          <div style={{ marginTop: 10 }}>
            {side === 'wiki' ? (
              wikiLoading ? (
                <Spin style={{ display: 'block', margin: '32px auto' }} />
              ) : treeData.length ? (
                <Tree
                  showIcon
                  treeData={treeData}
                  selectedKeys={selectedDoc ? [selectedDoc] : []}
                  onSelect={keys => {
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
              <Spin style={{ display: 'block', margin: '32px auto' }} />
            ) : rawTreeData.length ? (
              <Tree
                showIcon
                treeData={rawTreeData}
                selectedKeys={selectedRaw ? [selectedRaw] : []}
                onSelect={keys => {
                  const k = keys[0] as string | undefined;
                  if (k && !k.endsWith('/')) setSelectedRaw(k);
                }}
              />
            ) : (
              <EcpEmpty title="暂无原始文件" desc="点「上传文档」或「新建原始文件」添加" />
            )}
          </div>
        </div>

        <div className="ecp-wiki__reader">
          {side === 'wiki' ? (
            !selectedDoc ? (
              <EcpEmpty title="从左侧选择一篇词条" desc="选中后可直接查看或编辑" />
            ) : docLoading ? (
              <Spin style={{ display: 'block', margin: '64px auto' }} />
            ) : doc ? (
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                  <div className="ecp-wiki__doc-title" style={{ flex: 1 }}>
                    {doc.title}
                  </div>
                  <Button
                    size="small"
                    type={editing ? 'default' : 'primary'}
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
                {!!doc.frontmatter?.ref && (
                  <div className="ecp-wiki__doc-ref">ref → {String(doc.frontmatter.ref)}</div>
                )}
                <div className="ecp-wiki__doc-body" style={{ height: editing ? 480 : 'auto' }}>
                  {editing ? (
                    <div style={{ height: 480, border: '1px solid var(--line-soft)', borderRadius: 8, overflow: 'hidden' }}>
                      <MarkdownEditor
                        value={draft}
                        onChange={t => {
                          setDraft(t);
                          setDirty(true);
                        }}
                      />
                    </div>
                  ) : (
                    doc.content
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
              <div className="ecp-wiki__doc-title">{selectedRaw}</div>
              <div className="ecp-wiki__doc-body">
                <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13, fontFamily: 'inherit', margin: 0 }}>
                  {rawContent.content}
                </pre>
              </div>
            </>
          ) : (
            <EcpEmpty title="读取失败" />
          )}
        </div>
      </div>

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
