# Real Animation via Draw Things (Wan 2.2 5B, local, $0)

Turns each beat's keyframe into a genuinely animated clip: the SDXL image is
fed to Wan 2.2 5B image-to-video running inside Draw Things on the Mac mini.
Each beat gets ~3.4s of real motion, then settles into a slow zoom hold on
the final frame for the rest of the narration — reads as an intentional
cinematic beat, not a loop.

## One-time setup (~15 min + model download)

1. Install **Draw Things** from the Mac App Store (free).
2. In the model picker, download **Wan 2.2 TI2V 5B** (the 5B variant — it's
   the one sized for a 16GB mini; the 14B is too heavy).
3. Settings → **API Server** → enable, HTTP, port **7860**, localhost.
4. Keep the app open whenever animating (it is the render engine).

## Test ONE beat before committing a night

```bash
python -m minimyths animate content/hercules main:0
```

This animates a single beat, prints the render time, and extrapolates the
full-episode estimate. On a 16GB M4 expect very roughly 10–40 min per beat —
the test tells you the real number. Watch the output clip and judge the
motion quality before going further.

## Full animated episode (overnight)

In `config/channels/greek_myths.yaml` set:

```yaml
motion_backend: draw_things
```

then kick it off and go to bed (`caffeinate` guards against idle sleep):

```bash
caffeinate -i python -m minimyths produce content/hercules
```

- Keyframes and narration come from cache — only animation renders.
- **Every finished clip is cached** (keyframe+prompt+params). If the run
  dies at beat 14, rerunning skips 13 finished clips.
- A beat whose animation fails falls back to Ken Burns for that beat and the
  run continues — check the log in the morning.

## Tuning

- `num_frames` (81 ≈ 3.4s at 24fps): more real motion per beat, linearly
  more render time.
- `steps` (30): 20 is noticeably faster, slightly softer.
- Free performance: close everything else on the mini — 16GB unified memory
  is the constraint, and memory pressure (not CPU) is what causes stalls.
- Memory-tight? Drop `width/height` to 960x528 in the `draw_things` config;
  clips are upscaled to 1080p at assembly anyway.
