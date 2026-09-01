"use client";
import { ChatContext, ChatContextProvider } from "@/contexts";
import { InteractionProvider } from "@/components/interaction";
import SideBar from "@/components/layout/side-bar";
import TopHeader from "@/components/layout/top-header";
import CommandPalette from "@/components/layout/command-palette";
import {
  STORAGE_LANG_KEY,
  STORAGE_USERINFO_KEY,
  STORAGE_USERINFO_VALID_TIME_KEY,
} from "@/utils/constants/index";
import { App, ConfigProvider, MappingAlgorithm, Spin, theme } from "antd";
import enUS from "antd/locale/en_US";
import zhCN from "antd/locale/zh_CN";
import Head from "next/head";
import React, { useContext, useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { usePathname, useSearchParams } from "next/navigation";
import "./i18n";
import "@fontsource-variable/inter";
import "../styles/globals.css";
import { Suspense } from 'react'
import dynamic from "next/dynamic";
import { authService } from "@/services/auth";
import { setMessageInstance } from "@/utils/antd-instance";

// 附件预览弹窗宿主：全局挂载一次，供所有输入框/消息流的附件点击预览复用。
// 懒加载，避免把预览器依赖（GPTVis / syntax-highlighter）打进首屏 chunk。
const AttachmentPreviewHost = dynamic(
  () =>
    import("@/components/chat/input/attachment-preview").then((m) => ({
      default: m.AttachmentPreviewHost,
    })),
  { ssr: false }
);

// Prevent SSR flash
const EmptyLayout = ({ children }: { children: React.ReactNode }) => <>{children}</>;

// 把 App.useApp() 的 message 实例挂到全局 holder，供组件外 (axios 拦截器等) 使用
function StaticInstanceBridge() {
  const { message } = App.useApp();
  useEffect(() => {
    setMessageInstance(message);
  }, [message]);
  return null;
}

// 全局 AntD 主题 —— 与 src/styles/globals.css 设计 token 对齐
const antdTheme = {
  token: {
    colorPrimary: "#4f46e5",
    colorInfo: "#4f46e5",
    colorSuccess: "#22c55e",
    colorWarning: "#f59e0b",
    colorError: "#ef4444",
    colorText: "#14161c",
    colorTextSecondary: "#5d6577",
    colorTextTertiary: "#8a92a6",
    colorBorder: "#e5e8ef",
    colorBorderSecondary: "#eff1f6",
    colorFillSecondary: "#f2f4f8",
    colorBgLayout: "#f7f8fa",
    borderRadius: 8,
    borderRadiusSM: 6,
    borderRadiusLG: 12,
    fontSize: 13,
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Segoe UI", Roboto, sans-serif',
    boxShadowTertiary: "0 1px 2px rgba(16, 24, 40, 0.04)",
    boxShadowSecondary: "0 4px 16px rgba(16, 24, 40, 0.08)",
    boxShadow: "0 12px 40px rgba(16, 24, 40, 0.12)",
    controlHeight: 34,
  },
  components: {
    Button: { fontWeight: 500, primaryShadow: "none" },
    Card: { boxShadowTertiary: "0 1px 2px rgba(16, 24, 40, 0.04)" },
    Menu: { itemBorderRadius: 8 },
    Input: { activeShadow: "0 0 0 3px rgba(79, 70, 229, 0.08)" },
  },
};

const antdDarkTheme: MappingAlgorithm = (seedToken, mapToken) => {
  return {
    ...theme.darkAlgorithm(seedToken, mapToken),
    colorBgBase: "#232734",
    colorBorder: "#828282",
    colorBgContainer: "#232734",
  };
};

function CssWrapper({ children }: { children: React.ReactElement }) {
  const { mode } = useContext(ChatContext);
  const { i18n } = useTranslation();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (mode) {
      document.body?.classList?.add(mode);
      if (mode === "light") {
        document.body?.classList?.remove("dark");
      } else {
        document.body?.classList?.remove("light");
      }
      // Keep html data-theme and class in sync for markdown / CSS selectors
      document.documentElement?.setAttribute("data-theme", mode);
      document.documentElement?.classList?.remove(mode === "light" ? "dark" : "light");
      document.documentElement?.classList?.add(mode);
    }
  }, [mode]);

  useEffect(() => {
    if (mounted) {
      i18n.changeLanguage?.(
        window.localStorage.getItem(STORAGE_LANG_KEY) || "zh"
      );
    }
  }, [i18n, mounted]);

  if (!mounted) return <>{children}</>;

  return <div className="h-screen overflow-hidden">{children}</div>;
}

