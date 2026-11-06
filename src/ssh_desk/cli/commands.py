"""SSH Desk CLI - Typer application with alias shortcuts (`sss prod nginx`)."""

import logging
import os
import shutil
import sys

import typer

from ssh_desk import __version__
from ssh_desk.cli.output import (
    BOLD,
    CYAN,
    DIM,
    GREEN,
    RED,
    err,
    fmt_bool,
    fmt_duration,
    fmt_table,
    hint,
    info,
    ok,
    paint,
    warn,
)
from ssh_desk.core.exceptions import SshDeskError

log = logging.getLogger("ssh_desk.cli")

APP_COMMANDS = {
    "list", "add", "info", "test", "edit", "delete", "connect", "search",
    "history", "current", "config", "tunnel", "keys", "import", "export",
    "backup", "restore", "version", "install-cli", "uninstall-data",
    "proxy", "__complete",
}

app = typer.Typer(
    name="ssh-desk-cli",
    help="SSH Desk CLI - manage and connect to your servers by alias.",
    no_args_is_help=False,
    add_completion=False,
    pretty_exceptions_enable=False,
)

_ctx = None


def get_ctx():
    global _ctx
    if _ctx is None:
        from ssh_desk.core.application import AppContext

        _ctx = AppContext.instance()
    return _ctx


def set_ctx(ctx) -> None:
    global _ctx
    _ctx = ctx


# ===================================================================== list
@app.command("list")
def list_cmd(
    group: str | None = typer.Option(None, "--group", help="Filter by group name"),
    favorites: bool = typer.Option(False, "--favorites", "--fav", help="Only favorites"),
    search: str = typer.Option("", "--search", help="Search text"),
):
    """List all servers."""
    ctx = get_ctx()
    group_id = None
    if group:
        obj = next((g for g in ctx.servers.list_groups() if g.name == group), None)
        if not obj:
            err(f"Group '{group}' not found")
            raise typer.Exit(1)
        group_id = obj.id
    servers = ctx.servers.list_servers(search=search, group_id=group_id, favorites_only=favorites)
    if not servers:
        info("No servers yet. Add one with: sss add")
        return
    active = {s["alias"] for s in _session_scan()}
    rows = [
        [
            "*" if s.favorite else "",
            s.alias,
            s.name,
            s.host,
            s.port,
            s.username,
            s.group.name if s.group else "-",
            s.auth_type,
            paint("connected", GREEN) if s.alias in active else "-",
        ]
        for s in servers
    ]
    print(fmt_table(["FAV", "ALIAS", "NAME", "HOST", "PORT", "USER", "GROUP", "AUTH", "STATUS"], rows))


def _session_scan():
    from ssh_desk.utils.procs import list_sessions

    return list_sessions()


# ===================================================================== add
@app.command()
def add(
    alias: str | None = typer.Option(None, "--alias", "-a", help="Unique alias (used as `sss <alias>`)"),
    host: str | None = typer.Option(None, "--host", help="IP or hostname"),
    user: str | None = typer.Option(None, "--user", "-u", help="SSH username"),
    port: int | None = typer.Option(None, "--port", "-p", help="SSH port"),
    name: str | None = typer.Option(None, "--name", help="Display name"),
    auth: str | None = typer.Option(None, "--auth", help="password | key | agent | interactive"),
    key: str | None = typer.Option(None, "--key", help="Private key path (auth=key)"),
    group: str | None = typer.Option(None, "--group", help="Group name (created if missing)"),
    path: str | None = typer.Option(None, "--path", help="Default remote path"),
    description: str = typer.Option("", "--description", help="Description"),
    tags: str = typer.Option("", "--tags", help="Comma separated tags"),
    timeout: int | None = typer.Option(None, "--timeout", help="Connection timeout (s)"),
):
    """Add a new server (interactive when options are missing)."""
    ctx = get_ctx()
    if not alias:
        alias = typer.prompt("Alias (unique, e.g. prod)")
    if not host:
        host = typer.prompt("Host (IP or domain)")
    if not user:
        user = typer.prompt("Username", default="root")
    if not name:
        name = alias
    if port is None:
        port = int(typer.prompt("Port", default=ctx.settings.get("default_port", 22)))
    if not auth:
        auth = typer.prompt("Auth type [password/key/agent/interactive]", default="password")

    private_key_path = None
    secret = None
    auth = (auth or "password").strip().lower()
    if auth == "key":
        private_key_path = key or typer.prompt("Private key path")
    elif auth == "password":
        secret = typer.prompt("Password (stored in GNOME Keyring)", hide_input=True, confirmation_prompt=True)

    group_id = None
    if group:
        obj = next((g for g in ctx.servers.list_groups() if g.name == group), None)
        if obj:
            group_id = obj.id
        else:
            group_id = ctx.servers.create_group(group).id

    try:
        server = ctx.servers.create(
            _server_input(
                name=name or alias, alias=alias, host=host, port=port, username=user,
                auth_type=auth, default_path=path,
                connection_timeout=timeout if timeout else ctx.settings.get("connect_timeout", 15),
            ),
            group_id=group_id,
            secret=secret,
            private_key_path=private_key_path,
            description=description,
            tags=[t.strip() for t in tags.split(",") if t.strip()],
        )
    except Exception as exc:
        _print_error(exc)
        raise typer.Exit(1)
    ok(f"Server '{server.alias}' saved (id={server.id})")
    if secret:
        ok("Password stored securely in the system keyring (Secret Service)")
    hint(f"Connect now:  {ctx.settings.cli_command_name} {server.alias}")


