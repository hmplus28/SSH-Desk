# SSH Desk

<div align="center">

**Professional SSH connection manager for Ubuntu — Desktop GUI + CLI, one shared engine.**

`sss prod` · `sss prod nginx` · `sss prod --exec "uptime"`

[English](README.md) · [فارسی](README.fa.md) · [العربية](README.ar.md) · [简体中文](README.zh.md) · [Русский](README.ru.md) · [Español](README.es.md) · [Français](README.fr.md)

</div>

<p dir="rtl" align="right"><b>به فارسی:</b> SSH Desk یک مدیر اتصال SSH واقعی برای اوبونتو است — رمزها فقط در GNOME Keyring، ترمینال PTY واقعی، CLI بدون نیاز به GUI، و نصب آفلاین با میرورها برای اینترنت ناپایدار. راهنمای کامل: <a href="docs/SSH-Desk-User-Guide-fa.pdf">راهنمای کاربر (PDF فارسی)</a> · <a href="README.fa.md">README فارسی</a></p>

SSH Desk is a real, installable product (not a prototype) for managing all of your
SSH servers: passwords are stored **only** in the GNOME Keyring (Secret Service),
the SSH engine is the **system OpenSSH**, and the built-in terminal is a **real PTY**
(vim/nano, colors, Ctrl+C, resize — everything works).

- 🖥️ **Desktop GUI** (PySide6): dark/light themes, 7 UI languages (full RTL for Persian & Arabic), real terminal tabs, SFTP file manager, tunnels, keys, history
- ⌨️ **CLI** (Typer): works **without** the GUI, configurable command name (`sss`, `cnc`, `sshgo`, …), bash/zsh completion with alias completion
- 🔐 **Security-first**: strict host key checking with fingerprint dialogs, secrets never in DB/logs/argv, no `sshpass`, no `StrictHostKeyChecking=no`
- 🌐 **Network-outage-proof**: PyPI mirror fallback chain (official → ArvanCloud IR → TUNA → Aliyun → Tencent) + fully offline install (`install.sh --offline`)

📄 **User guides — 14-page illustrated PDFs in 7 languages:** [English](docs/SSH-Desk-User-Guide-en.pdf) · [فارسی](docs/SSH-Desk-User-Guide-fa.pdf) · [العربية](docs/SSH-Desk-User-Guide-ar.pdf) · [简体中文](docs/SSH-Desk-User-Guide-zh.pdf) · [Русский](docs/SSH-Desk-User-Guide-ru.pdf) · [Español](docs/SSH-Desk-User-Guide-es.pdf) · [Français](docs/SSH-Desk-User-Guide-fr.pdf) — install (incl. offline/mirror flow), full CLI reference, terminal, SFTP, tunnels, security model.

---

## Quick start

```bash
git clone https://github.com/hmplus28/SSH-Desk.git
cd SSH-Desk
bash scripts/install.sh
```

Then:

```bash
ssh-desk          # GUI
sss add           # add your first server
sss prod          # connect (interactive shell in your terminal)
```

See [docs/INSTALLATION.md](docs/INSTALLATION.md) for the DEB package and manual setup.

## The CLI in 30 seconds

```bash
sss                      # summary + hints
sss list                 # table of servers
sss add                  # interactive wizard (or use --alias/--host/...)
sss info prod            # full details
sss test prod            # connectivity test
sss prod                 # interactive shell at the default path
sss prod nginx           # connect to a saved path
sss prod /etc/nginx      # connect to an absolute path
sss prod --exec "uptime" # run a command (overrides nothing)
sss prod --user ubuntu --port 2222   # per-run override (not saved)
sss history              # connection history
sss current              # active sessions + running tunnels
sss tunnel db            # start a named tunnel (survives the terminal)
sss config cli-name cnc  # rename the terminal command system-wide
sss --help               # full reference
```

## Features

