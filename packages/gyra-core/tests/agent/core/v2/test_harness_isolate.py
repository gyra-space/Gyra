"""HarnessContext.isolate() 嵌套作用域测试。"""
import pytest

from gyra.agent.core.v2.harness.context import HarnessContext


def _mk_harness(**overrides) -> HarnessContext:
    """构造最小 HarnessContext 实例（用 None 字段）。"""
    base = dict(
        storage=None,
        events=None,
        tools=None,
        approval=None,
        subagents=None,
        jobs=None,
        hooks=None,
        thinking_fn=None,
        acting_fn=None,
    )
    base.update(overrides)
    return HarnessContext(**base)


def test_isolate_basic():
    """基本 isolate：子继承父字段，override 字段替换。"""
    parent = _mk_harness()
    parent_tools = object()
    sub = parent.isolate("readonly_preset", approval=None, tools=parent_tools)
    assert sub.storage is parent.storage
    assert sub.approval is None
    assert sub.tools is parent_tools
    assert sub is not parent
    # 父不变
    assert parent.approval is None
    assert parent.tools is None


def test_isolate_label_chain():
    """嵌套 isolate 形成 label 链。"""
    root = _mk_harness()
    a = root.isolate("a")
    b = a.isolate("b")
    c = b.isolate("c")
    chain = c.get_isolation_chain()
    assert chain == ["a", "b", "c"]


def test_isolate_invalid_label():
    with pytest.raises(ValueError):
        _mk_harness().isolate("")


def test_isolate_invalid_field():
    with pytest.raises(ValueError):
        _mk_harness().isolate("x", nonexistent_field=1)


def test_with_override():
    """with_override 自动生成 label。"""
    root = _mk_harness()
    sub = root.with_override(approval="X")
    assert sub.approval == "X"
    chain = sub.get_isolation_chain()
    assert len(chain) == 1
    assert chain[0].startswith("override-")


def test_isolate_independence():
    """修改子不影响父；修改父不影响已存在子。"""
    parent = _mk_harness()
    sub = parent.isolate("a", approval="P")
    assert sub.approval == "P"
    assert parent.approval is None
