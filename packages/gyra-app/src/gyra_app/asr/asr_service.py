import os
import tempfile
from typing import Optional

_WHISPER_MODELS: dict = {}


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _audio_ext(mime: Optional[str]) -> str:
    mime = (mime or "").split(";")[0].strip().lower()
    return {
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/ogg": ".ogg",
        "audio/mp4": ".mp4",
        "audio/m4a": ".m4a",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/webm": ".webm",
    }.get(mime, ".webm")


def _normalize_lang(lang: Optional[str]) -> Optional[str]:
    if not lang:
        return None
    return lang.split("-")[0].strip().lower() or None


def _transcribe_local_whisper(data: bytes, lang: Optional[str]) -> str:
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise RuntimeError("未安装 faster-whisper，请执行 pip install faster-whisper") from e

    model_name = _env("GYRA_ASR_WHISPER_MODEL", "small") or "small"
    device = _env("GYRA_ASR_WHISPER_DEVICE", "auto") or "auto"
    compute_type = _env("GYRA_ASR_WHISPER_COMPUTE_TYPE", "int8") or "int8"

    cache_key = (model_name, device, compute_type)
    model = _WHISPER_MODELS.get(cache_key)
    if model is None:
        model = WhisperModel(model_name, device=device, compute_type=compute_type)
        _WHISPER_MODELS[cache_key] = model

    tmp_path = ""
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".webm")
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        segments, _ = model.transcribe(
            tmp_path,
            language=_normalize_lang(lang),
            beam_size=5,
        )
        text = "".join(seg.text for seg in segments).strip()
        return text
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _transcribe_openai_compatible(data: bytes, lang: Optional[str], mime: Optional[str]) -> str:
    try:
        import httpx
    except ImportError as e:
        raise RuntimeError("未安装 httpx，请执行 pip install httpx") from e

    base_url = _env("GYRA_ASR_OPENAI_BASE_URL")
    api_key = _env("GYRA_ASR_OPENAI_API_KEY")
    model = _env("GYRA_ASR_OPENAI_MODEL", "whisper-1") or "whisper-1"
    if not base_url or not api_key:
        raise RuntimeError("openai 引擎缺少 GYRA_ASR_OPENAI_BASE_URL / GYRA_ASR_OPENAI_API_KEY 配置")

    url = base_url.rstrip("/") + "/audio/transcriptions"
    filename = "audio" + _audio_ext(mime)
    data_map: dict = {"model": model}
    normalized = _normalize_lang(lang)
    if normalized:
        data_map["language"] = normalized

    resp = httpx.post(
        url,
        headers={"Authorization": f"Bearer {api_key}"},
        files={"file": (filename, data, mime or "audio/webm")},
        data=data_map,
        timeout=120.0,
    )
    resp.raise_for_status()
    payload = resp.json()
    return (payload.get("text") or "").strip()


def transcribe_audio(data: bytes, lang: Optional[str] = None, mime: Optional[str] = None) -> str:
    provider = (_env("GYRA_ASR_PROVIDER", "auto") or "auto").lower()

    if provider in ("auto", "whisper"):
        try:
            text = _transcribe_local_whisper(data, lang)
            if text:
                return text
        except Exception as e:
            if provider == "whisper":
                raise RuntimeError(f"本地语音识别失败: {e}") from e

    if provider in ("auto", "openai"):
        text = _transcribe_openai_compatible(data, lang, mime)
        if text:
            return text

    raise RuntimeError("未返回识别结果，请检查语音识别引擎配置")
