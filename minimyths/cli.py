"""MiniMyths CLI.

  python -m minimyths source  --channel greek_myths [--trending]
  python -m minimyths script  "Hercules" --channel greek_myths [--wiki Labours_of_Hercules]
  python -m minimyths produce content/hercules --channel greek_myths
  python -m minimyths publish content/hercules --channel greek_myths [--at RFC3339]
  python -m minimyths run     "Hercules" --channel greek_myths
"""

import argparse
import json
import sys
from pathlib import Path

from .config import content_dir, load_channel


def main(argv=None):
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--channel", default="greek_myths")

    parser = argparse.ArgumentParser(prog="minimyths")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("source", parents=[common], help="show story backlog / trending topics")
    p.add_argument("--trending", action="store_true",
                   help="show Wikipedia trending instead of curated backlog")

    p = sub.add_parser("script", parents=[common], help="generate script.json for a topic")
    p.add_argument("topic")
    p.add_argument("--wiki", help="Wikipedia title for research context")
    p.add_argument("--style", help="style pack for this episode (config/styles.yaml)")
    p.add_argument("--notes", help="creative direction, woven into the script prompt")

    p = sub.add_parser("produce", parents=[common], help="voiceover + visuals + final videos")
    p.add_argument("dir", help="content dir containing script.json")
    p.add_argument("--draft", action="store_true",
                   help="review cut: espeak draft voice + placeholder art, $0 and fast")

    p = sub.add_parser("publish", parents=[common], help="upload finals to YouTube")
    p.add_argument("dir")
    p.add_argument("--at", help="RFC3339 publish time (schedules the upload)")
    p.add_argument("--skip-short", action="store_true")

    p = sub.add_parser("run", parents=[common], help="script + produce + publish in one go")
    p.add_argument("topic", nargs="?",
                   help="story topic; omit to auto-pick the next backlog story")
    p.add_argument("--wiki")
    p.add_argument("--style", help="style pack for this episode (config/styles.yaml)")
    p.add_argument("--notes", help="creative direction, woven into the script prompt")

    sub.add_parser("next", parents=[common], help="show pipeline status + next story")

    p = sub.add_parser("restyle", parents=[common],
                       help="rewrite an episode's visuals in a new style (narration kept)")
    p.add_argument("dir", help="content dir containing script.json")
    p.add_argument("--style", required=True, help="target style pack (config/styles.yaml)")
    p.add_argument("--notes", help="extra art direction for the new visuals")

    p = sub.add_parser("reroll", parents=[common],
                       help="regenerate specific beat images (e.g. reroll <dir> main:4 short:1)")
    p.add_argument("dir")
    p.add_argument("beats", nargs="+", help="beats as section:index, e.g. main:4")
    p.add_argument("--style", help="override style pack for these frames (e.g. clay)")

    p = sub.add_parser("review", parents=[common],
                       help="build review.html — every beat's frame, narration and timing")
    p.add_argument("dir")

    p = sub.add_parser("animate", parents=[common],
                       help="test-animate ONE beat (measure quality/cost before full runs)")
    p.add_argument("dir")
    p.add_argument("beat", help="section:index, e.g. main:0")
    p.add_argument("--style", help="override style pack for the motion prompt (e.g. clay)")
    p.add_argument("--backend", choices=["fal", "draw_things"],
                   help="override motion engine (default: channel config)")

    p = sub.add_parser("audition", parents=[common],
                       help="render a sample line in candidate Kokoro voices")
    p.add_argument("--text", default=(
        "This is the strongest man who ever lived. The gods hated him before "
        "he was even born. And the price for his freedom? Twelve impossible, "
        "monster-filled, absolutely unfair chores."))
    p.add_argument("--voices", default="am_michael,am_fenrir,am_adam,bm_george,bm_daniel,bm_fable")

    args = parser.parse_args(argv)
    channel = load_channel(args.channel)

    if args.command == "source":
        _cmd_source(args, channel)
    elif args.command == "script":
        _cmd_script(args.topic, args.wiki, channel, style=args.style, notes=args.notes)
    elif args.command == "produce":
        if args.draft:
            channel["voiceover"] = {"backend": "espeak", "voice": "en-us"}
            channel["visuals"]["image_backend"] = "placeholder"
        _cmd_produce(Path(args.dir), channel, draft=args.draft)
    elif args.command == "publish":
        _cmd_publish(Path(args.dir), channel, args.at, args.skip_short)
    elif args.command == "run":
        topic, wiki = args.topic, args.wiki
        if not topic:
            from .sourcing.ledger import next_story

            story = next_story(channel["genre"])
            if not story:
                sys.exit("Backlog exhausted — add stories to minimyths/sourcing/backlogs.py")
            topic, wiki = story["title"], story.get("wikipedia")
            print(f"Next up from backlog: {topic}")
        script_dir = _cmd_script(topic, wiki, channel, backlog_title=topic,
                                 style=args.style, notes=args.notes)
        _cmd_produce(script_dir, channel)
        print("\nReview the finals, then:")
        print(f"  python -m minimyths publish {script_dir}")
    elif args.command == "next":
        _cmd_next(channel)
    elif args.command == "audition":
        _cmd_audition(args.text, args.voices.split(","))
    elif args.command == "restyle":
        _cmd_restyle(Path(args.dir), channel, args.style, args.notes)
    elif args.command == "reroll":
        _cmd_reroll(Path(args.dir), channel, args.beats, style=args.style)
    elif args.command == "review":
        _cmd_review(Path(args.dir))
    elif args.command == "animate":
        _cmd_animate(Path(args.dir), channel, args.beat, style=args.style,
                     backend=args.backend)


