'use client';

/**
 * 带 trigger 唤起能力的通用文本框。
 *
 * 与对话输入框共用 detectTrigger / SceneTriggerMenu,靠 `triggers` prop 决定
 * 启用哪些字符 —— 这是「场景空间输入体验全局一致」的落点:
 * 剧本任务/触发器的指令框与对话输入框是同一种控件,只是启用范围不同。
 *
 * 指令框默认只开 `#`:剧本已经定了"用什么做",任务已经定了"谁来做",
 * 指令里只剩"对什么做"。
 */

import { useEffect, useRef, useState } from 'react';
import { Input } from 'antd';
import { CloseOutlined } from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { apiInterceptors, listArtifacts, listAssets } from '@/client/api';
import { SceneTriggerMenu } from './scene-trigger-menu';
import type { SceneTriggerMenuHandle, SceneTriggerSelection } from './scene-trigger-menu';
import { detectTrigger, stripTrigger } from './trigger-detect';
import type { TriggerChar, TriggerState } from './trigger-detect';
import type { ArtifactRef, AssetRef, ResourceRef } from './trigger-types';

export interface TriggerTextAreaProps {
  value?: string;
  onChange?: (v: string) => void;
  /** 启用的 trigger 集合,默认只开 `#` */
  triggers?: readonly TriggerChar[];
  /** 空间 id:`#` 数据源按空间维度拉取 */
  workspaceId?: number;
  /** 选中的资源引用(受控,便于宿主随表单一起提交) */
  refs?: ResourceRef[];
  onRefsChange?: (refs: ResourceRef[]) => void;
  placeholder?: string;
  rows?: number;
  disabled?: boolean;
}

export function TriggerTextArea({
  value = '',
  onChange,
  triggers = ['#'],
  workspaceId,
  refs = [],
  onRefsChange,
  placeholder,
  rows = 3,
  disabled,
}: TriggerTextAreaProps) {
  const [trigger, setTrigger] = useState<TriggerState | null>(null);
  const [requested, setRequested] = useState(false);
  const menuRef = useRef<SceneTriggerMenuHandle>(null);
  /**
   * 最新输入文本。受控组件无法像非受控那样用函数式更新拿到最新值,
   * 若直接读 value prop,在父级(如 Form)尚未回流时会清错文本。
   */
  const latestTextRef = useRef(value);
  /**
   * 只在 value prop 真正变化时回写 —— 若放在组件体直接赋值,
   * handleChange 里 setTrigger 引发的 rerender 会把刚输入的值冲掉。
   */
  useEffect(() => {
    latestTextRef.current = value;
  }, [value]);

  // `#` 数据源:首次唤起菜单时才拉
  const { data: artifactList, loading: artifactsLoading } = useRequest(async () => {
    if (!workspaceId || !requested) return [];
    const [err, res] = await apiInterceptors(listArtifacts({ workspace_id: workspaceId }));
    return err ? [] : (((res as any)?.items ?? res ?? []) as ArtifactRef[]);
  }, { refreshDeps: [workspaceId, requested] });

  const { data: assetList, loading: assetsLoading } = useRequest(async () => {
    if (!workspaceId || !requested) return [];
    const [err, res] = await apiInterceptors(listAssets({ workspace_id: workspaceId }));
    return err ? [] : (((res as any)?.items ?? res ?? []) as AssetRef[]);
  }, { refreshDeps: [workspaceId, requested] });

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const v = e.target.value;
    latestTextRef.current = v;
    onChange?.(v);
    const caret = (e.target as HTMLTextAreaElement).selectionStart ?? v.length;
    const next = detectTrigger(v, caret, triggers);
    if (next) setRequested(true);
    setTrigger(next);
  };

  /** 选中后清掉 trigger token,保留焦点 */
  const consumeTriggerToken = () => {
    if (trigger) onChange?.(stripTrigger(latestTextRef.current, trigger));
    setTrigger(null);
  };

  const addRef = (kind: 'artifact' | 'asset', ref: ArtifactRef | AssetRef) => {
    const meta =
      kind === 'artifact'
        ? {
            id: `artifact:${(ref as ArtifactRef).artifact_id}`,
            label: (ref as ArtifactRef).title,
            ref_id: (ref as ArtifactRef).artifact_id,
          }
        : {
            id: `asset:${(ref as AssetRef).asset_id}`,
            label: (ref as AssetRef).name,
            ref_id: (ref as AssetRef).asset_id,
          };
    if (!refs.some((r) => r.id === meta.id)) {
      onRefsChange?.([
        ...refs,
        {
          ...meta,
          kind,
          content_ref: ref.content_ref,
          start: latestTextRef.current.length,
          end: latestTextRef.current.length,
        },
      ]);
    }
    consumeTriggerToken();
  };

  const handleSelect = (sel: SceneTriggerSelection) => {
    if (sel.type === 'artifact' && sel.artifact) addRef('artifact', sel.artifact);
    else if (sel.type === 'asset' && sel.asset) addRef('asset', sel.asset);
  };

  return (
    <div className="w-full">
      <SceneTriggerMenu
        ref={menuRef}
        trigger={trigger}
        artifacts={artifactList ?? []}
        artifactsLoading={artifactsLoading}
        assets={assetList ?? []}
        assetsLoading={assetsLoading}
        onSelect={handleSelect}
        onClose={() => setTrigger(null)}
      >
        <Input.TextArea
          value={value}
          onChange={handleChange}
          onKeyDown={(e) => {
            // 指令框不拦截 Enter(提交走表单按钮),只让菜单消费方向键/Enter/Esc
            if (trigger && menuRef.current?.handleKey(e)) return;
          }}
          placeholder={placeholder}
          rows={rows}
          disabled={disabled}
        />
      </SceneTriggerMenu>

      {refs.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {refs.map((ref) => (
            <span
              key={ref.id}
              className="inline-flex items-center gap-1 rounded-md border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-2 py-0.5 text-[11px] text-gray-600 dark:text-gray-300"
            >
              <span className="text-gray-400">
                {ref.kind === 'artifact' ? '交付' : '资产'}
              </span>
              <span className="max-w-[160px] truncate">{ref.label}</span>
              <button
                type="button"
                className="text-gray-400 hover:text-red-500 transition-colors"
                onClick={() => onRefsChange?.(refs.filter((r) => r.id !== ref.id))}
                title="移除引用"
              >
                <CloseOutlined className="text-[10px]" />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
