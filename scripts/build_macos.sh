#!/usr/bin/env bash
# Build a distributable GridNotes.app for macOS (Apple Silicon / arm64 only).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

APP_NAME="GridNotes"
BUILD_VENV="$ROOT_DIR/.build-venv"
DIST_DIR="$ROOT_DIR/dist"
BUILD_DIR="$ROOT_DIR/build"
APP_BUNDLE="$DIST_DIR/${APP_NAME}.app"
ZIP_PATH="$DIST_DIR/GridNotes-macOS-AppleSilicon.zip"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Error: macOS build must run on Darwin." >&2
  exit 1
fi

if [[ "$(uname -m)" != "arm64" ]]; then
  echo "Error: GridNotes macOS releases target Apple Silicon (arm64) only." >&2
  exit 1
fi

echo "==> Building $APP_NAME for macOS (Apple Silicon) from $ROOT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required on PATH." >&2
  exit 1
fi

echo "==> Creating build virtual environment"
rm -rf "$BUILD_VENV"
python3 -m venv "$BUILD_VENV"
# shellcheck disable=SC1091
source "$BUILD_VENV/bin/activate"

echo "==> Installing dependencies"
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt

echo "==> Cleaning previous build artifacts"
rm -rf "$BUILD_DIR" "$DIST_DIR"

echo "==> Generating icon.icns for macOS"
python "$ROOT_DIR/scripts/generate_icon.py"

echo "==> Running PyInstaller"
pyinstaller gridnotes.spec --noconfirm --clean

if [[ ! -d "$APP_BUNDLE" ]]; then
  echo "Error: expected app bundle at $APP_BUNDLE" >&2
  exit 1
fi

if [[ -d "$APP_BUNDLE/Contents/MacOS/tests" ]]; then
  echo "Error: tests/ must not be included in the app bundle" >&2
  exit 1
fi

while IFS= read -r artifact; do
  echo "Error: test artifacts must not be bundled: $artifact" >&2
  exit 1
done < <(find "$APP_BUNDLE" \( -name 'test_*.py' -o -name 'conftest.py' -o -name 'pytest.ini' \) -print)

if command -v codesign >/dev/null 2>&1; then
  echo "==> Ad-hoc signing app bundle"
  codesign --force --deep --sign - "$APP_BUNDLE"
fi

echo "==> Creating GridNotes-macOS-AppleSilicon.zip"
rm -f "$ZIP_PATH"
(
  cd "$DIST_DIR"
  zip -ry "$(basename "$ZIP_PATH")" "$(basename "$APP_BUNDLE")"
)

echo ""
echo "Build complete."
echo "  App bundle: $APP_BUNDLE"
echo "  Zip:        $ZIP_PATH"
echo ""
echo "Share the zip with others. They unzip it and open GridNotes.app."
echo "If macOS blocks the app: right-click GridNotes.app → Open → Open."
echo ""
echo "User data is stored at:"
echo "  ~/Library/Application Support/GridNotes/driver_history.db"
