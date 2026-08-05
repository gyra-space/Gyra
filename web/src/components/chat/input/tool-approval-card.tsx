import { SafetyCertificateOutlined, CheckOutlined, CloseOutlined } from '@ant-design/icons';
import { Button, Space, Tag, Tooltip, App } from 'antd';
import React, { useContext } from 'react';
import { useTranslation } from 'react-i18next';
import { ChatContentContext } from '@/contexts';
import useToolApproval, { PendingApproval } from '@/hooks/use-tool-approval';

/** 工具执行授权卡片：渲染于输入框上方。
 *
 * Agent loop 因工具需授权而结束、对话进入 WAITING 时，后端在 ToolApprovalRegistry
 * 登记待授权工具。本卡片拉取并展示，用户确认后用旧 conv_id 发起恢复（is_retry_chat），
 * 重新执行待授权工具并继续 AgentLoop。
 */
const ToolApprovalCard: React.FC<{ sessionId: string | undefined; replyLoading: boolean }> = ({
  sessionId,
  replyLoading,
}) => {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { handleChat, appInfo } = useContext(ChatContentContext);
  const { hasPending, pending, submitting, approve, refresh } = useToolApproval(sessionId, replyLoading);

  if (!hasPending || pending.length === 0) return null;

  const onResume = async (item: PendingApproval, approved: boolean) => {
    const ok = await approve(item.action_uid, approved);
    if (!ok) {
      message.error(t('tool_approval_failed') || 'Authorization failed');
      return;
    }
    // 用旧 conv_id 发起恢复：对话处于 WAITING -> is_retry_chat -> 重新执行待授权工具。
    // 已授权则放行执行；拒绝则工具跳过，AgentLoop 继续。
    const marker = approved
      ? `✅ 已授权执行工具 ${item.tool_name}`
      : `❌ 已拒绝执行工具 ${item.tool_name}`;
    try {
      await handleChat(marker, {
        app_code: appInfo?.app_code || '',
      });
    } finally {
      refresh();
    }
  };

  return (
    <div className='flex flex-col gap-2 mb-2 px-1'>
      {pending.map(item => (
        <div
          key={item.action_uid}
          className='flex items-center justify-between rounded-xl border border-amber-300 bg-amber-50 dark:bg-[rgba(245,158,11,0.12)] dark:border-[rgba(245,158,11,0.4)] px-4 py-3'
        >
          <Space size={8} align='center' className='min-w-0'>
            <SafetyCertificateOutlined className='text-amber-500 text-lg' />
            <div className='min-w-0'>
              <div className='text-sm font-medium text-amber-900 dark:text-amber-200 truncate'>
                {t('tool_approval_required') || 'Tool execution requires authorization'}
              </div>
              <div className='text-xs text-amber-700 dark:text-amber-300 truncate'>
                <Tag color='orange' className='mr-1'>
                  {item.tool_name}
                </Tag>
                <Tooltip title={JSON.stringify(item.args, null, 2)}>
                  <span className='cursor-help'>
                    {Object.keys(item.args || {}).length > 0
                      ? `${Object.keys(item.args).join(', ')}`
                      : t('tool_approval_no_args') || 'no args'}
                  </span>
                </Tooltip>
              </div>
            </div>
          </Space>
          <Space size={8}>
            <Button
              size='small'
              type='primary'
              icon={<CheckOutlined />}
              loading={submitting}
              onClick={() => onResume(item, true)}
            >
              {t('approve') || 'Approve'}
            </Button>
            <Button
              size='small'
              danger
              icon={<CloseOutlined />}
              loading={submitting}
              onClick={() => onResume(item, false)}
            >
              {t('reject') || 'Reject'}
            </Button>
          </Space>
        </div>
      ))}
    </div>
  );
};

export default ToolApprovalCard;