def _cmd_source(args, channel):
    if args.trending:
        from .sourcing import trending_stories

        print("Trending on Wikipedia (story-scored):\n")
        for s in trending_stories():
            print(f"  {s['score']:>12,.0f}  {s['title']}  ({s['views']:,} views)")
    else:
        from .sourcing import get_backlog

        print(f"Backlog for {channel['name']}:\n")
        for i, story in enumerate(get_backlog(channel["genre"]), 1):
            print(f"  {i:2d}. {story['title']}\n      {story['hook']}")


def _cmd_script(topic, wiki, channel, backlog_title="", style=None, notes=None) -> Path:
    from .scripting import generate_script
    from .sourcing.ledger import mark

    print(f"Generating script for: {topic} …")
    script = generate_script(topic, channel, wikipedia_title=wiki,
                             style=style, notes=notes)
    out_dir = content_dir(script["slug"])
    path = out_dir / "script.json"
    path.write_text(json.dumps(script, indent=2))
    mark(script["slug"], "scripted", title=script["title"],
         backlog=backlog_title or topic)
    from .scripting.schema import word_count

    print(f"  ✓ {path}")
    print(f"    main: {len(script['main']['beats'])} beats, {word_count(script, 'main')} words")
    print(f"    short: {len(script['short']['beats'])} beats, {word_count(script, 'short')} words")
    return out_dir


def _cmd_produce(work_dir: Path, channel, draft=False):
    script_path = work_dir / "script.json"
    if not script_path.exists():
        sys.exit(f"No script.json in {work_dir}")
    script = json.loads(script_path.read_text())

    from .assembly import assemble
    from .visuals import generate_images, render_clips
    from .voiceover import generate_voiceover

    print("1/4 voiceover …")
    manifest = generate_voiceover(script, work_dir / "audio", channel)
    print("2/4 scene images …")
    generate_images(script, work_dir / "frames", channel)
    print("3/4 motion clips …")
    clips = render_clips(script, work_dir / "frames", manifest, work_dir / "clips", channel)
    print("4/4 assembly …")
    outputs = assemble(script, clips, manifest, work_dir / "final", channel)
    for section, path in outputs.items():
        print(f"  ✓ {section}: {path}")

    from .visuals import generate_thumbnail

    thumb = generate_thumbnail(script, work_dir, channel)
    print(f"  ✓ thumbnail: {thumb}")

    if not draft:  # draft cuts don't advance the pipeline state
        from .sourcing.ledger import mark

        mark(script["slug"], "produced", title=script["title"])


