from enum import Enum
from typing import Optional
from pydantic import BaseModel


class JobStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    EXTRACTING_AUDIO = "extracting_audio"
    LOADING_MODEL = "loading_model"
    TRANSCRIBING = "transcribing"
    GENERATING_SRT = "generating_srt"
    COMPLETED = "completed"
    FAILED = "failed"


STAGE_LABELS: dict[JobStatus, str] = {
    JobStatus.PENDING: "Pending",
    JobStatus.UPLOADING: "Uploading File",
    JobStatus.EXTRACTING_AUDIO: "Extracting Audio",
    JobStatus.LOADING_MODEL: "Loading AI Model",
    JobStatus.TRANSCRIBING: "Transcribing Audio",
    JobStatus.GENERATING_SRT: "Generating SRT",
    JobStatus.COMPLETED: "Completed",
    JobStatus.FAILED: "Failed",
}

STAGE_PROGRESS: dict[JobStatus, int] = {
    JobStatus.PENDING: 0,
    JobStatus.UPLOADING: 5,
    JobStatus.EXTRACTING_AUDIO: 20,
    JobStatus.LOADING_MODEL: 35,
    JobStatus.TRANSCRIBING: 80,
    JobStatus.GENERATING_SRT: 90,
    JobStatus.COMPLETED: 100,
    JobStatus.FAILED: 0,
}


class Job(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.PENDING
    progress: int = 0
    stage_label: str = "Pending"
    original_filename: str = ""
    upload_path: Optional[str] = None
    audio_path: Optional[str] = None
    srt_path: Optional[str] = None
    error: Optional[str] = None
    language: Optional[str] = None


class UploadResponse(BaseModel):
    job_id: str
    filename: str
    message: str


class GenerateRequest(BaseModel):
    job_id: str


class GenerateResponse(BaseModel):
    job_id: str
    message: str


class StatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    stage_label: str
    language: Optional[str] = None
    error: Optional[str] = None
