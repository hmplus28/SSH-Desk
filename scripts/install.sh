#!/usr/bin/env bash
# SSH Desk - user-level installer (no sudo required)
# Installs into ~/.local/share/ssh-desk/venv and creates CLI symlinks in ~/.local/bin
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${HOME}/.local/share/ssh-desk"
BIN_DIR="${HOME}/.local/bin"
VENV_DIR="${DATA_DIR}/venv"
PYTHON="${PYTHON:-python3}"

log()  { printf '\033[1;34m::\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m✘\033[0m %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- checks
command -v "$PYTHON" >/dev/null 2>&1 || fail "Python 3 not found (python3)."
"$PYTHON" - <<'EOF' || fail "Python 3.10+ is required."
import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)
EOF

command -v ssh >/dev/null 2>&1 || fail "OpenSSH client not found. Install it first:\n  sudo apt install openssh-client"
log "OpenSSH found: $(ssh -V 2>&1)"

log "Creating virtual environment at ${VENV_DIR}"
mkdir -p "$DATA_DIR" "$BIN_DIR"
"$PYTHON" -m venv "$VENV_DIR"

log "Installing SSH Desk (this downloads dependencies on first run)"
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install "$REPO_DIR" -q

# ---------------------------------------------------------------- entries
ln -sf "$VENV_DIR/bin/ssh-desk"        "$BIN_DIR/ssh-desk"
ln -sf "$VENV_DIR/bin/ssh-desk-cli"    "$BIN_DIR/ssh-desk-cli"
ln -sf "$VENV_DIR/bin/ssh-desk-askpass" "$BIN_DIR/ssh-desk-askpass"

log "Installing CLI command + bash completion"
"$BIN_DIR/ssh-desk-cli" install-cli --name sss >/dev/null 2>&1 || true
mkdir -p "${HOME}/.local/share/bash-completion/completions"
"$BIN_DIR/ssh-desk-cli" config completions --shell bash --install >/dev/null 2>&1 || true

# ---------------------------------------------------------------- desktop
if [ -t 0 ]; then
    log "Installing desktop entry and icon"
    APPS_DIR="${HOME}/.local/share/applications"
    ICONS_DIR="${HOME}/.local/share/icons/hicolor/scalable/apps"
    mkdir -p "$APPS_DIR" "$ICONS_DIR"
    cp "$REPO_DIR/packaging/ssh-desk.desktop" "$APPS_DIR/"
    cp "$REPO_DIR/packaging/ssh-desk.svg"     "$ICONS_DIR/ssh-desk.svg"
    # point Exec at the user binary
    sed -i "s|Exec=ssh-desk %U|Exec=${BIN_DIR}/ssh-desk %U|" "$APPS_DIR/ssh-desk.desktop"
    update-desktop-database "$APPS_DIR" 2>/dev/null || true
fi

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
        log "NOTE: $BIN_DIR is not in PATH. Add this to ~/.bashrc and reopen the terminal:"
        printf '    export PATH="%s:$PATH"\n' "$BIN_DIR"
        ;;
esac

log "Done!"
printf '  GUI : %s/ssh-desk\n' "$BIN_DIR"
printf '  CLI : %s/sss --help\n' "$BIN_DIR"
