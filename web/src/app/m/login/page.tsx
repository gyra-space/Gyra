'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Spin } from 'antd';
import { authService, type OAuthProvider } from '@/services/auth';
import { STORAGE_USERINFO_KEY, STORAGE_USERINFO_VALID_TIME_KEY } from '@/utils/constants/index';
import {
  DesktopOutlined,
  GithubOutlined,
  ThunderboltOutlined,
  UserOutlined,
  LockOutlined,
} from '@ant-design/icons';

/** 移动端 OAuth 回跳记录:点 OAuth 前写入,回调页据此跳回 /m */
const MOBILE_OAUTH_NEXT_KEY = 'gyra_m_oauth_next';

function ProviderIcon({ type }: { type: string }) {
  if (type === 'github') return <GithubOutlined style={{ fontSize: 18 }} />;
  if (type === 'alibaba-inc') return <ThunderboltOutlined style={{ fontSize: 18 }} />;
  return <UserOutlined style={{ fontSize: 18 }} />;
}

function providerLabel(p: OAuthProvider): string {
  if (p.type === 'github') return 'GitHub';
  if (p.type === 'alibaba-inc') return 'Alibaba';
  return p.id;
}

/**
 * 移动端专属登录页(Deep-Space 深空主题壳)。
 * 与桌面登录逻辑同源:本地登录/注册 + OAuth 提供商。登录成功回到 next(默认 /m)。
 */
