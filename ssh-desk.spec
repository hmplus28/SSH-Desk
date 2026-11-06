# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for SSH Desk (one-dir bundle)
import os

block_cipher = None

hiddenimports = [
    "ssh_desk.ssh.askpass",
    "ssh_desk.ssh.tunnel_runner",
    "ssh_desk.cli.main",
    "ssh_desk.cli.commands",
    "ssh_desk.services.server_service",
    "ssh_desk.services.connection_service",
    "ssh_desk.services.credential_service",
    "ssh_desk.services.sftp_service",
    "ssh_desk.services.tunnel_service",
    "ssh_desk.services.key_service",
    "ssh_desk.services.history_service",
    "ssh_desk.services.import_export_service",
    "secretstorage",
    "pyte",
]

a = Analysis(
    ["src/ssh_desk/main.py"],
    pathex=[os.path.join(os.getcwd(), "src")],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ssh-desk",
    console=False,
    disable_windowed_traceback=False,
)
cli_exe = EXE(
    pyz,
    a.scripts,
    [("run_cli", "src/ssh_desk/cli/run_cli_hook.py")],
    exclude_binaries=True,
    name="ssh-desk-cli",
    console=True,
)

coll = COLLECT(
    exe, cli_exe, a.binaries, a.zipfiles, a.datas,
    name="ssh-desk",
)
