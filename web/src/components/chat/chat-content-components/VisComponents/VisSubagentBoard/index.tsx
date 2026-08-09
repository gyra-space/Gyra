import React, { useEffect, useMemo, useState } from 'react';
import { VisSubagentBoardWrap } from './style';
import {
  AppstoreOutlined,
  UpOutlined,
  DownOutlined,
  RobotOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { Tooltip } from 'antd';

export interface SubagentArtifact {
  name?: string;
  type?: string;
  url?: string;
  mime_type?: string;
}

export interface SubagentItemData {
  sub_conv_id: string;
  agent_name?: string;
  agent_display_name?: string;
  task?: string;
  status: 'pending' | 'running' | 'done' | 'failed' | 'awaiting_authorization';
  mode?: string;
  authorization?: string;
  params?: Record<string, any>;
  progress?: number;
  steps?: string[];
  artifacts?: SubagentArtifact[];
}

export interface ISubagentBoardData {
  uid?: string;
  type?: string;
  items?: SubagentItemData[];
  total_count?: number;
  completed_count?: number;
}

interface IProps {
  otherComponents?: any;
  data: ISubagentBoardData;
  /** 覆盖默认「新标签打开子会话」行为:场景空间用它内联展开子对话。 */
  onOpenSubagent?: (subConvId: string) => void;
  /** dock tab 容器内嵌渲染：跳过卡片外壳装饰与 header，恒展开列表。 */
  embedded?: boolean;
}

const STATUS_LABEL: Record<SubagentItemData['status'], string> = {
  pending: '待开始',
  running: '运行中',
  done: '已完成',
  failed: '失败',
  awaiting_authorization: '待授权',
};

const isTerminal = (s: string) => s === 'done' || s === 'failed';

/** 把 media 参数渲染成可读的摘要片段，如 "视频 · 1080p · 16:9"。 */
const formatMediaParams = (params?: Record<string, any>): string | null => {
  if (!params || !params.media) return null;
  const m = params.media;
  const kind = m.kind === 'video' ? '视频' : m.kind === 'audio' ? '音频' : '图片';
  const bits: string[] = [kind];
  if (m.resolution) bits.push(m.resolution);
  if (m.aspect_ratio) bits.push(m.aspect_ratio);
  if (m.size) bits.push(m.size);
  if (m.duration) bits.push(`${m.duration}s`);
  if (m.model) bits.push(m.model);
  return bits.join(' · ');
};

const VisSubagentBoard: React.FC<IProps> = ({ data, onOpenSubagent, embedded = false }) => {
  const items: SubagentItemData[] = data.items || [];
  const [expanded, setExpanded] = useState(true);

  const toggleExpand = () => setExpanded(!expanded);

  const progress = useMemo(() => {
    const completed = items.filter((i) => isTerminal(i.status)).length;
    return { completed, total: items.length };
  }, [items]);

  // 全部终态自动折叠（参考 VisTodoList）；从完成态变回进行中则重新展开
  const allCompleted = items.length > 0 && items.every((i) => isTerminal(i.status));
  useEffect(() => {
    setExpanded(!allCompleted);
  }, [allCompleted]);

  const hasAuth = items.some((i) => i.status === 'awaiting_authorization');

  const openSubagent = (subConvId: string) => {
    // 场景空间传入 onOpenSubagent 时内联展开子对话(中间面板);否则默认新标签
    // 打开子会话,复用 chat 页面完整渲染子任务对话流(含 VIS/消息流)。
    if (onOpenSubagent) {
      onOpenSubagent(subConvId);
      return;
    }
    window.open(`/chat?app_code=chat_normal&conv_uid=${subConvId}`, '_blank');
  };

  const displayName = (item: SubagentItemData) =>
    item.agent_display_name || item.agent_name || item.sub_conv_id.slice(0, 8);

  return (
    <VisSubagentBoardWrap className={embedded ? 'embedded' : undefined}>
      {!embedded && (
        <div className="board-header" onClick={toggleExpand}>
          <div className="header-left">
            <AppstoreOutlined className="header-icon" />
            <span className="header-title">{allCompleted ? '子任务完成' : '子任务'}</span>
            <span className="header-progress">{progress.completed}/{progress.total}</span>
            {hasAuth && <span className="header-auth-badge">待授权</span>}
          </div>
          <div className="header-expand">
            {expanded ? <UpOutlined /> : <DownOutlined />}
          </div>
        </div>
      )}

      {(embedded || expanded) && (
        <div className="board-items">
          {items.map((item) => {
            const media = formatMediaParams(item.params);
            return (
              <div
                key={item.sub_conv_id}
                className={`subagent-item ${item.status}`}
                onClick={() => openSubagent(item.sub_conv_id)}
              >
                <div className="status-icon">
                  {item.status === 'running' && <span className="spinner" />}
                  {item.status === 'done' && <span className="dot done" />}
                  {item.status === 'failed' && <span className="dot failed" />}
                  {item.status === 'pending' && <span className="dot pending" />}
                  {item.status === 'awaiting_authorization' && <span className="dot awaiting" />}
                </div>
                <div className="item-content">
                  <div className="item-title-row">
                    <RobotOutlined className="item-robot" />
                    <span className={`item-title ${item.status}`}>{displayName(item)}</span>
                    {item.mode && (
                      <span
                        className={`item-mode mode-${item.mode}`}
                        title={
                          item.mode === 'async'
                            ? '异步：主 Agent 不等待，子 Agent 后台运行，全部完成后触发主恢复'
                            : '同步：主 Agent 等待子 Agent 完成后继续'
                        }
                      >
                        {item.mode === 'async' ? '异步' : '同步'}
                      </span>
                    )}
                  </div>
                  {item.task && (
                    <div className="item-task" title={item.task}>{item.task}</div>
                  )}
                  {media && (
                    <div className="item-params">
                      <ThunderboltOutlined />
                      <span>{media}</span>
                    </div>
                  )}
                  {item.authorization && (
                    <div className="item-auth">⚠ {item.authorization}</div>
                  )}
                  {item.status === 'running' && typeof item.progress === 'number' && (
                    <div className="item-progress">
                      <div className="progress-track">
                        <div
                          className="progress-fill"
                          style={{ width: `${Math.min(100, Math.max(0, item.progress))}%` }}
                        />
                      </div>
                      <span className="progress-label">{item.progress}%</span>
                    </div>
                  )}
                  {isTerminal(item.status) && item.artifacts && item.artifacts.length > 0 && (
                    <div
                      className="item-artifacts"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {item.artifacts.map((art, idx) => {
                        const isImage =
                          art.type === 'image' ||
                          (art.mime_type || '').startsWith('image/');
                        if (isImage && art.url) {
                          return (
                            <a
                              key={idx}
                              className="artifact-thumb"
                              href={art.url}
                              target="_blank"
                              rel="noreferrer"
                              title={art.name || '查看图片'}
                            >
                              <img src={art.url} alt={art.name || '生成图片'} loading="lazy" />
                            </a>
                          );
                        }
                        return art.url ? (
                          <a
                            key={idx}
                            className="artifact-link"
                            href={art.url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            {art.name || '查看产物'}
                          </a>
                        ) : null;
                      })}
                    </div>
                  )}
                </div>
                <Tooltip title={STATUS_LABEL[item.status]}>
                  <span className={`item-status-badge ${item.status}`}>
                    {STATUS_LABEL[item.status]}
                  </span>
                </Tooltip>
              </div>
            );
          })}

          {items.length === 0 && (
            <div className="board-empty">
              <span>暂无子任务</span>
            </div>
          )}
        </div>
      )}
    </VisSubagentBoardWrap>
  );
};

export default VisSubagentBoard;
