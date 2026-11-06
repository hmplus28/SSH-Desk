"""Detached tunnel daemon: keeps `ssh -N -L/-R/-D` alive and tracks its status in the DB.

Started by TunnelService as a detached process:
    python -m ssh_desk.ssh.tunnel_runner <tunnel_id>
"""

import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from ssh_desk.database.models import Tunnel
from ssh_desk.ssh import client

log = logging.getLogger("ssh_desk.tunnel_runner")


def _update(tunnel_id: int, **fields) -> None:
    from ssh_desk.core.application import AppContext

    ctx = AppContext.instance()
    with ctx.db.session() as session:
        tunnel = session.get(Tunnel, tunnel_id)
        if not tunnel:
            return
        for key, value in fields.items():
            setattr(tunnel, key, value)
        session.commit()


def _load(tunnel_id: int) -> Tunnel:
    from ssh_desk.core.application import AppContext

    ctx = AppContext.instance()
    with ctx.db.session() as session:
        tunnel = session.get(Tunnel, tunnel_id)
        if not tunnel:
            raise SystemExit(f"tunnel {tunnel_id} not found")
        session.expunge(tunnel)
        return tunnel


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python -m ssh_desk.ssh.tunnel_runner <tunnel_id>", file=sys.stderr)
        return 2
    tunnel_id = int(sys.argv[1])
    from ssh_desk.core.application import AppContext

    ctx = AppContext.instance()
    tunnel = _load(tunnel_id)
    server = ctx.servers.get(tunnel.server_id)

    from ssh_desk.services.connection_service import NonInteractiveGate

    ctx.connections.check_host_key(server, NonInteractiveGate())
    service = ctx.tunnels
    argv, env = client.build_tunnel_argv(ctx, server, port_spec=service.port_spec(tunnel))

    proc = subprocess.Popen(argv, env={**os.environ, **env}, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    _update(tunnel_id, status="running", pid=proc.pid, last_error=None)
    log.info("tunnel %s running (ssh pid %s)", tunnel.name, proc.pid)

    stopping = {"flag": False}

    def _sigterm(_signum, _frame):
        stopping["flag"] = True

    signal.signal(signal.SIGTERM, _sigterm)
    signal.signal(signal.SIGINT, _sigterm)

    stderr_tail = b""
    try:
        while True:
            code = proc.poll()
            if code is not None:
                break
            if stopping["flag"]:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                code = 0
                break
            if proc.stderr and not proc.stderr.closed:
                import select

                readable, _, _ = select.select([proc.stderr], [], [], 0.5)
                if readable:
                    chunk = os.read(proc.stderr.fileno(), 4096)
                    if chunk:
                        stderr_tail = (stderr_tail + chunk)[-4000:]
            time.sleep(0.3)
    finally:
        try:
            if proc.stderr:
                proc.stderr.close()
        except OSError:
            pass
        status = "stopped" if (code == 0 or stopping["flag"]) else "error"
        if code not in (0, None) and not stopping["flag"]:
            text_tail = stderr_tail.decode(errors="replace").strip().splitlines()
            message = text_tail[-1] if text_tail else f"ssh exited with code {code}"
            if "exitonforwardfailure" in message.lower() or "address already in use" in message.lower():
                message = f"Forward failed: {message}"
            _update(tunnel_id, status=status, pid=None, last_error=message[:500])
        else:
            _update(tunnel_id, status="stopped", pid=None, last_error=None)
        log.info("tunnel %s exited (code=%s)", tunnel.name, code)
    return 0


if __name__ == "__main__":
    from ssh_desk.utils.logging_setup import setup_logging

    setup_logging(Path(os.path.expanduser("~/.local/share/ssh-desk")) / "logs")
    sys.exit(main())
