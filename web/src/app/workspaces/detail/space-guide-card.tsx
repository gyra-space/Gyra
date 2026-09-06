'use client';

import { apiInterceptors, listResources, listTriggers, getWorkspaceInfo, listExperts } from '@/client/api';
import { ExpertInfo } from '@/client/api/expert';
import {
  DatabaseOutlined,
  ToolOutlined,
  MessageOutlined,
  PlayCircleOutlined,
  ScheduleOutlined,
  DeploymentUnitOutlined,
  DownOutlined,
  RightOutlined,
  InboxOutlined,
  TeamOutlined,
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
  /** 专家对话:@引用 带入输入框 */
  onTalkExpert?: (expert: ExpertInfo) => void;
  /** 专家编辑:进入空间内专家编辑器 */
  onEditExpert?: (expert: ExpertInfo) => void;
  /** 专家派单:为该专家创建任务 */
  onDispatchExpert?: (expert: ExpertInfo) => void;
  /** 以下数据由 Lobby 聚合端点一次性下发,省略时回退到内部拉取(兼容独立使用) */
  workspace?: any;
  resources?: any[];
  triggers?: any[];
  /** 聚合数据加载中:显示骨架,避免数字从 0 跳变 */
  loading?: boolean;
}

const DATA_TYPES = ['data_source', 'knowledge_space', 'environment'];
const CAPABILITY_TYPES = ['skill', 'mcp', 'app', 'llm_model'];

/**
 * 空间问候条 + 开始工作区:
 * 顶部问候(待办/空间状态) + 计数 + 动作胶囊;下方推荐问题与发起任务 —— 让用户不用想"问什么",
 * 一键即可进入执行。导览卡被吸收为本卡,不再单独占用一行。
 */
export function SpaceGuideCard({
  workspaceId,
  workspaceCode,
  pendingCount = 0,
  semanticNames = [],
  onGuide,
  onAsk,
  onTalkExpert,
  onEditExpert,
  onDispatchExpert,
  workspace: workspaceProp,
  resources: resourcesProp,
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

  // 专家团队列表（Agent Team 空间重构 Phase 1.4）：替代原"可跑剧本/发起任务"，展示团队卡片
  const { data: expertsFetched } = useRequest(async () => {
    const [err, res] = await apiInterceptors(listExperts(workspaceId));
    return err ? [] : res || [];
  }, { refreshDeps: [workspaceId] });
  const experts = expertsFetched ?? [];

  const { data: triggersFetched } = useRequest(async () => {
    if (triggersProp) return null;
    const [err, res] = await apiInterceptors(listTriggers({ workspace_id: workspaceId, limit: 200 }));
    return err ? [] : res || [];
  }, { refreshDeps: [workspaceId, triggersProp] });
  const triggers = triggersProp ?? triggersFetched ?? [];

  const stats = useMemo(() => {
    const dataCount = (resources || []).filter((r: any) => DATA_TYPES.includes(r.type)).length;
    const capCount = (resources || []).filter((r: any) => CAPABILITY_TYPES.includes(r.type)).length;
    const expertCount = (experts || []).length;
    return { dataCount, capCount, expertCount, semanticCount: semanticNames.length };
  }, [resources, experts, semanticNames]);

  // 推荐问题:由空间已有内容推导(前端 fallback,后续由 /overview 聚合端点替换)
  const suggestions = useMemo(() => {
    const qs: string[] = [];
    const firstExpert: any = (experts || [])[0];
    if (firstExpert?.app_name || firstExpert?.app_code) qs.push(`问问「${firstExpert.app_name || firstExpert.app_code}」`);
    if (semanticNames.length > 0) qs.push(`「${semanticNames[0]}」的现状如何?`);
    if (qs.length < 2) qs.push('帮我看看这周的数据情况');
    return qs.slice(0, 3);
  }, [experts, semanticNames]);

  const toggle = () => {
    const next = !collapsed;
    setCollapsed(next);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(storageKey, next ? '1' : '0');
    }
  };

  const statusLine = pendingCount > 0
    ? `今天有 ${pendingCount} 件待办需要你,处理完流水线继续跑`
    : '一切就绪,可以随时提问或发起一个专家任务';

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
              <TeamOutlined />
              专家 <b>{stats.expertCount}</b>
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
              <PlayCircleOutlined /> 发起专家任务
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

          {/* 开始工作:推荐问题 + 专家团队 */}
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
            {(experts || []).length > 0 && (
              <div className="ws-guide__pbs">
                {(experts || []).slice(0, 3).map((ex: ExpertInfo) => (
                  <div
                    key={ex.app_code}
                    className="ws-guide__pb"
                    role="button"
                    tabIndex={0}
                    onClick={() => onTalkExpert?.(ex)}
                    onKeyDown={(e) => { if (e.key === 'Enter') onTalkExpert?.(ex); }}
                  >
                    <PlayCircleOutlined className="ws-guide__pb-icon" />
                    <span className="ws-guide__pb-name">{ex.app_name || ex.app_code}</span>
                    <span className="ws-guide__pb-hint">对话</span>
                    <span
                      className="ws-guide__pb-link"
                      role="button"
                      tabIndex={0}
                      onClick={(e) => { e.stopPropagation(); onEditExpert?.(ex); }}
                      onKeyDown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); onEditExpert?.(ex); } }}
                    >
                      编辑
                    </span>
                    <span
                      className="ws-guide__pb-link"
                      role="button"
                      tabIndex={0}
                      onClick={(e) => { e.stopPropagation(); onDispatchExpert?.(ex); }}
                      onKeyDown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); onDispatchExpert?.(ex); } }}
                    >
                      派单
                    </span>
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
