"""Application context shared by GUI and CLI (single source of truth)."""

import logging
import os
from pathlib import Path
from typing import Any, Optional

from ssh_desk.core.config import AppConfig
from ssh_desk.core.constants import (
    CLI_WRAPPER_NAME,
    DB_FILE_NAME,
    KNOWN_HOSTS_NAME,
    default_config_dir,
    default_data_dir,
)
from ssh_desk.core.events import EventBus
from ssh_desk.database.database import Database
from ssh_desk.ssh.askpass import ensure_askpass_helper
from ssh_desk.ssh.process_manager import ProcessManager
from ssh_desk.utils.logging_setup import setup_logging

log = logging.getLogger("ssh_desk.app")


class AppContext:
    _instance: Optional["AppContext"] = None

    def __init__(
        self,
        data_dir: Path | None = None,
        config_dir: Path | None = None,
        db_path: Path | None = None,
        secret_store=None,
        quiet_logs: bool = False,
    ):
        self.data_dir = Path(data_dir or default_data_dir())
        self.config_dir = Path(config_dir or default_config_dir())
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "logs").mkdir(parents=True, exist_ok=True)

        self.settings = AppConfig(self.config_dir / "config.toml")
        setup_logging(self.data_dir / "logs", self.settings.get("log_level", "INFO"))
        if quiet_logs:
            logging.getLogger("ssh_desk").setLevel(logging.WARNING)

        self.events = EventBus()
        self.process_manager = ProcessManager()
        self.db = Database(db_path or (self.data_dir / DB_FILE_NAME))
        self.db.init()
        # ensure known_hosts exists with safe permissions
        kh = self.data_dir / KNOWN_HOSTS_NAME
        if not kh.exists():
            kh.touch()
        try:
            kh.chmod(0o600)
        except OSError:
            pass
        ensure_askpass_helper(self.data_dir, CLI_WRAPPER_NAME)

        self._secret_store = secret_store
        self._services: dict[str, Any] = {}

    # ------------------------------------------------------------- singleton
    @classmethod
    def instance(cls, **kwargs) -> "AppContext":
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    # ------------------------------------------------------------- services
    @property
    def credentials(self):
        return self._get("credentials", self._make_credentials)

    def _make_credentials(self):
        from ssh_desk.services.credential_service import CredentialService

        return CredentialService(self, store=self._secret_store)

    @property
    def servers(self):
        return self._get("servers", lambda: _import("server_service", "ServerService")(self))

    @property
    def history(self):
        return self._get("history", lambda: _import("history_service", "HistoryService")(self))

    @property
    def keys(self):
        return self._get("keys", lambda: _import("key_service", "KeyService")(self))

    @property
    def connections(self):
        return self._get("connections", lambda: _import("connection_service", "ConnectionService")(self))

    @property
    def tunnels(self):
        return self._get("tunnels", lambda: _import("tunnel_service", "TunnelService")(self))

    @property
    def sftp(self):
        return self._get("sftp", lambda: _import("sftp_service", "SftpService")(self))

    @property
    def transfer(self):
        return self._get("transfer", lambda: _import("import_export_service", "TransferService")(self))

    def _get(self, name, factory):
        if name not in self._services:
            self._services[name] = factory()
        return self._services[name]

    # ------------------------------------------------------------- lifecycle
    def shutdown(self) -> None:
        try:
            if "sftp" in self._services:
                self._services["sftp"].disconnect_all()
        except Exception:
            pass
        try:
            self.db.dispose()
        except Exception:
            pass
        log.info("application context shut down")


def _import(module_name: str, class_name: str):
    import importlib

    module = importlib.import_module(f"ssh_desk.services.{module_name}")
    return getattr(module, class_name)


def ensure_data_safety(ctx: "AppContext") -> None:
    """Best-effort hardening of file permissions."""
    for path in (ctx.config_dir / "config.toml", ctx.data_dir):
        try:
            if path.is_file():
                os.chmod(path, 0o600)
            elif path.is_dir():
                os.chmod(path, 0o700)
        except OSError:
            pass
