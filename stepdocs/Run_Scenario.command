#!/bin/bash
set -euo pipefail

# Run Playwright + Electron scenario for stepdocs
# Usage: double-click or run from terminal.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Use the bundled Electron (desktop-app/node_modules/electron)
export ELECTRON_PATH="$ROOT_DIR/desktop-app/node_modules/electron/dist/Electron.app/Contents/MacOS/Electron"
export ELECTRON_ENABLE_LOGGING=1
# Electron must NOT run as node.
unset ELECTRON_RUN_AS_NODE

cd "$SCRIPT_DIR"

SCENARIO_PATH="${1:-$SCRIPT_DIR/stepdocs/scenarios/02_basic_flow.json}"

if [[ ! -f "$SCENARIO_PATH" ]]; then
  echo "[ERROR] Scenario not found: $SCENARIO_PATH"
  exit 1
fi

echo "[stepdocs] Running scenario: $SCENARIO_PATH"
node record_electron.js --scenario="$SCENARIO_PATH"
