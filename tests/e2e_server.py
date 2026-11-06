"""E2E helper: a REAL paramiko SSH server for password-authentication testing.

The product's engine (OpenSSH client) connects to this server, so the full
password flow is exercised for real: keyring -> credential service -> askpass
helper -> OpenSSH client -> SSH server. Only the server side is simulated,
which the spec explicitly allows for tests ("test SSH Server").
"""

import socket
import subprocess
import threading

import paramiko
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


def _generate_ed25519_host_key() -> paramiko.Ed25519Key:
    """Ed25519 host key: OpenSSH 10 clients reject RSA/SHA-1 host keys."""
    import tempfile
    from pathlib import Path

    raw = ed25519.Ed25519PrivateKey.generate()
    pem = raw.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.OpenSSH,
        serialization.NoEncryption(),
    )
    with tempfile.NamedTemporaryFile("wb", suffix=".pem", delete=False) as fh:
        fh.write(pem)
        path = fh.name
    try:
        return paramiko.Ed25519Key(filename=path)
    finally:
        Path(path).unlink(missing_ok=True)


class PasswordServerInterface(paramiko.ServerInterface):
    def __init__(self, password: str, attempts: list, allow_pubkey_fp: str | None = None):
        self._password = password
        self._allow_pubkey_fp = allow_pubkey_fp  # md5 hex, no colons
        self.attempts = attempts
        self._lock = threading.Lock()

    def get_allowed_auths(self, username) -> str:
        return "password,publickey"

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED

    def check_auth_password(self, username, password):
        with self._lock:
            self.attempts.append({"username": username, "password": password})
        return paramiko.AUTH_SUCCESSFUL if password == self._password else paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        if self._allow_pubkey_fp and key.get_fingerprint().hex() == self._allow_pubkey_fp:
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_channel_pty_request(self, *a, **k) -> bool:
        return True

    def check_channel_exec_request(self, channel, command) -> bool:
        threading.Thread(target=self._run_exec, args=(channel, command), daemon=True).start()
        return True

    def _run_exec(self, channel, command):
        try:
            proc = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=20
            )
            out = (proc.stdout + proc.stderr).encode("utf-8", "replace")
            if out:
                channel.sendall(out)
            channel.send_exit_status(proc.returncode)
        except Exception:
            try:
                channel.send_exit_status(127)
            except Exception:
                pass
        finally:
            try:
                channel.close()
            except Exception:
                pass


class PasswordSSHServer:
    """Threaded single-port SSH server accepting password auth, records attempts."""

    def __init__(self, host: str = "127.0.0.1", port: int = 2223):
        self.host, self.port = host, port
        self.attempts: list[dict] = []
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((host, port))
        self._sock.listen(16)
        self._sock.settimeout(0.5)
        self.host_key = _generate_ed25519_host_key()
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self):
        while self._running:
            try:
                client_sock, addr = self._sock.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            threading.Thread(target=self._handle, args=(client_sock,), daemon=True).start()

    def _handle(self, sock):
        transport = None
        try:
            transport = paramiko.Transport(sock)
            transport.add_server_key(self.host_key)
            transport.set_keepalive(15)
            iface = PasswordServerInterface(self._password, self.attempts)
            transport.start_server(server=iface)
            # hold the transport until the client closes
            deadline = __import__("time").monotonic() + 120
            while transport.is_active() and __import__("time").monotonic() < deadline:
                __import__("time").sleep(0.2)
        except Exception:
            pass
        finally:
            try:
                if transport:
                    transport.close()
                sock.close()
            except Exception:
                pass

    @property
    def _password(self) -> str:
        return "Str0ng-T3st-Pass!"

    def stop(self):
        self._running = False
        try:
            self._sock.close()
        except OSError:
            pass
