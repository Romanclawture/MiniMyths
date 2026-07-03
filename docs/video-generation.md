# Video Generation Strategy & Open-Source Tooling Research

*Updated 2026-07 with a survey of local/open-source video generation options.*

## Where we landed (and why it changed)

The original scoping chat considered Runway ML, then pivoted to CogVideoX-5B
running locally on the M4 Mac mini. After researching the 2026 landscape,
**the pipeline ships with Ken Burns motion over AI stills as the default**,
with open-source generative video as a hero-shot upgrade path. Reasons:

1. **Generative video on a 16GB M4 mini is not factory-speed.** Even with
   GGUF quantization, Wan 2.2 took ~82 minutes for a 2-second clip on an
   M1 Max with 64GB — a 3-minute video needs ~14 beats of footage. Metal
   also lacks FP8 support, so Macs are stuck with slower quantized paths.
2. **The channels that win in the faceless-story niche** overwhelmingly use
   stills + slow zoom/pan + strong narration + captions. Viewers judge the
   story and the voice, not per-frame motion.
3. Ken Burns is instant, deterministic, and $0 — it ships video #1 today.

## The shipped default

- `image_backend: diffusers` — SDXL-Turbo locally on the M4 (mps), ~2-5s per
  image, $0. (`placeholder` renders styled stand-ins for pipeline testing.)
- `motion_backend: ken_burns` — FFmpeg zoompan, alternating zoom in/out.

## Open-source video generation landscape (researched 2026-07)

### Models (all open weights, $0 licenses)

| Model | Strength | Hardware reality |
|---|---|---|
| **Wan 2.2** (Alibaba) | Best open-source quality: motion consistency, texture, prompt adherence. MoE A14B variant. | 24GB GPU native; **~11GB VRAM with GGUF Q5**; runs on a 12GB RTX 3060. Mac: works via GGUF but extremely slow. |
| **LTX-Video / LTX-2** (Lightricks) | Speed king: 5-sec clip in seconds on an RTX 4090 (4-8× faster than Wan/Hunyuan). Only top model comfortable on 16GB cards. | 12GB+ VRAM. Mac: GGUF quantized builds exist (Kijai/LTXV2_comfy); no FP8 on Metal. |
| **HunyuanVideo 1.5** (Tencent) | Reference for prompt adherence + best face rendering in open source, 720p. | Heavier; needs a serious GPU. |
| **CogVideoX** (original plan) | Still capable but superseded by all three above. | Dropped from the plan. |

### Runners / front-ends

| Tool | What it is | Fit for us |
|---|---|---|
| **[open-generative-ai](https://github.com/anil-matcha/open-generative-ai)** (22k★, MIT) | Self-hosted AI studio (Next.js/Electron): image, video, lip-sync, workflow automation across 200+ models. | ⚠️ **Adopted with eyes open**: the 200+ models (Kling, Sora, Veo, Wan…) route through the **Muapi.ai paid API gateway** — that part is convenient, not free. Genuinely free parts: the workflow UI, sd.cpp local image engine, and Wan2GP integration. Use it as our **experiment bench** for auditioning models/prompts before wiring anything into the pipeline. |
| **Wan2GP** (deepbeepmeep) | "Video for the GPU poor": runs Wan 2.1/2.2, LTX-2, Hunyuan, Flux on 6-8GB VRAM via smart RAM/VRAM swapping. | **The engine to use on a rented GPU.** Windows/Linux + NVIDIA/AMD only — no Mac support. |
| **Draw Things** (free Mac app) | Metal-native image/video generation, 20-40% faster than ComfyUI on Apple Silicon; supports Wan 2.2; runs on a 16GB M4 mini. | **The Mac-native path.** Fine for occasional hero shots and image generation; too slow for volume video. |
| **ComfyUI** | Node-based workflow runner, the community standard; MPS support with GGUF models. | Fallback/power-user option on the mini. |

## Recommended strategy (in rollout order)

1. **Ship videos 1-3 on stills + Ken Burns.** Zero blockers, zero cost.
2. **Hero-shot hybrid (next):** generate 2-3 key beats per video (the hook,
   the climax) as real video:
   - *Local, $0:* Draw Things on the mini running Wan 2.2 — kick off a
     hero-shot render overnight.
   - *Rented, pennies:* an RTX 4090 spot instance (~$0.30-0.40/hr) running
     **Wan2GP** — LTX-2 generates a 5-sec clip in seconds, so a whole
     video's hero shots cost well under $1.
3. **Full generative video:** revisit once a channel is monetized. At that
   point Wan2GP + LTX-2 on a rented GPU makes every beat a real clip for
   roughly $1-2/video.
4. **open-generative-ai studio:** install on the mini as the audition bench —
   compare Wan vs LTX vs Hunyuan outputs on our actual prompts before
   committing pipeline code to one.

The `motion_backend` config key exists so any of these slots in without
touching the rest of the pipeline (`ken_burns` today; `wan2gp` / `ltx` /
`draw_things` are the planned values).

### Sources

- [Hyperstack: Best open-source video models 2026](https://www.hyperstack.cloud/blog/case-study/best-open-source-video-generation-models)
- [InsiderLLM: Local AI video generation, what works in 2026](https://insiderllm.com/guides/local-ai-video-generation/)
- [Can LTX-2 and Wan 2.2 run on Apple Silicon? (M1 Max benchmarks)](https://lilting.ch/en/articles/ltx2-wan22-mac-local-video-gen)
- [Wan2GP — video for the GPU poor](https://github.com/deepbeepmeep/Wan2GP)
- [Draw Things on M4 Mac mini benchmarks](https://www.heyuan110.com/posts/ai/2026-02-15-mac-mini-local-image-generation/)
- [open-generative-ai](https://github.com/anil-matcha/open-generative-ai)
