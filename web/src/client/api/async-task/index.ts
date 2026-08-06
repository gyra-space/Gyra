import { GET } from '../index';

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

// ---- API ----

const API_PREFIX = '/api/v2/serve/multimodal';

export const listAsyncTasks = (
  params: { conv_id?: string; status?: string; limit?: number } = {},
) => {
  return GET<Record<string, any>, AsyncTask[]>(`${API_PREFIX}/media-jobs`, params as any);
};

export const getAsyncTask = (taskId: string) => {
  return GET<{}, AsyncTask>(`${API_PREFIX}/media-jobs/${taskId}`);
};