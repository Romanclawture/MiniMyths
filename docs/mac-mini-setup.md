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
pip install torch diffusers transformers accelerate
```

Then set `visuals.image_backend: diffusers` in `config/channels/greek_myths.yaml`.
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
