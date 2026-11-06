# Troubleshooting

## "Secret Service is not available" / passwords cannot be saved

The Secret Service daemon is missing or not reachable.

```bash
sudo apt install gnome-keyring libsecret-1-0
# On GNOME/Wayland it starts automatically after re-login.
# Bare window managers:
eval $(gnome-keyring-daemon --start --components=secrets)
```

Check availability: Settings page → Keyring, or:

```bash
busctl --user list | grep -i secret
```

## Keyring is locked

Unlock it once:

```bash
secret-tool lookup ssh-desk.application ssh-desk   # triggers an unlock prompt
# or open "Passwords and Keys" (seahorse) and unlock "Default keyring"
```

SSH Desk will also prompt interactively where possible.

## `sss: command not found`

```bash
ls ~/.local/bin/sss         # symlink exists?
echo $PATH | tr ':' '\n' | grep .local/bin || \
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
sss install-cli             # recreate symlinks
```

## CLI rename left a stale command

```bash
sss install-cli --name newname
rm -f ~/.local/bin/<oldname>     # if you renamed manually
```

## Host key problems

**Unknown host** (first connect): verify the fingerprint against the server
admin, then accept (GUI dialog or `sss test prod --accept-host-key`).

**Host key CHANGED** (possible MITM):

```bash
# only if you verified the change is legitimate:
ssh-keygen -R "[host]:port"        # e.g. ssh-keygen -R '[1.2.3.4]:22'
sss test prod --accept-host-key
```

The app keyring file is `~/.local/share/ssh-desk/known_hosts`.

## Permission denied (publickey/password)

- Password auth: re-enter with `sss edit prod --set-password`.
- Key auth: does `sss info prod` show the right key? Is its passphrase stored?
  (`sss keys list`, register with `sss keys import`.)
- Test with the CLI for a readable error: `sss test prod`.

## GUI does not start

```bash
ssh-desk 2>&1 | tail -20
```

- Missing Qt system libs: `sudo apt install libegl1 libgl1 libxkbcommon0 libglib2.0-0 libfontconfig1`
- Wayland issues: try `QT_QPA_PLATFORM=xcb ssh-desk` (needs `libxcb`).
- Check the log: `~/.local/share/ssh-desk/logs/ssh-desk.log`.

## Tunnel does not start / "port already in use"

```bash
ss -tlnp | grep <port>       # who owns the port?
sss tunnel stop <name>
sss current                  # shows running tunnel daemons
```

Tunnel logs: `~/.local/share/ssh-desk/logs/tunnel-<id>.log`.

## SFTP fails but terminal works

- The server may disable the SFTP subsystem (`Subsystem sftp` in `sshd_config`).
- Host key must be accepted first (connect once via terminal or Test).

## Database locked / corrupt

SQLite with WAL is robust; still:

```bash
cp ~/.local/share/ssh-desk/ssh-desk.db ~/ssh-desk.backup
sqlite3 ~/.local/share/ssh-desk/ssh-desk.db "PRAGMA integrity_check;"
```

## Reset everything

```bash
sss uninstall-data           # asks to type PURGE; also purges keyring secrets
```

## Where things live

| What | Path |
| --- | --- |
| Database | `~/.local/share/ssh-desk/ssh-desk.db` |
| Settings | `~/.config/ssh-desk/config.toml` |
| App known_hosts | `~/.local/share/ssh-desk/known_hosts` |
| Generated keys | `~/.local/share/ssh-desk/keys/` |
| Logs | `~/.local/share/ssh-desk/logs/` |
| Secrets | GNOME Keyring (Secret Service) |
