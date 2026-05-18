import random
NEWS_API_KEY = "e7ebf6d7eecf479e95dcc55b4b5c812b"
NUM_ARTICLES = 10
DEDUPLICATE_NEWS = True 

# 📰 NEWS VARIETY
# Categories: technology, business, entertainment, general, health, science, sports
#NEWS_CATEGORIES = [
#    "NVIDIA GPU", "Intel CPU", "AMD Ryzen", "computer gaming news",
#    "information technology", "cloud computing", "AWS Azure Google Cloud",
#    "cybersecurity", "software development", "programming news",
#    "linux open source", "gadgets", "smartphones", "quantum computing",
#    "robotics", "automation", "server hardware", "networking IT"
#]
NEWS_CATEGORIES = [
"Artificial Intelligence",
"Machine Learning",
"Generative AI",
"OpenAI",
"ChatGPT",
"LLM models",
"AI automation",
"AI startups",
"AI coding tools",
"Deep Learning",
"Computer Vision",
"Natural Language Processing",
"AI agents",
"NVIDIA GPU",
"Intel CPU",
"AMD Ryzen",
"ARM processors",
"data center hardware",
"server hardware",
"custom silicon",
"semiconductor industry",
"chip manufacturing",
"TSMC",
"Qualcomm",
"Apple silicon",
"computer gaming news",
"PC gaming",
"gaming laptops",
"gaming GPU",
"Steam gaming",
"eSports",
"PlayStation",
"Xbox",
"Nintendo",
"gaming industry",
"cloud computing",
"AWS",
"Microsoft Azure",
"Google Cloud",
"DevOps",
"Kubernetes",
"Docker containers",
"microservices",
"enterprise IT",
"virtualization",
"VMware",
"OpenStack",
"hybrid cloud",
"cybersecurity",
"ethical hacking",
"ransomware attacks",
"malware analysis",
"data breaches",
"zero day vulnerability",
"SOC security",
"network security",
"penetration testing",
"cyber crime",
"digital forensics",
"software development",
"programming news",
"Python programming",
"JavaScript",
"TypeScript",
"Rust programming",
"Go programming",
"Java development",
"Visual Studio Code",
"GitHub",
"software engineering",
"developer tools",
"API development",
"linux open source",
"Ubuntu Linux",
"Debian Linux",
"Arch Linux",
"Fedora Linux",
"Kali Linux",
"open source software",
"GNU Linux",
"Linux server",
"system administration",
"gadgets",
"smartphones",
"Android phones",
"iPhone",
"Samsung Galaxy",
"wearable technology",
"smartwatch",
"tablet devices",
"consumer electronics",
"mobile processors",
"quantum computing",
"robotics",
"automation",
"humanoid robots",
"space technology",
"satellite internet",
"augmented reality",
"virtual reality",
"mixed reality",
"metaverse",
"edge computing",
"5G technology",
"6G research",
"networking IT",
"Cisco networking",
"Juniper networks",
"WiFi technology",
"network automation",
"data centers",
"fiber internet",
"telecom technology",
"big data",
"data analytics",
"data engineering",
"business intelligence",
"Apache Hadoop",
"Apache Spark",
"database technology",
"SQL databases",
"NoSQL databases",
"blockchain technology",
"cryptocurrency",
"Bitcoin",
"Ethereum",
"Web3",
"NFT technology",
"decentralized finance",
"scientific innovation",
"future technology",
"renewable energy technology",
"battery technology",
"electric vehicles",
"drone technology",
"biotechnology",
"nanotechnology",
"technology startups",
"Silicon Valley",
"tech acquisitions",
"startup funding",
"IPO technology",
"Big Tech companies",
"technology business news"
]

RANDOMIZE_CATEGORY = False
CURRENT_CATEGORY = random.choice(NEWS_CATEGORIES) if RANDOMIZE_CATEGORY else "technology"
SLIDE_DURATION = None  # Set to None for auto-sync with audio length, or a fixed number of seconds
SIZE_PORTRAIT = (1080, 1920)
SIZE_LANDSCAPE = (1920, 1080)
VIDEO_SIZE = SIZE_PORTRAIT
FONT_SIZE = 50
# LLM
LLM_MODEL = "llama3:latest"
LLM_URL = "http://127.0.0.1:11434/api/generate" 

# 🎙️ TTS CONFIGURATION
# Options: "edge" (free), "openai" (paid), "eleven" (paid/premium), "kokoro" (local/high-quality), "piper" (local/fast)
TTS_PROVIDER = "edge" 
RANDOMIZE_VOICE = True 

# If RANDOMIZE_VOICE is True and this list is NOT empty, it will pick one of these regardless of TTS_PROVIDER
RANDOM_VOICE_POOL = [
    "am_adam",                # Kokoro
    "en-US-AndrewNeural",      # Edge
    "bf_emma",                # Kokoro
    "en_US-lessac-low",        # Piper
    "en_US-ryan-low"           # Piper
]


# Professional Voice Recommendations:
# Piper Voices:
# en_US-amy-low ⭐ (lightweight, fast)
# en_US-amy-medium ⭐ (balanced quality)
# en_US-amy-high 🔥 (best quality, heavier)
# en_US-lessac-low
# en_US-lessac-medium
# en_US-lessac-high 🔥 (very natural)
# en_US-ryan-low
# en_US-ryan-medium
# en_US-ryan-high (Deep Male)
TTS_VOICE_PIPER = "en_US-lessac-medium"

# Kokoro: "af_heart" (Human/Warm), "af_bella" (Clear/Narrator), "am_adam" (Deep/Male)
TTS_VOICE_KOKORO = "af_heart"

# Edge TTS (Microsoft Neural): "en-US-AvaNeural" (Female/Pro), "en-US-AndrewNeural" (Male/Pro), "en-US-EmmaNeural", "en-US-BrianNeural"
TTS_VOICE_EDGE = "en-US-AvaNeural"

# 📱 FACEBOOK PAGE CONFIGURATION
UPLOAD_TO_FACEBOOK = True
FB_PAGE_ID = "111235544540553"
FB_PAGE_ACCESS_TOKEN = "EAAXQ6OrYrLMBRH57jWl14k4WHLBZAf2fZBDRmj4TzrlitZBnGrEgZBjuQZBvE6Ani0nzvSiwkDORpTTt6SAsBfZABvB2rLN5WXBhnthDYRhpt72TOBHmamxn1xqWk4O3vkrX88EdrqalxBZCDY5UE8cW4mu1rVvgtnJD3DC2fwej92PXmeRh3CBBlo52DLed7kBzqtqTGZCj9EOJql5zQ0ZBu"


# 📅 SCHEDULING
# Scheduling is dynamically calculated based on the Tech Niche Golden Strategy.
# See modules/schedule.py for details on timing rules.
