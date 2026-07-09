"""Claude-backed script generation.

Two backends, tried in order:
1. `claude` CLI  — uses the Max subscription, zero marginal cost. Preferred.
2. Anthropic API — needs ANTHROPIC_API_KEY; used when the CLI isn't installed.
"""

import json
import os
import re
import shutil
import subprocess

from ..sourcing.wikipedia import fetch_summary
from .schema import validate_script

PROMPT_TEMPLATE = """\
You are the head writer for "{channel_name}", a faceless YouTube channel.

Channel tone: {tone}

Write a video script about: {topic}

Research (from Wikipedia):
{research}

Produce TWO scripts:
1. "main" — a {main_seconds}-second video (~{main_words} words of narration total)
2. "short" — a {short_seconds}-second vertical Short (~{short_words} words) that
   teases the story and ends with "full story on the channel"

Rules:
- Break each script into beats: one beat = one visual scene (main: 10-16 beats, short: 3-5).
- narration: spoken text only. No stage directions. Hook hard in beat 1.
- visual: a vivid image-generation prompt for that scene. Write it like a
  cinematographer's shot description: SHOT TYPE + camera angle (extreme
  close-up / wide establishing / low-angle / over-the-shoulder), subject +
  a single clear action, setting, lighting, and mood. Vary shot types
  across beats like a film editor would. No text/words in the image. Refer
  to recurring characters by NAME (e.g. "Hercules", not "a hero") — names
  attach reference images that keep characters consistent across shots.
- motion: one sentence describing what MOVES in the shot — character action,
  environment motion, and a camera move (e.g. "he slams the axe down, dust
  bursts up, storm clouds churn; slow push-in"). Video models animate only
  what is described as moving.
- seconds: rough duration; narration should fit it at ~150 wpm.
{style_rule}{notes_rule}

Respond with ONLY a JSON object, no markdown fences, matching:
{{"slug": "...", "title": "...", "description": "...", "tags": [...],
  "thumbnail_text": "...",
  "main": {{"beats": [{{"narration": "...", "visual": "...",
  "motion": "...", "seconds": 12}}]}},
  "short": {{"beats": [...]}}}}

title: clickable but honest, <70 chars. description: 2-3 sentences + a question
to drive comments. tags: 10-15. slug: lowercase-hyphenated.
thumbnail_text: 2-4 punchy words for the thumbnail overlay (NOT the title).
"""


def generate_script(topic: str, channel: dict, wikipedia_title: str | None = None,
                    style: str | None = None, notes: str | None = None) -> dict:
    """Generate and validate a script for `topic` using the channel's style.

    style: style-pack name (config/styles.yaml) — beat visuals are written FOR
    that look (a clay scene is staged differently than an 8-bit one).
    notes: free-form creative direction from the producer.
    """
    research = ""
    if wikipedia_title:
        try:
            research = fetch_summary(wikipedia_title)["extract"]
        except Exception:
            pass  # research is a bonus, not a requirement

    style_rule = ""
    if style:
        from ..visuals.images import resolve_style

        pack = resolve_style({"style": style}, channel)  # validates the name
        style_rule = (
            f"- This episode is rendered in a '{pack['name']}' visual style "
            f"({pack['suffix'].strip()}). Write every visual prompt to play to "
            "that medium's strengths — its textures, its framing, its charm. "
            "Do NOT repeat the style keywords themselves; they are appended "
            "automatically.\n"
        )
    notes_rule = ""
    if notes:
        notes_rule = f"- Creative direction from the producer (honor it): {notes}\n"

    cfg = channel["script"]
    main_s = cfg["main_video"]["target_seconds"]
    short_s = cfg["short"]["target_seconds"]
    prompt = PROMPT_TEMPLATE.format(
        channel_name=channel["name"],
        tone=cfg["tone"].strip(),
        topic=topic,
        research=research or "(none — use your own knowledge, stay true to the classical sources)",
        main_seconds=main_s,
        main_words=int(main_s / 60 * cfg["main_video"]["words_per_minute"]),
        short_seconds=short_s,
        short_words=int(short_s / 60 * cfg["short"]["words_per_minute"]),
        style_rule=style_rule,
        notes_rule=notes_rule,
    )

    raw = _ask_claude(prompt)
    script = _parse_json(raw)
    if style:
        script["style"] = style
    problems = validate_script(script)
    if problems:
        raise ValueError(f"Generated script failed validation: {problems}")
    return script


