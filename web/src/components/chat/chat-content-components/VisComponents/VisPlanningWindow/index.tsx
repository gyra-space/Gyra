'use client';

import React, { FC } from 'react';
import {
  AimOutlined,
  CheckOutlined,
  ClockCircleOutlined,
  CloseOutlined,
  FieldTimeOutlined,
} from '@ant-design/icons';
import Avatar from '../../avatar';
import { VisPWCardWrapper } from './style';

interface PlanningWindow {
  data: {
    items: Plan[];
  };
}

interface Plan {
  title?: string;
  description?: string;
  items: PlanItem[];
  model?: string;
  agent?: string;
  avatar?: string;
  start_time?: string;
  cost?: number;
}

interface PlanItem {
  title: string;
  task_id: string;
  status?: 'running' | 'todo' | 'complete' | 'failed';
  description?: string;
  avatar?: string;
  model?: string;
  agent?: string;
  task_type?: string;
  start_time?: string;
  cost?: number;
}

type NodeStatus = 'running' | 'complete' | 'failed' | 'todo';

/* ═══════════════════════════════════════════════════════════════
   Helpers
   ═══════════════════════════════════════════════════════════════ */

const normalizeStatus = (s?: string): NodeStatus => {
  if (s === 'running') return 'running';
  if (s === 'complete' || s === 'completed' || s === 'done') return 'complete';
  if (s === 'failed' || s === 'error') return 'failed';
  return 'todo';
};

const formatDuration = (sec?: number | null): string | null => {
  if (sec == null || !Number.isFinite(sec) || sec <= 0) return null;
  if (sec < 60) return `${Math.round(sec)}s`;
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
};

const formatTime = (t?: string): string | null => {
  if (!t) return null;
  const d = new Date(t);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
};

const TYPE_ICON_MAP: Record<string, string> = {
  knowledge_pack: '/icons/package.png',
  knowledge: '/icons/package.png',
  tool: '/icons/tool.png',
  code: '/icons/code.png',
  report: '/icons/report.png',
  monitor: '/icons/monitor.png',
  agent: '/icons/agent.png',
  plan: '/icons/plan.png',
  llm: '/icons/llm.png',
  stage: '/icons/stage.png',
  task: '/icons/task.png',
  default: '/icons/tool_default.svg',
};

const renderIcon = (type?: string) => {
  const normalized = String(type || '').toLowerCase();
  return TYPE_ICON_MAP[normalized] || TYPE_ICON_MAP.default;
};

/** 任务类型配色(icon tile 着色) */
const TYPE_STYLE_MAP: Record<string, { color: string; label: string }> = {
  agent: { color: '#4f46e5', label: 'AGENT' },
  tool: { color: '#0284c7', label: 'TOOL' },
  knowledge_pack: { color: '#7c3aed', label: 'KNOWLEDGE' },
  knowledge: { color: '#7c3aed', label: 'KNOWLEDGE' },
  code: { color: '#0f766e', label: 'CODE' },
  report: { color: '#c2410c', label: 'REPORT' },
  llm: { color: '#4f46e5', label: 'LLM' },
  default: { color: '#64748b', label: 'TASK' },
};

const typeStyle = (type?: string) =>
  TYPE_STYLE_MAP[String(type || '').toLowerCase()] || TYPE_STYLE_MAP.default;

/* ═══════════════════════════════════════════════════════════════
   Status node — 导轨上的状态节点(与 VisManusLeftPanel 同语言)
   ═══════════════════════════════════════════════════════════════ */

