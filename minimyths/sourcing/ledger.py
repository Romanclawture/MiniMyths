"""Production ledger — which stories have been scripted/produced/published.

State lives in content/ledger.json (committed, human-editable):
{
  "hercules": {
    "title": "Hercules: The 12 Impossible Chores That Made a God",
    "backlog": "Hercules and the Twelve Labors",   # ties entry to backlog item
    "status": "scripted",
    "published_url": null
  }
}

Status progression: scripted → produced → published.
The picker returns the first backlog story not yet claimed by any entry.
"""

import json

from ..config import CONTENT_DIR
from .backlogs import get_backlog

LEDGER_PATH = CONTENT_DIR / "ledger.json"
STATUSES = ("scripted", "produced", "published")


def load_ledger() -> dict:
    if LEDGER_PATH.exists():
        return json.loads(LEDGER_PATH.read_text())
    return {}


def save_ledger(ledger: dict) -> None:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEDGER_PATH.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")


def mark(slug: str, status: str, title: str = "", backlog: str = "",
         url: str | None = None) -> None:
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    ledger = load_ledger()
    entry = ledger.setdefault(slug, {"title": title, "backlog": backlog,
                                     "published_url": None})
    entry["status"] = status
    if title:
        entry["title"] = title
    if backlog:
        entry["backlog"] = backlog
    if url:
        entry["published_url"] = url
    save_ledger(ledger)


def next_story(genre: str) -> dict | None:
    """First backlog story not yet claimed by a ledger entry."""
    ledger = load_ledger()
    claimed = {e.get("backlog", "") for e in ledger.values()}
    for story in get_backlog(genre):
        if story["title"] not in claimed:
            return story
    return None
