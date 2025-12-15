#!/bin/bash
# Run the Playwright step recorder (npm run record) inside stepdocs
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d "${HOME}/Library/Caches/ms-playwright" ]; then
  echo "[stepdocs] Playwright browsers not found. Installing chromium..."
  npx playwright install chromium
fi
echo "[stepdocs] Running recorder..."
npm run record
echo "[stepdocs] Recorder finished. Check docs/stepdocs/steps.json and screenshots."
