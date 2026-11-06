"""SSH config import: parsing, preview, dedupe, apply."""

from ssh_desk.ssh.config_manager import parse_ssh_config

SAMPLE = """
# comment
Host prod
    HostName 192.168.1.1
    User deploy
    Port 2222
    IdentityFile ~/.ssh/id_prod
    ServerAliveInterval 60

Host *
    Compression yes

Host staging-web
    hostname staging.example.com
    user ubuntu
    ForwardAgent yes
    ProxyJump bastion

Host bastion
    HostName 10.0.0.1
"""


def test_parse_entries():
    entries = parse_ssh_config(SAMPLE)
    names = [e.host for e in entries]
    assert "prod" in names and "staging-web" in names and "bastion" in names
    assert "*" not in names  # wildcards skipped
    prod = next(e for e in entries if e.host == "prod")
    assert prod.hostname == "192.168.1.1"
    assert prod.user == "deploy"
    assert prod.port == 2222
    assert prod.identity_file.endswith("id_prod")
    assert prod.server_alive_interval == 60
    staging = next(e for e in entries if e.host == "staging-web")
    assert staging.hostname == "staging.example.com"
    assert staging.proxy_jump == "bastion"


def test_import_preview_and_apply(ctx):
    config_file = ctx.config_dir / "ssh_config"
    config_file.write_text(SAMPLE)
    rows = ctx.transfer.preview_ssh_config(str(config_file))
    assert len(rows) == 3
    assert all(not r.exists for r in rows)
    for row in rows:
        row.selected = True
    report = ctx.transfer.apply_ssh_import(rows)
    assert report["created"] == 3
    prod = ctx.servers.get_by_alias("prod")
    assert prod.host == "192.168.1.1"
    assert prod.port == 2222
    assert prod.username == "deploy"


def test_import_dedupe(ctx):
    config_file = ctx.config_dir / "ssh_config"
    config_file.write_text(SAMPLE)
    rows = ctx.transfer.preview_ssh_config(str(config_file))
    for row in rows:
        row.selected = True
    ctx.transfer.apply_ssh_import(rows)
    # second run: same host/user/port -> flagged as existing and skipped
    rows2 = ctx.transfer.preview_ssh_config(str(config_file))
    assert all(r.exists for r in rows2)
    report = ctx.transfer.apply_ssh_import(rows2)
    assert report["created"] == 0


def test_key_registration_on_import(ctx, tmp_path):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    key = ed25519.Ed25519PrivateKey.generate()
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.OpenSSH,
                            serialization.NoEncryption())
    key_file = tmp_path / "id_import_test"
    key_file.write_bytes(pem)
    config = f"Host ksrv\n    HostName 10.1.1.1\n    IdentityFile {key_file}\n"
    (ctx.config_dir / "cfg2").write_text(config)
    rows = ctx.transfer.preview_ssh_config(str(ctx.config_dir / "cfg2"))
    for row in rows:
        row.selected = True
    ctx.transfer.apply_ssh_import(rows)
    server = ctx.servers.get_by_alias("ksrv")
    assert server.auth_type == "key"
    assert len(ctx.keys.list()) == 1
