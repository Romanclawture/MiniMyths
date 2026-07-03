"""Channel configuration loading."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CHANNELS_DIR = REPO_ROOT / "config" / "channels"
CONTENT_DIR = REPO_ROOT / "content"


def load_channel(name: str) -> dict:
    """Load a channel config by name (filename without .yaml)."""
    path = CHANNELS_DIR / f"{name}.yaml"
    if not path.exists():
        available = sorted(p.stem for p in CHANNELS_DIR.glob("*.yaml"))
        raise FileNotFoundError(
            f"No channel config '{name}'. Available: {', '.join(available) or 'none'}"
        )
    with open(path) as f:
        return yaml.safe_load(f)


def content_dir(slug: str) -> Path:
    """Working directory for one video, created on demand."""
    d = CONTENT_DIR / slug
    d.mkdir(parents=True, exist_ok=True)
    return d