export default function MobileLoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [oauthEnabled, setOauthEnabled] = useState(false);
  const [providers, setProviders] = useState<OAuthProvider[]>([]);
  const loadedRef = useRef(false);

  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (loadedRef.current) return;
    loadedRef.current = true;
    (async () => {
      try {
        const status = await authService.getOAuthStatus();
        setOauthEnabled(status.enabled);
        setProviders(status.providers || []);
      } catch {
        setOauthEnabled(false);
        setProviders([]);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // 安全解析 next:仅允许站内相对路径,默认 /m
  const resolveNext = (): string => {
    const raw = searchParams?.get('next') || '/m';
    try {
      const decoded = decodeURIComponent(raw);
      if (decoded.startsWith('/') && !decoded.startsWith('/login')) return decoded;
    } catch {
      /* ignore */
    }
    return '/m';
  };

  const saveUserAndGo = async () => {
    try {
      const me = await authService.getMe();
      localStorage.setItem(STORAGE_USERINFO_KEY, JSON.stringify({
        user_channel: me.user_channel,
        user_no: me.user_no,
        nick_name: me.nick_name,
        avatar_url: me.avatar_url || me.user?.avatar || '',
        email: me.email || me.user?.email || '',
        role: me.role || 'normal',
      }));
      localStorage.setItem(STORAGE_USERINFO_VALID_TIME_KEY, Date.now().toString());
    } catch {
      /* will be loaded by layout */
    }
    router.replace(resolveNext());
  };

  const handleOAuth = (providerId: string) => {
    // 记录移动端回跳目标,供 /auth/callback 读取
    try {
      sessionStorage.setItem(MOBILE_OAUTH_NEXT_KEY, resolveNext());
    } catch {
      /* ignore */
    }
    window.location.href = authService.getOAuthLoginUrl(providerId);
  };

  const handleLocalLogin = async () => {
    setError('');
    if (!username.trim() || !password) { setError('请输入用户名和密码'); return; }
    setSubmitting(true);
    try {
      await authService.localLogin({ username: username.trim(), password });
      await saveUserAndGo();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.response?.data?.err_msg ?? '登录失败,请检查账号密码');
    } finally {
      setSubmitting(false);
    }
  };

  const handleLocalRegister = async () => {
    setError('');
    if (!username.trim() || username.trim().length < 3) { setError('用户名至少 3 个字符'); return; }
    if (!password || password.length < 6) { setError('密码至少 6 位'); return; }
    if (password !== confirmPassword) { setError('两次输入的密码不一致'); return; }
    setSubmitting(true);
    try {
      await authService.localRegister({ username: username.trim(), password, email: email.trim() || undefined });
      await saveUserAndGo();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.response?.data?.err_msg ?? '注册失败');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmit = () => (isRegister ? handleLocalRegister() : handleLocalLogin());

  const oauthProviders = providers.filter((p) => p.type !== 'local');
  const hasLocal = providers.some((p) => p.type === 'local');

  if (loading) {
    return (
      <div className="ms-frame__body" style={{ alignItems: 'center', justifyContent: 'center' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div className="ms-auth">
      <div className="ms-auth__top">
        <div className="ms-auth__brand">
          <div className="ms-auth__logo">G</div>
          <div className="ms-auth__brand-text">
            <div className="ms-eyebrow">GYRA</div>
            <b>移动空间</b>
          </div>
        </div>
        <button type="button" className="ms-auth__desk" onClick={() => router.push('/login')}>
          <DesktopOutlined /> 桌面端登录
        </button>
      </div>

      <h1 className="ms-auth__title">欢迎回来</h1>
      <p className="ms-auth__sub">登录后即可随时发任务、看执行、做审批。</p>

      <div className="ms-auth__card">
        {error && <div className="ms-auth__err">{error}</div>}

        {!oauthEnabled ? (
          <div className="ms-auth__sub" style={{ textAlign: 'center', padding: '12px 0' }}>
            登录未配置,请在系统设置中启用 OAuth2 或访问控制插件。
          </div>
        ) : hasLocal || oauthProviders.length === 0 ? (
          <>
            <div className="ms-auth__field">
              <div className="ms-auth__label">{isRegister ? '用户名(至少 3 字符)' : '用户名'}</div>
              <input
                className="ms-auth__input"
                placeholder="用户名"
                value={username}
                autoCapitalize="none"
                onChange={(e) => setUsername(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
              />
            </div>
            <div className="ms-auth__field">
              <div className="ms-auth__label">密码</div>
              <input
                className="ms-auth__input"
                type="password"
                placeholder="密码"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
              />
            </div>
            {isRegister && (
              <>
                <div className="ms-auth__field">
                  <div className="ms-auth__label">确认密码</div>
                  <input
                    className="ms-auth__input"
                    type="password"
                    placeholder="确认密码"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
                  />
                </div>
                <div className="ms-auth__field">
                  <div className="ms-auth__label">邮箱(可选)</div>
                  <input
                    className="ms-auth__input"
                    type="email"
                    placeholder="邮箱"
                    autoCapitalize="none"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>
              </>
            )}
            <button type="button" className="ms-auth__btn" disabled={submitting} onClick={handleSubmit}>
              {submitting ? '处理中…' : isRegister ? '创建账号' : '登录'}
            </button>
            <button
              type="button"
              className="ms-auth__switch"
              onClick={() => { setIsRegister(!isRegister); setError(''); setConfirmPassword(''); }}
            >
              {isRegister ? '已有账号?<em> 去登录</em>' : '没有账号?<em> 立即注册</em>'}
            </button>

            {oauthProviders.length > 0 && (
              <>
                <div className="ms-auth__divider">或使用第三方登录</div>
                <div className="ms-auth__oauth">
                  {oauthProviders.map((p) => (
                    <button key={p.id} type="button" className="ms-auth__oauth-btn" onClick={() => handleOAuth(p.id)}>
                      <ProviderIcon type={p.type} /> 使用 {providerLabel(p)} 登录
                    </button>
                  ))}
                </div>
              </>
            )}
          </>
        ) : (
          <>
            <div className="ms-auth__oauth">
              {oauthProviders.map((p) => (
                <button key={p.id} type="button" className="ms-auth__oauth-btn" onClick={() => handleOAuth(p.id)}>
                  <ProviderIcon type={p.type} /> 使用 {providerLabel(p)} 登录
                </button>
              ))}
            </div>
            {hasLocal && (
              <>
                <div className="ms-auth__divider">或</div>
                <button type="button" className="ms-auth__btn" onClick={() => setIsRegister(false)}>
                  <LockOutlined /> 用户名密码登录
                </button>
              </>
            )}
          </>
        )}
      </div>

      <div className="ms-auth__foot">POWERED BY GYRA</div>
    </div>
  );
}