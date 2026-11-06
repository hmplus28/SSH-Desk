"""Parser/serializer for ~/.ssh/config (import & export support)."""

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SshConfigEntry:
    host: str
    hostname: str | None = None
    user: str | None = None
    port: int | None = None
    identity_file: str | None = None
    proxy_jump: str | None = None
    server_alive_interval: int | None = None
    compression: bool | None = None
    forward_agent: bool | None = None
    skipped_options: list = field(default_factory=list)

    @property
    def effective_hostname(self) -> str:
        return self.hostname or self.host


_TOKEN_RE = re.compile(r'''(?:^[ \t]*|(?<=[ \t]))(?: "[^"]*" | '[^']*' | [^\s"'#]+ )''', re.VERBOSE)


def _tokenize(line: str) -> list[str]:
    out = []
    for tok in _TOKEN_RE.findall(line):
        tok = tok.strip()
        if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in "\"'":
            tok = tok[1:-1]
        if tok:
            out.append(tok)
    return out


def parse_ssh_config(text: str) -> list[SshConfigEntry]:
    entries: list[SshConfigEntry] = []
    current: SshConfigEntry | None = None
    seen: set[str] = set()

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        tokens = _tokenize(raw_line)
        if len(tokens) < 2:
            continue
        key = tokens[0].lower()
        value = tokens[1]
        rest = tokens[1:]

        if key == "host":
            patterns = rest
            if any(("*" in p or "?" in p or p.startswith("!")) for p in patterns):
                current = None
                continue
            host = patterns[0]
            if host in seen:
                current = None
                continue
            seen.add(host)
            current = SshConfigEntry(host=host)
            entries.append(current)
            continue

        if current is None:
            continue

        if key == "hostname":
            current.hostname = value
        elif key == "user":
            current.user = value
        elif key == "port":
            try:
                current.port = int(value)
            except ValueError:
                current.skipped_options.append(f"Port={value}")
        elif key == "identityfile":
            current.identity_file = str(Path(value).expanduser())
        elif key == "proxyjump":
            current.proxy_jump = value
        elif key == "serveraliveinterval":
            try:
                current.server_alive_interval = int(value)
            except ValueError:
                current.skipped_options.append(f"ServerAliveInterval={value}")
        elif key == "compression":
            current.compression = value.lower() in ("yes", "true", "1")
        elif key == "forwardagent":
            current.forward_agent = value.lower() in ("yes", "true", "1")
        elif key in ("include", "match"):
            current.skipped_options.append(key.capitalize())
            if key == "match":
                current = None
        else:
            if key not in current.skipped_options:
                current.skipped_options.append(key)

    return entries


def default_ssh_config_path() -> Path:
    return Path.home() / ".ssh" / "config"
