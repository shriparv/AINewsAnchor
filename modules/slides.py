from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import os
import numpy as np
import platform
from config import VIDEO_SIZE

# =========================
# CONFIG
# =========================
SLIDE_W, SLIDE_H = VIDEO_SIZE
PADDING = 50

# =========================
# FONT SETUP
# =========================
def get_font_paths():
    system = platform.system()

    if system == "Windows":
        base = "C:/Windows/Fonts/"
        return base + "segoeui.ttf", base + "segoeuib.ttf"
    elif system == "Linux":
        base = "/usr/share/fonts/truetype/dejavu/"
        return base + "DejaVuSans.ttf", base + "DejaVuSans-Bold.ttf"
    elif system == "Darwin":
        base = "/System/Library/Fonts/"
        return base + "Helvetica.ttc", base + "Helvetica-Bold.ttc"
    else:
        return "arial.ttf", "arialbd.ttf"

FONT_PATH, BOLD_FONT_PATH = get_font_paths()

def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except:
        return ImageFont.load_default()

# =========================
# TEXT WRAP
# =========================
def wrap_text(text, font, max_width, draw):
    words = text.split()
    lines, current = [], ""

    for word in words:
        test = f"{current} {word}".strip()
        w = draw.textbbox((0, 0), test, font=font)[2]

        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines

# =========================
# BACKGROUND: Cinematic blurred article image
# =========================
def create_cinematic_background(image_path=None):
    """Creates a cinematic blurred background from the article image, or a gradient fallback."""
    w, h = SLIDE_W, SLIDE_H

    if image_path and os.path.exists(image_path):
        try:
            base = Image.open(image_path).convert("RGB")
            img = ImageOps.fit(base, (w, h), method=Image.Resampling.LANCZOS)
            # Heavy blur for depth-of-field cinematic effect
            img = img.filter(ImageFilter.GaussianBlur(radius=25))
            # Dark overlay for readability
            overlay = Image.new("RGBA", (w, h), (0, 0, 0, 160))
            img = Image.alpha_composite(img.convert("RGBA"), overlay)
            return img
        except Exception:
            pass

    # Gradient fallback
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    c1, c2 = (8, 12, 22), (20, 35, 65)
    for i in range(3):
        arr[:, :, i] = np.linspace(c1[i], c2[i], h).reshape(-1, 1)
    return Image.fromarray(arr, "RGB").convert("RGBA")


# =========================
# NEON BORDER
# =========================
def draw_neon_border(draw, bbox, color, radius=30, thickness=3, glow_passes=5):
    """Draws a glowing neon rounded-rectangle border."""
    x1, y1, x2, y2 = bbox
    # Glow layers (expanding outward, decreasing opacity)
    for i in range(glow_passes, 0, -1):
        alpha = int(40 * i / glow_passes)
        glow_color = (*color[:3], alpha)
        offset = i * 2
        draw.rounded_rectangle(
            [(x1 - offset, y1 - offset), (x2 + offset, y2 + offset)],
            radius=radius + offset,
            outline=glow_color,
            width=2
        )
    # Main solid border
    draw.rounded_rectangle(
        [(x1, y1), (x2, y2)],
        radius=radius,
        outline=(*color[:3], 255),
        width=thickness
    )


# =========================
# TEXT WITH CLEAN SHADOW
# =========================
def draw_styled_text(draw, pos, text, font, fill):
    """Draws crisp text with a clean dark shadow for readability."""
    x, y = pos

    # Dark outline/shadow for contrast against any background
    shadow_color = (0, 0, 0, 200)
    for dx, dy in [(-1,-1), (1,-1), (-1,1), (1,1), (2,2), (3,3)]:
        draw.text((x + dx, y + dy), text, font=font, fill=shadow_color)

    # Main text (crisp, no blur)
    draw.text((x, y), text, font=font, fill=fill)


# =========================
# DIVIDER LINE
# =========================
def draw_divider(draw, y, x_start, x_end, color):
    """Draws a thin accent-colored horizontal divider."""
    line_color = (*color[:3], 140)
    draw.line([(x_start, y), (x_end, y)], fill=line_color, width=2)


