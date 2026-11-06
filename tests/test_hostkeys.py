"""Host key policy: known_hosts matching (plain + hashed), fingerprints, parse/round-trip."""

import base64
import hashlib
import hmac

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from ssh_desk.ssh import hostkeys


def make_ed25519_key() -> str:
    key = ed25519.Ed25519PrivateKey.generate()
    return key.public_key().public_bytes(
        serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH
    ).decode()


def test_fingerprint_format():
    pub = make_ed25519_key()
    blob = pub.split()[1]
    fp = hostkeys.fingerprint_from_blob(blob)
    assert fp.startswith("SHA256:")
    assert len(fp) == len("SHA256:") + 43
    # matches ssh-keygen computation (base64 of sha256 over the raw blob)
    digest = hashlib.sha256(base64.b64decode(blob)).digest()
    assert fp == "SHA256:" + base64.b64encode(digest).decode().rstrip("=")


def test_parse_and_match(tmp_path):
    pub = make_ed25519_key()
    key_file = tmp_path / "known_hosts"
    key_file.write_text(f"example.com {pub}\n")
    entries = hostkeys.lookup([key_file], "example.com", 22)
    assert len(entries) == 1
    assert entries[0].key_type == "ssh-ed25519"
    assert hostkeys.lookup([key_file], "other.com", 22) == []
    # non-standard port uses [host]:port form
    key_file.write_text(f"[example.com]:2222 {pub}\n")
    assert hostkeys.lookup([key_file], "example.com", 2222)
    assert not hostkeys.lookup([key_file], "example.com", 22)


def test_hashed_known_hosts(tmp_path):
    pub = make_ed25519_key()
    salt = b"\x01" * 20
    host = "secret.example.com"

    def hashed(name: str) -> str:
        return "|1|" + base64.b64encode(salt).decode() + "|" + base64.b64encode(
            hmac.new(salt, name.encode(), hashlib.sha1).digest()
        ).decode()

    key_file = tmp_path / "known_hosts"
    key_file.write_text(f"{hashed(host)} {pub}\n")
    assert hostkeys.lookup([key_file], host, 22)
    assert not hostkeys.lookup([key_file], "evil.example.com", 22)


def test_add_and_remove_entry(tmp_path):
    pub = make_ed25519_key()
    line = f"[1.2.3.4]:2200 {pub}"
    key_file = tmp_path / "known_hosts"
    entry = hostkeys.HostKeyEntry("[1.2.3.4]:2200", "ssh-ed25519", pub.split()[1],
                                  hostkeys.fingerprint_from_blob(pub.split()[1]), line)
    hostkeys.add_entry(key_file, entry)
    hostkeys.add_entry(key_file, entry)  # deduplicated
    assert len(key_file.read_text().splitlines()) == 1
    assert key_file.stat().st_mode & 0o777 == 0o600
    entries = hostkeys.lookup([key_file], "1.2.3.4", 2200)
    assert len(entries) == 1
    hostkeys.remove_entry(key_file, "1.2.3.4", 2200)
    assert key_file.read_text().strip() == ""


def test_fetch_host_keys_localhost_missing():
    # unreachable host -> empty result (no crash); no real server required
    try:
        entries = hostkeys.fetch_host_keys("127.0.0.1", 59999, timeout=1)
        assert isinstance(entries, list)
    except Exception:
        pytest.fail("fetch_host_keys should not raise for unreachable host")


def test_host_key_gates():
    from ssh_desk.core.exceptions import HostKeyUnknownError
    from ssh_desk.services.connection_service import NonInteractiveGate

    server = type("S", (), {"host": "h", "port": 22, "alias": "h"})()
    with pytest.raises(HostKeyUnknownError):
        NonInteractiveGate().on_unknown(server, [])
