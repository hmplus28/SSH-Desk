"""Heavy E2E tests against REAL servers.

Backends under test:
  * Real OpenSSH sshd on 127.0.0.1:2222 (key auth, exec, PTY shell, SFTP, tunnels)
  * Real GNOME Keyring (Secret Service) on a private session D-Bus
  * Real OpenSSH *client* for every connection (the product's engine)
  * paramiko server on 127.0.0.1:2223 ONLY to accept passwords (see e2e_server.py)

Run:  SSH_DESK_E2E=1 pytest -m e2e -v
Everything is localhost; no user machine or real server is ever touched.
"""

import hashlib
import os
import socket
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

SSHD_PORT = 2222
PW_PORT = 2223
SSHD_DIR = Path("/tmp/ssh-desk-e2e")
PLAIN_KEY = SSHD_DIR / "client_plain"
ENC_KEY = SSHD_DIR / "client_ed25519"
PW_USER = "e2e-user"
PW_PASS = "Str0ng-T3st-Pass!"
OK_MARKER = "SSH_DESK_TEST_OK"


# --------------------------------------------------------------------------- env
@pytest.fixture(scope="session", autouse=True)
def e2e_env():
    if os.environ.get("SSH_DESK_E2E") != "1":
        pytest.skip("E2E suite: run with SSH_DESK_E2E=1")
    # OpenSSH client binaries live in ~/.local/bin inside the sandbox
    local_bin = str(Path.home() / ".local" / "bin")
    if local_bin not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{local_bin}:{os.environ.get('PATH', '')}"
    # private session D-Bus with the real GNOME Keyring
    addr_file = Path("/tmp/ssh-desk-e2e-bus/dbus.addr")
    if addr_file.exists() and "DBUS_SESSION_BUS_ADDRESS" not in os.environ:
        os.environ["DBUS_SESSION_BUS_ADDRESS"] = addr_file.read_text().strip()
    yield


@pytest.fixture(scope="session")
def sshd(e2e_env):
    """Real OpenSSH sshd on 2222 must be up (started by scripts/setup_sshd.sh)."""
    import subprocess as sp

    probe = sp.run(["ssh", "-p", str(SSHD_PORT), "-i", str(PLAIN_KEY),
                    "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
                    "-o", "ConnectTimeout=3", "z@127.0.0.1", "echo SSHD_UP"],
                   capture_output=True, text=True, timeout=15, input="")
    assert "SSHD_UP" in probe.stdout, f"real sshd not reachable: {probe.stderr}"
    return {"host": "127.0.0.1", "port": SSHD_PORT, "user": "z", "plain_key": str(PLAIN_KEY)}


@pytest.fixture(scope="session")
def pw_server(e2e_env):
    from tests.e2e_server import PasswordSSHServer

    server = PasswordSSHServer(port=PW_PORT)
    yield server
    server.stop()


