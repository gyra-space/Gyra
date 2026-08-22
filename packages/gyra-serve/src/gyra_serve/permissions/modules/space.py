"""场景空间域权限模块（scope_type=space，按空间判定）。

角色矩阵（内置三角色）：
- space.admin  : 全部 space.* 权限
- space.member : 对话/任务/看产出，资产/能力/剧本只读（"使用成员"）
- space.viewer : 全部只读（不包含发起对话/任务）
"""

from gyra_serve.permissions.protocol import PermDef, PermissionModule, SCOPE_SPACE


def _sp(key: str, name: str, desc: str = "", risk: str = "write") -> PermDef:
    return PermDef(key, name, desc, scope_type=SCOPE_SPACE, risk_level=risk)


class SpacePermModule(PermissionModule):
    name = "space"
    permissions = [
        _sp("space.workspace.view", "空间可见", "看到空间并浏览概览", risk="read"),
        _sp("space.workspace.manage", "空间管理", "改空间配置/成员/资源/释放空间", risk="dangerous"),
        _sp("space.chat.use", "空间对话", "在空间内发起对话"),
        _sp("space.task.view", "查看任务", "查看任务列表与详情", risk="read"),
        _sp("space.task.start", "发起任务", "创建并启动场景任务"),
        _sp("space.task.manage", "任务管理", "终止/关闭/删除/改派任务", risk="dangerous"),
        _sp("space.file.read", "查看产出文件", "查看/下载任务产出文件", risk="read"),
        _sp("space.asset.view", "查看资产", "查看空间资产", risk="read"),
        _sp("space.asset.manage", "资产管理", "资产增删改/发布/认证/教练", risk="dangerous"),
        _sp("space.capability.view", "查看能力", "查看空间能力装配", risk="read"),
        _sp("space.capability.manage", "能力维护", "维护空间资源/能力装配"),
        _sp("space.playbook.view", "查看剧本", "查看剧本", risk="read"),
        _sp("space.playbook.manage", "剧本维护", "剧本增删改"),
        _sp("space.playbook.run", "运行剧本", "执行/调试剧本"),
        _sp("space.scene.manage", "场景管理", "场景模式/场景切换/注入", risk="dangerous"),
    ]


# ===== 内置空间角色权限矩阵（seed 用） =====
SPACE_ALL = [p.key for p in SpacePermModule.permissions]

SPACE_MEMBER_KEYS = [
    "space.workspace.view",
    "space.chat.use",
    "space.task.view",
    "space.task.start",
    "space.file.read",
    "space.asset.view",
    "space.capability.view",
    "space.playbook.view",
]

SPACE_VIEWER_KEYS = [
    "space.workspace.view",
    "space.task.view",
    "space.file.read",
    "space.asset.view",
    "space.capability.view",
    "space.playbook.view",
]
