"""SceneResourceAssembler 测试:lobby/workbench 装配 + 边界。

RFC-006 SSR Task 5:对话前按场景模式装配 AgentResource。
- lobby(task_id 为空) -> [WorkspaceSceneResource AgentResource]
- workbench 有 playbook_id -> [PlaybookResource AgentResource(完整 config)]
- workbench 无 playbook_id -> []
- 缺 workspace -> []
- 异常 -> [](装配器永不把异常抛入 chat 路径)
"""
import json
from unittest.mock import MagicMock, patch


def _ws_mock(name="营收空间", code="ws_abc123"):
    """构造 workspace mock,确保 .name 是真实字符串(避开 MagicMock name= 构造陷阱:
    Magicmock(name=...) 设置的是 mock 自身的标识名,而非 .name 属性)。"""
    m = MagicMock()
    m.name = name  # 构造后赋值,使 getattr(ws, "name") 返回字符串
    m.workspace_code = code
    return m


def _mock_system_app(workspace=None, task=None, playbook=None, missing_ws=False):
    sa = MagicMock()
    def get_component(name, cls=None):
        m = MagicMock()
        if name == "serve_workspace_service":
            m.get_by_id.return_value = None if missing_ws else (workspace or _ws_mock())
        elif name == "serve_task_service":
            m.get_by_id.return_value = task
        elif name == "serve_playbook_service":
            m.get_by_id.return_value = playbook
        return m
    sa.get_component.side_effect = get_component
    return sa


def test_lobby_assembles_workspace_scene_resource():
    from gyra_serve.workspace.scene_resource_assembler import SceneResourceAssembler
    sa = _mock_system_app(workspace=_ws_mock("营收空间"))
    out = SceneResourceAssembler.assemble(sa, workspace_id=1, task_id=None, conv_uid="c1")
    assert len(out) == 2
    assert out[0].type == "workspace_scene"
    data = json.loads(out[0].value) if isinstance(out[0].value, str) else out[0].value
    assert data["workspace_id"] == 1
    assert data["conv_uid"] == "c1"
    assert data["workspace_name"] == "营收空间"


def test_lobby_injects_derived_ecp_resource():
    """lobby 自动注入派生 ECP 资源:场景 agent 的语意资产落在本空间专属
    ECP workspace(ecp_<workspace_code>),而非全局 default。"""
    from gyra_serve.workspace.scene_resource_assembler import SceneResourceAssembler
    sa = _mock_system_app(workspace=_ws_mock(code="ws_abc123"))
    out = SceneResourceAssembler.assemble(sa, workspace_id=1, task_id=None, conv_uid="c1")
    ecp = [r for r in out if r.type == "ecp"]
    assert len(ecp) == 1
    data = json.loads(ecp[0].value) if isinstance(ecp[0].value, str) else ecp[0].value
    assert data["workspace_id"] == "ecp_ws_abc123"


def test_lobby_attaches_experts_as_app_resources():
    """每位空间专家挂为 Leader 的 app 资源(AgentResource type="app"):
    标准 SubAgent 工具 sync/async 均可按 app_code 寻址到专家,
    场景空间不再有专用派单工具。"""
    from gyra_serve.workspace.scene_resource_assembler import SceneResourceAssembler

    member = MagicMock()
    member.app_code = "expert_sales"
    member.role_hint = "销售分析"
    app_info = MagicMock()
    app_info.app_name = "销售专家"
    app_info.app_describe = "擅长销售数据分析"
    with patch(
        "gyra_serve.workspace.expert.expert_api._service"
    ) as svc, patch(
        "gyra_serve.workspace.expert.expert_api._get_app_info"
    ) as gai:
        svc.return_value.list_members.return_value = [member]
        gai.return_value = app_info
        sa = _mock_system_app(workspace=_ws_mock(code="ws_abc123"))
        out = SceneResourceAssembler.assemble(sa, workspace_id=1, task_id=None, conv_uid="c1")
    apps = [r for r in out if r.type == "app"]
    assert len(apps) == 1
    data = json.loads(apps[0].value) if isinstance(apps[0].value, str) else apps[0].value
    assert data["app_code"] == "expert_sales"
    assert data["app_name"] == "销售专家"
    assert data["app_desc"] == "擅长销售数据分析"


