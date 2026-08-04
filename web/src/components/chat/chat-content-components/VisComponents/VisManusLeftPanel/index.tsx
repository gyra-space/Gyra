'use client';

import React, { FC, useMemo, useState } from 'react';
import { Tooltip } from 'antd';
import {
  CheckOutlined,
  CloseOutlined,
  CheckCircleFilled,
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
   Status node — 导轨上的状态节点(Linear / Manus 风格)
   ═══════════════════════════════════════════════════════════════ */

const StatusNode: FC<{ status: ManusStepStatus }> = ({ status }) => {
  if (status === 'running') {
    return (
      <span className="relative z-10 flex h-[14px] w-[14px] flex-shrink-0 items-center justify-center rounded-full border-2 border-indigo-500 bg-white shadow-[0_0_0_3px_rgba(79,70,229,0.12)]">
        <span className="h-[5px] w-[5px] animate-pulse rounded-full bg-indigo-500" />
      </span>
    );
  }
  if (status === 'completed') {
    return (
      <span className="relative z-10 flex h-[14px] w-[14px] flex-shrink-0 items-center justify-center rounded-full border-2 border-emerald-500 bg-emerald-500">
        <CheckOutlined className="text-[7px] text-white" />
      </span>
    );
  }
  if (status === 'error') {
    return (
      <span className="relative z-10 flex h-[14px] w-[14px] flex-shrink-0 items-center justify-center rounded-full border-2 border-red-500 bg-red-500">
        <CloseOutlined className="text-[7px] text-white" />
      </span>
    );
  }
  // pending — 空心节点
  return (
    <span className="relative z-10 h-[14px] w-[14px] flex-shrink-0 rounded-full border-2 border-slate-300 bg-white" />
  );
};

/* ═══════════════════════════════════════════════════════════════
   Step card — 节点挂在导轨上,内容卡浮动在右侧
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
        group relative flex items-start gap-2.5 rounded-xl border px-2.5 py-2 cursor-pointer
        transition-all duration-150
        ${isActive
          ? 'border-indigo-200 bg-indigo-50/60 shadow-sm'
          : 'border-transparent hover:border-slate-200 hover:bg-slate-50'
        }
      `}
      onClick={onClick}
    >
      {/* 状态节点(吸附在左侧导轨线上) */}
      <span className="absolute -left-[20px] top-[10px]">
        <StatusNode status={step.status} />
      </span>

      {/* 类型 icon tile */}
      <span
        className="mt-[1px] flex h-[22px] w-[22px] flex-shrink-0 items-center justify-center rounded-md border text-[11px]"
        style={{
          color: config.color,
          backgroundColor: `${config.color}12`,
          borderColor: `${config.color}26`,
        }}
      >
        {config.icon}
      </span>

      {/* 内容 */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span
            className="text-[10px] font-semibold uppercase tracking-wider"
            style={{ color: config.color }}
          >
            {config.label}
          </span>
          {step.status === 'running' && (
            <LoadingOutlined className="text-[10px] text-indigo-400" spin />
          )}
        </div>
        <div className="mt-px truncate text-[13px] font-medium leading-snug text-slate-800">
          {step.title}
        </div>
        {step.subtitle && (
          <div className="mt-px truncate text-[11px] text-slate-400">
            {step.subtitle}
          </div>
        )}

        {/* 思考气泡 */}
        {thought && (
          <div className="mt-1.5">
            <button
              className="flex items-center gap-1 text-[11px] font-medium text-indigo-400 transition-colors hover:text-indigo-600"
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
              <div className="mt-1.5 whitespace-pre-wrap rounded-lg border border-slate-100 bg-slate-50/80 p-2.5 text-[11.5px] leading-relaxed text-slate-500">
                {thought}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════════
   Section block — 标题 + mini 进度 + 导轨步骤列表
   ═══════════════════════════════════════════════════════════════ */

const SectionBlock: FC<{
  section: ManusThinkingSection;
  activeStepId?: string;
  stepThoughts: Record<string, string>;
  onStepClick?: (stepId: string) => void;
}> = ({ section, activeStepId, stepThoughts, onStepClick }) => {
  const [expanded, setExpanded] = useState(true);

  const completedCount = section.steps.filter(
    (s) => s.status === 'completed' || s.status === 'error'
  ).length;
  const totalCount = section.steps.length;
  const pct = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;
  const allDone = totalCount > 0 && completedCount === totalCount;

  return (
    <div className="mb-1">
      {/* Section header */}
      <button
        className="flex w-full items-center gap-1.5 rounded-lg px-2 py-1.5 text-left transition-colors hover:bg-slate-50"
        onClick={() => setExpanded(!expanded)}
      >
        <CaretRightOutlined
          className={`flex-shrink-0 text-[10px] text-slate-400 transition-transform duration-150 ${expanded ? 'rotate-90' : ''}`}
        />
        <span className="min-w-0 flex-1 truncate text-[13px] font-semibold text-slate-800">
          {section.title}
        </span>
        {/* mini 进度条 + 计数 */}
        <span className="flex flex-shrink-0 items-center gap-1.5">
          <span className="h-[3px] w-9 overflow-hidden rounded-full bg-slate-100">
            <span
              className={`block h-full rounded-full transition-all duration-500 ${
                allDone
                  ? 'bg-gradient-to-r from-emerald-400 to-emerald-500'
                  : 'bg-gradient-to-r from-indigo-400 to-indigo-500'
              }`}
              style={{ width: `${pct}%` }}
            />
          </span>
          <span className="text-[10px] font-medium tabular-nums text-slate-400">
            {completedCount}/{totalCount}
          </span>
        </span>
        {section.is_completed && (
          <CheckCircleFilled className="flex-shrink-0 text-[11px] text-emerald-500" />
        )}
      </button>

      {/* 导轨步骤列表 */}
      {expanded && (
        <div className="relative ml-[15px] space-y-1 border-l-[1.5px] border-slate-200/70 py-1 pl-[13px]">
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
