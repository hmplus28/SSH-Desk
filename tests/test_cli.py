"""CLI tests via Typer CliRunner: version, CRUD, dry-run connect, config, completions."""

import pytest
from typer.testing import CliRunner

from ssh_desk.cli import commands
from ssh_desk.cli.commands import app

runner = CliRunner()


@pytest.fixture()
def cli(ctx, monkeypatch):
    commands.set_ctx(ctx)
    monkeypatch.setenv("SSH_DESK_BIN_DIR", str(ctx.data_dir / "bin"))
    return app


def test_version(cli):
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "SSH Desk CLI" in result.output


def test_bare_summary(ctx, capsys):
    commands.set_ctx(ctx)
    assert commands.run([]) == 0
    out = capsys.readouterr().out
    assert "SSH Desk CLI" in out


def test_add_list_info_delete(cli):
    result = runner.invoke(app, ["add", "--alias", "prod", "--host", "192.168.1.1",
                                 "--user", "root", "--port", "22", "--auth", "interactive"])
    assert result.exit_code == 0, result.output
    result = runner.invoke(app, ["list"])
    assert "prod" in result.output
    result = runner.invoke(app, ["info", "prod"])
    assert "192.168.1.1" in result.output
    result = runner.invoke(app, ["delete", "prod", "--yes"])
    assert result.exit_code == 0


def test_alias_unique_via_cli(cli):
    args = ["add", "--alias", "x1", "--host", "1.2.3.4", "--port", "22", "--user", "root", "--auth", "interactive"]
    runner.invoke(app, args)
    result = runner.invoke(app, args)
    assert result.exit_code == 1
    assert "already exists" in result.output


def test_invalid_port_exits_nonzero(cli):
    result = runner.invoke(app, ["add", "--alias", "p1", "--host", "1.2.3.4",
                                 "--port", "70000", "--auth", "interactive"])
    assert result.exit_code != 0


def test_add_password_prompted_and_stored(cli, server_input):
    ctx = commands.get_ctx()
    result = runner.invoke(
        app, ["add", "--alias", "pw1", "--host", "5.5.5.5", "--port", "22", "--user", "root", "--auth", "password"],
        input="secret-pw\nsecret-pw\n",
    )
    assert result.exit_code == 0, result.output
    server = ctx.servers.get_by_alias("pw1")
    assert ctx.credentials.get_server_password(server) == "secret-pw"


def test_connect_dry_run(cli, server_input):
    ctx = commands.get_ctx()
    ctx.servers.create(server_input(alias="dr1", default_path="/var/www"))
    result = runner.invoke(app, ["connect", "dr1", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "StrictHostKeyChecking=yes" in result.output
    assert "/var/www" in result.output
    assert "root@192.168.1.1" in result.output


def test_connect_dry_run_with_saved_path(cli, server_input):
    from ssh_desk.utils.validation import PathInput

    ctx = commands.get_ctx()
    server = ctx.servers.create(server_input(alias="dr2"))
    ctx.servers.set_paths(server.id, [PathInput(name="nginx", path="/etc/nginx")])
    result = runner.invoke(app, ["connect", "dr2", "nginx", "--dry-run"])
    assert "/etc/nginx" in result.output


def test_connect_unknown_alias(cli):
    result = runner.invoke(app, ["connect", "ghost"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_search(cli, server_input):
    ctx = commands.get_ctx()
    ctx.servers.create(server_input(alias="findme"))
    result = runner.invoke(app, ["search", "findme"])
    assert "findme" in result.output


def test_history_command(cli, server_input):
    ctx = commands.get_ctx()
    server = ctx.servers.create(server_input())
    hid = ctx.history.start(server)
    ctx.history.close(hid, "closed")
    result = runner.invoke(app, ["history"])
    assert "closed" in result.output


def test_config_get_set(cli):
    result = runner.invoke(app, ["config", "set", "connect_timeout", "42"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["config", "get", "connect_timeout"])
    assert result.output.strip() == "42"


def test_cli_name_change(monkeypatch, ctx):
    commands.set_ctx(ctx)
    monkeypatch.setenv("SSH_DESK_BIN_DIR", str(ctx.data_dir / "bin"))
    # make the wrapper resolvable: shell_integration falls back to data_dir/bin/ssh-desk-cli
    bin_dir = ctx.data_dir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    wrapper = bin_dir / "ssh-desk-cli"
    wrapper.write_text("#!/bin/sh\nexit 0\n")
    wrapper.chmod(0o755)
    result = runner.invoke(app, ["config", "cli-name", "cnc"])
    assert result.exit_code == 0, result.output
    assert (bin_dir / "cnc").is_symlink()
    assert ctx.settings.cli_command_name == "cnc"
    # old default removed
    assert not (bin_dir / "sss").exists()


def test_completions_output(cli):
    result = runner.invoke(app, ["config", "completions", "--shell", "bash"])
    assert "complete" in result.output
    result = runner.invoke(app, ["config", "completions", "--shell", "zsh"])
    assert "#compdef" in result.output


def test_complete_candidates(cli, server_input):
    ctx = commands.get_ctx()
    ctx.servers.create(server_input(alias="alpha"))
    result = runner.invoke(app, ["__complete", "", ""])
    assert "alpha" in result.output
    assert "connect" in result.output


def test_export_and_exit_codes(cli, server_input, tmp_path):
    ctx = commands.get_ctx()
    ctx.servers.create(server_input(alias="ex1"))
    out = tmp_path / "export.toml"
    result = runner.invoke(app, ["export", str(out)])
    assert result.exit_code == 0
    assert out.exists()
