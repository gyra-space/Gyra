"""Unit tests for SceneAgentWorkspaceConverter."""
import json
import re
from unittest.mock import AsyncMock, patch
import pytest

from gyra_ext.vis.gyra.gyra_vis_scene_agent_workspace_converter import (
    SceneAgentWorkspaceConverter,
)


def _make_gpt_msg(content="", thinking=None, action_report=None, message_id="m1", sender="BAIZE"):
    """构造一个最小 GptsMessage-like 对象(对齐真实 GptsMessage 契约)。"""
    class _Msg:
        def __init__(self):
            self.message_id = message_id
            self.sender = sender
            self.role = "assistant" if sender != "Human" else "Human"
            self.content = content
            self.thinking = thinking
            self.action_report = action_report
            self.created_at = None
    return _Msg()


def _make_action_output(**overrides):
    """构造 ActionOutput-like 对象(流内工具推送形态)。"""
    class _AO:
        pass
    ao = _AO()
    ao.action_id = overrides.get("action_id", "tool-abc")
    ao.action = overrides.get("action", "Bash")
    ao.action_name = overrides.get("action_name", "Execute a shell command")
    ao.action_input = overrides.get("action_input", {"command": "ls"})
    ao.content = overrides.get("content", "执行中")
    ao.state = overrides.get("state", "running")
    ao.is_exe_success = overrides.get("is_exe_success", True)
    ao.start_time = overrides.get("start_time", "2026-07-17T08:20:34")
    ao.view = overrides.get("view")
    return ao


def _extract_payload(out: str) -> dict:
    match = re.search(r"```scene_agent_workspace\n(.*?)\n```", out, re.DOTALL)
    assert match is not None, f"未找到 scene_agent_workspace vis tag, got: {out!r}"
    return json.loads(match.group(1))


@pytest.mark.asyncio
async def test_render_name_is_scene_agent_workspace():
    conv = SceneAgentWorkspaceConverter(gyra_url="http://localhost")
    assert conv.render_name == "scene_agent_workspace"
    assert conv.web_use is True


@pytest.mark.asyncio
async def test_tool_stream_msg_produces_execution_step():
    """stream_msg 携带 action_report(ActionOutput 对象)→ execution 工具步骤。"""
    conv = SceneAgentWorkspaceConverter(gyra_url="http://localhost")
    stream_msg = {
        "type": "all",
        "message_id": "m1",
        "action_report": [_make_action_output(state="running", content="执行中")],
    }
    payload = _extract_payload(await conv.visualization(messages=[], stream_msg=stream_msg))

    assert payload["render_name"] == "scene_agent_workspace"
    assert len(payload["execution"]) == 1
    step = payload["execution"][0]
    assert step["action"] == "Bash"
    assert step["status"] == "running"
    assert step["action_input"] == {"command": "ls"}
    # 执行中占位文案不作为 output
    assert step["output"] is None

    # 同一 action_id 完成推送 → 步骤状态与结果被合并更新
    done_msg = {
        "type": "all",
        "message_id": "m1",
        "action_report": [_make_action_output(state="complete", content="找到 3 条记录")],
    }
    payload = _extract_payload(await conv.visualization(messages=[], stream_msg=done_msg))
    assert len(payload["execution"]) == 1
    step = payload["execution"][0]
    assert step["status"] == "done"
    assert step["output"] == "找到 3 条记录"


@pytest.mark.asyncio
async def test_tool_step_carries_vis_from_view():
    """工具报告的 view(VIS 围栏)→ 步骤 vis 字段,前端 GPTVis 据此渲染工具组件。

    对齐 vis_manus:工具执行的 view/simple_view 包含结构化 VIS tag(如 d-sql-query),
    场景空间此前只保留 output 文本导致右侧只能渲染原始 JSON;补上 vis 后恢复组件渲染。
    """
    conv = SceneAgentWorkspaceConverter(gyra_url="http://localhost")
    view = "```d-batch-tasks\n{\"tasks\":[{\"id\":4,\"name\":\"Walmart 数据分析\"}]}\n```"
    report = _make_action_output(
        state="complete",
        content="[{\"id\":4,\"workspace_id\":2,\"name\":\"Walmart 数据分析\"}]",
        view=view,
    )
    payload = _extract_payload(
        await conv.visualization(messages=[], stream_msg={"type": "all", "message_id": "m1", "action_report": [report]})
    )
    step = payload["execution"][0]
    assert step["type"] == "tool_call"
    assert step["output"] == '[{"id":4,"workspace_id":2,"name":"Walmart 数据分析"}]'
    assert step["vis"] == view

    # simple_view 兜底:view 缺失时取 simple_view
    report2 = _make_action_output(state="complete", content="ok", view=None)
    report2.simple_view = "```d-tool\n{\"tool_name\":\"list_playbooks\"}\n```"
    payload2 = _extract_payload(
        await conv.visualization(messages=[], stream_msg={"type": "all", "message_id": "m2", "action_report": [report2]})
    )
    assert payload2["execution"][0]["vis"] == report2.simple_view


