# Installation

SSH Desk supports two installation paths on Ubuntu. Both are **user-level by default**
(no permanent root processes, no services).

## Prerequisites

```bash
sudo apt update
sudo apt install -y openssh-client gnome-keyring libsecret-1-0 python3 python3-venv python3-pip
```

| Requirement | Why |
| --- | --- |
| `openssh-client` | The SSH engine (`ssh`, `ssh-keyscan`, `ssh-copy-id`) |
| `gnome-keyring` + `libsecret-1-0` | Secure password storage (Secret Service) |
| Python 3.10+ | Runtime (3.12 recommended) |

## Option A — user install (recommended, no sudo for the app itself)

```bash
git clone https://github.com/hmplus28/SSH-Desk.git
cd SSH-Desk
bash scripts/install.sh
```

The script:

1. Checks Python 3.10+ and OpenSSH.
2. Creates a virtual environment at `~/.local/share/ssh-desk/venv`.
3. Installs SSH Desk and dependencies.
4. Creates symlinks in `~/.local/bin`: `ssh-desk` (GUI), `ssh-desk-cli`, `ssh-desk-askpass`, and the terminal command (`sss` by default).
5. Installs bash completion and (if available) the desktop entry + icon.

Verify:

```bash
ssh-desk --help 2>/dev/null || true   # GUI binary exists
sss --help                            # CLI works
```

If `sss` is not found, add `~/.local/bin` to your PATH:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## Option B — DEB package (system-wide)

Build the package (requires `dpkg-deb`, ships a self-contained PyInstaller bundle):

```bash
bash scripts/package_deb.sh
sudo apt install ./dist/ssh-desk_1.0.0_amd64.deb
```

or:

```bash
sudo dpkg -i dist/ssh-desk_1.0.0_amd64.deb
sudo apt-get install -f   # pulls openssh-client if missing
```

What the DEB installs:

```
/opt/ssh-desk/                       PyInstaller bundle
/usr/bin/ssh-desk|ssh-desk-cli|...   symlinks
/usr/share/applications/ssh-desk.desktop
/usr/share/icons/hicolor/scalable/apps/ssh-desk.svg
```

## First run

1. Launch the GUI (`ssh-desk`) or stay in the terminal (`sss add`).
2. Add a server. If you choose password auth, the password is stored in GNOME Keyring.
   If the keyring is locked you will be prompted to unlock it.
3. The database is created automatically on first run at
   `~/.local/share/ssh-desk/ssh-desk.db`.

## Enabling the CLI command

After `sss add`, connect from any terminal:

```bash
sss myserver
```

To use a different command name (applies to the OS for real):

```bash
sss config cli-name cnc     # now: cnc myserver
```

Zsh users should also run once:

```bash
sss config completions --shell zsh --install
# then add to ~/.zshrc:
#   fpath=(~/.local/share/ssh-desk/completions $fpath)
#   autoload -Uz compinit && compinit
```

## Weak or interrupted network: mirrors and offline install

Every pip call made by the scripts walks a **mirror fallback chain** — if one
mirror is unreachable it is skipped automatically and the next one is tried
(`pypi.org` → ArvanCloud (IR) → TUNA → Aliyun → Tencent). Nothing to configure
for this; it just works when some mirrors are down.

Force one mirror when you know which one works on your network:

```bash
bash scripts/install.sh --mirror-name ir        # ArvanCloud (Iran)
bash scripts/install.sh --mirror-name tuna      # TUNA (China)
bash scripts/install.sh --mirror https://pypi.org/simple
# or by env: SSH_DESK_PIP_INDEX_URL=... bash scripts/install.sh
```

### Fully offline install (two machines, or before an outage)

1. On a machine **with** internet (same Python major version and architecture),
   pre-download every wheel — through any mirror you like:

   ```bash
   bash scripts/download_wheels.sh --mirror-name ir
   ```

2. Move/copy the repo folder (it now contains `vendor/wheels/`) to the target
   machine and install with **no network at all**:

   ```bash
   bash scripts/install.sh --offline
   ```

`pip` will refuse to touch the network in `--offline` mode
(`--no-index --find-links vendor/wheels`), so a broken connection cannot break
the install halfway. Custom location: `--wheelhouse /path/to/wheels` or
`SSH_DESK_WHEELHOUSE=...`.

`scripts/build.sh` (PyInstaller bundle) uses the same fallback chain, so DEB
packaging also survives failing mirrors.

## Upgrade

```bash
cd SSH-Desk
git pull
bash scripts/install.sh      # same path, replaces the venv contents
```

DEB: build and install the newer package with `dpkg -i` (upgrades in place).
Your data and secrets are untouched by upgrades.

## Uninstall

```bash
bash scripts/uninstall.sh
```

The uninstaller asks explicitly before deleting user data
(`~/.config/ssh-desk`, `~/.local/share/ssh-desk`) and before purging keyring
secrets. Without confirmation your data and passwords are kept.

DEB removal:

```bash
sudo apt remove ssh-desk
# user data/secrets are kept; purge manually with: ssh-desk-cli uninstall-data
```

## Troubleshooting install

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
