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
- visual: a vivid image-generation prompt for that scene (subject + action +
  setting + mood). No text/words in the image.
- seconds: rough duration; narration should fit it at ~150 wpm.

Respond with ONLY a JSON object, no markdown fences, matching:
{{"slug": "...", "title": "...", "description": "...", "tags": [...],
  "thumbnail_text": "...",
  "main": {{"beats": [{{"narration": "...", "visual": "...", "seconds": 12}}]}},
  "short": {{"beats": [...]}}}}

title: clickable but honest, <70 chars. description: 2-3 sentences + a question
to drive comments. tags: 10-15. slug: lowercase-hyphenated.
thumbnail_text: 2-4 punchy words for the thumbnail overlay (NOT the title).
"""


def generate_script(topic: str, channel: dict, wikipedia_title: str | None = None) -> dict:
    """Generate and validate a script for `topic` using the channel's style."""
    research = ""
    if wikipedia_title:
        try:
            research = fetch_summary(wikipedia_title)["extract"]
        except Exception:
            pass  # research is a bonus, not a requirement

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
    )

    raw = _ask_claude(prompt)
    script = _parse_json(raw)
    problems = validate_script(script)
    if problems:
        raise ValueError(f"Generated script failed validation: {problems}")
    return script


def _ask_claude(prompt: str) -> str:
    if shutil.which("claude"):
        result = subprocess.run(
            ["claude", "-p", prompt], capture_output=True, text=True, timeout=600,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
        raise RuntimeError(f"claude CLI failed: {result.stderr[:500]}")

    if os.environ.get("ANTHROPIC_API_KEY"):
        import anthropic

        client = anthropic.Anthropic()
        msg = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text

    raise RuntimeError(
        "No Claude backend available: install the `claude` CLI (Max subscription) "
        "or set ANTHROPIC_API_KEY."
    )


def _parse_json(raw: str) -> dict:
    """Extract the JSON object from a model response, tolerating fences/preamble."""
    raw = raw.strip()
    if raw.startswith("{"):
        return json.loads(raw)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object in response: {raw[:200]}")
    return json.loads(match.group(0))
