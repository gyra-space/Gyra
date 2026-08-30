'use client';

import { apiInterceptors } from '@/client/api';
import { addEcpObjectFromSql, EcpSemanticObject, importEcpObjectFromFile, proposeEcpObject } from '@/client/api/ecp';
import { getUserId } from '@/utils';
import { useRequest } from 'ahooks';
import { App, Alert, Button, Input, InputNumber, Modal, Select, Tabs, Upload } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import { useState } from 'react';

import PayloadEditor from './PayloadEditor';

const OBJ_TYPES = ['entity', 'metric', 'relation', 'dimension', 'claim', 'terminology', 'policy'];

function emptyPayload(objType: string): Record<string, any> {
  switch (objType) {
    case 'entity':
      return { binding: { kind: 'db', table: '', pk: '', datasource_id: undefined }, aliases: [], default_filters: [] };
    case 'metric':
      return { entity: '', expression: '', unit: '', grain: [], extra_filters: [], aliases: [] };
    case 'dimension':
      return { column: '', aliases: [], values: [] };
    case 'relation':
      return { from: '', to: '', cardinality: '', path: '' };
    case 'claim':
      return { text: '', source_quote: '', binding: { kind: 'doc', doc_id: '', space: '' } };
    case 'terminology':
      return { definition: '', aliases: [], binding: { kind: 'doc', doc_id: '', space: '' } };
    case 'policy':
      return { rule: '', condition: '', source_quote: '', binding: { kind: 'doc', doc_id: '', space: '' } };
    default:
      return {};
  }
}

function idPrefix(objType: string): string {
  if (objType === 'entity') return 'ent.';
  if (objType === 'metric') return 'mtr.';
  if (objType === 'relation') return 'rel.';
  if (objType === 'dimension') return 'dim.';
  return `${objType}.`;
}

