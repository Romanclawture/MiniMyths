#!/usr/bin/env bash
# One-time setup for the M4 Mac mini. Run from the repo root:
#   bash scripts/setup-mac.sh
set -euo pipefail

echo "==> Checking Homebrew prerequisites"
command -v brew >/dev/null || {
  echo 'Homebrew missing — install from https://brew.sh first'; exit 1; }
# python@3.12 pinned: kokoro→spacy→thinc→blis lack wheels on newer Pythons
# (3.14 tries to compile them from source and fails on old Cython pins)
for pkg in ffmpeg espeak-ng python@3.12; do
  brew list "$pkg" >/dev/null 2>&1 || brew install "$pkg"
done
PYTHON="$(brew --prefix python@3.12)/bin/python3.12"

echo "==> Creating virtualenv (Python 3.12)"
if [ -d .venv ] && ! .venv/bin/python --version 2>/dev/null | grep -q "3\.12"; then
  echo "    existing .venv uses $(.venv/bin/python --version 2>&1) — recreating"
  rm -rf .venv
fi
[ -d .venv ] || "$PYTHON" -m venv .venv
source .venv/bin/activate
pip install --quiet --upgrade pip

echo "==> Installing pipeline dependencies"
pip install --quiet -r requirements.txt

echo "==> Installing Kokoro TTS (free local narration)"
pip install --quiet kokoro soundfile

echo "==> Warming up Kokoro (first run downloads the ~330MB model)"
python - <<'EOF'
from kokoro import KPipeline
import soundfile as sf
import numpy as np
p = KPipeline(lang_code="a")
chunks = [a for _, _, a in p("Mini Myths setup complete.", voice="am_michael")]
sf.write("/tmp/kokoro_check.wav", np.concatenate(chunks), 24000)
print("Kokoro OK — wrote /tmp/kokoro_check.wav")
EOF

echo
echo "Setup complete. Next steps:"
echo "  source .venv/bin/activate"
echo "  python -m minimyths audition            # pick the channel voice"
echo "  python -m minimyths produce content/hercules"
