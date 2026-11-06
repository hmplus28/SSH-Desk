# Development

## Setup

```bash
git clone https://github.com/hmplus28/SSH-Desk.git
cd SSH-Desk
python3 -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
pytest
```

Optional system bits (already on a normal Ubuntu desktop): `openssh-client`,
`gnome-keyring`. In CI/sandboxes without a keyring the tests use an in-memory
secret store — no DBus needed.

## Layout

See [ARCHITECTURE.md](ARCHITECTURE.md). Everything lives under `src/ssh_desk/`
with `core/`, `database/`, `services/`, `ssh/`, `cli/`, `gui/`, `utils/`.

## Running

```bash
ssh-desk                      # GUI (from the venv: .venv/bin/ssh-desk)
ssh-desk-cli list             # CLI
QT_QPA_PLATFORM=offscreen ssh-desk   # headless debugging
```

## Tests

```bash
pytest            # 54 tests: services, CLI, validation, hostkeys, backup, GUI smoke
pytest tests/test_gui_smoke.py -v
ruff check .      # lint (configured in pyproject.toml)
mypy src/         # optional, config present
```

Test conventions:
- Each test gets an isolated `AppContext` (`tmp_path` dirs + `MemorySecretStore`).
- No real servers are ever contacted; host-key fetch tests only assert
  non-crash behaviour on unreachable hosts.

## Release flow

```bash
# 1. quality gates
pytest && ruff check .

# 2. bump version (pyproject.toml + packaging/deb/control + CHANGELOG.md)

# 3. build artifacts
bash scripts/build.sh          # PyInstaller bundle -> dist/ssh-desk/
bash scripts/package_deb.sh    # -> dist/ssh-desk_<version>_amd64.deb

# 4. verify the DEB on a clean machine
sudo apt install ./dist/ssh-desk_*_amd64.deb
```

## Code conventions

- Type hints everywhere; SQLAlchemy 2.0 `Mapped[...]` style.
- Services raise `SshDeskError` subclasses; CLI/GUI translate to exit codes /
  dialogs.
- No secrets in logs (use `register_secret` when handling raw values).
- GUI: never block the main thread — use `GenericWorker` / `run_worker`.
- i18n: every user-visible string goes through `gui.i18n.tr` with `en`+`fa`.

## Adding a migration

1. Bump `SCHEMA_VERSION` in `database/database.py`.
2. Add `_MIGRATIONS[new_version] = lambda engine: ...` performing the DDL.
3. Keep older migration lambdas intact — they run in order on old databases.
