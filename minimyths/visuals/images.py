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

import yaml

from ..config import REPO_ROOT

SIZES = {"main": (1920, 1080), "short": (1080, 1920)}
STYLES_PATH = REPO_ROOT / "config" / "styles.yaml"


def resolve_style(script: dict, channel: dict) -> dict:
    """Style pack for this episode: script's `style` key beats channel default."""
    styles = yaml.safe_load(STYLES_PATH.read_text())
    name = script.get("style") or channel["visuals"].get("style", "painted-epic")
    if name not in styles:
        raise KeyError(f"Unknown style '{name}'. Available: {', '.join(sorted(styles))}")
    return {"name": name, **styles[name]}


def generate_images(script: dict, out_dir: Path, channel: dict) -> list[Path]:
    backend = channel["visuals"].get("image_backend", "placeholder")
    pack = resolve_style(script, channel)
    suffix = pack["suffix"].strip()
    fast = channel["visuals"].get("image_quality", "final") == "fast"
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = []
    for section in ("main", "short"):
        for i, beat in enumerate(script[section]["beats"]):
            path = out_dir / f"{section}_{i:02d}.png"
            _render_beat(beat, path, SIZES[section], backend, pack, fast)
            paths.append(path)
    return paths


def generate_one(script: dict, section: str, index: int, out_dir: Path,
                 channel: dict) -> Path:
    """Regenerate a single beat's image — the `reroll` command."""
    backend = channel["visuals"].get("image_backend", "placeholder")
    pack = resolve_style(script, channel)
    fast = channel["visuals"].get("image_quality", "final") == "fast"
    beat = script[section]["beats"][index]
    path = out_dir / f"{section}_{index:02d}.png"
    _render_beat(beat, path, SIZES[section], backend, pack, fast)
    return path


def _render_beat(beat: dict, path: Path, size: tuple[int, int],
                 backend: str, pack: dict, fast: bool) -> None:
    suffix = pack["suffix"].strip()
    prompt = f"{beat['visual']}, {suffix}" if suffix else beat["visual"]
    if backend == "placeholder":
        _placeholder(prompt, path, size)
    elif backend == "diffusers":
        _diffusers(prompt, path, size, negative=pack.get("negative", ""),
                   lora=pack.get("lora"), fast=fast)
    else:
        raise ValueError(f"Unknown image backend: {backend}")


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


# SDXL generates at native buckets; we upscale to the video resolution after.
SDXL_BUCKETS = {(1920, 1080): (1344, 768), (1080, 1920): (768, 1344)}

_PIPE_CACHE = {"key": None, "pipe": None}  # model+LoRA loads take ~30s; reuse


def _diffusers(prompt: str, path: Path, size: tuple[int, int],
               negative: str = "", lora: str | None = None,
               fast: bool = False) -> None:
    """Local SDXL via diffusers on Apple Silicon (mps).

    fast=False (default): full SDXL, 30 steps — the quality path.
    fast=True: SDXL-Turbo, 4 steps — quick previews (negative/lora ignored;
    Turbo doesn't use guidance).
    LoRA: style packs may name a file in assets/loras/ (see styles.yaml).
    """
    import torch
    from diffusers import AutoPipelineForText2Image

    model = "stabilityai/sdxl-turbo" if fast else "stabilityai/stable-diffusion-xl-base-1.0"
    lora_path = str(REPO_ROOT / "assets" / "loras" / lora) if lora else None
    key = (model, lora_path)
    if _PIPE_CACHE["key"] != key:
        device = "mps" if torch.backends.mps.is_available() else "cpu"
        pipe = AutoPipelineForText2Image.from_pretrained(
            model, torch_dtype=torch.float16,
        ).to(device)
        if lora_path:
            pipe.load_lora_weights(lora_path)
        _PIPE_CACHE.update(key=key, pipe=pipe)
    pipe = _PIPE_CACHE["pipe"]

    gen_size = SDXL_BUCKETS.get(size, size)
    kwargs = dict(prompt=prompt, width=gen_size[0], height=gen_size[1])
    if fast:
        kwargs.update(num_inference_steps=4, guidance_scale=0.0)
    else:
        kwargs.update(num_inference_steps=30, guidance_scale=7.0,
                      negative_prompt=negative or None)
    image = pipe(**kwargs).images[0]
    image = image.resize(size)
    image.save(path)
