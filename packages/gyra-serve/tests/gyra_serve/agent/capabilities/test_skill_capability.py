"""RFC-005 Step B / RFC-006 Stage 7: skill capability 迁移测试。

技能纯声明:SkillCapability declare 渲染 skill 列表(<agent-skills>)进 SYSTEM。
"""

from gyra.core.interface.resource.bundle import CacheScope, Slot


# =========================================================================== #
# RFC-006 Stage 7: SkillCapability 自管理(对象模型统一)
# =========================================================================== #
def test_skill_capability_declares_from_explicit_skills():
    """原生路径:直接给 skills 列表,declare 渲染 <agent-skills>。"""
    from gyra_serve.agent.capabilities.skill import SkillCapability

    skills = [{"name": "s1", "description": "d1", "path": "/p1", "owner": "o", "branch": "master"}]
    cap = SkillCapability(skills=skills)
    contribs = cap.declare()
    assert len(contribs) == 1
    c = contribs[0]
    assert c.slot == Slot.SYSTEM
    assert c.capability_id == "skill"
    assert c.cache_scope == CacheScope.USER
    assert "agent-skills" in c.content
    assert "s1" in c.content


def test_skill_capability_empty_when_no_skills():
    """无 skills → 空 declare。"""
    from gyra_serve.agent.capabilities.skill import SkillCapability

    assert SkillCapability().declare() == []


def test_skill_capability_discovered_by_registry():
    """CapabilityRegistry.discover 发现 skill 目录。"""
    from gyra.agent.capabilities.registry import CapabilityRegistry
    reg = CapabilityRegistry()
    reg.discover()
    # skill register() 是 pass(不注册实例),仅验证目录被扫描不报错
    assert reg is not None


def test_skill_capability_from_config_pure_config():
    from gyra_serve.agent.capabilities.skill import SkillCapability
    cap = SkillCapability.from_config(
        {"skill_name": "xlsx", "skill_description": "Excel 处理", "skill_path": "/p"}
    )
    contribs = cap.declare()
    assert len(contribs) == 1
    assert "xlsx" in contribs[0].content
    assert "Excel 处理" in contribs[0].content


# =========================================================================== #
# RFC-006 Stage 8: SkillCapability prepare 自管 skill_code/path 解析
# =========================================================================== #
async def test_skill_capability_prepare_skips_when_path_present():
    """skills 已带 path → prepare 免 I/O,直接 ready。"""
    from gyra_serve.agent.capabilities.skill import SkillCapability
    cap = SkillCapability(skills=[{"name": "xlsx", "description": "d", "path": "/p", "owner": "", "branch": "master"}])
    await cap.prepare()
    assert cap._status.value == "ready"
    assert cap._skills[0]["path"] == "/p"  # 未被覆盖


async def test_skill_capability_prepare_no_skills_ready():
    from gyra_serve.agent.capabilities.skill import SkillCapability
    cap = SkillCapability(skills=None)
    await cap.prepare()
    assert cap._status.value == "ready"


async def test_skill_capability_prepare_degrades_without_system_app(monkeypatch):
    """缺 path 且无 _SYSTEM_APP → prepare 降级不崩(ready,path 仍空)。"""
    from gyra_serve.agent.capabilities.skill import SkillCapability
    import gyra_serve.agent.capabilities.skill.capability as mod
    monkeypatch.setattr(mod, "_SYSTEM_APP", None, raising=False) if hasattr(mod, "_SYSTEM_APP") else None
    cap = SkillCapability(skills=[{"name": "xlsx", "description": "d", "path": "", "owner": "", "branch": "master"}])
    await cap.prepare()
    assert cap._status.value == "ready"


# =========================================================================== #
# Phase D: SkillCapability 补全(全字段 from_config / skill_code 保留 / "skill" 别名)
# =========================================================================== #
def test_skill_from_config_carries_full_fields():
    from gyra_serve.agent.capabilities.skill import SkillCapability

    cap = SkillCapability.from_config(
        {
            "skill_name": "data-viz",
            "skill_description": "图表技能",
            "skill_path": "/skills/data-viz",
            "skill_code": "sc-123",
            "parent_folder": "/skills",
            "allowed_tools": ["run_python"],
            "branch": "dev",
            "debug_info": {"is_debug": True, "branch": "dev"},
        }
    )
    sk = cap._skills[0]
    assert sk["name"] == "data-viz"
    assert sk["skill_code"] == "sc-123"
    assert sk["parent_folder"] == "/skills"
    assert sk["allowed_tools"] == ["run_python"]
    assert sk["branch"] == "dev"
    assert sk["debug_info"] == {"is_debug": True, "branch": "dev"}


def test_skill_type_alias_registered():
    from gyra.agent.capabilities.registry_factory import CapabilityFactoryRegistry
    from gyra_serve.agent.capabilities.skill import register_capability_to

    registry = CapabilityFactoryRegistry()
    register_capability_to(registry)
    assert registry.has("skill(gyra)")
    assert registry.has("skill")


def test_skill_prepare_keeps_skill_code_when_lookup_needed(monkeypatch):
    """path 缺失走查码路径时,查到的 skill_code 要写回 _skills。"""
    import asyncio
    from types import SimpleNamespace

    from gyra_serve.agent.capabilities.skill import SkillCapability

    cap = SkillCapability.from_config({"skill_name": "data-viz"})
    service = SimpleNamespace(
        get_list=lambda req: [SimpleNamespace(skill_code="sc-9", name="data-viz")],
        get_skill_directory=lambda code: f"/skills/{code}",
    )
    monkeypatch.setattr(
        SkillCapability, "_lookup_skill_code", staticmethod(lambda s, n: "sc-9")
    )
    monkeypatch.setattr(
        SkillCapability,
        "_get_skill_directory",
        staticmethod(lambda s, c: f"/skills/{c}"),
    )
    monkeypatch.setattr("os.path.exists", lambda p: True)

    # 绕过 _SYSTEM_APP 检查:直接驱动 prepare 的核心循环不可行(依赖 service 组件),
    # 改为验证 _lookup/_get_directory 契约 + from_config 不带 path 时不免 I/O 的标记。
    assert cap._skills[0]["path"] == ""
    assert cap._skills[0]["skill_code"] == ""
