"""Image-to-video engines: fal.ai (hosted, quality) and Draw Things (local).

Both animate a beat's keyframe into a clip, then settle into a slow Ken
Burns hold on the final frame for the remaining narration time. Clips cache
on keyframe + prompt + params, so interrupted runs resume where they stopped.

- fal: frontier-quality clips (Kling / Wan 14B class) in ~1-2 min each,
  roughly $0.25-0.40 per 5s clip. Needs FAL_KEY. See docs/fal-setup.md.
- draw_things: local Wan 2.2 5B via the Draw Things app's API server.
  $0 but slow and modest quality on a 16GB mini. docs/draw-things-setup.md.
"""

import base64
import hashlib
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import requests

from .motion import FPS as OUT_FPS
from .motion import _ken_burns

# Conservative first-run defaults for a 16GB M4 mini — measure with
# `minimyths animate`, then raise num_frames/steps/resolution in the channel
# config's draw_things section as time and memory allow.
# Wan 2.2 5B is trained at 24 fps, up to 1280x704-class resolutions.
DEFAULTS = {
    "url": "http://127.0.0.1:7860",
    "num_frames": 49,          # ~2s of real motion per beat (Wan wants 4k+1)
    "fps": 24,
    "steps": 20,
    # Draw Things requires 64-px increments; 1024x576 is exact 16:9
    "width": 1024, "height": 576,     # landscape; swapped for portrait
    "timeout": 7200,
}


FAL_DEFAULTS = {
    "model": "fal-ai/kling-video/v2.5-turbo/pro/image-to-video",
    "duration": "5",           # seconds of real motion per beat
    "timeout": 900,
    "poll_seconds": 5,
}


def check_fal(cfg: dict) -> None:
    if not os.environ.get("FAL_KEY"):
        raise SystemExit(
            "FAL_KEY not set. Create an account at fal.ai, generate a key\n"
            "(fal.ai/dashboard/keys), then:  export FAL_KEY=...\n"
            "Full guide: docs/fal-setup.md"
        )


def fal_clip(keyframe: Path, out: Path, seconds: float, prompt: str,
             portrait: bool, cfg: dict) -> None:
    """Animate one keyframe via a hosted fal.ai I2V model (I2V + hold)."""
    cfg = {**FAL_DEFAULTS, **cfg}
    cache_key = _cache_key(keyframe, prompt, cfg)
    sidecar = out.with_suffix(".motion.txt")
    if out.exists() and sidecar.exists() and sidecar.read_text() == cache_key:
        return

    data_uri = ("data:image/png;base64,"
                + base64.b64encode(keyframe.read_bytes()).decode())
    payload = {"prompt": prompt, "image_url": data_uri,
               "duration": str(cfg["duration"]), **cfg.get("extra", {})}
    headers = {"Authorization": f"Key {os.environ['FAL_KEY']}"}

    queued = requests.post(f"https://queue.fal.run/{cfg['model']}",
                           json=payload, headers=headers, timeout=120)
    if queued.status_code not in (200, 201, 202):
        raise RuntimeError(
            f"fal.ai rejected the request ({queued.status_code}): "
            f"{queued.text[:600]}"
        )
    job = queued.json()
    status_url = job["status_url"]
    response_url = job["response_url"]

    deadline = time.monotonic() + cfg["timeout"]
    while True:
        status = requests.get(status_url, headers=headers, timeout=60).json()
        if status.get("status") == "COMPLETED":
            break
        if status.get("status") in ("FAILED", "CANCELLED", "ERROR"):
            raise RuntimeError(f"fal.ai job failed: {json.dumps(status)[:600]}")
        if time.monotonic() > deadline:
            raise RuntimeError(f"fal.ai job timed out after {cfg['timeout']}s")
        time.sleep(cfg["poll_seconds"])

    result = requests.get(response_url, headers=headers, timeout=120).json()
    video_url = (result.get("video") or {}).get("url")
    if not video_url:
        raise RuntimeError(f"fal.ai response had no video url: {json.dumps(result)[:600]}")

    target = _target_size(keyframe)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        raw = td / "raw.mp4"
        with requests.get(video_url, stream=True, timeout=600) as dl:
            dl.raise_for_status()
            with open(raw, "wb") as f:
                for chunk in dl.iter_content(1 << 20):
                    f.write(chunk)
        motion_part = td / "motion.mp4"
        w, h = target
        _run(["ffmpeg", "-y", "-i", raw,
              "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                     f"crop={w}:{h},fps={OUT_FPS}",
              "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", motion_part])
        _extend_with_hold(motion_part, td, seconds, out, target)
    sidecar.write_text(cache_key)


def check_server(cfg: dict) -> None:
    url = {**DEFAULTS, **cfg}["url"]
    try:
        requests.get(url, timeout=10)
    except requests.RequestException:
        raise SystemExit(
            f"Draw Things API server not reachable at {url}.\n"
            "In Draw Things: Settings → API Server → enable (HTTP, port 7860),\n"
            "select the Wan 2.2 5B model in the app, and keep it open.\n"
            f"Check with:  curl {url}/\n"
            "Full guide: docs/draw-things-setup.md"
        ) from None


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
        # Draw Things requires the init image to match the output dimensions
        "init_images": [_resized_b64(keyframe, w, h)],
        "width": w, "height": h,
        "num_frames": cfg["num_frames"],
        "steps": cfg["steps"],
        **cfg.get("extra", {}),   # passthrough for model-specific knobs
    }
    resp = requests.post(f"{cfg['url']}/sdapi/v1/img2img", json=payload,
                         timeout=cfg["timeout"])
    if resp.status_code != 200:
        sent = {k: v for k, v in payload.items() if k != "init_images"}
        raise RuntimeError(
            f"Draw Things rejected the request ({resp.status_code}).\n"
            f"Server said: {resp.text[:800] or '(empty body)'}\n"
            f"Payload (minus image data): {json.dumps(sent)}"
        )
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


def _resized_b64(keyframe: Path, w: int, h: int) -> str:
    import io

    from PIL import Image

    with Image.open(keyframe) as img:
        scale = max(w / img.width, h / img.height)
        img = img.convert("RGB").resize(
            (round(img.width * scale), round(img.height * scale)))
        left, top = (img.width - w) // 2, (img.height - h) // 2
        img = img.crop((left, top, left + w, top + h))
        buf = io.BytesIO()
        img.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


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
