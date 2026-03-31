from moviepy.editor import *
import random


from config import SLIDE_DURATION

def animate_clip(bg_img, text_img, audio_clip):
    # Set to a strict 10-second interval or whatever SLIDE_DURATION is
    duration = SLIDE_DURATION

    # If the audio is longer than the slide duration, we must truncate it so the video doesn't break
    audio_clip = audio_clip.subclip(0, min(duration, audio_clip.duration))

    # Animate background
    bg_clip = ImageClip(bg_img).set_duration(duration)
    style = random.choice(["zoom_in", "zoom_out", "pan"])
    if style == "zoom_in":
        bg_clip = bg_clip.resize(lambda t: 1 + 0.04 * t)
    elif style == "zoom_out":
        bg_clip = bg_clip.resize(lambda t: 1.1 - 0.04 * t)
    elif style == "pan":
        bg_clip = bg_clip.set_position(lambda t: ("center", int(-30 * t)))
    bg_clip = bg_clip.fadein(0.5).fadeout(0.5)

    # Animate text
    text_clip = ImageClip(text_img).set_duration(duration)
    text_clip = text_clip.set_position(
        lambda t: ("center", max(0, int(50 - 50 * t)))
    ).crossfadein(0.8)

    # Combine bg and text
    composite = CompositeVideoClip([bg_clip, text_clip]).set_audio(audio_clip)
    
    # We still add a tiny fade to transition nicely between the intervals
    return composite


def create_video(slides, audios):
    clips = []

    for (bg_img, text_img), audio in zip(slides, audios):
        audio_clip = AudioFileClip(audio)

        clip = animate_clip(bg_img, text_img, audio_clip)
        clips.append(clip)

    final = concatenate_videoclips(
        clips,
        method="compose",
        padding=-0.5   # 🔥 smooth transitions
    )

    final.write_videofile(
        "output/final/technews.mp4",
        fps=24,
        codec="h264_nvenc",
        audio_codec="aac",
        ffmpeg_params=[
            "-preset", "p4",
            "-rc", "vbr",
            "-cq", "19"
        ]
    )