# =========================
# SLIDE NUMBER BADGE
# =========================
def draw_slide_badge(draw, index, bbox, font_path):
    """Draws a small pill-shaped badge with the slide number."""
    x2, y2 = bbox[2], bbox[3]
    badge_font = load_font(font_path, 28)
    text = str(index + 1)
    tw = draw.textbbox((0, 0), text, font=badge_font)[2]
    
    pill_w, pill_h = tw + 28, 40
    px = x2 - pill_w - 15
    py = y2 - pill_h - 15
    
    draw.rounded_rectangle(
        [(px, py), (px + pill_w, py + pill_h)],
        radius=20,
        fill=(255, 255, 255, 35)
    )
    draw.text(
        (px + (pill_w - tw) // 2, py + 4),
        text,
        font=badge_font,
        fill=(255, 255, 255, 180)
    )


# =========================
# MAIN: CREATE SLIDE
# =========================
def create_slide(title, text, index, image_path=None, accent_color=(0, 180, 255)):
    """
    Creates a single self-contained slide image with:
    - Cinematic blurred background
    - Neon-bordered panel
    - Inner thumbnail
    - Headline + body with adaptive font sizing
    - Divider, slide badge
    
    Returns: slide_path (str)
    """
    os.makedirs("output/slides", exist_ok=True)

    # ── Background ──
    img = create_cinematic_background(image_path)
    draw = ImageDraw.Draw(img, "RGBA")

    # ── Panel dimensions ──
    margin = 15  # Small equal margin for "edge to edge" look
    panel_x1 = margin
    panel_y1 = margin
    panel_x2 = SLIDE_W - margin
    panel_y2 = SLIDE_H - margin
    panel_w = panel_x2 - panel_x1
    panel_h = panel_y2 - panel_y1

    # Glass panel fill
    draw.rounded_rectangle(
        [(panel_x1, panel_y1), (panel_x2, panel_y2)],
        radius=20, # Slightly smaller radius for tighter margin
        fill=(10, 15, 22, 200)
    )

    # Neon border
    draw_neon_border(draw, (panel_x1, panel_y1, panel_x2, panel_y2), accent_color)

    # ── Inner content area ──
    content_pad = 25 # Reduced padding
    cx1 = panel_x1 + content_pad
    cy1 = panel_y1 + content_pad
    cx2 = panel_x2 - content_pad
    content_w = cx2 - cx1

    cursor_y = cy1  # Tracks vertical position as we lay out elements

    # ── Inner Thumbnail ──
    thumb_h = 0
    if image_path and os.path.exists(image_path):
        try:
            tw = content_w
            th = int(tw * (9 / 16))
            thumb_base = Image.open(image_path).convert("RGBA")
            thumb = ImageOps.fit(thumb_base, (tw, th), method=Image.Resampling.LANCZOS)

            # Rounded corners mask
            mask = Image.new("L", (tw, th), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rounded_rectangle((0, 0, tw, th), radius=20, fill=255)
            thumb.putalpha(mask)

            img.paste(thumb, (cx1, cursor_y), thumb)
            thumb_h = th + 25
            cursor_y += thumb_h
        except Exception as e:
            print(f"Warning: thumbnail render failed: {e}")

    # ── Available space for text ──
    badge_reserve = 60  # Space for the badge at the bottom
    available_h = (panel_y2 - content_pad - badge_reserve) - cursor_y
    divider_gap = 30  # Space for the divider between headline & body

    # ── Adaptive Typography ──
    max_title_size = 64
    max_body_size = 42
    min_title_size = 36
    min_body_size = 24
    title_size = max_title_size
    body_size = max_body_size

    # Dummy draw surface for measuring
    measure_img = Image.new("RGBA", (1, 1))
    measure_draw = ImageDraw.Draw(measure_img)

    title_lines = []
    body_lines = []
    lh_title = 0
    lh_body = 0

    while title_size >= min_title_size:
        title_font = load_font(BOLD_FONT_PATH, title_size)
        body_font = load_font(FONT_PATH, body_size)

        title_lines = wrap_text(title, title_font, content_w - 20, measure_draw)
        body_lines = wrap_text(text, body_font, content_w - 20, measure_draw)

        lh_title = measure_draw.textbbox((0, 0), "Ay", font=title_font)[3] + 8
        lh_body = measure_draw.textbbox((0, 0), "Ay", font=body_font)[3] + 8

        total_text_h = (len(title_lines) * lh_title) + divider_gap + (len(body_lines) * lh_body)

        if total_text_h <= available_h:
            break

        title_size -= 2
        body_size = max(min_body_size, body_size - 1)

    # Graceful degradation: if still too tall at minimum sizes, truncate body
    title_font = load_font(BOLD_FONT_PATH, title_size)
    body_font = load_font(FONT_PATH, body_size)

    title_block_h = len(title_lines) * lh_title
    remaining_for_body = available_h - title_block_h - divider_gap
    max_body_lines = max(1, int(remaining_for_body / lh_body)) if lh_body > 0 else len(body_lines)

    if len(body_lines) > max_body_lines:
        body_lines = body_lines[:max_body_lines]
        # Add ellipsis to last line
        if body_lines:
            body_lines[-1] = body_lines[-1].rstrip() + "..."

    # ── Render Headline ──
    text_x = cx1 + 10
    for line in title_lines:
        draw_styled_text(draw, (text_x, cursor_y), line, title_font, (*accent_color, 255))
        cursor_y += lh_title

    # ── Divider ──
    cursor_y += 10
    draw_divider(draw, cursor_y, cx1 + 10, cx2 - 10, accent_color)
    cursor_y += divider_gap - 10 + 10

    # ── Render Body ──
    for line in body_lines:
        draw_styled_text(draw, (text_x, cursor_y), line, body_font, (230, 230, 235, 255))
        cursor_y += lh_body

    # ── Slide Number Badge ──
    draw_slide_badge(draw, index, (panel_x1, panel_y1, panel_x2, panel_y2), FONT_PATH)

    # ── Save ──
    slide_path = f"output/slides/slide_{index}.png"
    img.convert("RGB").save(slide_path, "PNG", optimize=True)
    print(f"  🖼️  Slide {index + 1} saved: {slide_path}")

    return slide_path