'use client';

import { useContext, useEffect, useState, type ReactNode } from 'react';
import { ConfigProvider, theme } from 'antd';
import Head from 'next/head';
import { ChatContext } from '@/contexts';
import { STORAGE_THEME_KEY } from '@/utils/constants/index';
import '@/styles/mobile.css';

/**
 * Gyra Mobile · 移动端独立布局壳
 * 视觉壳浅/深主题由移动端自身决策:仅当用户在桌面端显式切换过主题(写入了 STORAGE_THEME_KEY)
 * 才跟随;否则移动端默认浅色、不跟随系统深色偏好。深色色板作用域为 .ms-app.dark(mobile.css)。
 * 认证与 /m 旁路已在根 layout.tsx 处理。
 */
const baseTokens = {
  colorPrimary: '#6d5cff',
  colorInfo: '#6d5cff',
  borderRadius: 10,
  borderRadiusSM: 8,
  borderRadiusLG: 12,
  fontSize: 14,
  fontFamily:
    '-apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC", "Hiragino Sans GB", "Segoe UI", Roboto, sans-serif',
};

const lightTokens = {
  ...baseTokens,
  colorSuccess: '#16a34a',
  colorWarning: '#d97706',
  colorError: '#dc2626',
  colorBgBase: '#f6f7fb',
  colorBgContainer: '#ffffff',
  colorText: '#14161c',
  colorTextSecondary: '#5d6577',
  colorTextTertiary: '#8a92a6',
  colorBorder: 'rgba(15,23,42,0.12)',
  colorBorderSecondary: 'rgba(15,23,42,0.08)',
};

const darkTokens = {
  ...baseTokens,
  colorSuccess: '#34d399',
  colorWarning: '#fbbf24',
  colorError: '#f87171',
  colorBgBase: '#0b0d14',
  colorBgContainer: '#141724',
  colorText: '#e8eaf2',
  colorTextSecondary: '#9aa3b5',
  colorTextTertiary: '#5d6678',
  colorBorder: 'rgba(255,255,255,0.12)',
  colorBorderSecondary: 'rgba(255,255,255,0.08)',
};

export default function MobileLayout({ children }: { children: ReactNode }) {
  const { mode } = useContext(ChatContext);
  // 初始跟随全局 mode;挂载后按"是否显式选择过主题"重算——未显式选择则移动端固定浅色
  const [isDark, setIsDark] = useState(() => mode === 'dark');

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_THEME_KEY);
    setIsDark(stored ? stored === 'dark' : false);
  }, [mode]);

  const mobileTheme = {
    algorithm: isDark ? theme.darkAlgorithm : theme.lightAlgorithm,
    token: isDark ? darkTokens : lightTokens,
    components: {
      Input: { activeShadow: isDark ? '0 0 0 3px rgba(109,92,255,0.18)' : '0 0 0 3px rgba(109,92,255,0.14)' },
      Button: { fontWeight: 500 },
    },
  };

  return (
    <ConfigProvider theme={mobileTheme}>
      <Head>
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1, viewport-fit=cover, maximum-scale=1"
        />
        <meta name="theme-color" content={isDark ? '#0b0d14' : '#f6f7fb'} />
        <meta
          name="apple-mobile-web-app-status-bar-style"
          content={isDark ? 'black-translucent' : 'default'}
        />
      </Head>
      <div className={isDark ? 'ms-app dark' : 'ms-app'}>
        <div className="ms-frame">{children}</div>
      </div>
    </ConfigProvider>
  );
}