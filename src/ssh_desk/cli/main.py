"""CLI entry module."""

import sys

from ssh_desk.cli.commands import run

if __name__ == "__main__":
    sys.exit(run())
