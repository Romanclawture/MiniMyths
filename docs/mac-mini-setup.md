# Running MiniMyths on the M4 Mac mini

## Prereqs

```bash
# Homebrew packages
brew install ffmpeg python@3.12

# Clone + env
git clone https://github.com/Romanclawture/MiniMyths.git && cd MiniMyths
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Backends to enable for production

```bash
# Free local TTS (recommended once auditioned — see docs/tts-research.md)
pip install kokoro soundfile

# Local image generation on Apple Silicon (SDXL-Turbo via mps)
pip install torch diffusers transformers accelerate
```

Then in `config/channels/greek_myths.yaml`:
- `voiceover.backend: kokoro` (or keep `elevenlabs` + `export ELEVENLABS_API_KEY=…`)
- `visuals.image_backend: diffusers`

## Claude script generation

The generator shells out to the `claude` CLI if installed (uses the Max
subscription — no API cost). Otherwise set `ANTHROPIC_API_KEY`.

## First video, end to end

The Hercules script is already committed, so:

```bash
python -m minimyths produce content/hercules   # voiceover + images + video
open content/hercules/final/main.mp4           # review!
python -m minimyths publish content/hercules   # uploads as PRIVATE
```

## Automation (later)

Once a few videos have shipped manually, add a monthly launchd/cron job:

```
0 9 1 * *  cd ~/MiniMyths && .venv/bin/python -m minimyths run "<next topic>" 
```

The intended end state is a picker that pops the next story off the backlog
automatically — tracked in the README roadmap.
