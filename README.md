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

- 🖥️ **Desktop GUI** (PySide6): dark/light themes, Persian/English (full RTL), real terminal tabs, SFTP file manager, tunnels, keys, history
- ⌨️ **CLI** (Typer): works **without** the GUI, configurable command name (`sss`, `cnc`, `sshgo`, …), bash/zsh completion with alias completion
- 🔐 **Security-first**: strict host key checking with fingerprint dialogs, secrets never in DB/logs/argv, no `sshpass`, no `StrictHostKeyChecking=no`
- 🌐 **Network-outage-proof**: PyPI mirror fallback chain (official → ArvanCloud IR → TUNA → Aliyun → Tencent) + fully offline install (`install.sh --offline`)

📄 **Persian user guide (14-page illustrated PDF): [docs/SSH-Desk-User-Guide-fa.pdf](docs/SSH-Desk-User-Guide-fa.pdf)** — install (incl. offline/mirror flow), full CLI reference, terminal, SFTP, tunnels, security model.

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
pytest          # 54 tests
ruff check .    # clean
```

Architecture and internals: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) ·
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) · [docs/USER_GUIDE.md](docs/USER_GUIDE.md) ·
[Guide PDF (fa)](docs/SSH-Desk-User-Guide-fa.pdf)

## Requirements

- Ubuntu 22.04 / 24.04+ (or any Debian-based distro)
- Python 3.10+ (3.12 recommended), `openssh-client`
- GNOME Keyring (`sudo apt install gnome-keyring`) for stored passwords

## License

MIT — see [LICENSE](LICENSE).
