'use client';

import { apiInterceptors } from '@/client/api';
import { proposeEcpObject, EcpSemanticObject } from '@/client/api/ecp';
import { useRequest } from 'ahooks';
import { App, Alert, Input, InputNumber, Modal, Select } from 'antd';
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
  const [objType, setObjType] = useState('metric');
  const [objectId, setObjectId] = useState('');
  const [confidence, setConfidence] = useState<number | undefined>();
  const [payload, setPayload] = useState<Record<string, any>>(emptyPayload('metric'));

  const changeType = (v: string) => {
    setObjType(v);
    setPayload(emptyPayload(v));
  };

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
      title="新增语义（手工配置）"
      open={open}
      onOk={() => submit()}
      confirmLoading={loading}
      onCancel={onClose}
      okText="提交提案"
      cancelText="取消"
    >
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
    </Modal>
  );
}
