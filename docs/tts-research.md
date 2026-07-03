# TTS Research — picking the Mini Myths narrator

Goal: broadcast-quality narration at near-zero burn, running on the M4 Mac mini
where possible. These are the four options from our chat plus ElevenLabs as the
paid benchmark.

## TL;DR recommendation

**Start with ElevenLabs pay-as-you-go for video #1** (fastest path to a
great-sounding first upload, a 3-min video costs well under $1), and **stand up
Kokoro locally in parallel**. If Kokoro's narrator voice sounds good enough on
the Hercules script, switch the config to `backend: kokoro` and the marginal
cost per video drops to $0 forever. Piper stays as the fast-draft option.

## The contenders

### ElevenLabs (paid benchmark)
- **Quality:** best-in-class, expressive, great pacing for storytelling.
- **Cost:** free tier ~10 min/mo; Starter $5/mo ≈ 30 min. At 3.5 min per video
  we fit several videos/month in the $5 tier.
- **Ops:** trivial (API). Already wired in as the default backend.
- **Risk:** recurring cost scales with channel count — exactly what we want to avoid long-term.

### Kokoro (kokorottsai.com) — 82M-param open model, Apache-2.0
- **Quality:** the standout free option — consistently ranked near the top of
  open TTS leaderboards; smooth, natural narration well above typical open TTS.
- **Cost:** $0. Runs comfortably on CPU/Apple Silicon (82M params is tiny);
  faster than realtime on the M4.
- **Ops:** `pip install kokoro soundfile`; voices like `am_michael` (deep male)
  fit the epic-narrator brief.
- **Risk:** less emotional range than ElevenLabs; no voice cloning.
- **Verdict:** *the* long-term default for a zero-burn factory.

### Piper (github.com/rhasspy/piper)
- **Quality:** solid but noticeably synthetic vs Kokoro/ElevenLabs. Home-assistant heritage.
- **Cost:** $0, extremely fast, tiny footprint, fully offline.
- **Ops:** single binary + voice model file; dead simple.
- **Verdict:** keep as the draft/preview backend (instant iteration on script
  pacing) — not the publish voice.

### Chatterbox / Chatterbox Turbo (Resemble AI)
- **Quality:** very good open-weights model (MIT), with emotion-exaggeration
  control that's interesting for dramatic narration; Turbo variant is faster.
- **Cost:** $0 open weights, but heavier than Kokoro (0.5B params) — runs on
  the M4 but slower; also offered as a paid API.
- **Ops:** more setup than Kokoro; outputs are watermarked (PerTh) — fine for
  our use, worth knowing.
- **Verdict:** the upgrade path if Kokoro feels flat and we still want $0.
  Revisit after video #2-3.

### OmniVoice-Studio (github.com/debpalash/OmniVoice-Studio)
- **What it is:** a self-hosted studio UI wrapping multiple open TTS engines
  (rather than a model itself). Small community project.
- **Verdict:** skip for the pipeline — we need library/CLI calls, not a GUI,
  and it adds a maintenance dependency on a small repo. Fine as a manual
  audition tool to compare voices by ear.

## Decision matrix

| | Quality | Cost | Speed on M4 | Pipeline fit |
|---|---|---|---|---|
| ElevenLabs | ★★★★★ | $5+/mo | API | ✅ wired |
| Kokoro | ★★★★ | $0 | fast | ✅ wired |
| Chatterbox | ★★★★ | $0 | medium | future |
| Piper | ★★★ | $0 | instant | ✅ wired (drafts) |
| OmniVoice-Studio | n/a (wrapper) | $0 | n/a | ❌ GUI-only |

## Next action

Generate the Hercules narration with both ElevenLabs (`Daniel`) and Kokoro
(`am_michael`), listen back to back, pick the channel voice, lock it in
`config/channels/greek_myths.yaml`.