@pytest.fixture(scope="session")
def echo_server():
    """Plain TCP echo server used as the tunnel target."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(8)
    port = srv.getsockname()[1]

    def _echo():
        while True:
            try:
                conn, _ = srv.accept()
            except OSError:
                break
            with conn:
                while True:
                    data = conn.recv(65536)
                    if not data:
                        break
                    conn.sendall(data)

    t = threading.Thread(target=_echo, daemon=True)
    t.start()
    yield {"port": port}
    srv.close()


_CURRENT_APP_DIR = {"data": str(SSHD_DIR / "appdata"), "config": str(SSHD_DIR / "appconfig")}


@pytest.fixture()
def ctx(e2e_env):
    """Isolated AppContext per test, wired to the REAL Secret Service (GNOME Keyring)."""
    import uuid as _uuid

    from ssh_desk.core.application import AppContext
    from ssh_desk.services.credential_service import SecretServiceStore

    AppContext.reset()
    tag = _uuid.uuid4().hex[:8]
    data_dir = SSHD_DIR / f"app-{tag}"
    config_dir = SSHD_DIR / f"cfg-{tag}"
    _CURRENT_APP_DIR["data"] = str(data_dir)
    _CURRENT_APP_DIR["config"] = str(config_dir)
    context = AppContext(
        data_dir=data_dir,
        config_dir=config_dir,
        quiet_logs=True,
    )
    assert SecretServiceStore().available(), "real keyring must be available for E2E"
    yield context
    context.shutdown()
    AppContext.reset()


@pytest.fixture()
def clean_keyring(ctx):
    """Remove ssh-desk secrets from the real keyring before/after each test."""
    from ssh_desk.services.credential_service import SecretServiceStore

    store = SecretServiceStore()
    store.purge_all()
    yield
    store.purge_all()


def run_cli(args, ctx=None, timeout=60, check=False):
    """Run the REAL CLI as a subprocess (like a user would)."""
    env = {**os.environ,
           "SSH_DESK_DATA_DIR": _CURRENT_APP_DIR["data"],
           "SSH_DESK_CONFIG_DIR": _CURRENT_APP_DIR["config"],
           "SSH_DESK_BIN_DIR": str(Path(_CURRENT_APP_DIR["data"]) / "bin"),
           "PYTHONPATH": "/home/z/my-project/SSH-Desk/src"}
    proc = subprocess.run(
        [sys.executable, "-m", "ssh_desk.cli.main", *args],
        capture_output=True, text=True, timeout=timeout, env=env, input="",
    )
    if check and proc.returncode != 0:
        raise AssertionError(f"CLI {args} failed rc={proc.returncode}\nSTDERR: {proc.stderr}")
    return proc


def make_server(ctx, alias, **kw):
    from ssh_desk.utils.validation import ServerInput

    defaults = dict(name=f"Server {alias}", alias=alias, host="127.0.0.1",
                    port=SSHD_PORT, username="z", auth_type="key")
    defaults.update(kw)
    key_path = defaults.pop("private_key_path", None)
    timeout = defaults.pop("connection_timeout", None)
    if timeout is not None:
        defaults["connection_timeout"] = timeout
    return ctx.servers.create(ServerInput(**defaults), private_key_path=key_path)


def accept_hostkey(ctx, server, port=None):
    """Trust-and-store the host key (what a user does once via --accept-host-key)."""
    from ssh_desk.services.connection_service import CliHostKeyGate

    ctx.connections.check_host_key(server, CliHostKeyGate(assume_yes=True), port_override=port)


def set_password(ctx, server, password):
    """Store a password through the OFFICIAL service path (stores + links secret_ref)."""
    from ssh_desk.utils.validation import ServerInput

    data = ServerInput(
        name=server.name, alias=server.alias, host=server.host, port=server.port,
        username=server.username, auth_type=server.auth_type,
    )
    return ctx.servers.update(server.id, data, secret=password)


def add_saved_path(ctx, server, name, path, is_default=False):
    """Append a saved path via the official update() API."""
    from ssh_desk.utils.validation import PathInput, ServerInput

    existing = [PathInput(name=p.name, path=p.path, is_default=p.is_default) for p in server.paths]
    existing.append(PathInput(name=name, path=path, is_default=is_default))
    data = ServerInput(
        name=server.name, alias=server.alias, host=server.host, port=server.port,
        username=server.username, auth_type=server.auth_type,
        default_path=(path if is_default else server.default_path),
    )
    ctx.servers.update(server.id, data, paths=existing)
    return ctx.servers.get(server.id)


# =================================================================================
# 1. KEYRING (real GNOME Keyring)
# =================================================================================
def test_real_keyring_roundtrip(ctx):
    from ssh_desk.services.credential_service import SecretServiceStore

    store = SecretServiceStore()
    ref = store.store({"ssh-desk.type": "e2e"}, "s3cr3t-value", "e2e-roundtrip")
    assert store.retrieve(ref) == "s3cr3t-value"
    assert store.delete(ref)
    assert store.retrieve(ref) is None


# =================================================================================
# 2. PASSWORD AUTH: keyring -> askpass -> OpenSSH client -> server
# =================================================================================
def test_password_flow_full_pipeline(ctx, clean_keyring, pw_server):
    server = make_server(ctx, "pwfull", port=PW_PORT, username=PW_USER, auth_type="password")
    accept_hostkey(ctx, server)
    server = set_password(ctx, server, PW_PASS)
    result = ctx.connections.test(server)
    assert result.ok, f"password auth failed: {result.message}"
    assert result.latency_ms >= 0
    # the server must have received the exact secret via askpass (not argv/env)
    assert {"username": PW_USER, "password": PW_PASS} in pw_server.attempts


def test_wrong_password_fails_cleanly(ctx, clean_keyring, pw_server):
    server = make_server(ctx, "pwwrong", port=PW_PORT, username=PW_USER, auth_type="password")
    accept_hostkey(ctx, server)
    server = set_password(ctx, server, "definitely-wrong-pass")
    result = ctx.connections.test(server)
    assert not result.ok
    assert "denied" in result.message.lower() or "auth" in result.message.lower()


def test_missing_password_secret_detected(ctx, clean_keyring, pw_server):
    server = make_server(ctx, "pwmiss", port=PW_PORT, username=PW_USER, auth_type="password")
    accept_hostkey(ctx, server)
    # password never stored -> test must fail with a clear message, not crash
    result = ctx.connections.test(server)
    assert not result.ok
    assert result.message


def test_user_override_reaches_server_and_db_untouched(ctx, clean_keyring, pw_server):
    server = make_server(ctx, "pwuser", port=PW_PORT, username="alice", auth_type="password")
    accept_hostkey(ctx, server)
    server = set_password(ctx, server, PW_PASS)
    assert ctx.connections.test(server).ok
    # override to bob (not saved)
    assert ctx.connections.test(server, user="bob").ok
    assert {"username": "bob", "password": PW_PASS} in pw_server.attempts
    assert {"username": "alice", "password": PW_PASS} in pw_server.attempts
    fresh = ctx.servers.require_by_alias("pwuser")
    assert fresh.username == "alice"  # DB unchanged


# =================================================================================
# 3. KEY AUTH against REAL OpenSSH sshd
# =================================================================================
def test_key_auth_real_sshd(ctx, sshd):
    server = make_server(ctx, "keyprod", username="z", auth_type="key",
                         private_key_path=str(PLAIN_KEY))
    accept_hostkey(ctx, server)
    result = ctx.connections.test(server)
    assert result.ok, result.message
    assert result.latency_ms < 15000


def test_exec_real_remote_output(ctx, sshd):
    server = make_server(ctx, "keyexec", username="z", auth_type="key",
                         private_key_path=str(PLAIN_KEY))
    accept_hostkey(ctx, server)
    proc = run_cli(["keyexec", "--exec", "echo E2E_$((21*2)) && whoami && uname -s"])
    assert proc.returncode == 0, proc.stderr
    assert "E2E_42" in proc.stdout
    assert "z" in proc.stdout
    assert "Linux" in proc.stdout


def test_interactive_shell_with_real_pty(ctx, sshd):
    """TRUE interactive terminal: real PTY, real remote shell, arrows/colors capable."""
    import fcntl
    import pty
    import select as sel
    import struct
    import termios

    server = make_server(ctx, "keyshell", username="z", auth_type="key",
                         private_key_path=str(PLAIN_KEY))
    accept_hostkey(ctx, server)
    env = {**os.environ,
           "SSH_DESK_DATA_DIR": _CURRENT_APP_DIR["data"],
           "SSH_DESK_CONFIG_DIR": _CURRENT_APP_DIR["config"]}
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 120, 0, 0))
    proc = subprocess.Popen(
        [sys.executable, "-m", "ssh_desk.cli.main", "keyshell"],
        stdin=slave, stdout=slave, stderr=slave, env=env,
        preexec_fn=os.setsid,
    )
    os.close(slave)
    collected, deadline = b"", time.time() + 40
    sent = False
    try:
        while time.time() < deadline:
            r, _, _ = sel.select([master], [], [], 1.0)
            if r:
                try:
                    chunk = os.read(master, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                collected += chunk
            if not sent and (b"$" in collected or b"#" in collected or b"~" in collected):
                time.sleep(0.8)  # let the login shell settle
                os.write(master, b"echo PTY_E2E_$((6*7))\n")
                sent = True
            if sent and b"PTY_E2E_42" in collected:
                os.write(master, b"exit\n")
                break
        proc.wait(timeout=15)
    finally:
        if proc.poll() is None:
            proc.kill()
        os.close(master)
    assert b"PTY_E2E_42" in collected, f"PTY shell output: {collected[-800:]!r}"
    assert proc.returncode == 0


# =================================================================================
# 4. SAVED PATHS (names, absolute, spaces, errors)
# =================================================================================
@pytest.fixture()
def path_server(ctx, sshd):
    base = SSHD_DIR / "data"
    (base / "my docs").mkdir(parents=True, exist_ok=True)
    (base / "nginx-conf").mkdir(exist_ok=True)
    server = make_server(ctx, "pathsrv", username="z", auth_type="key",
                         private_key_path=str(PLAIN_KEY),
                         default_path=str(base / "nginx-conf"))
    server = add_saved_path(ctx, server, "nginx", str(base / "nginx-conf"))
    server = add_saved_path(ctx, server, "my docs", str(base / "my docs"))
    accept_hostkey(ctx, server)
    return server


def test_saved_path_by_name(ctx, path_server):
    proc = run_cli(["pathsrv", "nginx", "--exec", "pwd"])
    assert proc.returncode == 0, proc.stderr
    assert (SSHD_DIR / "data" / "nginx-conf").as_posix() in proc.stdout


def test_saved_path_name_with_spaces(ctx, path_server):
    proc = run_cli(["pathsrv", "my docs", "--exec", "pwd"])
    assert proc.returncode == 0, proc.stderr
    assert (SSHD_DIR / "data" / "my docs").as_posix() in proc.stdout


def test_absolute_path_with_spaces(ctx, path_server):
    proc = run_cli(["pathsrv", str(SSHD_DIR / "data" / "my docs"), "--exec", "pwd"])
    assert proc.returncode == 0, proc.stderr
    assert (SSHD_DIR / "data" / "my docs").as_posix() in proc.stdout


def test_unknown_path_name_error_lists_available(ctx, path_server):
    proc = run_cli(["pathsrv", "no-such-path", "--exec", "pwd"])
    assert proc.returncode == 1
    out = proc.stdout + proc.stderr
    assert "no-such-path" in out
    assert "nginx" in out and "my docs" in out  # helpful hint


def test_nonexistent_absolute_path_clean_error(ctx, path_server):
    proc = run_cli(["pathsrv", "/definitely/not/here", "--exec", "pwd"])
    assert proc.returncode != 0
    out = proc.stdout + proc.stderr
    assert "definitely" in out or "not" in out  # understandable failure


def test_default_path_used_when_no_target(ctx, path_server):
    proc = run_cli(["pathsrv", "--exec", "pwd"])
    assert proc.returncode == 0, proc.stderr
    assert (SSHD_DIR / "data" / "nginx-conf").as_posix() in proc.stdout


# =================================================================================
# 5. HOST KEY SECURITY (accept, store, CHANGE = blocked)
# =================================================================================
def test_hostkey_unknown_then_accept_and_store(ctx, clean_keyring, sshd):
    from ssh_desk.services.connection_service import CliHostKeyGate, NonInteractiveGate
    from ssh_desk.ssh import hostkeys

    server = make_server(ctx, "freshhost", username="z", auth_type="key",
                         private_key_path=str(PLAIN_KEY))
    # simulate a machine that has never seen this host
    hostkeys.remove_entry(ctx.connections.app_known_hosts, "127.0.0.1", SSHD_PORT)
    # 1) unknown host + non-interactive gate => refused, not silently accepted
    with pytest.raises(Exception) as ei:
        ctx.connections.check_host_key(server, NonInteractiveGate())
    assert "not known" in str(ei.value).lower() or "finger" in str(ei.value).lower()
    # 2) explicit accept => stored with fingerprint
    ctx.connections.check_host_key(server, CliHostKeyGate(assume_yes=True))
    from ssh_desk.ssh import hostkeys
    entries = hostkeys.lookup([ctx.connections.app_known_hosts], "127.0.0.1", SSHD_PORT)
    assert entries, "host key must be stored after acceptance"
    assert all(e.fingerprint.startswith("SHA256:") for e in entries)
    # 3) subsequent test() succeeds (key already known)
    assert ctx.connections.test(server).ok


def test_hostkey_change_is_blocked_mitm(ctx, sshd):
    """THE security test: swap the sshd host key -> connection MUST be blocked."""
    from ssh_desk.services.connection_service import CliHostKeyGate, NonInteractiveGate
    from ssh_desk.ssh import hostkeys

    server = make_server(ctx, "mitmhost", username="z", auth_type="key",
                         private_key_path=str(PLAIN_KEY))
    ctx.connections.check_host_key(server, CliHostKeyGate(assume_yes=True))
    assert ctx.connections.test(server).ok
    fps_before = {e.fingerprint for e in
                  hostkeys.lookup([ctx.connections.app_known_hosts], "127.0.0.1", SSHD_PORT)}

    def _swap_all_host_keys():
        """Replace BOTH host key types (otherwise the untouched one still matches)."""
        for keytype, name in (("ed25519", "host_ed25519"), ("rsa", "host_rsa")):
            priv = SSHD_DIR / name
            pub = SSHD_DIR / f"{name}.pub"
            (SSHD_DIR / f"{name}.mitm-new").unlink(missing_ok=True)
            priv.unlink()
            pub.unlink(missing_ok=True)
            subprocess.run(["ssh-keygen", "-q", "-t", keytype, "-N", "", "-f", str(priv)],
                           check=True)
            os.chmod(priv, 0o600)

    def _restore_host_keys():
        for name in ("host_ed25519", "host_rsa"):
            bak = SSHD_DIR / f"{name}.mitm-bak"
            priv = SSHD_DIR / name
            if bak.exists():
                bak.rename(priv)
                os.chmod(priv, 0o600)
            pub_bak = SSHD_DIR / f"{name}.pub.mitm-bak"
            if pub_bak.exists():
                pub_bak.rename(SSHD_DIR / f"{name}.pub")

    # snapshot current keys so they can be restored even if assertions fail
    for name in ("host_ed25519", "host_rsa"):
        (SSHD_DIR / f"{name}.mitm-bak").write_bytes((SSHD_DIR / name).read_bytes())
        (SSHD_DIR / f"{name}.pub.mitm-bak").write_bytes((SSHD_DIR / f"{name}.pub").read_bytes())

    pid = int((SSHD_DIR / "sshd.pid").read_text())
    os.kill(pid, 15)
    _wait_port_closed()
    _swap_all_host_keys()
    _restart_sshd()

    try:
        with pytest.raises(Exception) as ei:
            ctx.connections.test(server, gate=NonInteractiveGate())
        msg = str(ei.value).lower()
        assert "changed" in msg or "middle" in msg, f"unexpected error: {ei.value}"
        # nothing was silently overwritten
        fps_after = {e.fingerprint for e in
                     hostkeys.lookup([ctx.connections.app_known_hosts], "127.0.0.1", SSHD_PORT)}
        assert fps_after == fps_before, "known_hosts must not be altered on key change"
    finally:
        # restore original keys and restart sshd
        try:
            os.kill(int((SSHD_DIR / "sshd.pid").read_text()), 15)
        except (ProcessLookupError, ValueError):
            pass
        _wait_port_closed()
        _restore_host_keys()
        _restart_sshd()
    assert ctx.connections.test(server).ok  # original key accepted again


def _wait_port_closed(timeout=10):
    import socket as _s

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            _s.create_connection(("127.0.0.1", SSHD_PORT), timeout=0.5).close()
            time.sleep(0.3)
        except OSError:
            return
    raise TimeoutError("sshd did not stop")


def _restart_sshd():
    # the sandbox uses the monolithic OpenSSH 9.2 binary (sshd-session is root-only
    # on modern OpenSSH); it needs libwrap from ~/.local/lib
    subprocess.run(
        ["/home/z/my-project/local-ssh-old/usr/sbin/sshd",
         "-f", str(SSHD_DIR / "sshd_config"), "-E", str(SSHD_DIR / "sshd.log")],
        check=True, env={**os.environ, "LD_LIBRARY_PATH": str(Path.home() / ".local" / "lib")})
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            import socket as _s
            _s.create_connection(("127.0.0.1", SSHD_PORT), timeout=0.5).close()
            return
        except OSError:
            time.sleep(0.3)
    raise TimeoutError("sshd did not come up")


# =================================================================================
# 6. SFTP against REAL OpenSSH internal-sftp
# =================================================================================
REMOTE_BASE = "/home/z/e2e-upload"


@pytest.fixture()
def sftp(ctx, sshd):
    server = make_server(ctx, "sftpserver", username="z", auth_type="key",
                         private_key_path=str(PLAIN_KEY))
    accept_hostkey(ctx, server)
    session = ctx.sftp.connect(server)
    try:
        session.remove_tree(REMOTE_BASE)
    except Exception:
        pass
    session.mkdir(REMOTE_BASE)
    yield session
    ctx.sftp.disconnect_all()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_sftp_roundtrip_3mb(sftp, tmp_path):
    local = tmp_path / "payload.bin"
    local.write_bytes(os.urandom(3 * 1024 * 1024))
    sftp.upload(str(local), f"{REMOTE_BASE}/payload.bin")
    back = tmp_path / "payload.back"
    sftp.download(f"{REMOTE_BASE}/payload.bin", str(back))
    assert _sha256(back) == _sha256(local)


def test_sftp_paths_with_spaces_and_unicode(sftp, tmp_path):
    sftp.mkdir(f"{REMOTE_BASE}/ remote dir ")
    local = tmp_path / "ünïcode file.txt"
    local.write_text("سلام از SSH Desk! Hello!")
    sftp.upload(str(local), f"{REMOTE_BASE}/ remote dir /ünïcode file.txt")
    back = tmp_path / "back ünïcode.txt"
    sftp.download(f"{REMOTE_BASE}/ remote dir /ünïcode file.txt", str(back))
    assert back.read_text() == "سلام از SSH Desk! Hello!"


def test_sftp_mkdir_list_rename_delete(sftp, tmp_path):
    sftp.mkdir(f"{REMOTE_BASE}/sub dir")
    entries = {e.name for e in sftp.list_dir(REMOTE_BASE)}
    assert "sub dir" in entries
    local = tmp_path / "r.txt"
    local.write_text("rename-me")
    sftp.upload(str(local), f"{REMOTE_BASE}/r.txt")
    sftp.rename(f"{REMOTE_BASE}/r.txt", f"{REMOTE_BASE}/r2 renamed.txt")
    sftp.remove_file(f"{REMOTE_BASE}/r2 renamed.txt")
    with pytest.raises(Exception):
        sftp.download(f"{REMOTE_BASE}/r2 renamed.txt", str(tmp_path / "gone.txt"))


def test_sftp_20mb_throughput(sftp, tmp_path):
    local = tmp_path / "big.bin"
    local.write_bytes(os.urandom(20 * 1024 * 1024))
    t0 = time.monotonic()
    sftp.upload(str(local), f"{REMOTE_BASE}/big.bin")
    up = time.monotonic() - t0
    back = tmp_path / "big.back"
    t0 = time.monotonic()
    sftp.download(f"{REMOTE_BASE}/big.bin", str(back))
    down = time.monotonic() - t0
    assert _sha256(back) == _sha256(local)
    assert up < 60 and down < 60, f"transfer too slow: up={up:.1f}s down={down:.1f}s"


# =================================================================================
# 7. TUNNELS (real TCP forwarding through sshd)
# =================================================================================
def test_local_tunnel_roundtrip(ctx, sshd, echo_server):
    from ssh_desk.utils.validation import TunnelInput

    server = make_server(ctx, "tunnelhost", username="z", auth_type="key",
                         private_key_path=str(PLAIN_KEY))
    accept_hostkey(ctx, server)
    tunnel = ctx.tunnels.create(server.id, "echo-tunnel", TunnelInput(
        tunnel_type="local", local_host="127.0.0.1", local_port=18443,
        remote_host="127.0.0.1", remote_port=echo_server["port"]))
    ctx.tunnels.start(tunnel.id)
    try:
        # wait for forward to come up
        ok = False
        payload = os.urandom(1024)
        for _ in range(30):
            try:
                with socket.create_connection(("127.0.0.1", 18443), timeout=2) as s:
                    s.sendall(payload)
                    got = b""
                    while len(got) < len(payload):
                        got += s.recv(65536)
                if got == payload:
                    ok = True
                    break
            except OSError:
                time.sleep(0.5)
        assert ok, "tunnel did not forward the payload"
        running = ctx.tunnels.get(tunnel.id)
        assert running.status == "running" and running.pid
    finally:
        ctx.tunnels.stop(tunnel.id)
    time.sleep(0.5)
    with pytest.raises(OSError):
        socket.create_connection(("127.0.0.1", 18443), timeout=2)


def test_dynamic_socks_tunnel_opens_and_closes(ctx, sshd, echo_server):
    from ssh_desk.utils.validation import TunnelInput

    server = make_server(ctx, "sockshost", username="z", auth_type="key",
                         private_key_path=str(PLAIN_KEY))
    accept_hostkey(ctx, server)
    tunnel = ctx.tunnels.create(server.id, "socks", TunnelInput(
        tunnel_type="dynamic", local_host="127.0.0.1", local_port=18444))
    ctx.tunnels.start(tunnel.id)
    try:
        time.sleep(1.5)
        # SOCKS5 handshake: greeting + CONNECT to the echo server
        with socket.create_connection(("127.0.0.1", 18444), timeout=4) as s:
            s.sendall(b"\x05\x01\x00")  # hello, no auth
            assert s.recv(2) == b"\x05\x00"
            target = socket.inet_aton("127.0.0.1") + (echo_server["port"]).to_bytes(2, "big")
            s.sendall(b"\x05\x01\x00\x01" + target)
            reply = b""
            while len(reply) < 10:
                reply += s.recv(10 - len(reply))
            assert reply[1] == 0, f"SOCKS connect failed: {reply!r}"
            s.sendall(b"ping-socks")
            assert s.recv(1024) == b"ping-socks"
    finally:
        ctx.tunnels.stop(tunnel.id)


# =================================================================================
# 8. CLI INTEGRATION (OS-level command rename, history, export)
# =================================================================================
def test_cli_rename_command_os_level(ctx, sshd):
    """User renames sss -> cnc in settings; the OS-level command must really appear."""
    from ssh_desk.cli import shell_integration

    make_server(ctx, "cnchost", username="z", auth_type="key",
                private_key_path=str(PLAIN_KEY))
    ctx.settings.set("cli_command_name", "cnc")
    link = shell_integration.install_cli_name("cnc", previous="sss")
    assert link.exists(), f"renamed command not installed at {link}"
    env = {**os.environ, "PATH": f"{link.parent}:{os.environ['PATH']}",
           "SSH_DESK_DATA_DIR": _CURRENT_APP_DIR["data"],
           "SSH_DESK_CONFIG_DIR": _CURRENT_APP_DIR["config"],
           "PYTHONPATH": "/home/z/my-project/SSH-Desk/src"}
    proc = subprocess.run(["cnc", "list"], capture_output=True, text=True, env=env,
                          timeout=30, input="")
    assert proc.returncode == 0, proc.stderr
    assert "cnchost" in proc.stdout, proc.stdout


def test_cli_history_recorded(ctx, sshd):
    server = make_server(ctx, "histhost", username="z", auth_type="key",
                         private_key_path=str(PLAIN_KEY))
    accept_hostkey(ctx, server)
    proc_exec = run_cli(["histhost", "--exec", "echo HISTORY_E2E"])
    assert proc_exec.returncode == 0, proc_exec.stderr  # exec session records history
    proc = run_cli(["history"])
    assert proc.returncode == 0, proc.stderr
    assert "histhost" in proc.stdout
    rows = ctx.history.list(server_id=server.id)
    assert len(rows) >= 1
    assert rows[0].status in ("closed", "failed", "open")


def test_delete_server_removes_keyring_secret(ctx, clean_keyring, pw_server):
    from ssh_desk.services.credential_service import SecretServiceStore

    server = make_server(ctx, "todelete", port=PW_PORT, username=PW_USER, auth_type="password")
    accept_hostkey(ctx, server)
    server = set_password(ctx, server, PW_PASS)
    ref = server.secret_ref
    assert SecretServiceStore().retrieve(ref) == PW_PASS
    run_cli(["delete", "todelete", "--yes"], check=True)
    assert SecretServiceStore().retrieve(ref) is None, "keyring secret must be purged on delete"
    with pytest.raises(Exception):
        ctx.servers.require_by_alias("todelete")


def test_export_contains_no_secrets(ctx, clean_keyring, pw_server, tmp_path):
    server = make_server(ctx, "exportme", port=PW_PORT, username=PW_USER, auth_type="password")
    accept_hostkey(ctx, server)
    server = set_password(ctx, server, PW_PASS)
    out = tmp_path / "export.toml"
    run_cli(["export", str(out)], check=True)
    content = out.read_text()
    assert PW_PASS not in content, "PASSWORD LEAKED INTO EXPORT FILE"
    assert server.secret_ref not in content
    assert "exportme" in content


# =================================================================================
# 9. STRESS
# =================================================================================
def test_stress_15_servers_parallel_tests(ctx, clean_keyring, pw_server):
    """15 servers, 8-way parallel real connection tests (mix of key + password)."""
    servers = []
    for i in range(15):
        if i % 3 == 0:
            s = make_server(ctx, f"stress-key-{i}", username="z", auth_type="key",
                            private_key_path=str(PLAIN_KEY))
            accept_hostkey(ctx, s)
        else:
            s = make_server(ctx, f"stress-pw-{i}", port=PW_PORT, username=PW_USER,
                            auth_type="password")
            accept_hostkey(ctx, s)
            s = set_password(ctx, s, PW_PASS)
        servers.append(s)
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda s: ctx.connections.test(s), servers))
    elapsed = time.monotonic() - t0
    assert all(r.ok for r in results), [r.message for r in results if not r.ok]
    assert elapsed < 120, f"parallel tests too slow: {elapsed:.1f}s"


def test_stress_history_50_rows(ctx):

    s = make_server(ctx, "histstress", username="z", auth_type="key",
                    private_key_path=str(PLAIN_KEY))
    accept_hostkey(ctx, s)
    for _ in range(50):
        ctx.history.start(s)
    rows = ctx.history.list(server_id=s.id, limit=100)
    assert len(rows) >= 50
    assert len(ctx.history.list(server_id=s.id, limit=10)) == 10
    assert all(r.server_alias == "histstress" for r in rows)


def test_stress_concurrent_sftp(ctx, sshd, tmp_path):
    server = make_server(ctx, "sftpstress", username="z", auth_type="key",
                         private_key_path=str(PLAIN_KEY))
    accept_hostkey(ctx, server)
    from ssh_desk.services.sftp_service import SftpService

    results, errors = [], []

    def worker(i: int):
        try:
            time.sleep(i * 0.3)  # stagger connects (sshd MaxStartups throttling)
            svc = SftpService(ctx)
            session = svc.connect(server)
            local = tmp_path / f"cc-{i}.bin"
            local.write_bytes(os.urandom(1024 * 1024))
            session.upload(str(local), f"{REMOTE_BASE}/cc-{i}.bin")
            back = tmp_path / f"cc-{i}.back"
            session.download(f"{REMOTE_BASE}/cc-{i}.bin", str(back))
            results.append(_sha256(back) == _sha256(local))
            svc.disconnect_all()
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=90)
    assert not errors, errors
    assert results == [True] * 5


def test_connect_cycles_no_ssh_zombie_leak(ctx, sshd):
    server = make_server(ctx, "cyclehost", username="z", auth_type="key",
                         private_key_path=str(PLAIN_KEY))
    accept_hostkey(ctx, server)
    before = _ssh_proc_count()
    for _ in range(5):
        assert ctx.connections.test(server).ok
    time.sleep(1.0)
    after = _ssh_proc_count()
    assert after <= before + 2, f"ssh processes leaked: {before} -> {after}"


def _ssh_proc_count() -> int:
    out = subprocess.run(["ps", "-eo", "comm"], capture_output=True, text=True).stdout
    return sum(1 for line in out.splitlines() if line.strip() == "ssh")


# =================================================================================
# 10. UNREACHABLE / ROBUSTNESS
# =================================================================================
def test_unreachable_host_clean_timeout(ctx, clean_keyring):

    s = make_server(ctx, "unreach", host="127.0.0.1", port=59977, username="z",
                    auth_type="key", private_key_path=str(PLAIN_KEY),
                    connection_timeout=3)
    t0 = time.monotonic()
    result = ctx.connections.test(s)
    elapsed = time.monotonic() - t0
    assert not result.ok
    assert elapsed < 30
    assert result.message


def test_reserved_and_invalid_cli_names_rejected(ctx):
    from ssh_desk.cli import shell_integration
    from ssh_desk.core.exceptions import ValidationErrorX

    with pytest.raises(ValidationErrorX):
        shell_integration.install_cli_name("SSH")            # uppercase
    with pytest.raises(ValidationErrorX):
        shell_integration.install_cli_name("ls")             # reserved system name
    with pytest.raises(ValidationErrorX):
        shell_integration.install_cli_name("a" * 40)         # too long
