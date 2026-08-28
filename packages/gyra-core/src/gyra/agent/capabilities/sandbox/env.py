"""Sandbox env 文本构建(RFC-005 S14)。

从 sandbox_client 静态属性(provider/work_dir/skill_dir)产 env 信息文本。
属轻量属性读取(非 I/O),务实放宽 declare 纯函数约束。
"""

from __future__ import annotations

import os
from typing import Any, Optional


def build_env_text(sandbox_client: Any, work_dir: str) -> str:
    """构建沙箱 env 信息文本。

    Args:
        sandbox_client: SandboxBase 实例。
        work_dir: **会话工作目录**。场景空间下为
            ``<空间公共目录>/sessions/<conv_uid>/``;未启用会话隔离时与
            ``sandbox_client.work_dir`` 一致。
    """
    lines = ["### 环境信息", ""]
    lines.append(f"工作目录: {work_dir}")

    shared_root = ""
    if sandbox_client is not None:
        system_info = get_system_info(sandbox_client)
        if system_info:
            lines.append(f"系统: {system_info}")
        skill_dir = getattr(sandbox_client, "skill_dir", "")
        if skill_dir:
            lines.append(f"技能目录: {skill_dir}")
        shared_root = getattr(sandbox_client, "work_dir", "") or ""

    lines.append("")
    if shared_root and os.path.normpath(shared_root) != os.path.normpath(work_dir):
        # 场景空间:会话目录挂在公共层之下
        lines.append(f"空间公共目录: {shared_root}")
        lines.append(
            "相对路径(如 report.xlsx)默认写入当前会话目录,与其他会话互不干扰;"
            "空间级公共资产(上传的数据集等)位于空间公共目录,用绝对路径访问,"
            "需要共享给其他会话时把文件写到公共目录下的 shared/ 。"
        )
        lines.append("")
        lines.append(
            "<important>工作目录与空间公共目录都是持久的,写入的文件跨轮次、跨会话保留。</important>"
        )
    else:
        lines.append(
            "<important>沙箱环境是临时的，会话结束后会被销毁。如需持久化文件，请使用 write_file 工具。</important>"
        )
    return "\n".join(lines)


def get_system_info(sandbox_client: Any) -> str:
    """按 sandbox provider 类型产系统信息(逻辑对齐 _get_sandbox_system_info)。"""
    provider = getattr(sandbox_client, "provider", lambda: "unknown")()
    if provider == "local":
        import platform

        system = platform.system()
        if system == "Darwin":
            return f"macOS ({platform.processor()}), 本地沙箱环境，路径映射到项目目录"
        elif system == "Linux":
            return f"Linux ({platform.processor()}), 本地沙箱环境，路径映射到项目目录"
        elif system == "Windows":
            return "Windows, 本地沙箱环境，路径映射到项目目录"
        return f"{system}, 本地沙箱环境，路径映射到项目目录"
    return "Ubuntu 24.04 linux/amd64（已联网），用户：ubuntu（拥有免密 sudo 权限）"