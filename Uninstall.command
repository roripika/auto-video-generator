#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

echo "[Uninstall] Removing Python virtual environment (.venv)..."
rm -rf .venv

echo "[Uninstall] Removing desktop-app/node_modules..."
rm -rf desktop-app/node_modules

if [[ -d tools/voicevox_engine ]]; then
  read -r -p "Remove tools/voicevox_engine? [y/N] " confirm
  if [[ "${confirm:-N}" =~ ^[Yy]$ ]]; then
    rm -rf tools/voicevox_engine
  fi
fi

echo "[Uninstall] Cleaning caches (work/, tmp/, logs/llm_errors)..."
rm -rf work tmp
rm -rf logs/llm_errors/*

echo "[Uninstall] Done. Run Setup.command to recreate the environment."
