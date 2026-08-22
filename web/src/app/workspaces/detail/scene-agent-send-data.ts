import type { PlaybookCommand, SkillRef } from './agent-workspace-types';
import type { MediaParams } from '@/components/chat/input/media-params';

export interface SceneAgentSendPayload {
  text: string;
  resources?: unknown[];
  model?: string;
  playbookCommand?: PlaybookCommand;
  /** 本次对话选用的技能(随 chat_in_params 下发,sub_type='skill(gyra)') */
  skills?: SkillRef[];
  /** 多媒体生成参数（图片/视频），场景空间输入框设定，随 chat_in_params 下发，由多媒体子 Agent 消费 */
  media?: MediaParams;
  /** 本次对话的 Agent 工具权限级别(plan/auto/manual),写入 ext_info.permission_mode,
   *  接入后端 5 级权限链(reader 只读 / 写工具按级别放行或 ASK) */
  permission?: string;
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
  const { text, resources = [], model, playbookCommand, skills, media, permission } = payload;
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
  if (media && Object.keys(media).length > 0) {
    chatInParams.push({
      param_type: 'media',
      param_value: JSON.stringify(media),
      sub_type: '',
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
      // 工具权限级别:写入 extra.permission_mode,接入 Agent 5 级权限链
      // (plan=只读放行/写 ASK, auto=全放行, manual=全部 ASK)
      ...(permission ? { permission_mode: permission } : {}),
    },
  };
}