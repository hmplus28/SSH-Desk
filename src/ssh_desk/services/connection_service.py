"""Connection orchestration: host-key policy, session preparation, testing, CLI sessions."""

import logging
import subprocess
import time
import uuid
from dataclasses import dataclass

from ssh_desk.core import constants
from ssh_desk.core.exceptions import (
    HostKeyChangedError,
    HostKeyUnknownError,
    SSHConnectionError,
)
from ssh_desk.database.models import Server
from ssh_desk.ssh import client, hostkeys

log = logging.getLogger("ssh_desk.connection")


@dataclass
class PreparedSession:
    argv: list[str]
    env: dict
    server: Server
    remote_desc: str = ""
    path: str | None = None
    exec_cmd: str | None = None
    _ephemeral_ref: str | None = None


@dataclass
class TestResult:
    ok: bool
    message: str
    latency_ms: int = 0


@dataclass
class HostKeyDecision:
    accepted: bool = False
    forget: bool = False


class CliHostKeyGate:
    """Interactive terminal gate for unknown / changed host keys."""

    def __init__(self, assume_yes: bool = False):
        self.assume_yes = assume_yes

    def on_unknown(self, server, entries) -> bool:
        if self.assume_yes:
            return True
        import sys

        if not sys.stdin.isatty():
            log.info("non-interactive terminal; rejecting unknown host key for %s", server.alias)
            raise HostKeyUnknownError(
                f"Host key of '{server.host}' is not known yet.",
                fingerprints=[e.fingerprint for e in entries],
                hint=f"Run: sss test {server.alias} --accept-host-key  (verify the fingerprint first)",
            )
        print(f"The authenticity of host '{server.host}:{server.port}' can't be established.", file=sys.stderr)
        for entry in entries:
            print(f"  {entry.key_type}  {entry.fingerprint}", file=sys.stderr)
        answer = input("Accept this host key and store it? [y/N] ").strip().lower()
        return answer in ("y", "yes")

    def on_changed(self, server, expected, actual) -> bool:

        raise HostKeyChangedError(
            f"WARNING: host key of '{server.host}' has CHANGED - possible man-in-the-middle!",
            expected=[e.fingerprint for e in expected],
            actual=[e.fingerprint for e in actual],
            hint="If you are sure the key changed legitimately, remove it with: "
            f"ssh-keygen -R [{server.host}]:{server.port}",
        )


class NonInteractiveGate:
    def on_unknown(self, server, entries) -> bool:
        raise HostKeyUnknownError(
            f"Host key of '{server.host}' is not known yet.",
            fingerprints=[e.fingerprint for e in entries],
            hint=f"Connect once interactively first (sss test {server.alias} --accept-host-key).",
        )

    def on_changed(self, server, expected, actual) -> bool:
        raise HostKeyChangedError(
            f"Host key of '{server.host}' has changed!",
            expected=[e.fingerprint for e in expected],
            actual=[e.fingerprint for e in actual],
        )


