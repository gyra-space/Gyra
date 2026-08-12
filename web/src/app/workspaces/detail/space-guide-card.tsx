'use client';

import { apiInterceptors, listResources, listPlaybooks, listTriggers, getWorkspaceInfo } from '@/client/api';
import {
  DatabaseOutlined,
  ToolOutlined,
  BookOutlined,
  MessageOutlined,
  PlayCircleOutlined,
  ScheduleOutlined,
  DeploymentUnitOutlined,
  DownOutlined,
  RightOutlined,
  InboxOutlined,
} from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { useMemo, useState } from 'react';

interface SpaceGuideCardProps {
  workspaceId: number;
  workspaceCode: string;
  /** 今日待办数(由 lobby 复用其收件箱拉取结果传入,避免重复请求) */
  pendingCount?: number;
  /** 已确认语义资产名列表(由 lobby 复用其语义拉取结果传入) */
  semanticNames?: string[];
  /** 动作回调:全部在场景空间壳内切换,不再整页跳转 */
  onGuide?: (action: 'ask' | 'run_playbook' | 'triggers' | 'data_assets') => void;
  /** 推荐问题:填入输入框并聚焦 */
  onAsk?: (text?: string) => void;
  /** 剧本快捷执行:@引用 带入输入框并聚焦 */
  onRunPlaybook?: (pb: { playbook_id: number; playbook_name: string }) => void;
  /** 以下数据由 Lobby 聚合端点一次性下发,省略时回退到内部拉取(兼容独立使用) */
  workspace?: any;
  resources?: any[];
  playbooks?: any[];
  triggers?: any[];
  /** 聚合数据加载中:显示骨架,避免数字从 0 跳变 */
  loading?: boolean;
}

const DATA_TYPES = ['data_source', 'knowledge_space', 'environment'];
const CAPABILITY_TYPES = ['skill', 'mcp', 'app', 'llm_model'];

/**
 * 空间问候条 + 开始工作区:
 * 顶部问候(待办/空间状态) + 计数 + 动作胶囊;下方推荐问题与可跑剧本 —— 让用户不用想"问什么",
 * 一键即可进入执行。导览卡被吸收为本卡,不再单独占用一行。
 */
