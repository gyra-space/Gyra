"""全局域内置权限模块（对齐存量 RBAC 的 8 类资源与动作梯度）。

动作梯度沿用现有语义（如 agent: read -> chat -> write -> admin），
与存量 role_permission 数据完全兼容。
"""

from gyra_serve.permissions.protocol import PermDef, PermissionModule


class SystemPermModule(PermissionModule):
    name = "system"
    permissions = [
        PermDef("system.read", "系统配置查看", "查看用户/角色/分组等系统配置",
                risk_level="read"),
        PermDef("system.write", "系统配置编辑", "编辑用户/角色/分组等系统配置"),
        PermDef("system.admin", "系统管理", "系统/用户/角色等全局管理",
                risk_level="dangerous"),
    ]


class AgentPermModule(PermissionModule):
    name = "agent"
    permissions = [
        PermDef("agent.read", "Agent 查看", "查看智能体列表与详情",
                risk_level="read", grantable=True),
        PermDef("agent.chat", "Agent 使用", "与智能体对话/运行",
                grantable=True),
        PermDef("agent.write", "Agent 编辑", "新增/编辑智能体配置"),
        PermDef("agent.admin", "Agent 管理", "完全管理智能体（含发布/删除）",
                risk_level="dangerous"),
    ]


class ToolPermModule(PermissionModule):
    name = "tool"
    permissions = [
        PermDef("tool.read", "工具查看", "查看工具列表与详情",
                risk_level="read"),
        PermDef("tool.execute", "工具执行", "执行工具",
                grantable=True),
        PermDef("tool.manage", "工具管理", "维护工具配置"),
        PermDef("tool.admin", "工具完全管理", "工具全部管理权限",
                risk_level="dangerous"),
    ]


class KnowledgePermModule(PermissionModule):
    name = "knowledge"
    permissions = [
        PermDef("knowledge.read", "知识库查看", "查看知识库",
                risk_level="read", grantable=True),
        PermDef("knowledge.query", "知识库检索", "检索知识库内容",
                grantable=True),
        PermDef("knowledge.write", "知识库维护", "管理知识库内容"),
        PermDef("knowledge.admin", "知识库完全管理", "知识库全部管理权限",
                risk_level="dangerous"),
    ]


class ModelPermModule(PermissionModule):
    name = "model"
    permissions = [
        PermDef("model.read", "模型查看", "查看模型/Provider 配置",
                risk_level="read"),
        PermDef("model.chat", "模型使用", "使用模型对话",
                grantable=True),
        PermDef("model.manage", "模型管理", "维护模型/Provider 配置"),
        PermDef("model.admin", "模型完全管理", "模型全部管理权限",
                risk_level="dangerous"),
    ]


class CronPermModule(PermissionModule):
    name = "cron"
    permissions = [
        PermDef("cron.read", "定时任务查看", "查看定时任务",
                risk_level="read"),
        PermDef("cron.manage", "定时任务管理", "管理定时任务"),
    ]


class ChannelPermModule(PermissionModule):
    name = "channel"
    permissions = [
        PermDef("channel.read", "渠道查看", "查看渠道配置",
                risk_level="read"),
        PermDef("channel.manage", "渠道管理", "管理渠道配置"),
    ]


class SkillPermModule(PermissionModule):
    name = "skill"
    permissions = [
        PermDef("skill.read", "技能查看", "查看技能资源列表与详情",
                risk_level="read"),
        PermDef("skill.publish", "技能发布", "把会话内创建的技能发布到技能资源库",
                risk_level="write"),
    ]


class DatabasePermModule(PermissionModule):
    name = "database"
    permissions = [
        PermDef("database.read", "数据库查看", "查看数据库连接配置",
                risk_level="read", grantable=True),
        PermDef("database.manage", "数据库管理", "管理数据库连接（含数据查询）",
                grantable=True),
        PermDef("database.admin", "数据库完全管理", "数据库全部权限（覆盖所有表读写）",
                risk_level="dangerous"),
    ]


class EcpPermModule(PermissionModule):
    name = "ecp"
    permissions = [
        PermDef("ecp.read", "ECP 查看", "查看语义资产/数据契约控制台",
                risk_level="read", grantable=True),
        PermDef("ecp.manage", "ECP 管理", "提案确认/驳回、语义对象维护与治理操作",
                risk_level="write"),
    ]
