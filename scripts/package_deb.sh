#!/usr/bin/env bash
# SSH Desk - build a DEB package (dist/ssh-desk_<version>_amd64.deb)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

STAGING="packaging/_staging/ssh-desk"
DIST_DIR="dist"
VERSION="$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml | head -1)"

command -v dpkg-deb >/dev/null 2>&1 || { echo "dpkg-deb is required"; exit 1; }

echo ":: building PyInstaller bundle first"
bash scripts/build.sh

echo ":: staging DEB tree (version ${VERSION})"
rm -rf packaging/_staging
mkdir -p \
    "$STAGING/opt/ssh-desk" \
    "$STAGING/usr/bin" \
    "$STAGING/usr/share/applications" \
    "$STAGING/usr/share/icons/hicolor/scalable/apps" \
    "$STAGING/usr/share/doc/ssh-desk" \
    "$STAGING/DEBIAN"

cp -a "$DIST_DIR/ssh-desk/." "$STAGING/opt/ssh-desk/"
cp packaging/ssh-desk.desktop "$STAGING/usr/share/applications/"
cp packaging/ssh-desk.svg      "$STAGING/usr/share/icons/hicolor/scalable/apps/ssh-desk.svg"
cp README.md LICENSE "$STAGING/usr/share/doc/ssh-desk/" 2>/dev/null || true

cp packaging/deb/control  "$STAGING/DEBIAN/control"
sed -i "s/^Version: .*/Version: ${VERSION}/" "$STAGING/DEBIAN/control"
cp packaging/deb/postinst "$STAGING/DEBIAN/postinst"
cp packaging/deb/prerm    "$STAGING/DEBIAN/prerm"
chmod 755 "$STAGING/DEBIAN/postinst" "$STAGING/DEBIAN/prerm"

echo ":: building package"
mkdir -p "$DIST_DIR"
dpkg-deb --build --root-owner-group "$STAGING" "$DIST_DIR/ssh-desk_${VERSION}_amd64.deb"

echo ":: done: $DIST_DIR/ssh-desk_${VERSION}_amd64.deb"
echo "   install: sudo apt install $DIST_DIR/ssh-desk_${VERSION}_amd64.deb"
echo "     (or)  sudo dpkg -i $DIST_DIR/ssh-desk_${VERSION}_amd64.deb"
