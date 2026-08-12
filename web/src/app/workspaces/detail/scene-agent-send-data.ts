import type { PlaybookCommand, SkillRef } from './agent-workspace-types';

export interface SceneAgentSendPayload {
  text: string;
  resources?: unknown[];
  model?: string;
  playbookCommand?: PlaybookCommand;
  /** 本次对话选用的技能(随 chat_in_params 下发,sub_type='skill(gyra)') */
  skills?: SkillRef[];
}

export interface SendDataOptions {
  workspaceId?: number | string;
  taskId?: number | string;
  focusArtifactId?: number | string;
}

export interface ChatInParam {
  param_type: string;
  param_value: string;
  sub_type?: string;
}

export interface SceneAgentSendData {
  conv_uid: string;
  user_input: string | { role: 'user'; content: unknown[] };
  workspace_id?: number | string;
  task_id?: number | string;
  model_name?: string;
  chat_in_params?: ChatInParam[];
  team_mode: string;
  app_config_code: string;
  agent_version: string;
  ext_info: {
    vis_render: 'scene_agent_workspace';
    workspace_id?: number;
    task_id?: number;
    /** 显式命中的剧本:后端回合前路由据此预建会话内任务(in_session 同步执行) */
    playbook_id?: number;
  };
}

/**
 * 纯函数:构造 scene-agent send 载荷。对齐 chat-session.tsx:306-320 的多模态/参数构造。
 * 从 use-scene-agent-chat.ts 的 send 中抽出,便于单测(node env,无 DOM/依赖链)。
 */
export function buildSceneAgentSendData(
  payload: SceneAgentSendPayload,
  options: SendDataOptions,
  convUid: string,
): SceneAgentSendData {
  const { text, resources = [], model, playbookCommand, skills } = payload;
  const { workspaceId, taskId, focusArtifactId } = options;
  const trimmed = text.trim();

  const userInput =
    resources.length > 0
      ? {
          role: 'user' as const,
          content: [...resources, ...(trimmed ? [{ type: 'text', text: trimmed }] : [])],
        }
      : trimmed;

  const chatInParams: ChatInParam[] = [];
  if (resources.length > 0) {
    chatInParams.push({ param_type: 'resource', param_value: JSON.stringify(resources), sub_type: 'common_file' });
  }
  if (model) {
    chatInParams.push({ param_type: 'model', param_value: model });
  }
  if (playbookCommand) {
    chatInParams.push({
      param_type: 'playbook_command',
      sub_type: 'playbook',
      param_value: JSON.stringify(playbookCommand),
    });
  }
  if (skills && skills.length > 0) {
    skills.forEach((skill) => {
      chatInParams.push({
        param_type: 'resource',
        param_value: JSON.stringify(skill),
        sub_type: 'skill(gyra)',
      });
    });
  }

  return {
    conv_uid: convUid,
    user_input: userInput,
    workspace_id: workspaceId,
    task_id: taskId,
    ...(model ? { model_name: model } : {}),
    ...(chatInParams.length ? { chat_in_params: chatInParams } : {}),
    team_mode: '',
    app_config_code: '',
    agent_version: 'v1',
    ext_info: {
      vis_render: 'scene_agent_workspace',
      ...(workspaceId !== undefined ? { workspace_id: Number(workspaceId) } : {}),
      ...(taskId !== undefined ? { task_id: Number(taskId) } : {}),
      // 显式命中剧本:透传 playbook_id 给后端回合前路由,预建会话内任务
      // (execution_mode=in_session)并在当前对话同步执行。已绑定任务的
      // workbench 对话不受影响(路由对 task_id 已有时跳过)。
      ...(playbookCommand ? { playbook_id: Number(playbookCommand.playbook_id) } : {}),
      ...(focusArtifactId !== undefined ? { focus_artifact_id: Number(focusArtifactId) } : {}),
    },
  };
}