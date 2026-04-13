import logging
import requests
import os
import json
import asyncio
from langdetect import detect, LangDetectException
from config import TTS_PROVIDER, OPENAI_API_KEY, ELEVENLABS_API_KEY, TTS_VOICE_OPENAI, TTS_VOICE_ELEVEN, TTS_VOICE_KOKORO, TTS_VOICE_PIPER

logger = logging.getLogger(__name__)

# =========================
# CONFIG
# =========================
AUDIO_DIR = "output/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# Tracks providers that have hit quota/errors in the current session
DISABLED_PROVIDERS = set()

# Cache for the Kokoro Pipeline singleton
K_PIPELINE = None

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

DEFAULT_VOICE = "en-IN-NeerjaNeural"

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
# PROVIDER-SPECIFIC LOGIC
# =========================

async def generate_edge_tts(text: str, voice: str, audio_path: str, json_path: str):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice=voice, rate="-5%", pitch="-2Hz")
    word_timings = []
    audio_chunks = []

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            word_timings.append({
                "word": chunk["text"],
                "start": round(chunk["offset"] / 1e7, 4),
                "duration": round(chunk["duration"] / 1e7, 4),
                "end": round((chunk["offset"] + chunk["duration"]) / 1e7, 4),
            })

    with open(audio_path, "wb") as f:
        for chunk in audio_chunks:
            f.write(chunk)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(word_timings, f, indent=2, ensure_ascii=False)

async def generate_openai_tts(text: str, audio_path: str):
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    response = await client.audio.speech.create(
        model="tts-1",
        voice=TTS_VOICE_OPENAI,
        input=text
    )
    await response.astream_to_file(audio_path)

async def generate_elevenlabs_tts(text: str, audio_path: str):
    # We use direct request to avoid bloated dependencies in simple scripts
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{TTS_VOICE_ELEVEN}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8,
            "style": 0.0,
            "use_speaker_boost": True
        }
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        with open(audio_path, "wb") as f:
            f.write(response.content)
    else:
        raise RuntimeError(f"ElevenLabs API Error: {response.status_code} - {response.text}")

async def generate_kokoro_tts(text: str, voice: str, audio_path: str):
    """Generates audio locally using the Kokoro TTS engine."""
    global K_PIPELINE
    import soundfile as sf
    from kokoro import KPipeline
    
    # Lazy initialisation of the pipeline (singleton)
    if K_PIPELINE is None:
        logger.info("⚡ Loading Kokoro TTS Pipeline (this occurs once per session)...")
        # 'a' = American English, 'b' = British English
        import torch
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        logger.info(f"Kokoro utilizing device: {device.upper()}")
        K_PIPELINE = KPipeline(lang_code='a', device=device) 

    # Generate audio chunks
    generator = K_PIPELINE(text, voice=voice, speed=1.0)
    
    audio_segments = []
    for _, _, audio in generator:
        audio_segments.append(audio)
    
    if not audio_segments:
        raise RuntimeError("Kokoro failed to generate any audio segments.")
    
    # Stitch segments together (Kokoro returns numpy arrays)
    import numpy as np
    full_audio = np.concatenate(audio_segments)
    
    # Save as .wav first (or directly to output path if soundfile supports it)
    # Output path in main is .mp3, but soundfile can write to it if formatted correctly, 
    # though usually we use .wav for local high-quality and then optionally convert.
    # We'll save it to the requested path (24000Hz is Kokoro's default)
    sf.write(audio_path, full_audio, 24000)
    logger.info(f"✅ Kokoro audio saved to {audio_path}")

