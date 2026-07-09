# Hosted Motion via fal.ai (Kling-class quality, ~$2-8/episode)

The animation stage sends each beat's keyframe + motion prompt to a hosted
image-to-video model and gets a frontier-quality clip back in ~1-2 minutes.
Everything else (script, voice, keyframes, assembly) stays local and free.

## One-time setup (~5 min)

1. Create an account at [fal.ai](https://fal.ai) and add a payment method
   (pay-per-use, no subscription).
2. Generate an API key: fal.ai → Dashboard → Keys.
3. On the Mac mini:

```bash
export FAL_KEY=...            # add to ~/.zshrc to persist
```

## Test one beat first (~$0.35)

```bash
python -m minimyths animate content/hercules main:4 --backend fal
```

Beat main:4 (the lion wrestle) has high-action motion — a good quality probe.
The clip lands in `content/hercules/clips/`; judge it against the reference
channels before running the full episode.

## Full episode

Set in `config/channels/greek_myths.yaml`:

```yaml
motion_backend: fal
```

then `python -m minimyths produce content/hercules`. 18 beats × ~$0.35 ≈
**$6.30 per episode** at Kling 2.5 Turbo Pro quality (see cheaper options
below). Clips cache like everything else — re-produces don't re-buy motion
unless the keyframe or prompt changed, and a failed beat falls back to
Ken Burns instead of killing the run.

## Model options (`visuals.fal.model`)

| Model id | Quality | ~Cost per 5s |
|---|---|---|
| `fal-ai/kling-video/v2.5-turbo/pro/image-to-video` | excellent, default | $0.35 |
| `fal-ai/kling-video/v2.6/pro/image-to-video` | newest Kling, audio-capable | $0.35 (audio off) |
| Wan 2.5 I2V endpoints | very good, cheapest | ~$0.25 (480p) |

Any fal I2V endpoint that takes `prompt` + `image_url` + `duration` works;
model-specific knobs go in `visuals.fal.extra`.

## Why motion prompts matter

I2V models animate what is *described as moving*. Every beat now carries a
`motion` field ("storm clouds churn, his cloak whips; slow push-in") that is
appended to the animation prompt — this, plus the keyframe, is what separates
"static screen that flickers" from an actual shot. New scripts get motion
lines automatically; older scripts can have them added by hand or via restyle.
