import logging
from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)

MAX_CHARS_PER_CALL = 4500


def _parse_srt(content: str) -> list[dict]:
    blocks = content.strip().split("\n\n")
    segments = []
    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue
        try:
            index = lines[0].strip()
            timestamp = lines[1].strip()
            text = "\n".join(lines[2:]).strip()
            segments.append({"index": index, "timestamp": timestamp, "text": text})
        except Exception:
            continue
    return segments


def _reassemble_srt(segments: list[dict]) -> str:
    blocks = []
    for seg in segments:
        blocks.append(f"{seg['index']}\n{seg['timestamp']}\n{seg['text']}")
    return "\n\n".join(blocks) + "\n"


def _translate_texts(texts: list[str], target_language: str) -> list[str]:
    translator = GoogleTranslator(source="auto", target=target_language)
    results: list[str] = []
    batch: list[str] = []
    batch_indices: list[int] = []
    translated_map: dict[int, str] = {}

    for i, text in enumerate(texts):
        if len(text) > MAX_CHARS_PER_CALL:
            # Translate oversized segment individually, truncated if needed
            logger.warning("Segment %d exceeds max chars — truncating for translation", i)
            translated_map[i] = translator.translate(text[:MAX_CHARS_PER_CALL])
        else:
            batch.append(text)
            batch_indices.append(i)

    if batch:
        try:
            batch_result = translator.translate_batch(batch)
            for idx, translated in zip(batch_indices, batch_result):
                translated_map[idx] = translated or texts[idx]
        except Exception as exc:
            logger.error("Batch translation failed, falling back to per-segment: %s", exc)
            for idx, text in zip(batch_indices, batch):
                try:
                    translated_map[idx] = translator.translate(text) or text
                except Exception:
                    translated_map[idx] = text

    for i in range(len(texts)):
        results.append(translated_map.get(i, texts[i]))

    return results


def translate_srt(srt_content: str, target_language: str) -> str:
    logger.info("Translating SRT to '%s'", target_language)
    segments = _parse_srt(srt_content)
    if not segments:
        raise ValueError("SRT file is empty or could not be parsed")

    texts = [seg["text"] for seg in segments]
    translated_texts = _translate_texts(texts, target_language)

    for seg, translated in zip(segments, translated_texts):
        seg["text"] = translated

    result = _reassemble_srt(segments)
    logger.info("Translation complete — %d segments", len(segments))
    return result
