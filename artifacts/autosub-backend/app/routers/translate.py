import logging
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator
from deep_translator import GoogleTranslator

from app.models.job import JobStatus
from app.utils.srt_translator import translate_srt
from app.config import OUTPUT_DIR
from app import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/translate-srt", tags=["Translation"])


@lru_cache(maxsize=1)
def _supported_languages() -> dict[str, str]:
    """
    Returns {language_name: language_code} e.g. {'spanish': 'es', 'french': 'fr', ...}
    Cached after the first call — GoogleTranslator fetches this from Google once.
    """
    try:
        return GoogleTranslator().get_supported_languages(as_dict=True)  # type: ignore[return-value]
    except Exception:
        logger.warning("Could not fetch supported languages — skipping validation")
        return {}


def _resolve_language_code(value: str) -> str:
    """
    Accept either a language code ('es') or a language name ('spanish').
    Raises ValueError with a helpful message if neither matches.
    """
    supported = _supported_languages()
    if not supported:
        return value

    codes = set(supported.values())
    names = supported

    if value in codes:
        return value

    if value in names:
        return names[value]

    examples = ["es", "fr", "de", "zh-CN", "ar", "ja", "pt", "hi", "ru", "it"]
    raise ValueError(
        f"Unsupported language '{value}'. "
        f"Pass a valid language code (e.g. {', '.join(examples)}) "
        f"or a language name (e.g. 'spanish', 'french'). "
        f"Call GET /languages for the full list."
    )


class TranslateRequest(BaseModel):
    job_id: str
    target_language: str

    @field_validator("target_language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if not cleaned:
            raise ValueError("target_language must not be empty")
        return _resolve_language_code(cleaned)


@router.get("/languages", summary="List all supported translation language codes")
async def list_languages():
    supported = _supported_languages()
    if not supported:
        raise HTTPException(status_code=503, detail="Could not retrieve language list from translation service")
    return {
        "count": len(supported),
        "languages": [
            {"name": name, "code": code}
            for name, code in sorted(supported.items())
        ],
    }


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
            detail=f"Translation failed: {exc}",
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
