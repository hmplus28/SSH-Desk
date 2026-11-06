"""Server CRUD, alias uniqueness, port validation, paths, duplicate, groups."""

import pytest

from ssh_desk.core.exceptions import AliasExistsError, NotFoundError, PathNotFoundError
from ssh_desk.utils.validation import PathInput


def test_create_and_get(ctx, server_input):
    server = ctx.servers.create(server_input())
    assert server.id >= 1
    assert ctx.servers.get(server.id).alias == "prod"
    assert ctx.servers.get_by_alias("PROD").id == server.id  # case-insensitive lookup


def test_alias_must_be_unique(ctx, server_input):
    ctx.servers.create(server_input())
    with pytest.raises(AliasExistsError):
        ctx.servers.create(server_input(name="Other", alias="prod"))
    # update keeping own alias is fine
    server = ctx.servers.get_by_alias("prod")
    ctx.servers.update(server.id, server_input(host="10.0.0.2"))
    assert ctx.servers.get(server.id).host == "10.0.0.2"


def test_port_validation(ctx, server_input):
    with pytest.raises(Exception):
        server_input(port=70000)
    with pytest.raises(Exception):
        server_input(port=0)
    server = ctx.servers.create(server_input(port=2222))
    assert server.port == 2222


def test_host_validation(server_input):
    with pytest.raises(Exception):
        server_input(host="bad host with spaces")
    with pytest.raises(Exception):
        server_input(host="")
    assert server_input(host="srv.example.com").host == "srv.example.com"
    assert server_input(host="::1").host == "::1"


def test_alias_validation(server_input):
    with pytest.raises(Exception):
        server_input(alias="Bad Alias!")
    assert server_input(alias="Web-01").alias == "web-01"  # normalized lowercase


def test_update_without_recreate(ctx, server_input):
    server = ctx.servers.create(server_input())
    ctx.servers.update(server.id, server_input(alias="staging", host="10.0.0.9", port=2200))
    updated = ctx.servers.get(server.id)
    assert updated.alias == "staging"
    assert updated.port == 2200
    assert ctx.servers.get_by_alias("prod") is None


def test_delete_removes_secret_and_cascades(ctx, server_input):
    server = ctx.servers.create(
        server_input(auth_type="password"), secret="s3cret-value"
    )
    assert server.secret_ref
    assert ctx.credentials.get_server_password(server) == "s3cret-value"
    ctx.servers.set_paths(server.id, [PathInput(name="logs", path="/var/log", is_default=True)])
    ctx.servers.delete(server.id)
    with pytest.raises(NotFoundError):
        ctx.servers.get(server.id)
    assert ctx.credentials.store.retrieve(server.secret_ref) is None  # secret gone


def test_saved_paths_and_default(ctx, server_input):
    server = ctx.servers.create(server_input(default_path="/var/www"))
    ctx.servers.set_paths(
        server.id,
        [
            PathInput(name="website", path="/var/www/html"),
            PathInput(name="nginx", path="/etc/nginx", is_default=True),
            PathInput(name="logs", path="/var/log"),
        ],
    )
    server = ctx.servers.get(server.id)
    assert len(server.paths) == 3
    assert ctx.servers.resolve_target(server, "nginx") == "/etc/nginx"
    assert ctx.servers.resolve_target(server, "logs") == "/var/log"
    assert ctx.servers.resolve_target(server, None) == "/var/www"
    assert ctx.servers.resolve_target(server, "/etc/hosts") == "/etc/hosts"
    with pytest.raises(PathNotFoundError):
        ctx.servers.resolve_target(server, "nope")
    # duplicate names rejected
    with pytest.raises(ValueError):
        ctx.servers.set_paths(
            server.id, [PathInput(name="a", path="/a"), PathInput(name="a", path="/b")]
        )


def test_duplicate_server(ctx, server_input):
    original = ctx.servers.create(
        server_input(auth_type="password"), secret="dup-secret", paths=[PathInput(name="web", path="/srv")]
    )
    copy = ctx.servers.duplicate(original.id)
    assert copy.alias != original.alias
    assert copy.alias.startswith("prod-copy")
    assert len(copy.paths) == 1
    assert ctx.credentials.get_server_password(copy) == "dup-secret"


def test_groups(ctx, server_input):
    group = ctx.servers.create_group("web")
    server = ctx.servers.create(server_input(), group_id=group.id)
    assert server.group.name == "web"
    assert len(ctx.servers.list_servers(group_id=group.id)) == 1
    with pytest.raises(AliasExistsError):
        ctx.servers.create_group("web")


def test_search_and_filters(ctx, server_input):
    ctx.servers.create(server_input(alias="web1", name="Web One", tags=["nginx"]))
    ctx.servers.create(server_input(alias="db1", name="DB", host="10.0.0.5"))
    assert len(ctx.servers.list_servers(search="web")) == 1
    assert len(ctx.servers.list_servers(search="10.0.0")) == 1
    fav = ctx.servers.toggle_favorite(ctx.servers.get_by_alias("db1").id)
    assert fav.favorite is True
    assert len(ctx.servers.list_servers(favorites_only=True)) == 1
