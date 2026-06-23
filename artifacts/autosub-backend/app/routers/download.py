import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.models.job import JobStatus
from app import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/download", tags=["Download"])


@router.get("/{job_id}", summary="Download the generated SRT file")
async def download_srt(job_id: str):
    job = store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Job is not complete yet. Current status: {job.stage_label}",
        )

    if job.srt_path is None or not Path(job.srt_path).exists():
        raise HTTPException(status_code=404, detail="SRT file not found on server")

    original_stem = Path(job.original_filename).stem if job.original_filename else job_id
    download_name = f"{original_stem}.srt"

    logger.info("Serving SRT download for job %s → %s", job_id, download_name)
    return FileResponse(
        path=job.srt_path,
        media_type="text/plain; charset=utf-8",
        filename=download_name,
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
    )
