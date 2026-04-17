import requests
import time
import config
from config import NEWS_API_KEY, NUM_ARTICLES, DEDUPLICATE_NEWS
from modules.history import is_seen

def fetch_articles(retries=3, delay=5):
    url = "https://newsapi.org/v2/top-headlines"
    
    # Fetch more articles if deduplication is on
    fetch_count = 50 if DEDUPLICATE_NEWS else NUM_ARTICLES

    params = {
        "category": config.CURRENT_CATEGORY,
        "language": "en",
        "pageSize": fetch_count,
        "apiKey": NEWS_API_KEY
    }

    print(f"📡 Fetching top headlines for category: {config.CURRENT_CATEGORY.upper()}...")

    for attempt in range(retries):
        try:
            res = requests.get(url, params=params, timeout=10)

            # ✅ Check reachability
            if res.status_code != 200:
                print(f"⚠️ Attempt {attempt + 1}: Error {res.status_code} - {res.text}")
                if attempt < retries - 1:
                    time_sleep = delay * (attempt + 1)
                    print(f"🔄 Retrying in {time_sleep} seconds...")
                    time.sleep(time_sleep)
                    continue
                return []

            data = res.json()
            raw_articles = data.get("articles", [])
            import random
            random.shuffle(raw_articles) # 🔥 Shuffling for more variety
            
            if DEDUPLICATE_NEWS:
                filtered = [a for a in raw_articles if not is_seen(a["url"])]
                print(f"🔍 Deduplication: {len(raw_articles) - len(filtered)} already seen. {len(filtered)} random new articles found.")
                
                # If we have enough new ones, return them
                if len(filtered) >= NUM_ARTICLES:
                    return filtered[:NUM_ARTICLES]
                else:
                    print(f"⚠️ Only {len(filtered)} new articles found. Filling remaining spots with recently seen content for variety.")
                    # Fill the rest with seen articles (shuffled) to meet the count if possible
                    seen = [a for a in raw_articles if is_seen(a["url"])]
                    combined = filtered + seen
                    return combined[:NUM_ARTICLES]
            
            return raw_articles[:NUM_ARTICLES]

        except requests.exceptions.RequestException as e:
            print(f"⚠️ Attempt {attempt + 1} failed: Connection error: {e}")
            if attempt < retries - 1:
                time_sleep = delay * (attempt + 1)
                print(f"🔄 Retrying in {time_sleep} seconds...")
                time.sleep(time_sleep)
            else:
                print("❌ Max retries reached. Could not fetch articles.")
                return []