def _server_input(**kwargs):
    from ssh_desk.utils.validation import ServerInput

    try:
        return ServerInput(**kwargs)
    except Exception as exc:
        from pydantic import ValidationError

        if isinstance(exc, ValidationError):
            first = exc.errors()[0]
            raise SshDeskError(f"Invalid input for '{first.get('loc', ('?',))[0]}': {first.get('msg', exc)}")
        raise


def _print_error(exc: Exception) -> None:
    if isinstance(exc, SshDeskError):
        err(str(exc))
        if exc.hint:
            hint(f"hint: {exc.hint}")
    else:
        err(f"{type(exc).__name__}: {exc}")


# ===================================================================== info
@app.command("info")
def info_cmd(
    alias: str = typer.Argument(..., help="Server alias"),
    show_secret: bool = typer.Option(False, "--show-secret", help="Reveal stored password (requires confirmation)"),
):
    """Show full server details."""
    ctx = get_ctx()
    try:
        server = ctx.servers.require_by_alias(alias)
    except SshDeskError as exc:
        _print_error(exc)
        raise typer.Exit(1)
    rows = [
        ["ID", str(server.id)],
        ["Name", server.name],
        ["Alias", server.alias],
        ["Host", f"{server.host}:{server.port}"],
        ["Username", server.username],
        ["Auth type", server.auth_type],
        ["Private key", server.private_key_path or "-"],
        ["Password", "stored in keyring" if server.secret_ref else "-"],
        ["Default path", server.default_path or "-"],
        ["Group", server.group.name if server.group else "-"],
        ["Tags", ", ".join(server.tags or []) or "-"],
        ["Favorite", fmt_bool(server.favorite)],
        ["Timeout / KeepAlive", f"{server.connection_timeout}s / {server.keep_alive}s"],
        ["Compression / Agent", f"{fmt_bool(server.compression)} / {fmt_bool(server.forward_agent)}"],
        ["Jump host", ctx.servers.get(server.jump_host_id).alias if server.jump_host_id else "-"],
        ["Custom options", ", ".join(server.custom_options or []) or "-"],
    ]
    if server.description:
        rows.append(["Description", server.description])
    print(fmt_table(["FIELD", "VALUE"], rows))
    if server.paths:
        print()
        print(fmt_table(
            ["PATH NAME", "REMOTE PATH", "DEFAULT"],
            [[p.name, p.path, "*" if p.is_default else ""] for p in server.paths],
        ))
    if show_secret:
        answer = typer.prompt(f"Type the alias '{server.alias}' to confirm revealing the password")
        if answer.strip().lower() != server.alias:
            err("Confirmation failed - password not shown")
            raise typer.Exit(1)
        try:
            secret = ctx.credentials.get_server_password(server)
        except SshDeskError as exc:
            _print_error(exc)
            raise typer.Exit(1)
        if secret:
            print(paint("Password: ", BOLD) + secret)
        else:
            warn("No password stored for this server")


# ===================================================================== test
@app.command()
def test(
    alias: str = typer.Argument(...),
    user: str | None = typer.Option(None, "--user", help="Override username (not saved)"),
    port: int | None = typer.Option(None, "--port", help="Override port (not saved)"),
    accept_host_key: bool = typer.Option(False, "--accept-host-key", help="Accept and store unknown host key"),
):
    """Test connection to a server."""
    ctx = get_ctx()
    try:
        server = ctx.servers.require_by_alias(alias)
        gate = _cli_gate(accept_host_key)
        result = ctx.connections.test(server, user=user, port=port, gate=gate)
    except SshDeskError as exc:
        _print_error(exc)
        raise typer.Exit(1)
    if result.ok:
        ok(f"{server.alias}: connection successful ({result.latency_ms} ms)")
    else:
        err(f"{server.alias}: {result.message}")
        raise typer.Exit(1)


