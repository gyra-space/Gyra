"""预加载技能 helper —— 剧本关联技能 / 手动选择技能 的 SKILL.md 全文注入。

背景（场景空间）：剧本会关联 Skill，该 Skill 是剧本的指导，每次对话必然加载。
现状是 skill 只把 ``<available_skills>`` 目录（name+description）注入上下文，
完整指令要 LLM 调用 ``skill()`` 工具才进入上下文（多一轮工具调用 token）。

本模块为两个特殊情况提供"预加载"：在对话开始时把 SKILL.md **全文**直接放进
上下文（V1 引擎 append 进 system prompt；V2 引擎以 user-role ``<system-reminder>``
注入），等价于 LLM 已调用过 skill 工具，省掉那一轮。**动态 skill 机制（目录 +
skill() 工具）完全不变**——大部分场景仍由 agent 自主选择加载。

约定：
- 内容格式与 V2 ``SkillTool`` 输出一致：``<skill_content name="...">正文</skill_content>``
  （正文去掉 YAML frontmatter，模型对这个格式已经熟悉）；
- **不截断**：SKILL.md 全文注入，大小由 skill 作者在 SKILL.md 里自己控制；
- 注入文案提示模型"已加载，直接按其执行"，避免重复调用 skill 工具；
- 数据来源：剧本 ``declaration.skills`` + ``chat_in_params`` 中 ``sub_type='skill(gyra)'``。
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 与 V2 SkillTool / SkillCatalogConsumer 对齐的注入说明文案
_PRELOAD_NOTE = (
    "以下技能指令已预加载到当前对话上下文，直接按其执行，无需再次调用 skill "
    "工具加载指令；如需读取技能目录下的其它文件（references/scripts 等），可调用 skill 工具。"
)


def _xml_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_preloaded_skill_xml(name: str, body: str) -> str:
    """渲染单个预加载技能 XML（不截断，与 V2 SkillTool 输出格式对齐）。"""
    body = body or ""
    return f'<skill_content name="{_xml_escape(name)}">\n{body}\n</skill_content>'


def build_preloaded_skills_reminder(xmls: List[str]) -> str:
    """把预加载技能 XML 列表包装为注入块（system 段 / user-role reminder 共用）。"""
    if not xmls:
        return ""
    return (
        "<loaded_skills>\n"
        + "\n".join(xmls)
        + "\n</loaded_skills>\n\n"
        + _PRELOAD_NOTE
    )


def _get_skill_service(system_app):
    from gyra_serve.skill.service.service import (
        Service,
        SKILL_SERVICE_COMPONENT_NAME,
    )

    return system_app.get_component(
        SKILL_SERVICE_COMPONENT_NAME, Service, default=None
    )


def _get_playbook_service(system_app):
    from gyra_serve.playbook.service.service import (
        PlaybookService,
        PLAYBOOK_SERVICE_COMPONENT_NAME,
    )

    return system_app.get_component(
        PLAYBOOK_SERVICE_COMPONENT_NAME, PlaybookService, default=None
    )


def load_skill_markdown(
    system_app, skill_ref: str
) -> Optional[Dict[str, str]]:
    """读取 skill 的 SKILL.md 全文（不截断）。

    Args:
        system_app: SystemApp 实例（查 skill service）。
        skill_ref: skill_name 或 skill_code（``get_skill_directory`` 两者都支持）。

    Returns:
        ``{"name": str, "skill_code": str, "body": str}``（body 为去 YAML
        frontmatter 的完整正文）或 None（skill 不存在 / 读取失败）。
    """
    service = _get_skill_service(system_app)
    if service is None:
        logger.debug("[preload-skills] skill service unavailable")
        return None
    try:
        skill_dir = service.get_skill_directory(skill_ref)
        skill_md = os.path.join(skill_dir, "SKILL.md")
        if not os.path.isfile(skill_md):
            logger.debug(
                f"[preload-skills] SKILL.md not found for {skill_ref!r} ({skill_dir})"
            )
            return None
        with open(skill_md, encoding="utf-8") as f:
            raw = f.read()
        if not raw.strip():
            return None
        from gyra.agent.core.v2.skills.filesystem_provider import (
            _parse_frontmatter,
            _strip_frontmatter,
        )

        fm = _parse_frontmatter(raw)
        name = fm.get("name") or skill_ref
        body = _strip_frontmatter(raw).strip("\n")
        return {"name": name, "skill_code": skill_ref, "body": body}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[preload-skills] load {skill_ref!r} failed: {e}")
        return None


def _resolve_playbook_skills(system_app, playbook_id) -> List[str]:
    """从剧本 ``declaration.skills`` 提取技能引用列表（str 或 {name|skill_code}）。"""
    pb_service = _get_playbook_service(system_app)
    if pb_service is None:
        return []
    try:
        pb = pb_service.get_by_id(playbook_id)
        if not pb:
            return []
        decl = getattr(pb, "declaration", None) or {}
        if isinstance(decl, str):
            try:
                decl = json.loads(decl)
            except Exception:  # noqa: BLE001
                decl = {}
        out: List[str] = []
        for s in decl.get("skills") or []:
            if isinstance(s, str):
                ref = s
            elif isinstance(s, dict):
                ref = (
                    s.get("name")
                    or s.get("skill_code")
                    or s.get("skill")
                    or ""
                )
            else:
                ref = ""
            ref = str(ref or "").strip()
            if ref:
                out.append(ref)
        return out
    except Exception as e:  # noqa: BLE001
        logger.warning(
            f"[preload-skills] resolve playbook {playbook_id} skills failed: {e}"
        )
        return []


def _extract_chat_param_skills(chat_in_params) -> List[str]:
    """从 ``chat_in_params`` 提取 ``sub_type='skill(gyra)'`` 的技能引用。"""
    if not chat_in_params:
        return []
    out: List[str] = []
    for p in chat_in_params:
        sub = getattr(p, "sub_type", None)
        if sub != "skill(gyra)":
            continue
        pv = getattr(p, "param_value", None)
        try:
            data = json.loads(pv) if isinstance(pv, str) else pv
        except Exception:  # noqa: BLE001
            data = pv
        if isinstance(data, dict):
            ref = data.get("name") or data.get("skill_code") or data.get("skill_name")
        else:
            ref = str(data or "")
        ref = str(ref or "").strip()
        if ref:
            out.append(ref)
    return out


def _resolve_bound_playbook_id(system_app, ext_info) -> Optional[int]:
    """解析当前对话命中的剧本 id：ext_info.playbook_id（lobby 显式命中）或
    task 绑定的 playbook_id（workbench / 任务提交）。"""
    if not ext_info:
        return None
    playbook_id = ext_info.get("playbook_id")
    if playbook_id is not None:
        return int(playbook_id)
    task_id = ext_info.get("task_id")
    if task_id is None:
        return None
    try:
        from gyra_serve.task.service.service import (
            TaskService,
            TASK_SERVICE_COMPONENT_NAME,
        )

        ts = system_app.get_component(
            TASK_SERVICE_COMPONENT_NAME, TaskService, default=None
        )
        task = ts.get_by_id(int(task_id)) if ts else None
        pb_id = getattr(task, "playbook_id", None) if task else None
        return int(pb_id) if pb_id else None
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[preload-skills] resolve task playbook failed: {e}")
        return None


def collect_preloaded_skill_xmls(
    system_app, ext_info: Optional[Dict[str, Any]], chat_in_params
) -> List[str]:
    """汇总预加载技能 XML 列表（剧本关联 + 手动选择，按引用去重）。

    任何单点失败都不阻断：加载不到的技能直接跳过，绝不抛异常。
    """
    refs: List[str] = []
    playbook_id = _resolve_bound_playbook_id(system_app, ext_info)
    if playbook_id is not None:
        refs.extend(_resolve_playbook_skills(system_app, playbook_id))
    refs.extend(_extract_chat_param_skills(chat_in_params))

    xmls: List[str] = []
    seen = set()
    for ref in refs:
        key = ref.lower()
        if not key or key in seen:
            continue
        seen.add(key)
        loaded = load_skill_markdown(system_app, ref)
        if loaded is None:
            continue
        xmls.append(render_preloaded_skill_xml(loaded["name"], loaded["body"]))
    return xmls
