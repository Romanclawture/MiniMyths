"""Wikipedia story sourcing.

Two capabilities:
- trending_stories(): yesterday's most-viewed articles, filtered and scored for
  "story potential" — used to discover topics beyond the curated backlogs.
- fetch_summary(): article intro text, used as research input for the script
  generator.
"""

from datetime import date, timedelta

import requests

HEADERS = {"User-Agent": "MiniMyths/0.1 (faceless-youtube pipeline)"}

# Pages that top the charts every day but make terrible videos.
BORING = {
    "Main_Page", "Special:Search", "Wikipedia",
    "XXX", "Pornhub", "OnlyFans", "XNXX", "XVideos",
}
BORING_PREFIXES = ("Special:", "Portal:", "Help:", "Wikipedia:", "File:", "Template:", "User:")

# Signals that a trending page is a *story* rather than a utility page.
STORY_WORDS = [
    "battle", "war", "myth", "legend", "hero", "king", "queen", "emperor",
    "assassin", "murder", "mystery", "disaster", "expedition", "conspiracy",
    "revolt", "siege", "pirate", "curse", "lost", "ancient", "trial",
]


def trending_stories(limit: int = 20, when: date | None = None) -> list[dict]:
    """Yesterday's most-viewed en.wikipedia articles, scored for story potential."""
    when = when or (date.today() - timedelta(days=1))
    url = (
        "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/"
        f"en.wikipedia/all-access/{when:%Y/%m/%d}"
    )
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    articles = resp.json()["items"][0]["articles"]

    results = []
    for a in articles:
        title = a["article"]
        if title in BORING or title.startswith(BORING_PREFIXES):
            continue
        score = _story_score(title, a["views"])
        results.append({"title": title.replace("_", " "), "wikipedia": title,
                        "views": a["views"], "score": score})
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:limit]


def _story_score(title: str, views: int) -> float:
    """Views weighted by how story-shaped the title looks."""
    t = title.lower().replace("_", " ")
    keyword_boost = 1 + sum(2 for w in STORY_WORDS if w in t)
    return views * keyword_boost


def fetch_summary(title: str) -> dict:
    """Intro extract + metadata for an article — research input for scripts."""
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return {
        "title": data.get("title", title),
        "extract": data.get("extract", ""),
        "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
    }
