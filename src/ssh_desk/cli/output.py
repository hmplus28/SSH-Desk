"""CLI output helpers: ANSI colors, readable tables, exit codes."""

import os
import sys

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
CYAN = "\033[36m"


def _enabled() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


def paint(text: str, color: str) -> str:
    if not _enabled():
        return text
    return f"{color}{text}{RESET}"


def ok(message: str) -> None:
    print(paint("✔ ", GREEN) + message)


def warn(message: str) -> None:
    print(paint("⚠ ", YELLOW) + message)


def err(message: str) -> None:
    print(paint("✘ ", RED) + message, file=sys.stderr)


def info(message: str) -> None:
    print(paint("• ", CYAN) + message)


def hint(message: str) -> None:
    print(paint(message, DIM))


def fmt_table(headers: list[str], rows: list[list[str]], indent: str = "  ") -> str:
    """Render a plain-text table with computed column widths."""
    rows = [[("" if c is None else str(c)) for c in row] for row in rows]
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    line = indent + "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    separator = indent + "  ".join("-" * w for w in widths)
    body = [indent + "  ".join(c.ljust(widths[i]) for i, c in enumerate(row)) for row in rows]
    return "\n".join([line, separator, *body])


def fmt_duration(seconds) -> str:
    if seconds is None:
        return "-"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {sec:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


def fmt_bool(value: bool) -> str:
    return "yes" if value else "no"
