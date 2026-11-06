"""GUI entry point: `ssh-desk` (or `python -m ssh_desk`)."""

import sys


def run() -> int:
    from ssh_desk.core.application import AppContext

    ctx = AppContext.instance()
    from ssh_desk.gui.app import run_gui

    return run_gui(ctx)


if __name__ == "__main__":
    sys.exit(run())
