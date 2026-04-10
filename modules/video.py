from moviepy.editor import *
import random

from config import SLIDE_DURATION, VIDEO_SIZE

W, H = VIDEO_SIZE

# =========================
# TRANSITION EFFECTS
# =========================
# All transitions use only position/opacity (NO per-frame resize)
# for maximum rendering speed at any resolution.

def _ease_in_out(t):
    """Smooth ease-in-out curve (cubic)."""
    return 3 * t**2 - 2 * t**3

def fx_fade(clip, duration, td):
    """Simple opacity fade in and fade out."""
    return clip.set_position("center").fadein(td).fadeout(td)

def fx_slide_left(clip, duration, td):
    """Slide enters from the right, exits to the left."""
    def pos(t):
        if t < td:
            progress = _ease_in_out(t / td)
            return (int(W * (1 - progress)), 0)
        elif t > duration - td:
            progress = _ease_in_out((t - (duration - td)) / td)
            return (int(-W * progress), 0)
        return (0, 0)
    return clip.set_position(pos).fadein(0.15).fadeout(0.15)

def fx_slide_right(clip, duration, td):
    """Slide enters from the left, exits to the right."""
    def pos(t):
        if t < td:
            progress = _ease_in_out(t / td)
            return (int(-W * (1 - progress)), 0)
        elif t > duration - td:
            progress = _ease_in_out((t - (duration - td)) / td)
            return (int(W * progress), 0)
        return (0, 0)
    return clip.set_position(pos).fadein(0.15).fadeout(0.15)

def fx_slide_up(clip, duration, td):
    """Slide enters from the bottom, exits to the top."""
    def pos(t):
        if t < td:
            progress = _ease_in_out(t / td)
            return (0, int(H * (1 - progress)))
        elif t > duration - td:
            progress = _ease_in_out((t - (duration - td)) / td)
            return (0, int(-H * progress))
        return (0, 0)
    return clip.set_position(pos).fadein(0.15).fadeout(0.15)

def fx_slide_down(clip, duration, td):
    """Slide enters from the top, exits to the bottom."""
    def pos(t):
        if t < td:
            progress = _ease_in_out(t / td)
            return (0, int(-H * (1 - progress)))
        elif t > duration - td:
            progress = _ease_in_out((t - (duration - td)) / td)
            return (0, int(H * progress))
        return (0, 0)
    return clip.set_position(pos).fadein(0.15).fadeout(0.15)

def fx_zoom_fade(clip, duration, td):
    """Fade in with a slight opacity pulse — no expensive resize."""
    return clip.set_position("center").fadein(td * 1.5).fadeout(td)

def fx_crossfade(clip, duration, td):
    """Extended crossfade — longer fade for a cinematic blend."""
    return clip.set_position("center").crossfadein(td * 1.2).fadeout(td * 0.8)

# All available transition effects (NO per-frame resize in any of them)
TRANSITIONS = [
    fx_fade,
    fx_slide_left,
    fx_slide_right,
    fx_slide_up,
    fx_slide_down,
    fx_zoom_fade,
    fx_crossfade,
]

TRANSITION_NAMES = [
    "Fade", "Slide Left", "Slide Right", "Slide Up",
    "Slide Down", "Zoom Fade", "Crossfade"
]


# =========================
# KEN BURNS (position-based, no resize)
# =========================
def apply_ken_burns(clip, duration):
    """
    Subtle slow pan instead of resize — nearly zero performance cost.
    Drifts the image slightly downward over the duration.
    """
    drift = 15  # pixels to drift over the full duration
    def pos(t):
        progress = t / duration
        return ("center", int(-drift * progress))
    return clip.set_position(pos)


# =========================
# ANIMATE A SINGLE SLIDE
# =========================
def animate_clip(slide_img, audio_clip, transition_fx, transition_name):
    """Creates a single animated slide clip with Ken Burns + transitions."""
    # Dynamic duration: config value or auto-sync with audio + buffer
    duration = SLIDE_DURATION if SLIDE_DURATION is not None else (audio_clip.duration + 0.5)
    trans_dur = min(0.6, duration * 0.15)  # Transition takes ~15% of clip, max 0.6s

    # Base slide
    base = ImageClip(slide_img).set_duration(duration)

    # Ken Burns subtle pan (position-based, not resize-based)
    base = apply_ken_burns(base, duration)

    # Apply the randomized transition effect
    base = transition_fx(base, duration, trans_dur)

    # Compose to exact video size
    composite = CompositeVideoClip([base], size=VIDEO_SIZE).set_duration(duration)
    composite = composite.set_audio(audio_clip)

    print(f"    🎬 Transition: {transition_name}")
    return composite


# =========================
# BUILD FULL VIDEO
# =========================
def create_video(slides, audios):
    """
    Creates the final video from a list of slide image paths and audio paths.
    Each slide gets a random (non-repeating) transition effect.
    """
    clips = []
    last_fx_index = -1  # Track last used transition to avoid consecutive repeats

    for i, (slide_img, audio_path) in enumerate(zip(slides, audios)):
        audio_clip = AudioFileClip(audio_path)

        # Pick a random transition, ensuring no consecutive repeats
        available = list(range(len(TRANSITIONS)))
        if last_fx_index in available and len(available) > 1:
            available.remove(last_fx_index)
        fx_index = random.choice(available)
        last_fx_index = fx_index

        clip = animate_clip(slide_img, audio_clip, TRANSITIONS[fx_index], TRANSITION_NAMES[fx_index])
        clips.append(clip)

    # Concatenate with slight overlap for smooth blending
    final = concatenate_videoclips(
        clips,
        method="compose",
        padding=-0.4  # 🔥 Smooth overlap transitions
    )

    # 🎵 Background music
    import os
    bgm_path = "bgm.mp3"
    if os.path.exists(bgm_path):
        try:
            from moviepy.editor import afx
            print(f"🎵 Background music '{bgm_path}' detected! Mixing at 8% volume...")
            bgm = AudioFileClip(bgm_path).fx(afx.volumex, 0.08)
            bgm = afx.audio_loop(bgm, duration=final.duration)
            final = final.set_audio(CompositeAudioClip([final.audio, bgm]))
        except Exception as e:
            print(f"⚠️ Warning: Could not process background music: {e}")

    # 🖥️ GPU / CPU encoding
    try:
        import torch
        has_gpu = torch.cuda.is_available()
    except ImportError:
        has_gpu = False

    if has_gpu:
        print("🚀 Utilizing GPU (NVENC) for hardware-accelerated video encoding!")
        final.write_videofile(
            "output/final/technews.mp4",
            fps=15,
            codec="h264_nvenc",
            audio_codec="aac",
            threads=8,
            ffmpeg_params=[
                "-preset", "p1",
                "-rc", "vbr",
                "-cq", "26",
                "-qmin", "26",
                "-qmax", "26",
                "-pix_fmt", "yuv420p",
                "-b:a", "128k"
            ]
        )
    else:
        print("🐢 NVIDIA GPU not found. Falling back to CPU (libx264).")
        final.write_videofile(
            "output/final/technews.mp4",
            fps=15,
            codec="libx264",
            audio_codec="aac",
            threads=8,
            ffmpeg_params=[
                "-preset", "ultrafast",
                "-crf", "26",
                "-pix_fmt", "yuv420p",
                "-b:a", "128k"
            ]
        )