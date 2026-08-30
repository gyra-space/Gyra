'use client';

/**
 * 场景空间三合一 trigger 菜单:`/` 能力编排、`@` 身份切换、`#` 对象引用。
 *
 * 对外只暴露一个组件和一个 ref —— 调用方(输入框)不必关心当前激活的是哪个
 * trigger,统一把 keydown 转交给 handleKey 即可。内部按 trigger.char 构建
 * 对应分组,再委托给通用 TriggerMenu 渲染,因此三个入口的交互与视觉天然一致。
 */

import { forwardRef, useMemo } from 'react';
import {
  ApiOutlined,
  AppstoreOutlined,
  ClearOutlined,
  CompressOutlined,
  DatabaseOutlined,
  FileDoneOutlined,
  FileOutlined,
  FileTextOutlined,
  RobotOutlined,
  RocketOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import classNames from 'classnames';
import { TriggerMenu } from './trigger-menu';
import type { TriggerMenuGroup, TriggerMenuItem } from './trigger-menu';
import type {
  PlusMenuMcpRef,
  PlusMenuPlaybookRef,
  PlusMenuSkillRef,
} from './plus-menu';
import type { SubAgentRef, ArtifactRef, AssetRef, SessionCommandItem } from './trigger-types';
import type { TriggerState } from './trigger-detect';

export type { SubAgentRef, ArtifactRef, AssetRef };

type SceneItemData =
  | { kind: 'addFile' }
  | { kind: 'playbook'; ref: PlusMenuPlaybookRef }
  | { kind: 'skill'; ref: PlusMenuSkillRef }
  | { kind: 'mcp'; ref: PlusMenuMcpRef }
  | { kind: "command"; ref: SessionCommandItem }
  | { kind: 'subAgent'; ref: SubAgentRef }
  | { kind: 'artifact'; ref: ArtifactRef }
  | { kind: 'asset'; ref: AssetRef };

/** 选中结果:trigger 字段标明来源,便于调用方分流处理 */
export type SceneTriggerSelection =
  | { trigger: '/'; type: 'addFile' }
  | { trigger: '/'; type: 'playbook'; playbook: PlusMenuPlaybookRef }
  | { trigger: '/'; type: 'skill'; skill: PlusMenuSkillRef }
  | { trigger: '/'; type: 'mcp'; mcp: PlusMenuMcpRef }
  | { trigger: "/"; type: "command"; command: SessionCommandItem }
  | { trigger: '@'; type: 'subAgent'; subAgent: SubAgentRef }
  | { trigger: '#'; type: 'artifact'; artifact: ArtifactRef }
  | { trigger: '#'; type: 'asset'; asset: AssetRef };

export interface SceneTriggerMenuProps {
  /** 当前 trigger 状态;null 表示未激活(菜单关闭) */
  trigger: TriggerState | null;
  // ---- `/` 能力编排 ----
  playbooks?: PlusMenuPlaybookRef[];
  skills?: PlusMenuSkillRef[];
  mcps?: PlusMenuMcpRef[];
  mcpsLoading?: boolean;
  commands?: SessionCommandItem[];
  onAddFile?: () => void;
  // ---- `@` 身份切换 ----
  subAgents?: SubAgentRef[];
  subAgentsLoading?: boolean;
  // ---- `#` 对象引用 ----
  artifacts?: ArtifactRef[];
  artifactsLoading?: boolean;
  assets?: AssetRef[];
  assetsLoading?: boolean;
  onSelect: (sel: SceneTriggerSelection) => void;
  /** 受控关闭 */
  onClose: () => void;
  children: React.ReactNode;
}

export interface SceneTriggerMenuHandle {
  handleKey: (e: React.KeyboardEvent) => boolean;
}

const mcpKey = (m: PlusMenuMcpRef) => String(m.id || m.uuid || m.name);

const ICON_BG = {
  playbook: 'bg-gradient-to-br from-indigo-500 to-blue-600',
  skill: 'bg-gradient-to-br from-violet-500 to-indigo-600',
  mcp: 'bg-gradient-to-br from-emerald-500 to-teal-600',
  subAgent: 'bg-gradient-to-br from-purple-500 to-fuchsia-600',
  artifact: 'bg-gradient-to-br from-amber-500 to-orange-600',
  asset: 'bg-gradient-to-br from-sky-500 to-cyan-600',
};

function IconBox({ icon, fallback, gradient }: { icon?: string; fallback: React.ReactNode; gradient: string }) {
  return (
    <div className={classNames('h-8 w-8 rounded-lg flex items-center justify-center flex-shrink-0 text-white text-xs font-semibold overflow-hidden', gradient)}>
      {icon ? <img src={icon} alt="" className="h-full w-full object-cover" /> : fallback}
    </div>
  );
}

const COMMAND_ACTION_ICON: Record<string, React.ReactNode> = {
  compact: <CompressOutlined className="text-sm" />,
  clear: <ClearOutlined className="text-sm" />,
  plan: <ThunderboltOutlined className="text-sm" />,
  custom: <ThunderboltOutlined className="text-sm" />,
};

const COMMAND_ACTION_BG: Record<string, string> = {
  compact: 'bg-gradient-to-br from-slate-500 to-gray-600',
  clear: 'bg-gradient-to-br from-orange-500 to-red-500',
  plan: 'bg-gradient-to-br from-cyan-500 to-blue-600',
  custom: 'bg-gradient-to-br from-cyan-500 to-blue-600',
};

export const SceneTriggerMenu = forwardRef<SceneTriggerMenuHandle, SceneTriggerMenuProps>(
  function SceneTriggerMenu(
    {
      trigger,
      playbooks,
      skills,
      mcps,
      mcpsLoading,
      commands,
      onAddFile,
      subAgents,
      subAgentsLoading,
      artifacts,
      artifactsLoading,
      assets,
      assetsLoading,
      onSelect,
      onClose,
      children,
    },
    ref,
  ) {
    const char = trigger?.char ?? '/';
    const query = trigger?.query ?? '';

    const { groups, placeholder, emptyText } = useMemo(() => {
      if (!trigger) {
        return { groups: [] as TriggerMenuGroup<SceneItemData>[], placeholder: '', emptyText: '无匹配项' };
      }

      if (trigger.char === '/') {
        const out: TriggerMenuGroup<SceneItemData>[] = [];
        if (onAddFile) {
          out.push({
            key: 'addFile',
            label: '文件',
            items: [
              {
                key: 'addFile',
                icon: <FileOutlined className="text-base text-gray-500 dark:text-gray-400" />,
                title: '添加文件',
                description: '上传本地文件作为上下文',
                keywords: ['file', 'upload', '文件'],
                data: { kind: 'addFile' },
              },
            ],
          });
        }
        out.push({
          key: 'playbook',
          label: '剧本',
          items: (playbooks ?? []).map<TriggerMenuItem<SceneItemData>>((pb) => ({
            key: `playbook:${pb.playbook_id}`,
            icon: <IconBox gradient={ICON_BG.playbook} fallback={<RocketOutlined className="text-sm" />} />,
            title: pb.playbook_name,
            description: '以该剧本发起任务',
            data: { kind: 'playbook', ref: pb },
          })),
        });
        out.push({
          key: 'skill',
          label: '技能',
          items: (skills ?? []).map<TriggerMenuItem<SceneItemData>>((s) => ({
            key: `skill:${s.skill_code}`,
            icon: <IconBox icon={s.icon} gradient={ICON_BG.skill} fallback={<AppstoreOutlined className="text-sm" />} />,
            title: s.name,
            description: s.description,
            data: { kind: 'skill', ref: s },
          })),
        });
        out.push({
          key: 'mcp',
          label: 'MCP',
          loading: mcpsLoading,
          items: (mcps ?? []).map<TriggerMenuItem<SceneItemData>>((m) => ({
            key: `mcp:${mcpKey(m)}`,
            icon: <IconBox icon={m.icon} gradient={ICON_BG.mcp} fallback={<ApiOutlined className="text-sm" />} />,
            title: m.name,
            description: m.description,
            data: { kind: 'mcp', ref: m },
          })),
        });
        out.push({
          key: 'command',
          label: '命令',
          items: (commands ?? []).map<TriggerMenuItem<SceneItemData>>((c) => ({
            key: `command:${c.command}`,
            icon: (
              <div className={classNames('h-8 w-8 rounded-lg flex items-center justify-center flex-shrink-0 text-white overflow-hidden', COMMAND_ACTION_BG[c.action ?? ''] ?? COMMAND_ACTION_BG.plan)}>
                {COMMAND_ACTION_ICON[c.action ?? ''] ?? <ThunderboltOutlined className="text-sm" />}
              </div>
            ),
            title: `/${c.command}`,
            description: c.description || c.name,
            mono: true,
            data: { kind: 'command', ref: c },
          })),
        });
        return { groups: out, placeholder: '选择剧本/技能/MCP/命令或输入关键词', emptyText: '无匹配项' };
      }

      if (trigger.char === '@') {
        return {
          groups: [
            {
              key: 'subAgent',
              label: '子 Agent',
              loading: subAgentsLoading,
              items: (subAgents ?? []).map<TriggerMenuItem<SceneItemData>>((a) => ({
                key: `subAgent:${a.physical_ref}`,
                icon: <IconBox gradient={ICON_BG.subAgent} fallback={<RobotOutlined className="text-sm" />} />,
                title: a.name,
                description: a.description || '接管本会话,直接与该 Agent 对话',
                data: { kind: 'subAgent', ref: a },
              })),
            },
          ],
          placeholder: '选择要接管的子 Agent',
          emptyText: '当前空间暂无可用子 Agent',
        };
      }

      // '#'
      return {
        groups: [
          {
            key: 'artifact',
            label: '交付产物',
            loading: artifactsLoading,
            items: (artifacts ?? []).map<TriggerMenuItem<SceneItemData>>((a) => ({
              key: `artifact:${a.artifact_id}`,
              icon: <IconBox gradient={ICON_BG.artifact} fallback={<FileDoneOutlined className="text-sm" />} />,
              title: a.title,
              description: a.content_ref,
              data: { kind: 'artifact', ref: a },
            })),
          },
          {
            key: 'asset',
            label: '空间资产',
            loading: assetsLoading,
            items: (assets ?? []).map<TriggerMenuItem<SceneItemData>>((a) => ({
              key: `asset:${a.asset_id}`,
              icon: <IconBox gradient={ICON_BG.asset} fallback={<DatabaseOutlined className="text-sm" />} />,
              title: a.name,
              description: a.description || (a.maturity ? `成熟度 ${a.maturity}` : undefined),
              data: { kind: 'asset', ref: a },
            })),
          },
        ],
        placeholder: '检索文件/交付资源',
        emptyText: '暂无可引用的资源',
      };
    }, [
      trigger,
      playbooks,
      skills,
      mcps,
      mcpsLoading,
      commands,
      onAddFile,
      subAgents,
      subAgentsLoading,
      artifacts,
      artifactsLoading,
      assets,
      assetsLoading,
    ]);

    const handleSelect = (item: TriggerMenuItem<SceneItemData>) => {
      const d = item.data;
      if (!d) return;
      switch (d.kind) {
        case 'addFile':
          onAddFile?.();
          break;
        case 'playbook':
          onSelect({ trigger: '/', type: 'playbook', playbook: d.ref });
          break;
        case 'skill':
          onSelect({ trigger: '/', type: 'skill', skill: d.ref });
          break;
        case 'mcp':
          onSelect({ trigger: '/', type: 'mcp', mcp: d.ref });
          break;
        case 'command':
          onSelect({ trigger: '/', type: 'command', command: d.ref });
          break;
        case 'subAgent':
          onSelect({ trigger: '@', type: 'subAgent', subAgent: d.ref });
          break;
        case 'artifact':
          onSelect({ trigger: '#', type: 'artifact', artifact: d.ref });
          break;
        case 'asset':
          onSelect({ trigger: '#', type: 'asset', asset: d.ref });
          break;
      }
    };

    return (
      <TriggerMenu
        ref={ref}
        open={!!trigger}
        query={query}
        triggerChar={char}
        groups={groups}
        placeholder={placeholder}
        emptyText={emptyText}
        onSelect={handleSelect}
        onClose={onClose}
      >
        {children}
      </TriggerMenu>
    );
  },
);