// 移动端设备检测:窄屏(≤767px)或移动 UA 视为移动设备,用于自动进入 /m 移动端模式
function useIsMobileDevice() {
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 767px)');
    const isMobileUA = () =>
      /Android|iPhone|iPod|iPad|Mobile|Windows Phone|webOS/i.test(
        navigator.userAgent
      );
    const update = () => setIsMobile(mq.matches || isMobileUA());
    update();
    mq.addEventListener('change', update);
    return () => mq.removeEventListener('change', update);
  }, []);
  return isMobile;
}

function LayoutWrapper({ children }: { children: React.ReactNode }) {
  const { mode } = useContext(ChatContext);
  const { i18n } = useTranslation();
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);
  const [authChecked, setAuthChecked] = useState(false);
  const authCheckInProgress = useRef(false);

  const isMobileDevice = useIsMobileDevice();
  const prevMobileDevice = useRef(isMobileDevice);

  // 移动设备 + 非移动路由 → 自动进入移动端模式
  useEffect(() => {
    if (!mounted || !isMobileDevice) return;
    const p = pathname || '';
    if (p.startsWith('/app-card-share')) return; // 分享页桌面/移动统一渲染
    if (p.startsWith('/m/') || p === '/m') return; // 已在移动端
    if (p === '/auth/callback') return; // 桌面/移动共用 OAuth 回调,不跳转
    if (p === '/login') {
      window.location.replace('/m/login');
      return;
    }
    if (p.startsWith('/workspaces/detail')) {
      // 桌面工作区详情 → 移动工作区,保留 id 参数
      window.location.replace('/m/workspace' + window.location.search);
      return;
    }
    // 其余桌面路由 → 移动首页
    window.location.replace('/m/');
  }, [mounted, isMobileDevice, pathname]);

  // 设备由移动端切回桌面(如拉宽窗口) → 自动从 /m 回到对应桌面路由
  useEffect(() => {
    if (!mounted) return;
    const wasMobile = prevMobileDevice.current;
    prevMobileDevice.current = isMobileDevice;
    if (isMobileDevice || !wasMobile) return; // 仅当"曾是移动 → 现为桌面"才回跳
    const p = pathname || '';
    if (!p.startsWith('/m/')) return; // 不在移动端,无需处理
    if (p === '/m/login') {
      window.location.replace('/login');
      return;
    }
    if (p.startsWith('/m/workspace')) {
      // 移动工作区 → 桌面工作区详情,保留 id 参数
      window.location.replace('/workspaces/detail' + window.location.search);
      return;
    }
    // 其余移动路由 → 桌面首页
    window.location.replace('/');
  }, [mounted, isMobileDevice, pathname]);

  // 公开页面:直接渲染(无侧边栏)。app-card-share 为应用卡片独立分享页(匿名无需登录)
  if (pathname?.startsWith("/app-card-share")) {
    return (
      <ConfigProvider
        locale={i18n.language === "en" ? enUS : zhCN}
        theme={{ ...antdTheme, algorithm: undefined }}
      >
        <App><StaticInstanceBridge />{children}</App>
      </ConfigProvider>
    );
  }

  const isPublicRoute =
    pathname?.startsWith("/login") ||
    pathname?.startsWith("/auth/callback") ||
    pathname?.startsWith("/m/login");
  // 移动端独立路由 /m/*:保留认证,但跳过桌面侧边栏/命令面板,由 /m/layout 提供全屏移动壳
  // 注意必须用 "/m/" 前缀,避免误伤 /mcp /models /me /monitoring 等以 /m 开头的桌面路由
  const isMobileRoute = pathname?.startsWith("/m/");

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted || isPublicRoute || authCheckInProgress.current) return;

    const checkAuth = async () => {
      authCheckInProgress.current = true;
      try {
        const me = await authService.getMe();
        const user = {
          user_channel: me.user_channel,
          user_no: me.user_no,
          nick_name: me.nick_name,
          avatar_url: me.avatar_url || me.user?.avatar || '',
          email: me.email || me.user?.email || '',
          role: me.role || 'normal',
        };
        localStorage.setItem(STORAGE_USERINFO_KEY, JSON.stringify(user));
        localStorage.setItem(STORAGE_USERINFO_VALID_TIME_KEY, Date.now().toString());
        window.dispatchEvent(new Event('userinfochanged'));
        setAuthChecked(true);
      } catch {
        localStorage.removeItem(STORAGE_USERINFO_KEY);
        localStorage.removeItem(STORAGE_USERINFO_VALID_TIME_KEY);
        const currentPath = window.location.pathname;
        const next = encodeURIComponent(currentPath + window.location.search);
        if (currentPath.startsWith("/m/")) {
          // 移动端未登录 → 移动专属登录页
          window.location.href = `/m/login?next=${next}`;
        } else if (!currentPath.startsWith("/login") && !currentPath.startsWith("/auth/callback")) {
          window.location.href = `/login?next=${next}`;
        }
      } finally {
        authCheckInProgress.current = false;
      }
    };
    checkAuth();
  }, [mounted, isPublicRoute]);

  // 公开页面：直接渲染（无侧边栏）
  if (isPublicRoute) {
    return (
      <ConfigProvider
        locale={i18n.language === "en" ? enUS : zhCN}
        theme={{ ...antdTheme, algorithm: undefined }}
      >
        <App><StaticInstanceBridge />{children}</App>
      </ConfigProvider>
    );
  }

  if (!authChecked) {
    return (
      <ConfigProvider
        locale={i18n.language === "en" ? enUS : zhCN}
        theme={{ ...antdTheme, algorithm: undefined }}
      >
        <App className="w-screen h-screen flex items-center justify-center">
          <Spin />
        </App>
      </ConfigProvider>
    );
  }

  const renderContent = () => {
    if (isMobileRoute) {
      // 移动端:全屏无桌面侧栏,由 /m/layout 渲染移动壳
      return <>{children}</>;
    }
    return (
      <div className="flex w-screen h-screen overflow-hidden">
        <Head>
          <meta
            name="viewport"
            content="initial-scale=1.0, width=device-width, maximum-scale=1"
          />
        </Head>
        <div className="transition-[width] duration-300 ease-in-out h-full flex flex-col">
          <SideBar />
        </div>
        <div className="flex flex-col flex-1 overflow-hidden">
          {children}
        </div>
        <CommandPalette />
      </div>
    );
  };

  return (
    <ConfigProvider
      locale={i18n.language === "en" ? enUS : zhCN}
      theme={{
        ...antdTheme,
        algorithm: mode === "dark" ? theme.darkAlgorithm : undefined,
      }}
    >
      <App>
        <StaticInstanceBridge />
        {renderContent()}
        <AttachmentPreviewHost />
      </App>
    </ConfigProvider>
  );
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning data-theme="light" className="light">
      <head>
        <title>Gyra</title>
        <meta name="description" content="Gyra — The Team-Native AI Flywheel. AI-Native Multi-Agent development and runtime framework." />
        <link rel="icon" href="/gyra-logo.svg" type="image/svg+xml" />
        <link rel="apple-touch-icon" href="/gyra-logo.jpg" />
      </head>
      <body suppressHydrationWarning={true} className="bg-surface-page dark:bg-[#111]">
        <Suspense fallback={
          <App className="w-screen h-screen flex items-center justify-center">
            <Spin />
          </App>
          }>
          <ChatContextProvider>
            <InteractionProvider autoConnect={false}>
              <CssWrapper>
                <LayoutWrapper>{children}</LayoutWrapper>
              </CssWrapper>
            </InteractionProvider>
          </ChatContextProvider>
        </Suspense>
      </body>
    </html>
  );
}
