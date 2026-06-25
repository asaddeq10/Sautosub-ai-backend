import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator

from app.models.job import JobStatus
from app.utils.srt_translator import translate_srt
from app.config import OUTPUT_DIR
from app import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/translate-srt", tags=["Translation"])


class TranslateRequest(BaseModel):
    job_id: str
    target_language: str

    @field_validator("target_language")
    @classmethod
    def normalise_language(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if not cleaned:
            raise ValueError("target_language must not be empty")
        return cleaned


@router.post("", summary="Translate a completed SRT file to a target language")
async def translate_srt_endpoint(payload: TranslateRequest):
    job = store.get_job(payload.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{payload.job_id}' not found")

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Job is not complete yet. Current status: {job.stage_label}",
        )

    if job.srt_path is None or not Path(job.srt_path).exists():
        raise HTTPException(status_code=404, detail="Original SRT file not found on server")

    logger.info(
        "[job=%s] Translation requested — target_language=%s",
        payload.job_id,
        payload.target_language,
    )

    try:
        original_content = Path(job.srt_path).read_text(encoding="utf-8")
        translated_content = translate_srt(original_content, payload.target_language)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("[job=%s] Translation failed", payload.job_id)
        raise HTTPException(
            status_code=502,
            detail=f"Translation failed: {exc}. Check that the language code is valid.",
        )

    translated_path = OUTPUT_DIR / f"{payload.job_id}_{payload.target_language}.srt"
    translated_path.write_text(translated_content, encoding="utf-8")
    logger.info("[job=%s] Translated SRT saved to %s", payload.job_id, translated_path)

    original_stem = Path(job.original_filename).stem if job.original_filename else payload.job_id
    download_name = f"{original_stem}_{payload.target_language}.srt"

    return FileResponse(
        path=str(translated_path),
        media_type="text/plain; charset=utf-8",
        filename=download_name,
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
    )
