import logging
import shutil
from pathlib import Path

from fastapi import UploadFile, HTTPException

from app.config import UPLOAD_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def validate_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )
    return suffix


async def save_upload(file: UploadFile, job_id: str) -> str:
    suffix = validate_extension(file.filename or "")
    dest_path = UPLOAD_DIR / f"{job_id}{suffix}"

    total_bytes = 0
    try:
        with open(dest_path, "wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_FILE_SIZE_BYTES:
                    out.close()
                    dest_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds maximum size of {MAX_FILE_SIZE_MB} MB",
                    )
                out.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to save uploaded file")
        dest_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Failed to save file") from exc

    logger.info("Saved upload %s (%d bytes) → %s", file.filename, total_bytes, dest_path)
    return str(dest_path)


def cleanup_job_files(upload_path: str | None, audio_path: str | None) -> None:
    for path in (upload_path, audio_path):
        if path:
            p = Path(path)
            if p.exists():
                p.unlink()
                logger.debug("Deleted temp file %s", path)
