"""Shared test fixtures: isolated AppContext with in-memory secret store."""

import ctypes
import ctypes.util
import os

# Preload Qt runtime system libraries when they are not on the default linker path
# (sandboxed CI). On a normal Ubuntu desktop these are already present.
if ctypes.util.find_library("EGL") is None:
    for _candidate in ("/tmp/qtlibs/root/usr/lib/x86_64-linux-gnu",):
        if os.path.isdir(_candidate):
            for _name in (
                "libglib-2.0.so.0", "libgobject-2.0.so.0", "libgio-2.0.so.0",
                "libfontconfig.so.1", "libfreetype.so.6", "libpng16.so.16",
                "libbrotlicommon.so.1", "libbrotlidec.so.1", "libexpat.so.1",
                "libzstd.so.1", "liblzma.so.5", "libmd.so.0", "libbsd.so.0",
                "libffi.so.8", "libpcre2-8.so.0", "libdeflate.so.0",
                "libGLdispatch.so.0", "libGLX.so.0", "libGL.so.1", "libEGL.so.1",
                "libxkbcommon.so.0", "libdbus-1.so.3", "libdrm.so.2",
                "libglapi.so.0", "libxcb.so.1", "libXau.so.6", "libXdmcp.so.6",
            ):
                try:
                    ctypes.CDLL(os.path.join(_candidate, _name), mode=ctypes.RTLD_GLOBAL)
                except OSError:
                    pass
            break

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from ssh_desk.core.application import AppContext
from ssh_desk.services.credential_service import MemorySecretStore
from ssh_desk.utils.validation import ServerInput


@pytest.fixture()
def ctx(tmp_path, monkeypatch):
    context = AppContext(
        data_dir=tmp_path / "data",
        config_dir=tmp_path / "config",
        secret_store=MemorySecretStore(),
        quiet_logs=True,
    )
    yield context
    context.shutdown()
    AppContext.reset()


@pytest.fixture()
def server_input():
    def make(**kwargs):
        defaults = dict(
            name="Production",
            alias="prod",
            host="192.168.1.1",
            port=22,
            username="root",
            auth_type="interactive",
        )
        defaults.update(kwargs)
        return ServerInput(**defaults)

    return make
