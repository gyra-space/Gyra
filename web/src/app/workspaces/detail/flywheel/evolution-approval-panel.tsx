'use client';

/**
 * 剧本演化审批面板 —— 提议列表 + 差异预览 + 一键审批。
 *
 * 视觉:提议卡左侧色条按变更类型着色,操作行通过/拒绝按钮,
 * 差异预览弹窗展示 detector / diff 详情。
 */
import { useState } from 'react';
import { App, Button, Modal } from 'antd';
import {
  CheckOutlined,
  CloseOutlined,
  EyeOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';
import { useRequest } from 'ahooks';
import {
  approveEvolutionProposal,
  listEvolutionProposals,
  rejectEvolutionProposal,
  type EvolutionProposal,
} from '@/client/api/flywheel';

interface EvolutionApprovalPanelProps {
  workspaceId: number;
}

/** 变更类型 → 颜色(与飞轮语义色一致) */
const CHANGE_TYPE_STYLE: Record<string, { color: string; soft: string }> = {
  add_step: { color: 'var(--fw-evaluation)', soft: 'var(--fw-evaluation-soft)' },
  modify_prompt: { color: 'var(--fw-evolution)', soft: 'var(--fw-evolution-soft)' },
  adjust_gate: { color: 'var(--fw-trace)', soft: 'var(--fw-trace-soft)' },
  add_resource: { color: 'var(--fw-agent)', soft: 'var(--fw-agent-soft)' },
  remove_step: { color: 'var(--ws-danger, #ef4444)', soft: 'rgba(239, 68, 68, 0.08)' },
};

function changeStyle(changeType: string) {
  return (
    CHANGE_TYPE_STYLE[changeType] || {
      color: 'var(--ws-ink-2, #5d6577)',
      soft: 'var(--ws-bg, #f7f8fa)',
    }
  );
}

/** 差异预览弹窗 */
function DiffPreviewModal({
  proposal,
  open,
  onClose,
}: {
  proposal: EvolutionProposal | null;
  open: boolean;
  onClose: () => void;
}) {
  if (!proposal) return null;
  const entries = Object.entries(proposal.diff || {});

  return (
    <Modal
      title={
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
          <EyeOutlined />
          <span>差异预览</span>
        </span>
      }
      open={open}
      onCancel={onClose}
      footer={null}
      width={640}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div style={{ borderRadius: 8, background: '#f7f8fa', padding: 12 }}>
          <div style={{ fontSize: 11.5, color: '#8a92a6', marginBottom: 4 }}>提议描述</div>
          <div style={{ fontSize: 13, color: '#14161c' }}>{proposal.description || '无描述'}</div>
        </div>
        <div style={{ borderRadius: 8, background: '#f7f8fa', padding: 12 }}>
          <div style={{ fontSize: 11.5, color: '#8a92a6', marginBottom: 4 }}>检测器</div>
          <span
            className="ws-flywheel__proposal-type"
            style={changeStyle(proposal.change_type) as React.CSSProperties}
          >
            {proposal.detector_name}
          </span>
        </div>
        <div style={{ borderRadius: 8, background: '#f7f8fa', padding: 12 }}>
          <div style={{ fontSize: 11.5, color: '#8a92a6', marginBottom: 4 }}>变更内容</div>
          {entries.length > 0 ? (
            entries.map(([key, value]) => (
              <div key={key} style={{ fontSize: 12, marginBottom: 8 }}>
                <span style={{ fontWeight: 500, color: '#5d6577' }}>{key}:</span>
                <pre
                  style={{
                    marginTop: 4,
                    overflowX: 'auto',
                    borderRadius: 6,
                    background: '#fff',
                    padding: 8,
                    fontSize: 12,
                    color: '#14161c',
                  }}
                >
                  {JSON.stringify(value, null, 2)}
                </pre>
              </div>
            ))
          ) : (
            <div style={{ fontSize: 12, color: '#8a92a6' }}>无差异内容</div>
          )}
        </div>
      </div>
    </Modal>
  );
}

/** 审批操作弹窗 */
function ApprovalModal({
  proposal,
  action,
  open,
  onClose,
  onSubmit,
}: {
  proposal: EvolutionProposal | null;
  action: 'approve' | 'reject' | null;
  open: boolean;
  onClose: () => void;
  onSubmit: (reason: string) => Promise<void>;
}) {
  const [reason, setReason] = useState('');
  if (!proposal || !action) return null;
  const isApprove = action === 'approve';

  return (
    <Modal
      title={
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
          {isApprove ? (
            <CheckOutlined style={{ color: '#22c55e' }} />
          ) : (
            <CloseOutlined style={{ color: '#ef4444' }} />
          )}
          <span>{isApprove ? '审批通过' : '拒绝提议'}</span>
        </span>
      }
      open={open}
      onCancel={onClose}
      onOk={() => onSubmit(reason)}
      okText="确认"
      cancelText="取消"
      okButtonProps={isApprove ? {} : { danger: true }}
    >
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 13, color: '#14161c', marginBottom: 8 }}>
          {isApprove ? '确认通过此演化提议?' : '确认拒绝此演化提议?'}
        </div>
        <div style={{ borderRadius: 8, background: '#f7f8fa', padding: 12, fontSize: 12, color: '#5d6577' }}>
          {proposal.description || proposal.detector_name}
        </div>
      </div>
      {!isApprove && (
        <div>
          <label style={{ display: 'block', fontSize: 11.5, color: '#5d6577', marginBottom: 4 }}>
            拒绝原因
          </label>
          <textarea
            className="w-full h-20 rounded-lg border border-[#e5e8ef] bg-white px-3 py-2 text-[13px] resize-none focus:border-[#ef4444] focus:outline-none transition-colors"
            placeholder="说明拒绝的原因(可选)"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </div>
      )}
    </Modal>
  );
}

