'use client';

/**
 * 评委工作台 —— 四种评委动作一键操作。
 *
 * 视觉:四动作色块矩阵(背书/纠偏/升级/对账),
 * 待评委列表复用 ws item 语言,行内图标按钮触发动作。
 */
import { useState } from 'react';
import { App, Modal, Select, Tooltip } from 'antd';
import {
  AuditOutlined,
  CheckCircleOutlined,
  EditOutlined,
  ExclamationCircleOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { useRequest } from 'ahooks';
import {
  createAttestIntervention,
  createCoachIntervention,
  createEscalateIntervention,
  createReconcileIntervention,
  listAgentMaturity,
} from '@/client/api/flywheel';

interface JudgeBenchProps {
  workspaceId: number;
  onActionComplete?: () => void;
}

/** 待评委项 */
interface JudgeItem {
  id: number;
  title: string;
  type: 'asset' | 'intervention';
  agent_id?: string;
  description?: string;
  status: string;
}

/** 动作配置(varName 对应 flywheel.css 语义色) */
const ACTION_CONFIG = {
  attest: {
    label: '背书',
    icon: <CheckCircleOutlined />,
    varName: '--fw-asset',
    description: '认可资产/Agent 产出,提升成熟度',
    fields: ['note'],
  },
  coach: {
    label: '纠偏',
    icon: <EditOutlined />,
    varName: '--fw-trace',
    description: '指出错误,降低成熟度,Agent 扣分',
    fields: ['coach_note', 'severity'],
  },
  escalate: {
    label: '升级',
    icon: <ExclamationCircleOutlined />,
    varName: '--fw-danger',
    description: '问题转交更高级别处理',
    fields: ['reason'],
  },
  reconcile: {
    label: '对账',
    icon: <SyncOutlined />,
    varName: '--fw-evaluation',
    description: '触发索引对账,发现资产漂移',
    fields: ['description'],
  },
} as const;

type ActionKey = keyof typeof ACTION_CONFIG;

/** 取动作主色(escalate 用 danger 色,其余用语义色) */
function actionColor(varName: string): string {
  return varName === '--fw-danger' ? 'var(--ws-danger, #ef4444)' : `var(${varName})`;
}

export function JudgeBench({ workspaceId, onActionComplete }: JudgeBenchProps) {
  const { message } = App.useApp();
  const [modalOpen, setModalOpen] = useState(false);
  const [currentAction, setCurrentAction] = useState<ActionKey | null>(null);
  const [currentItem, setCurrentItem] = useState<JudgeItem | null>(null);
  const [formData, setFormData] = useState<Record<string, string | number | undefined>>({});

  // Agent 列表(供背书/纠偏选择,后续接真实待评委源)
  useRequest(
    async () => {
      const res = await listAgentMaturity(workspaceId);
      return res.data?.data || [];
    },
    { refreshDeps: [workspaceId] },
  );

  // 待评委列表(TODO: 接入真实待评委 API)
  const { data: pendingItems, refresh: refreshPending } = useRequest(
    async () =>
      [
        {
          id: 1,
          title: '资产 #1: 月报模板',
          type: 'asset' as const,
          agent_id: 'analyst_v1',
          description: 'Agent 产出的月报模板,待确认',
          status: 'proposed',
        },
        {
          id: 2,
          title: '资产 #2: 数据口径定义',
          type: 'asset' as const,
          agent_id: 'fetcher_v1',
          description: '新增数据口径定义,待背书',
          status: 'proposed',
        },
      ],
    { refreshDeps: [workspaceId] },
  );

  const handleActionClick = (action: ActionKey, item: JudgeItem) => {
    setCurrentAction(action);
    setCurrentItem(item);
    setFormData({});
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    if (!currentAction || !currentItem) return;
    const action = ACTION_CONFIG[currentAction];
    const base = {
      workspace_id: workspaceId,
      user_id: 1, // TODO: 从 auth context 获取
    };
    const note = typeof formData.note === 'string' ? formData.note : undefined;
    const reason = typeof formData.reason === 'string' ? formData.reason : undefined;
    const description = typeof formData.description === 'string' ? formData.description : undefined;
    const coachNote = typeof formData.coach_note === 'string' ? formData.coach_note : undefined;
    const severity = formData.severity === 'major' ? 'major' : 'minor';
    try {
      switch (currentAction) {
        case 'attest':
          await createAttestIntervention({
            ...base,
            agent_id: currentItem.agent_id || '',
            asset_id: currentItem.type === 'asset' ? currentItem.id : undefined,
            task_id: currentItem.type === 'intervention' ? currentItem.id : undefined,
            note,
          });
          break;
        case 'coach':
          await createCoachIntervention({
            ...base,
            agent_id: currentItem.agent_id || '',
            asset_id: currentItem.type === 'asset' ? currentItem.id : undefined,
            task_id: currentItem.type === 'intervention' ? currentItem.id : undefined,
            coach_note: coachNote || '',
            severity,
          });
          break;
        case 'escalate':
          await createEscalateIntervention({
            ...base,
            task_id: currentItem.type === 'intervention' ? currentItem.id : undefined,
            reason: reason || '',
          });
          break;
        case 'reconcile':
          await createReconcileIntervention({
            ...base,
            task_id: currentItem.type === 'intervention' ? currentItem.id : undefined,
            description: description || '',
          });
          break;
      }
      message.success(`${action.label}成功`);
      setModalOpen(false);
      refreshPending();
      onActionComplete?.();
    } catch (e) {
      const err = e as Error;
      message.error(err.message || `${action.label}失败`);
    }
  };

  const renderField = (field: string) => {
    const textareaCls =
      'w-full h-20 rounded-lg border border-[#e5e8ef] bg-white px-3 py-2 text-[13px] resize-none focus:border-[#4f46e5] focus:outline-none transition-colors';
    const labelCls = 'block text-[11.5px] text-[#5d6577] mb-1';
    switch (field) {
      case 'note':
        return (
          <div key={field} className="mb-3">
            <label className={labelCls}>备注</label>
            <textarea
              className={textareaCls}
              placeholder="添加背书备注(可选)"
              value={formData.note || ''}
              onChange={(e) => setFormData((p) => ({ ...p, note: e.target.value }))}
            />
          </div>
        );
      case 'coach_note':
        return (
          <div key={field} className="mb-3">
            <label className={labelCls}>纠偏说明</label>
            <textarea
              className={textareaCls}
              placeholder="说明需要纠偏的具体内容"
              value={formData.coach_note || ''}
              onChange={(e) => setFormData((p) => ({ ...p, coach_note: e.target.value }))}
            />
          </div>
        );
      case 'severity':
        return (
          <div key={field} className="mb-3">
            <label className={labelCls}>严重程度</label>
            <Select
              className="w-full"
              value={formData.severity || 'minor'}
              onChange={(v) => setFormData((p) => ({ ...p, severity: v }))}
              options={[
                { label: '轻微 (minor)', value: 'minor' },
                { label: '严重 (major)', value: 'major' },
              ]}
            />
          </div>
        );
      case 'reason':
        return (
          <div key={field} className="mb-3">
            <label className={labelCls}>升级原因</label>
            <textarea
              className={textareaCls}
              placeholder="说明需要升级处理的原因"
              value={formData.reason || ''}
              onChange={(e) => setFormData((p) => ({ ...p, reason: e.target.value }))}
            />
          </div>
        );
      case 'description':
        return (
          <div key={field} className="mb-3">
            <label className={labelCls}>对账描述</label>
            <textarea
              className={textareaCls}
              placeholder="描述对账范围或关注点"
              value={formData.description || ''}
              onChange={(e) => setFormData((p) => ({ ...p, description: e.target.value }))}
            />
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="ws-flywheel__card">
      <div className="ws-flywheel__card-head">
        <span className="ws-flywheel__card-icon"><AuditOutlined /></span>
        <span className="ws-flywheel__card-title">评委工作台</span>
        <span
          className="ws-flywheel__card-chip"
          style={
            (pendingItems?.length || 0) > 0
              ? { color: 'var(--fw-trace)', background: 'var(--fw-trace-soft)' }
              : undefined
          }
        >
          {pendingItems?.length || 0} 待评委
        </span>
      </div>
      <div className="ws-flywheel__card-body">
        {/* 动作矩阵 */}
        <div className="ws-flywheel__actions">
          {(Object.keys(ACTION_CONFIG) as ActionKey[]).map((key) => {
            const action = ACTION_CONFIG[key];
            const color = actionColor(action.varName);
            return (
              <button
                key={key}
                type="button"
                className="ws-flywheel__action"
                style={
                  {
                    '--action-color': color,
                    '--action-soft': `var(${action.varName}-soft, var(--ws-bg))`,
                  } as React.CSSProperties
                }
                onClick={() => {
                  const first = (pendingItems || [])[0];
                  if (first) handleActionClick(key, first);
                  else message.info('暂无待评委项');
                }}
              >
                <span className="ws-flywheel__action-icon">{action.icon}</span>
                <span className="ws-flywheel__action-label">{action.label}</span>
                <span className="ws-flywheel__action-desc">{action.description}</span>
              </button>
            );
          })}
        </div>

        {/* 待评委列表 */}
        {(pendingItems || []).map((item) => (
          <div key={item.id} className="ws-flywheel__item">
            <div className="ws-flywheel__item-main">
              <div className="ws-flywheel__item-title">{item.title}</div>
              <div className="ws-flywheel__item-sub">
                {item.description}
                {item.agent_id ? ` · Agent: ${item.agent_id}` : ''}
              </div>
            </div>
            {(Object.keys(ACTION_CONFIG) as ActionKey[]).map((key) => {
              const action = ACTION_CONFIG[key];
              return (
                <Tooltip key={key} title={action.label}>
                  <button
                    type="button"
                    className="ws-flywheel__icon-btn"
                    style={
                      {
                        '--btn-color': actionColor(action.varName),
                        '--btn-soft': `var(${action.varName}-soft, var(--ws-accent-light))`,
                      } as React.CSSProperties
                    }
                    onClick={() => handleActionClick(key, item)}
                  >
                    {action.icon}
                  </button>
                </Tooltip>
              );
            })}
          </div>
        ))}
        {(pendingItems || []).length === 0 && (
          <div className="ws-flywheel__empty">
            <div className="ws-flywheel__empty-title">暂无待评委项</div>
            <div className="ws-flywheel__empty-hint">Agent 产出资产后会出现在这里等待背书</div>
          </div>
        )}
      </div>

      {/* 操作确认弹窗 */}
      <Modal
        title={
          currentAction ? (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
              <span style={{ color: actionColor(ACTION_CONFIG[currentAction].varName) }}>
                {ACTION_CONFIG[currentAction].icon}
              </span>
              <span>{ACTION_CONFIG[currentAction].label}</span>
              {currentItem && (
                <span style={{ fontSize: 13, fontWeight: 400, color: '#8a92a6' }}>
                  — {currentItem.title}
                </span>
              )}
            </span>
          ) : null
        }
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        okText="确认"
        cancelText="取消"
      >
        {currentAction ? ACTION_CONFIG[currentAction].fields.map(renderField) : null}
      </Modal>
    </div>
  );
}
