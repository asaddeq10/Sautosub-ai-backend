import logging
from typing import Any

logger = logging.getLogger(__name__)


def format_timestamp(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds % 1) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def segments_to_srt(segments: list[Any]) -> str:
    lines: list[str] = []
    for index, segment in enumerate(segments, start=1):
        start = format_timestamp(segment.start)
        end = format_timestamp(segment.end)
        text = segment.text.strip()
        lines.append(f"{index}")
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def save_srt(content: str, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info("SRT file saved to %s", path)