export function EvolutionApprovalPanel({ workspaceId }: EvolutionApprovalPanelProps) {
  const { message } = App.useApp();
  const [selectedProposal, setSelectedProposal] = useState<EvolutionProposal | null>(null);
  const [diffModalOpen, setDiffModalOpen] = useState(false);
  const [approvalModalOpen, setApprovalModalOpen] = useState(false);
  const [approvalAction, setApprovalAction] = useState<'approve' | 'reject' | null>(null);

  const { data: proposals, refresh } = useRequest(
    async () => {
      const res = await listEvolutionProposals({ workspace_id: workspaceId });
      return res.data?.data || [];
    },
    { refreshDeps: [workspaceId] },
  );

  const pendingProposals = (proposals || []).filter((p) => p.status === 'pending');

  const handleApprovalSubmit = async (reason: string) => {
    if (!selectedProposal || !approvalAction) return;
    try {
      if (approvalAction === 'approve') {
        await approveEvolutionProposal(selectedProposal.proposal_id, { reviewer: 'user' });
        message.success('审批通过');
      } else {
        await rejectEvolutionProposal(selectedProposal.proposal_id, {
          reviewer: 'user',
          reason,
        });
        message.success('已拒绝');
      }
      setApprovalModalOpen(false);
      refresh();
    } catch (e) {
      const err = e as Error;
      message.error(err.message || '操作失败');
    }
  };

  return (
    <>
      <div className="ws-flywheel__card">
        <div className="ws-flywheel__card-head">
          <span className="ws-flywheel__card-icon" style={{ color: 'var(--fw-evolution)' }}>
            <ExperimentOutlined />
          </span>
          <span className="ws-flywheel__card-title">剧本演化审批</span>
          <span
            className="ws-flywheel__card-chip"
            style={
              pendingProposals.length > 0
                ? { color: 'var(--fw-trace)', background: 'var(--fw-trace-soft)' }
                : undefined
            }
          >
            {pendingProposals.length} 待审批
          </span>
        </div>
        <div className="ws-flywheel__card-body">
          {pendingProposals.length > 0 ? (
            pendingProposals.map((p) => {
              const style = changeStyle(p.change_type);
              return (
                <div
                  key={p.proposal_id}
                  className="ws-flywheel__proposal"
                  style={
                    {
                      '--proposal-color': style.color,
                      '--proposal-soft': style.soft,
                    } as React.CSSProperties
                  }
                >
                  <div className="ws-flywheel__proposal-head">
                    <span className="ws-flywheel__proposal-type">{p.change_type}</span>
                    <span className="ws-flywheel__proposal-detector">{p.detector_name}</span>
                  </div>
                  <div className="ws-flywheel__proposal-desc">{p.description || '无描述'}</div>
                  <div className="ws-flywheel__proposal-meta">
                    由 {p.proposed_by} 提议 · {new Date(p.gmt_created).toLocaleString('zh-CN')}
                  </div>
                  <div className="ws-flywheel__proposal-ops">
                    <Button
                      size="small"
                      icon={<EyeOutlined />}
                      onClick={() => {
                        setSelectedProposal(p);
                        setDiffModalOpen(true);
                      }}
                    >
                      查看差异
                    </Button>
                    <Button
                      size="small"
                      type="primary"
                      icon={<CheckOutlined />}
                      onClick={() => {
                        setSelectedProposal(p);
                        setApprovalAction('approve');
                        setApprovalModalOpen(true);
                      }}
                    >
                      通过
                    </Button>
                    <Button
                      size="small"
                      danger
                      icon={<CloseOutlined />}
                      onClick={() => {
                        setSelectedProposal(p);
                        setApprovalAction('reject');
                        setApprovalModalOpen(true);
                      }}
                    >
                      拒绝
                    </Button>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="ws-flywheel__empty">
              <div className="ws-flywheel__empty-title">暂无待审批的演化提议</div>
              <div className="ws-flywheel__empty-hint">
                飞轮积累足够执行轨迹后,演化检测器会自动提出 playbook 优化建议
              </div>
            </div>
          )}
        </div>
      </div>

      <DiffPreviewModal
        proposal={selectedProposal}
        open={diffModalOpen}
        onClose={() => setDiffModalOpen(false)}
      />
      <ApprovalModal
        proposal={selectedProposal}
        action={approvalAction}
        open={approvalModalOpen}
        onClose={() => setApprovalModalOpen(false)}
        onSubmit={handleApprovalSubmit}
      />
    </>
  );
}
