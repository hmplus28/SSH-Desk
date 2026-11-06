"""GUI smoke test: all pages build and switch, theme/language apply (offscreen)."""

import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def test_main_window_pages(qapp, ctx):

    from ssh_desk.gui.main_window import MainWindow

    window = MainWindow(ctx)
    window.show()
    for page in ["dashboard", "servers", "terminal", "files", "keys", "tunnels",
                 "commands", "history", "settings", "details"]:
        window.show_page(page)
        qapp.processEvents()
    # theme + language
    window.apply_theme("light")
    window.apply_language("fa")
    qapp.processEvents()
    assert window.sidebar.item(0).text()
    window.apply_language("en")
    window.apply_theme("dark")
    qapp.processEvents()
    # status bar refresh
    window.refresh_statusbar()
    qapp.processEvents()
    window.close()


def test_servers_page_crud_flow(qapp, ctx, server_input):
    from ssh_desk.gui.main_window import MainWindow

    server = ctx.servers.create(server_input(alias="guix"))
    window = MainWindow(ctx)
    window.show()
    window.show_page("servers")
    qapp.processEvents()
    page = window.pages["servers"]
    assert page.table.rowCount() >= 1
    window.show_page("details")
    window.pages["details"].set_server(server.id)
    qapp.processEvents()
    assert window.pages["details"].title.text().startswith("Production")
    window.close()
