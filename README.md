# MiniMyths 🏛️

Faceless YouTube content factory. First channel: **Mini Myths** ([@Mini_Myths](https://youtube.com/@Mini_Myths)) — animated retellings of Greek myths and history's most fascinating stories. Built as a genre-agnostic pipeline so new channels (interesting people, bizarre history, …) are just a new config file.

## The Pipeline

```
source → script → voiceover → visuals → assemble → publish
```

| Stage | What it does | Tool | Cost |
|-------|-------------|------|------|
| **Source** | Find great stories: curated myth backlog + Wikipedia most-viewed pages ranked by "interestingness" | Wikimedia APIs | $0 |
| **Script** | Turn a story into a beat-by-beat video script (narration + visual prompt per scene) | Claude (Max subscription via `claude` CLI, or API) | ~$0 |
| **Voiceover** | Narration audio per beat | Kokoro (free, local) / Piper (free, local) / ElevenLabs (premium) | $0–20/mo |
| **Visuals** | One clip per beat | Ken Burns over AI images (default, reliable); hero shots via Wan 2.2 / LTX-2 (open-source, local or rented GPU) | $0 |
| **Assemble** | Stitch beats + audio + subtitles into 16:9 3-min video and 9:16 30-sec Short | FFmpeg | $0 |
| **Publish** | Upload with metadata + scheduling | YouTube Data API | $0 |

Every stage is pluggable: backends are selected in the channel config, so swapping ElevenLabs for Kokoro or Ken Burns for CogVideoX is a one-line change.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. See the story backlog / what's trending on Wikipedia
python -m minimyths source --channel greek_myths

# 2. Generate a script (uses `claude` CLI if installed, else ANTHROPIC_API_KEY)
python -m minimyths script "Hercules" --channel greek_myths

# 3. Produce voiceover + visuals + final videos
python -m minimyths produce content/hercules

# 4. Upload (needs YouTube OAuth, see docs/youtube-setup.md)
python -m minimyths publish content/hercules

# Or the whole thing:
python -m minimyths run "Hercules" --channel greek_myths
```

The first script (Hercules, 3-min + 30-sec Short) is already checked in at `content/hercules/script.json` — you can run `produce` on it immediately.

## Project layout

```
minimyths/            # the pipeline package
  sourcing/           # Wikipedia trending + curated backlogs
  scripting/          # Claude script generation (CLI or API backend)
  voiceover/          # TTS backends: kokoro, piper, elevenlabs
  visuals/            # image gen + Ken Burns renderer, cogvideox stub
  assembly/           # FFmpeg stitching, subtitles, shorts crop
  publish/            # YouTube upload + metadata
config/channels/      # one YAML per channel (genre, voice, cadence, style)
content/<slug>/       # per-video working dir: script.json, audio/, frames/, final/
docs/                 # setup guides + research notes
```

## Docs

- [docs/mac-mini-setup.md](docs/mac-mini-setup.md) — getting the pipeline running on the M4 Mac mini
- [docs/tts-research.md](docs/tts-research.md) — comparison of ElevenLabs vs Kokoro vs Piper vs Chatterbox vs OmniVoice
- [docs/video-generation.md](docs/video-generation.md) — open-source video-gen research (Wan 2.2, LTX-2, Wan2GP, Draw Things, open-generative-ai) and the rollout strategy
- [docs/youtube-setup.md](docs/youtube-setup.md) — YouTube API credentials + OAuth flow

## Roadmap

- [x] Repo + pipeline scaffold
- [x] Story sourcing (curated backlog + Wikipedia trending)
- [x] Script generator + Hercules script v1
- [ ] Voiceover pass on Hercules (pick voice, generate audio)
- [ ] Image generation pass (pick style, generate scene images)
- [ ] Assemble + review first video
- [ ] Publish Hercules to @Mini_Myths
- [ ] Install open-generative-ai studio on the mini as a model audition bench
- [ ] Hero-shot hybrid: Wan 2.2 (Draw Things) or LTX-2 (Wan2GP on rented GPU) for 2-3 key beats per video
- [ ] Automate cadence (cron), then channel #2
