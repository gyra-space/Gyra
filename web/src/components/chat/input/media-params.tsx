'use client';

import { useEffect, useMemo, useState } from 'react';
import { InputNumber, Popover, Select, Tooltip } from 'antd';
import { PictureOutlined, VideoCameraOutlined } from '@ant-design/icons';
import classNames from 'classnames';
import { useTranslation } from 'react-i18next';
import { configService } from '@/services/config';
import type { MultimediaAgentConfig } from '@/types/app';

/** 图片尺寸档位：720p/1080p/2k/4k 为标准档位（后端解析为具体像素），其余为直接尺寸 */
export const IMAGE_SIZE_OPTIONS = ['720p', '1080p', '2k', '4k', '512x512', '768x768', '1024x1024', '1024x1792', '1792x1024'];
export const VIDEO_RESOLUTION_OPTIONS = ['480p', '720p', '1080p', '2k', '4k'];
export const VIDEO_ASPECT_RATIO_OPTIONS = ['16:9', '9:16', '1:1', '4:3', '21:9'];

export interface MediaParams {
  kind?: string;
  model?: string;
  size?: string;
  resolution?: string;
  duration?: number;
  aspect_ratio?: string;
  quality?: string;
}

/** 从 appInfo.ext_config 解析多媒体 Agent 配置；非多媒体应用返回 null */
export function getMultimediaConfig(appInfo: any): MultimediaAgentConfig | null {
  const cfg = appInfo?.ext_config?.multimedia_agent;
  if (!cfg || typeof cfg !== 'object') return null;
  return cfg as MultimediaAgentConfig;
}

/** 是否为多媒体应用（ext_config.multimedia_agent 存在且未显式禁用） */
export function isMultimediaApp(appInfo: any): boolean {
  const cfg = getMultimediaConfig(appInfo);
  if (!cfg) return false;
  return cfg.enabled !== false;
}

/** 把多媒体参数序列化为 chat_in_params 的 media 项（param_type='media'，JSON 值） */
export function buildMediaChatInParam(params: MediaParams): { param_type: string; param_value: string; sub_type: string } | null {
  const keys = ['kind', 'model', 'size', 'resolution', 'duration', 'aspect_ratio', 'quality'] as const;
  const obj: Record<string, unknown> = {};
  for (const k of keys) {
    const v = params[k];
    if (v !== undefined && v !== null && v !== '') obj[k] = v;
  }
  if (Object.keys(obj).length === 0) return null;
  return {
    param_type: 'media',
    param_value: JSON.stringify(obj),
    sub_type: '',
  };
}

/**
 * 多媒体参数设定面板（Popover 内容）：模型选择 + 图片尺寸 / 视频分辨率宽高比时长。
 * 用于对话输入框与场景空间输入框。
 * - capability 固定（image/video）时按该类型渲染；
 * - capability 未指定时顶部提供 kind 切换（场景空间可 spawn 图片/视频子 Agent 场景）。
 */
