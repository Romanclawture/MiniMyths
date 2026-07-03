"""Thumbnail generation — the single biggest click-through lever.

Composes a 1280x720 JPEG from:
- the hook beat's scene image (frames/main_00.png), cropped to fill
- a darkening gradient so text pops
- 2-4 huge stroke-outlined words (script's `thumbnail_text`, else the title
  up to the colon), plus an accent underline bar
- the channel name as a small corner watermark

Style knobs live in the channel config under `thumbnail:`.
YouTube limit: 1280x720, under 2MB.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

SIZE = (1280, 720)

FONT_CANDIDATES = [
    # Linux
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    # macOS
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Impact.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


def generate_thumbnail(script: dict, work_dir: Path, channel: dict) -> Path:
    """Render final/thumbnail.jpg for a produced video."""
    cfg = channel.get("thumbnail", {})
    accent = cfg.get("accent", "#FFB800")
    text = (script.get("thumbnail_text") or script["title"].split(":")[0]).upper()

    hero = work_dir / "frames" / "main_00.png"
    canvas = _background(hero if hero.exists() else None)
    _burn_text(canvas, text, accent, channel.get("name", ""))

    out = work_dir / "final" / "thumbnail.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out, "JPEG", quality=90)
    return out


def _background(hero: Path | None) -> Image.Image:
    if hero:
        img = Image.open(hero).convert("RGB")
        img = _cover_crop(img, SIZE)
        img = ImageEnhance.Contrast(img).enhance(1.15)
        img = ImageEnhance.Color(img).enhance(1.25)
    else:
        img = Image.new("RGB", SIZE, (24, 22, 40))

    # left-to-right dark gradient behind the text zone
    overlay = Image.new("L", SIZE, 0)
    dr = ImageDraw.Draw(overlay)
    for x in range(SIZE[0]):
        alpha = max(0, 190 - int(x * 190 / (SIZE[0] * 0.72)))
        dr.line([(x, 0), (x, SIZE[1])], fill=alpha)
    black = Image.new("RGB", SIZE, (0, 0, 0))
    return Image.composite(black, img, overlay)


def _cover_crop(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    tw, th = size
    scale = max(tw / img.width, th / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)))
    left, top = (img.width - tw) // 2, (img.height - th) // 2
    return img.crop((left, top, left + tw, top + th))


def _burn_text(canvas: Image.Image, text: str, accent: str, watermark: str) -> None:
    draw = ImageDraw.Draw(canvas)
    margin, max_width = 64, int(SIZE[0] * 0.60)

    words = text.split()
    lines = _balance_lines(words, max_lines=3)
    font, line_sizes = _fit_font(draw, lines, max_width, start=150, floor=72)

    line_gap = int(font.size * 0.18)
    total_h = sum(h for _, h in line_sizes) + line_gap * (len(lines) - 1)
    y = (SIZE[1] - total_h) // 2

    stroke = max(4, font.size // 18)
    for line, (w, h) in zip(lines, line_sizes):
        draw.text((margin, y), line, font=font, fill="white",
                  stroke_width=stroke, stroke_fill="black")
        y += h + line_gap

    # accent bar under the block
    bar_w = max(w for w, _ in line_sizes)
    draw.rectangle([margin, y + 6, margin + int(bar_w * 0.55), y + 22], fill=accent)

    if watermark:
        wm_font = _load_font(34)
        draw.text((SIZE[0] - 24, SIZE[1] - 20), watermark.upper(), font=wm_font,
                  fill=(255, 255, 255, 220), anchor="rs",
                  stroke_width=2, stroke_fill="black")


def _balance_lines(words: list[str], max_lines: int) -> list[str]:
    """Split words into up to max_lines visually balanced lines."""
    n_lines = min(len(words), 2 if len(words) <= 4 else max_lines)
    per, lines, i = -(-len(words) // n_lines), [], 0
    while i < len(words):
        lines.append(" ".join(words[i:i + per]))
        i += per
    return lines


def _fit_font(draw, lines, max_width, start, floor):
    size = start
    while size > floor:
        font = _load_font(size)
        sizes = [draw.textbbox((0, 0), ln, font=font)[2:] for ln in lines]
        if max(w for w, _ in sizes) <= max_width:
            return font, sizes
        size -= 6
    font = _load_font(floor)
    return font, [draw.textbbox((0, 0), ln, font=font)[2:] for ln in lines]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size)
