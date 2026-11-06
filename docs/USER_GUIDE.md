# User Guide

A practical, step-by-step guide for daily use. UI text is available in
English and Persian (Settings → Language); screenshots positions refer to
the English UI.

## 1. First launch

```bash
ssh-desk
```

The window has a collapsible sidebar (Dashboard, Servers, Terminal, Files,
SSH Keys, Port Forwarding, Commands, History, Settings) and a status bar
showing active sessions and tunnels. Keyboard: `Ctrl+1..9` switch pages,
`Ctrl+N` new server, `Ctrl+K` new terminal session, `Ctrl+Q` quit.

## 2. Adding a server

Servers → **Add server** (or `sss add` in a terminal).

- **General**: Name, Alias (unique, used as `sss <alias>`), Host (IP or domain),
  Port, Username, Group, Tags, Description.
- **Authentication**:
  - *Password*: stored in GNOME Keyring (never in the database).
  - *SSH private key*: pick a registered key or browse to a file.
  - *SSH agent*: use your running `ssh-agent`.
  - *Interactive*: type the password at each connect.
- **Connection**: Default path, timeout, keep-alive, compression, agent forwarding,
  and **saved paths** (e.g. `website → /var/www/html`, `nginx → /etc/nginx`).
- **Advanced**: Jump host (bastion), preferred auth methods, custom `ssh -o` options.

Use **Test** before saving — it performs a real connection attempt
(including host-key acceptance).

## 3. Connecting

- GUI: double-click a server (Details) or press **Connect**; a real terminal
  tab opens (interactive shell at the default path).
- CLI: `sss prod`, `sss prod nginx` (saved path), `sss prod /var/www` (absolute
  path), `sss prod --exec "uptime"` (run command), `sss prod --user ubuntu --port 2222`
  (per-run overrides, never saved).

The first connection to a new host shows its **fingerprint**; verify it and accept
once. If a host key **changes**, SSH Desk refuses and explains how to handle it.

## 4. The terminal

Each tab is a real PTY session:

- Colors, arrow keys, `Ctrl+C`, `Ctrl+D`, `Tab` completion, `vim`, `nano`, `htop` all work.
- Copy: select with the mouse (auto-copies) or `Ctrl+Shift+C`-style via toolbar.
- Paste: middle-click, toolbar, or `Ctrl+V` inside the terminal.
- Resize: drag the window — the remote program is notified (SIGWINCH).
- Tab title shows the server and the remote window title; reconnect by opening a
  new session with the same server.

## 5. Files (SFTP)

Select a server → **Connect**. Two panes: local (left) and remote (right).

- Navigate: double-click folders, `↑` parent, edit the path directly.
- Upload/download, new folder, rename, delete (with confirmation, recursive),
  change permissions (octal), edit text files locally (auto re-upload prompt).
- **Send to server...** streams a file directly between two registered servers.

## 6. SSH keys

- **Generate**: Ed25519 (recommended), RSA, ECDSA — written in OpenSSH format;
  optional passphrase stored in the keyring.
- **Import**: register an existing private key (reference it, or copy into
  `~/.local/share/ssh-desk/keys/` with `0600` — your explicit choice).
- **Export public key** to a file, or use **Install on server** which builds the
  `ssh-copy-id` command and can run it in a terminal session.
- The fingerprint column helps you verify keys; "Linked servers" shows which
  servers use a key.

## 7. Port forwarding

Create a tunnel (name, server, type, binding):

- **Local** `127.0.0.1:5432 → db-internal:5432`
- **Remote** (reverse) `0.0.0.0:8080 → localhost:80`
- **Dynamic** SOCKS5 proxy on `127.0.0.1:1080`

Press **Start** — the tunnel runs in a detached daemon, so it survives the GUI
closing. CLI: `sss tunnel list|start|stop`, `sss current` shows live tunnels.

## 8. Saved commands

Define commands per server or globally (name, command, category,
"requires confirmation"). Run them from the Commands page (opens a terminal
session) or with `sss prod --exec "<command>"`. Commands flagged as sensitive
always ask first.

## 9. History

Every connection records server, start/end time, duration, status
(`closed`/`failed`/`interrupted`) and a short sanitized error. Terminal contents
and passwords are never recorded. Clear everything with one confirmed click.

## 10. Settings that matter

- **Terminal command name**: change `sss` to `cnc`, `sshgo`, ... — the rename is
  applied to the OS (symlink in `~/.local/bin`).
- Theme (dark/light) and Language (English/فارسی, RTL-aware).
- Default port / timeout / keep-alive for new servers.
- Keyring status with install hints when the Secret Service is missing.
- **Backup / Restore** (TOML; passwords excluded unless you opt in),
  **Import ~/.ssh/config** (preview + duplicate detection).

## 11. GUI ↔ CLI sharing

Both interfaces use the same database, keyring and settings: add a server in the
GUI and `sss prod` works immediately in any terminal (no GUI running needed),
and vice versa.
