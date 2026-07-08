"""Fast, dependency-light tests: schema, configs, backlogs, ledger, scripts.

No network, no TTS, no rendering — safe for CI.
"""

import json
from pathlib import Path

import pytest

from minimyths.config import CHANNELS_DIR, CONTENT_DIR, load_channel
from minimyths.scripting.schema import validate_script, word_count
from minimyths.sourcing.backlogs import BACKLOGS, get_backlog

REPO = Path(__file__).resolve().parent.parent


# --- channel configs -------------------------------------------------------

def channel_names():
    return sorted(p.stem for p in CHANNELS_DIR.glob("*.yaml"))


@pytest.mark.parametrize("name", channel_names())
def test_channel_config_complete(name):
    ch = load_channel(name)
    for key in ("name", "genre", "script", "voiceover", "visuals", "publish"):
        assert key in ch, f"{name}.yaml missing '{key}'"
    assert ch["script"]["main_video"]["target_seconds"] > 0
    assert ch["genre"] in BACKLOGS, f"no backlog for genre {ch['genre']}"


def test_unknown_channel_raises():
    with pytest.raises(FileNotFoundError):
        load_channel("does-not-exist")


# --- backlogs ---------------------------------------------------------------

def test_backlog_entries_well_formed():
    for genre, stories in BACKLOGS.items():
        assert stories, f"{genre} backlog empty"
        titles = [s["title"] for s in stories]
        assert len(titles) == len(set(titles)), f"{genre} has duplicate titles"
        for story in stories:
            assert story["title"] and story["wikipedia"] and story["hook"]


def test_get_backlog_unknown_genre():
    with pytest.raises(KeyError):
        get_backlog("underwater-basket-weaving")


# --- committed scripts ------------------------------------------------------

def committed_scripts():
    return sorted(CONTENT_DIR.glob("*/script.json"))


@pytest.mark.parametrize("path", committed_scripts(), ids=lambda p: p.parent.name)
def test_committed_script_valid(path):
    script = json.loads(path.read_text())
    assert validate_script(script) == []
    assert script["slug"] == path.parent.name
    assert len(script["title"]) <= 100  # YouTube hard limit


@pytest.mark.parametrize("path", committed_scripts(), ids=lambda p: p.parent.name)
def test_committed_script_pacing(path):
    """Narration must roughly fit the target length at a speakable pace."""
    script = json.loads(path.read_text())
    for section, lo, hi in (("main", 120, 170), ("short", 120, 180)):
        words = word_count(script, section)
        seconds = sum(b["seconds"] for b in script[section]["beats"])
        wpm = words / (seconds / 60)
        assert lo <= wpm <= hi, f"{section}: {wpm:.0f} wpm outside [{lo}, {hi}]"


def test_validate_script_catches_problems():
    assert validate_script({}) != []
    broken = {"slug": "x", "title": "x", "description": "x", "tags": [],
              "main": {"beats": [{"narration": "hi"}]}, "short": {"beats": []}}
    problems = validate_script(broken)
    assert any("missing visual" in p for p in problems)
    assert any("short: no beats" in p for p in problems)


# --- restyle ------------------------------------------------------------------

def test_apply_restyle():
    from minimyths.scripting.generator import apply_restyle

    script = {"main": {"beats": [{"narration": "a", "visual": "old1"},
                                 {"narration": "b", "visual": "old2"}]},
              "short": {"beats": [{"narration": "c", "visual": "old3"}]}}
    out = apply_restyle(script, {"main": ["new1", "new2"], "short": ["new3"]}, "clay")
    assert [b["visual"] for b in out["main"]["beats"]] == ["new1", "new2"]
    assert out["short"]["beats"][0]["visual"] == "new3"
    assert out["main"]["beats"][0]["narration"] == "a"  # narration untouched
    assert out["style"] == "clay"

    with pytest.raises(ValueError, match="short"):
        apply_restyle(script, {"main": ["x", "y"], "short": []}, "clay")


# --- styles -------------------------------------------------------------------

def test_style_packs_well_formed():
    import yaml

    from minimyths.visuals.images import STYLES_PATH

    styles = yaml.safe_load(STYLES_PATH.read_text())
    assert "painted-epic" in styles  # channel default must exist
    for name, pack in styles.items():
        assert pack.get("suffix", "").strip(), f"style '{name}' missing suffix"


def test_resolve_style_precedence():
    from minimyths.visuals.images import resolve_style

    channel = {"visuals": {"style": "painted-epic"}}
    assert resolve_style({}, channel)["name"] == "painted-epic"
    assert resolve_style({"style": "clay"}, channel)["name"] == "clay"
    with pytest.raises(KeyError):
        resolve_style({"style": "vaporwave"}, channel)


# --- thumbnails ---------------------------------------------------------------

def test_thumbnail_generation(tmp_path):
    from PIL import Image

    from minimyths.visuals.thumbnail import SIZE, generate_thumbnail

    script = {"title": "Test: A Story", "thumbnail_text": "NEVER LOOK AT HER"}
    channel = {"name": "Mini Myths", "thumbnail": {"accent": "#FFB800"}}
    out = generate_thumbnail(script, tmp_path, channel)

    assert out.exists()
    assert out.stat().st_size < 2 * 1024 * 1024  # YouTube limit
    with Image.open(out) as img:
        assert img.size == SIZE


# --- ledger -----------------------------------------------------------------

def test_ledger_next_story(tmp_path, monkeypatch):
    from minimyths.sourcing import ledger

    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "ledger.json")
    genre = "greek_myths"
    first = ledger.next_story(genre)
    assert first == get_backlog(genre)[0]

    ledger.mark("some-slug", "scripted", title="t", backlog=first["title"])
    second = ledger.next_story(genre)
    assert second == get_backlog(genre)[1]

    with pytest.raises(ValueError):
        ledger.mark("some-slug", "not-a-status")


def test_committed_ledger_consistent():
    from minimyths.sourcing.ledger import STATUSES, load_ledger

    for slug, entry in load_ledger().items():
        assert entry["status"] in STATUSES
        assert (CONTENT_DIR / slug / "script.json").exists(), (
            f"ledger entry '{slug}' has no committed script"
        )
