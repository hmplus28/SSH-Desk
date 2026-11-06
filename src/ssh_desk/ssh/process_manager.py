"""Registry of long-lived processes (SSH sessions / tunnel daemons) with cleanup on exit."""

import atexit
import logging
import threading

from ssh_desk.utils.procs import terminate_tree

log = logging.getLogger("ssh_desk.process_manager")


class ProcessManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._processes: dict[int, dict] = {}
        atexit.register(self.cleanup_all)

    def register(self, pid: int, kind: str, meta: dict | None = None) -> None:
        with self._lock:
            self._processes[pid] = {"kind": kind, "meta": meta or {}}

    def unregister(self, pid: int) -> None:
        with self._lock:
            self._processes.pop(pid, None)

    def list(self) -> dict[int, dict]:
        with self._lock:
            return dict(self._processes)

    def cleanup_all(self) -> None:
        with self._lock:
            items = list(self._processes.items())
            self._processes.clear()
        for pid, info in items:
            log.info("cleaning up %s process pid=%s", info["kind"], pid)
            terminate_tree(pid)
