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
from modules.slides import create_layered_slide, create_intro_slide, create_welcome_cta_slide, create_thanks_cta_slide
from modules.tts import generate_tts, get_random_voice
from modules.video import create_video

from modules.youtube import upload_video
from modules.facebook import upload_video_to_facebook
from modules.history import mark_seen
import time
import shutil
import config
import torch
import subprocess

def print_hardware_status():
    print("\n" + "="*50)
    print("🛠️  HARDWARE ACCELERATION STATUS")
    print("="*50)
    
    # 1. AI/Torch Status
    cuda_available = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_available else "N/A"
    print(f"🧠 AI Engines (TTS/LLM):  {'✅ GPU (' + device_name + ')' if cuda_available else '🐢 CPU ONLY'}")
    
    # 2. Video Encoding Status
    try:
        res = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True)
        nvenc = "h264_nvenc" in res.stdout
        print(f"🎬 Video Encoding:      {'✅ GPU (NVENC)' if nvenc else '🐢 CPU (libx264)'}")
    except:
        print(f"🎬 Video Encoding:      ❌ FFmpeg not found")
        
    print("="*50 + "\n")


def archive_workspace():
    """Moves temporary assets to an archive and maintains last 5 runs."""
    archive_base = "archives/lastpost"
    os.makedirs(archive_base, exist_ok=True)
    
    # ── Rotation logic (5 -> gone, 4 -> 5, ..., 1 -> 2) ──
    archive_depth = 5
    print(f"\n📦 Archiving workspace (keeping last {archive_depth} posts)...")
    
    # 1. Remove the oldest archive
    oldest_path = os.path.join(archive_base, f"post_{archive_depth}")
    if os.path.exists(oldest_path):
        try: shutil.rmtree(oldest_path)
        except: pass

    # 2. Shift existing archives: N -> N+1
    for i in range(archive_depth - 1, 0, -1):
        src = os.path.join(archive_base, f"post_{i}")
        dst = os.path.join(archive_base, f"post_{i+1}")
        if os.path.exists(src):
            try: os.rename(src, dst)
            except: pass
        
    p1 = os.path.join(archive_base, "post_1")
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

def truncate_description(lines, max_chars=4980):
    """
    Intelligently joins and truncates description lines to fit within a character limit.
    Prioritizes items from the top (Intro, Headlines).
    """
    final_desc = ""
    for line in lines:
        if len(final_desc) + len(line) + 1 > max_chars:
            # If the very first header is too long (rare), just cut it
            if not final_desc:
                return line[:max_chars-3] + "..."
            
            # append a small footer if space permits
            footer = "\n\n...[Content Truncated due to YouTube limits]"
            if len(final_desc) + len(footer) <= max_chars:
                final_desc += footer
            break
        final_desc += line + "\n"
    return final_desc.strip()


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

