"""
多媒体生成执行器（可复用）

把「模型解析 → provider 创建 → 同步/异步生成 → 轮询下载 → AFS 交付」这条链路
从具体工具里抽出来，封装成可复用的执行器。它不依赖任何 LLM 推理循环，输入一个
任务描述 + 固定配置 + 覆盖参数，确定性映射到媒体生成 provider 调用。

被谁使用：
- ``MultimediaAgent``（agent 协作范式的载体）
- 需要直接调用媒体生成能力的其它服务（工具范式保留）

核心职责（对应配置项）：
- 自管模型选择：request.model 覆盖 › config.default_*_model › 系统默认 › 首个可用
- 预设风格/场景 prompt：style_prompt 前置 + scene_prompt 后置
- 固定参数覆盖：config.fixed_params + config 输出默认值（尺寸/分辨率/宽高比/时长）
- 异步轮询下载：wait=False 时经 ``AsyncTaskManager`` 提交 submit + 后台 resume/deliver
- AFS 交付：字节经 AFS 落盘并产出 artifact（交付物）
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .config import MultimediaAgentConfig

logger = logging.getLogger(__name__)

# 媒体生成能力
KIND_IMAGE = "image"
KIND_VIDEO = "video"


@dataclass
class MultimediaRequest:
    """一次多媒体生成任务的入参。

    Attributes:
        prompt: 任务描述（必填）。会被 config.style_prompt 前置、scene_prompt 后置。
        kind: "image" | "video"。
        model: 显式指定模型名（可选，覆盖 config 默认模型）。
        params: provider 参数覆盖（如 size/resolution/duration/quality/seed）。
        description: 交付文件描述（可选，默认用 prompt 截断）。
        wait: 是否同步等待。None 时用 config.async_default 的取反。
        afs: 本次调用可用的 AFS 实例（可选，覆盖构造时传入的）。
        conv_id: 所属会话 ID（异步模式用于通知过滤）。
        reference_images: 参考图 URL 列表（图生图/图生视频/参考生视频）。
        image_url: 首帧/参考图 URL（图生视频/图片编辑）。
        image_url_last: 尾帧 URL（首尾帧生视频）。
    """

    prompt: str
    kind: str = KIND_IMAGE
    model: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    wait: Optional[bool] = None
    afs: Any = None
    conv_id: str = ""
    reference_images: List[str] = field(default_factory=list)
    image_url: str = ""
    image_url_last: str = ""


class MultimediaExecutor:
    """可复用的多媒体生成执行器。

    Args:
        config: 固定配置（默认模型 / 预设提示词 / 输出设置 / 交付方式）。
        afs: 默认 AFS 实例（单次调用可用 request.afs 覆盖）。
        conv_id: 默认所属会话 ID。
    """

    def __init__(
        self,
        config: Optional[MultimediaAgentConfig] = None,
        afs: Any = None,
        conv_id: str = "",
    ):
        self.config = config or MultimediaAgentConfig()
        self.afs = afs
        self.conv_id = conv_id
        # 当多媒体 Agent 作为子 Agent 在子会话(sub_conv)运行时,主会话 ID 由
        # MultimediaAgent 从 agent_context.extra["main_conv_id"] 注入。轮询任务
        # 仍以 sub_conv 隔离(不触发主 resume),但记录 main_conv_id 使主会话能
        # 查到子 Agent 生成的产物 artifact(图片/视频 URL),无需下钻子会话。
        self.main_conv_id: str = ""

    # ------------------------------------------------------------------
    # 对外主入口
    # ------------------------------------------------------------------

    async def run(self, request: MultimediaRequest) -> Any:
        """执行一次多媒体生成任务，返回 ToolResult。

        - wait=True / 不可异步：同步生成并交付，返回 SUCCESS 的 ToolResult。
        - wait=False / provider 支持异步提交：提交到 AsyncTaskManager，
          返回 PENDING 的 ToolResult（含 job_id），后台轮询下载并交付。
        """
        from gyra.agent.tools.result import ToolResult

        kind = (request.kind or "").lower()
        if kind not in (KIND_IMAGE, KIND_VIDEO):
            return ToolResult.fail(
                error=f"不支持的媒体类型 '{request.kind}'",
                tool_name=self.name_for(kind),
            )

        prompt = (request.prompt or "").strip()
        if not prompt:
            return ToolResult.fail(
                error="任务描述不能为空", tool_name=self.name_for(kind)
            )

        # 能力类型检查（二选一）：config.capability 决定该实例唯一允许的媒体类型。
        allowed = (self.config.capability or KIND_IMAGE).lower()
        if allowed in (KIND_IMAGE, KIND_VIDEO) and kind != allowed:
            want = "视频" if kind == KIND_VIDEO else "图片"
            only = "图片" if allowed == KIND_IMAGE else "视频"
            return ToolResult.fail(
                error=f"该多媒体 Agent 配置为仅生成{only}，无法生成{want}。"
                f"如需生成{want}，请在 Agent 配置中把能力类型切换为「{only}」，"
                f"或另建一个 {want} Agent。",
                tool_name=self._tool_name(kind),
            )
        # 兼容旧配置：capability 未识别时回退 capability_* 开关
        if allowed not in (KIND_IMAGE, KIND_VIDEO):
            if kind == KIND_IMAGE and not self.config.capability_image:
                return ToolResult.fail(
                    error="该多媒体 Agent 未启用图片生成能力",
                    tool_name=self._tool_name(kind),
                )
            if kind == KIND_VIDEO and not self.config.capability_video:
                return ToolResult.fail(
                    error="该多媒体 Agent 未启用视频生成能力",
                    tool_name=self._tool_name(kind),
                )

        # 1) 自管模型选择
        model = self._resolve_model(kind, request.model)
        if not model:
            cap = "图片" if kind == KIND_IMAGE else "视频"
            return ToolResult.fail(
                error=(
                    f"未配置任何可用的{cap}生成模型。请在模型管理中配置，"
                    f"或给该 Agent 设置 default_{kind}_model。"
                ),
                tool_name=self._tool_name(kind),
            )

        # 2) 解析协议 / 凭证
        protocol, api_key, base_url = self._resolve_media_model(model)
        if not protocol:
            cap = "图片" if kind == KIND_IMAGE else "视频"
            return ToolResult.fail(
                error=f"未找到模型 '{model}' 对应的{cap}生成服务。",
                tool_name=self._tool_name(kind),
            )
        if not api_key:
            return ToolResult.fail(
                error=f"未找到模型 '{model}' (protocol={protocol}) 的 API Key。",
                tool_name=self._tool_name(kind),
            )

        from gyra.agent.util.media_gen.provider_registry import MediaGenProviderRegistry

        provider = MediaGenProviderRegistry.create_provider_by_protocol(
            protocol=protocol, api_key=api_key, base_url=base_url
        )
        if not provider:
            return ToolResult.fail(
                error=f"protocol '{protocol}' 未注册对应的 provider。",
                tool_name=self._tool_name(kind),
            )

        # 3) 组装最终 prompt（预设风格/场景）
        final_prompt = self._build_prompt(prompt)

        # 4) 组装 provider 参数（固定覆盖 + 输出默认 + 请求覆盖）
        gen_kwargs = self._build_gen_kwargs(kind, request)

        # 4.5) 防重复提交（在任何 provider 提交之前）：同会话已有同 kind/model/
        # 同内容的在途任务时直接复用该 job，不再向 provider 发起请求——图片/视频
        # 生成按次计费，LLM 误判任务丢失而重试时必须在这里拦下，不重复扣费。
        reused = self._find_in_flight_media(kind, model, final_prompt, request)
        if reused is not None:
            return reused

        # 5) 决定同步/异步
        wait = self._resolve_wait(request.wait)
        description = request.description or (f"AI 生成内容: {request.prompt[:50]}")
        submission = None
        if hasattr(provider, "submit_video") and kind == KIND_VIDEO:
            try:
                submission = await provider.submit_video(
                    final_prompt, model, **gen_kwargs
                )
            except NotImplementedError:
                submission = None  # provider 声明了 submit_video 但实际不支持 → 走同步
            except Exception as e:  # noqa: BLE001 - 提交失败立即返回
                logger.error(f"[multimedia-executor] submit failed: {e}", exc_info=True)
                return ToolResult.fail(
                    error=f"视频生成提交失败: {e}",
                    tool_name=self._tool_name(kind),
                )

        if submission is not None and not wait:
            return await self._run_async(
                kind=kind,
                model=model,
                prompt=final_prompt,
                description=description,
                request=request,
                submission=submission,
            )

        # 5.5) 任务记录（媒体生成很贵，一个请求结果都不能丢）：同步路径（含
        # SubAgent 内联轮询）在生成前登记持久化任务记录，provider_task_id/prompt/
        # 原始链接落 gpts_async_tasks.detail，终态回写——进程重启也可按
        # provider_task_id 找回结果。同时在途记录使防重复守卫覆盖同步路径。
        mirror_id = await self._register_media_mirror(
            kind, model, final_prompt, description, request, protocol, submission
        )

        # 同步路径
        try:
            if submission is not None:
                # 已显式提交（video + submit 支持）：就地轮询同一 submission，
                # 与 provider.generate_video 内部行为一致，但 submission 在手可登记
                result = await submission.complete()
            elif kind == KIND_VIDEO:
                result = await provider.generate_video(
                    final_prompt, model, **gen_kwargs
                )
            else:
                result = await provider.generate_image(
                    final_prompt, model, **gen_kwargs
                )
        except NotImplementedError:
            cap = "视频" if kind == KIND_VIDEO else "图片"
            self._complete_media_mirror(
                mirror_id, error=f"模型 '{model}' 不支持{cap}生成"
            )
            return ToolResult.fail(
                error=f"模型 '{model}' (protocol={protocol}) 不支持{cap}生成",
                tool_name=self._tool_name(kind),
            )
        except TimeoutError as e:
            # 提交已成功、仅本地轮询超时：转后台继续等待同一 provider task，
            # 不重复提交（重复扣费）。无 submission 的 provider 维持原报错。
            submission = submission or getattr(e, "submission", None)
            if submission is not None:
                logger.info(
                    f"[multimedia-executor] poll timed out after submit; "
                    f"continue polling provider task {submission.task_id} in background"
                )
                tr = await self._run_async(
                    kind=kind,
                    model=model,
                    prompt=final_prompt,
                    description=description,
                    request=request,
                    submission=submission,
                    resumed_after_timeout=str(e),
                )
                # 镜像记为"已转后台"并指向真正的 atask（不丢记录、不重复计费）
                bg_job = (getattr(tr, "metadata", None) or {}).get("job_id", "")
                self._complete_media_mirror(
                    mirror_id,
                    result=(
                        f"前台等待超时，已转后台任务 {bg_job} 续等同一 "
                        f"provider task {submission.task_id}（不重复扣费）"
                    ),
                )
                return tr
            self._complete_media_mirror(mirror_id, error=f"生成超时: {e}")
            return ToolResult.fail(
                error=f"生成超时: {e}", tool_name=self._tool_name(kind)
            )
        except Exception as e:  # noqa: BLE001
            logger.error(f"[multimedia-executor] generation failed: {e}", exc_info=True)
            cap = "视频" if kind == KIND_VIDEO else "图片"
            self._complete_media_mirror(mirror_id, error=f"{cap}生成失败: {e}")
            return ToolResult.fail(
                error=f"{cap}生成失败: {e}",
                tool_name=self._tool_name(kind),
            )

        file_name = f"{self.config.file_prefix}_{uuid.uuid4().hex[:8]}.{result.format}"
        tr = await self._deliver(
            kind=kind,
            result=result,
            file_name=file_name,
            description=description,
            prompt=final_prompt,
            afs=request.afs or self.afs,
        )
        # 终态回写：补充 provider task_id / 原始下载地址后完成镜像（结果随
        # ToolResult 入台账，含 artifact 信息）。已同步交付，标记 consumed
        # 避免完成通知被重复注入主 agent 上下文。
        meta = result.metadata or {}
        self._complete_media_mirror(
            mirror_id,
            result=tr if getattr(tr, "success", False) else None,
            error=None if getattr(tr, "success", False) else getattr(tr, "error", None),
            extra_context={
                k: v
                for k, v in {
                    "provider_task_id": meta.get("task_id"),
                    "raw_url": meta.get("video_url") or meta.get("image_url"),
                    "file_name": file_name,
                }.items()
                if v
            },
        )
        return tr

    # ------------------------------------------------------------------
    # 模型 / 参数解析
    # ------------------------------------------------------------------

    def _resolve_model(self, kind: str, explicit: str) -> str:
        """模型选择优先级：显式 › 候选池(默认›第一个可用) › 系统默认 › 首个可用。

        候选池（config.image_models / video_models）存在时，只在池内选：
        - 默认模型在池内且可用 → 用它；
        - 否则池内第一个可用；
        - 否则池内第一个（让下游报错更明确）。
        候选池为空时回退全局（系统默认 / 首个可用）。
        """
        from gyra.agent.util.media_gen.provider_registry import MediaGenProviderRegistry

        if explicit:
            return explicit

        if kind == KIND_VIDEO:
            default = self.config.default_video_model
            pool = self.config.video_models or []
            if pool:
                usable = set(MediaGenProviderRegistry.get_usable_model_names("video"))
                if default and default in pool and default in usable:
                    return default
                for m in pool:
                    if m in usable:
                        return m
                return default if default in pool else pool[0]
            return (
                default
                or MediaGenProviderRegistry.get_default_video_model()
                or MediaGenProviderRegistry.get_first_usable_model("video")
                or ""
            )

        default = self.config.default_image_model
        pool = self.config.image_models or []
        if pool:
            usable = set(MediaGenProviderRegistry.get_usable_model_names("image"))
            if default and default in pool and default in usable:
                return default
            for m in pool:
                if m in usable:
                    return m
            return default if default in pool else pool[0]
        return (
            default
            or MediaGenProviderRegistry.get_default_image_model()
            or MediaGenProviderRegistry.get_first_usable_model("image")
            or ""
        )

    @staticmethod
    def _resolve_media_model(model: str):
        """解析 (protocol, api_key, base_url)。复用工具模块的解析逻辑。"""
        from gyra.agent.tools.builtin.media_gen.media_gen_tools import (
            _resolve_media_model,
        )

        return _resolve_media_model(model)

    def _build_prompt(self, prompt: str) -> str:
        """组装最终 prompt：style_prompt + prompt + scene_prompt。"""
        parts = []
        if self.config.style_prompt:
            parts.append(self.config.style_prompt)
        parts.append(prompt)
        if self.config.scene_prompt:
            parts.append(self.config.scene_prompt)
        return "\n".join(p for p in parts if p)

    def _build_gen_kwargs(
        self, kind: str, request: MultimediaRequest
    ) -> Dict[str, Any]:
        """组装传给 provider 的参数：
        1) config.fixed_params（固定覆盖）
        2) config 输出默认值（尺寸/分辨率/宽高比/时长）
        3) request.params（调用方覆盖，最高优先级）
        """
        kwargs: Dict[str, Any] = dict(self.config.fixed_params or {})

        if kind == KIND_IMAGE:
            kwargs.setdefault("size", self.config.default_image_size)
            if self.config.negative_prompt:
                kwargs.setdefault("negative_prompt", self.config.negative_prompt)
        else:
            kwargs.setdefault("resolution", self.config.default_video_resolution)
            kwargs.setdefault("aspect_ratio", self.config.default_video_aspect_ratio)
            kwargs.setdefault("duration", self.config.default_video_duration)
            if self.config.negative_prompt:
                kwargs.setdefault("negative_prompt", self.config.negative_prompt)

        # 参考图 / 首帧 / 尾帧
        if request.reference_images:
            kwargs["reference_images"] = list(request.reference_images)
        if request.image_url:
            kwargs["image_url"] = request.image_url
        if request.image_url_last:
            kwargs["image_url_last"] = request.image_url_last

        # 请求覆盖（最高优先级），过滤空值
        for k, v in (request.params or {}).items():
            if v is not None and v != "":
                kwargs[k] = v

        return kwargs

    def _resolve_wait(self, wait: Optional[bool]) -> bool:
        """wait 解析：显式 › config.async_default 取反 › 默认同步。"""
        if wait is not None:
            return wait
        return not self.config.async_default

    def _tool_name(self, kind: str) -> str:
        return f"multimedia_{'video' if kind == KIND_VIDEO else 'image'}"

    def name_for(self, kind: str = "") -> str:
        """供 ToolResult.tool_name 使用的稳定名称。"""
        return self._tool_name(kind or "")

    # ------------------------------------------------------------------
    # 持久化任务记录（同步路径镜像：一个请求结果都不能丢）
    # ------------------------------------------------------------------

    async def _register_media_mirror(
        self,
        kind: str,
        model: str,
        final_prompt: str,
        description: str,
        request: MultimediaRequest,
        protocol: str,
        submission: Any = None,
    ) -> Optional[str]:
        """同步生成路径在 AsyncTaskManager 登记持久化任务记录。

        与 _run_async 的 atask 同构（kind/model/description/prompt/provider_task_id
        落 gpts_async_tasks.detail），使 SubAgent 内联轮询等同步生成也有完整
        记录：进程重启可按 provider_task_id 找回结果；在途状态同时供防重复
        守卫（_find_in_flight_media）命中。任何失败返回 None，不影响生成。
        """
        try:
            from gyra.agent.util.async_task_manager import (
                AsyncTaskManager,
                AsyncTaskSpec,
            )

            conv_id = request.conv_id or self.conv_id
            gen_kwargs = (
                {
                    k: v
                    for k, v in (getattr(submission, "metadata", {}) or {}).items()
                    if isinstance(v, (str, int, float, bool))
                }
                if submission is not None
                else {}
            )
            context: Dict[str, Any] = {
                "provider": getattr(submission, "provider", "") or protocol or "",
                "prompt": final_prompt[:2000],
                "gen_kwargs": gen_kwargs,
                "source": "multimedia_sync",
            }
            if self.main_conv_id:
                context["main_conv_id"] = self.main_conv_id
            provider_task_id = getattr(submission, "task_id", "") if submission else ""
            if provider_task_id:
                context["provider_task_id"] = provider_task_id

            task_id = f"atask_{uuid.uuid4().hex[:8]}"
            await AsyncTaskManager.media_instance().register_external(
                AsyncTaskSpec(
                    task_id=task_id,
                    kind=kind,
                    model=model,
                    task_description=description,
                    conv_id=conv_id,
                    context=context,
                )
            )
            logger.info(
                f"[multimedia-executor] registered sync media record {task_id} "
                f"({kind}/{model}, provider_task={provider_task_id or 'pending'})"
            )
            return task_id
        except Exception as e:  # noqa: BLE001 - 记录失败不影响生成主流程
            logger.warning(f"[multimedia-executor] media mirror register failed: {e}")
            return None

    def _complete_media_mirror(
        self,
        mirror_id: Optional[str],
        result: Any = None,
        error: Optional[str] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """回写同步路径任务记录的终态（并标记 consumed，结果已同步交付）。"""
        if not mirror_id:
            return
        try:
            from gyra.agent.util.async_task_manager import AsyncTaskManager

            mgr = AsyncTaskManager.media_instance()
            if extra_context:
                mgr.merge_external_context(mirror_id, extra_context)
            mgr.complete_external(mirror_id, result=result, error=error)
            # 结果已同步交付给调用方，不再需要完成通知注入
            state = mgr.get_status(mirror_id)
            if state is not None:
                state.consumed = True
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[multimedia-executor] media mirror complete failed: {e}")

    # ------------------------------------------------------------------
    # 防重复提交（在途任务复用）
    # ------------------------------------------------------------------

    def _find_in_flight_media(
        self,
        kind: str,
        model: str,
        final_prompt: str,
        request: MultimediaRequest,
    ) -> Any:
        """查找内容相同的在途媒体任务，命中则返回复用该 job 的 PENDING ToolResult。

        dedup key = (conv_id, kind, model, 归一化任务描述)，并用 spec.context 里
        的完整 prompt 做二次校验（任务描述只含 prompt 前 50 字符，可能碰撞）。
        仅进程内存态生效；任何异常都不阻断正常提交。
        """
        try:
            from gyra.agent.tools.result import ResultStatus, ToolResult
            from gyra.agent.util.async_task_manager import (
                AsyncTaskManager,
                normalize_task_text,
            )

            conv_id = request.conv_id or self.conv_id
            description = request.description or (
                f"AI 生成内容: {request.prompt[:50]}"
            )
            state = AsyncTaskManager.media_instance().find_in_flight(
                conv_id=conv_id,
                kind=kind,
                model=model,
                task_description=description,
            )
            if state is None:
                return None
            # 双保险：完整 prompt 也必须一致（spec.context["prompt"] 截断 2000 字）
            stored_prompt = (state.spec.context or {}).get("prompt", "")
            if stored_prompt and normalize_task_text(stored_prompt) != (
                normalize_task_text(final_prompt[:2000])
            ):
                return None

            job_id = state.spec.task_id
            logger.info(
                f"[multimedia-executor] dedup: reuse in-flight job {job_id} "
                f"({kind}/{model}), skip duplicate submit"
            )
            return ToolResult(
                success=True,
                status=ResultStatus.PENDING,
                tool_name=self._tool_name(kind),
                output=(
                    f"同一生成任务已在后台执行中，已复用该任务、"
                    f"未重复提交（不重复扣费）。\n"
                    f"- job_id: {job_id}\n"
                    f"- 模型: {model}\n"
                    f"- 状态: {state.status.value}\n\n"
                    f"完成后会自动通知，请勿重复提交生成请求。"
                ),
                metadata={
                    "job_id": job_id,
                    "model": model,
                    "reused": True,
                    "conv_id": conv_id,
                    "async_task": {
                        "task_id": job_id,
                        "kind": kind,
                        "model": model,
                        "conv_id": conv_id,
                    },
                },
            )
        except Exception as e:  # noqa: BLE001 - 去重失败不阻断正常提交
            logger.warning(f"[multimedia-executor] dedup check failed: {e}")
            return None

    # ------------------------------------------------------------------
    # 异步执行（提交 + 后台轮询下载 + 交付）
    # ------------------------------------------------------------------

    async def _run_async(
        self,
        kind: str,
        model: str,
        prompt: str,
        description: str,
        request: MultimediaRequest,
        submission: Any,
        resumed_after_timeout: str = "",
    ) -> Any:
        """提交异步任务到 AsyncTaskManager，立即返回 PENDING ToolResult。

        Args:
            resumed_after_timeout: 非空表示该任务此前已提交成功、本地轮询超时后
                转后台续等（同一 provider task，不重复提交）；值为原超时信息。
        """
        from gyra.agent.tools.result import ResultStatus, ToolResult
        from gyra.agent.util.async_task_manager import (
            AsyncTaskManager,
            AsyncTaskSpec,
        )

        # 提交阶段上下文必然存活，预先解析 AFS，后台 deliver 复用
        resolved_afs = request.afs or self.afs

        async def _resume():
            return await submission.complete()

        async def _deliver(result):
            fname = f"{self.config.file_prefix}_{uuid.uuid4().hex[:8]}.{result.format}"
            return await self._deliver(
                kind=kind,
                result=result,
                file_name=fname,
                description=description,
                prompt=prompt,
                afs=resolved_afs,
            )

        task_id = "atask_" + uuid.uuid4().hex[:8]
        provider_task_id = getattr(submission, "task_id", "") or ""
        spec = AsyncTaskSpec(
            task_id=task_id,
            conv_id=request.conv_id or self.conv_id,
            kind=kind,
            model=model,
            task_description=description,
            context={
                # 请求侧信息落库（gpts_async_tasks.detail）：重启/中断后可按
                # provider task_id 找回任务与下载地址
                "provider": getattr(submission, "provider", "") or "",
                "provider_task_id": provider_task_id,
                "prompt": prompt[:2000],
                "gen_kwargs": {
                    k: v for k, v in (getattr(submission, "metadata", {}) or {}).items()
                    if isinstance(v, (str, int, float, bool))
                },
                **({"main_conv_id": self.main_conv_id} if self.main_conv_id else {}),
                **({"resumed_after_timeout": resumed_after_timeout} if resumed_after_timeout else {}),
            },
            resume=_resume,
            deliver=_deliver,
            timeout=self.config.timeout,
            poll_hint="~60-180s" if kind == KIND_VIDEO else "~10-60s",
        )
        mgr = AsyncTaskManager.media_instance()
        job_id = await mgr.spawn(spec)

        if resumed_after_timeout:
            note = (
                f"⚠️ 前台等待超时，但生成任务已成功提交、后台仍在继续"
                f"（同一任务，不会重复扣费）。\n"
            )
        else:
            note = ""
        return ToolResult(
            success=True,
            status=ResultStatus.PENDING,
            tool_name=self._tool_name(kind),
            output=(
                f"{note}"
                f"⏳ 已提交{('视频' if kind == KIND_VIDEO else '图片')}"
                f"生成到后台执行。\n"
                f"- job_id: {job_id}\n"
                f"- 模型: {model}\n"
                f"- provider 任务ID: {provider_task_id}\n"
                f"- 预计耗时: {spec.poll_hint}\n\n"
                f"完成后会自动通知，请勿重复提交生成请求。"
            ),
            metadata={
                "job_id": job_id,
                "model": model,
                "conv_id": request.conv_id or self.conv_id,
                "async_task": {
                    "task_id": job_id,
                    "kind": kind,
                    "model": model,
                    "conv_id": request.conv_id or self.conv_id,
                },
            },
        )

    # ------------------------------------------------------------------
    # AFS 交付
    # ------------------------------------------------------------------

    async def _deliver(
        self,
        kind: str,
        result: Any,
        file_name: str,
        description: str,
        prompt: str,
        afs: Any,
    ) -> Any:
        """把生成结果字节经 AFS 落盘并构造带 artifact 的 ToolResult。

        多媒体生成结果始终保存到 AFS 并产出 Artifact（强制交付）。
        """
        from gyra.agent.tools.result import Artifact, ToolResult

        preview_url = None
        dattach_md = ""
        extension = file_name.rsplit(".", 1)[1] if "." in file_name else result.format
        file_key = file_name.rsplit(".", 1)[0]

        # 强制交付：afs 为 None 或保存失败时不得谎报“✅ 成功”
        save_ok = False
        save_error = "afs 不可用(为 None)，未注入文件存储"
        if afs is not None:
            try:
                from gyra.agent.core.memory.gpts.file_base import FileType

                file_metadata = await afs.save_binary_file(
                    file_key=file_key,
                    data=result.data,
                    file_type=FileType.DELIVERABLE,
                    extension=extension,
                    file_name=file_name,
                    tool_name=self._tool_name(kind),
                    is_deliverable=True,
                    description=description,
                    metadata={
                        "file_category": "deliverable",
                        "mime_type": result.mime_type,
                        "prompt": prompt[:200],
                        **(result.metadata or {}),
                    },
                )
                save_ok = True
                if file_metadata:
                    preview_url = file_metadata.preview_url
                    try:
                        from gyra.agent.core.file_system.dattach_utils import (
                            render_dattach,
                        )

                        dattach_md = render_dattach(
                            file_name=file_name,
                            file_url=preview_url or "",
                            file_type="deliverable",
                            object_path=(file_metadata.metadata or {}).get(
                                "object_path"
                            ),
                            preview_url=preview_url,
                            download_url=getattr(file_metadata, "download_url", None)
                            or preview_url,
                            description=description,
                            mime_type=result.mime_type,
                        )
                    except Exception as e:  # noqa: BLE001
                        logger.warning(
                            f"[multimedia-executor] d-attach render failed: {e}"
                        )
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    f"[multimedia-executor] AFS save failed: {e}", exc_info=True
                )
                save_error = str(e)

        # 强制交付：保存未成功(afs 为 None 或 save 抛异常)直接 fail，不输出“✅ 成功”
        if not save_ok:
            label = "图片" if kind == KIND_IMAGE else "视频"
            meta = result.metadata or {}
            raw_url = meta.get("video_url") or meta.get("image_url")
            hint = f"原始链接: {raw_url}" if raw_url else "(无原始链接，内容可能无法恢复)"
            return ToolResult.fail(
                error=f"{label}生成成功但未落盘: {save_error}。{hint}",
                tool_name=self._tool_name(kind),
                # media 元数据（含原始链接/provider task_id）随结果落库，
                # 交付失败也能找回下载地址
                metadata={"media": meta},
            )

        # 组装输出文本
        label = "图片" if kind == KIND_IMAGE else "视频"
        parts = [f"✅ {label}生成成功: {file_name}", f"📋 描述: {description}"]
        meta = result.metadata or {}
        if meta.get("model"):
            parts.append(f"🎨 模型: {meta['model']}")
        if meta.get("provider"):
            parts.append(f"🔌 服务商: {meta['provider']}")
        if kind == KIND_VIDEO and result.duration_seconds:
            parts.append(f"⏱️ 时长: {result.duration_seconds}s")
        if meta.get("resolution"):
            parts.append(f"📐 分辨率: {meta['resolution']}")
        if meta.get("aspect_ratio"):
            parts.append(f"📱 宽高比: {meta['aspect_ratio']}")
        raw_url = meta.get("video_url") or meta.get("image_url")
        if raw_url:
            parts.append(f"🔗 原始链接: {raw_url}")
        if preview_url:
            prefix = "!" if kind == KIND_IMAGE else ""
            parts.append(f"\n{prefix}[{description}]({preview_url})")
        if dattach_md:
            parts.append(f"\n\n**交付文件:**\n{dattach_md}")
        elif preview_url:
            parts.append(f"\n**下载链接:** {preview_url}")

        artifacts = [
            Artifact(
                name=file_name,
                type=kind if kind == KIND_IMAGE else "file",
                url=preview_url,
                mime_type=result.mime_type,
                size=len(result.data),
                metadata=meta,
            )
        ]

        return ToolResult.ok(
            output="\n".join(parts),
            tool_name=self._tool_name(kind),
            artifacts=artifacts,
            # media 元数据（含原始链接/provider task_id）随结果落库
            metadata={"media": meta},
        )


__all__ = [
    "KIND_IMAGE",
    "KIND_VIDEO",
    "MultimediaRequest",
    "MultimediaExecutor",
]