@pytest.mark.asyncio
async def test_streaming_text_becomes_summary():
    """LLM 流式文本(stream_msg.content,增量 delta)→ summary 实时拼接更新。"""
    conv = SceneAgentWorkspaceConverter(gyra_url="http://localhost")
    out1 = await conv.visualization(messages=[], stream_msg={"message_id": "m9", "content": "正在"})
    assert _extract_payload(out1)["summary"] == "正在"
    out2 = await conv.visualization(messages=[], stream_msg={"message_id": "m9", "content": "查询"})
    assert _extract_payload(out2)["summary"] == "正在查询"


@pytest.mark.asyncio
async def test_streaming_delta_appends_not_replaces():
    """stream_msg.content 是增量 delta:多个 chunk 应追加拼接,而非互相替换。"""
    conv = SceneAgentWorkspaceConverter(gyra_url="http://localhost")
    await conv.visualization(messages=[], stream_msg={"message_id": "m9", "content": "正在"})
    await conv.visualization(messages=[], stream_msg={"message_id": "m9", "content": "查询"})
    out = await conv.visualization(messages=[], stream_msg={"message_id": "m9", "content": "任务"})
    assert _extract_payload(out)["summary"] == "正在查询任务"


@pytest.mark.asyncio
async def test_gpt_msg_history_dict_reports():
    """gpt_msg(落库形态:action_report 为 List[dict])→ 步骤 + summary。"""
    conv = SceneAgentWorkspaceConverter(gyra_url="http://localhost")
    report = {
        "action_id": "tool-1",
        "action": "search_workspace",
        "action_input": {"query": "营收"},
        "state": "complete",
        "is_exe_success": True,
        "content": "找到 3 条记录",
        "start_time": "2026-07-17T08:20:34",
    }
    msg = _make_gpt_msg(content="这是最终回答", action_report=[report], message_id="m7")
    payload = _extract_payload(await conv.visualization(messages=[msg], gpt_msg=msg))

    assert payload["summary"] == "这是最终回答"
    tool_steps = [s for s in payload["execution"] if s["type"] == "tool_call"]
    assert len(tool_steps) == 1
    assert tool_steps[0]["action"] == "search_workspace"
    assert tool_steps[0]["status"] == "done"
    assert tool_steps[0]["output"] == "找到 3 条记录"


@pytest.mark.asyncio
async def test_intermediate_replies_become_steps_not_summary():
    """多条 assistant 文本:每条都作为 answer 步骤按时序内联,最新一条同时进 summary。
    不再凝固为 thinking「阶段回复」—— 文本组件与 thinking(推理)各自独立展示。"""
    conv = SceneAgentWorkspaceConverter(gyra_url="http://localhost")
    msgs = [
        _make_gpt_msg(content="先查一下", message_id="m1"),
        _make_gpt_msg(content="最终结果如下", message_id="m2"),
    ]
    payload = _extract_payload(await conv.final_view(messages=msgs))
    assert payload["summary"] == "最终结果如下"
    answer_steps = [s for s in payload["execution"] if s["type"] == "answer"]
    assert [s["output"] for s in answer_steps] == ["先查一下", "最终结果如下"]


