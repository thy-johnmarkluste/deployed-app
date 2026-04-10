#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but not found."
  exit 1
fi

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

pyinstaller --noconfirm --clean ThyWeb.macos.spec
pyinstaller --noconfirm --clean ThyWebSetup.macos.spec

APP_PATH="dist/ThyWeb.app"
if [ ! -d "$APP_PATH" ]; then
  echo "Build succeeded but $APP_PATH was not found."
  exit 1
fi

SETUP_APP_PATH="dist/ThyWebSetup.app"
if [ ! -d "$SETUP_APP_PATH" ]; then
  echo "Build succeeded but $SETUP_APP_PATH was not found."
  exit 1
fi

# Optional signing. Set CODESIGN_IDENTITY to a valid Developer ID if available.
# If not set, use ad-hoc signing so Gatekeeper checks can still run locally.
CODESIGN_IDENTITY="${CODESIGN_IDENTITY:--}"
codesign --deep --force --verify --verbose --sign "$CODESIGN_IDENTITY" "$APP_PATH"
codesign --deep --force --verify --verbose --sign "$CODESIGN_IDENTITY" "$SETUP_APP_PATH"

DMG_PATH="dist/ThyWeb-macOS.dmg"
DMG_STAGING="dist/dmg_staging"
rm -rf "$DMG_STAGING"
mkdir -p "$DMG_STAGING"
cp -R "$APP_PATH" "$DMG_STAGING/ThyWeb.app"
cp -R "$SETUP_APP_PATH" "$DMG_STAGING/ThyWebSetup.app"
hdiutil create -volname "ThyWeb" -srcfolder "$DMG_STAGING" -ov -format UDZO "$DMG_PATH"

PKG_ROOT="dist/pkgroot"
PKG_PATH="dist/ThyWeb-macOS.pkg"
rm -rf "$PKG_ROOT"
mkdir -p "$PKG_ROOT/Applications"
cp -R "$APP_PATH" "$PKG_ROOT/Applications/ThyWeb.app"
cp -R "$SETUP_APP_PATH" "$PKG_ROOT/Applications/ThyWebSetup.app"
pkgbuild \
  --root "$PKG_ROOT" \
  --identifier "com.thyweb.desktop" \
  --version "1.0.1" \
  "$PKG_PATH"

echo "macOS build complete:"
echo "  App: $APP_PATH"
echo "  Setup App: $SETUP_APP_PATH"
echo "  DMG: $DMG_PATH"
echo "  PKG: $PKG_PATH"
