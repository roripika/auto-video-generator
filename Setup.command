#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

# Ensure Homebrew dependencies when available
if command -v brew >/dev/null 2>&1; then
  brew install --quiet ffmpeg || echo "Please install ffmpeg manually if brew is unavailable"
  brew install --quiet p7zip || echo "Please install p7zip manually if brew is unavailable"
  if ! command -v pyenv >/dev/null 2>&1; then
    echo "[Setup] pyenv not found. Installing via Homebrew..."
    brew install pyenv || echo "Failed to install pyenv via Homebrew."
  fi
  brew install --quiet gettext || echo "Please install gettext manually if required."
fi

PYTHON_BIN="python3"
USE_PYENV=true
if ! command -v pyenv >/dev/null 2>&1; then
  USE_PYENV=false
fi

if $USE_PYENV; then
  PYENV_VERSION="${PYENV_PYTHON_VERSION:-3.10.15}"
  if command -v brew >/dev/null 2>&1; then
    export LDFLAGS="-L/opt/homebrew/opt/zlib/lib -L/opt/homebrew/opt/sqlite/lib -L/opt/homebrew/opt/readline/lib -L/opt/homebrew/opt/gettext/lib ${LDFLAGS:-}"
    export CPPFLAGS="-I/opt/homebrew/opt/zlib/include -I/opt/homebrew/opt/sqlite/include -I/opt/homebrew/opt/readline/include -I/opt/homebrew/opt/gettext/include ${CPPFLAGS:-}"
    export PKG_CONFIG_PATH="/opt/homebrew/opt/zlib/lib/pkgconfig:/opt/homebrew/opt/sqlite/lib/pkgconfig:/opt/homebrew/opt/gettext/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
  fi
  if ! pyenv versions --bare | grep -Fxq "$PYENV_VERSION"; then
    echo "[Setup] pyenv python $PYENV_VERSION not found. Installing..."
    if ! pyenv install "$PYENV_VERSION"; then
      echo "[WARN] pyenv install failed. Falling back to system python3."
      USE_PYENV=false
    fi
  fi
fi

if $USE_PYENV; then
  eval "$(pyenv init -)"
  PYTHON_BIN="$(pyenv root)/versions/$PYENV_VERSION/bin/python"
else
  if command -v brew >/dev/null 2>&1 && command -v /opt/homebrew/bin/python3 >/dev/null 2>&1; then
    PYTHON_BIN="/opt/homebrew/bin/python3"
    echo "[INFO] Using Homebrew python ($($PYTHON_BIN --version 2>/dev/null))."
  else
    PYTHON_BIN="python3"
    echo "[INFO] Using system python3 ($(python3 --version 2>/dev/null)). For the most stable experience, install pyenv manually."
  fi
fi

rm -rf .venv
"$PYTHON_BIN" -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt || pip install pydantic PyYAML requests

if [[ -x scripts/setup_voicevox.sh ]]; then
  echo "Installing VOICEVOX Engine..."
  scripts/setup_voicevox.sh || echo "VOICEVOX Engine setup failed. You can rerun scripts/setup_voicevox.sh later."
else
  echo "scripts/setup_voicevox.sh が見つかりませんでした。VOICEVOX Engine は手動でセットアップしてください。"
fi

echo "Setup completed. Activate with 'source .venv/bin/activate'"