@pytest.mark.asyncio
async def test_text_before_tool_inlines_not_summary():
    """文本先于工具调用产生(时序):文本作为 answer 步骤按时序排在工具前;
    最新 narration 仍进 summary(前端有 answer step 时不重复渲染)。"""
    conv = SceneAgentWorkspaceConverter(gyra_url="http://localhost")
    # 1) LLM 先输出文本(stream content 携带 start_time)
    await conv.visualization(messages=[], stream_msg={
        "message_id": "m1", "content": "先检查当前可用的模型", "start_time": "2026-08-05T10:00:01",
    })
    # 2) 之后工具调用(工具 start_time 更晚)
    await conv.visualization(messages=[], stream_msg={
        "message_id": "m1",
        "action_report": [_make_action_output(
            action_id="t1", action="list_media_models", state="complete",
            content="共 2 个模型", start_time="2026-08-05T10:00:05",
        )],
    })
    payload = _extract_payload(
        await conv.visualization(messages=[], stream_msg={"message_id": "m1"})
    )
    assert payload["summary"] == "先检查当前可用的模型"
    steps = payload["execution"]
    # 文本组件(answer)按时序在工具步骤之前,不凝固为 thinking
    assert [s["type"] for s in steps] == ["answer", "tool_call"]
    assert steps[0]["output"] == "先检查当前可用的模型"
    assert steps[1]["action"] == "list_media_models"


@pytest.mark.asyncio
async def test_text_after_tool_stays_summary():
    """工具完成后再输出的总结文本(时序最后)仍作为底部 summary,顺序不错乱。"""
    conv = SceneAgentWorkspaceConverter(gyra_url="http://localhost")
    await conv.visualization(messages=[], stream_msg={
        "message_id": "m1", "content": "先查一下", "start_time": "2026-08-05T10:00:01",
    })
    await conv.visualization(messages=[], stream_msg={
        "message_id": "m1",
        "action_report": [_make_action_output(
            action_id="t1", action="list_media_models", state="complete",
            content="共 2 个模型", start_time="2026-08-05T10:00:05",
        )],
    })
    # 3) 工具之后 LLM 输出总结(新 message,start_time 最晚)
    await conv.visualization(messages=[], stream_msg={
        "message_id": "m2", "content": "已找到可用模型", "start_time": "2026-08-05T10:00:09",
    })
    payload = _extract_payload(
        await conv.visualization(messages=[], stream_msg={"message_id": "m2"})
    )
    assert payload["summary"] == "已找到可用模型"
    steps = payload["execution"]
    # 两段文本各自作为 answer 步骤按时序内联,顺序不错乱
    assert [s["type"] for s in steps] == ["answer", "tool_call", "answer"]
    assert steps[-1]["output"] == "已找到可用模型"


@pytest.mark.asyncio
async def test_final_reply_also_becomes_answer_step():
    """本轮最终回复除进 summary 外,也作为 answer step 进 execution(稳定 id=narr-{mid}),
    跨轮按 id 合并保留,避免前端 summary 单值被新轮覆盖丢失历史回复。"""
    conv = SceneAgentWorkspaceConverter(gyra_url="http://localhost")
    msgs = [_make_gpt_msg(content="这是最终回答", message_id="m7")]
    payload = _extract_payload(await conv.final_view(messages=msgs))
    assert payload["summary"] == "这是最终回答"
    answer_steps = [s for s in payload["execution"] if s["type"] == "answer"]
    assert len(answer_steps) == 1
    assert answer_steps[0]["id"] == "narr-m7"
    assert answer_steps[0]["output"] == "这是最终回答"


@pytest.mark.asyncio
async def test_answer_step_keeps_text_type_when_tool_arrives():
    """流式文本先作为 answer 推送;工具随后到达时 id(narr-{mid})保持 answer 类型不变、
    按时序排在工具之前 —— 文本组件不翻转为 thinking,与工具步骤各自独立。"""
    conv = SceneAgentWorkspaceConverter(gyra_url="http://localhost")
    # 1) 流式文本:此时是唯一 narration → answer step
    out = await conv.visualization(messages=[], stream_msg={
        "message_id": "m1", "content": "先检查当前可用的模型", "start_time": "2026-08-05T10:00:01",
    })
    steps = _extract_payload(out)["execution"]
    assert [(s["id"], s["type"]) for s in steps] == [("narr-m1", "answer")]

    # 2) 工具调用(更晚 start_time):文本保持 answer,按 ts 排在工具前
    out = await conv.visualization(messages=[], stream_msg={
        "message_id": "m1",
        "action_report": [_make_action_output(
            action_id="t1", action="list_media_models", state="complete",
            content="共 2 个模型", start_time="2026-08-05T10:00:05",
        )],
    })
    steps = _extract_payload(out)["execution"]
    assert [(s["id"], s["type"]) for s in steps] == [("narr-m1", "answer"), ("t1", "tool_call")]


