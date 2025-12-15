#!/bin/bash
# Install Playwright recorder dependencies for stepdocs
set -euo pipefail
cd "$(dirname "$0")"
echo "[stepdocs] Installing dependencies..."
npm install
echo "[stepdocs] Installing Playwright browsers (chromium only)..."
npx playwright install chromium
echo "[stepdocs] Done. You can now run 'npm run record'."
