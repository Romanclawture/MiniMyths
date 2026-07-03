"""Script JSON schema and validation.

A script.json is the contract between stages — everything downstream
(voiceover, visuals, assembly, publish) reads only this file.

{
  "slug": "hercules",
  "title": "...",                     # YouTube title
  "description": "...",              # YouTube description
  "tags": ["..."],
  "main": {"beats": [BEAT, ...]},    # 3-min video
  "short": {"beats": [BEAT, ...]}    # 30-sec vertical Short
}

BEAT = {
  "narration": "...",       # what the narrator says
  "visual": "...",          # image/video generation prompt for this scene
  "seconds": 12             # rough target duration (refined to actual VO length)
}
"""

REQUIRED_TOP = ["slug", "title", "description", "tags", "main", "short"]
REQUIRED_BEAT = ["narration", "visual", "seconds"]


def validate_script(script: dict) -> list[str]:
    """Return a list of problems; empty list means valid."""
    problems = []
    for key in REQUIRED_TOP:
        if key not in script:
            problems.append(f"missing top-level key: {key}")
    for section in ("main", "short"):
        beats = script.get(section, {}).get("beats", [])
        if not beats:
            problems.append(f"{section}: no beats")
        for i, beat in enumerate(beats):
            for key in REQUIRED_BEAT:
                if key not in beat:
                    problems.append(f"{section}.beats[{i}]: missing {key}")
    return problems


def word_count(script: dict, section: str) -> int:
    return sum(len(b["narration"].split()) for b in script[section]["beats"])
