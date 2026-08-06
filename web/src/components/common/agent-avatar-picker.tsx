'use client';

import React, { useRef, useState } from 'react';
import { Dropdown, Spin } from 'antd';
import { CameraOutlined, DeleteOutlined, LoadingOutlined } from '@ant-design/icons';
import { uploadAgentAvatar } from '@/client/api/agent-avatar';
import { isDefaultAvatar } from '@/utils/agent-avatar';
import { AgentAvatar } from './agent-avatar';

interface AgentAvatarPickerProps {
  /** 当前头像值（icon URL / gyra-fs URI / 空字符串表示首字母头像） */
  value?: string;
  /** Agent 名称，用于首字母头像预览 */
  name?: string;
  /** 头像变更回调（传空字符串 = 使用首字母头像） */
  onChange?: (icon: string) => void;
  /** 预览尺寸（像素） */
  size?: number;
}

/**
 * 统一的 Agent 头像设置器：
 * - 点击头像本体弹出菜单，选择「上传图片」或「清除头像」。
 * - 未上传时实时预览「名称首字母头像」。
 * - 无侧置按钮、无角标，交互全部收敛在头像上。
 */
export const AgentAvatarPicker: React.FC<AgentAvatarPickerProps> = ({
  value,
  name,
  onChange,
  size = 64,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  const hasCustom = !isDefaultAvatar(value);

  const handleSelectFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    if (!file.type.startsWith('image/')) return;
    setUploading(true);
    try {
      const url = await uploadAgentAvatar(file);
      onChange?.(url);
    } catch {
      /* 上传失败保持原头像 */
    } finally {
      setUploading(false);
    }
  };

  const menuItems = [
    {
      key: 'upload',
      icon: <CameraOutlined />,
      label: '上传图片',
      onClick: () => fileInputRef.current?.click(),
    },
    ...(hasCustom
      ? [
          {
            key: 'clear',
            icon: <DeleteOutlined />,
            label: '清除头像',
            onClick: () => onChange?.(''),
          },
        ]
      : []),
  ];

  return (
    <div className="relative inline-flex" style={{ width: size, height: size }}>
      <Dropdown
        menu={{ items: menuItems }}
        trigger={['click']}
        placement="bottomRight"
        disabled={uploading}
      >
        <button
          type="button"
          className="group relative block cursor-pointer rounded-full transition-transform hover:scale-[1.03] disabled:cursor-wait"
        >
          <AgentAvatar icon={value} name={name} size={size} className="ring-2 ring-white shadow-md" />
          {/* hover 遮罩：相机图标 */}
          <span className="absolute inset-0 flex items-center justify-center rounded-full bg-black/45 text-white opacity-0 transition-opacity group-hover:opacity-100">
            {uploading ? (
              <Spin indicator={<LoadingOutlined className="text-white" spin />} />
            ) : (
              <CameraOutlined style={{ fontSize: size * 0.3 }} />
            )}
          </span>
        </button>
      </Dropdown>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        style={{ display: 'none' }}
        onChange={handleSelectFile}
      />
    </div>
  );
};

export default AgentAvatarPicker;