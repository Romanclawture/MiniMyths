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

    p = sub.add_parser("produce", parents=[common], help="voiceover + visuals + final videos")
    p.add_argument("dir", help="content dir containing script.json")

    p = sub.add_parser("publish", parents=[common], help="upload finals to YouTube")
    p.add_argument("dir")
    p.add_argument("--at", help="RFC3339 publish time (schedules the upload)")
    p.add_argument("--skip-short", action="store_true")

    p = sub.add_parser("run", parents=[common], help="script + produce + publish in one go")
    p.add_argument("topic")
    p.add_argument("--wiki")

    args = parser.parse_args(argv)
    channel = load_channel(args.channel)

    if args.command == "source":
        _cmd_source(args, channel)
    elif args.command == "script":
        _cmd_script(args.topic, args.wiki, channel)
    elif args.command == "produce":
        _cmd_produce(Path(args.dir), channel)
    elif args.command == "publish":
        _cmd_publish(Path(args.dir), channel, args.at, args.skip_short)
    elif args.command == "run":
        script_dir = _cmd_script(args.topic, args.wiki, channel)
        _cmd_produce(script_dir, channel)
        print("\nReview the finals, then:")
        print(f"  python -m minimyths publish {script_dir}")


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


def _cmd_script(topic, wiki, channel) -> Path:
    from .scripting import generate_script

    print(f"Generating script for: {topic} …")
    script = generate_script(topic, channel, wikipedia_title=wiki)
    out_dir = content_dir(script["slug"])
    path = out_dir / "script.json"
    path.write_text(json.dumps(script, indent=2))
    from .scripting.schema import word_count

    print(f"  ✓ {path}")
    print(f"    main: {len(script['main']['beats'])} beats, {word_count(script, 'main')} words")
    print(f"    short: {len(script['short']['beats'])} beats, {word_count(script, 'short')} words")
    return out_dir


def _cmd_produce(work_dir: Path, channel):
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
    outputs = assemble(script, clips, manifest, work_dir / "final")
    for section, path in outputs.items():
        print(f"  ✓ {section}: {path}")


def _cmd_publish(work_dir: Path, channel, publish_at, skip_short):
    script = json.loads((work_dir / "script.json").read_text())
    from .publish import upload_video

    main_path = work_dir / "final" / "main.mp4"
    print(f"Uploading {main_path} …")
    vid = upload_video(main_path, script, channel, publish_at=publish_at)
    print(f"  ✓ https://youtu.be/{vid}")

    short_path = work_dir / "final" / "short.mp4"
    if not skip_short and short_path.exists():
        print(f"Uploading {short_path} …")
        vid = upload_video(short_path, script, channel, is_short=True)
        print(f"  ✓ https://youtu.be/{vid}")
