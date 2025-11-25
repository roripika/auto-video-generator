#!/usr/bin/env bash
set -euo pipefail

VERSION="${VOICEVOX_ENGINE_VERSION:-0.25.0}"
TARGET_DIR="${VOICEVOX_ENGINE_DIR:-tools/voicevox_engine}"
OS_NAME="$(uname -s)"
ARCH_NAME="$(uname -m)"

case "$OS_NAME" in
  Darwin)
    if [[ "$ARCH_NAME" == "arm64" ]]; then
      PLATFORM="macos-arm64"
    else
      PLATFORM="macos-x64"
    fi
    ;;
  Linux)
    if [[ "$ARCH_NAME" == "aarch64" || "$ARCH_NAME" == "arm64" ]]; then
      PLATFORM="linux-cpu-arm64"
    else
      PLATFORM="linux-cpu-x64"
    fi
    ;;
  *)
    echo "Unsupported OS: $OS_NAME. Please install VOICEVOX Engine manually." >&2
    exit 1
    ;;
esac

ASSET="voicevox_engine-${PLATFORM}-${VERSION}.7z.001"
DEFAULT_URL="https://github.com/VOICEVOX/voicevox_engine/releases/download/${VERSION}/${ASSET}"
DOWNLOAD_URL="${VOICEVOX_ENGINE_URL:-$DEFAULT_URL}"

echo "VOICEVOX Engine setup"
echo "  Version : $VERSION"
echo "  Platform: $PLATFORM"
echo "  Target  : $TARGET_DIR"
echo "  Source  : $DOWNLOAD_URL"

if ! command -v 7z >/dev/null 2>&1 && ! command -v 7za >/dev/null 2>&1 && ! command -v 7zr >/dev/null 2>&1; then
  echo "7z コマンドが見つかりません。'brew install p7zip' などで 7zip を導入してください。" >&2
  exit 1
fi

SEVEN_ZIP="$(command -v 7z || command -v 7za || command -v 7zr)"

mkdir -p "$TARGET_DIR"
WORK_DIR="$(mktemp -d)"
ARCHIVE_PATH="$WORK_DIR/$ASSET"
trap 'rm -rf "$WORK_DIR"' EXIT

echo "Downloading package..."
if ! curl -fL "$DOWNLOAD_URL" -o "$ARCHIVE_PATH"; then
  echo "Failed to download $DOWNLOAD_URL" >&2
  exit 1
fi

echo "Extracting archive..."
"$SEVEN_ZIP" x -y "$ARCHIVE_PATH" -o"$WORK_DIR" >/dev/null
rm -f "$ARCHIVE_PATH"

# Some releases extract to an intermediate .7z file. Unpack again if needed.
INTERMEDIATE="$(find "$WORK_DIR" -maxdepth 1 -type f -name 'voicevox_engine-*.7z' | head -n 1)"
if [[ -n "$INTERMEDIATE" ]]; then
  "$SEVEN_ZIP" x -y "$INTERMEDIATE" -o"$WORK_DIR" >/dev/null
  rm -f "$INTERMEDIATE"
fi

RUN_FILE="$(find "$WORK_DIR" -maxdepth 6 -type f -name 'run' | head -n 1)"
if [[ -z "$RUN_FILE" ]]; then
  echo "Failed to locate 'run' script inside extracted archive." >&2
  exit 1
fi
EXTRACTED_DIR="$(dirname "$RUN_FILE")"

rsync -a --delete "$EXTRACTED_DIR"/ "$TARGET_DIR"/

echo "VOICEVOX Engine files installed to $TARGET_DIR"
echo "You can start the engine via Start_VoicevoxEngine.command"
