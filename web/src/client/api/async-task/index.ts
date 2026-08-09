import { GET, POST } from '../index';

// ---- Types ----

export interface AsyncTaskArtifact {
  [key: string]: any;
}

export interface AsyncTask {
  task_id: string;
  conv_id: string;
  /** video / image / subagent ... */
  kind: string;
  /** model name (media) or agent name (subagent) */
  model: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'timeout' | 'cancelled';
  error?: string;
  result_preview?: string;
  /** Deliverable artifact metadata (JSON) — AFS preview/download links */
  artifact?: AsyncTaskArtifact;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
}

export interface AsyncTaskListResponse {
  items: AsyncTask[];
  total: number;
}

// ---- API ----

const API_PREFIX = '/api/v2/serve/multimodal';

export const listAsyncTasks = (
  params: { conv_id?: string; status?: string; kind?: string; limit?: number; offset?: number } = {},
) => {
  return GET<Record<string, any>, AsyncTaskListResponse>(`${API_PREFIX}/media-jobs`, params as any);
};

export const getAsyncTask = (taskId: string) => {
  return GET<{}, AsyncTask>(`${API_PREFIX}/media-jobs/${taskId}`);
};

/**
 * 手动召回媒体生成结果（不重新提交、不重复扣费）。
 * 按任务记录里的 provider_task_id 对 provider 侧已有任务重新轮询 + 下载，
 * 交付到原会话工作区并回写任务记录。
 */
export const recallAsyncTask = (taskId: string, timeout = 600) => {
  return POST<{}, { task_id: string; message: string }>(
    `${API_PREFIX}/media-jobs/${taskId}/recall?timeout=${timeout}`,
  );
};