import requests
import time
import config
from modules.history import is_seen
import random

def fetch_articles(retries=3, delay=5):
    # Fetch more articles if deduplication is on, max 100 for NewsAPI
    fetch_count_per_cat = min(100, max(config.NUM_ARTICLES * 3, 50))
    # NewsAPI only supports these 7 in top-headlines; everything else uses /everything
    #STANDARD_CATEGORIES = {"business", "entertainment", "general", "health", "science", "sports", "technology"}
    STANDARD_CATEGORIES = {
    "technology",
    "artificial intelligence",
    "machine learning",
    "generative AI",
    "ChatGPT",
    "cybersecurity",
    "ethical hacking",
    "ransomware",
    "data breach",
    "cloud computing",
    "AWS",
    "Azure",
    "Google Cloud",
    "DevOps",
    "Kubernetes",
    "Docker",
    "programming",
    "software development",
    "Python",
    "JavaScript",
    "Linux",
    "open source",
    "gadgets",
    "smartphones",
    "iPhone",
    "Android",
    "wearables",
    "gaming",
    "PC gaming",
    "PlayStation",
    "Xbox",
    "eSports",
    "science",
    "space",
    "NASA",
    "ISRO",
    "robotics",
    "automation",
    "quantum computing",
    "electric vehicles",
    "Tesla",
    "renewable energy",
    "battery technology",
    "blockchain",
    "cryptocurrency",
    "Bitcoin",
    "Ethereum",
    "Web3",
    "NFT",
    "metaverse",
    "augmented reality",
    "virtual reality",
    "mixed reality",
    "future technology",
    "consumer electronics",
    "startup funding",
    "technology startups",
    "Silicon Valley",
    "Big Tech",
    "Google",
    "Microsoft",
    "Apple",
    "NVIDIA",
    "Intel",
    "AMD",
    "Qualcomm",
    "TSMC",
    "semiconductors",
    "chip manufacturing",
    "server hardware",
    "data centers",
    "telecom",
    "5G",
    "6G",
    "internet",
    "WiFi",
    "networking",
    "big data",
    "data science",
    "business intelligence",
    "SQL",
    "NoSQL",
    "API development",
    "developer tools",
    "GitHub",
    "Visual Studio Code",
    "productivity tools",
    "SaaS",
    "FinTech",
    "digital payments",
    "UPI",
    "online business",
    "ecommerce",
    "Amazon",
    "Flipkart",
    "social media",
    "YouTube",
    "Instagram",
    "content creators",
    "influencer marketing",
    "digital marketing",
    "SEO",
    "online earning",
    "freelancing",
    "remote work",
    "work from home",
    "automation tools",
    "smart home",
    "drone technology",
    "biotechnology",
    "health technology",
    "fitness technology",
    "medical AI",
    "education technology",
    "EdTech",
    "online learning",
    "mobile apps",
    "streaming platforms",
    "OTT",
    "Netflix",
    "Disney",
    "innovation",
    "future trends"
    }

    # Shuffle CATEGORIES to try them randomly
    shuffled_cats = list(config.NEWS_CATEGORIES)
    random.shuffle(shuffled_cats)
    
    for selected_cat in shuffled_cats:
        print(f"📡 Checking Category: {selected_cat.upper()}...")
        all_raw_articles = []
        cat_lower = selected_cat.lower()
        params = {
            "language": "en",
            "pageSize": fetch_count_per_cat,
            "apiKey": config.NEWS_API_KEY
        }
        
        if cat_lower in STANDARD_CATEGORIES:
            url = "https://newsapi.org/v2/top-headlines"
            params["category"] = cat_lower
        else:
            url = "https://newsapi.org/v2/everything"
            params["q"] = selected_cat
        
        # Try fetching this category
        for attempt in range(retries):
            try:
                res = requests.get(url, params=params, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    all_raw_articles = data.get("articles", [])
                    break
                else:
                    print(f"  ⚠️ Attempt {attempt+1} failed: Error {res.status_code}")
                    if attempt < retries - 1: time.sleep(delay)
            except Exception as e:
                print(f"  ⚠️ Error fetching category {selected_cat}: {e}")
                if attempt < retries - 1: time.sleep(delay)

        if not all_raw_articles:
            print(f"  ❌ No articles found in {selected_cat}. Trying next category...")
            continue

        # Shuffle then Deduplicate
        random.shuffle(all_raw_articles)
        
        if config.DEDUPLICATE_NEWS:
            filtered = [a for a in all_raw_articles if not is_seen(a["url"])]
            print(f"  🔍 Found {len(filtered)} new articles in {selected_cat}.")
            
            if len(filtered) >= config.NUM_ARTICLES:
                print(f"  ✅ Quota met! Using {selected_cat.upper()}.")
                return filtered[:config.NUM_ARTICLES], selected_cat
            else:
                print(f"  ⚠️ Not enough new articles in {selected_cat} ({len(filtered)}/{config.NUM_ARTICLES}). Searching other categories...")
                continue
        else:
            if len(all_raw_articles) >= config.NUM_ARTICLES:
                return all_raw_articles[:config.NUM_ARTICLES], selected_cat
    
    # ── FALLBACK AGGREGATION (If no single category was enough) ──
    print("\n⚠️ No single category had enough new articles. Aggregating from multiple categories...")
    aggregated_articles = []
    seen_urls = set()
    
    # Try one more pass to collect bits from everywhere
    for selected_cat in shuffled_cats:
        # (This is a simplified re-fetch or use cached, for now let's just do a final broad fetch)
        params = {"language": "en", "pageSize": fetch_count_per_cat, "apiKey": config.NEWS_API_KEY, "q": "technology"}
        try:
            res = requests.get("https://newsapi.org/v2/everything", params=params, timeout=10)
            if res.status_code == 200:
                for a in res.json().get("articles", []):
                    if a["url"] not in seen_urls and (not config.DEDUPLICATE_NEWS or not is_seen(a["url"])):
                        aggregated_articles.append(a)
                        seen_urls.add(a["url"])
                    if len(aggregated_articles) >= config.NUM_ARTICLES:
                        return aggregated_articles, "General Tech"
        except: pass

    if aggregated_articles:
        return aggregated_articles, "Tech Mix"

    return [], "None"