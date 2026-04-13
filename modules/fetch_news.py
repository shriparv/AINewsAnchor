import requests
import time
from config import NEWS_API_KEY, NUM_ARTICLES, DEDUPLICATE_NEWS
from modules.history import is_seen

def fetch_articles(retries=3, delay=5):
    url = "https://newsapi.org/v2/top-headlines"
    
    # Fetch more articles if deduplication is on
    fetch_count = 50 if DEDUPLICATE_NEWS else NUM_ARTICLES

    params = {
        "category": "technology",
        "language": "en",
        "pageSize": fetch_count,
        "apiKey": NEWS_API_KEY,
        "domains": "techcrunch.com, theverge.com, wired.com, arstechnica.com, engadget.com, zdnet.com, venturebeat.com,venturebeat.com, analyticsindiamag.com, towardsdatascience.com, ai.googleblog.com, openai.com/blog, deepmind.com/blog, synchedreview.com,gsmarena.com, androidauthority.com, 9to5google.com, macrumors.com, windowscentral.com,"
    }

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

            if DEDUPLICATE_NEWS:
                filtered = [a for a in raw_articles if not is_seen(a["url"])]
                print(f"🔍 Deduplication: {len(raw_articles) - len(filtered)} already seen. {len(filtered)} new articles found.")
                return filtered[:NUM_ARTICLES]
            
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