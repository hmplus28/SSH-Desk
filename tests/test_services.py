"""Backup/restore round-trip, keys, tunnels argv, logging redaction, session scan."""


import pytest

from ssh_desk.utils.validation import CommandInput, PathInput, ServerInput, TunnelInput


def test_backup_restore_roundtrip(ctx, tmp_path):
    group = ctx.servers.create_group("grp1")
    server = ctx.servers.create(
        ServerInput(name="S", alias="srv1", host="1.1.1.1", username="u", auth_type="password"),
        group_id=group.id, secret="restore-pw",
        paths=[PathInput(name="logs", path="/var/log")],
    )
    ctx.servers.create_command(CommandInput(name="uptime-cmd", command="uptime"), server_id=server.id)
    ctx.servers.create_command(CommandInput(name="global-cmd", command="df -h"), server_id=None)
    ctx.keys.generate("k1", "ed25519")
    backup = tmp_path / "backup.toml"
    report = ctx.transfer.export_toml(str(backup), include_secrets=True, include_history=True)
    assert report["servers"] == 1

    # restore into a fresh context
    from ssh_desk.core.application import AppContext
    from ssh_desk.services.credential_service import MemorySecretStore

    ctx2 = AppContext(data_dir=tmp_path / "d2", config_dir=tmp_path / "c2",
                      secret_store=MemorySecretStore(), quiet_logs=True)
    try:
        result = ctx2.transfer.import_toml(str(backup))
        assert result["servers"] == 1
        restored = ctx2.servers.get_by_alias("srv1")
        assert restored.host == "1.1.1.1"
        assert restored.group.name == "grp1"
        assert [p.path for p in restored.paths] == ["/var/log"]
        assert ctx2.credentials.get_server_password(restored) == "restore-pw"
        assert len(ctx2.keys.list()) == 1
        # restore again -> skipped (alias exists)
        again = ctx2.transfer.import_toml(str(backup))
        assert again["skipped"] == 1
    finally:
        ctx2.shutdown()


def test_export_without_secrets(ctx, tmp_path, server_input):
    ctx.servers.create(server_input(alias="nosec", auth_type="password"), secret="hidden-value")
    out = tmp_path / "nosec.toml"
    ctx.transfer.export_toml(str(out), include_secrets=False)
    content = out.read_text()
    assert "hidden-value" not in content


def test_key_generate_import_export(ctx):
    key = ctx.keys.generate("gen1", "ed25519", comment="test")
    assert key.fingerprint.startswith("SHA256:")
    assert (key.private_key_path).endswith("id_ed25519")
    public = ctx.keys.export_public(key.id)
    assert public.startswith("ssh-ed25519 ")
    # register the same key for a server -> linked_servers
    server = ctx.servers.create(
        ServerInput(name="K", alias="ksrv", host="2.2.2.2", username="u", auth_type="key"),
        private_key_path=key.private_key_path,
    )
    assert [s.id for s in ctx.keys.linked_servers(key.id)] == [server.id]
    # passphrase storage
    ctx.keys.set_passphrase(key.id, "key-pass")
    assert ctx.credentials.get_key_passphrase(ctx.keys.get(key.id).passphrase_ref) == "key-pass"
    ctx.keys.delete(key.id, delete_files=True)


def test_tunnel_port_spec_and_service(ctx, server_input):
    server = ctx.servers.create(server_input())
    tunnel = ctx.tunnels.create(server.id, "db", TunnelInput(
        tunnel_type="local", local_port=5432, remote_host="localhost", remote_port=5432))
    assert ":5432:localhost:5432" in ctx.tunnels.port_spec(tunnel)
    dynamic = ctx.tunnels.create(server.id, "socks", TunnelInput(
        tunnel_type="dynamic", local_port=1080))
    assert ctx.tunnels.port_spec(dynamic).startswith("-D 127.0.0.1:1080")
    # duplicate tunnel name rejected
    with pytest.raises(Exception):
        ctx.tunnels.create(server.id, "db", TunnelInput(
            tunnel_type="local", local_port=6000, remote_host="x", remote_port=1))


def test_tunnel_argv(ctx, server_input):
    from ssh_desk.ssh import client

    server = ctx.servers.create(server_input(auth_type="interactive"))
    argv, env = client.build_tunnel_argv(ctx, server, port_spec="-L 127.0.0.1:5432:localhost:5432")
    joined = " ".join(argv)
    assert "-N" in argv and "-T" in argv
    assert "-L 127.0.0.1:5432:localhost:5432" in joined
    assert "ExitOnForwardFailure=yes" in joined


def test_logging_redaction():
    from ssh_desk.utils.logging_setup import redact

    assert "hunter2" not in redact("password=hunter2 done")
    assert "hunter2" not in redact("PASSWORD: hunter2")
    assert redact("normal message") == "normal message"


def test_session_scan_tools():
    import os

    from ssh_desk.utils.procs import list_sessions, pid_alive, port_bindable

    assert pid_alive(os.getpid())
    assert not pid_alive(999999)
    assert isinstance(list_sessions(), list)
    assert port_bindable("127.0.0.1", 0)  # ephemeral


def test_resolve_target_security(ctx, server_input):
    server = ctx.servers.create(server_input(default_path="/var/www"))
    # absolute paths pass through; name lookup fails loudly
    assert ctx.servers.resolve_target(server, "/etc/passwd; rm -rf /") == "/etc/passwd; rm -rf /"
    with pytest.raises(Exception):
        ctx.servers.resolve_target(server, "../relative")
