"""Scene image generation — one still per beat.

Backends (channel config `visuals.image_backend`):
- placeholder: styled gradient + scene text. Lets the whole pipeline run
  end-to-end today with zero setup; swap backend later, regenerate, done.
- diffusers:   local Stable Diffusion on the Mac mini (SDXL-Turbo). $0.
- api:         hosted image API — plug in when a provider is chosen.

Main video renders at 1920x1080; shorts at 1080x1920.
"""

import hashlib
from pathlib import Path

SIZES = {"main": (1920, 1080), "short": (1080, 1920)}


def generate_images(script: dict, out_dir: Path, channel: dict) -> list[Path]:
    backend = channel["visuals"].get("image_backend", "placeholder")
    style = channel["visuals"].get("style_suffix", "").strip()
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = []
    for section in ("main", "short"):
        size = SIZES[section]
        for i, beat in enumerate(script[section]["beats"]):
            path = out_dir / f"{section}_{i:02d}.png"
            prompt = f"{beat['visual']}, {style}" if style else beat["visual"]
            if backend == "placeholder":
                _placeholder(prompt, path, size)
            elif backend == "diffusers":
                _diffusers(prompt, path, size)
            else:
                raise ValueError(f"Unknown image backend: {backend}")
            paths.append(path)
    return paths


def _placeholder(prompt: str, path: Path, size: tuple[int, int]) -> None:
    """Deterministic styled gradient with the scene prompt rendered on it."""
    from PIL import Image, ImageDraw

    w, h = size
    seed = int(hashlib.md5(prompt.encode()).hexdigest()[:6], 16)
    top = ((seed >> 16) & 0xFF // 2 + 20, (seed >> 8) & 0x7F + 20, seed & 0x7F + 40)
    bottom = (top[2] + 30, top[0] // 2 + 10, top[1] + 60)

    img = Image.new("RGB", size)
    for y in range(h):
        t = y / h
        row = tuple(int(a + (b - a) * t) for a, b in zip(top, bottom))
        img.paste(Image.new("RGB", (w, 1), row), (0, y))

    draw = ImageDraw.Draw(img)
    text = "\n".join(_wrap(prompt, 48))
    draw.multiline_text((w // 2, h // 2), text, fill=(255, 255, 255),
                        anchor="mm", align="center")
    img.save(path)


def _wrap(text: str, width: int) -> list[str]:
    words, lines, line = text.split(), [], ""
    for word in words:
        if len(line) + len(word) + 1 > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return lines[:8]


def _diffusers(prompt: str, path: Path, size: tuple[int, int]) -> None:
    """Local SDXL-Turbo via diffusers — targets Apple Silicon (mps)."""
    import torch
    from diffusers import AutoPipelineForText2Image

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    pipe = AutoPipelineForText2Image.from_pretrained(
        "stabilityai/sdxl-turbo", torch_dtype=torch.float16,
    ).to(device)
    image = pipe(prompt=prompt, num_inference_steps=4, guidance_scale=0.0).images[0]
    image = image.resize(size)
    image.save(path)
