"""TOML configuration (source of truth for user preferences) with safe defaults."""

import re
from pathlib import Path

import tomllib

from ssh_desk.core.exceptions import ConfigError

try:
    import tomli_w
except ImportError:  # pragma: no cover
    tomli_w = None

DEFAULTS = {
    "theme": "dark",
    "language": "en",
    "default_port": 22,
    "connect_timeout": 15,
    "keep_alive": 30,
    "terminal_font_size": 11,
    "terminal_font_family": "monospace",
    "cli_command_name": "sss",
    "start_page": "dashboard",
    "log_level": "INFO",
    "confirm_dangerous_commands": True,
    "clear_clipboard_after": 30,
}

CLI_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")


class AppConfig:
    """Typed access over config.toml. Unknown keys are preserved."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                with open(self.path, "rb") as fh:
                    self._data = tomllib.load(fh)
            except Exception as exc:  # corrupted file -> keep defaults, surface message
                raise ConfigError(f"Cannot parse config file {self.path}: {exc}") from exc
        else:
            self._data = {}
        for key, value in DEFAULTS.items():
            self._data.setdefault(key, value)
        self.save()

    def save(self) -> None:
        if tomli_w is None:  # pragma: no cover
            raise ConfigError("tomli-w package is required to save configuration")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "wb") as fh:
            tomli_w.dump(self._data, fh)
        try:
            self.path.chmod(0o600)
        except OSError:
            pass

    def get(self, key: str, default=None):
        return self._data.get(key, DEFAULTS.get(key, default))

    def set(self, key: str, value) -> None:
        self._data[key] = value
        self.save()

    def as_dict(self) -> dict:
        return dict(self._data)

    @property
    def cli_command_name(self) -> str:
        name = str(self.get("cli_command_name", "sss"))
        return name if CLI_NAME_RE.match(name) else "sss"
