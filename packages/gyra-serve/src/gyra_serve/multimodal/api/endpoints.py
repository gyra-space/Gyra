import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from gyra.component import SystemApp
from gyra_serve.core import Result

from ..config import SERVE_SERVICE_COMPONENT_NAME, ServeConfig
from ..service.service import MultimodalService

logger = logging.getLogger(__name__)

router = APIRouter()
global_system_app: Optional[SystemApp] = None


def get_service() -> MultimodalService:
    return global_system_app.get_component(
        SERVE_SERVICE_COMPONENT_NAME, MultimodalService
    )


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    bucket: Optional[str] = Form(default=None),
    conv_uid: Optional[str] = Form(default=None),
    message_id: Optional[str] = Form(default=None),
    service: MultimodalService = Depends(get_service),
):
    """上传多模态文件.

    文件会被存储到文件系统，并记录元数据到会话中。

    Args:
        file: 上传的文件
        bucket: 存储桶名称
        conv_uid: 会话ID，用于关联文件到会话
        message_id: 消息ID，用于关联文件到特定消息

    Returns:
        文件信息，包括URI、预览URL等
    """
    try:
        file_info = service.upload_file(
            file_name=file.filename,
            file_data=file.file,
            bucket=bucket,
            conv_id=conv_uid,
            message_id=message_id,
            custom_metadata={"conv_uid": conv_uid} if conv_uid else None,
        )
        return Result.succ(service.get_file_info(file_info.uri))
    except ValueError as e:
        return Result.failed(msg=str(e))


@router.get("/files/{conv_id}")
async def list_session_files(
    conv_id: str,
    service: MultimodalService = Depends(get_service),
):
    """获取会话中用户上传的文件列表.

    Args:
        conv_id: 会话ID

    Returns:
        文件列表，包含文件名、类型、预览URL等信息
    """
    files = await service.list_user_files(conv_id)
    return Result.succ(files)


@router.post("/process")
async def process_multimodal(
    text: Optional[str] = Form(default=None),
    file_uris: Optional[str] = Form(default=None),
    preferred_provider: Optional[str] = Form(default=None),
    service: MultimodalService = Depends(get_service),
):
    """处理多模态内容，自动匹配合适的模型.

    Args:
        text: 文本内容
        file_uris: 文件URI列表，逗号分隔
        preferred_provider: 首选模型提供商

    Returns:
        处理后的内容、匹配的模型、文件信息
    """
    uris = file_uris.split(",") if file_uris else None
    result = service.process_multimodal_content(
        text=text,
        file_uris=uris,
        preferred_provider=preferred_provider,
    )
    return Result.succ(result)


@router.get("/models")
async def list_models(
    capability: Optional[str] = None,
    provider: Optional[str] = None,
    service: MultimodalService = Depends(get_service),
):
    """列出支持的多模态模型.

    Args:
        capability: 按能力筛选 (image_input, audio_input, video_input等)
        provider: 按提供商筛选 (openai, anthropic, alibaba, google等)

    Returns:
        模型列表
    """
    models = service.list_supported_models(capability=capability, provider=provider)
    return Result.succ(models)


@router.get("/media-jobs")
async def list_media_jobs(
    conv_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
):
    """列出异步任务（media 生成 / spawn_agent_task 子 Agent）。

    数据来自 DB 持久化（gpts_async_tasks 表，经 AsyncTaskDao），跨实例 / 跨进程 / 重启后
    仍可见，支撑分布式。每个任务包含状态、模型、描述、错误，以及完成后的 AFS 交付物
    （预览/下载地址），便于用户在界面上查看进度与结果。

    Args:
        conv_id: 按会话过滤
        status: 按状态过滤 (pending/running/completed/failed/timeout/cancelled)
        limit: 返回条数上限
    """
    try:
        from gyra_serve.agent.db.async_task_db import AsyncTaskDao

        jobs = AsyncTaskDao().list(
            conv_id=conv_id or "", status=status, limit=limit
        )
        return Result.succ(jobs)
    except Exception as e:
        logger.exception("list_media_jobs exception!")
        return Result.failed(str(e))


@router.get("/media-jobs/{job_id}")
async def get_media_job(job_id: str):
    """查询单个异步任务的详情（含交付物信息）。"""
    try:
        from gyra_serve.agent.db.async_task_db import AsyncTaskDao

        job = AsyncTaskDao().get(job_id)
        if job is None:
            return Result.failed(msg=f"async task {job_id} not found")
        return Result.succ(job)
    except Exception as e:
        logger.exception("get_media_job exception!")
        return Result.failed(str(e))


@router.post("/media-jobs/{job_id}/recall")
async def recall_media_job(job_id: str, timeout: int = Query(600, ge=30, le=3600)):
    """手动召回媒体生成结果（不走 Agent 流程）。

    服务重启 / 流程中断后，按任务记录里的 provider_task_id 对 provider 侧
    已有任务重新轮询 + 下载（不重新提交、不重复扣费），交付到原会话的
    AFS 工作区并回写任务记录。
    """
    try:
        from gyra.agent.multimedia.recall import recall_media_job_record
        from gyra_serve.agent.db.async_task_db import AsyncTaskDao

        dao = AsyncTaskDao()
        job = dao.get(job_id)
        if job is None:
            return Result.failed(msg=f"async task {job_id} not found")

        outcome = await recall_media_job_record(job, timeout=timeout)
        if not outcome.get("success"):
            return Result.failed(msg=outcome.get("message") or "recall failed")

        # 回写记录（status/result_preview/artifact/detail）
        updated = {**job, **(outcome.get("record_updates") or {})}
        dao.upsert(updated)
        return Result.succ({"task_id": job_id, "message": outcome["message"]})
    except Exception as e:
        logger.exception("recall_media_job exception!")
        return Result.failed(str(e))


def init_endpoints(system_app: SystemApp, config: ServeConfig) -> None:
    global global_system_app
    global_system_app = system_app
    # MultimodalService is registered in serve.py after_init method
