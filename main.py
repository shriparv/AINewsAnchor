import asyncio
import os
import requests
import random
import sys
import argparse

# Force UTF-8 encoding for Windows terminals so emojis don't crash the script
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from modules.fetch_news import fetch_articles
from modules.extract import extract_text
from modules.summarize import summarize, generate_video_metadata
from modules.slides import create_layered_slide, create_intro_slide
from modules.tts import generate_tts, get_random_voice
from modules.video import create_video

from modules.youtube import upload_video
from modules.history import mark_seen
import time
import shutil
import config


def archive_workspace():
    """Moves temporary assets to an archive and maintains last 3 runs."""
    archive_base = "archives/lastpost"
    os.makedirs(archive_base, exist_ok=True)
    
    # ── Rotation logic (3 -> gone, 2 -> 3, 1 -> 2) ──
    p3 = os.path.join(archive_base, "post_3")
    p2 = os.path.join(archive_base, "post_2")
    p1 = os.path.join(archive_base, "post_1")
    
    print("\n📦 Archiving workspace...")
    
    if os.path.exists(p3):
        shutil.rmtree(p3)
    if os.path.exists(p2):
        os.rename(p2, p3)
    if os.path.exists(p1):
        os.rename(p1, p2)
        
    os.makedirs(p1, exist_ok=True)
    
    # ── Move current output to post_1 ──
    dirs_to_archive = ["output/slides", "output/images", "output/audio", "output/final"]
    for d in dirs_to_archive:
        if os.path.exists(d) and os.listdir(d):
            try:
                target = os.path.join(p1, os.path.basename(d))
                shutil.move(d, target)
                os.makedirs(d, exist_ok=True) # Recreate empty for next run
                print(f"  ✅ Archived {d} -> lastpost/post_1")
            except Exception as e:
                print(f"  ⚠️ Could not archive {d}: {e}")

    # Remove moviepy temp files if they exist in the root
    for f in os.listdir("."):
        if f.startswith("TEMP_MPY") or f.endswith(".mp4.25") or f.endswith("wvf_snd.mp4"):
            try:
                os.remove(f)
                print(f"  ✅ Removed temp file: {f}")
            except:
                pass


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

async def process_article(article, i, accent_color, voice):
    """Processes a single article: extract, download image, summarize, create slide, and generate TTS."""
    print(f"Processing ({i+1}/{config.NUM_ARTICLES}): {article['title']}")

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

        # 🎙️ Generate TTS (say the headline, then the summary)
        tts_text = f"{article['title']}. {summary}"
        audio_path, _ = await generate_tts(tts_text, i, voice_override=voice)
    except Exception as e:
        print(f"  ❌ Failed processing article '{article['title']}': {e}")
        return None


    return {
        "index": i,
        "title": article["title"],
        "url": article["url"],
        "summary": summary,
        "local_img_path": local_img_path,
        "audio_path": audio_path,
        "accent_color": accent_color # Store for later slide generation
    }