export function SpaceGuideCard({
  workspaceId,
  workspaceCode,
  pendingCount = 0,
  semanticNames = [],
  onGuide,
  onAsk,
  onRunPlaybook,
  workspace: workspaceProp,
  resources: resourcesProp,
  playbooks: playbooksProp,
  triggers: triggersProp,
  loading = false,
}: SpaceGuideCardProps) {
  const storageKey = `ws-guide-collapsed-${workspaceId}`;
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    return window.localStorage.getItem(storageKey) === '1';
  });

  const { data: wsFetched } = useRequest(async () => {
    if (workspaceProp || !workspaceCode) return null;
    const [err, res] = await apiInterceptors(getWorkspaceInfo(workspaceCode));
    return err ? null : res;
  }, { refreshDeps: [workspaceCode, workspaceProp] });
  const ws = workspaceProp ?? wsFetched;
  const description = ws?.description;

  const { data: resourcesFetched } = useRequest(async () => {
    if (resourcesProp) return null;
    const [err, res] = await apiInterceptors(listResources({ workspace_id: workspaceId }));
    return err ? [] : res || [];
  }, { refreshDeps: [workspaceId, resourcesProp] });
  const resources = resourcesProp ?? resourcesFetched ?? [];

  const { data: playbooksFetched } = useRequest(async () => {
    if (playbooksProp) return null;
    const [err, res] = await apiInterceptors(listPlaybooks({ workspace_id: workspaceId, limit: 200 }));
    return err ? [] : res || [];
  }, { refreshDeps: [workspaceId, playbooksProp] });
  const playbooks = playbooksProp ?? playbooksFetched ?? [];

  const { data: triggersFetched } = useRequest(async () => {
    if (triggersProp) return null;
    const [err, res] = await apiInterceptors(listTriggers({ workspace_id: workspaceId, limit: 200 }));
    return err ? [] : res || [];
  }, { refreshDeps: [workspaceId, triggersProp] });
  const triggers = triggersProp ?? triggersFetched ?? [];

  const stats = useMemo(() => {
    const dataCount = (resources || []).filter((r: any) => DATA_TYPES.includes(r.type)).length;
    const capCount = (resources || []).filter((r: any) => CAPABILITY_TYPES.includes(r.type)).length;
    const pbCount = (playbooks || []).length;
    const triggeredPb = new Set(
      (triggers || []).filter((t: any) => t.is_active !== false).map((t: any) => t.playbook_id),
    ).size;
    return { dataCount, capCount, pbCount, triggeredPb, semanticCount: semanticNames.length };
  }, [resources, playbooks, triggers, semanticNames]);

  // 推荐问题:由空间已有内容推导(前端 fallback,后续由 /overview 聚合端点替换)
  const suggestions = useMemo(() => {
    const qs: string[] = [];
    const firstPb: any = (playbooks || [])[0];
    if (firstPb?.name) qs.push(`跑一下「${firstPb.name}」剧本`);
    if (semanticNames.length > 0) qs.push(`「${semanticNames[0]}」的现状如何?`);
    if (qs.length < 2) qs.push('帮我看看这周的数据情况');
    return qs.slice(0, 3);
  }, [playbooks, semanticNames]);

  const toggle = () => {
    const next = !collapsed;
    setCollapsed(next);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(storageKey, next ? '1' : '0');
    }
  };

  const statusLine = pendingCount > 0
    ? `今天有 ${pendingCount} 件待办需要你,处理完流水线继续跑`
    : '一切就绪,可以随时提问或跑一个剧本';

  return (
    <div className="ws-guide">
      <div
        className="ws-guide__head"
        role="button"
        tabIndex={0}
        onClick={toggle}
        onKeyDown={(e) => { if (e.key === 'Enter') toggle(); }}
      >
        <span className="ws-guide__title">{ws?.name || '空间工作台'}</span>
        <span className="ws-guide__desc">
          <InboxOutlined style={{ marginRight: 4 }} />
          {statusLine}
        </span>
        <span className="ws-guide__toggle">{collapsed ? <RightOutlined /> : <DownOutlined />}</span>
      </div>
      {!collapsed && (
        <div className="ws-guide__body">
          {loading && (
            <div className="ws-guide__loading">
              <div className="ws-guide__loading-brief" />
              <div className="ws-guide__loading-stats">
                <span /><span /><span /><span />
              </div>
              <div className="ws-guide__loading-actions">
                <span /><span /><span /><span />
              </div>
            </div>
          )}
          {!loading && (
            <>
          {description && <div className="ws-guide__brief">{description}</div>}
          <div className="ws-guide__stats">
            <span className="ws-guide__stat">
              <DatabaseOutlined />
              数据资产 <b>{stats.dataCount}</b>
            </span>
            <span className="ws-guide__stat">
              <ToolOutlined />
              能力 <b>{stats.capCount}</b>
            </span>
            <span className="ws-guide__stat">
              <DeploymentUnitOutlined />
              语义 <b>{stats.semanticCount}</b>
            </span>
            <span className="ws-guide__stat">
              <BookOutlined />
              剧本 <b>{stats.pbCount}</b>
              {stats.triggeredPb > 0 && <em>({stats.triggeredPb} 有自动触发)</em>}
            </span>
          </div>
          <div className="ws-guide__actions">
            <span
              className="ws-guide__action"
              role="button"
              tabIndex={0}
              onClick={() => onAsk?.()}
              onKeyDown={(e) => { if (e.key === 'Enter') onAsk?.(); }}
            >
              <MessageOutlined /> 随便问问
            </span>
            <span
              className="ws-guide__action"
              role="button"
              tabIndex={0}
              onClick={() => onGuide?.('run_playbook')}
              onKeyDown={(e) => { if (e.key === 'Enter') onGuide?.('run_playbook'); }}
            >
              <PlayCircleOutlined /> 跑一个剧本
            </span>
            <span
              className="ws-guide__action"
              role="button"
              tabIndex={0}
              onClick={() => onGuide?.('triggers')}
              onKeyDown={(e) => { if (e.key === 'Enter') onGuide?.('triggers'); }}
            >
              <ScheduleOutlined /> 订阅提醒
            </span>
            <span
              className="ws-guide__action"
              role="button"
              tabIndex={0}
              onClick={() => onGuide?.('data_assets')}
              onKeyDown={(e) => { if (e.key === 'Enter') onGuide?.('data_assets'); }}
            >
              <DatabaseOutlined /> 数据资产
            </span>
          </div>

          {/* 开始工作:推荐问题 + 可跑剧本 */}
          <div className="ws-guide__work">
            {suggestions.length > 0 && (
              <div className="ws-guide__qs">
                {suggestions.map((q) => (
                  <span
                    key={q}
                    className="ws-guide__q"
                    role="button"
                    tabIndex={0}
                    onClick={() => onAsk?.(q)}
                    onKeyDown={(e) => { if (e.key === 'Enter') onAsk?.(q); }}
                  >
                    {q} →
                  </span>
                ))}
              </div>
            )}
            {(playbooks || []).length > 0 && (
              <div className="ws-guide__pbs">
                {(playbooks || []).slice(0, 3).map((pb: any) => (
                  <div
                    key={pb.id}
                    className="ws-guide__pb"
                    role="button"
                    tabIndex={0}
                    onClick={() => onRunPlaybook?.({ playbook_id: pb.id, playbook_name: pb.name })}
                    onKeyDown={(e) => { if (e.key === 'Enter') onRunPlaybook?.({ playbook_id: pb.id, playbook_name: pb.name }); }}
                  >
                    <PlayCircleOutlined className="ws-guide__pb-icon" />
                    <span className="ws-guide__pb-name">{pb.name}</span>
                    <span className="ws-guide__pb-hint">点击运行</span>
                    <RightOutlined className="ws-guide__pb-arrow" />
                  </div>
                ))}
              </div>
            )}
          </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
