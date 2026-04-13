from moviepy.editor import *
import random
import math

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
def _ease_out_elastic(t):
    """Elastic overshoot easing for 'springy' professional motion."""
    if t == 0: return 0
    if t == 1: return 1
    p = 0.3
    s = p / 4
    return (2**(-10 * t) * math.sin((t - s) * (2 * math.pi) / p) + 1)

def animate_layered_slide(bg_img, panel_img, audio_clip, is_intro=False):
    """
    Creates a layered animated slide where the background and panel move independently.
    Uses 'parallax-lite' and elastic easing for a high-end feel.
    """
    # Dynamic duration: config value or auto-sync with audio + buffer
    duration = SLIDE_DURATION if SLIDE_DURATION is not None else (audio_clip.duration + 0.5)
    
    # ── Background Layer (Slow Ken Burns) ──
    bg = ImageClip(bg_img).set_duration(duration)
    drift = 25 if not is_intro else 40
    def bg_pos(t):
        return ("center", int(-drift * (t / duration)))
    bg = bg.set_position(bg_pos)

    # ── Panel Layer (Elastic Entrance) ──
    panel = ImageClip(panel_img, transparent=True).set_duration(duration)
    intro_dur = 0.8 # Duration of the entrance animation
    
    def panel_pos(t):
        if t < intro_dur:
            progress = _ease_out_elastic(t / intro_dur)
            # Starts off-screen bottom, springs to center
            return ("center", int(H * (1 - progress)))
        return ("center", 0)

    panel = panel.set_position(panel_pos).fadein(0.2)

    # ── Composite ──
    composite = CompositeVideoClip([bg, panel], size=VIDEO_SIZE).set_duration(duration)
    composite = composite.set_audio(audio_clip)

    print(f"    🎭 Applied Animation: {'Elastic Intro Collage' if is_intro else 'Elastic Parallax Entrance'}")
    return composite


# =========================
# BUILD FULL VIDEO
# =========================
def create_video(layered_slides, audios):
    """
    Creates the final video from a list of (bg_path, panel_path) tuples and audio paths.
    """
    clips = []
    
    for i, ((bg, panel), audio_path) in enumerate(zip(layered_slides, audios)):
        audio_clip = AudioFileClip(audio_path)
        
        # Check if this is the intro slide (usually the first one)
        is_intro = (i == 0)
        
        clip = animate_layered_slide(bg, panel, audio_clip, is_intro=is_intro)
        clips.append(clip)
        
    if not clips:
        print("⚠️ Warning: No video clips were generated. Skipping video concatenation.")
        return

    # Concatenate with slight overlap for smooth blending
    final = concatenate_videoclips(
        clips,
        method="compose",
        padding=-0.3  # 🔥 Smother overlap transitions
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

    # 🖥️ GPU / CPU encoding (Robust check via nvidia-smi)
    import subprocess
    has_gpu = False
    try:
        subprocess.run(["nvidia-smi"], capture_output=True)
        has_gpu = True
    except:
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