async def generate_piper_tts(text: str, voice_name: str, audio_path: str):
    import wave
    from piper import PiperVoice
    
    model_dir = "output/piper_models"
    os.makedirs(model_dir, exist_ok=True)
    
    model_path = os.path.join(model_dir, f"{voice_name}.onnx")
    config_path = model_path + ".json"
    
    if not os.path.exists(model_path):
        if voice_name == "en_US-lessac-medium":
            logger.info("Downloading Piper TTS model (one time)...")
            open(model_path, "wb").write(requests.get("https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx").content)
            open(config_path, "wb").write(requests.get("https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json").content)
        else:
            raise RuntimeError(f"Piper model {voice_name} not found locally at {model_path}. Please download it manually.")

    try:
        import torch
        use_cuda = torch.cuda.is_available()
    except ImportError:
        use_cuda = False

    try:
        voice = PiperVoice.load(model_path, config_path=config_path, use_cuda=use_cuda)
    except Exception as e:
        logger.warning(f"Piper CUDA initialization failed ({e}). Falling back to CPU.")
        voice = PiperVoice.load(model_path, config_path=config_path, use_cuda=False)

    with wave.open(audio_path, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)

# =========================
# MAIN ENTRY POINT
# =========================
async def generate_tts(text: str, index: int) -> tuple[str, str]:
    if not text or not text.strip():
        raise ValueError(f"Empty text passed for index {index}.")

    audio_path = os.path.join(AUDIO_DIR, f"audio_{index}.mp3")
    json_path  = os.path.join(AUDIO_DIR, f"audio_{index}.json")

    provider = TTS_PROVIDER.lower()
    
    # 🚨 Dynamic Session Fallback: If a provider is "broken" for this run, skip it entirely
    if provider in DISABLED_PROVIDERS:
        # Silently switch to edge to avoid repeated error noise
        provider = "edge"

    # Fallback to Edge if API keys are missing
    if provider == "openai" and not OPENAI_API_KEY:
        logger.warning("OpenAI API key missing. Falling back to Edge TTS.")
        provider = "edge"
    if provider == "eleven" and not ELEVENLABS_API_KEY:
        logger.warning("ElevenLabs API key missing. Falling back to Edge TTS.")
        provider = "edge"

    try:
        if provider == "openai":
            logger.info(f"[{index}] Generating OpenAI TTS ({TTS_VOICE_OPENAI})...")
            await generate_openai_tts(text, audio_path)
            # Create a dummy JSON if word timings aren't supported by provider
            with open(json_path, "w") as f: json.dump([], f)
            
        elif provider == "eleven":
            logger.info(f"[{index}] Generating ElevenLabs TTS ({TTS_VOICE_ELEVEN})...")
            await generate_elevenlabs_tts(text, audio_path)
            with open(json_path, "w") as f: json.dump([], f)
            
        elif provider == "kokoro":
            print(f"🎙️ [{index}] Generating Kokoro Local TTS ({TTS_VOICE_KOKORO})...")
            await generate_kokoro_tts(text, TTS_VOICE_KOKORO, audio_path)
            with open(json_path, "w") as f: json.dump([], f)
            
        elif provider == "piper":
            print(f"🎙️ [{index}] Generating Piper TTS ({TTS_VOICE_PIPER})...")
            await generate_piper_tts(text, TTS_VOICE_PIPER, audio_path)
            with open(json_path, "w") as f: json.dump([], f)

        else: # Default/Edge
            voice, _ = pick_voice(text)
            logger.info(f"[{index}] Generating Edge TTS ({voice})...")
            await generate_edge_tts(text, voice, audio_path, json_path)

    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"TTS Generation failed for {provider}: {e}")

        # Check for permanent account/quota issues to disable provider for the rest of the session
        if "insufficient_quota" in error_msg or "quota exceeded" in error_msg or "429" in error_msg:
            logger.warning(f"🏁 Provider '{provider}' looks exhausted. Disabling for the rest of this run.")
            DISABLED_PROVIDERS.add(provider)

        # Final fallback to Edge if something went wrong with paid providers
        if provider != "edge":
            logger.info(f"[{index}] Emergency fallback to Edge TTS...")
            voice, _ = pick_voice(text)
            await generate_edge_tts(text, voice, audio_path, json_path)
        else:
            raise

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