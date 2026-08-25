import { getUserId } from '@/utils';
import { HEADER_USER_ID_KEY, STORAGE_USERINFO_KEY, STORAGE_USERINFO_VALID_TIME_KEY } from '@/utils/constants/index';
import { getMessage } from '@/utils/antd-instance';
import { getApiErrorMessage } from '@/utils/apiError';
import axios, { AxiosError, AxiosRequestConfig, AxiosResponse } from 'axios';

export type ResponseType<T = any> = {
  data: T;
  err_code: string | null;
  err_msg: string | null;
  success: boolean;
};

export type ApiResponse<T = any, D = any> = AxiosResponse<ResponseType<T>, D>;

export type SuccessTuple<T = any, D = any> = [null, T, ResponseType<T>, ApiResponse<T, D>];

export type FailedTuple<T = any, D = any> = [Error | AxiosError<T, D>, null, null, null];

export const ins = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL ?? '/',
  withCredentials: true, // Send cookies for session-based auth
});

const LONG_TIME_API: string[] = [
  '/db/add',
  '/db/test/connect',
  '/db/summary',
  '/params/file/load',
  '/chat/prepare',
  '/model/start',
  '/model/stop',
  '/editor/sql/run',
  '/sql/editor/submit',
  '/editor/chart/run',
  '/chart/editor/submit',
  '/document/upload',
  '/document/sync',
  '/agent/install',
  '/agent/uninstall',
  '/personal/agent/upload',
];

// Endpoints whose 401 should NOT trigger a redirect (the page handles them inline).
const AUTH_ENDPOINTS_BYPASS_REDIRECT = [
  '/api/v1/auth/me',
  '/api/v1/auth/local/login',
  '/api/v1/auth/local/register',
  '/api/v1/auth/oauth/status',
];

ins.interceptors.request.use(request => {
  const isLongTimeApi = LONG_TIME_API.some(item => request.url && request.url.indexOf(item) >= 0);
  if (!request.timeout) {
    request.timeout = isLongTimeApi ? 60000 : 100000;
  }
  request.headers.set(HEADER_USER_ID_KEY, getUserId());
  return request;
});

// 全局错误提示去重：同一错误消息在静默窗口内只提示一次，避免轮询/定时刷新
// (如打开会话后的状态轮询、列表轮询)在后端异常时每几秒刷屏骚扰用户。
let lastGlobalErrorMsg = '';
let lastGlobalErrorTime = 0;
const GLOBAL_ERROR_DEDUP_MS = 3000;

/**
 * 统一的"后端/网络错误"兜底提示。所有经 `ins` 发出的请求在拦截器层兜底弹 toast，
 * 确保页面任何操作(打开会话、拉列表、提交表单等)在后端报错时都有可见反馈，
 * 而不是静默无响应。401 由上面的重定向逻辑处理，403 单独提示，其余落这里。
 */
const notifyGlobalError = (error: AxiosError): void => {
  if (typeof window === 'undefined') return;
  const msg = getApiErrorMessage(error) || '请求失败，请稍后重试';
  const now = Date.now();
  if (msg === lastGlobalErrorMsg && now - lastGlobalErrorTime < GLOBAL_ERROR_DEDUP_MS) {
    return;
  }
  lastGlobalErrorMsg = msg;
  lastGlobalErrorTime = now;
  getMessage()?.error(msg);
};

ins.interceptors.response.use(
  response => response,
  (error: AxiosError) => {
    if (typeof window !== 'undefined' && error.response?.status === 401) {
      const url = error.config?.url || '';
      const path = window.location.pathname;
      const onAuthPage = path.startsWith('/login') || path.startsWith('/auth/callback');
      const bypass = AUTH_ENDPOINTS_BYPASS_REDIRECT.some(p => url.indexOf(p) >= 0);
      if (!onAuthPage && !bypass) {
        try {
          localStorage.removeItem(STORAGE_USERINFO_KEY);
          localStorage.removeItem(STORAGE_USERINFO_VALID_TIME_KEY);
        } catch {
          /* ignore */
        }
        const next = encodeURIComponent(path + window.location.search);
        window.location.href = `/login?next=${next}`;
      }
    } else if (typeof window !== 'undefined' && error.response?.status === 403) {
      getMessage()?.error('没有访问该资源的权限 (403)');
    } else {
      // 兜底提示：覆盖 4xx/5xx/超时/断网等所有未单独处理的错误
      notifyGlobalError(error);
    }
    return Promise.reject(error);
  },
);

export const GET = <Params = any, Response = any, D = any>(
  url: string,
  params?: Params,
  config?: AxiosRequestConfig<D>,
) => {
  return ins.get<Params, ApiResponse<Response>>(url, { params, ...config });
};

export const POST = <Data = any, Response = any, D = any>(url: string, data?: Data, config?: AxiosRequestConfig<D>) => {
  return ins.post<Data, ApiResponse<Response>>(url, data, config);
};

export const PATCH = <Data = any, Response = any, D = any>(
  url: string,
  data?: Data,
  config?: AxiosRequestConfig<D>,
) => {
  return ins.patch<Data, ApiResponse<Response>>(url, data, config);
};

export const PUT = <Data = any, Response = any, D = any>(url: string, data?: Data, config?: AxiosRequestConfig<D>) => {
  return ins.put<Data, ApiResponse<Response>>(url, data, config);
};

export const DELETE = <Params = any, Response = any, D = any>(
  url: string,
  params?: Params,
  config?: AxiosRequestConfig<D>,
) => {
  return ins.delete<Params, ApiResponse<Response>>(url, { params, ...config });
};

export * from './app';
export * from './chat';
export * from './evaluate';
export * from './flow';
// TODO: rewire to new knowledge-vault page — `export * from './knowledge';` removed.
export * from './prompt';
export * from './request';
export * from './tools';
export * from './skill';
export * from './cron';
export * from './channel';
export * from './monitoring';
export * from './usage';
// Scenario Workspace MVP modules
export * from './workspace';
export * from './task';
export * from './playbook';
export * from './artifact';
export * from './workspace-asset';
export * from './delivery';
export * from './intervention';
export * from './trigger';
export * from './async-task';
