"""Final assembly: clips + narration → published-ready MP4s.

Produces final/main.mp4 (16:9) and final/short.mp4 (9:16), each with
burned-in captions from the beat narration (faceless channels live and die
by watchability-on-mute).
"""

import subprocess
from pathlib import Path


def _video_size(path) -> tuple[int, int]:
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-select_streams", "v:0", "-show_entries",
         "stream=width,height", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    ).stdout.strip()
    w, h = out.split(",")
    return int(w), int(h)


def _ffmpeg(args: list) -> None:
    """Run ffmpeg, surfacing its stderr on failure instead of swallowing it."""
    proc = subprocess.run([str(a) for a in args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg exited {proc.returncode}: {' '.join(str(a) for a in args)}\n"
            f"--- last output ---\n{proc.stderr[-1500:]}"
        )


def assemble(script: dict, clips: list[dict], audio_manifest: list[dict],
             final_dir: Path, channel: dict | None = None) -> dict:
    final_dir.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for section in ("main", "short"):
        out = final_dir / f"{section}.mp4"
        _assemble_section(script, section, clips, audio_manifest, final_dir, out)
        _add_music(out, channel or {})
        outputs[section] = out
    return outputs


def _add_music(video: Path, channel: dict) -> None:
    """Mix a looped music bed under the narration, auto-ducked.

    Config (channel assembly section):
      assembly:
        music: assets/music/theme.mp3   # relative to repo root
        music_db: -16                   # bed level before ducking
    Silently skipped when unconfigured; warns when the file is missing.
    """
    cfg = (channel.get("assembly") or {})
    if not cfg.get("music"):
        return
    from ..config import REPO_ROOT

    music = REPO_ROOT / cfg["music"]
    if not music.exists():
        print(f"  ⚠ music bed skipped — {music} not found")
        return
    vol = float(cfg.get("music_db", -16))
    tmp = video.with_name(f"tmp_{video.name}")
    # narration ducks the bed via sidechain compression, then both are mixed
    _ffmpeg([
        "ffmpeg", "-y", "-i", video, "-stream_loop", "-1", "-i", music,
        "-filter_complex",
        f"[1:a]volume={vol}dB[bed];"
        "[bed][0:a]sidechaincompress=threshold=0.03:ratio=8:attack=50:release=600[duck];"
        "[0:a][duck]amix=inputs=2:duration=first:normalize=0[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", tmp,
    ])
    tmp.replace(video)


def _assemble_section(script, section, clips, audio_manifest, work_dir, out):
    beats = script[section]["beats"]
    section_clips = sorted(
        (c for c in clips if c["section"] == section), key=lambda c: c["index"]
    )
    section_audio = sorted(
        (a for a in audio_manifest if a["section"] == section), key=lambda a: a["index"]
    )

    # 1. Per beat: composite the caption (PIL PNG + overlay — portable across
    #    ffmpeg builds, no libass needed) and mux the narration
    from .captions import caption_png

    muxed, caption_files = [], []
    for clip, audio, beat in zip(section_clips, section_audio, beats):
        piece = work_dir / f"muxed_{section}_{clip['index']:02d}.mp4"
        size = _video_size(clip["path"])
        cap = work_dir / f"caption_{section}_{clip['index']:02d}.png"
        caption_png(beat["narration"], size, cap)
        caption_files.append(cap)
        _ffmpeg(["ffmpeg", "-y", "-i", clip["path"], "-i", audio["path"],
                 "-i", cap,
                 "-filter_complex", "[0:v][2:v]overlay=0:0[v]",
                 "-map", "[v]", "-map", "1:a",
                 "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                 "-shortest", piece])
        muxed.append(piece)

    # 2. Concat all beats
    concat_list = work_dir / f"concat_{section}.txt"
    concat_list.write_text("".join(f"file '{p.resolve()}'\n" for p in muxed))
    joined = work_dir / f"joined_{section}.mp4"
    _ffmpeg(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
             "-c", "copy", joined])
    joined.replace(out)

    # SRT still written — uploadable to YouTube as closed captions
    _write_srt(beats, section_audio, work_dir / f"{section}.srt")

    # tidy intermediates
    for p in [*muxed, *caption_files, concat_list]:
        p.unlink(missing_ok=True)


def _write_srt(beats, section_audio, path: Path):
    durations = {a["index"]: a["seconds"] for a in section_audio}
    lines, t = [], 0.0
    for i, beat in enumerate(beats):
        dur = durations.get(i, beat["seconds"]) + 0.4
        lines.append(f"{i + 1}\n{_ts(t)} --> {_ts(t + dur)}\n{beat['narration']}\n")
        t += dur
    path.write_text("\n".join(lines))


def _ts(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
