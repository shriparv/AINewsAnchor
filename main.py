import asyncio
import os
import requests
import random
import sys

# Force UTF-8 encoding for Windows terminals so emojis don't crash the script
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from modules.fetch_news import fetch_articles
from modules.extract import extract_text
from modules.summarize import summarize, generate_video_metadata
from modules.slides import create_slide
from modules.tts import generate_tts
from modules.video import create_video
from modules.youtube import upload_video
from modules.history import mark_seen
import time
from config import NUM_ARTICLES, DEDUPLICATE_NEWS


def split_text(text, max_words=25):
    words = text.split()
    return [" ".join(words[i:i+max_words]) for i in range(0, len(words), max_words)]

def download_image(url: str, output_path: str, retries=2, delay=3) -> str:
    if not url: return None
    for attempt in range(retries):
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            res = requests.get(url, timeout=10)
            res.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(res.content)
            return output_path
        except Exception as e:
            if attempt < retries - 1:
                print(f"⚠️ Warning: Retrying image download {url} ({e})")
                time.sleep(delay)
            else:
                print(f"Warning: Could not download image {url} after {retries} attempts ({e})")
                return None

async def process_article(article, i, accent_color):
    """Processes a single article: extract, download image, summarize, create slide, and generate TTS."""
    print(f"Processing ({i+1}/{NUM_ARTICLES}): {article['title']}")

    text = extract_text(article["url"])
    if not text:
        # Fallback: use the description provided by NewsAPI
        text = article.get("description", "") or article.get("content", "")
        if not text:
            print(f"  ❌ Skipping article (no text available): {article['title']}")
            return None
        print(f"  📝 Using NewsAPI description as fallback for: {article['title']}")

    # Download Article Image if available
    img_url = article.get("urlToImage")
    local_img_path = download_image(img_url, f"output/images/news_{i}.jpg")
    
    try:
        summary = summarize(article["title"], text)

        # Create slide image (single composite)
        slide_path = create_slide(article["title"], summary, i, image_path=local_img_path, accent_color=accent_color)

        # 🎙️ Generate TTS (say the headline, then the summary)
        tts_text = f"{article['title']}. {summary}"
        audio_path, _ = await generate_tts(tts_text, i)
    except Exception as e:
        print(f"  ❌ Failed processing article '{article['title']}': {e}")
        return None

    return {
        "index": i,
        "title": article["title"],
        "url": article["url"],
        "summary": summary,
        "local_img_path": local_img_path,
        "slide_path": slide_path,
        "audio_path": audio_path,
    }

async def main():
    articles = fetch_articles()

    if not articles:
        print("❌ Error: No articles found! Please check your NewsAPI configuration or parameters.")
        return

    slides = []
    audios = []
    description_lines = ["🔥 Daily Tech News Update! 🔥\n"]
    raw_content_for_metadata = ""
    thumbnail_image = None

    # Select a random theme color for this run
    THEME_COLORS = [
        (0, 255, 255),   # Neon Cyan
        (57, 255, 20),   # Neon Green
        (255, 0, 255),   # Neon Pink
        (191, 0, 255),   # Electric Purple
        (255, 170, 0),   # Neon Gold
        (0, 180, 255)    # Sky Blue
    ]
    accent_color = random.choice(THEME_COLORS)

    start_time = time.time()
    
    # 🚀 Process all articles in PARALLEL
    tasks = [process_article(article, i, accent_color) for i, article in enumerate(articles[:NUM_ARTICLES])]
    results = await asyncio.gather(*tasks)
    
    # Filter out failed extractions
    results = [r for r in results if r is not None]
    
    if not results:
        print("Error: All articles failed during processing (could not extract text). Aborting video creation.")
        return
        
    results.sort(key=lambda x: x["index"]) # Maintain original order
    
    for r in results:
        slides.append(r["slide_path"])
        audios.append(r["audio_path"])
        
        description_lines.append(f"📰 {r['title']}")
        description_lines.append(f"👉 {r['summary']}\n")
        raw_content_for_metadata += f"Headline: {r['title']}\nSummary: {r['summary']}\n\n"
        
        if r["local_img_path"] and not thumbnail_image:
            thumbnail_image = r["local_img_path"]

    print(f"✅ AI Processing Complete in {time.time() - start_time:.2f} seconds.")
    
    # 🎬 Build video with transitions
    create_video(slides, audios)

    print("\n🧠 Brainstorming AI Metadata (Catchy Title & SEO Tags)...")
    ai_title, ai_tags = generate_video_metadata(raw_content_for_metadata)

    # 📏 Ensure tags fit within 450 chars for YouTube
    final_tags = []
    current_length = 0
    for tag in ai_tags:
        if current_length + len(tag) + 1 <= 450:
            final_tags.append(tag)
            current_length += len(tag) + 1
            
    desc_hashtags = " ".join([f"#{t.replace(' ', '')}" for t in final_tags[:10]])
    description_lines.append(f"\n{desc_hashtags}")
    
    desc_text = "\n".join(description_lines)

    with open("output/final/description.txt", "w", encoding="utf-8") as f:
        f.write(desc_text)

    print(f"\n🎬 Video Pipeline Complete. Authenticating YouTube: '{ai_title}'")
    upload_video(
        file_path="output/final/technews.mp4",
        title=ai_title,
        description=desc_text,
        tags=final_tags,
        thumbnail_path=thumbnail_image
    )

    # ✅ Mark articles as seen in history
    if DEDUPLICATE_NEWS:
        for r in results:
            mark_seen(r["url"])
        print(f"📖 History depth: {len(results)} new articles added to permanent record.")



if __name__ == "__main__":
    asyncio.run(main())