#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$SCRIPT_DIR/desktop-app"

if [[ ! -d "$APP_DIR" ]]; then
  echo "Desktop app directory not found at $APP_DIR"
  exit 1
fi

VENV_DIR="$SCRIPT_DIR/.venv"
if [[ -d "$VENV_DIR" ]]; then
  source "$VENV_DIR/bin/activate"
  export PYTHON_BIN="$VENV_DIR/bin/python"
else
  echo ".venv not found. Please run Setup.command first."
  exit 1
fi

export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"

cd "$APP_DIR"

if [[ ! -d node_modules ]]; then
  echo "[Setup] Installing npm dependencies..."
  npm install
fi

echo "[Start] Launching Electron desktop app..."
npm start
