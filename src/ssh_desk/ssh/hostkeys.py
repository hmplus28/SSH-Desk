"""Host key management: known_hosts parsing (plain + hashed), fingerprints, ssh-keyscan."""

import base64
import hashlib
import hmac
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ssh_desk.core.exceptions import SSHConnectionError

log = logging.getLogger("ssh_desk.hostkeys")

_KEY_ORDER = {"ssh-ed25519": 0, "ecdsa-sha2-nistp256": 1, "ecdsa-sha2-nistp384": 2, "ecdsa-sha2-nistp521": 3, "ssh-rsa": 4}


@dataclass
class HostKeyEntry:
    host_field: str
    key_type: str
    blob_b64: str
    fingerprint: str
    line: str


def fingerprint_from_blob(blob_b64: str) -> str:
    """SHA256 base64 fingerprint (same format as `ssh-keygen -lf`)."""
    try:
        digest = hashlib.sha256(base64.b64decode(blob_b64)).digest()
        return "SHA256:" + base64.b64encode(digest).decode().rstrip("=")
    except Exception as exc:
        raise SSHConnectionError(f"Cannot fingerprint host key: {exc}") from exc


def parse_line(line: str):
    """Parse a known_hosts line -> (host_field, key_type, blob_b64) or None."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    parts = line.split()
    if len(parts) < 3:
        return None
    host_field, key_type, blob = parts[0], parts[1], parts[2]
    if host_field.startswith("@"):
        return None  # @revoked / @cert-authority markers are skipped
    try:
        base64.b64decode(blob, validate=True)
    except Exception:
        return None
    return host_field, key_type, blob


def _host_candidates(host: str, port: int) -> list[str]:
    if port == 22:
        return [host]
    return [f"[{host}]:{port}"]


def _match_host_field(host_field: str, candidates: list[str]) -> bool:
    if host_field.startswith("|1|"):
        try:
            _, _, salt_b64, hash_b64 = host_field.split("|", 3)
            salt = base64.b64decode(salt_b64)
            expected = base64.b64decode(hash_b64)
        except Exception:
            return False
        return any(
            hmac.new(salt, cand.encode(), hashlib.sha1).digest() == expected for cand in candidates
        )
    for pattern in host_field.split(","):
        if pattern in candidates:
            return True
    return False


def lookup(paths, host: str, port: int) -> list[HostKeyEntry]:
    """Return matching entries from the given known_hosts files."""
    candidates = _host_candidates(host, port)
    found = []
    for path in paths:
        path = Path(path).expanduser()
        if not path.exists():
            continue
        try:
            lines = path.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            parsed = parse_line(line)
            if not parsed:
                continue
            host_field, key_type, blob = parsed
            if _match_host_field(host_field, candidates):
                found.append(
                    HostKeyEntry(host_field, key_type, blob, fingerprint_from_blob(blob), line)
                )
    return found


def fetch_host_keys(host: str, port: int, timeout: int = 6) -> list[HostKeyEntry]:
    """Fetch the server's public host keys with ssh-keyscan (no trust implied)."""
    cmd = ["ssh-keyscan", "-T", str(timeout), "-t", "rsa,ecdsa,ed25519", "-p", str(port), host]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 4)
    except FileNotFoundError as exc:
        raise SSHConnectionError("OpenSSH (ssh-keyscan) is not installed") from exc
    except subprocess.TimeoutExpired:
        return []
    if proc.returncode != 0 and not proc.stdout.strip():
        return []
    entries = []
    for line in proc.stdout.splitlines():
        parsed = parse_line(line)
        if not parsed:
            continue
        host_field, key_type, blob = parsed
        entries.append(HostKeyEntry(host_field, key_type, blob, fingerprint_from_blob(blob), line))
    entries.sort(key=lambda e: _KEY_ORDER.get(e.key_type, 9))
    return entries


def add_entry(file_path: Path, entry: HostKeyEntry) -> None:
    """Append a host key line to the app known_hosts file (deduplicated)."""
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    existing = set()
    if file_path.exists():
        existing = {l.strip() for l in file_path.read_text(errors="replace").splitlines()}
    if entry.line.strip() not in existing:
        with open(file_path, "a", encoding="utf-8") as fh:
            fh.write(entry.line.strip() + "\n")
    _chmod_600(file_path)


def remove_entry(file_path: Path, host: str, port: int) -> None:
    """Remove matching entries (pure python, handles hashed entries)."""
    file_path = Path(file_path)
    if not file_path.exists():
        return
    candidates = _host_candidates(host, port)
    kept = []
    for line in file_path.read_text(errors="replace").splitlines():
        parsed = parse_line(line)
        if parsed and _match_host_field(parsed[0], candidates):
            continue
        kept.append(line)
    file_path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    _chmod_600(file_path)


def _chmod_600(path: Path) -> None:
    try:
        path.chmod(0o600)
    except OSError:
        pass


def best_fingerprint(entries: list[HostKeyEntry]) -> str:
    if not entries:
        return ""
    return entries[0].fingerprint