def _cmd_next(channel):
    from .sourcing.ledger import load_ledger, next_story

    ledger = load_ledger()
    if ledger:
        print("Pipeline status:\n")
        icons = {"scripted": "📝", "produced": "🎬", "published": "✅"}
        for slug, e in sorted(ledger.items()):
            url = f"  {e['published_url']}" if e.get("published_url") else ""
            print(f"  {icons.get(e['status'], '?')} {e['status']:<10} {slug}{url}")
        print()
    story = next_story(channel["genre"])
    if story:
        print(f"Next up: {story['title']}")
        print(f"  {story['hook']}")
        print(f"\n  python -m minimyths run \"{story['title']}\" --wiki {story['wikipedia']}")
    else:
        print("Backlog exhausted — add stories to minimyths/sourcing/backlogs.py")


def _cmd_audition(text: str, voices: list[str]):
    """Same line, every candidate voice → content/_auditions/<voice>.mp3."""
    try:
        import kokoro  # noqa: F401
    except ImportError:
        sys.exit("Kokoro not installed — run `bash scripts/setup-mac.sh` "
                 "(or `pip install kokoro soundfile`).")
    import minimyths.voiceover.engine as engine
    from .config import CONTENT_DIR

    out_dir = CONTENT_DIR / "_auditions"
    out_dir.mkdir(parents=True, exist_ok=True)
    for voice in voices:
        engine._KOKORO_PIPELINE = None  # brits and americans need different G2P
        path = out_dir / f"{voice}.mp3"
        seconds = engine._kokoro(text, path, voice)
        print(f"  ✓ {voice:<12} {seconds:.1f}s  {path}")
    print(f"\nListen back to back:  open {out_dir}")
    print("Then set your pick in config/channels/greek_myths.yaml → voiceover.voice")


def _cmd_restyle(work_dir: Path, channel, style: str, notes):
    script_path = work_dir / "script.json"
    if not script_path.exists():
        sys.exit(f"No script.json in {work_dir}")
    script = json.loads(script_path.read_text())
    old = script.get("style", "painted-epic")

    from .scripting.generator import restyle_script

    print(f"Restyling {script['slug']}: {old} → {style} …")
    script = restyle_script(script, channel, style, notes=notes)
    script_path.write_text(json.dumps(script, indent=2))
    print(f"  ✓ {script_path} — visuals rewritten, narration untouched")
    print(f"\nNow re-render (existing voiceover is reused automatically):")
    print(f"  python -m minimyths produce {work_dir}")


def _cmd_reroll(work_dir: Path, channel, beats: list[str], style=None):
    """Regenerate cherry-picked beat images, then re-run produce to see them."""
    from .visuals.images import generate_one

    script = json.loads((work_dir / "script.json").read_text())
    if style:
        script["style"] = style  # in-memory override, script.json untouched
    for spec in beats:
        try:
            section, index = spec.split(":")
            index = int(index)
            script[section]["beats"][index]
        except (ValueError, KeyError, IndexError):
            sys.exit(f"Bad beat spec '{spec}' — use section:index, e.g. main:4")
        path = generate_one(script, section, index, work_dir / "frames", channel)
        print(f"  ✓ rerolled {spec} → {path}")
    print(f"\nRe-render to pick up the new frames:\n  python -m minimyths produce {work_dir}")


