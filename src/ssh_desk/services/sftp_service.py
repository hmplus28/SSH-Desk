"""SFTP file management built on Paramiko, aligned with the app's host-key policy.

Host keys: pre-checked with the same policy as OpenSSH (unknown -> gate, changed -> error).
Auth: password (from keyring), private key (with optional passphrase from keyring) or agent.
"""

import logging
import os
import stat as statmod
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from ssh_desk.core.exceptions import AuthError, HostKeyChangedError, HostKeyUnknownError, SftpError

log = logging.getLogger("ssh_desk.sftp")


@dataclass
class FileEntry:
    name: str
    longname: str
    size: int
    mtime: int
    is_dir: bool
    is_link: bool
    permissions: str


def _format_permissions(mode: int) -> str:
    import stat

    return stat.filemode(mode)


class SftpSession:
    def __init__(self, client, sftp, server):
        self.client = client
        self.sftp = sftp
        self.server = server

    # ------------------------------------------------------------------ ops
    def list_dir(self, path: str) -> list[FileEntry]:
        try:
            entries = self.sftp.listdir_attr(path)
        except FileNotFoundError as exc:
            raise SftpError(f"Remote path not found: {path}") from exc
        except PermissionError as exc:
            raise SftpError(f"Permission denied: {path}") from exc
        out = []
        for attr in entries:
            mode = attr.st_mode or 0
            out.append(
                FileEntry(
                    name=attr.filename,
                    longname=attr.longname or "",
                    size=attr.st_size or 0,
                    mtime=attr.st_mtime or 0,
                    is_dir=statmod.S_ISDIR(mode),
                    is_link=statmod.S_ISLNK(mode),
                    permissions=_format_permissions(mode) if mode else "---------",
                )
            )
        out.sort(key=lambda e: (not e.is_dir, e.name.lower()))
        return out

    def exists(self, path: str) -> bool:
        try:
            self.sftp.stat(path)
            return True
        except FileNotFoundError:
            return False

    def mkdir(self, path: str) -> None:
        try:
            self.sftp.mkdir(path)
        except OSError as exc:
            raise SftpError(f"Cannot create directory {path}: {exc}") from exc

    def remove_file(self, path: str) -> None:
        try:
            self.sftp.remove(path)
        except OSError as exc:
            raise SftpError(f"Cannot remove {path}: {exc}") from exc

    def remove_tree(self, path: str, progress: Optional[Callable[[str], None]] = None) -> None:
        entries = self.list_dir(path)
        for entry in entries:
            full = f"{path.rstrip('/')}/{entry.name}"
            if progress:
                progress(full)
            if entry.is_dir and not entry.is_link:
                self.remove_tree(full, progress)
            else:
                self.remove_file(full)
        self.sftp.rmdir(path)

    def rename(self, old: str, new: str) -> None:
        try:
            self.sftp.rename(old, new)
        except OSError as exc:
            raise SftpError(f"Cannot rename {old}: {exc}") from exc

    def chmod(self, path: str, mode: int) -> None:
        try:
            self.sftp.chmod(path, mode)
        except OSError as exc:
            raise SftpError(f"Cannot chmod {path}: {exc}") from exc

    def download(self, remote: str, local: str, progress: Optional[Callable[[int, int], None]] = None) -> str:
        size = self.sftp.stat(remote).st_size
        self.sftp.get(remote, local, callback=lambda done, _total: progress(done, size) if progress else None)
        return local

    def upload(self, local: str, remote: str, progress: Optional[Callable[[int, int], None]] = None) -> str:
        size = os.path.getsize(local)
        self.sftp.put(local, remote, callback=lambda done, _total: progress(done, size) if progress else None)
        return remote

    def read_text(self, remote: str, max_bytes: int = 8 * 1024 * 1024) -> str:
        with self.sftp.open(remote, "r") as fh:
            data = fh.read(max_bytes)
        return data.decode("utf-8", errors="replace") if isinstance(data, bytes) else str(data)

    def write_text(self, remote: str, text: str) -> None:
        with self.sftp.open(remote, "w") as fh:
            fh.write(text.encode("utf-8"))

    def close(self) -> None:
        for resource in (self.sftp, self.client):
            try:
                resource.close()
            except Exception:
                pass