const StatusNode: FC<{ status: NodeStatus }> = ({ status }) => {
  if (status === 'running') {
    return (
      <span className="relative z-10 flex h-[14px] w-[14px] flex-shrink-0 items-center justify-center rounded-full border-2 border-indigo-500 bg-white shadow-[0_0_0_3px_rgba(79,70,229,0.12)]">
        <span className="h-[5px] w-[5px] animate-pulse rounded-full bg-indigo-500" />
      </span>
    );
  }
  if (status === 'complete') {
    return (
      <span className="relative z-10 flex h-[14px] w-[14px] flex-shrink-0 items-center justify-center rounded-full border-2 border-emerald-500 bg-emerald-500">
        <CheckOutlined className="text-[7px] text-white" />
      </span>
    );
  }
  if (status === 'failed') {
    return (
      <span className="relative z-10 flex h-[14px] w-[14px] flex-shrink-0 items-center justify-center rounded-full border-2 border-red-500 bg-red-500">
        <CloseOutlined className="text-[7px] text-white" />
      </span>
    );
  }
  return (
    <span className="relative z-10 h-[14px] w-[14px] flex-shrink-0 rounded-full border-2 border-slate-300 bg-white" />
  );
};

/* ═══════════════════════════════════════════════════════════════
   Task row — 挂在导轨上的任务节点
   ═══════════════════════════════════════════════════════════════ */

