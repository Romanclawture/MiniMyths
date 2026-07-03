"""Turn scene stills into moving clips.

Default backend is `ken_burns`: slow zoom/pan over each image via FFmpeg's
zoompan filter. It's what most successful faceless story channels actually
use — reliable, instant, $0 — and it ships video #1 while generative video
(Wan 2.2 / LTX-2 via Wan2GP or Draw Things) stays an upgrade path.
See docs/video-generation.md.
"""

import subprocess
from pathlib import Path

FPS = 30


def render_clips(script: dict, frames_dir: Path, audio_manifest: list[dict],
                 out_dir: Path, channel: dict) -> list[dict]:
    """One clip per beat, sized to that beat's actual narration length.

    Returns [{"section", "index", "path"}, ...].
    """
    backend = channel["visuals"].get("motion_backend", "ken_burns")
    if backend != "ken_burns":
        raise NotImplementedError(
            f"motion_backend '{backend}' is a planned upgrade path (wan2gp, ltx, "
            "draw_things) — see docs/video-generation.md. Use ken_burns for now."
        )

    durations = {(m["section"], m["index"]): m["seconds"] for m in audio_manifest}
    out_dir.mkdir(parents=True, exist_ok=True)

    clips = []
    for section in ("main", "short"):
        for i, beat in enumerate(script[section]["beats"]):
            image = frames_dir / f"{section}_{i:02d}.png"
            clip = out_dir / f"{section}_{i:02d}.mp4"
            # pad narration with a beat of breathing room
            seconds = durations.get((section, i), beat["seconds"]) + 0.4
            _ken_burns(image, clip, seconds, zoom_in=(i % 2 == 0))
            clips.append({"section": section, "index": i, "path": str(clip)})
    return clips


def _ken_burns(image: Path, out: Path, seconds: float, zoom_in: bool) -> None:
    """Slow zoom over a still. Alternating in/out keeps cuts feeling alive."""
    frames = max(int(seconds * FPS), FPS)
    if zoom_in:
        zoom = f"min(1+0.10*on/{frames},1.10)"
    else:
        zoom = f"max(1.10-0.10*on/{frames},1.0)"
    # upscale first so zoompan has pixels to spare (avoids jitter)
    vf = (
        "scale=iw*2:ih*2,"
        f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={frames}:s={_size_arg(image)}:fps={FPS}"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-loop", "1", "-i", str(image), "-vf", vf,
         "-t", f"{seconds:.2f}", "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-r", str(FPS), str(out)],
        check=True, capture_output=True,
    )


def _size_arg(image: Path) -> str:
    from PIL import Image

    with Image.open(image) as img:
        return f"{img.width}x{img.height}"