def _cli_gate(accept_host_key: bool):
    from ssh_desk.services.connection_service import CliHostKeyGate

    return CliHostKeyGate(assume_yes=accept_host_key)


# ===================================================================== edit
@app.command()
def edit(
    alias: str = typer.Argument(...),
    name: str | None = typer.Option(None, "--name"),
    host: str | None = typer.Option(None, "--host"),
    user: str | None = typer.Option(None, "--user"),
    port: int | None = typer.Option(None, "--port"),
    auth: str | None = typer.Option(None, "--auth"),
    key: str | None = typer.Option(None, "--key"),
    group: str | None = typer.Option(None, "--group"),
    path: str | None = typer.Option(None, "--path", help="Default remote path ('' clears)"),
    description: str | None = typer.Option(None, "--description"),
    tags: str | None = typer.Option(None, "--tags"),
    set_password: bool = typer.Option(False, "--set-password", help="Prompt to (re)set the keyring password"),
):
    """Edit a server. Without options an interactive editor runs."""
    ctx = get_ctx()
    try:
        server = ctx.servers.require_by_alias(alias)
        updates = {}
        if name is not None: updates["name"] = name
        if host is not None: updates["host"] = host
        if user is not None: updates["username"] = user
        if port is not None: updates["port"] = port
        if auth is not None: updates["auth_type"] = auth.strip().lower()
        if path is not None: updates["default_path"] = path or None
        if description is not None: updates["description"] = description
        if tags is not None: updates["tags"] = [t.strip() for t in tags.split(",") if t.strip()]

        secret = None
        if set_password:
            secret = typer.prompt("New password", hide_input=True, confirmation_prompt=True)

        if not updates and key is None and group is None and secret is None:
            _interactive_edit(ctx, server)
            return

        group_id = ...
        if group is not None:
            obj = next((g for g in ctx.servers.list_groups() if g.name == group), None)
            group_id = obj.id if obj else ctx.servers.create_group(group).id
        kwargs = dict(group_id=group_id)
        if secret:
            kwargs["secret"] = secret
        if key is not None:
            kwargs["private_key_path"] = key or None
        fields = dict(
            name=updates.get("name", server.name),
            alias=server.alias,
            host=updates.get("host", server.host),
            port=updates.get("port", server.port),
            username=updates.get("username", server.username),
            auth_type=updates.get("auth_type", server.auth_type),
            default_path=updates.get("default_path", server.default_path),
            connection_timeout=server.connection_timeout,
            keep_alive=server.keep_alive,
        )
        ctx.servers.update(
            server.id,
            _server_input(**fields),
            description=updates.get("description", ...),
            tags=updates.get("tags", ...),
            **kwargs,
        )
        ok(f"Server '{server.alias}' updated")
    except SshDeskError as exc:
        _print_error(exc)
        raise typer.Exit(1)


def _interactive_edit(ctx, server):
    from ssh_desk.utils.validation import ServerInput

    fields = [
        ("name", server.name), ("host", server.host), ("port", str(server.port)),
        ("username", server.username), ("auth_type", server.auth_type),
        ("default_path", server.default_path or ""), ("description", server.description or ""),
    ]
    info("Press Enter to keep the current value. Type 'done' (or empty on field name) to finish.")
    updates = {}
    while True:
        for i, (field, current) in enumerate(fields, 1):
            print(f"  {i}. {field} = {current}")
        choice = typer.prompt("Field number to edit (empty=finish)", default="", show_default=False)
        if not choice.strip():
            break
        if not choice.strip().isdigit() or not (1 <= int(choice) <= len(fields)):
            warn("Invalid selection")
            continue
        field, current = fields[int(choice) - 1]
        new_value = typer.prompt(f"New value for '{field}'", default=str(current), show_default=True)
        updates[field] = new_value
    if not updates:
        info("Nothing changed")
        return
    data = ServerInput(
        name=updates.get("name", server.name),
        alias=server.alias,
        host=updates.get("host", server.host),
        port=int(updates.get("port", server.port)),
        username=updates.get("username", server.username),
        auth_type=updates.get("auth_type", server.auth_type),
        default_path=updates.get("default_path") or None,
        connection_timeout=server.connection_timeout,
        keep_alive=server.keep_alive,
    )
    kwargs = {}
    if "description" in updates:
        kwargs["description"] = updates["description"]
    ctx.servers.update(server.id, data, **kwargs)
    ok(f"Server '{server.alias}' updated")


