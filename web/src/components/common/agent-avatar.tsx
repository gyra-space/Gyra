'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { SmartPluginIcon } from '@/components/icons/smart-plugin-icon';
import { getAvatarColor, getInitial, isDefaultAvatar, resolveAvatarUrl } from '@/utils/agent-avatar';

interface AgentAvatarProps {
  /** Agent icon URL / gyra-fs URI。空值、magic 值 `smart-plugin` 或历史默认占位图均视为未上传。 */
  icon?: string | null;
  /** Agent name，用于首字母头像回退与图片 alt。 */
  name?: string | null;
  /** 渲染尺寸（像素）。 */
  size?: number;
  /** 附加类名（如圆角、边框）。 */
  className?: string;
  /** 是否渲染为圆形（默认圆形，移除圆角样式时传 false）。 */
  rounded?: boolean;
}

/**
 * 统一的 Agent 头像组件，全链路共用：
 * 1. 已上传 icon → 渲染图片（自动 transformFileUrl，兼容 gyra-fs://）。
 * 2. 未上传 → 名称首字母彩色头像（无名称时回退 SmartPlugin SVG 图标）。
 * 3. 图片加载失败 → 自动回退到首字母头像。
 */
export const AgentAvatar: React.FC<AgentAvatarProps> = ({
  icon,
  name,
  size = 36,
  className = '',
  rounded = true,
}) => {
  const [error, setError] = useState(false);

  useEffect(() => {
    setError(false);
  }, [icon]);

  const displayName = name || '';
  const initial = useMemo(() => getInitial(displayName), [displayName]);
  const bgColor = useMemo(() => getAvatarColor(displayName), [displayName]);
  const src = useMemo(() => resolveAvatarUrl(isDefaultAvatar(icon) ? '' : icon), [icon]);

  const containerCls = `flex items-center justify-center overflow-hidden ${className}`;
  const radius = rounded ? 'rounded-full' : '';
  const commonStyle = { width: size, height: size };

  if (!src || error) {
    if (!displayName) {
      return (
        <div className={`${containerCls} ${radius}`} style={commonStyle}>
          <SmartPluginIcon size={Math.round(size * 0.75)} />
        </div>
      );
    }
    return (
      <div
        className={`${containerCls} ${radius} text-white font-medium`}
        style={{ ...commonStyle, backgroundColor: bgColor, fontSize: size * 0.45 }}
      >
        {initial}
      </div>
    );
  }

  return (
    <div className={`${containerCls} ${radius}`} style={commonStyle}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt={displayName || 'Agent'}
        className="w-full h-full object-cover"
        onError={() => setError(true)}
      />
    </div>
  );
};

export default AgentAvatar;