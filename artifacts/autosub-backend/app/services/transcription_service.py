import logging
from typing import Any

from faster_whisper import WhisperModel

from app.config import WHISPER_MODEL_SIZE, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE

logger = logging.getLogger(__name__)

_model: WhisperModel | None = None


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        logger.info(
            "Loading Faster-Whisper model '%s' on device=%s compute=%s",
            WHISPER_MODEL_SIZE, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE,
        )
        _model = WhisperModel(
            WHISPER_MODEL_SIZE,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )
        logger.info("Model loaded successfully")
    return _model


def transcribe(audio_path: str) -> tuple[list[Any], str]:
    model = get_model()
    logger.info("Starting transcription for %s", audio_path)

    segments_gen, info = model.transcribe(
        audio_path,
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )

    detected_language = info.language
    logger.info("Detected language: %s (probability %.2f)", detected_language, info.language_probability)

    segments = list(segments_gen)
    logger.info("Transcription complete — %d segments", len(segments))
    return segments, detected_language
