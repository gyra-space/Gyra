"""SkillCapability —— 技能自管理资源能力(RFC-006 Stage 7/8)。

技能纯声明:declare 渲染 <available_skills> 列表进 SYSTEM
(与 identity/workflow/catalog_consumer 模板统一使用同一标签,
避免模型找不到技能目录而跳过技能加载)。

prepare 自管 skill_code/path 解析(facade 时序已改 prepare 先于 declare,RFC-006 Stage 8):
若 skills 已带 path(config 完整)则免 I/O;否则按 skill_name 查 Skill service
补 skill_code + 解析 sandbox path(get_skill_directory + FS 检查)。无 _SYSTEM_APP/
service 不可用时降级不崩(declare 用现有 path/空)。

execute 不收编:read_skill 工具暂走 Route A builtin(沙箱/local fs 读,
SandboxToolBase);skill_list/skill_exec 已废弃删除。本轮 SkillCapability 自管
prepare/declare,execute 保持 Route A。

"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from gyra.core.interface.resource.bundle import (
    CacheScope,
    Contribution,
    Lifetime,
    Slot,
)
from gyra.core.interface.resource.capability import Capability
from gyra.core.interface.resource.executor import (
    ExecutorCall,
    ExecutorStatus,
    ReleaseReason,
)

logger = logging.getLogger(__name__)

# 模板对齐 identity/workflow/catalog_consumer(标签统一为 available_skills)
_SKILL_PROMPT_TEMPLATE = """<available_skills>
可用技能目录。仅当技能与当前任务相关时，用 `skill` 工具加载其完整指令后按指令执行（如 skill(name="data-analysis")）。
{% for item in skills %}\
<{{loop.index }}>\
<name>{{item.name }}</name>
<description>{{item.description}}</description>
{% if item.owner %}\
<owner>{{item.owner}}</owner>
{% endif %}\
{% if item.branch %}\
<branch>{{item.branch}}</branch>
{% endif %}\
</{{loop.index }}>
{% endfor %}\
</available_skills>"""


def _render_skills(skills: List[dict]) -> str:
    """渲染技能列表为 <available_skills> 文本(对齐 identity/workflow 模板)。"""
    from gyra.util.template_utils import render

    return render(_SKILL_PROMPT_TEMPLATE, {"skills": skills})


class SkillCapability(Capability):
    """技能自管理能力:declare <available_skills> 列表进 SYSTEM。

    capability_id="skill";executor_id="skill"。
    """

    capability_id = "skill"

    def __init__(self, skills: Optional[List[dict]] = None, inject_system_catalog: bool = True):
        self._skills = skills
        self._legacy: Any = None
        self._inject_system_catalog = inject_system_catalog
        self._status = ExecutorStatus.UNINITIALIZED

    @classmethod
    def from_config(cls, value: dict, system_app: Any = None) -> "SkillCapability":
        """从 config dict 构造(若 config 已带 name/description/path 则纯配置态)。

        Phase D:补齐 path/parent_folder/allowed_tools/branch/skill_code/debug_info,
        使 skill 工具元数据(available_skills)可完全从本能力派生,不再依赖 v1
        AgentSkillResource 实例。
        """
        value = value or {}
        inject_system_catalog = bool(value.get("inject_system_catalog", True))
        skills = None
        if value.get("skill_name") or value.get("name"):
            skills = [
                {
                    "name": value.get("skill_name") or value.get("name") or "",
                    "description": value.get("skill_description")
                    or value.get("description")
                    or "",
                    "path": value.get("skill_path") or value.get("path") or "",
                    "owner": value.get("skill_author") or value.get("owner") or "",
                    "branch": value.get("skill_branch") or value.get("branch") or "master",
                    "skill_code": value.get("skill_code") or "",
                    "parent_folder": value.get("parent_folder") or "",
                    "allowed_tools": value.get("allowed_tools"),
                    "debug_info": value.get("debug_info"),
                }
            ]
        return cls(skills=skills, inject_system_catalog=inject_system_catalog)

    @property
    def executor_id(self) -> str:
        return "skill"

    # ----------------------------- 输入投影(declare 纯) ------------------ #
    def declare(self, config: Any = None) -> List[Contribution]:
        # V2 用 SkillRegistry/SkillCatalogConsumer 统一治理 skill 事实源；
        #   此时跳过 <available_skills> SYSTEM 注入，避免目录重复（DSH tool-skill）。
        if not self._inject_system_catalog:
            return []
        skills = self._resolve_skills()
        if not skills:
            return []
        try:
            text = _render_skills(skills)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[skill-capability] render skills failed: {e}")
            return []
        return [
            Contribution(
                capability_id=self.capability_id,
                slot=Slot.SYSTEM,
                content=text,
                lifetime=Lifetime.CONFIG_STATIC,
                cache_scope=CacheScope.USER,
                order=20,
            )
        ]

    def _resolve_skills(self) -> List[dict]:
        if self._skills is not None:
            return self._skills
        if self._legacy is None:
            return []
        mode, branch = "release", "master"
        debug_info = getattr(self._legacy, "debug_info", None)
        if debug_info and isinstance(debug_info, dict) and debug_info.get("is_debug"):
            mode, branch = "debug", debug_info.get("branch", "master")
        meta = None
        try:
            meta = self._legacy.skill_meta(mode)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[skill-capability] skill_meta failed: {e}")
            return []
        if not meta:
            return []
        skill_info = getattr(self._legacy, "_skill", None)
        parent_folder = getattr(skill_info, "parent_folder", None) if skill_info else None
        return [
            {
                "name": meta.name,
                "description": meta.description,
                "path": parent_folder or getattr(meta, "path", None),
                "owner": getattr(meta, "owner", None),
                "branch": branch,
            }
        ]

    def requires(self, config: Any = None) -> List[str]:
        return []

    def merge(self, other: Any) -> bool:
        """后续 skill 资源实例并入本实例:多个技能共享一份 <available_skills> 目录。

        工作空间常同时挂载多个技能,build_pack 为每个 skill 资源各产一个
        SkillCapability;若各自 declare,system prompt 会出现 N 份重复的目录
        块(含 N 遍加载指令)。在此吸收 other 的技能列表(按 name 去重),
        declare 时渲染单一目录块。
        """
        if not isinstance(other, SkillCapability):
            return False
        if other._skills:
            if self._skills is None:
                self._skills = []
            existing_names = {
                s.get("name") for s in self._skills if isinstance(s, dict)
            }
            for s in other._skills:
                name = s.get("name") if isinstance(s, dict) else None
                if name and name in existing_names:
                    continue
                self._skills.append(s)
                if name:
                    existing_names.add(name)
        self._inject_system_catalog = (
            self._inject_system_catalog or other._inject_system_catalog
        )
        return True

    # ----------------------------- 生命周期(无 I/O) ----------------------- #
    async def prepare(self) -> None:
        """补 skill_code/path(若 config 已带 path 则免 I/O;否则查 Skill service)。

        facets 时序已改 prepare 先于 declare(RFC-006 Stage 8)。config 多数已带
        skill_code/path(gyra_skill params 完整),仅边角(只给 skill_name)触发查码。
        path 解析:查码后用 service.get_skill_directory 获取 sandbox path。
        """
        if not self._skills:
            self._status = ExecutorStatus.READY
            return
        # 已带 path → 免 I/O
        if all(sk.get("path") for sk in self._skills):
            self._status = ExecutorStatus.READY
            return
        try:
            import asyncio
            import os

            from gyra_serve.skill.service.service import (
                Service,
                SKILL_SERVICE_COMPONENT_NAME,
            )
            from gyra_serve.skill.api.schemas import SkillRequest
            from gyra.agent.resource.manage import _SYSTEM_APP

            if not _SYSTEM_APP:
                self._status = ExecutorStatus.READY
                return
            service = _SYSTEM_APP.get_component(
                SKILL_SERVICE_COMPONENT_NAME, Service, default=None
            )
            if not service:
                self._status = ExecutorStatus.READY
                return

            for sk in self._skills:
                if sk.get("path"):
                    continue
                skill_name = sk.get("name") or ""
                # 查 skill_code(config 已带则直接用;否则精确名 + 前缀回退)
                skill_code = sk.get("skill_code") or await asyncio.to_thread(
                    self._lookup_skill_code, service, skill_name
                )
                if not skill_code:
                    continue
                sk["skill_code"] = skill_code
                # 解析 sandbox path
                skill_dir = await asyncio.to_thread(
                    self._get_skill_directory, service, skill_code
                )
                if skill_dir:
                    sk["path"] = skill_dir
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[skill-capability] prepare resolve code/path failed: {e}")
        self._status = ExecutorStatus.READY

    @staticmethod
    def _lookup_skill_code(service, skill_name: str):
        """复刻 gyra_skill._lookup_skill_code_by_name(精确名 + 前缀回退)。"""
        try:
            skills = service.get_list(SkillRequest(name=skill_name))
            if skills:
                return skills[0].skill_code
            for skill in service.get_list(SkillRequest()):
                if skill.name == skill_name or skill.skill_code.startswith(f"{skill_name}-"):
                    return skill.skill_code
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[skill-capability] lookup skill_code for '{skill_name}': {e}")
        return None

    @staticmethod
    def _get_skill_directory(service, skill_code: str):
        """复刻 gyra_skill._get_sandbox_path(service.get_skill_directory + FS 检查)。"""
        try:
            skill_dir = service.get_skill_directory(skill_code)
            import os

            if skill_dir and os.path.exists(skill_dir):
                return skill_dir
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[skill-capability] get_skill_directory for '{skill_code}': {e}")
        return None

    async def execute(self, call: ExecutorCall) -> Any:
        # read_skill 暂走 Route A builtin(SandboxToolBase)。
        raise NotImplementedError(
            "SkillCapability.execute 未收编 —— skill 工具暂走 Route A builtin"
        )

    async def release(self, reason: ReleaseReason) -> None:
        self._status = ExecutorStatus.RELEASED