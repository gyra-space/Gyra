"""技能发布核心逻辑:把会话内创建的 skill 目录注册进技能资源库。

skill_publish agent tool 的共享实现,与 REST ``/upload`` / ``/upload_folder``
走同一数据通路(service + DAO),不走 HTTP。同步实现,可在同步工具函数内
直接执行(对齐 skill service 全同步 DAO 模式)。

流程对齐 ``Service.upload_from_folder``:
定位 SKILL.md -> 解析 frontmatter -> 同名即原地 update -> 建/更 DB 记录 ->
拷贝到 project_skill_dir(可选 sandbox_skill_dir)-> 广播 workspace 事件。
"""

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _deny(error: str, code: str) -> Dict[str, Any]:
    return {"success": False, "error": error, "code": code}


def publish_skill_from_dir(
    skill_dir: str,
    operator: str = "",
    workspace_id: Optional[int] = None,
    system_app: Optional[Any] = None,
) -> Dict[str, Any]:
    """把 ``skill_dir`` 下的技能发布到技能资源库(server_app_skill 表)。

    Args:
        skill_dir: 技能目录路径(服务器本地可见,含 SKILL.md;也支持传父目录,
            内部会递归查找 SKILL.md)。
        operator: 操作者名(审计日志用)。
        workspace_id: 场景空间 ID;提供时广播 ``skill_published`` 事件给前端卡片。
        system_app: SystemApp 实例;缺省从全局 Config 解析(测试可注入)。

    Returns:
        ``{success, skill_code, name, action, path, ...}`` 或
        ``{success: False, error, code}``。
    """
    from gyra._private.config import Config
    from gyra_serve.skill.service.service import (
        Service,
        SKILL_SERVICE_COMPONENT_NAME,
        normalize_skill_name,
    )
    from gyra_serve.workspace.event_bus import emit_workspace_event

    skill_dir = (skill_dir or "").strip()
    if not skill_dir:
        return _deny("skill_dir 不能为空", "INVALID_ARGS")

    if system_app is None:
        system_app = Config().SYSTEM_APP
    service: Optional[Service] = system_app.get_component(
        SKILL_SERVICE_COMPONENT_NAME, Service, default=None
    )
    if service is None:
        return _deny("技能服务未启动,无法发布", "SERVICE_UNAVAILABLE")

    if not os.path.isdir(skill_dir):
        return _deny(
            f"目录不存在或不可访问: {skill_dir}"
            "(远程沙箱内路径暂不支持,请使用工作区/会话目录)",
            "DIR_NOT_FOUND",
        )

    skill_path = service._find_skill_directory(skill_dir)
    if not skill_path:
        return _deny(f"{skill_dir} 下未找到含 SKILL.md 的技能目录", "SKILL_MD_NOT_FOUND")

    skill_md_path = os.path.join(skill_path, "SKILL.md")
    skill_meta = service._parse_skill_md(skill_md_path) or {}
    fallback_name = os.path.basename(os.path.normpath(skill_path))
    skill_name = skill_meta.get("name") or fallback_name
    skill_code = normalize_skill_name(skill_name)

    try:
        with open(skill_md_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        return _deny(f"读取 SKILL.md 失败: {e}", "READ_FAILED")

    existing = service.dao.get_one({"skill_code": skill_code})
    action = "updated" if existing else "created"

    from gyra_serve.skill.api.schemas import SkillRequest

    request = SkillRequest(
        skill_code=skill_code,
        name=skill_name,
        description=skill_meta.get("description", ""),
        type=skill_meta.get("type", "python"),
        author=skill_meta.get("author"),
        email=skill_meta.get("email"),
        version=skill_meta.get("version"),
        path=skill_code,
        content=content,
        icon=skill_meta.get("icon"),
        category=skill_meta.get("category"),
        installed=0,
        available=True,
    )
    try:
        service.create(request)  # 已存在同名 skill_code 时 create 内部转 update
        project_skill_dir = service.config.get_project_skill_dir()
        service._copy_skill_to_project(
            skill_path, skill_name, project_skill_dir, skill_code
        )
        sandbox_skill_dir = service.config.get_sandbox_skill_dir()
        if sandbox_skill_dir:
            service._copy_skill_to_sandbox(
                skill_path, skill_name, sandbox_skill_dir, skill_code
            )
    except Exception as e:  # noqa: BLE001
        logger.exception("[skill_publish] publish failed: %s", skill_code)
        return _deny(f"发布失败: {e}", "PUBLISH_FAILED")

    logger.info(
        "[skill_publish] operator=%s skill_code=%s action=%s dir=%s",
        operator or "unknown", skill_code, action, skill_path,
    )

    if workspace_id:
        try:
            emit_workspace_event(
                int(workspace_id),
                "skill_published",
                {
                    "workspace_id": int(workspace_id),
                    "skill_code": skill_code,
                    "name": skill_name,
                    "description": skill_meta.get("description", ""),
                },
            )
        except Exception:  # noqa: BLE001
            logger.warning(
                "[skill_publish] emit workspace event failed: ws=%s", workspace_id,
                exc_info=True,
            )

    return {
        "success": True,
        "skill_code": skill_code,
        "name": skill_name,
        "action": action,
        "description": skill_meta.get("description", ""),
        "source_dir": skill_path,
        "detail_url": f"/agent-skills/detail?code={skill_code}",
        "message": (
            f"技能 {skill_name} 已{'更新' if action == 'updated' else '发布'}"
            f"(code={skill_code}),可在技能资源库查看"
        ),
    }
