import logging
import subprocess
from pathlib import Path

from app.config import UPLOAD_DIR

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi"}


def is_video(file_path: str) -> bool:
    return Path(file_path).suffix.lower() in VIDEO_EXTENSIONS


def extract_audio(upload_path: str, job_id: str) -> str:
    if not is_video(upload_path):
        logger.info("File is audio — skipping FFmpeg extraction")
        return upload_path

    audio_path = str(UPLOAD_DIR / f"{job_id}_audio.wav")
    command = [
        "ffmpeg",
        "-y",
        "-i", upload_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        audio_path,
    ]

    logger.info("Extracting audio: %s", " ".join(command))
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            logger.error("FFmpeg stderr: %s", result.stderr)
            raise RuntimeError(f"FFmpeg failed with code {result.returncode}: {result.stderr[-500:]}")
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("FFmpeg timed out after 5 minutes") from exc

    logger.info("Audio extracted to %s", audio_path)
    return audio_path
