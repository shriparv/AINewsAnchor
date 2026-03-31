import asyncio
import os
import requests

from modules.fetch_news import fetch_articles
from modules.extract import extract_text
from modules.summarize import summarize
from modules.slides import create_slide
from modules.tts import generate_tts
from modules.video import create_video


def split_text(text, max_words=25):
    words = text.split()
    return [" ".join(words[i:i+max_words]) for i in range(0, len(words), max_words)]

def download_image(url: str, output_path: str) -> str:
    if not url: return None
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(res.content)
        return output_path
    except Exception as e:
        print(f"Warning: Could not download image {url} ({e})")
        return None

async def main():
    articles = fetch_articles()

    if not articles:
        print("❌ Error: No articles found! Please check your NewsAPI configuration or parameters.")
        return

    slides = []
    audios = []

    for i, article in enumerate(articles):
        print(f"Processing: {article['title']}")

        text = extract_text(article["url"])
        if not text:
            continue

        # Download Article Image if available
        img_url = article.get("urlToImage")
        local_img_path = download_image(img_url, f"output/images/news_{i}.jpg")

        summary = summarize(text)

        # Create one slide and audio for the entire article summary
        slide_bg, slide_text = create_slide(article["title"], summary, i, image_path=local_img_path)

        # 🎙️ async TTS (say the headline, then the summary)
        tts_text = f"{article['title']}. {summary}"
        audio_path, _ = await generate_tts(tts_text, i)

        slides.append((slide_bg, slide_text))
        audios.append(audio_path)

    create_video(slides, audios)


if __name__ == "__main__":
    asyncio.run(main())