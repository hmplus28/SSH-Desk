"""Import from ~/.ssh/config, TOML export and full backup/restore (secrets stay opt-in)."""

import logging
from dataclasses import dataclass
from pathlib import Path

from ssh_desk.core.exceptions import ConfigError, NotFoundError
from ssh_desk.ssh.config_manager import default_ssh_config_path, parse_ssh_config
from ssh_desk.utils.validation import PathInput, ServerInput

try:
    import tomllib
except ImportError:  # pragma: no cover
    tomllib = None

try:
    import tomli_w
except ImportError:  # pragma: no cover
    tomli_w = None

log = logging.getLogger("ssh_desk.transfer")


@dataclass
class ImportRow:
    entry: object
    alias: str
    exists: bool
    selected: bool = True


class TransferService:
    def __init__(self, ctx):
        self.ctx = ctx

    # ------------------------------------------------------------------ ssh config import
    def preview_ssh_config(self, path: str | None = None) -> list[ImportRow]:
        config_path = Path(path).expanduser() if path else default_ssh_config_path()
        if not config_path.exists():
            raise NotFoundError(f"SSH config not found: {config_path}")
        entries = parse_ssh_config(config_path.read_text(errors="replace"))
        rows = []
        for entry in entries:
            alias = self._unique_alias(entry.host)
            exists = self._matches_existing(entry)
            rows.append(ImportRow(entry=entry, alias=alias, exists=exists))
        return rows

    def _matches_existing(self, entry) -> bool:
        host = entry.effective_hostname
        for server in self.ctx.servers.list_servers():
            if server.host == host and (entry.user in (None, server.username)) and (
                entry.port in (None, server.port)
            ):
                return True
        return False

    def _unique_alias(self, host: str) -> str:
        base = "".join(c if c.isalnum() or c in "-_" else "-" for c in host.lower()).strip("-")
        base = base or "server"
        existing = {s.alias for s in self.ctx.servers.list_servers()}
        candidate, counter = base, 2
        while candidate in existing or len(candidate) > 64:
            candidate = f"{base}{counter}"
            counter += 1
        return candidate

    def apply_ssh_import(self, rows: list[ImportRow]) -> dict:
        created, skipped = 0, 0
        for row in rows:
            if not row.selected:
                skipped += 1
                continue
            entry = row.entry
            auth_type = "interactive"
            private_key_path = None
            if entry.identity_file and Path(entry.identity_file).exists():
                auth_type = "key"
                private_key_path = entry.identity_file
                if not self.ctx.keys.get_by_path(private_key_path):
                    try:
                        self.ctx.keys.import_key(
                            name=self._unique_key_name(entry.host), private_path=private_key_path
                        )
                    except Exception as exc:  # key unreadable -> fall back to interactive auth
                        log.warning("key import failed for %s: %s", private_key_path, exc)
                        auth_type, private_key_path = "interactive", None
            data = ServerInput(
                name=entry.host,
                alias=row.alias,
                host=entry.effective_hostname,
                port=entry.port or 22,
                username=entry.user or "root",
                auth_type=auth_type,
                default_path=None,
                keep_alive=entry.server_alive_interval or 30,
            )
            if row.exists:
                skipped += 1
                continue
            self.ctx.servers.create(
                data,
                private_key_path=private_key_path,
                compression=entry.compression or False,
                forward_agent=entry.forward_agent or False,
            )
            created += 1
        return {"created": created, "skipped": skipped}

    def _unique_key_name(self, host: str) -> str:
        existing = {k.name for k in self.ctx.keys.list()}
        base = f"{host[:24]}-key"
        candidate, counter = base, 2
        while candidate in existing:
            candidate = f"{base}{counter}"
            counter += 1
        return candidate

    # ------------------------------------------------------------------ export / backup
    def export_toml(self, path: str, *, include_secrets=False, include_history=False) -> dict:
        if tomli_w is None:  # pragma: no cover
            raise ConfigError("tomli-w is required for export")
        doc: dict = {"version": 1}
        servers_out = []
        for server in self.ctx.servers.list_servers():
            item = {
                "name": server.name,
                "alias": server.alias,
                "host": server.host,
                "port": server.port,
                "username": server.username,
                "auth_type": server.auth_type,
                "default_path": server.default_path or "",
                "description": server.description or "",
                "tags": list(server.tags or []),
                "favorite": server.favorite,
                "compression": server.compression,
                "forward_agent": server.forward_agent,
                "custom_options": list(server.custom_options or []),
                "preferred_auth": server.preferred_auth or "",
                "connection_timeout": server.connection_timeout,
                "keep_alive": server.keep_alive,
                "private_key_path": server.private_key_path or "",
                "group": server.group.name if server.group else "",
            }
            item["paths"] = [
                {"name": p.name, "path": p.path, "is_default": p.is_default} for p in server.paths
            ]
            item["commands"] = [
                {
                    "name": c.name,
                    "command": c.command,
                    "description": c.description or "",
                    "category": c.category or "",
                    "requires_confirmation": c.requires_confirmation,
                }
                for c in server.commands
            ]
            if include_secrets and server.auth_type == "password":
                try:
                    item["_password"] = self.ctx.credentials.get_server_password(server)
                except Exception:
                    log.warning("secret unavailable for %s during export", server.alias)
            servers_out.append(item)
        doc["servers"] = servers_out
        doc["groups"] = [
            {"name": g.name, "color": g.color or "", "description": g.description or ""}
            for g in self.ctx.servers.list_groups()
        ]
        doc["commands_global"] = [
            {
                "name": c.name,
                "command": c.command,
                "description": c.description or "",
                "category": c.category or "",
                "requires_confirmation": c.requires_confirmation,
            }
            for c in self.ctx.servers.list_commands(server_id=None)
        ]
        doc["keys"] = [
            {
                "name": k.name,
                "private_key_path": k.private_key_path,
                "public_key_path": k.public_key_path or "",
                "key_type": k.key_type,
                "fingerprint": k.fingerprint or "",
            }
            for k in self.ctx.keys.list()
        ]
        if include_history:
            doc["history"] = [
                {
                    "server_alias": h.server_alias,
                    "connected_at": h.connected_at.isoformat(),
                    "disconnected_at": h.disconnected_at.isoformat() if h.disconnected_at else "",
                    "status": h.status,
                    "error_message": h.error_message or "",
                }
                for h in self.ctx.history.list(limit=10000)
            ]
        out = Path(path).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "wb") as fh:
            tomli_w.dump(doc, fh)
        out.chmod(0o600)
        return {"file": str(out), "servers": len(servers_out)}

    # ------------------------------------------------------------------ import / restore
    def import_toml(self, path: str, *, restore_secrets=True) -> dict:
        if tomllib is None:  # pragma: no cover
            raise ConfigError("Python 3.11+ (tomllib) is required")
        source = Path(path).expanduser()
        if not source.exists():
            raise NotFoundError(f"Backup file not found: {source}")
        with open(source, "rb") as fh:
            doc = tomllib.load(fh)
        report = {"groups": 0, "servers": 0, "skipped": 0, "secrets": 0, "keys": 0, "commands": 0}

        group_map = {}
        for group in doc.get("groups", []):
            try:
                obj = self.ctx.servers.create_group(group["name"], group.get("color", ""), group.get("description", ""))
                group_map[group["name"]] = obj.id
                report["groups"] += 1
            except Exception:
                group_map[group["name"]] = next(
                    (g.id for g in self.ctx.servers.list_groups() if g.name == group["name"]), None
                )

        # restore key registry entries (files are referenced, not copied)
        from ssh_desk.database.models import SSHKey

        for key in doc.get("keys", []):
            if self.ctx.keys.get_by_path(key["private_key_path"]) or any(
                k.name == key["name"] for k in self.ctx.keys.list()
            ):
                continue
            with self.ctx.db.session() as session:
                session.add(SSHKey(
                    name=key["name"],
                    private_key_path=key["private_key_path"],
                    public_key_path=key.get("public_key_path") or None,
                    key_type=key.get("key_type", "unknown"),
                    fingerprint=key.get("fingerprint") or None,
                ))
                session.commit()
            report["keys"] += 1

        for item in doc.get("servers", []):
            if self.ctx.servers.get_by_alias(item["alias"]):
                report["skipped"] += 1
                continue
            data = ServerInput(
                name=item.get("name") or item["alias"],
                alias=item["alias"],
                host=item["host"],
                port=int(item.get("port", 22)),
                username=item.get("username", "root"),
                auth_type=item.get("auth_type", "interactive"),
                default_path=item.get("default_path") or None,
                connection_timeout=int(item.get("connection_timeout", 15)),
                keep_alive=int(item.get("keep_alive", 30)),
            )
            password = item.get("_password") if restore_secrets else None
            server = self.ctx.servers.create(
                data,
                group_id=group_map.get(item.get("group", "")),
                secret=password if password else None,
                private_key_path=item.get("private_key_path") or None,
                description=item.get("description", ""),
                tags=list(item.get("tags", [])),
                favorite=bool(item.get("favorite", False)),
                compression=bool(item.get("compression", False)),
                forward_agent=bool(item.get("forward_agent", False)),
                custom_options=list(item.get("custom_options", [])),
                preferred_auth=item.get("preferred_auth") or None,
                paths=[PathInput(name=p["name"], path=p["path"], is_default=bool(p.get("is_default"))) for p in item.get("paths", [])],
            )
            report["servers"] += 1
            if password:
                report["secrets"] += 1
            for cmd in item.get("commands", []):
                try:
                    self.ctx.servers.create_command(
                        type(
                            "C",
                            (),
                            {
                                "name": cmd["name"],
                                "command": cmd["command"],
                                "description": cmd.get("description", ""),
                                "category": cmd.get("category", ""),
                                "requires_confirmation": bool(cmd.get("requires_confirmation")),
                            },
                        )(),
                        server_id=server.id,
                    )
                    report["commands"] += 1
                except Exception:
                    pass

        for cmd in doc.get("commands_global", []):
            try:
                self.ctx.servers.create_command(
                    type(
                        "C",
                        (),
                        {
                            "name": cmd["name"],
                            "command": cmd["command"],
                            "description": cmd.get("description", ""),
                            "category": cmd.get("category", ""),
                            "requires_confirmation": bool(cmd.get("requires_confirmation")),
                        },
                    )(),
                    server_id=None,
                )
                report["commands"] += 1
            except Exception:
                pass
        return report
