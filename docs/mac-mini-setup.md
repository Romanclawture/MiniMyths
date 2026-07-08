# Running MiniMyths on the M4 Mac mini

## One-command setup

```bash
git clone https://github.com/Romanclawture/MiniMyths.git && cd MiniMyths
git checkout claude/project-progress-u922nd
bash scripts/setup-mac.sh        # brew deps + venv + Kokoro + model warm-up
source .venv/bin/activate
```

Kokoro (free local narration) is the default voiceover backend. Pick the
channel voice by ear:

```bash
python -m minimyths audition     # renders the Hercules hook in 6 voices
open content/_auditions          # listen, pick, set voiceover.voice in config
```

## Image generation (for real visuals instead of placeholders)

```bash
pip install torch diffusers transformers accelerate peft
```

Then set `visuals.image_backend: diffusers` in `config/channels/greek_myths.yaml`.
First run downloads SDXL (~7GB). `image_quality: final` renders 30-step SDXL
(≈30-60s/image on the M4 — a full episode is ~15 min of image time);
`fast` uses SDXL-Turbo for quick previews.

### Style LoRAs (the big quality lever for clay/yarn/8-bit/noir)

A purpose-trained style LoRA beats prompt keywords every time. For each style
you plan to use, grab an SDXL LoRA from civitai.com (e.g. search "claymation
SDXL LoRA"), drop the `.safetensors` file in `assets/loras/`, and reference it
in `config/styles.yaml` under that style's `lora:` key. That's it — the
pipeline loads it automatically.

## The idea-to-video workflow

Your input is one command — topic, style, and any creative direction:

```bash
python -m minimyths run "Hercules" --style clay \
  --notes "Play up the comedy. Hera should feel genuinely menacing though."
```

The pipeline scripts it (visuals written FOR the clay medium, your notes
honored), voices it with George, renders style-locked keyframes, assembles
both formats + thumbnail, and stops for your review before publishing.
(ElevenLabs remains available: `voiceover.backend: elevenlabs` +
`export ELEVENLABS_API_KEY=…`.)

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
