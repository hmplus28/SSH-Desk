"""Secure SSH_ASKPASS helper.

OpenSSH invokes this helper (with SSH_ASKPASS_REQUIRE=force) to obtain passwords
or key passphrases. The secret itself is NEVER passed via argv or environment:
the helper receives only a secret *reference* (attributes) and reads the secret
from the Secret Service (GNOME Keyring) itself.
"""

import json
import logging
import os
import stat
import sys
from pathlib import Path

log = logging.getLogger("ssh_desk.askpass")  # never logs secret material


def _get_store():
    from ssh_desk.services.credential_service import SecretServiceStore

    return SecretServiceStore()


def obtain_secret() -> str:
    ref_env = os.environ.get("SSH_DESK_SECRET_REF", "")
    if not ref_env:
        sys.stderr.write("ssh-desk-askpass: no secret reference provided\n")
        return ""
    try:
        ref = json.loads(ref_env)
        store = _get_store()
        secret = store.retrieve(ref)
        return secret or ""
    except Exception as exc:
        # Detailed reason goes to stderr only; ssh shows a generic auth failure.
        sys.stderr.write(f"ssh-desk-askpass: cannot retrieve secret ({type(exc).__name__})\n")
        log.debug("askpass retrieval failed: %s", exc)
        return ""


def run() -> int:
    """Console-script entry point used as SSH_ASKPASS."""
    try:
        secret = obtain_secret()
    except Exception:
        secret = ""
    if not secret:
        return 1
    sys.stdout.write(secret + "\n")
    sys.stdout.flush()
    return 0


def ensure_askpass_helper(data_dir: Path, cli_wrapper_name: str = "ssh-desk-cli") -> Path:
    """Write a tiny sh wrapper so SSH_ASKPASS can point to a single executable path.

    The wrapper re-execs the *current* interpreter, so it stays correct for venvs
    and PyInstaller bundles alike.
    """
    bin_dir = Path(data_dir) / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    helper = bin_dir / "ssh-desk-askpass"
    wrapper = bin_dir / cli_wrapper_name
    python = sys.executable
    script = (
        "#!/bin/sh\n"
        f'exec "{python}" -m ssh_desk.ssh.askpass "$@"\n'
    )
    cli_script = (
        "#!/bin/sh\n"
        f'exec "{python}" -m ssh_desk.cli.main "$@"\n'
    )
    changed = False
    for path, content in ((helper, script), (wrapper, cli_script)):
        try:
            if not path.exists() or path.read_text() != content:
                path.write_text(content)
                changed = True
            path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except OSError:
            pass
    if changed:
        log.debug("askpass/cli helpers written to %s", bin_dir)
    return helper
