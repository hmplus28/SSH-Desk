"""Process helpers: detect running SSH Desk sessions by scanning /proc, PID checks, port checks."""

import logging
import os
import signal
import socket
import time
from pathlib import Path

from ssh_desk.core import constants

log = logging.getLogger("ssh_desk.procs")


def _read_environ(pid: int) -> dict:
    try:
        raw = Path(f"/proc/{pid}/environ").read_bytes()
    except (OSError, PermissionError):
        return {}
    env = {}
    for chunk in raw.split(b"\x00"):
        if b"=" in chunk:
            key, _, value = chunk.partition(b"=")
            env[key.decode(errors="replace")] = value.decode(errors="replace")
    return env


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def list_sessions() -> list[dict]:
    """Return SSH sessions started by SSH Desk (env-marked ssh processes owned by this user)."""
    sessions = []
    euid = os.geteuid()
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            if os.stat(entry).st_uid != euid:
                continue
        except OSError:
            continue
        env = _read_environ(pid)
        if constants.TERMINAL_SESSION_ENV in env:
            sessions.append(
                {
                    "pid": pid,
                    "session_id": env[constants.TERMINAL_SESSION_ENV],
                    "alias": env.get(constants.TERMINAL_ALIAS_ENV, "?"),
                }
            )
    sessions.sort(key=lambda s: s["pid"])
    return sessions


def terminate_tree(pid: int, timeout: float = 3.0) -> bool:
    """Terminate a process we own: SIGTERM then SIGKILL."""
    if not pid_alive(pid):
        return True
    try:
        os.kill(pid, signal.SIGTERM)
    except (OSError, PermissionError):
        return False
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not pid_alive(pid):
            return True
        time.sleep(0.1)
    try:
        os.kill(pid, signal.SIGKILL)
    except (OSError, PermissionError):
        return False
    return not pid_alive(pid)


def port_in_use(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.3):
            return True
    except OSError:
        return False


def port_bindable(host: str, port: int) -> bool:
    """True when we can bind the port locally (i.e. tunnel can listen)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()
