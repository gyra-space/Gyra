'use client';

import { authService, OAuthProvider } from '@/services/auth';
import { STORAGE_USERINFO_KEY, STORAGE_USERINFO_VALID_TIME_KEY } from '@/utils/constants/index';
import {
  GithubOutlined,
  ThunderboltOutlined,
  UserOutlined,
  LockOutlined,
  MailOutlined,
  ApartmentOutlined,
  DatabaseOutlined,
  ApiOutlined,
  SyncOutlined,
  ArrowRightOutlined,
} from '@ant-design/icons';
import { Alert, Button, ConfigProvider, Input, Spin, theme } from 'antd';
import Image from 'next/image';
import { useSearchParams, useRouter } from 'next/navigation';
import { useEffect, useRef, useState, useCallback } from 'react';

// ─── 品牌展示区数据 ───
const FEATURES = [
  {
    icon: <ApartmentOutlined className="text-[17px]" />,
    title: 'Multi-Agent Orchestration',
    desc: 'Orchestrate AI-native agents that plan, collaborate and act as one team.',
  },
  {
    icon: <DatabaseOutlined className="text-[17px]" />,
    title: 'Knowledge Grounding',
    desc: 'Ground every answer in your enterprise knowledge with built-in RAG.',
  },
  {
    icon: <ApiOutlined className="text-[17px]" />,
    title: 'Tools & MCP',
    desc: 'Connect any tool, API or data source through a unified MCP layer.',
  },
  {
    icon: <SyncOutlined className="text-[17px]" />,
    title: 'Data Flywheel',
    desc: 'Shared-event data flywheel that compounds value with every interaction.',
  },
];

const ERROR_MESSAGES: Record<string, string> = {
  user_disabled: 'Your account has been disabled. Please contact the administrator.',
  missing_params: 'OAuth callback parameters missing. Please try again.',
  invalid_state: 'OAuth state verification failed. Please try again.',
  token_exchange_failed: 'Failed to obtain OAuth token. Please try again.',
  userinfo_failed: 'Failed to fetch user information. Please try again.',
  user_create_failed: 'Failed to create user. Please contact the administrator.',
};

function ProviderIcon({ type }: { type: string }) {
  if (type === 'github') return <GithubOutlined style={{ fontSize: 18 }} />;
  if (type === 'alibaba-inc') return <ThunderboltOutlined style={{ fontSize: 18 }} />;
  return <UserOutlined style={{ fontSize: 18 }} />;
}

function providerLabel(p: OAuthProvider): string {
  if (p.type === 'github') return 'GitHub';
  if (p.type === 'alibaba-inc') return 'Alibaba';
  if (p.type === 'local') return '';
  return p.id;
}

