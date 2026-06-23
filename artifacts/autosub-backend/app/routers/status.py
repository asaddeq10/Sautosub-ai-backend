import logging

from fastapi import APIRouter, HTTPException

from app.models.job import StatusResponse
from app import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/status", tags=["Status"])


@router.get("/{job_id}", response_model=StatusResponse, summary="Get processing status for a job")
async def get_status(job_id: str):
    job = store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    return StatusResponse(
        job_id=job.job_id,
        status=job.status.value,
        progress=job.progress,
        stage_label=job.stage_label,
        language=job.language,
        error=job.error,
    )
