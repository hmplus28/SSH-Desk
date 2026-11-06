# CLI Reference

Command name: `sss` (configurable — see `sss config cli-name`).
Alias shortcut: any first token that is not a known subcommand is treated as a
server alias, so `sss prod` == `sss connect prod`.

Exit codes: `0` success · `1` runtime error · `2` invalid input/usage · `130` interrupted.

## General

```
sss                          Summary: servers, quick hints
sss --help                   Full help
sss version                  App/Python/OpenSSH versions
```

## Servers

```
sss list [--group NAME] [--favorites] [--search TEXT]
sss add [--alias A --host H --user U --port P --auth password|key|agent|interactive
         --key PATH --group G --path /default --description "..."; --tags "a,b"]
                             Interactive for anything not provided
sss info ALIAS [--show-secret]     Full details (--show-secret asks to type the alias)
sss edit ALIAS [--name --host --user --port --auth --key --group --path --description --tags]
                                   No options -> interactive field editor
sss edit ALIAS --set-password      Re-enter the keyring password
sss delete ALIAS [--yes]           Confirmation; removes the keyring secret too
sss search TERM                    Name/alias/host/user/description search
```

## Connecting

```
sss ALIAS [TARGET] [options]

TARGET   saved path name (sss prod nginx) or absolute path (sss prod /etc/nginx)
         omitted -> the server's default path

--exec "CMD"       Run CMD instead of a shell (non-interactive)
--user USER        Override username (not saved)
--port PORT        Override port (not saved)
--accept-host-key  Accept + store an unknown host key (verify the fingerprint!)
--dry-run          Print the exact ssh command line and exit
```

Examples:

```
sss prod
sss prod logs
sss prod --exec "tail -n 50 /var/log/syslog"
sss prod --user deploy --port 2200
```

## Monitoring

```
sss history [--server ALIAS] [--limit N] [--status connected|closed|failed|interrupted]
sss current                 Active SSH sessions (env-marked) + running tunnels
```

## Configuration

```
sss config list                     All settings + file locations
sss config get KEY
sss config set KEY VALUE
sss config cli-name NAME            Rename the terminal command (OS-level symlink)
sss config completions [--shell bash|zsh] [--install]
```

## Tunnels

```
sss tunnel list
sss tunnel start NAME        Detached daemon; keeps running after the CLI exits
sss tunnel stop NAME
```

(Tunnels are created in the GUI: Port Forwarding → New tunnel.)

## Keys

```
sss keys list
sss keys generate --name NAME [--type ed25519|rsa|ecdsa] [--bits 4096] [--comment C] [--passphrase]
sss keys import --path FILE --name NAME [--copy]
sss keys export-pub NAME
sss keys delete NAME [--remove-files] [--yes]
```

## Import / Export / Backup

```
sss import [--file ~/.ssh/config] [--apply] [--all]     Preview by default
sss export FILE.toml [--include-secrets] [--include-history]
sss backup FILE.toml [--include-secrets]
sss restore FILE.toml [--no-secrets]
```

`--include-secrets` is opt-in and warns — exported passwords are plaintext.

## System

```
sss install-cli [--name CMD]       (Re)create ~/.local/bin/<cmd> symlinks
sss uninstall-data [--yes] [--keep-secrets]   Purge data + keyring secrets
```

## Completion

Bash (auto-installed by `scripts/install.sh`): completes subcommands and aliases.
Zsh: `sss config completions --shell zsh --install` then add
`fpath=(~/.local/share/ssh-desk/completions $fpath); autoload -Uz compinit && compinit`
to `~/.zshrc`.

The completion engine calls the hidden command `sss __complete <word> "<line>"`.
