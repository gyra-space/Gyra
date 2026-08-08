"""媒体生成结果手动召回（不走 Agent 流程）。

服务重启 / 流程中断后，按 gpts_async_tasks 里的任务记录（detail 含
provider / provider_task_id / prompt / gen_kwargs）重建 provider 轮询，
下载已生成结果并交付到对应会话的 AFS 工作区——昂贵媒体请求的结果
一个都不丢，运维侧可随时手动召回。

用法（serve 层 endpoint 调用）::

    from gyra.agent.multimedia.recall import recall_media_job_record

    outcome = await recall_media_job_record(job_dict, timeout=600)
    # outcome["success"] / outcome["record_updates"]（回写 gpts_async_tasks）
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional

from .config import MultimediaAgentConfig
from .executor import KIND_IMAGE, KIND_VIDEO, MultimediaExecutor

logger = logging.getLogger(__name__)


def _build_recall_afs(conv_id: str) -> Optional[Any]:
    """为召回交付构建 AFS（FileStorage + 本地工作区兜底，无需真实沙箱）。"""
    try:
        from gyra.agent.core.file_system.agent_file_system import AgentFileSystem
        from gyra.agent.multimedia.agent import _LocalDirSandboxAdapter

        file_storage_client = None
        try:
            from gyra._private.config import Config
            from gyra.core.interface.file import FileStorageClient

            system_app = Config().SYSTEM_APP
            if system_app:
                file_storage_client = FileStorageClient.get_instance(system_app)
        except Exception:  # noqa: BLE001
            pass

        # 本地沙箱部署：交付文件同时落工作区目录（与正常生成路径一致）
        sandbox = None
        try:
            from gyra._private.config import Config

            system_app = Config().SYSTEM_APP
            app_config = (
                system_app.config.configs.get("app_config") if system_app else None
            )
            sandbox_config = getattr(app_config, "sandbox", None) if app_config else None
            s_type = getattr(sandbox_config, "type", None) if sandbox_config else None
            work_dir = getattr(sandbox_config, "work_dir", None) if sandbox_config else None
            if s_type in (None, "", "local") and work_dir:
                import os

                if os.path.isdir(work_dir):
                    sandbox = _LocalDirSandboxAdapter(work_dir)
        except Exception:  # noqa: BLE001
            sandbox = None

        return AgentFileSystem(
            conv_id=conv_id or "recall",
            session_id=conv_id or "recall",
            file_storage_client=file_storage_client,
            sandbox=sandbox,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[media-recall] build AFS failed: {e}")
        return None


async def recall_media_job_record(
    job: Dict[str, Any],
    timeout: int = 600,
) -> Dict[str, Any]:
    """按任务记录召回媒体生成结果。

    Args:
        job: gpts_async_tasks 记录（AsyncTaskDao.get 返回的 dict），
            detail 需含 provider_task_id；kind/model/prompt 取自记录。
        timeout: provider 轮询最大等待秒数。

    Returns:
        {
            "success": bool,
            "message": str,                # 给人看的结果说明
            "record_updates": dict,        # 需回写 gpts_async_tasks 的字段
        }
    """
    task_id = (job.get("task_id") or "").strip()
    detail = job.get("detail") or {}
    kind = (job.get("kind") or "").lower()
    model = job.get("model") or ""
    provider_task_id = detail.get("provider_task_id") or ""
    prompt = detail.get("prompt") or job.get("description") or ""
    gen_kwargs = detail.get("gen_kwargs") or {}
    conv_id = job.get("conv_id") or ""

    def _fail(msg: str) -> Dict[str, Any]:
        return {"success": False, "message": msg, "record_updates": {}}

    if not task_id:
        return _fail("任务记录缺少 task_id")
    if kind not in (KIND_IMAGE, KIND_VIDEO):
        return _fail(
            f"任务 {task_id} 不是媒体生成任务（kind={kind or '空'}），无法召回"
        )
    if not provider_task_id:
        return _fail(
            f"任务 {task_id} 的记录里没有 provider_task_id，无法定位 provider 侧任务"
            f"（可能是同步接口生成或记录过旧）"
        )
    if not model:
        return _fail(f"任务 {task_id} 的记录里没有 model，无法解析 provider")

    try:
        from gyra.agent.util.media_gen.provider_registry import (
            MediaGenProviderRegistry,
        )

        # model → protocol/api_key/base_url（与正常生成同一解析链路）
        executor = MultimediaExecutor(config=MultimediaAgentConfig())
        protocol, api_key, base_url = executor._resolve_media_model(model)
        if not protocol or not api_key:
            return _fail(
                f"无法为模型 '{model}' 解析出可用的 provider 配置"
                f"（protocol={protocol or '空'}）"
            )
        provider = MediaGenProviderRegistry.create_provider_by_protocol(
            protocol=protocol, api_key=api_key, base_url=base_url
        )
        if provider is None:
            return _fail(f"protocol '{protocol}' 未注册对应的 provider")

        # 按已有 task_id 重建轮询（不重新提交、不重复扣费）
        resume_fn = getattr(provider, "resume_task", None)
        if resume_fn is None:
            return _fail(f"provider '{protocol}' 不支持按 task_id 召回")
        # 过滤掉会被显式实参覆盖的保留键，避免 **gen_kwargs 与位置/关键字实参
        # 冲突（如 metadata 里带 task_id → resume_task() 重复传参）
        resume_kwargs = {
            k: v
            for k, v in (gen_kwargs or {}).items()
            if k not in ("task_id", "model", "timeout", "kind")
        }
        # kind 显式传给 provider 的 resume_task：厂商级多媒体 provider（image+video
        # 合并协议）靠它路由到正确的子 provider，否则图片召回会误打到视频 provider。
        submission = await resume_fn(
            provider_task_id, model, kind=kind, timeout=timeout, **resume_kwargs
        )
        result = await submission.complete()
    except NotImplementedError as e:
        return _fail(str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception(f"[media-recall] recall {task_id} failed: {e}")
        return _fail(f"召回失败: {e}")

    # 交付到对应会话的 AFS 工作区
    label = "图片" if kind == KIND_IMAGE else "视频"
    file_name = f"recalled_{uuid.uuid4().hex[:8]}.{result.format}"
    afs = _build_recall_afs(conv_id)
    description = job.get("description") or f"AI 生成内容: {prompt[:50]}"
    tr = await executor._deliver(
        kind=kind,
        result=result,
        file_name=file_name,
        description=description,
        prompt=prompt,
        afs=afs,
    )
    if not getattr(tr, "success", False):
        return _fail(
            f"{label}已取回但落盘失败: {getattr(tr, 'error', '未知错误')}"
        )

    # 回写记录：状态 + 交付物 + 结果预览（artifact 结构同 AsyncTaskState.to_record）
    from datetime import datetime

    meta = result.metadata or {}
    record_updates: Dict[str, Any] = {
        "status": "completed",
        "error": None,
        "completed_at": datetime.now().isoformat(),
        "result_preview": str(getattr(tr, "output", "") or "")[:800],
        "detail": {
            **detail,
            "recalled": True,
            "provider_task_id": provider_task_id,
            "raw_url": meta.get("video_url") or meta.get("image_url"),
            "file_name": file_name,
        },
    }
    arts = getattr(tr, "artifacts", None) or []
    if arts:
        a = arts[0]
        record_updates["artifact"] = {
            "name": getattr(a, "name", None),
            "type": getattr(a, "type", None),
            "url": getattr(a, "url", None),
            "mime_type": getattr(a, "mime_type", None),
        }

    logger.info(
        f"[media-recall] {task_id} recalled: {file_name} "
        f"(provider_task={provider_task_id})"
    )
    return {
        "success": True,
        "message": (
            f"✅ {label}已召回并交付: {file_name}\n"
            f"- provider 任务: {provider_task_id}\n"
            f"- 模型: {model}\n"
            + (f"- 预览: {record_updates['artifact']['url']}\n" if arts else "")
        ),
        "record_updates": record_updates,
    }


__all__ = ["recall_media_job_record"]
