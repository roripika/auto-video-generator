#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENGINE_DIR="${VOICEVOX_ENGINE_DIR:-$SCRIPT_DIR/tools/voicevox_engine}"
RUN_SCRIPT="${ENGINE_DIR}/run"

if [[ ! -x "$RUN_SCRIPT" ]]; then
  echo "VOICEVOX Engine run script was not found at $RUN_SCRIPT"
  echo "まず 'scripts/setup_voicevox.sh' を実行してエンジンを展開してください。"
  exit 1
fi

cd "$ENGINE_DIR"
chmod +x "$RUN_SCRIPT"
echo "Starting VOICEVOX Engine (Ctrl+C to stop)..."
"$RUN_SCRIPT"
