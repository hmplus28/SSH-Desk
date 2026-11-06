"""PyInstaller CLI entry hook: makes the bundled console binary behave like ssh-desk-cli."""

import sys

from ssh_desk.cli.commands import run

if __name__ == "__main__":
    sys.exit(run())