# ===================================================================== delete
@app.command()
def delete(
    alias: str = typer.Argument(...),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Delete a server (also removes its stored secret from the keyring)."""
    ctx = get_ctx()
    try:
        server = ctx.servers.require_by_alias(alias)
        if not yes:
            confirm = typer.prompt(
                f"Delete server '{server.alias}' ({server.username}@{server.host}) and its stored secret? Type 'DELETE' to confirm"
            )
            if confirm.strip() != "DELETE":
                info("Aborted")
                return
        ctx.servers.delete(server.id)
        ok(f"Server '{alias}' deleted (secret removed from keyring)")
    except SshDeskError as exc:
        _print_error(exc)
        raise typer.Exit(1)


# ===================================================================== connect
@app.command()
def connect(
    target: str = typer.Argument(..., help="Server alias"),
    path: str | None = typer.Argument(None, help="Saved path name or absolute remote path"),
    exec_cmd: str | None = typer.Option(None, "--exec", help="Run a command instead of a shell"),
    user: str | None = typer.Option(None, "--user", help="Override username (not saved)"),
    port: int | None = typer.Option(None, "--port", help="Override port (not saved)"),
    accept_host_key: bool = typer.Option(False, "--accept-host-key"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the ssh command line and exit"),
):
    """Connect to a server: `sss <alias> [path]`."""
    ctx = get_ctx()
    try:
        server = ctx.servers.require_by_alias(target)
        if dry_run:
            prepared = ctx.connections.prepare(
                server, path_target=path, exec_cmd=exec_cmd, user=user, port=port,
                gate=_cli_gate(True), force_tty=not exec_cmd, session_marker=False,
            )
            shown = list(prepared.argv)
            if "SSH_DESK_SECRET_REF" in prepared.env:
                shown.append("# (password supplied securely via askpass helper)")
            print(" ".join(shown))
            return
        prepared = ctx.connections.prepare(
            server, path_target=path, exec_cmd=exec_cmd, user=user, port=port,
            gate=_cli_gate(accept_host_key), force_tty=not exec_cmd,
        )
    except SshDeskError as exc:
        _print_error(exc)
        raise typer.Exit(1)
    if not exec_cmd:
        print(paint(f"Connecting to {prepared.remote_desc} ... (Ctrl+D or 'exit' to disconnect)", DIM), file=sys.stderr)
    code = ctx.connections.run_session(prepared)
    raise typer.Exit(code)


# ===================================================================== search
@app.command()
def search(term: str = typer.Argument(...)):
    """Search servers by name/alias/host/tags."""
    ctx = get_ctx()
    servers = ctx.servers.list_servers(search=term)
    if not servers:
        info(f"No servers match '{term}'")
        return
    rows = [[s.alias, s.name, s.host, s.port, s.username, ", ".join(s.tags or [])] for s in servers]
    print(fmt_table(["ALIAS", "NAME", "HOST", "PORT", "USER", "TAGS"], rows))


# ===================================================================== history
@app.command()
def history(
    server: str | None = typer.Option(None, "--server", help="Filter by alias"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of rows"),
    status: str = typer.Option("", "--status", help="Filter: connected|closed|failed|interrupted"),
):
    """Show connection history."""
    ctx = get_ctx()
    server_id = None
    if server:
        try:
            server_id = ctx.servers.require_by_alias(server).id
        except SshDeskError as exc:
            _print_error(exc)
            raise typer.Exit(1)
    rows_src = ctx.history.list(server_id=server_id, status=status, limit=limit)
    if not rows_src:
        info("No connection history yet")
        return
    rows = []
    for h in rows_src:
        color = {"closed": GREEN, "connected": CYAN, "failed": RED, "interrupted": ""}.get(h.status, "")
        rows.append([
            h.server_alias,
            h.connected_at.strftime("%Y-%m-%d %H:%M"),
            h.disconnected_at.strftime("%H:%M:%S") if h.disconnected_at else "-",
            fmt_duration(h.duration_seconds),
            paint(h.status, color) if color else h.status,
            (h.error_message or "-")[:60],
        ])
    print(fmt_table(["SERVER", "CONNECTED", "DISCONNECTED", "DURATION", "STATUS", "ERROR"], rows))


# ===================================================================== current
@app.command()
def current():
    """Show active SSH sessions and running tunnels."""
    ctx = get_ctx()
    sessions = _session_scan()
    if sessions:
        print(paint("Active SSH sessions:", BOLD))
        print(fmt_table(["PID", "ALIAS"], [[str(s["pid"]), s["alias"]] for s in sessions]))
    else:
        info("No active SSH sessions")
    ctx.tunnels.refresh_all()
    tunnels = [t for t in ctx.tunnels.list() if t.status == "running"]
    if tunnels:
        print()
        print(paint("Running tunnels:", BOLD))
        print(fmt_table(
            ["NAME", "SERVER", "TYPE", "BINDING"],
            [[t.name, ctx.servers.get(t.server_id).alias, t.tunnel_type, _tunnel_binding(t)] for t in tunnels],
        ))


def _tunnel_binding(t) -> str:
    if t.tunnel_type == "dynamic":
        return f"socks5://{t.local_host}:{t.local_port}"
    return f"{t.local_host}:{t.local_port} -> {t.remote_host}:{t.remote_port}"


# ===================================================================== config
config_app = typer.Typer(help="SSH Desk configuration")
app.add_typer(config_app, name="config")


@config_app.command("list")
def config_list():
    """Show all settings."""
    ctx = get_ctx()
    data = ctx.settings.as_dict()
    print(fmt_table(["KEY", "VALUE"], sorted([k, str(v)] for k, v in data.items())))
    print()
    info(f"Config file: {ctx.settings.path}")
    info(f"Database:    {ctx.db.path}")
    info(f"Data dir:    {ctx.data_dir}")


@config_app.command("get")
def config_get(key: str = typer.Argument(...)):
    ctx = get_ctx()
    print(ctx.settings.get(key, ""))


@config_app.command("set")
def config_set(key: str = typer.Argument(...), value: str = typer.Argument(...)):
    ctx = get_ctx()
    old = ctx.settings.get(key)
    converted: object = value
    if isinstance(old, bool):
        converted = value.lower() in ("1", "true", "yes", "on")
    elif isinstance(old, int):
        converted = int(value)
    ctx.settings.set(key, converted)
    ok(f"{key} = {converted}")


@config_app.command("cli-name")
def config_cli_name(name: str = typer.Argument(..., help="New terminal command, e.g. sss, cnc, sshgo")):
    """Change the terminal command name (applied system-wide)."""
    ctx = get_ctx()
    from ssh_desk.cli.shell_integration import install_cli_name

    previous = ctx.settings.get("installed_cli_name", "") or ctx.settings.cli_command_name
    try:
        link = install_cli_name(name, previous)
    except SshDeskError as exc:
        _print_error(exc)
        raise typer.Exit(1)
    ctx.settings.set("cli_command_name", name)
    ctx.settings.set("installed_cli_name", name)
    ok(f"Terminal command is now: {link}")
    hint("If it is not found, ensure ~/.local/bin is in your PATH and open a new terminal.")


@config_app.command("completions")
def config_completions(
    shell: str = typer.Option("bash", "--shell", help="bash or zsh"),
    install: bool = typer.Option(False, "--install", help="Install completion file"),
):
    """Generate or install shell completions (aliases included)."""
    ctx = get_ctx()
    command = ctx.settings.cli_command_name
    from ssh_desk.cli.shell_integration import install_completions

    if install:
        path = install_completions(shell, command)
        ok(f"{shell} completions installed: {path}")
        if shell == "zsh":
            hint("Add to ~/.zshrc:  fpath=(~/.local/share/ssh-desk/completions $fpath); autoload -Uz compinit && compinit")
        return
    from ssh_desk.cli.shell_integration import bash_completion_script, zsh_completion_script

    print(bash_completion_script(command) if shell == "bash" else zsh_completion_script(command))


# ===================================================================== tunnel
tunnel_app = typer.Typer(help="Manage port forwarding tunnels")
app.add_typer(tunnel_app, name="tunnel")
tunnels_alias = typer.Typer(help="Alias for `tunnel`")
app.add_typer(tunnels_alias, name="tunnels")


@tunnel_app.command("list")
def tunnel_list():
    ctx = get_ctx()
    ctx.tunnels.refresh_all()
    tunnels = ctx.tunnels.list()
    if not tunnels:
        info("No tunnels defined. Create one in the GUI (Tunnels page) or via API.")
        return
    rows = [
        [str(t.id), t.name, ctx.servers.get(t.server_id).alias, t.tunnel_type,
         _tunnel_binding(t), t.status]
        for t in tunnels
    ]
    print(fmt_table(["ID", "NAME", "SERVER", "TYPE", "BINDING", "STATUS"], rows))


@tunnel_app.command("start")
def tunnel_start(name: str = typer.Argument(...)):
    ctx = get_ctx()
    tunnel = _find_tunnel(ctx, name)
    try:
        ctx.tunnels.start(tunnel.id)
        t = ctx.tunnels.refresh_status(tunnel.id)
        if t.status == "running":
            ok(f"Tunnel '{t.name}' is running ({_tunnel_binding(t)})")
        else:
            err(f"Tunnel '{t.name}' failed to start: {t.last_error or 'unknown error'}")
            raise typer.Exit(1)
    except SshDeskError as exc:
        _print_error(exc)
        raise typer.Exit(1)


@tunnel_app.command("stop")
def tunnel_stop(name: str = typer.Argument(...)):
    ctx = get_ctx()
    tunnel = _find_tunnel(ctx, name)
    try:
        ctx.tunnels.stop(tunnel.id)
        ok(f"Tunnel '{tunnel.name}' stopped")
    except SshDeskError as exc:
        _print_error(exc)
        raise typer.Exit(1)


def _find_tunnel(ctx, name: str):
    for t in ctx.tunnels.list():
        if t.name == name:
            return t
    by_id = [t for t in ctx.tunnels.list() if str(t.id) == name]
    if by_id:
        return by_id[0]
    err(f"Tunnel '{name}' not found")
    raise typer.Exit(1)


tunnels_alias.command("list")(tunnel_list)
tunnels_alias.command("start")(tunnel_start)
tunnels_alias.command("stop")(tunnel_stop)


# ===================================================================== keys
keys_app = typer.Typer(help="Manage SSH keys")
app.add_typer(keys_app, name="keys")


@keys_app.command("list")
def keys_list():
    ctx = get_ctx()
    keys = ctx.keys.list()
    if not keys:
        info("No SSH keys registered")
        return
    rows = []
    for k in keys:
        linked = len(ctx.keys.linked_servers(k.id))
        rows.append([k.name, k.key_type, k.fingerprint or "-", k.private_key_path, str(linked)])
    print(fmt_table(["NAME", "TYPE", "FINGERPRINT", "PATH", "LINKED SERVERS"], rows))


@keys_app.command("generate")
def keys_generate(
    name: str = typer.Option(..., "--name", help="Key name"),
    type_: str = typer.Option("ed25519", "--type", help="ed25519 | rsa | ecdsa"),
    bits: int = typer.Option(4096, "--bits", help="RSA key size"),
    comment: str = typer.Option("", "--comment"),
    passphrase: bool = typer.Option(False, "--passphrase", help="Ask for a passphrase (stored in keyring)"),
):
    """Generate a new SSH key pair."""
    ctx = get_ctx()
    secret = ""
    if passphrase:
        secret = typer.prompt("Passphrase", hide_input=True, confirmation_prompt=True)
    try:
        key = ctx.keys.generate(name, type_, bits, comment, secret)
        ok(f"Key '{key.name}' generated ({key.key_type})")
        print(paint("Fingerprint: ", BOLD) + (key.fingerprint or "-"))
        hint(f"Public key: {key.private_key_path}.pub")
    except SshDeskError as exc:
        _print_error(exc)
        raise typer.Exit(1)


@keys_app.command("import")
def keys_import(
    path: str = typer.Option(..., "--path", help="Path to the private key"),
    name: str = typer.Option(..., "--name"),
    copy: bool = typer.Option(False, "--copy", help="Copy the private key into SSH Desk storage"),
):
    """Register an existing SSH private key."""
    ctx = get_ctx()
    try:
        key = ctx.keys.import_key(name, path, copy_into_store=copy)
        ok(f"Key '{key.name}' registered ({key.key_type}, {key.fingerprint})")
    except SshDeskError as exc:
        _print_error(exc)
        raise typer.Exit(1)


@keys_app.command("export-pub")
def keys_export_pub(name: str = typer.Argument(...)):
    """Print the public key of a registered key."""
    ctx = get_ctx()
    try:
        key = next((k for k in ctx.keys.list() if k.name == name), None)
        if not key:
            raise RuntimeError(f"Key '{name}' not found")
        print(ctx.keys.export_public(key.id))
    except SshDeskError as exc:
        _print_error(exc)
        raise typer.Exit(1)


@keys_app.command("delete")
def keys_delete(
    name: str = typer.Argument(...),
    remove_files: bool = typer.Option(False, "--remove-files", help="Also delete key files"),
    yes: bool = typer.Option(False, "--yes", "-y"),
):
    """Remove a key from the registry (and optionally delete files)."""
    ctx = get_ctx()
    key = next((k for k in ctx.keys.list() if k.name == name), None)
    if not key:
        err(f"Key '{name}' not found")
        raise typer.Exit(1)
    if not yes:
        confirm = typer.prompt(f"Remove key '{name}' from SSH Desk? [y/N]", default="n")
        if confirm.strip().lower() not in ("y", "yes"):
            info("Aborted")
            return
    ctx.keys.delete(key.id, delete_files=remove_files)
    ok(f"Key '{name}' removed")


# ===================================================================== import/export/backup/restore
@app.command("import")
def import_cmd(
    file: str | None = typer.Option(None, "--file", help="Path to ssh config (default ~/.ssh/config)"),
    apply: bool = typer.Option(False, "--apply", help="Actually import (default: preview only)"),
    all: bool = typer.Option(False, "--all", help="Import all entries without asking"),
):
    """Import servers from an OpenSSH config file (preview first)."""
    ctx = get_ctx()
    try:
        rows = ctx.transfer.preview_ssh_config(file)
    except SshDeskError as exc:
        _print_error(exc)
        raise typer.Exit(1)
    if not rows:
        info("No importable Host entries found")
        return
    print(fmt_table(
        ["#", "HOST", "ALIAS", "USER", "PORT", "KEY", "PROXYJUMP", "ALREADY EXISTS"],
        [
            [str(i), r.entry.host, r.alias, r.entry.user or "-", r.entry.port or 22,
             r.entry.identity_file or "-", r.entry.proxy_jump or "-", "yes" if r.exists else "no"]
            for i, r in enumerate(rows, 1)
        ],
    ))
    if not apply:
        hint("Dry run. Re-run with --apply to import.")
        return
    interactive = all is False and sys.stdin.isatty()
    for row in rows:
        if interactive:
            answer = typer.prompt(f"Import '{row.entry.host}' as '{row.alias}'? [Y/n]", default="y")
            row.selected = answer.strip().lower() in ("y", "yes")
        else:
            row.selected = True
    report = ctx.transfer.apply_ssh_import(rows)
    ok(f"Imported {report['created']} server(s), skipped {report['skipped']}")


@app.command("export")
def export_cmd(
    file: str = typer.Argument(..., help="Output TOML file"),
    include_secrets: bool = typer.Option(False, "--include-secrets", help="Include passwords (DANGEROUS)"),
    include_history: bool = typer.Option(False, "--include-history"),
):
    """Export servers/paths/commands to a TOML file (secrets excluded by default)."""
    ctx = get_ctx()
    try:
        report = ctx.transfer.export_toml(file, include_secrets=include_secrets, include_history=include_history)
    except SshDeskError as exc:
        _print_error(exc)
        raise typer.Exit(1)
    ok(f"Exported {report['servers']} server(s) to {report['file']}")
    if include_secrets:
        warn("Secrets were included in this export - protect the file!")


@app.command()
def backup(
    file: str = typer.Argument(...),
    include_secrets: bool = typer.Option(False, "--include-secrets"),
):
    """Full backup (servers, groups, paths, commands, keys metadata, tunnels)."""
    ctx = get_ctx()
    try:
        report = ctx.transfer.export_toml(file, include_secrets=include_secrets, include_history=True)
    except SshDeskError as exc:
        _print_error(exc)
        raise typer.Exit(1)
    ok(f"Backup written to {report['file']} ({report['servers']} servers)")


@app.command()
def restore(
    file: str = typer.Argument(...),
    no_secrets: bool = typer.Option(False, "--no-secrets", help="Do not restore stored passwords"),
):
    """Restore from a backup file (existing aliases are skipped)."""
    ctx = get_ctx()
    try:
        report = ctx.transfer.import_toml(file, restore_secrets=not no_secrets)
    except SshDeskError as exc:
        _print_error(exc)
        raise typer.Exit(1)
    ok(
        f"Restored {report['servers']} server(s), {report['groups']} group(s), "
        f"{report['secrets']} secret(s); skipped {report['skipped']} existing"
    )


# ===================================================================== misc
@app.command()
def version():
    """Show versions."""
    import subprocess

    print(f"SSH Desk CLI v{__version__}")
    print(f"Python {sys.version.split()[0]}")
    try:
        proc = subprocess.run(["ssh", "-V"], capture_output=True, text=True)
        print(proc.stderr.strip().splitlines()[0])
    except (FileNotFoundError, IndexError):
        warn("OpenSSH client not found - install it with: sudo apt install openssh-client")


@app.command("install-cli")
def install_cli(
    name: str | None = typer.Option(None, "--name", help="Command name (default: configured name)"),
):
    """Install/refresh the terminal command symlink in ~/.local/bin."""
    ctx = get_ctx()
    from ssh_desk.cli.shell_integration import bin_dir, install_cli_name

    command = name or ctx.settings.cli_command_name
    previous = ctx.settings.get("installed_cli_name", "")
    try:
        link = install_cli_name(command, previous)
    except SshDeskError as exc:
        _print_error(exc)
        raise typer.Exit(1)
    ctx.settings.set("installed_cli_name", command)
    ctx.settings.set("cli_command_name", command)
    ok(f"Terminal command installed: {link}")
    if str(bin_dir()) not in (os.environ.get("PATH") or ""):
        warn(f"{bin_dir()} is not in PATH. Add it to your ~/.bashrc:")
        hint(f'  export PATH="{bin_dir()}:$PATH"')


@app.command("uninstall-data")
def uninstall_data(
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation"),
    keep_secrets: bool = typer.Option(False, "--keep-secrets", help="Do NOT purge keyring secrets"),
):
    """Remove SSH Desk data (config, database, logs) - requires explicit confirmation."""
    from pathlib import Path

    ctx = get_ctx()
    if not yes:
        confirm = typer.prompt("This deletes ALL servers, history and settings. Type 'PURGE' to confirm")
        if confirm.strip() != "PURGE":
            info("Aborted")
            return
    removed_secrets = 0
    if not keep_secrets:
        try:
            removed_secrets = ctx.credentials.purge_all()
        except SshDeskError as exc:
            warn(f"Keyring purge skipped: {exc}")
    targets = [ctx.config_dir, ctx.data_dir]
    for target in targets:
        target = Path(target)
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
    ok(f"Data removed. Purged {removed_secrets} secret(s) from the keyring.")


@app.command("proxy", hidden=True)
def proxy(
    jump_alias: str = typer.Argument(..., help="Alias of the jump/bastion server"),
    target_host: str = typer.Argument(...),
    target_port: int = typer.Argument(...),
):
    """Internal ProxyCommand helper: stdio forward through a jump server (ssh -W)."""
    ctx = get_ctx()
    from ssh_desk.utils.validation import validate_host

    validate_host(target_host)
    if not (1 <= int(target_port) <= 65535):
        raise typer.Exit(2)
    try:
        jump = ctx.servers.require_by_alias(jump_alias)
        ctx.connections.proxy_exec(jump, target_host, int(target_port))
    except SshDeskError as exc:
        print(f"ssh-desk proxy: {exc}", file=sys.stderr)
        if getattr(exc, "hint", ""):
            print(f"hint: {exc.hint}", file=sys.stderr)
        raise typer.Exit(1)


@app.command("__complete", hidden=True)
def complete_cmd(
    word: str = typer.Argument(""),
    line: str = typer.Argument(""),
):
    """Completion candidates for bash/zsh integration."""
    ctx = get_ctx()
    try:
        aliases = [s.alias for s in ctx.servers.list_servers()]
        tunnels = [t.name for t in ctx.tunnels.list()]
    except Exception:
        aliases, tunnels = [], []
    commands = sorted(APP_COMMANDS - {"__complete", "proxy"})
    words = [w for w in (line or "").split() if w]
    first = words[0] if words else ""
    second = words[1] if len(words) > 1 else ""
    if first == "tunnel" and second in ("start", "stop"):
        candidates = tunnels
    elif first in ("info", "test", "edit", "delete", "connect") or first in aliases:
        candidates = aliases
    else:
        candidates = commands + aliases
    for candidate in candidates:
        print(candidate)


# ===================================================================== dispatcher
def run(argv: list[str] | None = None) -> int:
    """Entry point. Makes `sss <alias> ...` work as `connect <alias> ...`."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and not args[0].startswith("-") and args[0] not in APP_COMMANDS:
        args = ["connect", *args]
    if not args:
        _print_summary()
        return 0
    try:
        app(args)
        return 0
    except typer.Exit as exc:
        return exc.exit_code
    except SshDeskError as exc:
        _print_error(exc)
        return 1
    except KeyboardInterrupt:
        return 130


def _print_summary() -> None:
    ctx = get_ctx()
    command = ctx.settings.cli_command_name
    servers = ctx.servers.list_servers()
    print(paint(f"SSH Desk CLI v{__version__}", BOLD))
    print()
    if servers:
        active = {s["alias"] for s in _session_scan()}
        rows = [[s.alias, s.name, f"{s.username}@{s.host}:{s.port}",
                 paint("connected", GREEN) if s.alias in active else ""] for s in servers[:8]]
        print(fmt_table(["ALIAS", "NAME", "HOST", "STATUS"], rows))
        if len(servers) > 8:
            hint(f"  ... and {len(servers) - 8} more (run '{command} list')")
    else:
        info(f"No servers yet. Add your first server: {command} add")
    print()
    hint(f"Connect:            {command} <alias> [path]")
    hint(f"Run a command:      {command} <alias> --exec 'uptime'")
    hint(f"Help & full guide:  {command} --help")


if __name__ == "__main__":
    sys.exit(run())
