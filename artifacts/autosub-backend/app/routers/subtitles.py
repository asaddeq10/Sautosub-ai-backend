import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.models.job import GenerateRequest, GenerateResponse, JobStatus, STAGE_LABELS, STAGE_PROGRESS
from app.services.audio_service import extract_audio
from app.services.transcription_service import transcribe
from app.services.file_service import cleanup_job_files
from app.utils.srt_generator import segments_to_srt, save_srt
from app.config import OUTPUT_DIR
from app import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate-subtitles", tags=["Subtitles"])

_executor = ThreadPoolExecutor(max_workers=2)


def _process_job(job_id: str) -> None:
    def _update(status: JobStatus, **extra):
        store.update_job(
            job_id,
            status=status,
            progress=STAGE_PROGRESS[status],
            stage_label=STAGE_LABELS[status],
            **extra,
        )
        logger.info(
            "[job=%s] Stage: %s (%d%%)",
            job_id,
            STAGE_LABELS[status],
            STAGE_PROGRESS[status],
        )

    job = store.get_job(job_id)
    if job is None:
        logger.error("[job=%s] Not found in store — cannot process", job_id)
        return

    upload_path = job.upload_path
    audio_path: str | None = None

    try:
        logger.info("[job=%s] Pipeline starting — file: %s", job_id, job.original_filename)

        _update(JobStatus.EXTRACTING_AUDIO)
        audio_path = extract_audio(upload_path, job_id)
        logger.info("[job=%s] Audio ready at %s", job_id, audio_path)

        _update(JobStatus.LOADING_MODEL)
        logger.info("[job=%s] Whisper model requested", job_id)

        _update(JobStatus.TRANSCRIBING)
        logger.info("[job=%s] Transcription starting", job_id)
        segments, language = transcribe(audio_path)
        logger.info("[job=%s] Transcription done — %d segments, language=%s", job_id, len(segments), language)

        _update(JobStatus.GENERATING_SRT, language=language)
        srt_content = segments_to_srt(segments)
        srt_path = str(OUTPUT_DIR / f"{job_id}.srt")
        save_srt(srt_content, srt_path)
        logger.info("[job=%s] SRT written to %s", job_id, srt_path)

        cleanup_job_files(upload_path, audio_path if audio_path != upload_path else None)
        logger.info("[job=%s] Temporary files cleaned up", job_id)

        _update(JobStatus.COMPLETED, srt_path=srt_path, language=language)
        logger.info("[job=%s] Completed successfully", job_id)

    except Exception as exc:
        logger.exception("[job=%s] Pipeline failed: %s", job_id, exc)
        store.update_job(
            job_id,
            status=JobStatus.FAILED,
            progress=0,
            stage_label="Failed",
            error=str(exc),
        )


async def _run_job_in_background(job_id: str) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(_executor, _process_job, job_id)


@router.post("", response_model=GenerateResponse, summary="Start subtitle generation for a job")
async def generate_subtitles(payload: GenerateRequest, background_tasks: BackgroundTasks):
    job = store.get_job(payload.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{payload.job_id}' not found")

    active_statuses = (
        JobStatus.EXTRACTING_AUDIO,
        JobStatus.LOADING_MODEL,
        JobStatus.TRANSCRIBING,
        JobStatus.GENERATING_SRT,
    )
    if job.status in active_statuses:
        raise HTTPException(status_code=409, detail="Job is already being processed")

    if job.status == JobStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="Job already completed — download your SRT file")

    if job.upload_path is None:
        raise HTTPException(status_code=400, detail="No uploaded file associated with this job")

    logger.info("[job=%s] Queuing background processing", payload.job_id)
    background_tasks.add_task(_run_job_in_background, payload.job_id)

    return GenerateResponse(
        job_id=payload.job_id,
        message="Processing started. Poll GET /status/{job_id} to track progress.",
    )
