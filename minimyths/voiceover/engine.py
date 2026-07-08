"""Voiceover generation — one audio file per beat.

Backends (selected in channel config `voiceover.backend`):
- elevenlabs: best quality, ~$5-22/mo. Needs ELEVENLABS_API_KEY.
- kokoro:     free, local, surprisingly good. Recommended once installed.
- piper:      free, local, fastest, lighter quality. Good for drafts.
- espeak:     robotic draft voice, zero dependencies (apt/brew install
              espeak-ng). Only for reviewing pacing/edit — never publish.

See docs/tts-research.md for the comparison.
"""

import json
from pathlib import Path


def generate_voiceover(script: dict, out_dir: Path, channel: dict) -> list[dict]:
    """Render narration for every beat in main+short.

    Returns a manifest: [{"section", "index", "path", "seconds"}, ...],
    also written to out_dir/manifest.json for the assembly stage.
    """
    backend_name = channel["voiceover"]["backend"]
    voice = channel["voiceover"].get("voice", "")
    synth = _get_backend(backend_name)
    if backend_name == "kokoro":
        import functools

        speed = float(channel["voiceover"].get("speed", 1.0))
        synth = functools.partial(_kokoro, speed=speed)

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for section in ("main", "short"):
        for i, beat in enumerate(script[section]["beats"]):
            path = out_dir / f"{section}_{i:02d}.mp3"
            # narration sidecar = cache key: restyles keep narration, so the
            # already-generated audio is reused instead of re-synthesized
            sidecar = path.with_suffix(".txt")
            cache_key = f"{backend_name}/{voice}\n{beat['narration']}"
            if path.exists() and sidecar.exists() and sidecar.read_text() == cache_key:
                seconds = _audio_seconds(path)
            else:
                seconds = synth(beat["narration"], path, voice)
                sidecar.write_text(cache_key)
            manifest.append({
                "section": section, "index": i,
                "path": str(path), "seconds": seconds,
            })
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def _get_backend(name: str):
    if name == "elevenlabs":
        return _elevenlabs
    if name == "kokoro":
        return _kokoro
    if name == "piper":
        return _piper
    if name == "espeak":
        return _espeak
    raise ValueError(f"Unknown voiceover backend: {name}")


def _audio_seconds(path: Path) -> float:
    """Duration via ffprobe (ships with ffmpeg)."""
    import subprocess

    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    return float(out.stdout.strip() or 0)


def _elevenlabs(text: str, path: Path, voice: str) -> float:
    from elevenlabs.client import ElevenLabs

    client = ElevenLabs()  # reads ELEVENLABS_API_KEY
    audio = client.text_to_speech.convert(
        text=text,
        voice_id=voice or "onwK4e9ZLuTAKqWW03F9",  # "Daniel" — deep narrator
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )
    with open(path, "wb") as f:
        for chunk in audio:
            f.write(chunk)
    return _audio_seconds(path)


_KOKORO_PIPELINE = None  # model load takes seconds; share it across beats


def _kokoro(text: str, path: Path, voice: str, speed: float = 1.0) -> float:
    global _KOKORO_PIPELINE
    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline

    if _KOKORO_PIPELINE is None:
        # lang_code 'a' = American English ('b' for British voices like bm_george)
        _KOKORO_PIPELINE = KPipeline(lang_code=(voice or "am")[0])
    chunks = [audio for _, _, audio in
              _KOKORO_PIPELINE(text, voice=voice or "am_michael", speed=speed)]

    wav_path = path.with_suffix(".wav")
    sf.write(wav_path, np.concatenate(chunks), 24000)
    _wav_to_mp3(wav_path, path)
    return _audio_seconds(path)


def _piper(text: str, path: Path, voice: str) -> float:
    import subprocess

    wav_path = path.with_suffix(".wav")
    subprocess.run(
        ["piper", "--model", voice or "en_US-ryan-high", "--output_file", str(wav_path)],
        input=text, text=True, check=True,
    )
    _wav_to_mp3(wav_path, path)
    return _audio_seconds(path)


def _espeak(text: str, path: Path, voice: str) -> float:
    """Draft-quality narration for reviewing the edit. Not for publishing."""
    import subprocess

    wav_path = path.with_suffix(".wav")
    subprocess.run(
        ["espeak-ng", "-v", voice or "en-us", "-s", "150", "-w", str(wav_path), text],
        check=True, capture_output=True,
    )
    _wav_to_mp3(wav_path, path)
    return _audio_seconds(path)


def _wav_to_mp3(wav_path: Path, mp3_path: Path) -> None:
    import subprocess

    subprocess.run(
        ["ffmpeg", "-y", "-i", str(wav_path), "-b:a", "128k", str(mp3_path)],
        check=True, capture_output=True,
    )
    wav_path.unlink()