const TaskRow: FC<{ task: PlanItem }> = ({ task }) => {
  const status = normalizeStatus(task.status);
  const ts = typeStyle(task.task_type);
  const duration = formatDuration(task.cost);

  return (
    <div className="group relative flex items-start gap-2 rounded-lg px-2 py-1.5 transition-colors duration-150 hover:bg-slate-50">
      {/* 状态节点(吸附在左侧导轨线上) */}
      <span className="absolute -left-[20px] top-[9px]">
        <StatusNode status={status} />
      </span>

      {/* 类型 icon tile */}
      <span
        className="mt-px flex h-[22px] w-[22px] flex-shrink-0 items-center justify-center rounded-md border"
        style={{
          backgroundColor: `${ts.color}0f`,
          borderColor: `${ts.color}24`,
        }}
      >
        <img
          src={task.avatar || renderIcon(task.task_type)}
          alt=""
          className="h-[14px] w-[14px] rounded-[3px] object-cover"
        />
      </span>

      {/* 内容 */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span
            className="text-[9.5px] font-semibold uppercase tracking-wider"
            style={{ color: ts.color }}
          >
            {ts.label}
          </span>
          {status === 'running' && (
            <span className="rounded-full bg-indigo-50 px-1.5 py-px text-[9.5px] font-semibold text-indigo-500">
              执行中
            </span>
          )}
          {status === 'failed' && (
            <span className="rounded-full bg-red-50 px-1.5 py-px text-[9.5px] font-semibold text-red-500">
              失败
            </span>
          )}
        </div>
        <div
          className={`mt-px truncate text-[12.5px] font-medium leading-snug ${
            status === 'complete' ? 'text-slate-500' : 'text-slate-800'
          }`}
        >
          {task.title || '-'}
        </div>
        {(task.agent || duration) && (
          <div className="mt-0.5 flex items-center gap-1.5 text-[10.5px] text-slate-400">
            {task.agent && <span className="truncate">@{task.agent}</span>}
            {task.agent && duration && <span className="text-slate-200">·</span>}
            {duration && (
              <span className="tabular-nums">{duration}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════════
   Plan card — 目标 + 进度 + rail 任务节点(替代 antd Timeline)
   ═══════════════════════════════════════════════════════════════ */

const PlanCard: FC<{ plan: Plan }> = ({ plan }) => {
  const items = (plan.items || []).filter(Boolean);
  const total = items.length;
  const done = items.filter((t) => normalizeStatus(t.status) === 'complete').length;
  const failed = items.filter((t) => normalizeStatus(t.status) === 'failed').length;
  const hasRunning = items.some((t) => normalizeStatus(t.status) === 'running');
  const allDone = total > 0 && done === total;
  const pct = total > 0 ? Math.round(((done + failed) / total) * 100) : 0;

  const startAt = formatTime(plan.start_time);
  const duration = formatDuration(plan.cost);

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200/80 bg-white shadow-[0_1px_2px_rgba(16,24,40,0.04)]">
      {/* 头部:avatar + 标题 + 进度计数 */}
      <div className="bg-gradient-to-b from-indigo-50/50 via-white to-white px-3.5 pb-2.5 pt-3">
        <div className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center overflow-hidden rounded-lg border border-indigo-100 bg-white shadow-sm">
            <Avatar src={plan.avatar || '/agents/robot.png'} width={28} />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <AimOutlined className="text-[10px] text-indigo-400" />
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                任务计划
              </span>
              {plan.model && (
                <span className="rounded bg-slate-100 px-1 py-px font-mono text-[9.5px] text-slate-400">
                  {plan.model}
                </span>
              )}
            </div>
            <div className="mt-px truncate text-[13.5px] font-semibold leading-snug text-slate-800">
              {plan.title || '未命名计划'}
              {plan.agent && (
                <span className="ml-1.5 text-[12px] font-medium text-indigo-500">
                  @{plan.agent}
                </span>
              )}
            </div>
          </div>
          {total > 0 && (
            <span
              className={`flex-shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold tabular-nums ${
                allDone
                  ? 'bg-emerald-50 text-emerald-600'
                  : failed > 0 && !hasRunning
                    ? 'bg-red-50 text-red-500'
                    : 'bg-indigo-50 text-indigo-500'
              }`}
            >
              {done}/{total}
            </span>
          )}
        </div>

        {plan.description && (
          <p className="mt-1.5 line-clamp-2 text-[11.5px] leading-relaxed text-slate-400">
            {plan.description}
          </p>
        )}

        {/* hairline 进度条 */}
        {total > 0 && (
          <div className="mt-2.5 h-[3px] overflow-hidden rounded-full bg-slate-100">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                allDone
                  ? 'bg-gradient-to-r from-emerald-400 to-emerald-500'
                  : failed > 0 && !hasRunning
                    ? 'bg-gradient-to-r from-red-400 to-red-500'
                    : 'bg-gradient-to-r from-indigo-400 via-indigo-500 to-violet-500'
              }`}
              style={{ width: `${pct}%` }}
            />
          </div>
        )}

        {/* meta 行:开始时间 + 耗时 */}
        {(startAt || duration) && (
          <div className="mt-2 flex items-center gap-3 text-[10.5px] text-slate-400">
            {startAt && (
              <span className="flex items-center gap-1">
                <ClockCircleOutlined className="text-[10px]" />
                <span className="tabular-nums">{startAt}</span>
              </span>
            )}
            {duration && (
              <span className="flex items-center gap-1">
                <FieldTimeOutlined className="text-[10px]" />
                <span className="tabular-nums">{duration}</span>
              </span>
            )}
          </div>
        )}
      </div>

      {/* 导轨任务列表 */}
      {total > 0 && (
        <div className="px-3.5 pb-3 pt-1">
          <div className="relative ml-[15px] space-y-0.5 border-l-[1.5px] border-slate-200/70 py-1 pl-[13px]">
            {items.map((task, i) => (
              <TaskRow key={task.task_id || i} task={task} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════════
   Main
   ═══════════════════════════════════════════════════════════════ */

export const VisPlanningWindow: FC<PlanningWindow> = ({ data }) => {
  const plans = (data?.items || []).filter(Boolean);

  if (plans.length === 0) {
    return (
      <VisPWCardWrapper>
        <div className="flex items-center gap-2.5 rounded-xl border border-dashed border-slate-200 bg-slate-50/60 px-3.5 py-3">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-indigo-400 opacity-60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-indigo-500" />
          </span>
          <span className="text-shimmer text-[12px] font-medium">正在规划任务…</span>
        </div>
      </VisPWCardWrapper>
    );
  }

  return (
    <VisPWCardWrapper>
      <div className="space-y-2.5">
        {plans.map((plan, i) => (
          <PlanCard key={i} plan={plan} />
        ))}
      </div>
    </VisPWCardWrapper>
  );
};
