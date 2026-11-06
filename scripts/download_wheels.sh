#!/usr/bin/env bash
# SSH Desk - pre-download wheels for OFFLINE installation.
#
# For unreliable or blocked networks: run this ONCE on a machine that has
# internet (directly or via a mirror), keep the "vendor/wheels" folder next
# to the repo, then install with no network at all:
#
#     bash scripts/download_wheels.sh --mirror-name ir
#     # copy/move the repo folder to the target machine, then:
#     bash scripts/install.sh --offline
#
# Notes:
#   * Wheels are platform-specific: run download with the SAME Python major
#     version and architecture as the target machine (both x86_64 here).
#   * The folder can be reused: re-running skips nothing by design (pip
#     re-checks hashes), but keeps files that already exist.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

. "$SCRIPT_DIR/mirrors.sh"

fail() { printf '\033[1;31m✘\033[0m %s\n' "$*" >&2; exit 1; }

OUT="${SSH_DESK_WHEELHOUSE:-$REPO_DIR/vendor/wheels}"
QUIET=(-q)

usage() {
    cat <<'EOF'
Pre-download SSH Desk wheels for offline installation.

Usage: bash scripts/download_wheels.sh [options]

Options:
  -o, --output DIR      Destination directory
                        (default: vendor/wheels in the repo, or $SSH_DESK_WHEELHOUSE)
  --mirror URL          Download through one PyPI index URL
  --mirror-name NAME    pypi | ir | tuna | aliyun | tencent
  --no-mirrors          Official PyPI only
  --verbose             Show full pip output
  -h, --help            Show this help
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -o|--output)     [ $# -ge 2 ] || fail "option $1 needs a directory"; OUT="$2"; shift 2 ;;
        --mirror|--mirror-url)
                         [ $# -ge 2 ] || fail "option $1 needs a URL"
                         SSH_DESK_PIP_INDEX_URL="$2"; shift 2 ;;
        --mirror-name)   [ $# -ge 2 ] || fail "option $1 needs a name"
                         SSH_DESK_PIP_INDEX_URL="$(ssh_desk_mirror_url "$2")" || exit 1; shift 2 ;;
        --no-mirrors)    SSH_DESK_PIP_INDEX_URL="https://pypi.org/simple"; shift ;;
        --verbose)       QUIET=(); shift ;;
        -h|--help)       usage; exit 0 ;;
        *)               fail "unknown option: $1 (try --help)" ;;
    esac
done

command -v python3 >/dev/null 2>&1 || fail "Python 3 not found."
python3 -m pip --version >/dev/null 2>&1 || fail "pip is missing: sudo apt install python3-pip"

mkdir -p "$OUT"
ssh_desk_log "Downloading wheels to: $OUT"
ssh_desk_log "(PySide6 is large — this can take a few minutes on slow links)"

SSH_DESK_PIP=(python3 -m pip)

# bootstrap tools so "install.sh --offline" and future venvs have them too
pip_resilient download pip setuptools wheel --dest "$OUT" "${QUIET[@]}" || true

# the project itself + every dependency, as wheels/sdists
pip_resilient download "$REPO_DIR" --dest "$OUT" "${QUIET[@]}"

ssh_desk_log "Done."
printf '  %s wheel file(s) in %s\n' "$(ls "$OUT" | wc -l)" "$OUT"
printf '\nOffline install on the target machine:\n'
printf '  bash scripts/install.sh --offline\n'
