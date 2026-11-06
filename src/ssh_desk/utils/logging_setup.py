"""Logging setup with secret redaction. Secrets must never reach log files."""

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

_REDACT_RE = re.compile(r"(?i)(password|passwd|secret|passphrase|token)\s*[=:]\s*\S+")

_registered: set[str] = set()


def register_secret(value: str) -> None:
    """Register a runtime secret value so any accidental log line is redacted."""
    if value and len(value) >= 4:
        _registered.add(value)


def redact(message: str) -> str:
    out = _REDACT_RE.sub(r"\1=***", message)
    for secret in _registered:
        if secret in out:
            out = out.replace(secret, "***")
    return out


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.msg = redact(str(record.msg))
            if record.args:
                record.args = tuple(redact(str(a)) for a in record.args)
        except Exception:
            pass
        return True


def setup_logging(log_dir: Path, level: str = "INFO") -> logging.Logger:
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ssh_desk")
    logger.setLevel(getattr(logging, str(level).upper(), logging.INFO))
    logger.propagate = False
    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    file_handler = RotatingFileHandler(
        log_dir / "ssh-desk.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    file_handler.addFilter(RedactingFilter())
    logger.addHandler(file_handler)

    stream = logging.StreamHandler()
    stream.setFormatter(fmt)
    stream.addFilter(RedactingFilter())
    stream.setLevel(logging.WARNING)
    logger.addHandler(stream)
    return logger
