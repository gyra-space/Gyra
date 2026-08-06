import React from 'react';
import { AgentAvatar } from '@/components/common/agent-avatar';

interface AvatarProps {
  src: string;
  width?: string | number;
  className?: string;
  /** Agent 名称，用于首字母头像回退 */
  name?: string;
}

declare namespace NEXA_API {
  interface Result_List_String__ {
    success?: boolean;
    /** 获取错误码 */
    errorCode?: string;
    /** 获取错误信息 */
    errorMessage?: string;
    /** 获取返回数据 */
    data?: Array<string>;
    traceId?: string;
    host?: string;
  }
}

/** 统一头像组件：已上传用图片，未上传/占位图用首字母头像 */
const Avatar: React.FC<AvatarProps> = React.memo(
  ({ src, width = '32px', className, name }) => {
    const size = typeof width === 'number' ? width : parseInt(width, 10) || 32;
    return (
      <AgentAvatar
        icon={src}
        name={name}
        size={size}
        className={className}
      />
    );
  },
);

export default Avatar;