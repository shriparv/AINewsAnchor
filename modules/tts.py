import edge_tts
import json
import os
import asyncio
import logging
from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)

# =========================
# CONFIG
# =========================
AUDIO_DIR = "output/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# Maps detected language → best Edge TTS voice
VOICE_MAP = {
    "en": "en-IN-NeerjaNeural",
    "hi": "hi-IN-SwaraNeural",
    "fr": "fr-FR-DeniseNeural",
    "de": "de-DE-KatjaNeural",
    "es": "es-ES-ElviraNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
    "ar": "ar-SA-ZariyahNeural",
    "ja": "ja-JP-NanamiNeural",
}

DEFAULT_VOICE = "en-US-JennyNeural"

# Style options per language (only Neural voices with mstts:express-as support)
STYLE_MAP = {
    "en": "newscast",
    "hi": None,   # hi-IN-SwaraNeural doesn't support express-as
    "zh": "newscast",
}

# =========================
# VOICE SELECTION
# =========================
def pick_voice(text: str) -> tuple[str, str | None]:
    """
    Detect language from text and return (voice, style).
    Falls back to default English voice if detection fails.
    """
    try:
        lang = detect(text)
    except LangDetectException:
        logger.warning("Language detection failed, falling back to English.")
        lang = "en"

    voice = VOICE_MAP.get(lang, DEFAULT_VOICE)
    style = STYLE_MAP.get(lang, None)   # Only apply style if supported
    return voice, style



# =========================
# ASYNC CORE FUNCTION
# =========================
async def generate_tts(text: str, index: int) -> tuple[str, str]:
    """
    Async function that:
    - Picks voice + style based on detected language
    - Configures edge_tts rate and pitch
    - Streams audio chunks to .mp3
    - Captures word boundary timings to .json

    Returns:
        (audio_path, json_path)
    """
    if not text or not text.strip():
        raise ValueError(f"Empty text passed for index {index}.")

    voice, style = pick_voice(text)
    logger.info(f"[{index}] Voice: {voice} | Style: {style} (Ignored by edge-tts plain text API)")

    audio_path = os.path.join(AUDIO_DIR, f"audio_{index}.mp3")
    json_path  = os.path.join(AUDIO_DIR, f"audio_{index}.json")

    # Pass plain text and configure parameters directly, so it does not read SSML out loud
    communicate = edge_tts.Communicate(text, voice=voice, rate="-5%", pitch="-2Hz")

    word_timings = []
    audio_chunks  = []

    try:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])

            elif chunk["type"] == "WordBoundary":
                word_timings.append({
                    "word":     chunk["text"],
                    "start":    round(chunk["offset"]  / 1e7, 4),  # Convert to seconds
                    "duration": round(chunk["duration"] / 1e7, 4),
                    "end":      round((chunk["offset"] + chunk["duration"]) / 1e7, 4),
                })

    except Exception as e:
        raise RuntimeError(f"TTS streaming failed for index {index}: {e}") from e

    if not audio_chunks:
        raise RuntimeError(f"No audio data received for index {index}. Check SSML or voice name.")

    # Write audio only after successful stream (avoids corrupt partial files)
    with open(audio_path, "wb") as f:
        for chunk in audio_chunks:
            f.write(chunk)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(word_timings, f, indent=2, ensure_ascii=False)

    logger.info(f"[{index}] Saved: {audio_path} | Words captured: {len(word_timings)}")
    return audio_path, json_path


# =========================
# SYNC WRAPPER
# =========================
def generate_audio(text: str, index: int) -> str:
    """Synchronous wrapper around generate_tts. Returns audio file path."""
    audio_path, _ = asyncio.run(generate_tts(text, index))
    return audio_path


def generate_audio_with_timings(text: str, index: int) -> tuple[str, str]:
    """Synchronous wrapper that returns both audio path and word timings JSON path."""
    return asyncio.run(generate_tts(text, index))