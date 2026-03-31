from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import os
import numpy as np
import platform

# =========================
# CONFIG
# =========================
SLIDE_W, SLIDE_H = 1080, 1920
PADDING = 100

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
            lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines

# =========================
# BACKGROUND
# =========================
def draw_gradient_background(style="blue"):
    w, h = SLIDE_W, SLIDE_H

    palettes = {
        "blue": [(10, 20, 40), (30, 80, 160)],
        "dark": [(10, 10, 15), (40, 40, 60)],
        "purple": [(30, 10, 50), (100, 40, 140)],
        "orange": [(40, 15, 5), (140, 60, 10)],
    }

    c1, c2 = palettes.get(style, palettes["blue"])

    arr = np.zeros((h, w, 3), dtype=np.uint8)

    for i in range(3):
        arr[:, :, i] = np.linspace(c1[i], c2[i], h).reshape(-1, 1)

    return Image.fromarray(arr, "RGB")

# =========================
# VIGNETTE
# =========================
def add_vignette(img):
    w, h = img.size
    mask = Image.new("L", (w,h), 0)
    d = ImageDraw.Draw(mask)

    d.ellipse([w*0.1, h*0.1, w*0.9, h*0.9], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(300))

    black = Image.new("RGB",(w,h),(0,0,0))
    return Image.composite(img, black, mask)

# =========================
# TEXT STYLE
# =========================
def draw_text(draw, pos, text, font, fill):
    x, y = pos

    # glow
    for i in range(6,0,-1):
        draw.text((x,y), text, font=font, fill=(255,255,255,20*i))

    # shadow
    draw.text((x+4,y+4), text, font=font, fill=(0,0,0,180))

    # main
    draw.text((x,y), text, font=font, fill=fill)

# =========================
# MAIN FUNCTION
# =========================
def create_slide(title, text, index, image_path=None, style="blue", accent_color=(0,180,255)):
    os.makedirs("output/slides", exist_ok=True)

    if image_path and os.path.exists(image_path):
        try:
            base = Image.open(image_path).convert("RGBA")
            img = ImageOps.fit(base, (SLIDE_W, SLIDE_H), method=Image.Resampling.LANCZOS)
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 160))
            img = Image.alpha_composite(img, overlay)
        except Exception as e:
            print(f"Warning: failed building bg from image ({e}), defaulting to gradient.")
            img = draw_gradient_background(style).convert("RGBA")
    else:
        img = draw_gradient_background(style).convert("RGBA")

    img = add_vignette(img).convert("RGBA")
    draw = ImageDraw.Draw(img, "RGBA")

    # 🔥 Layout calculations (Larger glass panel so full text fits)
    panel_w = int(SLIDE_W * 0.85)
    panel_h = int(SLIDE_H * 0.70)

    px1 = (SLIDE_W - panel_w)//2
    py1 = (SLIDE_H - panel_h)//2
    px2 = px1 + panel_w
    py2 = py1 + panel_h

    # 🔹 Separate transparent image for the text layer AND UI boxes
    text_img = Image.new("RGBA", (SLIDE_W, SLIDE_H), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_img)

    # Draw the dark translucent panel and border onto the TEXT layer so it animates with the text
    text_draw.rectangle(
        [(px1, py1), (px2, py2)],
        fill=(10, 15, 20, 120), # Sleek dark tint instead of complex background blur 
        outline=(*accent_color, 120),
        width=2
    )

    title_font_size = 70
    text_font_size = 45
    min_title_size = 40

    max_width = int(SLIDE_W * 0.8)

    # 🔥 Limit lines (important)
    MAX_TEXT_LINES = 10

    while True:
        title_font = load_font(BOLD_FONT_PATH, title_font_size)
        text_font = load_font(FONT_PATH, text_font_size)

        title_lines = wrap_text(title, title_font, max_width, text_draw)
        text_lines = wrap_text(text, text_font, max_width, text_draw)

        if len(text_lines) > MAX_TEXT_LINES:
            text_lines = text_lines[:MAX_TEXT_LINES]

        lh_title = draw.textbbox((0,0),"Ay",font=title_font)[3]
        lh_text = draw.textbbox((0,0),"Ay",font=text_font)[3]

        total_h = len(title_lines)*(lh_title+15) + len(text_lines)*(lh_text+15) + 40 # gap

        if total_h < panel_h - 80:
            break

        title_font_size -= 2
        text_font_size -= 1
        if title_font_size < min_title_size:
            break

    # Center text inside panel
    y = py1 + (panel_h - total_h)//2
    cx = SLIDE_W // 2

    # 🔥 FIXED accent bar (relative position)
    bar_x = px1 + 20
    text_draw.rectangle(
        [(bar_x, py1+40), (bar_x+6, py2-40)],
        fill=(*accent_color, 200)
    )

    # Draw title onto the transparent layer
    for line in title_lines:
        w = text_draw.textbbox((0,0), line, font=title_font)[2]
        x = cx - w//2
        draw_text(text_draw, (x,y), line, title_font, (*accent_color,255))
        y += lh_title + 15

    y += 40 # distinct gap between title and text

    # Draw text onto the transparent layer
    for line in text_lines:
        w = text_draw.textbbox((0,0), line, font=text_font)[2]
        x = cx - w//2
        draw_text(text_draw, (x,y), line, text_font, (240,240,240,255))
        y += lh_text + 15

    # Slide number
    num_font = load_font(FONT_PATH, 40)
    text_draw.text(
        (SLIDE_W-PADDING, SLIDE_H-PADDING),
        f"{index}",
        font=num_font,
        fill=(255,255,255,120),
        anchor="rs"
    )

    bg_path = f"output/slides/slide_bg_{index}.png"
    text_path = f"output/slides/slide_text_{index}.png"

    img.convert("RGB").save(bg_path, "PNG", optimize=True)
    text_img.save(text_path, "PNG", optimize=True)

    return bg_path, text_path