export default function CreateProposalModal({
  workspaceId,
  open,
  onClose,
  onCreated,
}: {
  workspaceId: string;
  open: boolean;
  onClose: () => void;
  onCreated?: () => void;
}) {
  const { message } = App.useApp();
  // 默认走「给 SQL 添加语义」(添加即确认)；高级模式保留手工配置(进收件箱)
  const [tab, setTab] = useState('sql');
  const [sql, setSql] = useState('');
  const [desc, setDesc] = useState('');
  // 报表文件导入:整份文件异步提炼,产出进待确认收件箱;选中文件时优先于手贴 SQL
  const [file, setFile] = useState<File | null>(null);

  const [objType, setObjType] = useState('metric');
  const [objectId, setObjectId] = useState('');
  const [confidence, setConfidence] = useState<number | undefined>();
  const [payload, setPayload] = useState<Record<string, any>>(emptyPayload('metric'));

  const changeType = (v: string) => {
    setObjType(v);
    setPayload(emptyPayload(v));
  };

  const { run: submitSql, loading: sqlLoading } = useRequest(
    async () => {
      if (file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('workspace_id', workspaceId);
        if (desc.trim()) formData.append('description', desc.trim());
        const [err, res] = await apiInterceptors(importEcpObjectFromFile(formData));
        if (err) throw err;
        return { fileTask: true, taskId: res?.task_id };
      }
      if (!sql.trim()) throw new Error('请填写 SQL,或上传报表文件');
      const uid = getUserId() || 'user';
      const [err, res] = await apiInterceptors(
        addEcpObjectFromSql({
          sql: sql.trim(),
          description: desc.trim() || undefined,
          workspace_id: workspaceId,
          user_id: uid,
          confirm: true,
        }),
      );
      if (err) throw err;
      return res;
    },
    {
      manual: true,
      onSuccess: (res: any) => {
        if (res?.fileTask) {
          message.success('文件已提交,助手正在后台整份学习提炼,完成后请到「业务口径」收件箱确认提案');
          setFile(null);
          setSql('');
          setDesc('');
          onCreated?.();
          onClose();
          return;
        }
        const confirmed = res?.confirmed_ids ?? [];
        const errors = res?.errors ?? [];
        if (confirmed.length > 0) {
          message.success(
            `已添加并确认 ${confirmed.length} 条口径：${confirmed.join('、')}`,
          );
        } else if (errors.length > 0) {
          message.warning(`未添加成功：${errors[0]}`);
        } else {
          message.info('未提炼出新的语义（可能已存在同类口径，或助手未找到可提炼内容）');
        }
        setSql('');
        setDesc('');
        onCreated?.();
        onClose();
      },
      onError: (e: Error) => message.error(String(e?.message ?? e)),
    },
  );

  const { run: submit, loading } = useRequest(
    async () => {
      if (!objectId.trim()) throw new Error('请填写对象 ID');
      const [err, res] = await apiInterceptors(
        proposeEcpObject({
          id: objectId.trim(),
          obj_type: objType,
          payload,
          workspace_id: workspaceId,
          confidence,
          created_by: 'user',
          source: 'user:manual',
        }),
      );
      if (err) throw err;
      return res;
    },
    {
      manual: true,
      onSuccess: (res: EcpSemanticObject | undefined) => {
        message.success(res?.status === 'confirmed' ? '已存在相同已确认口径，未重复提案' : `已提交提案 ${res?.id}@v${res?.version}，请到「业务口径」确认`);
        onCreated?.();
        onClose();
      },
      onError: (e: Error) => message.error(String(e?.message ?? e)),
    },
  );

  return (
    <Modal
      title="新增语义"
      open={open}
      onOk={() => (tab === 'sql' ? submitSql() : submit())}
      confirmLoading={tab === 'sql' ? sqlLoading : loading}
      onCancel={onClose}
      okText={tab === 'sql' ? (file ? '提交提炼' : '添加并确认') : '提交提案'}
      cancelText="取消"
      width={640}
    >
      <Tabs
        activeKey={tab}
        onChange={setTab}
        items={[
          {
            key: 'sql',
            label: '用 SQL 添加（推荐）',
            children: (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <Alert
                  type="info"
                  showIcon
                  message="填入一条 SQL,助手会自动提炼出指标/实体/维度等语义,并直接生效为已确认口径(添加即确认);或上传一份报表文件(SQL 脚本/代码),助手在后台整份学习提炼,提案进待确认收件箱。需已在「治理」配置提案 Agent。"
                />
                <div>
                  <div style={{ fontSize: 12, color: 'var(--ink-500)', marginBottom: 4 }}>
                    SQL（必填，上传文件时以文件为准）
                  </div>
                  <textarea
                    rows={5}
                    placeholder={'示例：SELECT store, SUM(amount) AS sales FROM orders WHERE status=\x27paid\x27 GROUP BY store'}
                    value={sql}
                    onChange={e => setSql(e.target.value)}
                    style={{
                      width: '100%',
                      padding: 8,
                      borderRadius: 8,
                      border: '1px solid var(--line-soft, #f0f0f0)',
                      fontSize: 13,
                      fontFamily: 'monospace',
                      resize: 'vertical',
                    }}
                  />
                </div>
                <div>
                  <div style={{ fontSize: 12, color: 'var(--ink-500)', marginBottom: 4 }}>
                    报表文件（可选，.sql / .txt / 代码文件，≤50MB，助手分段通读全文）
                  </div>
                  <Upload
                    maxCount={1}
                    accept=".sql,.txt,.py,.java,.md"
                    beforeUpload={f => {
                      if (f.size > 50 * 1024 * 1024) {
                        message.error('文件超过 50MB');
                        return Upload.LIST_IGNORE;
                      }
                      setFile(f);
                      return false;
                    }}
                    onRemove={() => setFile(null)}
                    fileList={file ? [{ uid: '-1', name: file.name }] : []}
                  >
                    <Button size="small" icon={<UploadOutlined />}>
                      选择文件
                    </Button>
                  </Upload>
                </div>
                <div>
                  <div style={{ fontSize: 12, color: 'var(--ink-500)', marginBottom: 4 }}>
                    业务说明（可选，帮助助手理解口径）
                  </div>
                  <Input
                    size="small"
                    placeholder="例：各门店已付款订单的销售金额"
                    value={desc}
                    onChange={e => setDesc(e.target.value)}
                  />
                </div>
              </div>
            ),
          },
          {
            key: 'advanced',
            label: '高级手工配置',
            children: (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <Alert
                  type="info"
                  showIcon
                  message="手工配置的语义会进入待确认收件箱，确认后才会生效；可执行契约不满足时后端会拒绝并说明缺失字段。"
                />
                <div>
                  <div style={{ fontSize: 12, color: 'var(--ink-500)', marginBottom: 4 }}>类型</div>
                  <Select
                    size="small"
                    style={{ width: '100%' }}
                    value={objType}
                    onChange={changeType}
                    options={OBJ_TYPES.map(v => ({ value: v, label: v }))}
                  />
                </div>
                <div>
                  <div style={{ fontSize: 12, color: 'var(--ink-500)', marginBottom: 4 }}>对象 ID</div>
                  <Input
                    size="small"
                    value={objectId}
                    placeholder={`如 ${idPrefix(objType)}order`}
                    onChange={e => setObjectId(e.target.value)}
                  />
                </div>
                <div>
                  <div style={{ fontSize: 12, color: 'var(--ink-500)', marginBottom: 4 }}>置信度 confidence（0-1，可选）</div>
                  <InputNumber
                    size="small"
                    style={{ width: '100%' }}
                    min={0}
                    max={1}
                    step={0.05}
                    value={confidence}
                    onChange={setConfidence}
                  />
                </div>
                <div style={{ borderTop: '1px solid var(--border-subtle, #f0f0f0)', paddingTop: 12 }}>
                  <div style={{ fontSize: 12, color: 'var(--ink-500)', marginBottom: 8 }}>Payload</div>
                  <PayloadEditor objType={objType} value={payload} onChange={setPayload} />
                </div>
              </div>
            ),
          },
        ]}
      />
    </Modal>
  );
}
