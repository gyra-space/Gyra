'use client';

import { useEffect, useState } from 'react';
import { apiInterceptors } from '@/client/api';
import { startFeishuWikiSync, testFeishuWiki } from '@/client/api/knowledge-vault';
import type { FeishuWikiSpace } from '@/types/knowledge-vault';
import { ApiOutlined, CloudDownloadOutlined } from '@ant-design/icons';
import { App, Button, Input, Modal, Select, Space, Typography } from 'antd';

export default function WikiSyncModal({
  slug,
  open,
  onClose,
  onStarted,
}: {
  slug: string;
  open: boolean;
  onClose: () => void;
  onStarted?: () => void;
}) {
  const { message } = App.useApp();
  const [domain, setDomain] = useState('https://open.feishu.cn');
  const [appId, setAppId] = useState('');
  const [appSecret, setAppSecret] = useState('');
  const [llmModel, setLlmModel] = useState('');
  const [spaces, setSpaces] = useState<FeishuWikiSpace[]>([]);
  const [spaceId, setSpaceId] = useState<string>();
  const [testing, setTesting] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setSpaces([]);
      setSpaceId(undefined);
    }
  }, [open]);

  async function testConnection() {
    if (!appId.trim() || !appSecret.trim()) {
      message.warning('请先填写 App ID 和 App Secret');
      return;
    }
    setTesting(true);
    try {
      const [, res] = await apiInterceptors(
        testFeishuWiki(slug, {
          app_id: appId.trim(),
          app_secret: appSecret.trim(),
          domain: domain.trim() || undefined,
        }),
      );
      if (res?.ok) {
        setSpaces(res.spaces || []);
        message.success(`连接成功，获取到 ${res.spaces?.length ?? 0} 个知识库`);
      } else {
        setSpaces([]);
        message.error(`连接失败: ${res?.error || '未知错误'}`);
      }
    } finally {
      setTesting(false);
    }
  }

  async function submit() {
    if (!spaceId) {
      message.warning('请先测试连接并选择要同步的知识库');
      return;
    }
    setSubmitting(true);
    try {
      const [, res] = await apiInterceptors(
        startFeishuWikiSync(slug, {
          app_id: appId.trim(),
          app_secret: appSecret.trim(),
          domain: domain.trim() || undefined,
          wiki_space_id: spaceId,
          llm_model: llmModel.trim() || null,
        }),
      );
      if (res) {
        message.success(`同步任务已启动 (${res.job_id})，可在任务列表中查看进度`);
        onClose();
        onStarted?.();
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      title={
        <Space>
          <CloudDownloadOutlined />
          从飞书知识库同步
        </Space>
      }
      open={open}
      onCancel={onClose}
      onOk={submit}
      okText="开始同步"
      okButtonProps={{ disabled: !spaceId }}
      confirmLoading={submitting}
      width={520}
      destroyOnClose
    >
      <div className="flex flex-col gap-3 pt-1">
        <Typography.Text type="secondary" className="!text-xs">
          使用飞书自建应用凭证拉取知识库页面：页面会作为 L0 verbatim 入库，
          并自动生成 L1 wiki。凭证仅用于本次请求，不会在服务端保存。
        </Typography.Text>
        <div>
          <label className="text-xs text-gray-500">OpenAPI 域名</label>
          <Select
            value={domain}
            onChange={setDomain}
            className="w-full"
            options={[
              { value: 'https://open.feishu.cn', label: '飞书 (open.feishu.cn)' },
              { value: 'https://open.larksuite.com', label: 'Lark (open.larksuite.com)' },
            ]}
          />
        </div>
        <div>
          <label className="text-xs text-gray-500">App ID</label>
          <Input
            value={appId}
            onChange={(e) => setAppId(e.target.value)}
            placeholder="cli_xxx"
          />
        </div>
        <div>
          <label className="text-xs text-gray-500">App Secret</label>
          <Input.Password
            value={appSecret}
            onChange={(e) => setAppSecret(e.target.value)}
            placeholder="应用密钥"
          />
        </div>
        <div>
          <Button
            icon={<ApiOutlined />}
            loading={testing}
            onClick={testConnection}
          >
            测试连接并获取知识库
          </Button>
        </div>
        <div>
          <label className="text-xs text-gray-500">选择知识库</label>
          <Select
            value={spaceId}
            onChange={setSpaceId}
            className="w-full"
            placeholder={spaces.length ? '选择要同步的知识库' : '请先测试连接'}
            disabled={!spaces.length}
            showSearch
            optionFilterProp="label"
            options={spaces.map((s) => ({
              value: s.space_id,
              label: s.name || s.space_id,
            }))}
          />
        </div>
        <div>
          <label className="text-xs text-gray-500">
            LLM 模型（可选，留空使用空间默认）
          </label>
          <Input
            value={llmModel}
            onChange={(e) => setLlmModel(e.target.value)}
            placeholder="用于生成 L1 wiki 的模型"
          />
        </div>
      </div>
    </Modal>
  );
}
