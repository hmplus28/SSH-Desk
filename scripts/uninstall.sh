#!/usr/bin/env bash
# SSH Desk - user-level uninstaller
# User data and keyring secrets are NEVER removed without explicit confirmation.
set -uo pipefail

DATA_DIR="${HOME}/.local/share/ssh-desk"
CONFIG_DIR="${HOME}/.config/ssh-desk"
BIN_DIR="${HOME}/.local/bin"
CLI="${BIN_DIR}/ssh-desk-cli"

log()  { printf '\033[1;34m::\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!\033[0m %s\n' "$*"; }

# ---------------------------------------------------------------- binaries
log "Removing program files"
if [ -x "$CLI" ]; then
    # figure out the configured CLI name and remove its symlink
    NAME="$("$CLI" config get cli_command_name 2>/dev/null || echo sss)"
    rm -f "${BIN_DIR:?}/${NAME}"
else
    rm -f "${BIN_DIR:?}/sss"
fi
rm -f "${BIN_DIR:?}/ssh-desk" "${BIN_DIR:?}/ssh-desk-cli" "${BIN_DIR:?}/ssh-desk-askpass"
rm -f "${HOME}/.local/share/applications/ssh-desk.desktop"
rm -f "${HOME}/.local/share/icons/hicolor/scalable/apps/ssh-desk.svg"
rm -rf "${DATA_DIR}/venv"

# ---------------------------------------------------------------- data
if [ -d "$DATA_DIR" ] || [ -d "$CONFIG_DIR" ]; then
    warn "User data found:"
    [ -d "$DATA_DIR" ]   && warn "  $DATA_DIR   (database, known_hosts, keys, logs)"
    [ -d "$CONFIG_DIR" ] && warn "  $CONFIG_DIR (settings)"
    printf 'Delete user data AND purge stored passwords from GNOME Keyring? [y/N] '
    read -r answer
    if [ "${answer:-n}" = "y" ] || [ "${answer:-n}" = "Y" ]; then
        if [ -x "$CLI" ]; then
            "$CLI" uninstall-data --yes || true
        fi
        rm -rf "${DATA_DIR:?}" "${CONFIG_DIR:?}"
        log "User data and keyring secrets removed."
    else
        log "User data kept at $DATA_DIR and $CONFIG_DIR."
        log "Purge later with: ssh-desk-cli uninstall-data"
    fi
fi

log "SSH Desk uninstalled."
