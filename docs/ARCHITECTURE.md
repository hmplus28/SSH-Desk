# Architecture

## Overview

Three independent front-ends over one shared engine:

```
┌────────────┐   ┌────────────┐
│  GUI       │   │  CLI       │
│  PySide6   │   │  Typer     │
└─────┬──────┘   └─────┬──────┘
      │  AppContext (single source of truth)
      ├────────────────┤
      ▼                ▼
┌─────────────────────────────────────────┐
│ services/                               │
│  server · credential · key · connection │
│  history · tunnel · sftp · import/export│
├─────────────────────────────────────────┤
│ ssh/                                    │
│  client (argv builder) · hostkeys       │
│  askpass · config_manager · process_mgr │
│  tunnel_runner (detached daemon)        │
├─────────────────────────────────────────┤
│ database/  SQLite + SQLAlchemy 2.0      │
└─────────────────────────────────────────┘
      │                      │
      ▼                      ▼
~/.local/share/ssh-desk/   GNOME Keyring
  ssh-desk.db (0600)       (Secret Service)
  known_hosts (0600)       secrets only here
  keys/  logs/  bin/
```

## Layers

### core/
- `application.py` — `AppContext`: lazy services, paths, logging, event bus.
  Instantiated once per process; GUI and CLI both use it (`AppContext.instance()`).
- `config.py` — TOML config at `~/.config/ssh-desk/config.toml` (0600), typed
  defaults, survives unknown keys.
- `events.py` — pub/sub so service actions refresh GUI pages.
- `exceptions.py` — one hierarchy; CLI maps to exit codes, GUI to dialogs/toasts.

### database/
- SQLAlchemy 2.0 models (`Server`, `ServerPath`, `ServerGroup`, `SSHKey`,
  `ConnectionHistory`, `SavedCommand`, `Tunnel`, `AppSetting`).
- FKs with `ON DELETE` semantics (`CASCADE` for paths/commands/tunnels,
  `SET NULL` for history/group/jump), unique constraints (alias, server+path name,
  server+tunnel name), `PRAGMA foreign_keys=ON`, WAL, busy timeout.
- `Database.init()` creates the schema on first run and applies numbered
  migrations; the file is chmod 0600.

### services/
- `server_service` — CRUD/validation orchestration, alias uniqueness, groups,
  saved paths (`resolve_target`: default → name → absolute), duplicate
  (re-stores a fresh secret copy), dashboard stats.
- `credential_service` — `SecretServiceStore` (secretstorage) + test-only
  `MemorySecretStore`. Stores by attributes; DB keeps a JSON *reference* only.
  Ephemeral secrets support testing unsaved passwords.
- `key_service` — generation via `cryptography` (OpenSSH private format,
  encrypted with `BestAvailableEncryption` — no passphrase on any argv),
  import (reference vs. copy with consent), fingerprints (SHA256 base64,
  `ssh-keygen -lf` compatible).
- `connection_service` — host-key policy gate (`CliHostKeyGate`,
  `NonInteractiveGate`, GUI gate), session preparation (argv+env, no secrets in
  argv), `test()` with latency, `run_session()` with history recording,
  `proxy_exec()` for jump hosts.
- `tunnel_service` — spawns `python -m ssh_desk.ssh.tunnel_runner <id>`
  detached (`start_new_session=True`); runner rebuilds argv, owns the ssh
  process, tracks status/pid/last_error in SQLite.
- `sftp_service` — Paramiko with the **same** host-key pipeline; password from
  keyring, key+passphrase, agent; recursive delete, direct server↔server streaming.
- `import_export_service` — `~/.ssh/config` parser (Host blocks, wildcards
  skipped), TOML export/backup/restore (secrets opt-in, dedupe on restore).

### ssh/
- `client.py` — pure argv/env builders: connect (`-t -t` interactive, `-T` exec),
  exec, test, `-W` proxy, tunnel. Strict options: `StrictHostKeyChecking=yes`,
  `HashKnownHosts`, dual `UserKnownHostsFile`, keep-alive, custom `-o`s.
- `hostkeys.py` — known_hosts parse/match (incl. `|1|` HMAC-SHA1 hashed entries),
  fingerprinting, `ssh-keyscan` fetch, add/remove with 0600.
- `askpass.py` — the security centerpiece: OpenSSH calls `ssh-desk-askpass`;
  the helper resolves the secret **by reference** from the keyring. No password
  ever appears in argv/environment/logs. Wrappers are regenerated for the active
  interpreter (venv/PyInstaller-safe).
- `tunnel_runner.py` — detached daemon described above.
- `process_manager.py` — pid registry + cleanup on exit.

### cli/
- `commands.py` — Typer app + `run()` dispatcher that rewrites `sss prod ...` →
  `connect prod ...`; per-command exit codes; completion provider.
- `shell_integration.py` — real OS integration: `~/.local/bin` symlinks
  (rename = remove old link, create new), bash/zsh completion files.

### gui/
- `main_window.py` — sidebar + stacked pages, shortcuts, busy overlay, status bar.
- `terminal_widget.py` — `pty.openpty()` + `subprocess` with `TIOCSCTTY`,
  non-blocking master fd read via `QSocketNotifier`, parsing through
  **pyte** (VT100/xterm incl. alternate screen → vim/nano work), custom
  `QPainter` grid renderer (16/256 colors, bold/reverse, cursor), mouse
  selection, bracket-less paste, `TIOCSWINSZ` resize.
- Pages are plain `QWidget`s refreshed on show; all blocking work runs in
  `GenericWorker` threads → the UI never freezes on SSH/SFTP activity.

## Data flow example — `sss prod nginx`

1. Dispatcher rewrites argv → `connect prod nginx`.
2. `require_by_alias("prod")` (case-insensitive; suggestions on miss).
3. `resolve_target` maps `nginx` → `/etc/nginx`.
4. Host-key check: known? unchanged? (else gate).
5. Password auth → askpass env with keyring *reference*.
6. `Popen(["ssh", "-t", "-t", ..., "root@host", "cd -- /etc/nginx && exec \"$SHELL\" -l"])`
   with no shell=True.
7. History row opened; on exit closed with status/duration; exit code forwarded.