| Area | What works |
| --- | --- |
| Servers | CRUD, unique aliases, groups, tags, favorites, duplicate, search/sort/filter |
| Auth | Password (Keyring), private key (+passphrase in Keyring), SSH agent, interactive |
| Paths | Default path + named saved paths (`sss prod nginx`), safe quoting |
| Terminal | Real PTY (OpenSSH), multi-tab, colors, vim/nano, resize, copy/paste |
| Files | SFTP two-pane manager: upload/download/mkdir/rename/chmod/edit/delete, server↔server transfer |
| Keys | Generate (Ed25519/RSA/ECDSA in OpenSSH format), import, fingerprint, export pub, `ssh-copy-id` guide |
| Tunnels | Local / Remote / Dynamic SOCKS, start/stop, detached daemon, status tracking |
| Jump hosts | `ProxyCommand` via `ssh -W` through any registered server (nested chains supported) |
| Commands | Saved commands per server or global, confirmation for dangerous ones |
| History | Connect/disconnect, duration, status, errors (no terminal content, no passwords) |
| Import/Export | `~/.ssh/config` import with preview+dedupe, TOML backup/restore (secrets opt-in) |
| Install resilience | PyPI mirror fallback chain + offline wheelhouse install (`download_wheels.sh` → `install.sh --offline`) |

## Security model (short version)

1. Passwords/passphrases live **only** in the Secret Service (GNOME Keyring). The DB stores a non-secret reference.
2. OpenSSH gets secrets through a hardened **askpass helper** — never argv, never environment, never `sshpass`.
3. Host keys are enforced (`StrictHostKeyChecking=yes`): unknown → fingerprint dialog; changed → hard warning.
4. Database/config files are `0600`/`0700`; logs are redacted; no root daemons.

Full details: [docs/SECURITY.md](docs/SECURITY.md).

## Development

```bash
pip install -e .[dev]
pytest          # 65 tests
ruff check .    # clean
```

Architecture and internals: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) ·
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) · [docs/USER_GUIDE.md](docs/USER_GUIDE.md) ·
[User guide PDFs ×7](docs/SSH-Desk-User-Guide-en.pdf)

## Requirements

- Ubuntu 22.04 / 24.04+ (or any Debian-based distro)
- Python 3.10+ (3.12 recommended), `openssh-client`
- GNOME Keyring (`sudo apt install gnome-keyring`) for stored passwords

## FAQ

**What is SSH Desk?**
SSH Desk is an open-source SSH connection manager for Ubuntu (and any Debian-based distro). It combines a desktop GUI (PySide6) with a terminal-first CLI (`sss`) on one shared SQLite database and GNOME Keyring — a free, self-hosted alternative to tools like Termius, Remmina's SSH plugin or PuTTY on Linux.

**How are passwords stored?**
Only in the GNOME Keyring (Secret Service). The SQLite database holds a secret-less reference; the password never touches the database, logs, command arguments or environment variables. OpenSSH receives secrets through a secure askpass helper — `sshpass` is never used.

**Does it replace OpenSSH?**
No — it drives your **system's** OpenSSH. The terminal is a real PTY (vim, nano, htop, colors, Ctrl+C, resize all work), and host keys are checked with `StrictHostKeyChecking=yes`; turning that off is not possible.

**Can the GUI and CLI be used at the same time?**
Yes, and they always agree: one database, one keyring, one settings file. A server added in the GUI is immediately connectable via `sss prod nginx` from any terminal — and vice versa.

**Does it work without internet?**
Yes. Every pip call in the install scripts walks a mirror chain (official PyPI → ArvanCloud → TUNA → Aliyun → Tencent) and skips unreachable mirrors. You can pre-download everything with `scripts/download_wheels.sh` and install later with `install.sh --offline` using no network at all.

**Is it available in my language?**
The UI and CLI ship in 7 languages — English, Persian, Arabic (full RTL), Chinese, Russian, Spanish and French — selectable in Settings; the illustrated user guide is a separate PDF per language under `docs/`.

**How can I script it?**
The CLI has deterministic exit codes (0 success, 1 runtime error, 2 usage error, 130 Ctrl+C), `--dry-run` to print the exact ssh command, and `--exec` to run a single command — safe for cron, CI and Ansible-style automation.

**How do I migrate from my existing `~/.ssh/config`?**
Run `sss import --file ~/.ssh/config` — it previews every Host entry, detects duplicates, and imports aliases, users, ports, identity files and ProxyJump rules after you confirm.

---

## License

MIT — see [LICENSE](LICENSE).