export const MediaParamsPanel: React.FC<{
  capability?: string;
  /** 配置里的候选模型池（image_models / video_models），与全局可用多媒体模型合并展示 */
  modelPool?: string[];
  value?: MediaParams;
  onChange: (params: MediaParams) => void;
}> = ({ capability = 'image', modelPool = [], value = {}, onChange }) => {
  const { t } = useTranslation();
  const allowKindSwitch = !capability;
  const effectiveCapability = value.kind || capability || 'image';
  const isVideo = effectiveCapability === 'video';
  const [mediaModels, setMediaModels] = useState<string[]>([]);
  const [mediaVideoModels, setMediaVideoModels] = useState<string[]>([]);

  useEffect(() => {
    let disposed = false;
    (async () => {
      try {
        const data = await configService.getAvailableMediaModels();
        if (disposed) return;
        setMediaModels((data.image || []).map((m) => m.model));
        setMediaVideoModels((data.video || []).map((m) => m.model));
      } catch {
        /* 加载失败静默，仅展示候选池 */
      }
    })();
    return () => {
      disposed = true;
    };
  }, []);

  const activeModelPool = isVideo ? mediaVideoModels : mediaModels;
  const mergedModels = useMemo(() => {
    const set = new Set<string>([...(modelPool || []), ...activeModelPool]);
    return Array.from(set);
  }, [modelPool, activeModelPool]);

  const setParam = (key: keyof MediaParams, val: unknown) => {
    onChange({ ...value, [key]: val });
  };

  return (
    <div className="w-64 py-2">
      <div className="px-3 py-1.5 text-xs font-medium text-gray-500 flex items-center gap-1">
        {isVideo ? <VideoCameraOutlined className="text-pink-500" /> : <PictureOutlined className="text-purple-500" />}
        {t('multimedia_params', '多媒体参数')}
      </div>

      {allowKindSwitch && (
        <div className="px-3 py-1.5">
          <div className="text-xs text-gray-500 mb-1">{t('media_kind', '类型')}</div>
          <Select
            value={value.kind || 'image'}
            className="w-full !rounded-lg"
            onChange={(v) => setParam('kind', v)}
            options={[
              { value: 'image', label: '图片' },
              { value: 'video', label: '视频' },
            ]}
          />
        </div>
      )}

      {mergedModels.length > 0 && (
        <div className="px-3 py-1.5">
          <div className="text-xs text-gray-500 mb-1">{t('media_model', '生成模型')}</div>
          <Select
            allowClear
            placeholder={t('media_model_auto', '自动（系统默认）')}
            value={value.model}
            className="w-full !rounded-lg"
            onChange={(v) => setParam('model', v ?? '')}
            options={mergedModels.map((m) => ({ value: m, label: m }))}
          />
        </div>
      )}

      {isVideo ? (
        <>
          <div className="px-3 py-1.5">
            <div className="text-xs text-gray-500 mb-1">{t('video_resolution', '分辨率')}</div>
            <Select
              allowClear
              placeholder={t('use_default', '默认')}
              value={value.resolution}
              className="w-full !rounded-lg"
              onChange={(v) => setParam('resolution', v ?? '')}
              options={VIDEO_RESOLUTION_OPTIONS.map((v) => ({ value: v, label: v }))}
            />
          </div>
          <div className="px-3 py-1.5">
            <div className="text-xs text-gray-500 mb-1">{t('video_aspect_ratio', '宽高比')}</div>
            <Select
              allowClear
              placeholder={t('use_default', '默认')}
              value={value.aspect_ratio}
              className="w-full !rounded-lg"
              onChange={(v) => setParam('aspect_ratio', v ?? '')}
              options={VIDEO_ASPECT_RATIO_OPTIONS.map((v) => ({ value: v, label: v }))}
            />
          </div>
          <div className="px-3 py-1.5">
            <div className="text-xs text-gray-500 mb-1">{t('video_duration', '时长（秒）')}</div>
            <InputNumber
              min={1}
              max={600}
              placeholder={t('use_default', '默认')}
              value={value.duration}
              className="w-full !rounded-lg"
              onChange={(v) => setParam('duration', v ?? undefined)}
            />
          </div>
        </>
      ) : (
        <div className="px-3 py-1.5">
          <div className="text-xs text-gray-500 mb-1">{t('image_size', '图片尺寸')}</div>
          <Select
            allowClear
            placeholder={t('use_default', '默认')}
            value={value.size}
            className="w-full !rounded-lg"
            onChange={(v) => setParam('size', v ?? '')}
            options={IMAGE_SIZE_OPTIONS.map((v) => ({ value: v, label: v }))}
          />
        </div>
      )}
    </div>
  );
};

/**
 * 多媒体参数设置按钮：多媒体应用在输入框工具栏显示，点击弹出参数设定面板。
 * 可选的受控模式：传 value/onChange 由外部持有参数；否则内部自持。
 */
export const MediaParamsButton: React.FC<{
  capability?: string;
  modelPool?: string[];
  value?: MediaParams;
  onChange?: (params: MediaParams) => void;
}> = ({ capability = 'image', modelPool = [], value, onChange }) => {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [inner, setInner] = useState<MediaParams>({});
  const isVideo = capability === 'video';
  const current = value ?? inner;
  const applyChange = (params: MediaParams) => {
    setInner(params);
    onChange?.(params);
  };

  const activeCount = useMemo(() => {
    const keys = ['model', 'size', 'resolution', 'duration', 'aspect_ratio', 'quality'] as const;
    return keys.filter((k) => {
      const v = current[k];
      return v !== undefined && v !== null && v !== '';
    }).length;
  }, [current]);

  return (
    <Popover
      trigger="click"
      placement="topLeft"
      open={open}
      onOpenChange={setOpen}
      arrow={false}
      overlayClassName="[&_.ant-popover-inner]:!rounded-xl [&_.ant-popover-inner]:!shadow-xl"
      content={
        <MediaParamsPanel
          capability={capability}
          modelPool={modelPool}
          value={current}
          onChange={applyChange}
        />
      }
    >
      <Tooltip title={t('multimedia_params', '多媒体参数')} placement="top">
        <button
          className={classNames(
            'h-8 w-8 rounded-full flex items-center justify-center border transition-all flex-shrink-0',
            activeCount > 0
              ? 'border-[#4f46e5]/40 text-[#4f46e5] bg-[#eef0fe] dark:bg-indigo-900/20'
              : 'border-[#e5e8ef] dark:border-gray-600 text-[#5d6577] dark:text-gray-400 hover:text-[#4f46e5] hover:border-[#4f46e5]/40 hover:bg-[#eef0fe] dark:hover:bg-indigo-900/20'
          )}
        >
          {isVideo ? <VideoCameraOutlined className="text-sm" /> : <PictureOutlined className="text-sm" />}
        </button>
      </Tooltip>
    </Popover>
  );
};