@pytest.mark.asyncio
async def test_user_message_becomes_user_step():
    """Human 消息 → user 类型步骤(前端渲染用户气泡)。"""
    conv = SceneAgentWorkspaceConverter(gyra_url="http://localhost")
    msgs = [
        _make_gpt_msg(content="帮我查下任务", message_id="u1", sender="Human"),
        _make_gpt_msg(content="好的,结果如下", message_id="a1"),
    ]
    payload = _extract_payload(await conv.final_view(messages=msgs))
    user_steps = [s for s in payload["execution"] if s["type"] == "user"]
    assert len(user_steps) == 1
    assert user_steps[0]["output"] == "帮我查下任务"
    assert payload["summary"] == "好的,结果如下"


@pytest.mark.asyncio
async def test_blank_action_is_skipped():
    """最终回答的 blank 占位 action 不作为工具步骤(内容即 summary)。"""
    conv = SceneAgentWorkspaceConverter(gyra_url="http://localhost")
    report = {"action_id": "a1", "action": "blank", "state": "complete", "content": "最终回答"}
    msg = _make_gpt_msg(content="最终回答", action_report=[report], message_id="m8")
    payload = _extract_payload(await conv.visualization(messages=[msg]))
    assert [s for s in payload["execution"] if s["type"] == "tool_call"] == []


# ------------------------------------------------------------------
# 大厅 Exhibit 协议(lobby_exhibits)
# ------------------------------------------------------------------

