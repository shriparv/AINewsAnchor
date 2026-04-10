from newspaper import Article
import time
import requests

# Browser-like User-Agent to bypass basic anti-bot checks
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def extract_text(url, retries=2, delay=3):
    """
    Attempts to extract article text using newspaper3k.
    Falls back to a raw requests + basic parsing if newspaper fails.
    Returns empty string only as last resort.
    """
    # Attempt 1: newspaper3k (best quality)
    for attempt in range(retries):
        try:
            art = Article(url)
            art.download()
            art.parse()
            if art.text and len(art.text.strip()) > 50:
                return art.text[:1500]
        except Exception:
            if attempt < retries - 1:
                time.sleep(delay)

    # Attempt 2: Raw requests with browser headers (bypasses some anti-bot)
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            art = Article(url)
            art.set_html(res.text)
            art.parse()
            if art.text and len(art.text.strip()) > 50:
                return art.text[:1500]
    except Exception:
        pass

    print(f"  ⚠️ Could not extract text from: {url}")
    return ""