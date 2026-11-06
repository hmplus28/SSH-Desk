"""Server CRUD, groups, saved paths, saved commands, dashboard stats."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from ssh_desk.core.events import TOPIC_COMMANDS, TOPIC_SERVERS
from ssh_desk.core.exceptions import AliasExistsError, NotFoundError, PathNotFoundError
from ssh_desk.database.models import ConnectionHistory, SavedCommand, Server, ServerGroup, ServerPath, Tunnel
from ssh_desk.utils.procs import list_sessions
from ssh_desk.utils.validation import CommandInput, PathInput, ServerInput, sanitize_tags

log = logging.getLogger("ssh_desk.servers")


class ServerService:
    def __init__(self, ctx):
        self.ctx = ctx

    # ------------------------------------------------------------------ CRUD
    def create(
        self,
        data: ServerInput,
        *,
        group_id: Optional[int] = None,
        jump_host_id: Optional[int] = None,
        secret: Optional[str] = None,
        private_key_path: Optional[str] = None,
        description: str = "",
        tags: Optional[list] = None,
        favorite: bool = False,
        compression: bool = False,
        forward_agent: bool = False,
        custom_options: Optional[list] = None,
        preferred_auth: Optional[str] = None,
        paths: Optional[list[PathInput]] = None,
    ) -> Server:
        with self.ctx.db.session() as session:
            self._ensure_alias_free(session, data.alias)
            server = Server(
                name=data.name,
                alias=data.alias,
                host=data.host,
                port=data.port,
                username=data.username,
                auth_type=data.auth_type,
                default_path=data.default_path,
                group_id=group_id,
                jump_host_id=jump_host_id,
                description=description,
                tags=sanitize_tags(tags),
                favorite=favorite,
                connection_timeout=data.connection_timeout,
                keep_alive=data.keep_alive,
                compression=compression,
                forward_agent=forward_agent,
                custom_options=list(custom_options or []),
                preferred_auth=preferred_auth,
                private_key_path=private_key_path,
            )
            session.add(server)
            session.flush()
            self._apply_secret(server, secret)
            if paths:
                self._write_paths(session, server, paths)
            try:
                session.commit()
            except IntegrityError as exc:
                raise AliasExistsError(f"Alias '{data.alias}' already exists") from exc
            server = session.scalars(select(Server).where(Server.id == server.id)).one()
            self.ctx.events.publish(TOPIC_SERVERS, {"action": "create", "id": server.id})
            log.info("server created: %s (%s:%s)", server.alias, server.host, server.port)
            return server

    def update(
        self,
        server_id: int,
        data: ServerInput,
        *,
        group_id=...,
        jump_host_id=...,
        secret: Optional[str] = None,
        private_key_path=...,
        description=...,
        tags=...,
        favorite=...,
        compression=...,
        forward_agent=...,
        custom_options=...,
        preferred_auth=...,
        paths: Optional[list[PathInput]] = None,
    ) -> Server:
        with self.ctx.db.session() as session:
            server = session.get(Server, server_id)
            if not server:
                raise NotFoundError(f"Server id={server_id} not found")
            if data.alias != server.alias:
                self._ensure_alias_free(session, data.alias, exclude_id=server_id)
            server.name = data.name
            server.alias = data.alias
            server.host = data.host
            server.port = data.port
            server.username = data.username
            old_auth = server.auth_type
            server.auth_type = data.auth_type
            server.default_path = data.default_path
            server.connection_timeout = data.connection_timeout
            server.keep_alive = data.keep_alive
            if group_id is not ...:
                server.group_id = group_id
            if jump_host_id is not ...:
                if jump_host_id == server_id:
                    raise ValueError("A server cannot be its own jump host")
                server.jump_host_id = jump_host_id
            if description is not ...:
                server.description = description
            if tags is not ...:
                server.tags = sanitize_tags(tags)
            if favorite is not ...:
                server.favorite = favorite
            if compression is not ...:
                server.compression = compression
            if forward_agent is not ...:
                server.forward_agent = forward_agent
            if custom_options is not ...:
                server.custom_options = list(custom_options or [])
            if preferred_auth is not ...:
                server.preferred_auth = preferred_auth
            if private_key_path is not ...:
                server.private_key_path = private_key_path
            self._apply_secret(server, secret, old_auth=old_auth)
            if paths is not None:
                for p in list(server.paths):
                    session.delete(p)
                session.flush()
                self._write_paths(session, server, paths)
            try:
                session.commit()
            except IntegrityError as exc:
                raise AliasExistsError(f"Alias '{data.alias}' already exists") from exc
            server = session.scalars(select(Server).where(Server.id == server.id)).one()
            self.ctx.events.publish(TOPIC_SERVERS, {"action": "update", "id": server.id})
            log.info("server updated: %s", server.alias)
            return server

    def delete(self, server_id: int) -> None:
        with self.ctx.db.session() as session:
            server = session.get(Server, server_id)
            if not server:
                raise NotFoundError(f"Server id={server_id} not found")
            # detach tunnels referencing other servers' jump settings
            for other in session.scalars(select(Server).where(Server.jump_host_id == server_id)):
                other.jump_host_id = None
            self.ctx.credentials.delete_server_secret(server)
            session.delete(server)
            session.commit()
        self.ctx.events.publish(TOPIC_SERVERS, {"action": "delete", "id": server_id})
        log.info("server deleted: id=%s", server_id)

    def duplicate(self, server_id: int) -> Server:
        src = self.get(server_id)
        password = None
        if src.auth_type == "password" and src.secret_ref:
            password = self.ctx.credentials.get_server_password(src)
        alias = src.alias
        with self.ctx.db.session() as session:
            existing = {a for (a,) in session.execute(select(Server.alias))}
        base = f"{alias}-copy"
        candidate = base
        counter = 2
        while candidate in existing:
            candidate = f"{base}{counter}"
            counter += 1
        data = ServerInput(
            name=f"{src.name} (copy)",
            alias=candidate,
            host=src.host,
            port=src.port,
            username=src.username,
            auth_type=src.auth_type,
            default_path=src.default_path,
            connection_timeout=src.connection_timeout,
            keep_alive=src.keep_alive,
        )
        dup = self.create(
            data,
            group_id=src.group_id,
            jump_host_id=src.jump_host_id,
            secret=password,
            private_key_path=src.private_key_path,
            description=src.description or "",
            tags=list(src.tags or []),
            compression=src.compression,
            forward_agent=src.forward_agent,
            custom_options=list(src.custom_options or []),
            preferred_auth=src.preferred_auth,
            paths=[PathInput(name=p.name, path=p.path, is_default=p.is_default) for p in src.paths],
        )
        # duplicate saved commands too
        for cmd in self.list_commands(server_id=src.id):
            self.create_command(
                CommandInput(
                    name=cmd.name,
                    command=cmd.command,
                    description=cmd.description or "",
                    category=cmd.category or "",
                    requires_confirmation=cmd.requires_confirmation,
                ),
                server_id=dup.id,
            )
        return dup

    # ------------------------------------------------------------------ queries
    def get(self, server_id: int) -> Server:
        with self.ctx.db.session() as session:
            server = session.get(Server, server_id)
            if not server:
                raise NotFoundError(f"Server id={server_id} not found")
            return server

    def get_by_alias(self, alias: str) -> Optional[Server]:
        with self.ctx.db.session() as session:
            return session.scalars(
                select(Server).where(Server.alias == alias.strip().lower())
            ).first()

    def require_by_alias(self, alias: str) -> Server:
        server = self.get_by_alias(alias)
        if not server:
            with self.ctx.db.session() as session:
                aliases = [a for (a,) in session.execute(select(Server.alias))]
            close = [a for a in aliases if alias.lower() in a or a in alias.lower()]
            hint = f"Did you mean: {', '.join(close[:5])}?" if close else "Run 'list' to see servers."
            raise NotFoundError(f"Server '{alias}' not found", hint=hint)
        return server

    def list_servers(self, *, search: str = "", group_id=None, favorites_only=False, sort: str = "name") -> list[Server]:
        with self.ctx.db.session() as session:
            query = select(Server)
            if search:
                like = f"%{search.lower()}%"
                query = query.where(
                    or_(
                        Server.alias.like(like),
                        Server.name.like(like),
                        Server.host.like(like),
                        Server.username.like(like),
                        Server.description.like(like),
                    )
                )
            if group_id is not None:
                query = query.where(Server.group_id == group_id)
            if favorites_only:
                query = query.where(Server.favorite.is_(True))
            order = {
                "name": Server.name,
                "alias": Server.alias,
                "host": Server.host,
                "recent": Server.updated_at.desc(),
            }.get(sort, Server.name)
            query = query.order_by(order)
            return list(session.scalars(query))

    def toggle_favorite(self, server_id: int) -> Server:
        with self.ctx.db.session() as session:
            server = session.get(Server, server_id)
            if not server:
                raise NotFoundError("Server not found")
            server.favorite = not server.favorite
            session.commit()
            server = session.scalars(select(Server).where(Server.id == server_id)).one()
        self.ctx.events.publish(TOPIC_SERVERS, {"action": "update", "id": server_id})
        return server

    # ------------------------------------------------------------------ groups
    def list_groups(self) -> list[ServerGroup]:
        with self.ctx.db.session() as session:
            return list(session.scalars(select(ServerGroup).order_by(ServerGroup.name)))

    def create_group(self, name: str, color: str = "", description: str = "") -> ServerGroup:
        name = name.strip()
        if not name:
            raise ValueError("Group name is required")
        with self.ctx.db.session() as session:
            exists = session.scalars(select(ServerGroup).where(ServerGroup.name == name)).first()
            if exists:
                raise AliasExistsError(f"Group '{name}' already exists")
            group = ServerGroup(name=name, color=color, description=description)
            session.add(group)
            session.commit()
            session.refresh(group)
        self.ctx.events.publish(TOPIC_SERVERS, {"action": "group"})
        return group

    def delete_group(self, group_id: int) -> None:
        with self.ctx.db.session() as session:
            group = session.get(ServerGroup, group_id)
            if group:
                session.delete(group)
                session.commit()
        self.ctx.events.publish(TOPIC_SERVERS, {"action": "group"})

    # ------------------------------------------------------------------ paths
    def _write_paths(self, session, server: Server, paths: list[PathInput]) -> None:
        seen = set()
        for item in paths:
            if item.name in seen:
                raise ValueError(f"Duplicate path name: {item.name}")
            seen.add(item.name)
        has_default = any(p.is_default for p in paths)
        if not has_default and paths:
            paths = [PathInput(name=p.name, path=p.path, is_default=(p.name == paths[0].name)) for p in paths]
        for item in paths:
            session.add(ServerPath(server_id=server.id, name=item.name, path=item.path, is_default=item.is_default))

    def set_paths(self, server_id: int, paths: list[PathInput]) -> Server:
        with self.ctx.db.session() as session:
            server = session.get(Server, server_id)
            if not server:
                raise NotFoundError("Server not found")
            for p in list(server.paths):
                session.delete(p)
            session.flush()
            self._write_paths(session, server, paths)
            session.commit()
            server = session.scalars(select(Server).where(Server.id == server_id)).one()
        self.ctx.events.publish(TOPIC_SERVERS, {"action": "update", "id": server_id})
        return server

    def resolve_target(self, server: Server, target: Optional[str]) -> Optional[str]:
        """Resolve CLI path argument: None -> default, name -> saved path, /abs -> itself."""
        if target is None or target == "":
            return server.default_path
        if target.startswith("/"):
            return target
        for path in server.paths:
            if path.name == target:
                return path.path
        available = ", ".join(p.name for p in server.paths) or "none"
        raise PathNotFoundError(
            f"Path '{target}' is not defined for server '{server.alias}'",
            hint=f"Available saved paths: {available}. You can also pass an absolute path starting with '/'.",
        )

    # ------------------------------------------------------------------ commands
    def list_commands(self, server_id: Optional[int] = "any") -> list[SavedCommand]:
        with self.ctx.db.session() as session:
            query = select(SavedCommand).order_by(SavedCommand.category, SavedCommand.name)
            if server_id == "any":
                return list(session.scalars(query))
            if server_id is None:
                query = query.where(SavedCommand.server_id.is_(None))
            else:
                query = query.where(SavedCommand.server_id == server_id)
            return list(session.scalars(query))

    def create_command(self, data: CommandInput, server_id: Optional[int] = None) -> SavedCommand:
        with self.ctx.db.session() as session:
            exists = session.scalars(
                select(SavedCommand).where(SavedCommand.name == data.name, SavedCommand.server_id == server_id)
            ).first()
            if exists:
                raise AliasExistsError(f"Command '{data.name}' already exists")
            cmd = SavedCommand(
                server_id=server_id,
                name=data.name,
                command=data.command,
                description=data.description,
                category=data.category,
                requires_confirmation=data.requires_confirmation,
            )
            session.add(cmd)
            session.commit()
            session.refresh(cmd)
        self.ctx.events.publish(TOPIC_COMMANDS, {"action": "create"})
        return cmd

    def update_command(self, command_id: int, data: CommandInput, server_id: Optional[int] = None) -> SavedCommand:
        with self.ctx.db.session() as session:
            cmd = session.get(SavedCommand, command_id)
            if not cmd:
                raise NotFoundError("Command not found")
            cmd.name, cmd.command = data.name, data.command
            cmd.description, cmd.category = data.description, data.category
            cmd.requires_confirmation = data.requires_confirmation
            cmd.server_id = server_id
            session.commit()
            session.refresh(cmd)
        self.ctx.events.publish(TOPIC_COMMANDS, {"action": "update"})
        return cmd

    def delete_command(self, command_id: int) -> None:
        with self.ctx.db.session() as session:
            cmd = session.get(SavedCommand, command_id)
            if cmd:
                session.delete(cmd)
                session.commit()
        self.ctx.events.publish(TOPIC_COMMANDS, {"action": "delete"})

    # ------------------------------------------------------------------ stats
    def stats(self) -> dict:
        with self.ctx.db.session() as session:
            total = len(list(session.scalars(select(Server.id))))
            favorites = len(list(session.scalars(select(Server.id).where(Server.favorite.is_(True)))))
            tunnels_running = len(list(session.scalars(select(Tunnel.id).where(Tunnel.status == "running"))))
        active_sessions = len(list_sessions())
        return {
            "total_servers": total,
            "favorites": favorites,
            "active_sessions": active_sessions,
            "tunnels_running": tunnels_running,
        }

    def recent_servers(self, limit: int = 5) -> list[Server]:
        with self.ctx.db.session() as session:
            rows = session.execute(
                select(Server).order_by(Server.updated_at.desc()).limit(limit)
            ).scalars().all()
            return list(rows)

    def last_connection(self, server_id: int) -> Optional[ConnectionHistory]:
        with self.ctx.db.session() as session:
            return session.scalars(
                select(ConnectionHistory)
                .where(ConnectionHistory.server_id == server_id)
                .order_by(ConnectionHistory.connected_at.desc())
                .limit(1)
            ).first()

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _ensure_alias_free(session, alias: str, exclude_id: Optional[int] = None) -> None:
        query = select(Server).where(Server.alias == alias)
        if exclude_id:
            query = query.where(Server.id != exclude_id)
        if session.scalars(query).first():
            raise AliasExistsError(f"Alias '{alias}' already exists. Aliases must be unique.")

    def _apply_secret(self, server: Server, secret: Optional[str], old_auth: Optional[str] = None) -> None:
        """Store/delete the keyring secret according to the (new) auth type."""
        if secret:
            server.secret_ref = self.ctx.credentials.store_server_password(server.id, server.alias, secret)
        if server.auth_type != "password":
            self.ctx.credentials.delete_server_secret(server)
            server.secret_ref = None
