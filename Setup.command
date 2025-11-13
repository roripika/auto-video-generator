#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt || pip install pydantic PyYAML requests

brew install --quiet ffmpeg || echo "Please install ffmpeg manually if brew is unavailable"

echo "Setup completed. Activate with 'source .venv/bin/activate'"
