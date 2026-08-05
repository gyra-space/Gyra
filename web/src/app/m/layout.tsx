'use client';

import type { ReactNode } from 'react';
import { ConfigProvider, theme } from 'antd';
import Head from 'next/head';
import '@/styles/mobile.css';

/**
 * Gyra Mobile · 移动端独立布局壳
 * 全屏深空主题、安全区适配、桌面端居中 480px 手机列、底部导航由页内渲染。
 * 认证与 /m 旁路已在根 layout.tsx 处理;此处仅负责视觉壳与主题。
 */
const mobileTheme = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: '#6d5cff',
    colorInfo: '#6d5cff',
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
    borderRadius: 10,
    borderRadiusSM: 8,
    borderRadiusLG: 12,
    fontSize: 14,
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC", "Hiragino Sans GB", "Segoe UI", Roboto, sans-serif',
  },
  components: {
    Input: { activeShadow: '0 0 0 3px rgba(109,92,255,0.18)' },
    Button: { fontWeight: 500 },
  },
};

export default function MobileLayout({ children }: { children: ReactNode }) {
  return (
    <ConfigProvider theme={mobileTheme}>
      <Head>
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1, viewport-fit=cover, maximum-scale=1"
        />
        <meta name="theme-color" content="#0b0d14" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
      </Head>
      <div className="ms-app">
        <div className="ms-frame">{children}</div>
      </div>
    </ConfigProvider>
  );
}