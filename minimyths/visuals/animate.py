"""Draw Things image-to-video backend — real animation, rendered locally.

Drives the Draw Things app's API server (Settings → API Server, HTTP on
127.0.0.1:7860) running a Wan 2.2 5B image-to-video model. Each beat's
keyframe becomes a genuinely animated clip; because I2V clips are shorter
than most beats, the clip settles into a slow Ken Burns hold on its final
frame for the remaining narration time.

Clips cache on keyframe + prompt + params, so an interrupted overnight run
resumes where it stopped. See docs/draw-things-setup.md.
"""

import base64
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

import requests

from .motion import FPS as OUT_FPS
from .motion import _ken_burns

DEFAULTS = {
    "url": "http://127.0.0.1:7860",
    # Wan 2.2 5B is trained at 24 fps, 1280x704-class resolutions
    "num_frames": 81,          # ~3.4s of real motion per beat
    "fps": 24,
    "steps": 30,
    "width": 1280, "height": 704,     # landscape; swapped for portrait
    "timeout": 7200,
}


def check_server(cfg: dict) -> None:
    url = {**DEFAULTS, **cfg}["url"]
    try:
        requests.get(url, timeout=10)
    except requests.RequestException as e:
        raise RuntimeError(
            f"Draw Things API server not reachable at {url}. Open Draw Things, "
            "enable Settings → API Server (HTTP), load the Wan 2.2 5B I2V "
            "model, and keep the app open. See docs/draw-things-setup.md."
        ) from e


def animated_clip(keyframe: Path, out: Path, seconds: float, prompt: str,
                  portrait: bool, cfg: dict) -> None:
    """Animate one keyframe into a `seconds`-long clip (I2V + hold)."""
    cfg = {**DEFAULTS, **cfg}
    cache_key = _cache_key(keyframe, prompt, cfg)
    sidecar = out.with_suffix(".motion.txt")
    if out.exists() and sidecar.exists() and sidecar.read_text() == cache_key:
        return

    w, h = (cfg["height"], cfg["width"]) if portrait else (cfg["width"], cfg["height"])
    payload = {
        "prompt": prompt,
        "init_images": [base64.b64encode(keyframe.read_bytes()).decode()],
        "width": w, "height": h,
        "num_frames": cfg["num_frames"],
        "steps": cfg["steps"],
        **cfg.get("extra", {}),   # passthrough for model-specific knobs
    }
    resp = requests.post(f"{cfg['url']}/sdapi/v1/img2img", json=payload,
                         timeout=cfg["timeout"])
    resp.raise_for_status()
    frames = resp.json().get("images", [])
    if len(frames) < 2:
        raise RuntimeError(
            f"Draw Things returned {len(frames)} image(s), not a frame "
            "sequence — check that a video model (Wan 2.2 5B I2V) is selected "
            "in the app."
        )

    target = _target_size(keyframe)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for i, b64 in enumerate(frames):
            (td / f"f_{i:04d}.png").write_bytes(base64.b64decode(b64))
        motion_part = td / "motion.mp4"
        _frames_to_clip(td, motion_part, cfg["fps"], target)
        _extend_with_hold(motion_part, td, seconds, out, target)
    sidecar.write_text(cache_key)


def _cache_key(keyframe: Path, prompt: str, cfg: dict) -> str:
    img_hash = hashlib.md5(keyframe.read_bytes()).hexdigest()
    return f"{img_hash}|{prompt}|{json.dumps(cfg, sort_keys=True, default=str)}"


def _target_size(keyframe: Path) -> tuple[int, int]:
    from PIL import Image

    with Image.open(keyframe) as img:
        return img.size


def _frames_to_clip(frames_dir: Path, out: Path, fps: int,
                    target: tuple[int, int]) -> None:
    w, h = target
    _run(["ffmpeg", "-y", "-framerate", fps, "-i", frames_dir / "f_%04d.png",
          "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                 f"crop={w}:{h},fps={OUT_FPS}",
          "-c:v", "libx264", "-pix_fmt", "yuv420p", out])


def _extend_with_hold(motion: Path, td: Path, seconds: float, out: Path,
                      target: tuple[int, int]) -> None:
    """Real motion first, then a slow Ken Burns hold on the last frame."""
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(motion)], capture_output=True, text=True)
    motion_s = float(probe.stdout.strip() or 0)

    if motion_s >= seconds:
        _run(["ffmpeg", "-y", "-i", motion, "-t", f"{seconds:.2f}",
              "-c", "copy", out])
        return

    last = td / "last.png"
    _run(["ffmpeg", "-y", "-sseof", "-0.1", "-i", motion,
          "-update", "1", "-frames:v", "1", last])
    hold = td / "hold.mp4"
    _ken_burns(last, hold, seconds - motion_s, zoom_in=True)
    concat = td / "concat.txt"
    concat.write_text(f"file '{motion.resolve()}'\nfile '{hold.resolve()}'\n")
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat,
          "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(OUT_FPS), out])


def _run(args: list) -> None:
    proc = subprocess.run([str(a) for a in args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed ({proc.returncode}):\n{proc.stderr[-1200:]}"
        )
