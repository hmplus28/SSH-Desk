"""Pydantic models validating every user input before it reaches services or argv."""

import ipaddress
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from ssh_desk.core.constants import AUTH_TYPES, TUNNEL_TYPES

ALIAS_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
# Path names are human labels: spaces and non-Latin letters (e.g. Persian) allowed.
# Forbidden: control characters, leading '-' (argv option confusion), empty/overlong.
PATH_NAME_RE = re.compile(r"^[^\x00-\x1f\x7f-][^\x00-\x1f\x7f]{0,31}$", re.UNICODE)
USERNAME_RE = re.compile(r"^[^\s:/$]{1,64}$")
HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}\Z)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)*\.?\Z",
    re.IGNORECASE,
)
TAG_RE = re.compile(r"^[\w .:@+-]{1,32}$", re.UNICODE)

AuthType = Literal["password", "key", "agent", "interactive"]


def validate_host(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Host cannot be empty")
    if value.startswith("[") and value.endswith("]"):  # IPv6 literal
        value = value[1:-1]
    try:
        ipaddress.ip_address(value)
        return value
    except ValueError:
        pass
    if HOSTNAME_RE.match(value):
        return value.rstrip(".")
    raise ValueError(f"Invalid host: {value!r} (use an IPv4/IPv6 address or a hostname)")


class ServerInput(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    alias: str = Field(min_length=1, max_length=64)
    host: str
    port: int = Field(default=22, ge=1, le=65535)
    username: str = Field(min_length=1, max_length=64)
    auth_type: AuthType = "password"
    default_path: str | None = None
    connection_timeout: int = Field(default=15, ge=1, le=600)
    keep_alive: int = Field(default=30, ge=0, le=3600)

    @field_validator("alias")
    @classmethod
    def _alias(cls, v: str) -> str:
        v = v.strip().lower()
        if not ALIAS_RE.match(v):
            raise ValueError(
                "Alias must be 1-64 chars: lowercase letters, digits, '-' or '_', starting with a letter/digit"
            )
        return v

    @field_validator("host")
    @classmethod
    def _host(cls, v: str) -> str:
        return validate_host(v)

    @field_validator("username")
    @classmethod
    def _username(cls, v: str) -> str:
        if not USERNAME_RE.match(v):
            raise ValueError("Username must be 1-64 chars without spaces, ':' , '/' or '$'")
        return v

    @field_validator("default_path")
    @classmethod
    def _default_path(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        v = v.strip()
        if not v.startswith("/"):
            raise ValueError("Default path must be an absolute path (starts with '/')")
        if "\x00" in v:
            raise ValueError("Invalid characters in path")
        return v


class PathInput(BaseModel):
    name: str
    path: str
    is_default: bool = False

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = v.strip()
        if not PATH_NAME_RE.match(v):
            raise ValueError(
                "Path name must be 1-32 visible characters (spaces and unicode letters "
                "allowed), must not start with '-'"
            )
        return v

    @field_validator("path")
    @classmethod
    def _path(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith("/"):
            raise ValueError("Saved path must be absolute (starts with '/')")
        return v


class TunnelInput(BaseModel):
    tunnel_type: Literal["local", "remote", "dynamic"]
    local_host: str = "127.0.0.1"
    local_port: int = Field(ge=1, le=65535)
    remote_host: str | None = None
    remote_port: int | None = Field(default=None, ge=1, le=65535)

    @field_validator("local_host")
    @classmethod
    def _lh(cls, v: str) -> str:
        return validate_host(v)

    @field_validator("remote_host")
    @classmethod
    def _rh(cls, v: str | None) -> str | None:
        return validate_host(v) if v else v

    @field_validator("remote_port", "remote_host")
    @classmethod
    def _require_remote(cls, v, info):
        t = info.data.get("tunnel_type")
        if t in ("local", "remote"):
            if v is None:
                raise ValueError(f"'{info.field_name}' is required for {t} forwarding")
        return v


class CommandInput(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    command: str = Field(min_length=1, max_length=4000)
    description: str = Field(default="", max_length=500)
    category: str = Field(default="", max_length=64)
    requires_confirmation: bool = False

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        if not PATH_NAME_RE.match(v):
            raise ValueError("Command name must be 1-64 chars: letters, digits, '-' or '_'")
        return v


class KeyInput(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        if not PATH_NAME_RE.match(v):
            raise ValueError("Key name must be 1-32 chars: letters, digits, '-' or '_'")
        return v


def sanitize_tags(tags: list | None) -> list:
    out = []
    for tag in tags or []:
        tag = str(tag).strip()
        if tag and TAG_RE.match(tag) and tag not in out:
            out.append(tag)
    return out[:10]


def validate_auth_type(value: str) -> str:
    if value not in AUTH_TYPES:
        raise ValueError(f"auth_type must be one of {AUTH_TYPES}")
    return value


def validate_tunnel_type(value: str) -> str:
    if value not in TUNNEL_TYPES:
        raise ValueError(f"tunnel_type must be one of {TUNNEL_TYPES}")
    return value
