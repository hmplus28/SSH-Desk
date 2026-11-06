"""Credential service: storage round-trip, deletion sync, ephemeral secrets, purge."""

import json

import pytest

from ssh_desk.core.exceptions import SecretNotFoundError


def test_store_and_retrieve(ctx, server_input):
    server = ctx.servers.create(server_input(auth_type="password"), secret="hunter2")
    assert server.secret_ref
    ref = json.loads(server.secret_ref)
    assert ref["ssh-desk.type"] == "server"
    assert "hunter2" not in server.secret_ref  # only a reference, never the secret
    assert ctx.credentials.get_server_password(server) == "hunter2"


def test_missing_secret_raises(ctx, server_input):
    server = ctx.servers.create(server_input(auth_type="password"), secret="x")
    ctx.credentials.store.delete(server.secret_ref)
    with pytest.raises(SecretNotFoundError):
        ctx.credentials.get_server_password(server)


def test_auth_change_deletes_secret(ctx, server_input):
    server = ctx.servers.create(server_input(auth_type="password"), secret="pw")
    ctx.servers.update(server.id, server_input(auth_type="key"))
    server = ctx.servers.get(server.id)
    assert server.secret_ref is None
    assert ctx.credentials.store.retrieve(server.secret_ref or "") is None


def test_key_passphrase(ctx):
    ref = ctx.credentials.store_key_passphrase("my-key", "phrase-123")
    assert ctx.credentials.get_key_passphrase(ref) == "phrase-123"
    ctx.credentials.delete_key_passphrase(ref)
    assert ctx.credentials.get_key_passphrase(ref) is None


def test_ephemeral_and_delete_ref(ctx):
    ref = ctx.credentials.store_ephemeral("tmp-1", "temp-pass")
    assert ctx.credentials.store.retrieve(ref) == "temp-pass"
    ctx.credentials.delete_ref(ref)
    assert ctx.credentials.store.retrieve(ref) is None


def test_purge_all(ctx, server_input):
    ctx.servers.create(server_input(alias="a1", auth_type="password"), secret="one")
    ctx.servers.create(server_input(alias="a2", auth_type="password"), secret="two")
    count = ctx.credentials.purge_all()
    assert count == 2
    assert ctx.credentials.purge_all() == 0


def test_secret_never_in_db_file(ctx, server_input):
    import sqlite3

    server = ctx.servers.create(server_input(alias="sec1", auth_type="password"), secret="top-secret-value")
    raw = sqlite3.connect(str(ctx.db.path)).execute(
        "SELECT secret_ref FROM servers WHERE id=?", (server.id,)
    ).fetchone()
    assert "top-secret-value" not in str(raw)
