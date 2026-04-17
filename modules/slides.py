from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import os
import numpy as np
import platform
import config

# =========================
# CONFIG
# =========================
# SLIDE_W, SLIDE_H are now accessed via config.VIDEO_SIZE
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
    w, h = config.VIDEO_SIZE

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
    """Draws crisp text with multiple shadow layers for high readability and depth."""
    x, y = pos

    # Stronger multi-layer shadow for professional 'pop'
    shadow_opacity = 220
    shadow_color = (0, 0, 0, shadow_opacity)
    
    # Draw thicker shadow/glow
    for offset in range(1, 4):
        for dx, dy in [(-offset,-offset), (offset,-offset), (-offset,offset), (offset,offset), (0, offset), (0, -offset), (offset, 0), (-offset, 0)]:
            draw.text((x + dx, y + dy), text, font=font, fill=shadow_color)

    # Main text (crisp, no blur)
    draw.text((x, y), text, font=font, fill=fill)


def get_readable_color(color):
    """Ensures a color is bright enough for a dark background."""
    r, g, b = color[:3]
    # Simple brightness estimate (Luminance)
    brightness = (0.299 * r + 0.587 * g + 0.114 * b)
    
    # If the color is too dark (e.g. dark red/purple), boost it significantly
    if brightness < 130:
        # Boost saturation and value
        factor = 255 / max(r, g, b, 1)
        r = min(255, int(r * factor * 0.9 + 50))
        g = min(255, int(g * factor * 0.9 + 50))
        b = min(255, int(b * factor * 0.9 + 50))
        return (r, g, b)
    
    # Even if somewhat bright, give it a 'neon' boost
    return tuple(min(255, int(c * 1.3 + 30)) for c in (r, g, b))



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
    if isinstance(index, str): return # Do not draw badge for outro / string indices
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
# =========================
# MAIN: LAYERS & INTRO
# =========================
def create_intro_slide(articles):
    """
    Creates a high-impact intro slide with a grid of all article thumbnails.
    Returns: (background_path, panel_path, None)
    """
    os.makedirs("output/slides", exist_ok=True)
    
    # Background (Empty cinematic)
    bg = create_cinematic_background()
    bg_path = "output/slides/intro_bg.png"
    bg.convert("RGB").save(bg_path)

    sw, sh = config.VIDEO_SIZE

    # Panel with Grid
    panel = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(panel)

    # Header
    title_font = load_font(BOLD_FONT_PATH, 80)
    title_text = "TODAY'S TOP STORIES"
    tw = draw.textbbox((0, 0), title_text, font=title_font)[2]
    draw_styled_text(draw, ((sw - tw) // 2, 100), title_text, title_font, (0, 255, 200, 255))

    # Grid logic
    valid_images = [a["local_img_path"] for a in articles if a.get("local_img_path") and os.path.exists(a["local_img_path"])]
    if valid_images:
        num = len(valid_images)
        cols = 2 if num <= 4 else 3
        rows = (num + cols - 1) // cols
        
        # Grid area
        gx1, gy1 = 60, 250
        gx2, gy2 = sw - 60, sh - 100
        gw, gh = gx2 - gx1, gy2 - gy1
        
        cell_w = (gw - (cols - 1) * 20) // cols
        cell_h = (gh - (rows - 1) * 20) // rows
        
        for i, img_path in enumerate(valid_images):
            r, c = i // cols, i % cols
            try:
                thumb_base = Image.open(img_path).convert("RGBA")
                thumb = ImageOps.fit(thumb_base, (cell_w, cell_h), method=Image.Resampling.LANCZOS)
                
                # Rounded mask
                mask = Image.new("L", (cell_w, cell_h), 0)
                ImageDraw.Draw(mask).rounded_rectangle((0, 0, cell_w, cell_h), radius=15, fill=255)
                thumb.putalpha(mask)
                
                px = gx1 + c * (cell_w + 20)
                py = gy1 + r * (cell_h + 20)
                panel.paste(thumb, (px, py), thumb)
                
                # Neon outline for each cell
                ImageDraw.Draw(panel).rounded_rectangle((px, py, px+cell_w, py+cell_h), radius=15, outline=(0, 255, 200, 150), width=2)
            except:
                continue

    panel_path = "output/slides/intro_panel.png"
    panel.save(panel_path)
    return bg_path, panel_path, None


def create_titles_slide(results):
    """
    Creates a slide listing all headlines.
    """
    os.makedirs("output/slides", exist_ok=True)
    
    bg = create_cinematic_background()
    bg_path = "output/slides/titles_bg.png"
    bg.convert("RGB").save(bg_path)

    sw, sh = config.VIDEO_SIZE
    panel = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(panel)

    # Background panel
    margin = 50
    draw.rounded_rectangle([(margin, margin), (sw - margin, sh - margin)], radius=20, fill=(10, 15, 22, 200))
    draw_neon_border(draw, (margin, margin, sw - margin, sh - margin), (0, 255, 200))

    # Header
    title_font = load_font(BOLD_FONT_PATH, 70)
    header_text = "TODAY'S TOP STORIES"
    tw = draw.textbbox((0, 0), header_text, font=title_font)[2]
    draw_styled_text(draw, ((sw - tw) // 2, 80), header_text, title_font, (0, 255, 200, 255))

    # List titles
    y = 180
    list_font_size = 48
    if len(results) > 8:
        list_font_size = 36
    
    list_font = load_font(FONT_PATH, list_font_size)
    for i, r in enumerate(results):
        thumb_img = None
        thumb_w, thumb_h = 0, 0
        
        if r.get("local_img_path") and os.path.exists(r["local_img_path"]):
            try:
                base_h = 80 if len(results) <= 5 else 60
                base_w = int(base_h * (16/9))
                t_base = Image.open(r["local_img_path"]).convert("RGBA")
                t_base = ImageOps.fit(t_base, (base_w, base_h), method=Image.Resampling.LANCZOS)
                mask = Image.new("L", (base_w, base_h), 0)
                ImageDraw.Draw(mask).rounded_rectangle((0, 0, base_w, base_h), radius=8, fill=255)
                t_base.putalpha(mask)
                thumb_img = t_base
                thumb_w, thumb_h = base_w, base_h
            except Exception:
                pass
                
        text_x = 100 + thumb_w + 20 if thumb_img else 100
        max_w = sw - text_x - 50
        
        bullet_text = f"{i+1}. {r['title']}"
        lines = wrap_text(bullet_text, list_font, max_w, draw)
        
        lh = draw.textbbox((0, 0), "Ay", font=list_font)[3] + 8
        total_text_h = len(lines) * lh
        
        if thumb_img:
            panel.paste(thumb_img, (100, y + max(0, (total_text_h - thumb_h) // 2)), thumb_img)
            
        for line in lines:
            draw_styled_text(draw, (text_x, y), line, list_font, (230, 230, 235, 255))
            y += lh
            y += 5
        y += 20
        if y > sh - 100: break

    panel_path = "output/slides/titles_panel.png"
    panel.save(panel_path)
    return bg_path, panel_path, None


def create_layered_slide(title, text, index, image_path=None, accent_color=(0, 180, 255)):
    """
    Returns: (background_path, frame_path, text_path)
    """
    os.makedirs("output/slides", exist_ok=True)

    # 1. BACKGROUND LAYER
    bg = create_cinematic_background(image_path)
    bg_path = f"output/slides/bg_{index}.png"
    bg.convert("RGB").save(bg_path)

    sw, sh = config.VIDEO_SIZE

    # 2. FRAME LAYER (Box + Border + Image)
    frame = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    draw_frame = ImageDraw.Draw(frame)

    # 3. TEXT LAYER (Header + Summary)
    text_layer = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    draw_text = ImageDraw.Draw(text_layer)

    # ── Panel dimensions ──
    margin = 15  # Small equal margin for "edge to edge" look
    panel_x1 = margin
    panel_y1 = margin
    panel_x2 = sw - margin
    panel_y2 = sh - margin
    panel_w = panel_x2 - panel_x1
    panel_h = panel_y2 - panel_y1

    # Glass panel fill (Slightly lighter, more "glassy" tint)
    draw_frame.rounded_rectangle(
        [(panel_x1, panel_y1), (panel_x2, panel_y2)],
        radius=20,
        fill=(15, 20, 28, 180) # Slightly more transparent, lighter base
    )
    
    # White inner "shine" for glass effect
    draw_frame.rounded_rectangle(
        [(panel_x1 + 2, panel_y1 + 2), (panel_x2 - 2, panel_y2 - 2)],
        radius=18,
        outline=(255, 255, 255, 30), # Very subtle white highlight
        width=1
    )

    # Neon border
    draw_neon_border(draw_frame, (panel_x1, panel_y1, panel_x2, panel_y2), accent_color)

    # ── Inner content area ──
    content_pad = 25 # Reduced padding
    cx1 = panel_x1 + content_pad
    cy1 = panel_y1 + content_pad
    cx2 = panel_x2 - content_pad
    content_w = cx2 - cx1

    cursor_y = cy1
    is_landscape = sw > sh

    # ── Inner Thumbnail ──
    thumb_h = 0
    thumb_w = 0
    if image_path and os.path.exists(image_path):
        try:
            if is_landscape:
                # Landscape: Thumbnail on the left
                thumb_w = int(content_w * 0.45)
                thumb_h_max = panel_h - (content_pad * 2)
                tw = thumb_w
                th = int(tw * (9 / 16))
                if th > thumb_h_max:
                    th = thumb_h_max
                    tw = int(th * (16 / 9))
            else:
                # Portrait: Full width vertical stack
                tw = content_w
                th = int(tw * (9 / 16))

            thumb_base = Image.open(image_path).convert("RGBA")
            thumb = ImageOps.fit(thumb_base, (tw, th), method=Image.Resampling.LANCZOS)

            image_mask = Image.new("L", (tw, th), 0)
            mask_draw = ImageDraw.Draw(image_mask)
            mask_draw.rounded_rectangle((0, 0, tw, th), radius=20, fill=255)
            thumb.putalpha(image_mask)

            frame.paste(thumb, (cx1, cursor_y), thumb)
            
            if is_landscape:
                # Text will start to the right of the image
                text_x_start = cx1 + tw + 30
                content_w = cx2 - text_x_start
            else:
                thumb_h = th + 25
                cursor_y += thumb_h
                text_x_start = cx1 + 10
        except Exception as e:
            print(f"Warning: thumbnail render failed: {e}")
            text_x_start = cx1 + 10
    else:
        text_x_start = cx1 + 10

    # ── Available space for text ──
    badge_reserve = 60  # Space for the badge at the bottom
    available_h = (panel_y2 - content_pad - badge_reserve) - cursor_y
    divider_gap = 30  # Space for the divider between headline & body

    # ── Adaptive Typography ──
    max_title_size = 90
    max_body_size = 60
    min_title_size = 40
    min_body_size = 30
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
        if body_lines:
            body_lines[-1] = body_lines[-1].rstrip() + "..."
            
    # Center Vertically
    actual_text_h = (len(title_lines) * lh_title) + divider_gap + (len(body_lines) * lh_body)
    if actual_text_h < available_h:
        cursor_y += (available_h - actual_text_h) // 2

    # ── Render Headline ──
    # Use the enhanced color logic to ensure visibility
    header_color = get_readable_color(accent_color)
    
    for line in title_lines:
        draw_styled_text(draw_text, (text_x_start, cursor_y), line, title_font, (*header_color, 255))
        cursor_y += lh_title


    # ── Divider ──
    cursor_y += 10
    draw_divider(draw_text, cursor_y, text_x_start, cx2 - 10, accent_color)
    cursor_y += divider_gap - 10 + 10

    # ── Render Body ──
    # Pure bright white for body text
    for line in body_lines:
        draw_styled_text(draw_text, (text_x_start, cursor_y), line, body_font, (255, 255, 255, 255))
        cursor_y += lh_body

    # ── Slide Number Badge ──
    draw_slide_badge(draw_frame, index, (panel_x1, panel_y1, panel_x2, panel_y2), FONT_PATH)

    # ── Save Layers ──
    # 🔥 CRITICAL: Force RGB/RGBA conversion and remove any metadata that causes BGR swaps or channel issues in MoviePy
    frame_path = f"output/slides/frame_{index}.png"
    text_path = f"output/slides/text_{index}.png"
    
    # We strip info dict and save as clean RGBA to prevent color channel distortion
    frame = frame.convert("RGBA")
    text_layer = text_layer.convert("RGBA")
    
    frame.save(frame_path, "PNG")
    text_layer.save(text_path, "PNG")
    
    slide_id = index if isinstance(index, str) else index + 1
    print(f"  🖼️  Layered Slide {slide_id} generated (split-layer mode).")
    return bg_path, frame_path, text_path