"""Application-wide paths and constants. All user data lives under the user's home."""

import os
from pathlib import Path


def _home() -> Path:
    return Path.home()


def default_config_dir() -> Path:
    return Path(os.environ.get("SSH_DESK_CONFIG_DIR", _home() / ".config" / "ssh-desk"))


def default_data_dir() -> Path:
    return Path(os.environ.get("SSH_DESK_DATA_DIR", _home() / ".local" / "share" / "ssh-desk"))


def default_bin_dir() -> Path:
    return Path(os.environ.get("SSH_DESK_BIN_DIR", _home() / ".local" / "bin"))


CONFIG_FILE_NAME = "config.toml"
DB_FILE_NAME = "ssh-desk.db"
KNOWN_HOSTS_NAME = "known_hosts"
ASKPASS_HELPER_NAME = "ssh-desk-askpass"
CLI_WRAPPER_NAME = "ssh-desk-cli"

TERMINAL_SESSION_ENV = "SSH_DESK_SESSION"
TERMINAL_ALIAS_ENV = "SSH_DESK_ALIAS"
SECRET_REF_ENV = "SSH_DESK_SECRET_REF"

OK_MARKER = "__SSH_DESK_OK__"

RESERVED_CLI_NAMES = {"ssh", "scp", "sftp", "sftp-server", "sudo", "python", "python3", "git", "apt", "systemctl"}

AUTH_TYPES = ("password", "key", "agent", "interactive")
TUNNEL_TYPES = ("local", "remote", "dynamic")
