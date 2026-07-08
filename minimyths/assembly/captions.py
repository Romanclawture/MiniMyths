"""Caption rendering via PIL — portable across every ffmpeg build.

libass ('subtitles' filter) is missing from some ffmpeg builds (notably
certain Homebrew bottles), so captions are rendered as full-frame
transparent PNGs and composited with the always-available overlay filter.
"""

from pathlib import Path

from PIL import Image, ImageDraw

from ..visuals.thumbnail import _load_font


def caption_png(text: str, size: tuple[int, int], out: Path) -> Path:
    """Full-frame transparent PNG with the caption laid out at the bottom."""
    w, h = size
    portrait = h > w
    font = _load_font(int(w * (0.042 if portrait else 0.021)))
    # Shorts UI covers the bottom ~15% of portrait video; clear it
    bottom_margin = int(h * 0.16) if portrait else int(h * 0.06)

    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    lines = _wrap(draw, text, font, max_width=int(w * 0.88))
    line_h = int(font.size * 1.25)
    stroke = max(2, font.size // 14)

    y = h - bottom_margin - line_h * len(lines)
    for line in lines:
        draw.text((w // 2, y), line, font=font, fill="white", anchor="ma",
                  stroke_width=stroke, stroke_fill="black")
        y += line_h
    img.save(out)
    return out


def _wrap(draw, text: str, font, max_width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if draw.textlength(candidate, font=font) > max_width and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines
