from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile
from starlette.responses import JSONResponse

from gyra.util.executor_utils import blocking_func_to_async

from gyra_app.asr.asr_service import transcribe_audio

router = APIRouter()


@router.post("/v2/serve/asr/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    lang: Optional[str] = Form(None),
):
    data = await file.read()
    if not data:
        return JSONResponse(
            status_code=200,
            content={"data": None, "err_code": None, "err_msg": "音频内容为空", "success": False},
        )
    try:
        text = await blocking_func_to_async(
            None, transcribe_audio, data, lang, file.content_type
        )
    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={"data": None, "err_code": None, "err_msg": str(e), "success": False},
        )
    return {"data": {"text": text}, "err_code": None, "err_msg": None, "success": True}