async def main():
    # 📦 Archive previous run if exists
    archive_workspace()
    
    start_time = time.time()
    articles = fetch_articles()

    if not articles:
        print("❌ Error: No articles found! Please check your NewsAPI configuration or parameters.")
        return

    description_lines = ["🔥 Daily Tech News Update! 🔥\n"]
    raw_content_for_metadata = ""
    thumbnail_image = None

    # Select a random theme color for this run
    THEME_COLORS = [(0, 255, 255), (57, 255, 20), (255, 0, 255), (191, 0, 255), (255, 170, 0)]
    
    # Select a single voice for this entire run if randomization is on
    session_voice = get_random_voice() if config.RANDOMIZE_VOICE else None
    if session_voice:
        print(f"🎙️ Selected Session Voice: {session_voice.upper()}")

    # ── 1. ARTICLE PROCESSING ──
    results = []
    # Use a fixed palette of neon accent colors
    accents = [(0, 180, 255), (255, 30, 200), (0, 255, 180), (255, 150, 0)]
    random.shuffle(accents)
    
    for i, article in enumerate(articles[:config.NUM_ARTICLES]):
        color = accents[i % len(accents)]
        res = await process_article(article, i, color, session_voice)
        if res:
            results.append(res)

    if not results:
        print("Error: All articles failed during processing (could not extract text). Aborting video creation.")
        return

    # ── 2. DURATION CALCULATION & ORIENTATION ──
    from moviepy.editor import AudioFileClip
    
    # Generate Combined Intro
    intro_text = f"Welcome to today's news update. Here are the {len(results)} top stories we are covering today."
    intro_audio, _ = await generate_tts(intro_text, "intro", voice_override=session_voice)
    
    # Generate Outro
    outro_text = "Please like, subscribe, and comment your views on this channel!"
    outro_audio, _ = await generate_tts(outro_text, "outro", voice_override=session_voice)

    total_duration = AudioFileClip(intro_audio).duration + AudioFileClip(outro_audio).duration
    for r in results:
        total_duration += AudioFileClip(r["audio_path"]).duration

    print(f"\n⏱️ Total estimated video duration: {total_duration:.2f} seconds")
    
    if total_duration > 180:
        print("📐 Duration > 3.0 min: Switching to LANDSCAPE mode.")
        config.VIDEO_SIZE = config.SIZE_LANDSCAPE
    else:
        print("📐 Duration <= 3.0 min: Staying in PORTRAIT mode.")
        config.VIDEO_SIZE = config.SIZE_PORTRAIT

    # ── 3. SLIDE GENERATION ──
    print("\n🎬 Generating Slides...")
    for r in results:
        bg_p, frame_p, text_p = create_layered_slide(
            r["title"], r["summary"], r["index"], 
            image_path=r["local_img_path"], 
            accent_color=r["accent_color"]
        )
        r["layered_paths"] = (bg_p, frame_p, text_p)

    print("🎬 Generating Intro and Outro Slides...")
    from modules.slides import create_titles_slide
    intro_bg, intro_frame, intro_text = create_titles_slide(results)
    
    outro_bg, outro_frame, outro_text_img = create_layered_slide(
        "Thank You For Watching!", 
        outro_text, 
        "outro", 
        image_path=None, 
        accent_color=(0, 255, 200)
    )
    
    # Prepend Intro and append Outro sequence
    final_layered_slides = [(intro_bg, intro_frame, intro_text)] + [r["layered_paths"] for r in results] + [(outro_bg, outro_frame, outro_text_img)]
    final_audios = [intro_audio] + [r["audio_path"] for r in results] + [outro_audio]

    # ── 4. VIDEO GENERATION ──
    print(f"\n🚀 Creating Final Video ({len(final_layered_slides)} slides total)...")
    create_video(final_layered_slides, final_audios)

    # ── 4. METADATA & UPLOAD ──
    for r in results:
        description_lines.append(f"📰 {r['title']}")
        description_lines.append(f"👉 {r['summary']}\n")
        raw_content_for_metadata += f"Headline: {r['title']}\nSummary: {r['summary']}\n\n"
        
        if r["local_img_path"] and not thumbnail_image:
            thumbnail_image = r["local_img_path"]

    print(f"✅ AI Processing Complete in {time.time() - start_time:.2f} seconds.")

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

    # Ensure title is within YouTube's 100-char limit
    final_title = ai_title.strip()
    if len(final_title) > 95:
        final_title = final_title[:92] + "..."
    
    print(f"\n🎬 Video Pipeline Complete. Authenticating YouTube: '{final_title}'")
    upload_video(
        file_path="output/final/technews.mp4",
        title=final_title,
        description=desc_text,
        tags=final_tags,
        thumbnail_path=thumbnail_image
    )

    if config.DEDUPLICATE_NEWS:
        for r in results:
            mark_seen(r["url"])
        print(f"📖 History depth: {len(results)} new articles added to permanent record.")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI News Anchor Video Generator")
    parser.add_argument("-n", "--num", type=int, help="Number of articles to process")
    args = parser.parse_args()

    if args.num:
        config.NUM_ARTICLES = args.num
        print(f"📌 Overriding NUM_ARTICLES: {config.NUM_ARTICLES}")

    asyncio.run(main())