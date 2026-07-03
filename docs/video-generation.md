# Video Generation Strategy

## Where we landed (and why it changed)

The original scoping chat considered Runway ML, then pivoted to CogVideoX-5B
running locally on the M4 Mac mini. After a reality check, **the pipeline ships
with Ken Burns motion over AI stills as the default**, with generative video as
an upgrade path. Reasons:

1. **CogVideoX-5B on a 16GB M4 mini is painful in practice.** It technically
   runs, but generation is minutes-per-second-of-video on Apple Silicon (no
   CUDA), and a 3-minute video needs ~14 beats × 15s of footage. That's days of
   compute per video — the opposite of a factory.
2. **Runway's free tier is ~125 one-time credits** (roughly 25 seconds of
   Gen-3 video), then ~$12-15/mo. Fine for hero shots later; can't carry a
   whole video at $0.
3. **The channels that actually win in the faceless-story niche** overwhelmingly
   use stills + slow zoom/pan + strong narration + captions. Viewers judge the
   story and the voice, not per-frame motion.

## The shipped default

- `image_backend`: one AI-generated still per beat.
  - `placeholder` — styled stand-in frames so the pipeline runs end-to-end today.
  - `diffusers` — SDXL-Turbo locally on the M4 (mps). ~2-5s/image, $0. **The
    intended production backend.**
- `motion_backend: ken_burns` — FFmpeg zoompan, alternating zoom in/out per
  beat. Instant, $0, deterministic.

## Upgrade paths (in order of likely ROI)

1. **Better stills**: swap SDXL-Turbo → FLUX.1-schnell (also runs on M4 via
   mflux) for noticeably better mythology art.
2. **Hero-shot hybrid**: generate 2-3 key beats (the hook, the climax) with
   Runway/Kling/Luma free credits, Ken Burns for the rest. Big perceived-quality
   lift for pennies.
3. **Full generative video**: revisit when either (a) a cloud GPU makes sense
   (~$0.50/video on a rented 4090 running CogVideoX/LTX-Video), or (b) the
   channel is monetized and paying for itself.

The `motion_backend` config key exists so any of these slots in without
touching the rest of the pipeline.