RESTYLE_TEMPLATE = """\
You are the art director for "{channel_name}". An episode is being re-rendered
in a new visual style: '{style_name}' ({style_suffix}).

Rewrite ONLY the visual prompts below — the narration is final and must not
change. Stage each scene to play to the new medium's strengths (its textures,
framing, charm). Write each visual like a cinematographer's shot description:
SHOT TYPE + angle, subject + one clear action, setting, lighting, mood —
varying shot types across beats like a film editor would. Do NOT include the
style keywords themselves; they are appended automatically. No text/words in
the images.
{notes_rule}
Current beats:
{beats_json}

Respond with ONLY a JSON object, no markdown fences:
{{"main": ["new visual for main beat 0", ...], "short": ["...", ...]}}
Exactly one visual per beat, same order and count as the input.
"""


def restyle_script(script: dict, channel: dict, style: str,
                   notes: str | None = None) -> dict:
    """Rewrite an existing script's visual prompts for a new style pack.

    Narration, beats, and timings are untouched, so already-generated
    voiceover stays valid.
    """
    from ..visuals.images import resolve_style

    pack = resolve_style({"style": style}, channel)  # validates the name
    beats_json = json.dumps({
        section: [{"narration": b["narration"], "visual": b["visual"]}
                  for b in script[section]["beats"]]
        for section in ("main", "short")
    }, indent=2)
    prompt = RESTYLE_TEMPLATE.format(
        channel_name=channel["name"],
        style_name=pack["name"],
        style_suffix=pack["suffix"].strip(),
        notes_rule=f"Producer notes: {notes}\n" if notes else "",
        beats_json=beats_json,
    )
    visuals = _parse_json(_ask_claude(prompt))
    return apply_restyle(script, visuals, style)


def apply_restyle(script: dict, visuals: dict, style: str) -> dict:
    """Swap in new visual prompts; count/order must match the beats exactly."""
    for section in ("main", "short"):
        beats = script[section]["beats"]
        new = visuals.get(section, [])
        if len(new) != len(beats):
            raise ValueError(
                f"{section}: got {len(new)} visuals for {len(beats)} beats"
            )
        for beat, visual in zip(beats, new):
            beat["visual"] = visual
    script["style"] = style
    return script


def _ask_claude(prompt: str) -> str:
    cli_error = None
    if shutil.which("claude"):
        result = subprocess.run(
            ["claude", "-p"], input=prompt,  # prompt via stdin: no argv limits
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
        cli_error = (
            f"claude CLI exited {result.returncode}.\n"
            f"stdout: {result.stdout[-500:] or '(empty)'}\n"
            f"stderr: {result.stderr[-500:] or '(empty)'}\n"
            "Hint: run `claude -p \"say hi\"` to check the CLI works — if not, "
            "run `claude` once and log in / trust this folder."
        )

    if os.environ.get("ANTHROPIC_API_KEY"):
        if cli_error:
            print("  claude CLI failed, falling back to the API …")
        import anthropic

        client = anthropic.Anthropic()
        msg = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text

    raise RuntimeError(cli_error or (
        "No Claude backend available: install the `claude` CLI (Max subscription) "
        "or set ANTHROPIC_API_KEY."
    ))


def _parse_json(raw: str) -> dict:
    """Extract the JSON object from a model response, tolerating fences/preamble."""
    raw = raw.strip()
    if raw.startswith("{"):
        return json.loads(raw)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object in response: {raw[:200]}")
    return json.loads(match.group(0))
