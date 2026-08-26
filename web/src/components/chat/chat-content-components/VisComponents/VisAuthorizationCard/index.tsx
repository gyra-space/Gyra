import React, { useState, useEffect, useCallback } from 'react';
import { VisAuthorizationCardWrap } from './style';
import {
  Button,
  Divider,
  Checkbox,
  Collapse,
  Typography,
} from 'antd';
import {
  LockOutlined,
  ToolOutlined,
  CheckCircleFilled,
  CloseCircleFilled,
  WarningOutlined,
  InfoCircleOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { useInteraction } from '@/components/interaction';
import { GrantScope } from '@/types/interaction';
import { STORAGE_USERINFO_KEY } from '@/utils/constants';

const { Text } = Typography;

type Actor = { user_no?: string; nick_name?: string; avatar_url?: string };

interface AuthRecordData {
  request_id?: string;
  interaction_type?: string;
  state?: 'pending' | 'responded' | 'cancelled' | 'timed_out';
  responded_at?: string;
  actor?: Actor;
  question?: string | null;
  header?: string | null;
  result?: {
    choice?: string | null;
    grant_scope?: string | null;
    grant_duration?: string | null;
  };
}

const getCurrentUserMeta = (): Actor => {
  try {
    const raw = localStorage.getItem(STORAGE_USERINFO_KEY);
    if (!raw) return {};
    const user = JSON.parse(raw) as Actor;
    return {
      user_no: user.user_no,
      nick_name: user.nick_name,
      avatar_url: user.avatar_url,
    };
  } catch {
    return {};
  }
};

const formatTime = (ts?: string) => {
  if (!ts) return '';
  const date = new Date(ts);
  if (Number.isNaN(date.getTime())) return ts;
  return date.toLocaleString();
};

// ========== Types ==========

export interface VisAuthorizationCardData {
  request_id: string;
  message: string;
  tool_name: string;
  risk_level?: 'safe' | 'low' | 'medium' | 'high' | 'critical';
  risk_factors?: string[];
  arguments?: Record<string, unknown>;
  allow_session_grant?: boolean;
  timeout?: number;
  disabled?: boolean;
}

interface VisAuthorizationCardProps {
  data: VisAuthorizationCardData;
}

// ========== Helper Functions ==========

/**
 * Get risk level icon.
 */
function getRiskLevelIcon(riskLevel?: string): React.ReactNode {
  switch (riskLevel?.toLowerCase()) {
    case 'safe':
      return <CheckCircleOutlined />;
    case 'low':
      return <InfoCircleOutlined />;
    case 'medium':
      return <WarningOutlined />;
    case 'high':
    case 'critical':
      return <ExclamationCircleOutlined />;
    default:
      return <InfoCircleOutlined />;
  }
}

/**
 * Get risk level display name.
 */
function getRiskLevelLabel(riskLevel?: string): string {
  switch (riskLevel?.toLowerCase()) {
    case 'safe':
      return 'Safe';
    case 'low':
      return 'Low Risk';
    case 'medium':
      return 'Medium Risk';
    case 'high':
      return 'High Risk';
    case 'critical':
      return 'Critical Risk';
    default:
      return 'Unknown';
  }
}

/**
 * Format argument value for display.
 */
function formatArgumentValue(value: unknown): string {
  if (value === null || value === undefined) {
    return 'null';
  }
  if (typeof value === 'string') {
    if (value.length > 200) {
      return value.substring(0, 200) + '...';
    }
    return value;
  }
  if (typeof value === 'object') {
    const str = JSON.stringify(value, null, 2);
    if (str.length > 500) {
      return str.substring(0, 500) + '...';
    }
    return str;
  }
  return String(value);
}

// ========== Component ==========

const VisAuthorizationCard: React.FC<VisAuthorizationCardProps> = ({ data }) => {
  const { authorize, showRequest } = useInteraction();
  const [disabled, setDisabled] = useState<boolean>(!!data.disabled);
  const [record, setRecord] = useState<AuthRecordData | null>(null);
  const [statusLoaded, setStatusLoaded] = useState(false);
  const [grantScope, setGrantScope] = useState<GrantScope>(GrantScope.ONCE);
  const [loading, setLoading] = useState(false);

  const requestId = data.request_id || '';
  const toolArgs = data.arguments ?? {};
  const riskFactors = data.risk_factors ?? [];
  const allowSessionGrant = data.allow_session_grant ?? true;
  const riskLevel = data.risk_level?.toLowerCase() || 'unknown';
  const isDeny = record?.result?.choice === 'deny';
  const who = record?.actor?.nick_name || '';
  const avatar = record?.actor?.avatar_url;
  const initial = (who.trim().charAt(0) || 'U').toUpperCase();

  // 挂载即向后端读取统一交互记录：已处理则渲染只读态（含操作人/时间/决定）
  useEffect(() => {
    if (!requestId) {
      setStatusLoaded(true);
      return;
    }
    let cancelled = false;
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || '';
    (async () => {
      try {
        const res = await fetch(
          `${apiBaseUrl}/api/v1/interaction/status?request_id=${encodeURIComponent(requestId)}`,
        );
        if (res.ok) {
          const json = await res.json();
          if (!cancelled && json?.responded && json.record) {
            setRecord(json.record as AuthRecordData);
            setDisabled(true);
          }
        }
      } catch (e) {
        console.warn('Failed to fetch auth status:', e);
      } finally {
        if (!cancelled) setStatusLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [requestId]);

  const markHandled = useCallback((choice: 'allow' | 'deny') => {
    setRecord({
      request_id: requestId,
      interaction_type: 'authorize',
      state: 'responded',
      responded_at: new Date().toISOString(),
      actor: getCurrentUserMeta(),
      result: { choice },
    });
    setDisabled(true);
  }, [requestId]);

  const handleAuthorize = useCallback(async () => {
    setLoading(true);
    try {
      // Show the request in the interaction manager first
      showRequest(data.request_id);
      const success = await authorize(true, grantScope);
      if (success) {
        markHandled('allow');
      }
    } finally {
      setLoading(false);
    }
  }, [authorize, grantScope, data.request_id, showRequest, markHandled]);

  const handleDeny = useCallback(async () => {
    setLoading(true);
    try {
      showRequest(data.request_id);
      // 拒绝 = 授权决定为 deny，走统一的 authorize(false) 记录谁在何时拒绝
      const success = await authorize(false, grantScope);
      if (success) {
        markHandled('deny');
      }
    } finally {
      setLoading(false);
    }
  }, [authorize, grantScope, data.request_id, showRequest, markHandled]);

  const handled = statusLoaded && !!record;

  return (
    <VisAuthorizationCardWrap className="VisAuthorizationCardClass">
      <div className="card-content">
        {/* Header */}
        <div className="auth-header">
          <span className="auth-icon-chip">
            <LockOutlined />
          </span>
          <span className="auth-title">Tool Authorization Required</span>
          <span className={`risk-pill risk-${riskLevel}`}>
            {getRiskLevelIcon(data.risk_level)}
            {getRiskLevelLabel(data.risk_level)}
          </span>
        </div>

        <Divider
          style={{
            margin: '8px 0px 8px 0px',
            borderWidth: '1px',
            borderColor: 'var(--line-soft)',
          }}
        />

        {/* Message */}
        <div className="whitespace-normal" style={{ marginBottom: 12 }}>
          <Text>{data.message}</Text>
        </div>

        {/* Tool Info */}
        <div className="tool-info">
          <span className="tool-icon">
            <ToolOutlined />
          </span>
          <span className="tool-name">{data.tool_name}</span>
        </div>

        {/* Risk Factors */}
        {riskFactors.length > 0 && (
          <div className="risk-factors">
            <WarningOutlined className="risk-factors-icon" />
            {riskFactors.map((factor, index) => (
              <span key={index} className="risk-factor-tag">
                {factor}
              </span>
            ))}
          </div>
        )}

        {/* Tool Arguments */}
        {Object.keys(toolArgs).length > 0 && (
          <Collapse
            ghost
            size="small"
            className="arguments-section"
            items={[
              {
                key: 'arguments',
                label: (
                  <Text strong style={{ fontSize: 12 }}>
                    Tool Arguments ({Object.keys(toolArgs).length})
                  </Text>
                ),
                children: (
                  <div className="arguments-content">
                    {Object.entries(toolArgs).map(([key, value]) => (
                      <div key={key} className="arg-item">
                        <span className="arg-key">{key}:</span>
                        <pre className="arg-value">
                          {formatArgumentValue(value)}
                        </pre>
                      </div>
                    ))}
                  </div>
                ),
              },
            ]}
          />
        )}

        {/* Session Grant Option */}
        {allowSessionGrant && !disabled && (
          <div className="session-grant-option">
            <Checkbox
              checked={grantScope === GrantScope.SESSION}
              onChange={(e) =>
                setGrantScope(e.target.checked ? GrantScope.SESSION : GrantScope.ONCE)
              }
            >
              <Text style={{ fontSize: 12 }}>Allow this tool for the entire session</Text>
            </Checkbox>
          </div>
        )}

        <Divider
          style={{
            margin: '8px 0px 8px 0px',
            borderWidth: '1px',
            borderColor: 'var(--line-soft)',
          }}
        />

        {/* Footer: 已处理 → 只读记录；未处理 → 授权按钮 */}
        {handled ? (
          <div className={`auth-record auth-record-${isDeny ? 'deny' : 'allow'}`}>
            <div className="record-head">
              <span className="record-avatar">
                {avatar ? (
                  <img src={avatar} alt={who} />
                ) : (
                  <span>{initial}</span>
                )}
              </span>
              <div className="record-who">
                <span className="record-title">
                  {isDeny ? 'Denied' : 'Allowed'} by {who || 'user'}
                </span>
                {record?.responded_at && (
                  <span className="record-time">{formatTime(record.responded_at)}</span>
                )}
              </div>
              <span className="record-icon">
                {isDeny ? <CloseCircleFilled /> : <CheckCircleFilled />}
              </span>
            </div>
          </div>
        ) : (
          <div className="auth-footer">
            <Button
              disabled={disabled || !statusLoaded}
              danger
              icon={<CloseCircleFilled />}
              onClick={handleDeny}
              loading={loading}
            >
              Deny
            </Button>
            <Button
              disabled={disabled || !statusLoaded}
              type="primary"
              icon={<CheckCircleOutlined />}
              onClick={handleAuthorize}
              loading={loading}
            >
              {grantScope === GrantScope.SESSION ? 'Allow (Session)' : 'Allow Once'}
            </Button>
          </div>
        )}
      </div>
    </VisAuthorizationCardWrap>
  );
};

export default VisAuthorizationCard;
