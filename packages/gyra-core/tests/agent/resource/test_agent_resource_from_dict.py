"""Phase D: AgentResource.from_dict 容忍性测试。

老格式(非 JSON)value 走 normalize_resource_value 转换;未知类型/解析失败
保留原值、绝不 raise(DB 存量配置加载路径必须容忍历史数据)。
"""
import json

from gyra.agent.resource.base import AgentResource


def test_from_dict_v2_json_string_passthrough():
    d = {"type": "datasource", "name": "db1", "value": '{"db_name": "db1"}'}
    ar = AgentResource.from_dict(d)
    assert ar.value == '{"db_name": "db1"}'


def test_from_dict_v2_dict_passthrough():
    d = {"type": "datasource", "name": "db1", "value": {"db_name": "db1"}}
    ar = AgentResource.from_dict(d)
    assert ar.value == {"db_name": "db1"}


def test_from_dict_unknown_type_keeps_raw_value():
    """未知类型(如已删除的 reasoning_engine)不 raise,保留原值。"""
    d = {"type": "reasoning_engine", "name": "re1", "value": "some-legacy-value"}
    ar = AgentResource.from_dict(d)
    assert ar is not None
    assert ar.type == "reasoning_engine"
    assert ar.value == "some-legacy-value"


def test_from_dict_deleted_workflow_type_tolerated():
    d = {"type": "workflow", "name": "wf1", "value": "wf-ref"}
    ar = AgentResource.from_dict(d)
    assert ar is not None
    assert ar.value == "wf-ref"


def test_from_json_list_str_with_legacy_rows():
    """DB 加载路径:混合 v2 行 + 已删除类型行 + 纯字符串行,全部不炸。"""
    raw = json.dumps(
        [
            {"type": "datasource", "name": "db1", "value": {"db_name": "db1"}},
            {"type": "reasoning_engine", "name": "re", "value": "legacy"},
            {"type": "knowledge", "name": "k", "value": "kid-1"},
        ],
        ensure_ascii=False,
    )
    lst = AgentResource.from_json_list_str(raw)
    assert lst is not None and len(lst) == 3
    assert lst[1].type == "reasoning_engine"
    assert lst[2].value == "kid-1"