// 登录卡片浅色主题:干净输入框融入浅灰画布
const lightTheme = {
  token: {
    colorPrimary: '#4f46e5',
    colorBgContainer: '#ffffff',
    colorBorder: '#e5e8ef',
    colorTextPlaceholder: '#8a92a6',
    borderRadius: 8,
  },
};

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [providers, setProviders] = useState<OAuthProvider[]>([]);
  const [oauthEnabled, setOauthEnabled] = useState(false);
  const loadedRef = useRef(false);
  const searchParams = useSearchParams();
  const errorCode = searchParams?.get('error') || '';
  const errorMsg = errorCode ? ERROR_MESSAGES[errorCode] || `Login error: ${errorCode}` : '';

  // Local auth state
  const [isLocalMode, setIsLocalMode] = useState(false);
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [email, setEmail] = useState('');
  const [localError, setLocalError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (loadedRef.current) return;
    loadedRef.current = true;
    loadOAuthStatus();
  }, []);

  const loadOAuthStatus = async () => {
    setLoading(true);
    try {
      const status = await authService.getOAuthStatus();
      setOauthEnabled(status.enabled);
      setProviders(status.providers || []);

      // 自动登录检测：如果配置了 sso_auto_login_provider 且当前无 session
      // 自动跳转到主系统 OAuth（用户无感知）
      if (status.enabled && status.sso_auto_login_provider && !searchParams?.get('error')) {
        const hasSession = document.cookie.includes('gyra_session');
        if (!hasSession) {
          // 检查是否是从 OAuth callback 返回（避免无限循环）
          const isCallback = window.location.hash.includes('token=');
          if (!isCallback) {
            handleOAuthLogin(status.sso_auto_login_provider);
            return; // 不设置 loading=false，保持加载状态
          }
        }
      }

      const nonLocal = (status.providers || []).filter(p => p.type !== 'local');
      if (status.enabled && nonLocal.length === 0) {
        setIsLocalMode(true);
      }
    } catch {
      setOauthEnabled(false);
      setProviders([]);
    } finally {
      setLoading(false);
    }
  };

  const handleOAuthLogin = (providerId: string) => {
    window.location.href = authService.getOAuthLoginUrl(providerId);
  };

  const saveUserAndRedirect = useCallback(async () => {
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
    } catch { /* will be loaded by layout */ }
    const nextRaw = searchParams?.get('next') || '/';
    let next = '/';
    try {
      const decoded = decodeURIComponent(nextRaw);
      if (decoded.startsWith('/') && !decoded.startsWith('/login')) next = decoded;
    } catch {
      next = '/';
    }
    router.replace(next);
  }, [router, searchParams]);

  const handleLocalLogin = async () => {
    setLocalError('');
    if (!username.trim() || !password) {
      setLocalError('Please enter username and password');
      return;
    }
    setSubmitting(true);
    try {
      await authService.localLogin({ username: username.trim(), password });
      await saveUserAndRedirect();
    } catch (e: any) {
      const detail = e?.response?.data?.detail ?? e?.response?.data?.err_msg;
      setLocalError(typeof detail === 'string' && detail ? detail : 'Login failed. Please check your credentials.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleLocalRegister = async () => {
    setLocalError('');
    if (!username.trim() || username.trim().length < 3) {
      setLocalError('Username must be at least 3 characters');
      return;
    }
    if (!password || password.length < 6) {
      setLocalError('Password must be at least 6 characters');
      return;
    }
    if (password !== confirmPassword) {
      setLocalError('Passwords do not match');
      return;
    }
    setSubmitting(true);
    try {
      await authService.localRegister({
        username: username.trim(),
        password,
        email: email.trim() || undefined,
      });
      await saveUserAndRedirect();
    } catch (e: any) {
      const detail = e?.response?.data?.detail ?? e?.response?.data?.err_msg;
      setLocalError(typeof detail === 'string' && detail ? detail : 'Registration failed');
    } finally {
      setSubmitting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !submitting) {
      isRegister ? handleLocalRegister() : handleLocalLogin();
    }
  };

  if (loading) {
    return (
      <div className='relative flex items-center justify-center min-h-screen bg-[#0b0d16] overflow-hidden'>
        <div className='aurora-stage'>
          <div className='aurora-blob aurora-blob--brand top-[-10%] left-[20%] w-[520px] h-[520px]' />
          <div className='aurora-blob aurora-blob--cyan bottom-[-10%] right-[10%] w-[460px] h-[460px]' />
          <div className='aurora-blob aurora-blob--violet top-[40%] left-[60%] w-[380px] h-[380px]' />
        </div>
        <div className='relative z-10 flex flex-col items-center gap-5'>
          <Image src='/gyra-logo.svg' alt='Gyra' width={52} height={52} priority className='drop-shadow-[0_0_24px_rgba(79,70,229,0.6)]' />
          <Spin size='large' />
        </div>
      </div>
    );
  }

  const oauthProviders = providers.filter(p => p.type !== 'local');
  const hasLocal = providers.some(p => p.type === 'local');

  return (
    <div className='relative min-h-screen flex bg-[#0b0d16] overflow-hidden text-white'>
      {/* ─── 全页共享画布:极光 + 网格铺满整屏,消除左右割裂 ─── */}
      <div className='aurora-stage'>
        <div className='aurora-blob aurora-blob--brand top-[-12%] left-[-6%] w-[560px] h-[560px]' />
        <div className='aurora-blob aurora-blob--cyan bottom-[-16%] right-[2%] w-[560px] h-[560px]' />
        <div className='aurora-blob aurora-blob--violet top-[36%] left-[46%] w-[440px] h-[440px]' />
      </div>
      <div className='absolute inset-0 opacity-[0.04] pointer-events-none'
        style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)', backgroundSize: '56px 56px' }} />
      {/* 边缘压暗,视线聚焦内容 */}
      <div className='absolute inset-0 pointer-events-none bg-[radial-gradient(ellipse_at_center,transparent_50%,rgba(5,7,12,0.6)_100%)]' />

      {/* ─── 左侧品牌展示区 ─── */}
      <aside className='hidden lg:flex relative z-10 flex-col justify-between w-[46%] shrink-0 p-10 xl:p-14 overflow-y-auto min-h-0'>

        <div className='relative z-10 flex items-center gap-3 animate-rise'>
          <Image src='/gyra-logo.svg' alt='Gyra' width={40} height={40} priority className='drop-shadow-[0_0_20px_rgba(79,70,229,0.7)]' />
          <div className='flex items-baseline gap-2'>
            <span className='text-[22px] font-semibold tracking-tight'>Gyra</span>
            <span className='text-[11px] text-white/40 tracking-[0.2em] uppercase'>Flywheel</span>
          </div>
        </div>

        <div className='relative z-10 max-w-[480px] animate-rise-slow'>
          <div className='inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-white/15 bg-white/5 backdrop-blur-sm text-[12px] text-white/70 mb-5'>
            <span className='w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.9)]' />
            AI-Native Multi-Agent Platform
          </div>

          <h1 className='text-[36px] xl:text-[42px] font-semibold leading-[1.1] tracking-tight'>
            The Team-Native
            <br />
            <span className='bg-gradient-to-r from-[#00DAEF] via-[#818cf8] to-[#a78bfa] bg-clip-text text-transparent'>
              AI Flywheel
            </span>
          </h1>

          <p className='mt-4 text-[15px] leading-relaxed text-white/55 max-w-[420px]'>
            Build, run and scale intelligent agents that collaborate like a real team —
            orchestration, knowledge, tools and a compounding data flywheel in one platform.
          </p>

          {/* 特性卡片 */}
          <div className='mt-6 grid grid-cols-2 gap-3'>
            {FEATURES.map(f => (
              <div key={f.title}
                className='group rounded-xl border border-white/10 bg-white/[0.04] p-3.5 backdrop-blur-sm transition-all duration-300 hover:bg-white/[0.08] hover:border-white/20 hover:-translate-y-0.5'>
                <div className='w-8 h-8 rounded-lg flex items-center justify-center text-[#a5b4fc] bg-white/[0.06] border border-white/10 mb-2.5 transition-colors group-hover:bg-[#4f46e5] group-hover:text-white'>
                  {f.icon}
                </div>
                <h3 className='text-[13px] font-semibold text-white/90 mb-1'>{f.title}</h3>
                <p className='text-[12px] leading-relaxed text-white/45'>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* 底部：简洁品牌标语 */}
        <div className='relative z-10 flex items-center gap-3 animate-rise-slow'>
          <div className='w-8 h-8 rounded-lg bg-gradient-to-br from-[#00DAEF] to-[#4f46e5] flex items-center justify-center shadow-[0_6px_18px_rgba(79,70,229,0.4)]'>
            <ArrowRightOutlined className='text-white text-[14px]' />
          </div>
          <div className='text-[12px] text-white/40 leading-tight'>
            <div className='text-white/60 font-medium'>Powered by Gyra</div>
            <div className='text-white/30'>AI-native multi-agent orchestration</div>
          </div>
        </div>
      </aside>

      {/* ─── 右侧登录区:与品牌区共处同一深空画布 ─── */}
      <main className='relative z-10 flex-1 flex flex-col items-center justify-center px-6 py-10'>
        <div className='relative z-10 w-full max-w-[380px] animate-rise'>
          <ConfigProvider theme={darkTheme}>
          {/* 移动端 Logo */}
          <div className='lg:hidden flex items-center justify-center gap-2.5 mb-8'>
            <Image src='/gyra-logo.svg' alt='Gyra' width={34} height={34} priority className='drop-shadow-[0_0_16px_rgba(79,70,229,0.7)]' />
            <div className='flex items-baseline gap-2'>
              <span className='text-[19px] font-semibold tracking-tight'>Gyra</span>
              <span className='text-[10px] text-white/40 tracking-[0.2em] uppercase'>Flywheel</span>
            </div>
          </div>

          {/* 登录卡片:深色玻璃拟态 */}
          <div className='rounded-2xl border border-white/10 bg-[#12151f]/75 backdrop-blur-xl shadow-[0_24px_80px_rgba(0,0,0,0.5),inset_0_1px_0_rgba(255,255,255,0.06)] px-7 py-7'>
            <div className='mb-7'>
              <h2 className='text-[22px] font-semibold text-white tracking-tight'>
                Welcome back
              </h2>
              <p className='mt-1.5 text-[13px] text-white/45'>Sign in to continue to your workspace</p>
            </div>

            {errorMsg && (
              <Alert
                type={errorCode === 'user_disabled' ? 'error' : 'warning'}
                message={errorMsg}
                showIcon
                className='mb-4 rounded-lg'
              />
            )}

            {!oauthEnabled ? (
              <div className='text-center py-6'>
                <p className='text-white/45 text-sm leading-relaxed'>
                  Login is not configured.<br />
                  Please enable OAuth2 or access control plugin in System Settings.
                </p>
              </div>
            ) : isLocalMode ? (
              /* ─── Local login / register form ─── */
              <div>
                <div className='flex items-center justify-between mb-5'>
                  <h3 className='text-[15px] font-semibold text-white/90 tracking-tight'>
                    {isRegister ? 'Create Account' : 'Sign In'}
                  </h3>
                  {oauthProviders.length > 0 && (
                    <button
                      onClick={() => setIsLocalMode(false)}
                      className='text-xs text-white/45 hover:text-[#818cf8] transition-colors'
                    >
                      More options
                    </button>
                  )}
                </div>

                {localError && (
                  <Alert type='error' message={localError} showIcon className='mb-4 rounded-lg' closable onClose={() => setLocalError('')} />
                )}

                <div className='space-y-3'>
                  <Input
                    size='large'
                    prefix={<UserOutlined className='text-white/30' />}
                    placeholder='Username'
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                    onKeyDown={handleKeyDown}
                    className='rounded-lg'
                    style={{ height: 44 }}
                  />
                  <Input.Password
                    size='large'
                    prefix={<LockOutlined className='text-white/30' />}
                    placeholder='Password'
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    onKeyDown={handleKeyDown}
                    className='rounded-lg'
                    style={{ height: 44 }}
                  />
                  {isRegister && (
                    <>
                      <Input.Password
                        size='large'
                        prefix={<LockOutlined className='text-white/30' />}
                        placeholder='Confirm Password'
                        value={confirmPassword}
                        onChange={e => setConfirmPassword(e.target.value)}
                        onKeyDown={handleKeyDown}
                        className='rounded-lg'
                        style={{ height: 44 }}
                      />
                      <Input
                        size='large'
                        prefix={<MailOutlined className='text-white/30' />}
                        placeholder='Email (optional)'
                        value={email}
                        onChange={e => setEmail(e.target.value)}
                        onKeyDown={handleKeyDown}
                        className='rounded-lg'
                        style={{ height: 44 }}
                      />
                    </>
                  )}

                  <Button
                    type='primary'
                    block
                    size='large'
                    loading={submitting}
                    onClick={isRegister ? handleLocalRegister : handleLocalLogin}
                    className='rounded-lg font-medium'
                    style={{ height: 44 }}
                  >
                    {isRegister ? 'Create Account' : 'Sign In'}
                  </Button>
                </div>

                <div className='mt-4 text-center'>
                  <button
                    className='text-[13px] text-white/45 hover:text-[#818cf8] transition-colors'
                    onClick={() => {
                      setIsRegister(!isRegister);
                      setLocalError('');
                      setConfirmPassword('');
                    }}
                  >
                    {isRegister ? 'Already have an account? Sign in' : "Don't have an account? Register"}
                  </button>
                </div>

                {/* OAuth provider icons */}
                {oauthProviders.length > 0 && (
                  <>
                    <div className='flex items-center my-5'>
                      <div className='flex-1 h-px bg-white/10' />
                      <span className='px-3 text-[11px] text-white/30 uppercase tracking-widest'>or</span>
                      <div className='flex-1 h-px bg-white/10' />
                    </div>
                    <div className='flex justify-center gap-3'>
                      {oauthProviders.map(p => (
                        <button
                          key={p.id}
                          onClick={() => handleOAuthLogin(p.id)}
                          className='flex items-center justify-center w-11 h-11 rounded-xl border border-white/10 bg-white/[0.04] hover:bg-white/[0.08] hover:border-white/25 transition-all text-white/50 hover:text-white'
                          title={`Sign in with ${providerLabel(p)}`}
                        >
                          <ProviderIcon type={p.type} />
                        </button>
                      ))}
                    </div>
                  </>
                )}
              </div>
            ) : (
              /* ─── Provider selection ─── */
              <div>
                <h3 className='text-[15px] font-semibold text-white/90 mb-5 tracking-tight'>Sign In</h3>

                <div className='space-y-2.5'>
                  {oauthProviders.map(p => (
                    <button
                      key={p.id}
                      onClick={() => handleOAuthLogin(p.id)}
                      className='flex items-center w-full h-[44px] px-4 rounded-xl border border-white/10 bg-white/[0.04] hover:bg-white/[0.08] hover:border-white/25 transition-all group'
                    >
                      <span className='text-white/45 group-hover:text-white/85 transition-colors'>
                        <ProviderIcon type={p.type} />
                      </span>
                      <span className='ml-3 text-[13px] font-medium text-white/70 group-hover:text-white transition-colors'>
                        Continue with {providerLabel(p)}
                      </span>
                    </button>
                  ))}

                  {hasLocal && (
                    <>
                      {oauthProviders.length > 0 && (
                        <div className='flex items-center my-2.5'>
                          <div className='flex-1 h-px bg-white/10' />
                          <span className='px-3 text-[11px] text-white/30 uppercase tracking-widest'>or</span>
                          <div className='flex-1 h-px bg-white/10' />
                        </div>
                      )}
                      <button
                        onClick={() => setIsLocalMode(true)}
                        className='flex items-center w-full h-[44px] px-4 rounded-xl border border-white/10 bg-white/[0.04] hover:bg-white/[0.08] hover:border-white/25 transition-all group'
                      >
                        <span className='text-white/45 group-hover:text-white/85 transition-colors'>
                          <LockOutlined style={{ fontSize: 18 }} />
                        </span>
                        <span className='ml-3 text-[13px] font-medium text-white/70 group-hover:text-white transition-colors'>
                          Sign in with Username
                        </span>
                      </button>
                    </>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <p className='text-center mt-6 text-[11px] text-white/30 tracking-wide'>
            Powered by Gyra
          </p>
          </ConfigProvider>
        </div>
      </main>
    </div>
  );
}