class ConnectionService:
    def __init__(self, ctx):
        self.ctx = ctx
        self.process_manager = ctx.process_manager

    # ------------------------------------------------------------------ host keys
    def check_host_key(self, server, gate, port_override: int | None = None) -> None:
        """Enforce the security policy BEFORE any connection attempt."""
        host = server.host
        port = int(port_override or server.port)
        app_file = self.app_known_hosts
        system_file = Path_home() / ".ssh" / "known_hosts"
        known = hostkeys.lookup([system_file, app_file], host, port)
        try:
            fetched = hostkeys.fetch_host_keys(host, port)
        except SSHConnectionError:
            raise
        except Exception:
            fetched = []
        if not fetched:
            # unreachable server: let the real ssh attempt produce the error
            return
        if known:
            known_fps = {e.fingerprint for e in known}
            fetched_fps = {e.fingerprint for e in fetched}
            if not (known_fps & fetched_fps):
                if not gate.on_changed(server, known, fetched):
                    raise HostKeyChangedError(
                        f"Host key of '{host}' changed and was NOT accepted",
                        expected=[e.fingerprint for e in known],
                        actual=[e.fingerprint for e in fetched],
                    )
                # user accepted the new key: replace entries
                hostkeys.remove_entry(app_file, host, port)
                for entry in fetched:
                    hostkeys.add_entry(app_file, entry)
            return
        # unknown host
        if not gate.on_unknown(server, fetched):
            raise HostKeyUnknownError(
                f"Host key of '{host}' was NOT accepted",
                fingerprints=[e.fingerprint for e in fetched],
            )
        for entry in fetched:
            hostkeys.add_entry(app_file, entry)
        log.info("host key stored for %s:%s", host, port)

    @property
    def app_known_hosts(self):
        from pathlib import Path

        return Path(self.ctx.data_dir) / constants.KNOWN_HOSTS_NAME

    # ------------------------------------------------------------------ prepare
    def _resolve_server(self, server, user, port):
        """Attach key passphrase ref (transient) when a key record matches."""
        if server.auth_type == "key" and server.private_key_path:
            key_record = self.ctx.keys.get_by_path(server.private_key_path)
            if key_record and key_record.passphrase_ref:
                server.key_passphrase_ref = key_record.passphrase_ref
        if user:
            from ssh_desk.utils.validation import USERNAME_RE

            if not USERNAME_RE.match(user):
                raise SSHConnectionError(f"Invalid username override: {user!r}")
        if port is not None and not (1 <= int(port) <= 65535):
            raise SSHConnectionError(f"Invalid port override: {port}")
        return server

    def prepare(
        self,
        server,
        *,
        path_target: str | None = None,
        exec_cmd: str | None = None,
        user: str | None = None,
        port: int | None = None,
        saved_command: str | None = None,
        force_tty: bool = True,
        gate=None,
        password_override: str | None = None,
        session_marker: bool = True,
        check_host_keys: bool = True,
    ) -> PreparedSession:
        gate = gate or CliHostKeyGate()
        self._resolve_server(server, user, port)
        if check_host_keys:
            self.check_host_key(server, gate, port_override=port)

        path = self.ctx.servers.resolve_target(server, path_target)
        command = saved_command or exec_cmd
        if password_override:
            ref = self.ctx.credentials.store_ephemeral(f"tmp-{uuid.uuid4().hex[:8]}", password_override)
            prepared = self._build(server, path=path, exec_cmd=command, user=user, port=port,
                                   force_tty=force_tty, session_marker=session_marker)
            # swap the askpass ref to the ephemeral secret for this run
            prepared.env[constants.SECRET_REF_ENV] = ref
            prepared._ephemeral_ref = ref
            return prepared
        return self._build(server, path=path, exec_cmd=command, user=user, port=port,
                           force_tty=force_tty, session_marker=session_marker)

    def _build(self, server: Server, *, path, exec_cmd, user, port, force_tty, session_marker) -> PreparedSession:
        argv, env = client.build_connect_argv(
            self.ctx, server, path=path, exec_cmd=exec_cmd, user=user, port=port,
            force_tty=force_tty, session_marker=session_marker,
        )
        desc = f"{server.username}@{server.host}:{server.port}"
        if path:
            desc += f" -> {path}"
        return PreparedSession(argv=argv, env=env, server=server, remote_desc=desc, path=path, exec_cmd=exec_cmd)

    # ------------------------------------------------------------------ test
    def test(self, server, *, user=None, port=None, gate=None, password_override=None) -> TestResult:
        gate = gate or CliHostKeyGate()
        # re-read the row: callers may hold a stale instance whose secret_ref /
        # private_key_path were set by a later update() on a different object
        fresh = self.ctx.servers.get(server.id)
        if fresh is not None and fresh.id == server.id:
            server = fresh
        self._resolve_server(server, user, port)
        self.check_host_key(server, gate, port_override=port)

        ephemeral_ref = None
        if password_override:
            ephemeral_ref = self.ctx.credentials.store_ephemeral(f"test-{uuid.uuid4().hex[:8]}", password_override)
        try:
            argv, env = client.build_test_argv(self.ctx, server, user=user, port=port,
                                               password_override_ref=ephemeral_ref)
            full_env = {**__import__("os").environ, **env}
            started = time.monotonic()
            try:
                proc = subprocess.run(
                    argv, env=full_env, capture_output=True, text=True,
                    timeout=int(server.connection_timeout or 15) + 20,
                )
            except subprocess.TimeoutExpired:
                return TestResult(False, f"Timed out after {server.connection_timeout}s", 0)
            latency = int((time.monotonic() - started) * 1000)
            if proc.returncode == 0 and constants.OK_MARKER in proc.stdout:
                return TestResult(True, "Connection successful", latency)
            message = self._human_error(proc.stderr.strip() or f"ssh exited with code {proc.returncode}")
            return TestResult(False, message, latency)
        finally:
            if ephemeral_ref:
                self.ctx.credentials.delete_ref(ephemeral_ref)

    # ------------------------------------------------------------------ run (CLI)
    def run_session(self, prepared: PreparedSession, record_history: bool = True) -> int:
        """Run an interactive/exec SSH session in the foreground; record history."""
        import os

        history_id = None
        if record_history:
            history_id = self.ctx.history.start(prepared.server)
        log.info("starting session: %s (argv redacted)", prepared.remote_desc)
        env = {**os.environ, **prepared.env}
        try:
            proc = subprocess.Popen(prepared.argv, env=env)
        except FileNotFoundError as exc:
            if history_id:
                self.ctx.history.close(history_id, "failed", "OpenSSH client (ssh) not found")
            raise SSHConnectionError("OpenSSH client (ssh) is not installed") from exc
        self.process_manager.register(proc.pid, "session", {"alias": prepared.server.alias})
        status, error = "closed", None
        try:
            code = proc.wait()
            if code != 0:
                status = "failed"
                error = f"ssh exited with code {code}"
        except KeyboardInterrupt:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
            status, code = "interrupted", 130
        finally:
            self.process_manager.unregister(proc.pid)
            if history_id:
                self.ctx.history.close(history_id, status, error)
        return code

    # ------------------------------------------------------------------ proxy
    def proxy_exec(self, jump_server, target_host: str, target_port: int) -> None:
        """Replace the current process with `ssh -W` through the jump server (used by ProxyCommand)."""
        import os

        self._resolve_server(jump_server, None, None)
        self.check_host_key(jump_server, NonInteractiveGate())
        argv, env = client.build_proxy_argv(self.ctx, jump_server, target_host, target_port)
        full_env = {**os.environ, **env}
        os.execvpe(argv[0], argv, full_env)

    @staticmethod
    def _human_error(stderr: str) -> str:
        low = stderr.lower()
        if "permission denied" in low:
            return "Authentication failed (permission denied). Check username/password/key."
        if "connection refused" in low:
            return "Connection refused - is sshd running on that port?"
        if "connection timed out" in low or "timed out" in low:
            return "Connection timed out - host unreachable or firewall blocking."
        if "no route to host" in low:
            return "No route to host - check network/VPN."
        if "host key verification failed" in low:
            return "Host key verification failed."
        if "could not resolve hostname" in low:
            return "Cannot resolve hostname - check the host address."
        if "broken pipe" in low or "connection reset" in low:
            return "Connection reset by peer."
        return stderr.splitlines()[-1] if stderr else "Unknown SSH error"


def Path_home():
    from pathlib import Path

    return Path.home()
