# Changelog

All notable changes are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] - 2026-11-06

### Added
- **Core engine** shared by GUI and CLI: SQLite + SQLAlchemy 2.0 models
  (servers, saved paths, groups, keys, history, commands, tunnels, settings)
  with migrations, WAL, and 0600 permissions.
- **Security**:
  - Passwords/passphrases stored only in the Secret Service (GNOME Keyring).
  - Secure askpass helper — OpenSSH resolves secrets by reference; no argv/env
    leakage, no sshpass.
  - Strict host key policy with fingerprint dialogs and change warnings.
  - Redacting logger; input validation with Pydantic; argv-list subprocess only.
- **SSH engine**: interactive sessions, exec, per-run user/port overrides,
  jump hosts via `ssh -W` ProxyCommand (nested), keep-alive/compression/custom
  options.
- **CLI** (`sss` by default, renameable): list/add/info/test/edit/delete,
  alias shortcut with saved paths, search, history, current, config, tunnel
  start/stop, keys management, ssh-config import with preview, TOML
  export/backup/restore, bash+zsh completion.
- **GUI** (PySide6): Dashboard, Servers (search/sort/filter/groups/favorites),
  Add/Edit with 4 tabs + live connection test, Server Details with masked
  secret reveal, multi-tab **real PTY terminal** (pyte VT100: colors, vim/nano,
  resize, selection/copy/paste), two-pane SFTP file manager (upload/download/
  rename/chmod/edit/server-to-server transfer), SSH Keys (generate/import/
  export/ssh-copy-id), Tunnels (local/remote/SOCKS with detached daemon),
  Saved Commands (with confirmation flag), History, Settings.
  Dark/Light themes, Persian/English with RTL, toasts, empty/error/loading
  states, keyboard shortcuts.
- **Tunnel daemon**: detached runner with status/pid/error tracking in the DB.
- **Packaging**: PyInstaller spec, DEB pipeline (validated), user-level
  `install.sh` / `uninstall.sh` (consent-gated data+secret purge).
- **Tests**: 54 tests (services, CLI, validation, hostkeys incl. hashed
  entries, backup/restore round-trip, GUI smoke) — all green; ruff clean.
- **Docs**: README (EN/FA quick start), Installation, User Guide, CLI
  Reference, Architecture, Security, Development, Troubleshooting, Changelog.

[1.0.0]: https://github.com/hmplus28/SSH-Desk/releases/tag/v1.0.0
