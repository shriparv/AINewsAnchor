import logging
import requests
import os
import json
import asyncio
import random
from langdetect import detect, LangDetectException
from config import (
    TTS_PROVIDER,
    TTS_VOICE_KOKORO, TTS_VOICE_PIPER, TTS_VOICE_EDGE,
    RANDOMIZE_VOICE, RANDOM_VOICE_POOL
)

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

# =========================
# VOICE OPTIONS
# =========================
# Full 10 specified Kokoro voices
VOICES_KOKORO = ["af_heart", "af_bella", "af_nicole", "af_sarah", "am_adam", "am_michael", "bf_alice", "bf_emma", "bm_george", "bm_lewis"]

# Full 9 specified Piper voices
VOICES_PIPER = [
    "en_US-amy-low", "en_US-amy-medium", "en_US-amy-high",
    "en_US-lessac-low", "en_US-lessac-medium", "en_US-lessac-high",
    "en_US-ryan-low", "en_US-ryan-medium", "en_US-ryan-high"
]
VOICES_EDGE = ["en-US-AvaNeural", "en-US-AndrewNeural", "en-US-EmmaNeural", "en-US-BrianNeural", "en-US-SteffanNeural", "en-US-SoniaNeural"]

def get_random_voice(provider=None):
    """Returns a random voice for the current or specified provider."""
    # Priority 1: User's custom pool
    if RANDOMIZE_VOICE and RANDOM_VOICE_POOL:
        return random.choice(RANDOM_VOICE_POOL)
        
    p = (provider or TTS_PROVIDER).lower()
    if p == "kokoro": return random.choice(VOICES_KOKORO)
    if p == "piper": return random.choice(VOICES_PIPER)
    if p == "edge": return random.choice(VOICES_EDGE)
    return None

def detect_provider(voice_name: str) -> str:
    """Intelligently detects which TTS provider to use for a given voice name."""
    v = voice_name.lower()
    if any(prefix in v for prefix in ["af_", "am_", "bf_", "bm_"]):
        return "kokoro"
    if "neural" in v:
        return "edge"
    if "en_us-" in v or "-low" in v or "-medium" in v or "-high" in v:
        return "piper"
    return TTS_PROVIDER.lower()

# =========================
# PROVIDER-SPECIFIC LOGIC
# =========================

async def generate_edge_tts(text: str, voice: str, audio_path: str, json_path: str):
    import edge_tts
    # Use the provided voice or fallback to a default
    v = voice or "en-US-AvaNeural"
    communicate = edge_tts.Communicate(text, voice=v, rate="-5%", pitch="-2Hz")
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

async def generate_kokoro_tts(text: str, voice: str, audio_path: str):
    """Generates audio locally using the Kokoro TTS engine."""
    global K_PIPELINE
    import soundfile as sf
    from kokoro import KPipeline
    
    if K_PIPELINE is None:
        logger.info("⚡ Loading Kokoro TTS Pipeline...")
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
        import torch
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"🖥️  Kokoro TTS Engine is using: {device.upper()}")
        K_PIPELINE = KPipeline(lang_code='a', device=device, repo_id='hexgrad/Kokoro-82M') 

    generator = K_PIPELINE(text, voice=voice, speed=1.0)
    audio_segments = []
    for _, _, audio in generator:
        audio_segments.append(audio)
    
    if not audio_segments:
        raise RuntimeError("Kokoro failed to generate any audio segments.")
    
    import numpy as np
    full_audio = np.concatenate(audio_segments)
    sf.write(audio_path, full_audio, 24000)

async def generate_piper_tts(text: str, voice_name: str, audio_path: str):
    import wave
    from piper import PiperVoice
    
    model_dir = "output/piper_models"
    os.makedirs(model_dir, exist_ok=True)
    
    model_path = os.path.join(model_dir, f"{voice_name}.onnx")
    config_path = model_path + ".json"
    
    # Dynamic Piper Downloader
    if not os.path.exists(model_path):
        # Format: en_US-name-quality
        parts = voice_name.split("-")
        if len(parts) >= 3:
            name = parts[1]
            quality = parts[2]
            base_url = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/{name}/{quality}/{voice_name}.onnx"
            
            print(f"📥 Downloading Piper model: {voice_name}...")
            onnx_res = requests.get(base_url)
            json_res = requests.get(base_url + ".json")
            
            if onnx_res.status_code == 200:
                with open(model_path, "wb") as f: f.write(onnx_res.content)
                with open(config_path, "wb") as f: f.write(json_res.content)
            else:
                raise RuntimeError(f"Failed to download Piper model: {voice_name} from {base_url}")

    try:
        import torch
        use_cuda = torch.cuda.is_available()
        print(f"🖥️  Piper TTS Engine is using: {'GPU (CUDA)' if use_cuda else 'CPU'}")
    except ImportError:
        use_cuda = False
        print("🖥️  Piper TTS Engine is using: CPU (Torch not found)")

    voice = PiperVoice.load(model_path, config_path=config_path, use_cuda=use_cuda)
    with wave.open(audio_path, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)

# =========================
# MAIN ENTRY POINT
# =========================
async def generate_tts(text: str, index: int, voice_override: str = None) -> tuple[str, str]:
    if not text or not text.strip():
        raise ValueError(f"Empty text passed for index {index}.")

    audio_path = os.path.join(AUDIO_DIR, f"audio_{index}.mp3")
    json_path  = os.path.join(AUDIO_DIR, f"audio_{index}.json")

    # If a specific voice is passed, detect its provider automatically
    if voice_override:
        provider = detect_provider(voice_override)
        voice = voice_override
    else:
        provider = TTS_PROVIDER.lower()
        if RANDOMIZE_VOICE and RANDOM_VOICE_POOL:
            voice = random.choice(RANDOM_VOICE_POOL)
            provider = detect_provider(voice)
        elif RANDOMIZE_VOICE:
            voice = get_random_voice(provider)
        else:
            if provider == "kokoro": voice = TTS_VOICE_KOKORO
            elif provider == "piper": voice = TTS_VOICE_PIPER
            else: voice = TTS_VOICE_EDGE

    try:
        if provider == "kokoro":
            print(f"🎙️ [{index}] Generating Kokoro Local TTS ({voice})...")
            await generate_kokoro_tts(text, voice, audio_path)
            with open(json_path, "w") as f: json.dump([], f)
            
        elif provider == "piper":
            print(f"🎙️ [{index}] Generating Piper TTS ({voice})...")
            await generate_piper_tts(text, voice, audio_path)
            with open(json_path, "w") as f: json.dump([], f)

        else: # edge
            print(f"🎙️ [{index}] Generating Edge TTS ({voice})...")
            await generate_edge_tts(text, voice, audio_path, json_path)

    except Exception as e:
        logger.error(f"TTS Generation failed for {provider}: {e}")
        # Emergency fallback to Edge
        if provider != "edge":
            fallback_voice = "en-US-AvaNeural"
            logger.info(f"[{index}] Emergency fallback to Edge TTS ({fallback_voice})...")
            await generate_edge_tts(text, fallback_voice, audio_path, json_path)
        else:
            raise

    return audio_path, json_path

def generate_audio_with_timings(text: str, index: int) -> tuple[str, str]:
    return asyncio.run(generate_tts(text, index))