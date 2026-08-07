'use client';

/**
 * 移动端 ECP 提案详情 —— 在通知里点击「查看详情」后弹出。
 * 复用桌面端定位逻辑:source_id = `{ecp_ws}:{obj.id}@v{version}`,定位到待办指向的
 * proposed 版本;仅 status=proposed 时允许确认/否决,否则提示陈旧并允许关闭。
 */
import { apiInterceptors } from '@/client/api';
import {
  confirmEcpObject,
  getEcpObjectVersions,
  rejectEcpObject,
  type EcpSemanticObject,
} from '@/client/api/ecp';
import { getUserId } from '@/utils/storage';
import { CheckOutlined, CloseOutlined } from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { App, Modal, Spin } from 'antd';
import { useEffect, useState } from 'react';

import type { InboxItem } from '@/client/api';

interface MobileProposalDetailProps {
  item: InboxItem | null;
  onClose: () => void;
  onResolved: () => void;
}

interface ParsedSource {
  workspaceId: string;
  objId: string;
  version: number;
}

function parseSource(sourceId: string): ParsedSource | null {
  const m = sourceId.match(/^(.+):(.+)@v(\d+)$/);
  if (!m) return null;
  return { workspaceId: m[1], objId: m[2], version: Number(m[3]) };
}

const TYPE_LABEL: Record<string, string> = {
  entity: '实体',
  metric: '指标',
  relation: '关系',
  dimension: '维度',
  claim: '断言',
  terminology: '术语',
  policy: '策略',
};

const STATUS_LABEL: Record<string, string> = {
  proposed: '提案中',
  confirmed: '已确认',
  rejected: '已否决',
  deprecated: '已废弃',
  superseded: '已被取代',
};

function Kv({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="ms-prop__kv">
      <span className="ms-prop__k">{k}</span>
      <span className="ms-prop__v">{v}</span>
    </div>
  );
}

export default function MobileProposalDetail({
  item,
  onClose,
  onResolved,
}: MobileProposalDetailProps) {
  const { message } = App.useApp();
  const parsed = item && item.source_type === 'ecp_proposal' ? parseSource(item.source_id) : null;
  const [acting, setActing] = useState<'confirm' | 'reject' | null>(null);

  const { data: versions, loading } = useRequest(
    async () => {
      if (!parsed) return [];
      const [err, res] = await apiInterceptors(
        getEcpObjectVersions(parsed.objId, parsed.workspaceId),
      );
      if (err) {
        message.error(err.message);
        return [];
      }
      return res ?? [];
    },
    { refreshDeps: [item?.id], ready: !!parsed },
  );

  const obj: EcpSemanticObject | null = parsed
    ? (versions || []).find((v) => v.version === parsed.version) ?? null
    : null;

  // 提案已离开 proposed(已确认/否决/废弃) -> 待办陈旧,让收件箱消除。
  useEffect(() => {
    if (obj && obj.status !== 'proposed') {
      onResolved();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [obj?.id, obj?.status]);

  const api = (action: 'confirm' | 'reject') =>
    action === 'confirm' ? confirmEcpObject : rejectEcpObject;

  const settle = async (action: 'confirm' | 'reject') => {
    if (!obj || acting) return;
    setActing(action);
    try {
      const [err] = await apiInterceptors(
        api(action)(obj.id, obj.version, {
          user_id: String(getUserId() ?? 'unknown'),
          workspace_id: obj.workspace_id,
        }),
      );
      if (err) {
        message.error(err.message);
        return;
      }
      message.success(action === 'confirm' ? '已确认生效' : '已否决');
      onResolved();
      onClose();
    } finally {
      setActing(null);
    }
  };

  return (
    <Modal
      open={!!item}
      footer={null}
      centered
      destroyOnClose
      width={360}
      style={{ maxWidth: 'calc(100vw - 32px)' }}
      title={
        <div className="ms-prop__head">
          <span className="ms-prop__type">{obj ? TYPE_LABEL[obj.obj_type] || obj.obj_type : '提案'}</span>
          <span className="ms-prop__id">{obj?.id ?? item?.title ?? ''}</span>
          {obj && <span className="ms-prop__ver">v{obj.version}</span>}
        </div>
      }
      onCancel={() => {
        onClose();
      }}
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: '32px 0' }}>
          <Spin />
        </div>
      ) : !obj ? (
        <div className="ms-prop__empty">提案未找到（可能已被删除）</div>
      ) : obj.status !== 'proposed' ? (
        <div className="ms-prop__empty">
          该提案已处理
          <span className="ms-prop__status">{STATUS_LABEL[obj.status] || obj.status}</span>
        </div>
      ) : (
        <div className="ms-prop">
          <Kv k="状态" v={<span className="ms-prop__status">{STATUS_LABEL[obj.status] || obj.status}</span>} />
          <Kv k="名称" v={obj.name ?? '-'} />
          <Kv k="别名" v={(obj.payload?.aliases || []).join(' / ') || '-'} />
          <Kv k="说明" v={obj.payload?.description || obj.payload?.summary || '-'} />
          <Kv k="来源" v={obj.source ?? '-'} />

          {!!obj.evidence?.length && (
            <div className="ms-prop__section">
              <div className="ms-prop__section-title">证据引文</div>
              {obj.evidence.map((ev, i) => (
                <div key={i} className="ms-prop__evidence">
                  {ev.source ?? '来源未知'}：{ev.quote ?? ''}
                </div>
              ))}
            </div>
          )}

          <div className="ms-prop__section">
            <div className="ms-prop__section-title">Payload</div>
            <pre className="ms-prop__payload">{JSON.stringify(obj.payload, null, 2)}</pre>
          </div>

          <div className="ms-prop__actions">
            <button
              type="button"
              className="ms-notif__act ms-notif__act--danger"
              disabled={!!acting}
              onClick={() => settle('reject')}
            >
              <CloseOutlined /> {acting === 'reject' ? '处理中…' : '否决'}
            </button>
            <button
              type="button"
              className="ms-notif__act ms-notif__act--primary"
              disabled={!!acting}
              onClick={() => settle('confirm')}
            >
              <CheckOutlined /> {acting === 'confirm' ? '处理中…' : '确认生效'}
            </button>
          </div>
        </div>
      )}
    </Modal>
  );
}