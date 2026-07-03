"""Final assembly: clips + narration → published-ready MP4s.

Produces final/main.mp4 (16:9) and final/short.mp4 (9:16), each with
burned-in captions from the beat narration (faceless channels live and die
by watchability-on-mute).
"""

import subprocess
from pathlib import Path


def assemble(script: dict, clips: list[dict], audio_manifest: list[dict],
             final_dir: Path) -> dict:
    final_dir.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for section in ("main", "short"):
        out = final_dir / f"{section}.mp4"
        _assemble_section(script, section, clips, audio_manifest, final_dir, out)
        outputs[section] = out
    return outputs


def _assemble_section(script, section, clips, audio_manifest, work_dir, out):
    beats = script[section]["beats"]
    section_clips = sorted(
        (c for c in clips if c["section"] == section), key=lambda c: c["index"]
    )
    section_audio = sorted(
        (a for a in audio_manifest if a["section"] == section), key=lambda a: a["index"]
    )

    # 1. Mux narration onto each clip
    muxed = []
    for clip, audio in zip(section_clips, section_audio):
        piece = work_dir / f"muxed_{section}_{clip['index']:02d}.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-i", clip["path"], "-i", audio["path"],
             "-c:v", "copy", "-c:a", "aac", "-shortest", str(piece)],
            check=True, capture_output=True,
        )
        muxed.append(piece)

    # 2. Concat all beats
    concat_list = work_dir / f"concat_{section}.txt"
    concat_list.write_text("".join(f"file '{p.resolve()}'\n" for p in muxed))
    joined = work_dir / f"joined_{section}.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
         "-c", "copy", str(joined)],
        check=True, capture_output=True,
    )

    # 3. Burn captions
    srt = work_dir / f"{section}.srt"
    _write_srt(beats, section_audio, srt)
    style = "FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,Outline=2,MarginV=40"
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(joined),
         "-vf", f"subtitles={srt}:force_style='{style}'",
         "-c:a", "copy", str(out)],
        check=True, capture_output=True,
    )

    # tidy intermediates
    for p in [*muxed, concat_list, joined]:
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