def _cmd_review(work_dir: Path):
    """Contact sheet: every beat's frame + narration + timing in one HTML page."""
    script = json.loads((work_dir / "script.json").read_text())
    rows = []
    for section in ("main", "short"):
        rows.append(f"<h2>{section} — {sum(b['seconds'] for b in script[section]['beats'])}s target</h2>")
        for i, beat in enumerate(script[section]["beats"]):
            frame = work_dir / "frames" / f"{section}_{i:02d}.png"
            img = (f'<img src="frames/{frame.name}" loading="lazy">'
                   if frame.exists() else "<em>(no frame rendered yet)</em>")
            rows.append(
                f'<div class="beat">{img}<div><b>{section}:{i}</b> '
                f'({beat["seconds"]}s)<p>{beat["narration"]}</p>'
                f'<p class="v">🎨 {beat["visual"]}</p></div></div>'
            )
    html = (
        "<!doctype html><meta charset='utf-8'>"
        f"<title>{script['title']} — review</title>"
        "<style>body{font-family:sans-serif;max-width:1100px;margin:2rem auto}"
        ".beat{display:flex;gap:1rem;margin:1rem 0;border-bottom:1px solid #ddd;padding-bottom:1rem}"
        ".beat img{width:320px;height:auto;border-radius:6px}"
        ".v{color:#777;font-size:.85em}</style>"
        f"<h1>{script['title']}</h1>" + "".join(rows)
    )
    out = work_dir / "review.html"
    out.write_text(html)
    print(f"  ✓ {out}\n  open {out}")
    print("Spot a weak frame? Reroll it:  python -m minimyths reroll "
          f"{work_dir} main:4")


def _cmd_animate(work_dir: Path, channel, beat_spec: str, style=None, backend=None):
    """Animate a single beat and report time — the quality/cost test before
    pointing a full produce run at a motion engine."""
    import time

    from .visuals import animate
    from .visuals.images import resolve_style
    from .visuals.motion import motion_prompt

    script = json.loads((work_dir / "script.json").read_text())
    if style:
        script["style"] = style  # in-memory override, script.json untouched
    try:
        section, index = beat_spec.split(":")
        beat = script[section]["beats"][int(index)]
    except (ValueError, KeyError, IndexError):
        sys.exit(f"Bad beat spec '{beat_spec}' — use section:index, e.g. main:0")

    frame = work_dir / "frames" / f"{section}_{int(index):02d}.png"
    if not frame.exists():
        sys.exit(f"No keyframe at {frame} — run produce (or reroll) first")

    backend = backend or channel["visuals"].get("motion_backend")
    if backend not in ("fal", "draw_things"):
        backend = "fal"  # the sensible test default once ken_burns is outgrown
    if backend == "fal":
        cfg = channel["visuals"].get("fal", {})
        animate.check_fal(cfg)
        engine = animate.fal_clip
    else:
        cfg = channel["visuals"].get("draw_things", {})
        animate.check_server(cfg)
        engine = animate.animated_clip

    suffix = resolve_style(script, channel)["suffix"].strip()
    prompt = motion_prompt(beat, suffix)
    out = work_dir / "clips" / f"animated_test_{section}_{int(index):02d}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".motion.txt").unlink(missing_ok=True)  # force fresh render

    print(f"Animating {beat_spec} via {backend} …")
    print(f"  motion prompt: {prompt[:140]}…")
    t0 = time.monotonic()
    engine(frame, out, beat["seconds"] + 0.4, prompt,
           portrait=(section == "short"), cfg=cfg)
    minutes = (time.monotonic() - t0) / 60
    print(f"  ✓ {out}  ({minutes:.1f} min)")
    n_beats = len(script["main"]["beats"]) + len(script["short"]["beats"])
    print(f"  Full episode estimate: ~{minutes * n_beats:.0f} min for {n_beats} beats")
    print(f"  Watch it:  open {out}")


def _cmd_publish(work_dir: Path, channel, publish_at, skip_short):
    script = json.loads((work_dir / "script.json").read_text())
    from .publish import upload_video

    main_path = work_dir / "final" / "main.mp4"
    print(f"Uploading {main_path} …")
    vid = upload_video(main_path, script, channel, publish_at=publish_at)
    print(f"  ✓ https://youtu.be/{vid}")
    from .sourcing.ledger import mark

    mark(script["slug"], "published", title=script["title"],
         url=f"https://youtu.be/{vid}")

    short_path = work_dir / "final" / "short.mp4"
    if not skip_short and short_path.exists():
        print(f"Uploading {short_path} …")
        vid = upload_video(short_path, script, channel, is_short=True)
        print(f"  ✓ https://youtu.be/{vid}")
