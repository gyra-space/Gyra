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
import { Alert, Button, Input, Spin } from 'antd';
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
    <div className='relative min-h-screen flex bg-[#f7f8fa] overflow-hidden'>
      {/* ─── 左侧品牌展示区 ─── */}
      <aside className='hidden lg:flex relative flex-col justify-between w-[46%] shrink-0 p-12 xl:p-16 overflow-hidden bg-[#0b0d16] text-white'>
        {/* 极光背景 */}
        <div className='aurora-stage'>
          <div className='aurora-blob aurora-blob--brand top-[-12%] left-[-8%] w-[560px] h-[560px]' />
          <div className='aurora-blob aurora-blob--cyan bottom-[-14%] right-[-6%] w-[520px] h-[520px]' />
          <div className='aurora-blob aurora-blob--violet top-[38%] left-[52%] w-[420px] h-[420px]' />
        </div>
        {/* 网格纹理 */}
        <div className='absolute inset-0 opacity-[0.05]'
          style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)', backgroundSize: '56px 56px' }} />
        {/* 光晕过滤层 */}
        <div className='absolute inset-0 bg-gradient-to-tr from-[#0b0d16]/70 via-transparent to-[#0b0d16]/40' />

        <div className='relative z-10 flex items-center gap-3 animate-rise'>
          <Image src='/gyra-logo.svg' alt='Gyra' width={40} height={40} priority className='drop-shadow-[0_0_20px_rgba(79,70,229,0.7)]' />
          <div className='flex items-baseline gap-2'>
            <span className='text-[22px] font-semibold tracking-tight'>Gyra</span>
            <span className='text-[11px] text-white/40 tracking-[0.2em] uppercase'>Flywheel</span>
          </div>
        </div>

        <div className='relative z-10 max-w-[480px] animate-rise-slow'>
          <div className='inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-white/15 bg-white/5 backdrop-blur-sm text-[12px] text-white/70 mb-7'>
            <span className='w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.9)]' />
            AI-Native Multi-Agent Platform
          </div>

          <h1 className='text-[40px] xl:text-[48px] font-semibold leading-[1.08] tracking-tight'>
            The Team-Native
            <br />
            <span className='bg-gradient-to-r from-[#00DAEF] via-[#818cf8] to-[#a78bfa] bg-clip-text text-transparent'>
              AI Flywheel
            </span>
          </h1>

          <p className='mt-6 text-[15px] leading-relaxed text-white/55 max-w-[440px]'>
            Build, run and scale intelligent agents that collaborate like a real team —
            orchestration, knowledge, tools and a compounding data flywheel in one platform.
          </p>

          {/* 特性卡片 */}
          <div className='mt-10 grid grid-cols-2 gap-3.5'>
            {FEATURES.map(f => (
              <div key={f.title}
                className='group rounded-xl border border-white/10 bg-white/[0.04] p-4 backdrop-blur-sm transition-all duration-300 hover:bg-white/[0.08] hover:border-white/20 hover:-translate-y-0.5'>
                <div className='w-9 h-9 rounded-lg flex items-center justify-center text-[#a5b4fc] bg-white/[0.06] border border-white/10 mb-3 transition-colors group-hover:bg-[#4f46e5] group-hover:text-white'>
                  {f.icon}
                </div>
                <h3 className='text-[13px] font-semibold text-white/90 mb-1.5'>{f.title}</h3>
                <p className='text-[12px] leading-relaxed text-white/45'>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* 底部：Agent 运行预览 */}
        <div className='relative z-10 flex items-center gap-4 animate-rise-slow'>
          <div className='flex-1 rounded-xl border border-white/10 bg-[#0e111b]/80 backdrop-blur-md p-4 shadow-[0_20px_60px_rgba(0,0,0,0.45)]'>
            <div className='flex items-center gap-1.5 mb-3'>
              <span className='w-2 h-2 rounded-full bg-[#ff5f57]' />
              <span className='w-2 h-2 rounded-full bg-[#febc2e]' />
              <span className='w-2 h-2 rounded-full bg-[#28c840]' />
              <span className='ml-2 text-[10px] text-white/35 tracking-widest'>AGENT CONSOLE</span>
            </div>
            <div className='space-y-2 text-[11px] font-mono'>
              <div className='flex items-center gap-2 text-white/60'>
                <span className='text-[#818cf8]'>○</span> planning → research → act
              </div>
              <div className='flex items-center gap-2 text-white/60'>
                <span className='text-[#00DAEF]'>◐</span> grounding against knowledge base
              </div>
              <div className='flex items-center gap-2 text-white/60'>
                <span className='text-[#34d399]'>●</span> calling 3 tools via MCP
              </div>
              <div className='flex items-center gap-2 text-white'>
                <span className='text-[#a78bfa]'>✔</span> task completed · flywheel updated
              </div>
            </div>
          </div>
          <div className='hidden xl:flex flex-col items-center gap-2 shrink-0'>
            <div className='w-10 h-10 rounded-full bg-gradient-to-br from-[#00DAEF] to-[#4f46e5] flex items-center justify-center shadow-[0_8px_24px_rgba(79,70,229,0.5)]'>
              <ArrowRightOutlined className='text-white text-[16px]' />
            </div>
            <span className='text-[10px] text-white/40 tracking-widest'>Powered by Gyra</span>
          </div>
        </div>
      </aside>

      {/* ─── 右侧登录区 ─── */}
      <main className='relative flex-1 flex flex-col items-center justify-center px-6 py-10 bg-[#f7f8fa]'>
        {/* 浅色极光点缀 */}
        <div className='pointer-events-none absolute inset-0 overflow-hidden'>
          <div className='absolute top-[-120px] right-[-80px] w-[420px] h-[420px] rounded-full'
            style={{ background: 'radial-gradient(circle, rgba(0,218,239,0.10) 0%, transparent 70%)' }} />
          <div className='absolute bottom-[-100px] left-[-60px] w-[380px] h-[380px] rounded-full'
            style={{ background: 'radial-gradient(circle, rgba(79,70,229,0.08) 0%, transparent 70%)' }} />
        </div>

        <div className='relative z-10 w-full max-w-[400px] animate-rise'>
          {/* 移动端 Logo */}
          <div className='lg:hidden flex justify-center mb-8'>
            <Image src='/logo_zh_latest.png' alt='Gyra' width={160} height={42} className='h-[42px] w-auto' priority />
          </div>

          {/* 登录卡片 */}
          <div className='glass-panel rounded-2xl border border-white/60 shadow-[0_1px_2px_rgba(16,24,40,0.04),0_24px_60px_rgba(16,24,40,0.10)] px-8 py-8'>
            <div className='mb-7'>
              <h2 className='text-[22px] font-semibold text-ink-900 tracking-tight'>
                Welcome back
              </h2>
              <p className='mt-1.5 text-[13px] text-ink-400'>Sign in to continue to your workspace</p>
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
                <p className='text-ink-400 text-sm leading-relaxed'>
                  Login is not configured.<br />
                  Please enable OAuth2 or access control plugin in System Settings.
                </p>
              </div>
            ) : isLocalMode ? (
              /* ─── Local login / register form ─── */
              <div>
                <div className='flex items-center justify-between mb-5'>
                  <h3 className='text-[15px] font-semibold text-ink-900 tracking-tight'>
                    {isRegister ? 'Create Account' : 'Sign In'}
                  </h3>
                  {oauthProviders.length > 0 && (
                    <button
                      onClick={() => setIsLocalMode(false)}
                      className='text-xs text-ink-400 hover:text-[#4f46e5] transition-colors'
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
                    prefix={<UserOutlined className='text-gray-300' />}
                    placeholder='Username'
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                    onKeyDown={handleKeyDown}
                    className='rounded-lg'
                    style={{ height: 44 }}
                  />
                  <Input.Password
                    size='large'
                    prefix={<LockOutlined className='text-gray-300' />}
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
                        prefix={<LockOutlined className='text-gray-300' />}
                        placeholder='Confirm Password'
                        value={confirmPassword}
                        onChange={e => setConfirmPassword(e.target.value)}
                        onKeyDown={handleKeyDown}
                        className='rounded-lg'
                        style={{ height: 44 }}
                      />
                      <Input
                        size='large'
                        prefix={<MailOutlined className='text-gray-300' />}
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
                    style={{ height: 44, background: '#4f46e5' }}
                  >
                    {isRegister ? 'Create Account' : 'Sign In'}
                  </Button>
                </div>

                <div className='mt-4 text-center'>
                  <button
                    className='text-[13px] text-ink-400 hover:text-[#4f46e5] transition-colors'
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
                      <div className='flex-1 h-px bg-gray-100' />
                      <span className='px-3 text-[11px] text-gray-300 uppercase tracking-widest'>or</span>
                      <div className='flex-1 h-px bg-gray-100' />
                    </div>
                    <div className='flex justify-center gap-3'>
                      {oauthProviders.map(p => (
                        <button
                          key={p.id}
                          onClick={() => handleOAuthLogin(p.id)}
                          className='flex items-center justify-center w-11 h-11 rounded-xl border border-gray-100 bg-white hover:bg-gray-50 hover:border-gray-200 transition-all text-gray-400 hover:text-gray-600 shadow-[0_1px_2px_rgba(16,24,40,0.04)]'
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
                <h3 className='text-[15px] font-semibold text-ink-900 mb-5 tracking-tight'>Sign In</h3>

                <div className='space-y-2.5'>
                  {oauthProviders.map(p => (
                    <button
                      key={p.id}
                      onClick={() => handleOAuthLogin(p.id)}
                      className='flex items-center w-full h-[44px] px-4 rounded-xl border border-gray-100 bg-white hover:bg-gray-50 hover:border-gray-200 transition-all group shadow-[0_1px_2px_rgba(16,24,40,0.04)]'
                    >
                      <span className='text-gray-400 group-hover:text-gray-600 transition-colors'>
                        <ProviderIcon type={p.type} />
                      </span>
                      <span className='ml-3 text-[13px] font-medium text-gray-600 group-hover:text-gray-800 transition-colors'>
                        Continue with {providerLabel(p)}
                      </span>
                    </button>
                  ))}

                  {hasLocal && (
                    <>
                      {oauthProviders.length > 0 && (
                        <div className='flex items-center my-2.5'>
                          <div className='flex-1 h-px bg-gray-100' />
                          <span className='px-3 text-[11px] text-gray-300 uppercase tracking-widest'>or</span>
                          <div className='flex-1 h-px bg-gray-100' />
                        </div>
                      )}
                      <button
                        onClick={() => setIsLocalMode(true)}
                        className='flex items-center w-full h-[44px] px-4 rounded-xl border border-gray-100 bg-white hover:bg-gray-50 hover:border-gray-200 transition-all group shadow-[0_1px_2px_rgba(16,24,40,0.04)]'
                      >
                        <span className='text-gray-400 group-hover:text-gray-600 transition-colors'>
                          <LockOutlined style={{ fontSize: 18 }} />
                        </span>
                        <span className='ml-3 text-[13px] font-medium text-gray-600 group-hover:text-gray-800 transition-colors'>
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
          <p className='text-center mt-6 text-[11px] text-gray-300 tracking-wide'>
            Powered by Gyra
          </p>
        </div>
      </main>
    </div>
  );
}