def _make_output_file(**overrides):
    """构造工具产出文件 dict(action_report[].output_files 项)。"""
    base = {
        "file_id": "f1",
        "file_name": "report.csv",
        "file_type": "output",
        "file_size": 1024,
        "mime_type": "text/csv",
        "oss_url": "gyra-fs://conv/f1/report.csv",
        "preview_url": "http://oss/preview/report.csv",
        "download_url": "http://oss/download/report.csv",
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_render_type_extended_audio_table_slides():
    """场景空间扩展 render_type 推定:音频/表格/幻灯片(其余回落父类)。"""
    conv = SceneAgentWorkspaceConverter(gyra_url="http://localhost")
    assert conv._determine_render_type("a.mp3") == "audio"
    assert conv._determine_render_type("a.bin", "audio/wav") == "audio"
    assert conv._determine_render_type("data.csv") == "table"
    assert conv._determine_render_type("data.xlsx") == "table"
    assert conv._determine_render_type("deck.pptx") == "slides"
    # 父类既有类型不受影响
    assert conv._determine_render_type("pic.png") == "image"
    assert conv._determine_render_type("doc.pdf") == "pdf"
    assert conv._determine_render_type("page.html") == "iframe"


@pytest.mark.asyncio
async def test_tool_output_files_become_lobby_exhibits():
    """工具产出文件(output_files)→ lobby_exhibits 入驻 + 首个挂到步骤 exhibit。"""
    conv = SceneAgentWorkspaceConverter(gyra_url="http://localhost")
    ao = _make_action_output(state="complete", content="已生成")
    ao.output_files = [
        _make_output_file(file_id="f1", file_name="report.csv", mime_type="text/csv"),
        _make_output_file(file_id="f2", file_name="chart.png", mime_type="image/png"),
    ]
    stream_msg = {"type": "all", "message_id": "m1", "action_report": [ao]}
    payload = _extract_payload(await conv.visualization(messages=[], stream_msg=stream_msg))

    exhibits = payload["lobby_exhibits"]
    assert [e["exhibit_id"] for e in exhibits] == ["file_f1", "file_f2"]
    assert exhibits[0]["kind"] == "table"  # csv → table
    assert exhibits[1]["kind"] == "image"  # png → image
    # gyra-fs:// oss_url 优先作为 url
    assert exhibits[0]["source"]["url"] == "gyra-fs://conv/f1/report.csv"
    # 首个产出挂到步骤上(点击步骤 → 大厅打开对应内容)
    step = payload["execution"][0]
    assert step["exhibit"]["exhibit_id"] == "file_f1"
    assert step["exhibit"]["provenance"]["step_id"] == step["id"]


@pytest.mark.asyncio
async def test_lobby_exhibit_upsert_idempotent():
    """同一 file_id 重复推送(running→complete)→ 大厅仅保留一条(幂等覆盖)。"""
    conv = SceneAgentWorkspaceConverter(gyra_url="http://localhost")
    for state in ("running", "complete"):
        ao = _make_action_output(state=state, content="ok" if state == "complete" else "执行中")
        ao.output_files = [_make_output_file()]
        await conv.visualization(
            messages=[], stream_msg={"type": "all", "message_id": "m1", "action_report": [ao]}
        )
    payload = _extract_payload(
        await conv.visualization(messages=[], stream_msg={"type": "all", "message_id": "m1"})
    )
    assert len(payload["lobby_exhibits"]) == 1


@pytest.mark.asyncio
async def test_non_gyra_fs_prefers_preview_url():
    """非 gyra-fs oss_url → url 取 preview_url(回退 oss/download)。"""
    conv = SceneAgentWorkspaceConverter(gyra_url="http://localhost")
    ao = _make_action_output(state="complete", content="done")
    ao.output_files = [_make_output_file(oss_url="http://oss/raw/report.csv")]
    payload = _extract_payload(
        await conv.visualization(messages=[], stream_msg={"type": "all", "message_id": "m1", "action_report": [ao]})
    )
    assert payload["lobby_exhibits"][0]["source"]["url"] == "http://oss/preview/report.csv"


@pytest.mark.asyncio
async def test_deliverable_files_move_into_lobby():
    """交付文件(file_type=deliverable)→ deliverable_files + 入驻大厅(与步骤产出按 file_id 去重)。"""
    conv = SceneAgentWorkspaceConverter(gyra_url="http://localhost")
    report = {
        "action_id": "tool-d",
        "action": "deliver_file",
        "state": "complete",
        "is_exe_success": True,
        "content": "已交付",
        "output_files": [
            _make_output_file(
                file_id="f9",
                file_name="deck.pptx",
                mime_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                file_type="deliverable",
            ),
        ],
    }
    msg = _make_gpt_msg(content="完成", action_report=[report], message_id="m9")
    payload = _extract_payload(await conv.visualization(messages=[msg], gpt_msg=msg))

    assert payload["deliverable_files"][0]["file_id"] == "f9"
    exhibit = [e for e in payload["lobby_exhibits"] if e["exhibit_id"] == "file_f9"]
    assert len(exhibit) == 1  # 步骤产出与交付文件按 file_<id> 幂等去重
    assert exhibit[0]["kind"] == "slides"
    assert payload["panel_view"] == "deliverable"


@pytest.mark.asyncio
async def test_deliverable_ts_prefers_file_created_at_over_action_start_time():
    """增量收集交付文件的 ts 优先取文件元数据 created_at(与全量收集路径一致),
    避免同一文件在增量/全量两条路径下 ts 不同、前端按 file_id+ts 合并时重复展示。"""
    conv = SceneAgentWorkspaceConverter(gyra_url="http://localhost")
    report = {
        "action_id": "tool-d",
        "action": "deliver_file",
        "state": "complete",
        "is_exe_success": True,
        "content": "已交付",
        "start_time": "2026-08-05T10:00:05",
        "output_files": [
            _make_output_file(
                file_id="f9",
                file_name="deck.pptx",
                file_type="deliverable",
                created_at="2026-08-05T10:00:03",
            ),
        ],
    }
    msg = _make_gpt_msg(content="完成", action_report=[report], message_id="m9")
    payload = _extract_payload(await conv.visualization(messages=[msg], gpt_msg=msg))

    assert payload["deliverable_files"][0]["ts"] == "2026-08-05T10:00:03"


@pytest.mark.asyncio
async def test_deliverable_ts_falls_back_to_action_start_time():
    """文件元数据无 created_at 时,ts 回退产出该文件的动作/消息时间
    (与 messages 全量收集路径的兜底一致:消息 created_at)。"""
    conv = SceneAgentWorkspaceConverter(gyra_url="http://localhost")
    report = {
        "action_id": "tool-d",
        "action": "deliver_file",
        "state": "complete",
        "is_exe_success": True,
        "content": "已交付",
        "start_time": "2026-08-05T10:00:05",
        "output_files": [
            _make_output_file(file_id="f9", file_name="deck.pptx", file_type="deliverable"),
        ],
    }
    msg = _make_gpt_msg(content="完成", action_report=[report], message_id="m9")
    msg.created_at = "2026-08-05T10:00:05"
    payload = _extract_payload(await conv.visualization(messages=[msg], gpt_msg=msg))

    assert payload["deliverable_files"][0]["ts"] == "2026-08-05T10:00:05"


@pytest.mark.asyncio
async def test_deliverable_render_type_to_kind_mapping():
    """deliverable render_type → exhibit kind 映射(与前端 RENDER_TYPE_TO_KIND 对齐)。"""
    conv = SceneAgentWorkspaceConverter(gyra_url="http://localhost")
    cases = {
        "iframe": "html", "image": "image", "video": "video", "audio": "audio",
        "pdf": "pdf", "markdown": "markdown", "code": "code", "table": "table",
        "slides": "slides", "archive": "file", "unknown": "file",
    }
    for rt, kind in cases.items():
        ex = conv._deliverable_dict_to_exhibit({"file_id": "x", "file_name": "f", "render_type": rt})
        assert ex["kind"] == kind


@pytest.mark.asyncio
async def test_final_view_resets_lobby_exhibits():
    """final_view(历史重建)重置大厅:只含本次消息产生的入驻内容。"""
    conv = SceneAgentWorkspaceConverter(gyra_url="http://localhost")
    ao = _make_action_output(state="complete", content="done")
    ao.output_files = [_make_output_file(file_id="fold", file_name="old.png", mime_type="image/png")]
    await conv.visualization(messages=[], stream_msg={"type": "all", "message_id": "m1", "action_report": [ao]})

    msg = _make_gpt_msg(content="历史回答", message_id="h1")
    payload = _extract_payload(await conv.final_view(messages=[msg]))
    assert payload["lobby_exhibits"] == []
    assert payload["summary"] == "历史回答"


# ------------------------------------------------------------------
# 异步子 agent 任务看板(subagents)
# ------------------------------------------------------------------

def _make_subagent_item(**overrides):
    base = {
        "sub_conv_id": "sub_1",
        "agent_name": "multimedia",
        "task": "生成视频",
        "status": "running",
        "mode": "async",
        "authorization": None,
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_subagents_field_present_empty_by_default():
    """无 coordinator(单测环境)时 subagents 为空数组,字段始终存在。"""
    conv = SceneAgentWorkspaceConverter(gyra_url="http://localhost")
    payload = _extract_payload(await conv.visualization(messages=[]))
    assert payload["subagents"] == []


@pytest.mark.asyncio
async def test_subagents_collected_from_coordinator():
    """coordinator 返回子任务卡片 → 并入 scene_agent_workspace payload。"""
    conv = SceneAgentWorkspaceConverter(gyra_url="http://localhost")
    items = [
        _make_subagent_item(status="running"),
        _make_subagent_item(sub_conv_id="sub_2", status="done"),
    ]
    with patch(
        "gyra_serve.agent.subagent_coordinator.get_subagent_coordinator",
        return_value=AsyncMock(list_subagent_items=AsyncMock(return_value=items)),
    ):
        payload = _extract_payload(
            await conv.visualization(messages=[_make_gpt_msg(content="hi", message_id="m0")], conv_id="conv_main_1")
        )
    assert [it["sub_conv_id"] for it in payload["subagents"]] == ["sub_1", "sub_2"]
    assert payload["subagents"][0]["status"] == "running"


@pytest.mark.asyncio
async def test_subagents_final_view_rebuild():
    """历史重建(final_view)也能恢复到子任务看板。"""
    conv = SceneAgentWorkspaceConverter(gyra_url="http://localhost")
    items = [_make_subagent_item(sub_conv_id="sub_x", status="awaiting_authorization", authorization="确认?")]
    with patch(
        "gyra_serve.agent.subagent_coordinator.get_subagent_coordinator",
        return_value=AsyncMock(list_subagent_items=AsyncMock(return_value=items)),
    ):
        payload = _extract_payload(
            await conv.final_view(messages=[_make_gpt_msg(content="历史", message_id="h1")], conv_id="conv_main_1")
        )
    assert payload["subagents"][0]["sub_conv_id"] == "sub_x"
    assert payload["subagents"][0]["status"] == "awaiting_authorization"


@pytest.mark.asyncio
async def test_subagents_collect_failure_returns_empty():
    """coordinator 异常 → subagents 为空数组,不影响主视图。"""
    conv = SceneAgentWorkspaceConverter(gyra_url="http://localhost")
    with patch(
        "gyra_serve.agent.subagent_coordinator.get_subagent_coordinator",
        side_effect=RuntimeError("db down"),
    ):
        payload = _extract_payload(
            await conv.visualization(messages=[_make_gpt_msg(content="hi", message_id="m0")], conv_id="conv_main_1")
        )
    assert payload["subagents"] == []