def test_workbench_with_playbook_assembles_playbook_resource():
    from gyra_serve.workspace.scene_resource_assembler import SceneResourceAssembler
    task = MagicMock(); task.playbook_id = 7
    task.expert_app_code = None
    # 用真实 dict 的 declaration 构造 playbook,使 from_playbook_response -> to_agent_resource
    # 的整条路径产出 JSON 可序列化的 PlaybookConfig(零 I/O 序列化是 Task 4 的要求)。
    pb = MagicMock(); pb.id = 7; pb.name = "营收分析"
    pb.declaration = {"text_content": {"workflow": "step1"}}
    sa = _mock_system_app(workspace=_ws_mock(code="ws_abc123"), task=task, playbook=pb)
    out = SceneResourceAssembler.assemble(sa, workspace_id=1, task_id=99, conv_uid="c1")
    # 有 workspace 时先注入 ecp;有合约时注入承载合约文本/交付的 playbook 资源。
    types = [r.type for r in out]
    assert "ecp" in types
    assert "playbook" in types


def test_workbench_injects_derived_ecp_resource():
    """workbench(任务运行时)同样注入派生 ECP 资源。"""
    from gyra_serve.workspace.scene_resource_assembler import SceneResourceAssembler
    task = MagicMock(); task.playbook_id = 7
    task.expert_app_code = None
    pb = MagicMock(); pb.id = 7; pb.name = "营收分析"
    pb.declaration = {"text_content": {"workflow": "step1"}}
    sa = _mock_system_app(workspace=_ws_mock(code="ws_task9"), task=task, playbook=pb)
    out = SceneResourceAssembler.assemble(sa, workspace_id=1, task_id=99, conv_uid="c1")
    ecp = [r for r in out if r.type == "ecp"]
    assert len(ecp) == 1
    data = json.loads(ecp[0].value) if isinstance(ecp[0].value, str) else ecp[0].value
    assert data["workspace_id"] == "ecp_ws_task9"


def test_workbench_materializes_expert_equipment_only_not_declaration_skills():
    """_assemble_workbench 不再从合约 declaration 二次物化 skills/resources
    (专家能力收敛于 GptsApp 标准装备 + 空间外挂)；仅注入承载合约文本/交付的
    playbook 资源,以及可能的专家外挂。缺专家外挂时不从声明物化任何工具。"""
    from gyra_serve.workspace.scene_resource_assembler import SceneResourceAssembler
    task = MagicMock(); task.playbook_id = 7
    task.expert_app_code = None
    pb = MagicMock(); pb.id = 7; pb.name = "营收分析"
    pb.declaration = {
        "skills": ["data-analysis", "doc-coauthoring"],
        "context": {"resources": [{"type": "datasource", "ref": "prod_db"}]},
    }
    sa = _mock_system_app(workspace=_ws_mock(code="ws_abc123"), task=task, playbook=pb)
    out = SceneResourceAssembler.assemble(sa, workspace_id=1, task_id=99, conv_uid="c1")
    types = [r.type for r in out]
    assert "playbook" in types          # 合约元资源(承载交付/沉淀规则)
    assert types.count("skill(gyra)") == 0  # 不再从声明物化 skill
    assert "datasource" not in types    # 不再从声明物化 datasource


def test_workbench_without_playbook_still_injects_ecp():
    """workbench 无合约但 workspace 存在时,仍注入派生 ECP 资源(不因缺合约清空)。"""
    from gyra_serve.workspace.scene_resource_assembler import SceneResourceAssembler
    task = MagicMock(); task.playbook_id = None
    task.expert_app_code = None
    sa = _mock_system_app(workspace=_ws_mock(code="ws_abc123"), task=task)
    out = SceneResourceAssembler.assemble(sa, 1, 99, "c1")
    assert [r.type for r in out] == ["ecp"]


def test_missing_workspace_returns_empty():
    from gyra_serve.workspace.scene_resource_assembler import SceneResourceAssembler
    sa = _mock_system_app(missing_ws=True)
    assert SceneResourceAssembler.assemble(sa, 1, None, "c1") == []


def test_exception_returns_empty_never_raises():
    """装配器在 chat 预处理路径,任何异常都必须吞掉返回 []。"""
    from gyra_serve.workspace.scene_resource_assembler import SceneResourceAssembler
    sa = MagicMock()
    sa.get_component.side_effect = RuntimeError("boom")
    assert SceneResourceAssembler.assemble(sa, 1, None, "c1") == []