async def process_article(article, i, total, accent_color, voice):
    """Processes a single article: extract, download image, summarize, create slide, and generate TTS."""
    print(f"⚡ Processing ({i+1}/{total}): {article['title']}")

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
        short_mode = (total >= 4)
        summary = summarize(article["title"], text, short_mode=short_mode)

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
    # 🛠️ Print Hardware Status
    print_hardware_status()

    # 📦 Archive previous run if exists
    archive_workspace()
    
    start_time = time.time()
    articles, selected_cat = fetch_articles()

    if not articles:
        print("❌ Error: No articles found! Please check your NewsAPI configuration or parameters.")
        return

    cat_title = selected_cat.title()
    description_lines = [f"🔥 Daily Tech News Update! 🔥\n"]
    raw_content_for_metadata = f"Category: {cat_title}\n"
    thumbnail_image = None

    # Select a random theme color for this run
    THEME_COLORS = [(0, 255, 255), (57, 255, 20), (255, 0, 255), (191, 0, 255), (255, 170, 0)]
    
    # Select a single voice for this entire run if randomization is on
    if config.TTS_PROVIDER == "kokoro":
        default_v = config.TTS_VOICE_KOKORO
    elif config.TTS_PROVIDER == "piper":
        default_v = config.TTS_VOICE_PIPER
    else: # edge or fallback
        default_v = config.TTS_VOICE_EDGE

    session_voice = get_random_voice() if config.RANDOMIZE_VOICE else default_v
    if session_voice:
        print(f"🎙️ Selected Session Voice: {session_voice.upper()}")

    # ── 1. ARTICLE PROCESSING (Throttled Parallel) ──
    accents = [(0, 180, 255), (255, 30, 200), (0, 255, 180), (255, 150, 0)]
    random.shuffle(accents)
    
    article_slice = articles[:config.NUM_ARTICLES]
    total = len(article_slice)
    
    # Throttle concurrency to 2 to prevent Ollama timeouts!
    sem = asyncio.Semaphore(2)
    async def process_with_throttle(article, i, color):
        async with sem:
            return await process_article(article, i, total, color, session_voice)
            
    tasks = [
        process_with_throttle(article, i, accents[i % len(accents)])
        for i, article in enumerate(article_slice)
    ]
    print(f"\n⚡ Processing {total} articles in PARALLEL (Max 2 concurrent)...")
    raw_results = await asyncio.gather(*tasks)
    results = [r for r in raw_results if r is not None]  # Filter failed articles
    # Sort by original index to preserve order
    results.sort(key=lambda r: r["index"])

    if not results:
        print("Error: All articles failed during processing (could not extract text). Aborting video creation.")
        return

    # ── 2. INTRO + OUTRO TTS (Parallel with duration calc) ──
    from moviepy.editor import AudioFileClip

    is_hindi = getattr(config, "NEWS_LANGUAGE", "en") == "hi"

    if len(results) >= 4:
        intro_tts_text = f"आज की शीर्ष {len(results)} तकनीकी खबरें।" if is_hindi else f"Today's top {len(results)} tech stories."
        welcome_cta_text = "रोजाना टेक अपडेट के लिए सब्सक्राइब करें और बेल आइकन दबाएं!" if is_hindi else "Subscribe and hit the bell for daily tech updates!"
        thanks_cta_text = "देखने के लिए धन्यवाद! लाइक और कमेंट करें।" if is_hindi else "Thanks for watching! Like and comment below."
        outro_tts_text = "अगले अपडेट में मिलते हैं!" if is_hindi else "See you in the next update!"
    else:
        intro_tts_text = f"आज के न्यूज़ अपडेट में आपका स्वागत है। यहाँ आज की {len(results)} मुख्य खबरें हैं।" if is_hindi else f"Welcome to today's news update. Here are the {len(results)} top stories we are covering today."
        welcome_cta_text = "चैनल पर आपका स्वागत है! कृपया इस वीडियो को लाइक करें, सब्सक्राइब करें और भविष्य के सभी टेक अपडेट के लिए बेल आइकन दबाएं! 🚀 🔔" if is_hindi else "Welcome to the channel! Before we begin today's update, please take a moment to like this video, subscribe to our channel, and press the bell icon to receive notifications for all our future tech updates! 🚀 🔔"
        thanks_cta_text = "देखने के लिए धन्यवाद! कृपया लाइक करें, सब्सक्राइब करें और अपनी प्रतिक्रिया साझा करें। 👍 💬" if is_hindi else "Thanks for watching! Please do like, subscribe, and share your comments and feedbacks below. We love hearing from you! 👍 💬"
        outro_tts_text = "आज के लिए बस इतना ही। अगले अपडेट में मिलते हैं!" if is_hindi else "That's all for today's news. Stay informed and I will see you in the next update!"
    
    print("\n🎙️ Generating CTA TTS in parallel...")
    (intro_audio, _), (welcome_audio, _), (thanks_audio, _), (outro_audio, _) = await asyncio.gather(
        generate_tts(intro_tts_text, "intro", voice_override=session_voice),
        generate_tts(welcome_cta_text, "welcome_cta", voice_override=session_voice),
        generate_tts(thanks_cta_text, "thanks_cta", voice_override=session_voice),
        generate_tts(outro_tts_text, "outro", voice_override=session_voice),
    )
    outro_text = outro_tts_text

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

    # ── 3. SLIDE GENERATION (Parallel via threads) ──
    print("\n🎬 Generating Slides in PARALLEL...")

    async def generate_slide(r):
        bg_p, frame_p, text_p = await asyncio.to_thread(
            create_layered_slide,
            r["title"], r["summary"], r["index"],
            r["local_img_path"], r["accent_color"]
        )
        return r["index"], (bg_p, frame_p, text_p)

    slide_results = await asyncio.gather(*[generate_slide(r) for r in results])
    slide_map = dict(slide_results)
    for r in results:
        r["layered_paths"] = slide_map[r["index"]]

    print("🎬 Generating Intro + Outro Slides in parallel...")
    from modules.slides import create_titles_slide

    (intro_bg, intro_frame, intro_text_layer), (welcome_bg, welcome_frame, welcome_text), (thanks_bg, thanks_frame, thanks_text), (outro_bg, outro_frame, outro_text_img) = await asyncio.gather(
        asyncio.to_thread(create_titles_slide, results),
        asyncio.to_thread(create_welcome_cta_slide, "चैनल पर आपका स्वागत है!" if is_hindi else "Welcome to the Channel!", ["🚀 और अपडेट्स के लिए फॉलो करें" if is_hindi else "🚀 Follow for more", "🔔 बेल आइकन दबाएं" if is_hindi else "🔔 Hit the bell"], "welcome"),
        asyncio.to_thread(create_thanks_cta_slide, "देखने के लिए धन्यवाद!" if is_hindi else "Thanks for watching!", ["💬 नीचे कमेंट करें" if is_hindi else "💬 Comment below", "👍 लाइक करें" if is_hindi else "👍 Like if helpful"], "thanks_cta"),
        asyncio.to_thread(
            create_layered_slide,
            "जुड़े रहें!" if is_hindi else "Stay Informed!", outro_text, "outro", None, (0, 255, 200)
        ),
    )
    
    # Prepend Intro and append Outro sequence
    final_layered_slides = [(intro_bg, intro_frame, intro_text_layer), (welcome_bg, welcome_frame, welcome_text)] + \
                          [r["layered_paths"] for r in results] + \
                          [(thanks_bg, thanks_frame, thanks_text), (outro_bg, outro_frame, outro_text_img)]
    
    final_audios = [intro_audio, welcome_audio] + \
                  [r["audio_path"] for r in results] + \
                  [thanks_audio, outro_audio]

    # ── 4. VIDEO GENERATION ──
    print(f"\n🚀 Creating Final Video ({len(final_layered_slides)} slides total)...")
    video_path = create_video(final_layered_slides, final_audios)

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
    
    # 📏 Truncate description to fit YouTube's 5000 char limit
    desc_text = truncate_description(description_lines, max_chars=4980)

    with open("output/final/description.txt", "w", encoding="utf-8") as f:
        f.write(desc_text)

    # Ensure title is within YouTube's 100-char limit
    final_title = ai_title.strip()
    if len(final_title) > 95:
        final_title = final_title[:92] + "..."
    
    # ── 4. METADATA & UPLOAD ──
    print(f"\n🎬 Video Pipeline Complete. Authenticating YouTube: '{final_title}'")
    
    # 📤 Upload to YouTube (returns ID and the calculated schedule time)
    youtube_res = upload_video(
        file_path=video_path,
        title=final_title,
        description=desc_text,
        tags=final_tags,
        thumbnail_path=thumbnail_image,
        article_count=len(results)   # 📅 Triggers Sunday Digest if count > SUNDAY_DIGEST_THRESHOLD
    )
    
    video_id, schedule_time = youtube_res if youtube_res else (None, None)

    # 📤 Upload to Facebook if enabled
    if config.UPLOAD_TO_FACEBOOK:
        upload_video_to_facebook(
            file_path=video_path,
            title=final_title,
            description=desc_text,
            schedule_time=schedule_time  # Sync with YouTube time if available
        )

    if config.DEDUPLICATE_NEWS:
        for r in results:
            mark_seen(r["url"])
        print(f"📖 History depth: {len(results)} new articles added to permanent record.")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI News Anchor Video Generator")
    parser.add_argument("-n", "--num", type=int, help="Number of articles to process")
    parser.add_argument("--lang", type=str, choices=["en", "hi"], help="Language for the video (en or hi)")
    args = parser.parse_args()

    if args.num:
        config.NUM_ARTICLES = args.num
        print(f"📌 Overriding NUM_ARTICLES: {config.NUM_ARTICLES}")

    if args.lang:
        config.NEWS_LANGUAGE = args.lang
        print(f"📌 Overriding NEWS_LANGUAGE: {config.NEWS_LANGUAGE}")

    asyncio.run(main())
