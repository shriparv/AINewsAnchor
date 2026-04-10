NEWS_API_KEY = "e7ebf6d7eecf479e95dcc55b4b5c812b"
NUM_ARTICLES = 5
DEDUPLICATE_NEWS = True 
SLIDE_DURATION = None  # Set to None for auto-sync with audio length, or a fixed number of seconds
#VIDEO_SIZE = (720, 1280)
VIDEO_SIZE = (1080 , 1920)
FONT_SIZE = 50
# LLM
LLM_MODEL = "dolphin-mixtral:latest"
LLM_URL = "http://localhost:11434/api/generate" 

# 🎙️ TTS CONFIGURATION
# Options: "edge" (free), "openai" (paid), "eleven" (paid/premium), "kokoro" (local/high-quality), "piper" (local/fast)
TTS_PROVIDER = "kokoro" 


# Professional Voice Recommendations:
# ElevenLabs: "Adam" (News), "Antoni" (Professional), "Nicole" (Authoritative)
# OpenAI: "onyx" (Deep/News), "nova" (Clear/Energy), "fable" (Storyteller)
TTS_VOICE_OPENAI = "onyx"
TTS_VOICE_ELEVEN = "Adam"
TTS_VOICE_PIPER = "en_US-lessac-medium"

# Kokoro: "af_heart" (Human/Warm), "af_bella" (Clear/Narrator), "am_adam" (Deep/Male)
TTS_VOICE_KOKORO = "af_heart"

OPENAI_API_KEY = ""
ELEVENLABS_API_KEY = ""