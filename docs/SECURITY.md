# Security

This document maps SSH Desk's security requirements to their implementations.

## Threat model

A desktop tool storing credentials for production servers. Main risks: secret
leakage (disk/logs/process listing/CLI), MITM via host keys, command injection
through untrusted inputs, permission mistakes.

## Controls

### 1. Secrets live only in the Secret Service
- Passwords and key passphrases are written **only** to GNOME Keyring via
  SecretStorage (`services/credential_service.py`).
- SQLite stores a non-secret JSON *reference* (attribute set), never the secret
  (verified by `test_secret_never_in_db_file`).

### 2. No plaintext copies
- Export/backup excludes secrets by default; inclusion is opt-in and warns.
- Key files are referenced, not copied, unless the user explicitly opts in
  ("copy into SSH Desk storage"), then `0600`.

### 3. OpenSSH receives secrets through an askpass helper
- `ssh` is started with `SSH_ASKPASS=ssh-desk-askpass`,
  `SSH_ASKPASS_REQUIRE=force`.
- The helper resolves the secret **by reference** from the keyring
  (`src/ssh_desk/ssh/askpass.py`).
- Forbidden approaches are absent: no `sshpass`, no password in argv, no
  password in environment, no password in logs.

### 4. Host key checking is always on
- `StrictHostKeyChecking=yes` is hardcoded in the argv builder; `=no` is
  impossible to configure.
- Unknown host → fingerprint dialog / CLI prompt (`CliHostKeyGate`); in
  non-interactive contexts → hard error with instructions.
- Changed host key → refusal with a MITM warning (`HostKeyChangedError`);
  removal instructions use `ssh-keygen -R`.
- Paramiko (SFTP) uses the same pre-check pipeline plus `RejectPolicy`.

### 5. Injection resistance
- All subprocess calls use **argv lists**; `shell=True` is never used with user
  data.
- Remote paths are quoted with `shlex.quote` before composing remote commands.
- Every user input passes Pydantic validation (`utils/validation.py`): alias
  charset, port 1–65535, hostname/IP syntax, absolute paths, tunnel fields.

### 6. File permissions
- Database `0600`, config `0600`, app known_hosts `0600`, data dirs `0700`,
  generated private keys `0600`, public keys `0644`.

### 7. Logging hygiene
- `utils/logging_setup.py` redacts `password=`, `secret=`, `passphrase=` patterns
  and registered runtime secrets; session/terminal content is never recorded;
  history stores only status/duration/sanitized error (≤500 chars).

### 8. Sensitive operations need confirmation
- Delete server (mentions secret removal), delete files (recursive),
  run dangerous commands (`requires_confirmation`), reveal/copy password
  (type-the-alias challenge), uninstall-data (type `PURGE`), key deletion.

### 9. Clipboard hygiene
- Revealed password clipboard can auto-clear after a configurable delay
  (default 30 s).

### 10. No root services
- No daemons run as root. The tunnel runner is a user-session process started
  detached; the GUI/CLI never require sudo.

### 11. Key generation without argv secrets
- Keys are generated with `cryptography` and serialized to OpenSSH format
  in-process; even the optional passphrase never touches an argv or temp file.

### 12. Process visibility
- Interactive sessions mark their env (`SSH_DESK_SESSION`) only — that value is
  an opaque id, not a credential — enabling `sss current`.

## Known limitations

- `ssh-keyscan` fingerprint fetch happens over the network **before** trust is
  established (TOFU model). It never silently trusts; the user compares the
  fingerprint out-of-band for real security.
- A user-level attacker with access to the unlocked keyring can read secrets —
  the same is true of any Secret Service consumer.
- TOML export with `--include-secrets` is intentionally dangerous (opt-in).

## Reporting

Please open a GitHub issue for anything you find: github.com/hmplus28/SSH-Desk
