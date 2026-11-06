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

## [1.0.2] - 2026-11-07

### Added
- **7-language application** (GUI + CLI): English, Persian, Arabic, Chinese,
  Russian, Spanish, French.
  - `ssh_desk.i18n` shared strings module (288 keys x 7 languages, single
    source of truth) with `ssh_desk.gui.i18n` kept as a compatible re-export.
  - RTL layout for Persian **and** Arabic; language picker in Settings shows
    all seven languages with native names.
  - CLI messages and table headers localized; language follows the shared
    settings (`config.toml`) at startup; CJK-aware column widths in CLI
    tables; locale suffixes (`fa_IR`, `zh_CN.UTF-8`) accepted.
- **User-guide PDFs in 7 languages** (`docs/SSH-Desk-User-Guide-*.pdf`):
  en, fa (updated to reflect the 7-language UI), ar, zh, ru, es, fr —
  same illustrated dark design; Arabic and Persian use full RTL layout.
- **Discoverability**: `llms.txt` and `llms-full.txt` for AI assistants,
  FAQ section in the README, richer repository metadata (description,
  topics) for search engines.

### Tests
- `tests/test_i18n.py`: completeness (7 languages), placeholder parity,
  RTL rules, locale parsing, GUI-shim state sharing — 65 tests green,
  ruff clean, mypy clean.

[1.0.0]: https://github.com/hmplus28/SSH-Desk/releases/tag/v1.0.0

## [1.0.1] - 2026-11-07

### Added
- **Network resilience for installs** (outages / blocked PyPI):
  - `scripts/mirrors.sh`: shared mirror-fallback library — every pip call
    walks a chain (`pypi.org` → ArvanCloud IR → TUNA → Aliyun → Tencent) and
    skips unreachable mirrors automatically.
  - `scripts/install.sh`: `--mirror URL`, `--mirror-name pypi|ir|tuna|aliyun|
    tencent`, `--no-mirrors`, `--offline`, `--wheelhouse DIR`, `--verbose`.
  - `scripts/download_wheels.sh`: pre-download all wheels (incl. pip/setuptools/
    wheel) for a fully offline `install.sh --offline` (`--no-index`).
  - `scripts/build.sh`: same fallback chain for PyInstaller/DEB builds.
  - Env overrides: `SSH_DESK_PIP_INDEX_URL`, `SSH_DESK_MIRRORS`,
    `SSH_DESK_WHEELHOUSE`, `SSH_DESK_PIP_TIMEOUT`, `SSH_DESK_PIP_RETRIES`.
  - Offline/mirror flow tested end-to-end (bad-mirror fallback, forced-mirror
    failure, offline venv install, actionable errors).

[1.0.1]: https://github.com/hmplus28/SSH-Desk/releases/tag/v1.0.1
