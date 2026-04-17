from moviepy.editor import *
import random
import math

from config import SLIDE_DURATION
import config

# W, H = config.VIDEO_SIZE # These are now accessed dynamically

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
        w, h = config.VIDEO_SIZE
        if t < td:
            progress = _ease_in_out(t / td)
            return (int(w * (1 - progress)), 0)
        elif t > duration - td:
            progress = _ease_in_out((t - (duration - td)) / td)
            return (int(-w * progress), 0)
        return (0, 0)
    return clip.set_position(pos).fadein(0.15).fadeout(0.15)

def fx_slide_right(clip, duration, td):
    """Slide enters from the left, exits to the right."""
    def pos(t):
        w, h = config.VIDEO_SIZE
        if t < td:
            progress = _ease_in_out(t / td)
            return (int(-w * (1 - progress)), 0)
        elif t > duration - td:
            progress = _ease_in_out((t - (duration - td)) / td)
            return (int(w * progress), 0)
        return (0, 0)
    return clip.set_position(pos).fadein(0.15).fadeout(0.15)

def fx_slide_up(clip, duration, td):
    """Slide enters from the bottom, exits to the top."""
    def pos(t):
        w, h = config.VIDEO_SIZE
        if t < td:
            progress = _ease_in_out(t / td)
            return (0, int(h * (1 - progress)))
        elif t > duration - td:
            progress = _ease_in_out((t - (duration - td)) / td)
            return (0, int(-h * progress))
        return (0, 0)
    return clip.set_position(pos).fadein(0.15).fadeout(0.15)

def fx_slide_down(clip, duration, td):
    """Slide enters from the top, exits to the bottom."""
    def pos(t):
        w, h = config.VIDEO_SIZE
        if t < td:
            progress = _ease_in_out(t / td)
            return (0, int(-h * (1 - progress)))
        elif t > duration - td:
            progress = _ease_in_out((t - (duration - td)) / td)
            return (0, int(h * progress))
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

def load_transparent_image_clip(img_path, duration):
    from PIL import Image
    import numpy as np
    from moviepy.editor import ImageClip
    
    pil_img = Image.open(img_path).convert("RGBA")
    r, g, b, a = pil_img.split()
    rgb_img = np.array(Image.merge("RGB", (r, g, b)))
    mask_arr = np.array(a) / 255.0
    
    clip = ImageClip(rgb_img).set_duration(duration)
    mask_clip = ImageClip(mask_arr, ismask=True).set_duration(duration)
    return clip.set_mask(mask_clip)

def load_rgb_image_clip(img_path, duration):
    from PIL import Image
    import numpy as np
    from moviepy.editor import ImageClip
    
    pil_img = Image.open(img_path).convert("RGB")
    rgb_img = np.array(pil_img)
    return ImageClip(rgb_img).set_duration(duration)

def animate_layered_slide(bg_img, frame_img, text_img=None, audio_clip=None, is_intro=False):
    """
    Creates a layered animated slide where the background, frame, and text move independently.
    Now includes a synchronized text reveal (wipe) effect.
    """
    # Dynamic duration: config value or auto-sync with audio + buffer
    duration = SLIDE_DURATION if SLIDE_DURATION is not None else (audio_clip.duration + 0.5)
    
    # ── Background Layer (Slow Ken Burns) ──
    bg = load_rgb_image_clip(bg_img, duration)
    drift = 25 if not is_intro else 40
    def bg_pos(t):
        return ("center", int(-drift * (t / duration)))
    bg = bg.set_position(bg_pos)

    # ── Frame Layer (Elastic Entrance) ──
    frame = load_transparent_image_clip(frame_img, duration)
    intro_dur = 0.8 # Duration of the entrance animation
    
    def frame_pos(t):
        w, h = config.VIDEO_SIZE
        if t < intro_dur:
            progress = _ease_out_elastic(t / intro_dur)
            # Starts off-screen bottom, springs to center
            return ("center", int(h * (1 - progress)))
        return ("center", 0)

    frame = frame.set_position(frame_pos).fadein(0.2)
    
    # ── Synchronized Text Layer (Vertical Wipe Reveal) ──
    layers = [bg, frame]
    
    if text_img and os.path.exists(text_img):
        text_clip = load_transparent_image_clip(text_img, duration)
        text_clip = text_clip.set_position(frame_pos) # Stays with the frame
        
        # We start the reveal shortly after the slide begins entering
        reveal_start = 0.2
        # Finish the reveal by ~60% of the slide duration so it stays ahead of the speaker
        reveal_dur = max(1.0, duration * 0.6) 
        if reveal_dur > duration - 1.0: reveal_dur = max(1.0, duration - 1.0)
        
        def wipe_mask(t):
            if t < reveal_start:
                return 0.0 # Hidden
            elif t > reveal_start + reveal_dur:
                return 1.0 # Fully revealed
            else:
                return (t - reveal_start) / reveal_dur

        # Wipe effect keeping the original text alpha mask intact!
        def text_wipe_fl_mask(gf, t):
            mask_frame = gf(t).copy()
            progress = wipe_mask(t)
            h = mask_frame.shape[0]
            cutoff = int(h * progress)
            if cutoff < h:
                mask_frame[cutoff:, :] = 0.0
            return mask_frame

        import numpy as np
        if text_clip.mask is not None:
            text_clip.mask = text_clip.mask.fl(text_wipe_fl_mask)
            
        layers.append(text_clip)

    # ── Composite ──
    composite = CompositeVideoClip(layers, size=config.VIDEO_SIZE).set_duration(duration)
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
    
    for i, ((bg, frame, text), audio_path) in enumerate(zip(layered_slides, audios)):
        audio_clip = AudioFileClip(audio_path)
        
        # Check if this is the intro slide
        is_intro = (i == 0)
        
        clip = animate_layered_slide(bg, frame, text, audio_clip, is_intro=is_intro)
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
            threads=16, # Increase threading for modern many-core CPUs
            ffmpeg_params=[
                "-preset", "p1", # Fastest NVENC preset
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