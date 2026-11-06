"""SQLAlchemy 2.0 ORM models for SSH Desk."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    """Naive UTC timestamp (SQLite-friendly, consistent comparisons)."""
    from datetime import timezone

    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class ServerGroup(Base):
    __tablename__ = "server_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    color: Mapped[str | None] = mapped_column(String(9))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    servers: Mapped[list["Server"]] = relationship(back_populates="group")


class Server(Base):
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    alias: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=22)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    auth_type: Mapped[str] = mapped_column(String(16), nullable=False, default="password")
    secret_ref: Mapped[str | None] = mapped_column(Text)
    private_key_path: Mapped[str | None] = mapped_column(Text)
    default_path: Mapped[str | None] = mapped_column(Text)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("server_groups.id", ondelete="SET NULL"))
    description: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    connection_timeout: Mapped[int] = mapped_column(Integer, default=15)
    keep_alive: Mapped[int] = mapped_column(Integer, default=30)
    compression: Mapped[bool] = mapped_column(Boolean, default=False)
    forward_agent: Mapped[bool] = mapped_column(Boolean, default=False)
    custom_options: Mapped[list] = mapped_column(JSON, default=list)
    preferred_auth: Mapped[str | None] = mapped_column(String(128))
    jump_host_id: Mapped[int | None] = mapped_column(ForeignKey("servers.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    group: Mapped[Optional["ServerGroup"]] = relationship(back_populates="servers", lazy="selectin")
    jump_host: Mapped[Optional["Server"]] = relationship(remote_side=[id], lazy="selectin")
    paths: Mapped[list["ServerPath"]] = relationship(
        back_populates="server", cascade="all, delete-orphan", order_by="ServerPath.name", lazy="selectin"
    )
    commands: Mapped[list["SavedCommand"]] = relationship(
        back_populates="server", cascade="all, delete-orphan", lazy="selectin"
    )
    tunnels: Mapped[list["Tunnel"]] = relationship(back_populates="server", cascade="all, delete-orphan", lazy="selectin")
    history: Mapped[list["ConnectionHistory"]] = relationship(back_populates="server")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Server {self.alias} {self.username}@{self.host}:{self.port}>"


class ServerPath(Base):
    __tablename__ = "server_paths"
    __table_args__ = (UniqueConstraint("server_id", "name", name="uq_server_path_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    server: Mapped["Server"] = relationship(back_populates="paths")


class SSHKey(Base):
    __tablename__ = "ssh_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    private_key_path: Mapped[str] = mapped_column(Text, nullable=False)
    public_key_path: Mapped[str | None] = mapped_column(Text)
    key_type: Mapped[str] = mapped_column(String(16), default="ed25519")
    bits: Mapped[int | None] = mapped_column(Integer)
    fingerprint: Mapped[str | None] = mapped_column(String(64))
    comment: Mapped[str | None] = mapped_column(String(128))
    passphrase_ref: Mapped[str | None] = mapped_column(Text)
    stored_copy: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ConnectionHistory(Base):
    __tablename__ = "connection_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int | None] = mapped_column(ForeignKey("servers.id", ondelete="SET NULL"), index=True)
    server_alias: Mapped[str] = mapped_column(String(64), default="")
    server_name: Mapped[str] = mapped_column(String(128), default="")
    connected_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    disconnected_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(16), default="connected")  # connected|closed|failed|interrupted
    error_message: Mapped[str | None] = mapped_column(Text)

    server: Mapped[Optional["Server"]] = relationship(back_populates="history")

    @property
    def duration_seconds(self) -> int | None:
        if self.disconnected_at and self.connected_at:
            return int((self.disconnected_at - self.connected_at).total_seconds())
        return None


class SavedCommand(Base):
    __tablename__ = "saved_commands"
    __table_args__ = (UniqueConstraint("server_id", "name", name="uq_saved_command_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int | None] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    command: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(64))
    requires_confirmation: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    server: Mapped[Optional["Server"]] = relationship(back_populates="commands")


class Tunnel(Base):
    __tablename__ = "tunnels"
    __table_args__ = (UniqueConstraint("server_id", "name", name="uq_tunnel_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    tunnel_type: Mapped[str] = mapped_column(String(16), nullable=False, default="local")
    local_host: Mapped[str] = mapped_column(String(255), default="127.0.0.1")
    local_port: Mapped[int] = mapped_column(Integer, nullable=False)
    remote_host: Mapped[str | None] = mapped_column(String(255))
    remote_port: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="stopped")  # stopped|running|error
    pid: Mapped[int | None] = mapped_column(Integer)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    server: Mapped["Server"] = relationship(back_populates="tunnels")


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text)
