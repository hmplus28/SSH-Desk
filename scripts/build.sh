#!/usr/bin/env bash
# SSH Desk - build PyInstaller bundles (dist/ssh-desk/)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

BUILD_DIR="build/pyinstaller"
DIST_DIR="dist"

command -v python3 >/dev/null 2>&1 || { echo "python3 required"; exit 1; }

echo ":: creating build venv"
python3 -m venv "$BUILD_DIR/venv"
"$BUILD_DIR/venv/bin/pip" install --upgrade pip -q
"$BUILD_DIR/venv/bin/pip" install . pyinstaller -q

echo ":: running PyInstaller"
"$BUILD_DIR/venv/bin/pyinstaller" ssh-desk.spec --noconfirm --distpath "$DIST_DIR" --workpath "$BUILD_DIR/work"

echo ":: bundles ready:"
ls -d "$DIST_DIR"/ssh-desk
echo "  -> $DIST_DIR/ssh-desk/ssh-desk      (GUI)"
echo "  -> $DIST_DIR/ssh-desk/ssh-desk-cli  (CLI)"
