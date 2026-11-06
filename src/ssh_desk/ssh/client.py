"""Builds OpenSSH command lines. No secrets ever appear in argv; only safe references."""

import logging
import os
import shlex
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ssh_desk.core import constants
from ssh_desk.ssh.askpass import ensure_askpass_helper

log = logging.getLogger("ssh_desk.ssh_client")


@dataclass
class AuthContext:
    env: dict = field(default_factory=dict)
    uses_askpass: bool = False


def _known_hosts_value(ctx) -> str:
    app_file = Path(ctx.data_dir) / constants.KNOWN_HOSTS_NAME
    return f"~/.ssh/known_hosts {app_file}"


def _base_options(ctx, server) -> list[str]:
    opts = [
        "-o", "StrictHostKeyChecking=yes",
        "-o", "HashKnownHosts=yes",
        "-o", f"UserKnownHostsFile={_known_hosts_value(ctx)}",
        "-o", f"ConnectTimeout={int(server.connection_timeout or 15)}",
    ]
    keep_alive = int(server.keep_alive or 0)
    if keep_alive > 0:
        opts += ["-o", f"ServerAliveInterval={keep_alive}", "-o", "ServerAliveCountMax=3"]
    if getattr(server, "compression", False):
        opts += ["-o", "Compression=yes"]
    if getattr(server, "forward_agent", False):
        opts += ["-A"]
    for option in getattr(server, "custom_options", None) or []:
        option = str(option).strip()
        if option and not option.startswith("-"):
            opts += ["-o", option]
    if getattr(server, "preferred_auth", None):
        opts += ["-o", f"PreferredAuthentications={server.preferred_auth}"]
    return opts


def _jump_proxy_option(ctx, server) -> list[str]:
    jump_id = getattr(server, "jump_host_id", None)
    if not jump_id:
        return []
    jump = ctx.servers.get(jump_id)
    if not jump:
        return []
    wrapper = ensure_askpass_helper(ctx.data_dir)
    cmd = f"{shlex.quote(str(wrapper))} proxy {shlex.quote(jump.alias)} %h %p"
    return ["-o", f"ProxyCommand={cmd}"]


def _auth_argv(ctx, server) -> tuple[list[str], AuthContext]:
    argv: list[str] = []
    auth = AuthContext()
    auth_type = server.auth_type
    if auth_type == "password":
        ref = getattr(server, "secret_ref", None)
        if not ref:
            return argv, auth
        helper = ensure_askpass_helper(ctx.data_dir)
        auth.env = {
            "SSH_ASKPASS": str(helper),
            "SSH_ASKPASS_REQUIRE": "force",
            "DISPLAY": os.environ.get("DISPLAY", ":0"),
            constants.SECRET_REF_ENV: ref,
        }
        auth.uses_askpass = True
        argv += ["-o", "PubkeyAuthentication=no", "-o", "PreferredAuthentications=password,keyboard-interactive"]
    elif auth_type == "key":
        key_path = server.private_key_path
        if key_path:
            argv += ["-i", str(key_path), "-o", "IdentitiesOnly=yes"]
            key_ref = getattr(server, "key_passphrase_ref", None)
            if key_ref:
                helper = ensure_askpass_helper(ctx.data_dir)
                auth.env = {
                    "SSH_ASKPASS": str(helper),
                    "SSH_ASKPASS_REQUIRE": "force",
                    "DISPLAY": os.environ.get("DISPLAY", ":0"),
                    constants.SECRET_REF_ENV: key_ref,
                }
                auth.uses_askpass = True
        argv += ["-o", "PreferredAuthentications=publickey,keyboard-interactive"]
    elif auth_type == "agent":
        argv += ["-o", "IdentitiesOnly=no"]
    # interactive: no overrides, ssh falls back to its normal prompt flow
    return argv, auth


def remote_command(path: Optional[str] = None, exec_cmd: Optional[str] = None, interactive: bool = True) -> Optional[str]:
    parts: list[str] = []
    if path:
        parts.append(f"cd -- {shlex.quote(path)}")
    if exec_cmd:
        parts.append(exec_cmd)
    elif interactive and path:
        parts.append('if [ -n "$SHELL" ]; then exec "$SHELL" -l; else exec /bin/bash -l; fi')
    if not parts:
        return None
    return " && ".join(parts)


