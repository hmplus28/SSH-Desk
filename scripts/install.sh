#!/usr/bin/env bash
# SSH Desk - user-level installer (no sudo required)
# Installs into ~/.local/share/ssh-desk/venv and creates CLI symlinks in ~/.local/bin
#
# Network resilience (outages / blocked PyPI):
#   * pip installs walk a mirror fallback chain (see scripts/mirrors.sh)
#   * --offline installs from pre-downloaded wheels, no network needed
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_DIR="${HOME}/.local/share/ssh-desk"
BIN_DIR="${HOME}/.local/bin"
VENV_DIR="${DATA_DIR}/venv"
PYTHON="${PYTHON:-python3}"

. "$SCRIPT_DIR/mirrors.sh"

fail() { printf '\033[1;31m✘\033[0m %s\n' "$*" >&2; exit 1; }

OFFLINE=0
WHEELHOUSE="${SSH_DESK_WHEELHOUSE:-}"
QUIET=(-q)

usage() {
    cat <<'EOF'
SSH Desk installer (user-level, no sudo)

Usage: bash scripts/install.sh [options]

Network options:
  --mirror URL          Force one PyPI index URL (no fallback)
  --mirror-name NAME    pypi | ir | tuna | aliyun | tencent
  --no-mirrors          Use official PyPI only
  --offline             Install without network from local wheels
  --wheelhouse DIR      Wheels directory for --offline (default: vendor/wheels)

Other options:
  --verbose             Show full pip output
  -h, --help            Show this help

Environment overrides:
  SSH_DESK_PIP_INDEX_URL   Force a mirror (same as --mirror)
  SSH_DESK_WHEELHOUSE      Default wheelhouse directory
  PYTHON                   Python interpreter (default: python3)

Offline flow (two machines, or before an outage):
  bash scripts/download_wheels.sh --mirror-name ir
  bash scripts/install.sh --offline
EOF
}

# ---------------------------------------------------------------- options
while [ $# -gt 0 ]; do
    case "$1" in
        --mirror|--mirror-url)
            [ $# -ge 2 ] || fail "option $1 needs a URL"
            SSH_DESK_PIP_INDEX_URL="$2"; shift 2 ;;
        --mirror-name)
            [ $# -ge 2 ] || fail "option $1 needs a name"
            SSH_DESK_PIP_INDEX_URL="$(ssh_desk_mirror_url "$2")" || exit 1; shift 2 ;;
        --no-mirrors)  SSH_DESK_PIP_INDEX_URL="https://pypi.org/simple"; shift ;;
        --offline)     OFFLINE=1; shift ;;
        --wheelhouse)
            [ $# -ge 2 ] || fail "option $1 needs a directory"
            WHEELHOUSE="$2"; shift 2 ;;
        --verbose)     QUIET=(); shift ;;
        -h|--help)     usage; exit 0 ;;
        *)             fail "unknown option: $1 (try --help)" ;;
    esac
done

if [ "$OFFLINE" = 1 ]; then
    WHEELHOUSE="${WHEELHOUSE:-$REPO_DIR/vendor/wheels}"
    [ -d "$WHEELHOUSE" ] || fail "--offline needs a wheels directory. Fill it first (on any machine with internet):
  bash scripts/download_wheels.sh"
    export SSH_DESK_WHEELHOUSE="$WHEELHOUSE"
    ssh_desk_log "offline mode — wheelhouse: $WHEELHOUSE"
fi

# ---------------------------------------------------------------- checks
command -v "$PYTHON" >/dev/null 2>&1 || fail "Python 3 not found (python3)."
"$PYTHON" - <<'EOF' || fail "Python 3.10+ is required."
import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)
EOF

command -v ssh >/dev/null 2>&1 || fail "OpenSSH client not found. Install it first:
  sudo apt install openssh-client"
ssh_desk_log "OpenSSH found: $(ssh -V 2>&1)"

# ---------------------------------------------------------------- venv
ssh_desk_log "Creating virtual environment at ${VENV_DIR}"
mkdir -p "$DATA_DIR" "$BIN_DIR"
"$PYTHON" -m venv "$VENV_DIR"

SSH_DESK_PIP=("$VENV_DIR/bin/pip")

if [ "$OFFLINE" = 1 ]; then
    ssh_desk_log "Installing SSH Desk from local wheels"
    pip_resilient install "$REPO_DIR" "${QUIET[@]}"
else
    ssh_desk_log "Installing SSH Desk (auto-fallback across PyPI mirrors)"
    pip_resilient install --upgrade pip "${QUIET[@]}"
    pip_resilient install "$REPO_DIR" "${QUIET[@]}"
fi

# ---------------------------------------------------------------- entries
ln -sf "$VENV_DIR/bin/ssh-desk"        "$BIN_DIR/ssh-desk"
ln -sf "$VENV_DIR/bin/ssh-desk-cli"    "$BIN_DIR/ssh-desk-cli"
ln -sf "$VENV_DIR/bin/ssh-desk-askpass" "$BIN_DIR/ssh-desk-askpass"

ssh_desk_log "Installing CLI command + bash completion"
"$BIN_DIR/ssh-desk-cli" install-cli --name sss >/dev/null 2>&1 || true
mkdir -p "${HOME}/.local/share/bash-completion/completions"
"$BIN_DIR/ssh-desk-cli" config completions --shell bash --install >/dev/null 2>&1 || true

# ---------------------------------------------------------------- desktop
if [ -t 0 ]; then
    ssh_desk_log "Installing desktop entry and icon"
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
        ssh_desk_log "NOTE: $BIN_DIR is not in PATH. Add this to ~/.bashrc and reopen the terminal:"
        printf '    export PATH="%s:$PATH"\n' "$BIN_DIR"
        ;;
esac

ssh_desk_log "Done!"
printf '  GUI : %s/ssh-desk\n' "$BIN_DIR"
printf '  CLI : %s/sss --help\n' "$BIN_DIR"
