import logging
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.models.job import Job, JobStatus, STAGE_LABELS, STAGE_PROGRESS, UploadResponse
from app.services.file_service import save_upload
from app import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["Upload"])


@router.post("", response_model=UploadResponse, summary="Upload audio or video file")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    job_id = str(uuid.uuid4())

    job = Job(
        job_id=job_id,
        status=JobStatus.UPLOADING,
        progress=STAGE_PROGRESS[JobStatus.UPLOADING],
        stage_label=STAGE_LABELS[JobStatus.UPLOADING],
        original_filename=file.filename,
    )
    store.set_job(job)
    logger.info("Created job %s for file %s", job_id, file.filename)

    upload_path = await save_upload(file, job_id)

    store.update_job(
        job_id,
        upload_path=upload_path,
        status=JobStatus.PENDING,
        progress=STAGE_PROGRESS[JobStatus.PENDING],
        stage_label="Upload complete — ready to process",
    )

    return UploadResponse(
        job_id=job_id,
        filename=file.filename,
        message="File uploaded successfully. Call POST /generate-subtitles to start processing.",
    )
