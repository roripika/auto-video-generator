#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
if [[ ! -d "$VENV_DIR" ]]; then
  echo "[ERROR] .venv not found. Please run Setup.command first." >&2
  exit 1
fi
source "$VENV_DIR/bin/activate"
python scripts/generate_script_from_brief.py --brief "テスト" --sections 5 --provider openai --stdout | head -n 40