class SftpService:
    """One cached session per server id; all calls must happen off the GUI thread."""

    def __init__(self, ctx):
        self.ctx = ctx
        self._sessions: dict[int, SftpSession] = {}
        self._lock = threading.Lock()

    def is_connected(self, server_id: int) -> bool:
        return server_id in self._sessions

    def get(self, server_id: int) -> Optional[SftpSession]:
        return self._sessions.get(server_id)

    def connect(self, server, gate=None) -> SftpSession:
        with self._lock:
            existing = self._sessions.get(server.id)
            if existing:
                return existing
            session = self._connect(server, gate)
            self._sessions[server.id] = session
            return session

    def _connect(self, server, gate) -> SftpSession:
        import paramiko

        gate = gate or _RaiseGate()
        # enforce host key policy with the SAME pipeline as OpenSSH sessions
        self.ctx.connections._resolve_server(server, None, None)
        self.ctx.connections.check_host_key(server, gate)

        client = paramiko.SSHClient()
        try:
            client.load_system_host_keys()
        except Exception:
            pass
        app_known = self.ctx.connections.app_known_hosts
        if Path(app_known).exists():
            client.load_host_keys(str(app_known))
        client.set_missing_host_key_policy(paramiko.RejectPolicy())

        kwargs = {
            "hostname": server.host,
            "port": int(server.port),
            "username": server.username,
            "timeout": int(server.connection_timeout or 15),
            "allow_agent": False,
            "look_for_keys": False,
        }
        if server.auth_type == "password":
            kwargs["password"] = self.ctx.credentials.get_server_password(server)
        elif server.auth_type == "key" and server.private_key_path:
            kwargs["key_filename"] = server.private_key_path
            key_record = self.ctx.keys.get_by_path(server.private_key_path)
            if key_record and key_record.passphrase_ref:
                kwargs["passphrase"] = self.ctx.credentials.get_key_passphrase(key_record.passphrase_ref)
        elif server.auth_type == "agent":
            kwargs["allow_agent"] = True
        # interactive: paramiko only supports key/agent here; user should connect once via terminal

        try:
            client.connect(**kwargs)
        except paramiko.AuthenticationException as exc:
            client.close()
            raise AuthError("SFTP authentication failed") from exc
        except paramiko.BadHostKeyException as exc:
            client.close()
            raise HostKeyChangedError(
                f"Host key mismatch for {server.host}: got {exc.fingerprint}",
            ) from exc
        except paramiko.SSHException as exc:
            client.close()
            raise SftpError(f"SSH error: {exc}") from exc
        except OSError as exc:
            client.close()
            raise SftpError(f"Network error: {exc}") from exc

        try:
            sftp = client.open_sftp()
        except paramiko.SSHException as exc:
            client.close()
            raise SftpError(f"Cannot open SFTP subsystem: {exc}") from exc
        log.info("SFTP connected: %s@%s:%s", server.username, server.host, server.port)
        return SftpSession(client, sftp, server)

    def disconnect(self, server_id: int) -> None:
        with self._lock:
            session = self._sessions.pop(server_id, None)
        if session:
            session.close()
            log.info("SFTP disconnected for server id=%s", server_id)

    def disconnect_all(self) -> None:
        with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            session.close()

    # ------------------------------------------------------------------ transfer between servers
    def transfer(self, src_server, src_path: str, dst_server, dst_path: str,
                 progress: Optional[Callable[[int, int], None]] = None, gate=None) -> str:
        """Stream a file directly between two servers."""
        import paramiko

        src = self.connect(src_server, gate)
        dst = self.connect(dst_server, gate)
        try:
            size = src.sftp.stat(src_path).st_size
            with src.sftp.open(src_path, "rb") as fr, dst.sftp.open(dst_path, "wb") as fw:
                done = 0
                while True:
                    chunk = fr.read(65536)
                    if not chunk:
                        break
                    fw.write(chunk)
                    done += len(chunk)
                    if progress:
                        progress(done, size)
            return dst_path
        except paramiko.SSHException as exc:
            raise SftpError(f"Transfer failed: {exc}") from exc


class _RaiseGate:
    """Default gate used outside the GUI: refuses unknown/changed host keys with clear errors."""

    def on_unknown(self, server, entries) -> bool:
        raise HostKeyUnknownError(
            f"Host key of '{server.host}' is unknown",
            fingerprints=[e.fingerprint for e in entries],
            hint="Accept the host key by connecting once via the terminal or the test button.",
        )

    def on_changed(self, server, expected, actual) -> bool:
        raise HostKeyChangedError(
            f"Host key of '{server.host}' has changed",
            expected=[e.fingerprint for e in expected],
            actual=[e.fingerprint for e in actual],
        )


def open_local_temp(suffix: str = "") -> Path:
    fd, name = tempfile.mkstemp(suffix=suffix, prefix="ssh-desk-")
    os.close(fd)
    return Path(name)
