'use client';

import React, { FC, useEffect, useMemo, useRef, useState } from 'react';
import { Tooltip } from 'antd';
import {
  CheckOutlined,
  CheckCircleFilled,
  CloseOutlined,
  CaretRightOutlined,
  FileOutlined,
  DownloadOutlined,
  BulbOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import type {
  ManusLeftPanelData,
  ManusThinkingSection,
  ManusExecutionStep,
  ManusArtifactItem,
  ManusStepStatus,
} from '@/types/manus';
import { STEP_TYPE_CONFIG } from '@/types/manus';

interface IProps {
  data: ManusLeftPanelData;
  onStepClick?: (stepId: string) => void;
  onArtifactClick?: (artifact: ManusArtifactItem) => void;
}

/* ═══════════════════════════════════════════════════════════════
   Status node — 导轨上的状态节点(轻量圆点)
   ═══════════════════════════════════════════════════════════════ */

const StatusNode: FC<{ status: ManusStepStatus }> = ({ status }) => {
  if (status === 'running') {
    return (
      <span className="relative z-10 flex h-[13px] w-[13px] flex-shrink-0 items-center justify-center rounded-full border-[1.5px] border-indigo-500 bg-white shadow-[0_0_0_3px_rgba(79,70,229,0.1)]">
        <span className="h-[4px] w-[4px] animate-pulse rounded-full bg-indigo-500" />
      </span>
    );
  }
  if (status === 'completed') {
    return (
      <span className="relative z-10 flex h-[13px] w-[13px] flex-shrink-0 items-center justify-center rounded-full border-[1.5px] border-emerald-500 bg-emerald-500">
        <CheckOutlined className="text-[7px] text-white" />
      </span>
    );
  }
  if (status === 'error') {
    return (
      <span className="relative z-10 flex h-[13px] w-[13px] flex-shrink-0 items-center justify-center rounded-full border-[1.5px] border-red-500 bg-red-500">
        <CloseOutlined className="text-[7px] text-white" />
      </span>
    );
  }
  // pending — 空心节点
  return (
    <span className="relative z-10 h-[13px] w-[13px] flex-shrink-0 rounded-full border-[1.5px] border-slate-300 bg-white" />
  );
};

/* ═══════════════════════════════════════════════════════════════
   Step row — 轻量行:导轨状态点 + 类型小 tag + 标题 + 状态标记
   (替代旧版多层卡片,密度对齐执行胶囊的 L2 步骤行)
   ═══════════════════════════════════════════════════════════════ */

const StepCard: FC<{
  step: ManusExecutionStep;
  isActive: boolean;
  thought?: string;
  onClick?: () => void;
}> = ({ step, isActive, thought, onClick }) => {
  const config = STEP_TYPE_CONFIG[step.type] || STEP_TYPE_CONFIG.other;
  const [thoughtExpanded, setThoughtExpanded] = useState(false);

  return (
    <div
      className={`
        group relative rounded-lg px-2 py-[5px] cursor-pointer transition-colors duration-150
        ${isActive ? 'bg-indigo-50/70' : 'hover:bg-slate-50'}
      `}
      onClick={onClick}
    >
      {/* 状态节点(吸附在左侧导轨线上) */}
      <span className="absolute -left-[19px] top-[9px]">
        <StatusNode status={step.status} />
      </span>

      {/* 主行:类型 tag + 标题 + 状态标记 */}
      <div className="flex min-w-0 items-center gap-2">
        <span
          className="flex-shrink-0 rounded px-1 py-px font-mono text-[10px] leading-[15px]"
          style={{ color: config.color, backgroundColor: `${config.color}14` }}
        >
          {config.label}
        </span>
        <span
          className={`min-w-0 flex-1 truncate text-[12.5px] leading-snug ${
            step.status === 'error'
              ? 'text-red-500'
              : step.status === 'running'
                ? 'font-medium text-indigo-600'
                : 'text-slate-600'
          }`}
        >
          {step.title}
        </span>
        {step.status === 'running' && (
          <LoadingOutlined className="flex-shrink-0 text-[10px] text-indigo-400" spin />
        )}
        {step.status === 'error' && (
          <span className="flex-shrink-0 rounded bg-red-50 px-1 py-px text-[10px] leading-[15px] text-red-500">
            失败
          </span>
        )}
      </div>

      {/* 副标题(有才占行) */}
      {step.subtitle && (
        <div className="mt-px truncate pl-[3px] text-[11px] text-slate-400">
          {step.subtitle}
        </div>
      )}

      {/* 思考气泡 */}
      {thought && (
        <div className="mt-1">
          <button
            className="flex items-center gap-1 pl-[3px] text-[11px] font-medium text-indigo-400 transition-colors hover:text-indigo-600"
            onClick={(e) => {
              e.stopPropagation();
              setThoughtExpanded(!thoughtExpanded);
            }}
          >
            <BulbOutlined className="text-[10px]" />
            思考过程
            <CaretRightOutlined
              className={`text-[8px] transition-transform duration-150 ${thoughtExpanded ? 'rotate-90' : ''}`}
            />
          </button>
          {thoughtExpanded && (
            <div className="mt-1 whitespace-pre-wrap rounded-lg border border-slate-100 bg-slate-50/80 p-2.5 text-[11.5px] leading-relaxed text-slate-500">
              {thought}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════════
   Section block — 默认折叠;运行中自动展开所在段,完成整体收敛
   (结果为主、过程随行:过程段收起,需要时点开溯源)
   ═══════════════════════════════════════════════════════════════ */

const SectionBlock: FC<{
  section: ManusThinkingSection;
  activeStepId?: string;
  stepThoughts: Record<string, string>;
  /** 运行结束信号:is_working 变 false 时整体收敛(用户可再点开溯源) */
  working: boolean;
  onStepClick?: (stepId: string) => void;
}> = ({ section, activeStepId, stepThoughts, working, onStepClick }) => {
  const hasRunning = section.steps.some((s) => s.status === 'running');
  const hasError = section.steps.some((s) => s.status === 'error');
  // 默认折叠;运行中/失败的段自动展开定位
  const [expanded, setExpanded] = useState(hasRunning || hasError);
  const [touched, setTouched] = useState(false);

  // 运行推进到本段时自动展开(用户点过则尊重手动选择)
  useEffect(() => {
    if (!touched && (hasRunning || hasError)) setExpanded(true);
  }, [hasRunning, hasError, touched]);

  // 运行结束 → 整段收敛(过程退场,结果为主)
  const prevWorkingRef = useRef(working);
  useEffect(() => {
    if (prevWorkingRef.current && !working) {
      setExpanded(false);
      setTouched(false);
    }
    prevWorkingRef.current = working;
  }, [working]);

  const totalCount = section.steps.length;
  const completedCount = section.steps.filter(
    (s) => s.status === 'completed' || s.status === 'error'
  ).length;

  const meta = totalCount > 0 ? `${completedCount}/${totalCount}` : undefined;

  return (
    <div className="mb-0.5">
      {/* Section header:折叠开关 + 标题 + 步数 */}
      <button
        className="flex w-full items-center gap-2 rounded-lg px-2 py-[6px] text-left transition-colors hover:bg-slate-50"
        onClick={() => {
          setTouched(true);
          setExpanded(!expanded);
        }}
        aria-expanded={expanded}
      >
        <CaretRightOutlined
          className={`flex-shrink-0 text-[10px] text-slate-400 transition-transform duration-150 ${expanded ? 'rotate-90' : ''}`}
        />
        <StatusNode status={hasError ? 'error' : hasRunning ? 'running' : section.is_completed ? 'completed' : 'pending'} />
        <span className={`min-w-0 flex-1 truncate text-[12.5px] font-medium ${hasRunning ? 'text-indigo-600' : 'text-slate-700'}`}>
          {section.title}
        </span>
        {meta && (
          <span className="flex-shrink-0 font-mono text-[10px] tabular-nums text-slate-400">
            {meta}
          </span>
        )}
      </button>

      {/* 导轨步骤列表 */}
      {expanded && (
        <div className="relative ml-[15px] space-y-0.5 border-l-[1.5px] border-slate-200/70 py-1 pl-[12px]">
          {section.steps.map((step) => (
            <StepCard
              key={step.id}
              step={step}
              isActive={step.id === activeStepId}
              thought={stepThoughts[step.id]}
              onClick={() => onStepClick?.(step.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════════
   Artifact card
   ═══════════════════════════════════════════════════════════════ */

const ArtifactCard: FC<{
  artifact: ManusArtifactItem;
  onClick?: () => void;
}> = ({ artifact, onClick }) => {
  const typeIcons: Record<string, string> = {
    file: '📄',
    table: '📊',
    chart: '📈',
    image: '🖼️',
    code: '💻',
    markdown: '📝',
    summary: '📋',
    html: '🌐',
  };

  const archiveExts = [
    'tar.gz', 'tar.bz2', 'tar.xz', 'tgz', 'tbz2', 'txz',
    'zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz',
    'zst', 'lz4', 'lz', 'lzo', 'sz', 'rz',
    'jar', 'war', 'ear', 'skill',
  ];
  const isArchive = archiveExts.some(ext => artifact.name.toLowerCase().endsWith(`.${ext}`) || artifact.name.toLowerCase().endsWith(ext));
  const icon = isArchive ? '📦' : (typeIcons[artifact.type] || '📄');

  return (
    <div
      className="group flex cursor-pointer items-center gap-2.5 rounded-lg border border-slate-200/80 bg-white px-2.5 py-2 transition-all duration-150 hover:-translate-y-px hover:border-indigo-200 hover:bg-indigo-50/40 hover:shadow-sm"
      onClick={onClick}
    >
      <span className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md border border-slate-100 bg-slate-50 text-sm">
        {icon}
      </span>
      <div className="min-w-0 flex-1">
        <div className="truncate text-[12.5px] font-medium text-slate-700">
          {artifact.name}
        </div>
      </div>
      {artifact.downloadable && (
        <Tooltip title="下载">
          <DownloadOutlined className="flex-shrink-0 text-xs text-slate-300 opacity-0 transition-all group-hover:text-indigo-400 group-hover:opacity-100" />
        </Tooltip>
      )}
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════════
   Main left panel component
   ═══════════════════════════════════════════════════════════════ */

const VisManusLeftPanel: FC<IProps> = ({ data, onStepClick, onArtifactClick }) => {
  const {
    sections = [],
    active_step_id,
    is_working,
    step_thoughts = {},
    artifacts = [],
  } = data;

  // 全局进度
  const { doneAll, totalAll } = useMemo(() => {
    let done = 0;
    let total = 0;
    sections.forEach((sec) => {
      total += sec.steps.length;
      done += sec.steps.filter((s) => s.status === 'completed' || s.status === 'error').length;
    });
    return { doneAll: done, totalAll: total };
  }, [sections]);

  const allDone = totalAll > 0 && doneAll === totalAll;
  const pctAll = totalAll > 0 ? Math.round((doneAll / totalAll) * 100) : 0;

  return (
    <div className="flex max-h-[60vh] flex-col">
      {/* 总进度头部 */}
      {(sections.length > 0 || is_working) && (
        <div className="flex-shrink-0 border-b border-slate-100 px-4 pb-3 pt-3">
          <div className="flex items-center gap-2">
            {is_working ? (
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-indigo-400 opacity-60" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-indigo-500" />
              </span>
            ) : allDone ? (
              <CheckCircleFilled className="text-[11px] text-emerald-500" />
            ) : (
              <span className="h-2 w-2 rounded-full bg-slate-300" />
            )}
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              {is_working ? '正在执行' : allDone ? '执行完成' : '执行进度'}
            </span>
            {totalAll > 0 && (
              <span className="ml-auto text-[11px] font-medium tabular-nums text-slate-400">
                {doneAll}/{totalAll}
              </span>
            )}
          </div>
          {totalAll > 0 && (
            <div className="mt-2 h-1 overflow-hidden rounded-full bg-slate-100">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  allDone
                    ? 'bg-gradient-to-r from-emerald-400 to-emerald-500'
                    : 'bg-gradient-to-r from-indigo-400 via-indigo-500 to-violet-500'
                }`}
                style={{ width: `${pctAll}%` }}
              />
            </div>
          )}
        </div>
      )}

      {/* Sections */}
      <div className="min-h-0 flex-1 space-y-0.5 overflow-y-auto px-3 py-2">
        {sections.length > 0 ? (
          sections.map((section) => (
            <SectionBlock
              key={section.id}
              section={section}
              activeStepId={active_step_id}
              stepThoughts={step_thoughts}
              working={is_working}
              onStepClick={onStepClick}
            />
          ))
        ) : (
          <div className="flex flex-col items-center justify-center gap-2.5 py-10">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl border border-indigo-100 bg-indigo-50 text-indigo-400">
              <LoadingOutlined spin />
            </span>
            <span className="text-xs text-slate-400">等待执行…</span>
          </div>
        )}
      </div>

      {/* Artifacts */}
      {artifacts.length > 0 && (
        <div className="flex-shrink-0 border-t border-slate-100 px-3 py-3">
          <div className="mb-2 flex items-center gap-1.5 px-1">
            <span className="flex h-5 w-5 items-center justify-center rounded-md border border-emerald-100 bg-emerald-50 text-[10px] text-emerald-500">
              <FileOutlined />
            </span>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              产物
            </span>
            <span className="rounded-full bg-slate-100 px-1.5 py-px text-[10px] font-semibold tabular-nums text-slate-500">
              {artifacts.length}
            </span>
          </div>
          <div className="max-h-44 space-y-1.5 overflow-y-auto">
            {artifacts.map((artifact) => (
              <ArtifactCard
                key={artifact.id}
                artifact={artifact}
                onClick={() => onArtifactClick?.(artifact)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default VisManusLeftPanel;