def build_connect_argv(
    ctx,
    server,
    *,
    path: Optional[str] = None,
    exec_cmd: Optional[str] = None,
    user: Optional[str] = None,
    port: Optional[int] = None,
    force_tty: bool = True,
    session_marker: bool = True,
) -> tuple[list[str], dict]:
    """Return (argv, env_additions). argv is a list -> subprocess without shell."""
    argv = ["ssh"]
    argv += _base_options(ctx, server)
    argv += _jump_proxy_option(ctx, server)
    auth_argv, auth_env = _auth_argv(ctx, server)
    argv += auth_argv

    effective_port = int(port or server.port)
    effective_user = user or server.username
    argv += ["-p", str(effective_port)]
    if force_tty:
        argv += ["-t", "-t"]
    else:
        argv += ["-T"]
    argv.append(f"{effective_user}@{server.host}")

    cmd = remote_command(path=path, exec_cmd=exec_cmd, interactive=force_tty)
    if cmd:
        argv.append(cmd)

    env = dict(auth_env.env)
    if session_marker and force_tty:
        env[constants.TERMINAL_SESSION_ENV] = uuid.uuid4().hex[:12]
        env[constants.TERMINAL_ALIAS_ENV] = server.alias
    return argv, env


def build_exec_argv(ctx, server, command: str, *, user=None, port=None) -> tuple[list[str], dict]:
    return build_connect_argv(ctx, server, exec_cmd=command, user=user, port=port, force_tty=False, session_marker=False)


def build_test_argv(ctx, server, *, user=None, port=None, password_override_ref: Optional[str] = None) -> tuple[list[str], dict]:
    argv = ["ssh"]
    argv += _base_options(ctx, server)
    argv += _jump_proxy_option(ctx, server)
    auth_argv, auth_env = _auth_argv(ctx, server)
    if password_override_ref:
        helper = ensure_askpass_helper(ctx.data_dir)
        auth_argv += ["-o", "PubkeyAuthentication=no", "-o", "PreferredAuthentications=password,keyboard-interactive"]
        auth_env = type(auth_env)(
            env={
                "SSH_ASKPASS": str(helper),
                "SSH_ASKPASS_REQUIRE": "force",
                "DISPLAY": os.environ.get("DISPLAY", ":0"),
                constants.SECRET_REF_ENV: password_override_ref,
            },
            uses_askpass=True,
        )
    argv += auth_argv
    argv += ["-p", str(int(port or server.port)), "-T", f"{user or server.username}@{server.host}", f"echo {constants.OK_MARKER}"]
    return argv, auth_env.env


def build_proxy_argv(ctx, jump_server, target_host: str, target_port: int) -> tuple[list[str], dict]:
    """Stdio proxy (ssh -W) through the jump server, with its own auth."""
    argv = ["ssh"]
    argv += _base_options(ctx, jump_server)
    argv += _jump_proxy_option(ctx, jump_server)
    auth_argv, auth_env = _auth_argv(ctx, jump_server)
    argv += auth_argv
    argv += [
        "-p", str(jump_server.port),
        "-N", "-T",
        "-o", f"ExitOnForwardFailure=yes",
        "-W", f"{target_host}:{target_port}",
        f"{jump_server.username}@{jump_server.host}",
    ]
    return argv, auth_env.env


def build_tunnel_argv(ctx, server, *, port_spec: str, user=None, port=None) -> tuple[list[str], dict]:
    argv = ["ssh"]
    argv += _base_options(ctx, server)
    argv += _jump_proxy_option(ctx, server)
    auth_argv, auth_env = _auth_argv(ctx, server)
    argv += auth_argv
    argv += [
        "-p", str(int(port or server.port)),
        "-N", "-T",
        "-o", "ExitOnForwardFailure=yes",
        port_spec,
        f"{user or server.username}@{server.host}",
    ]
    return argv, auth_env.env
