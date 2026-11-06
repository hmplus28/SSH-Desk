"""Main window: collapsible sidebar navigation, header, status bar, busy indicator."""

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ssh_desk.core.exceptions import SshDeskError
from ssh_desk.gui.i18n import is_rtl, set_language, tr
from ssh_desk.gui.theme import build_qss
from ssh_desk.gui.toast import ToastManager
from ssh_desk.gui.widgets_common import BusyOverlay, Page

PAGE_ORDER = ["dashboard", "servers", "terminal", "files", "keys", "tunnels", "commands", "history", "settings"]
PAGE_TITLES = {
    "dashboard": "page_dashboard", "servers": "page_servers", "terminal": "page_terminal",
    "files": "page_files", "keys": "page_keys", "tunnels": "page_tunnels",
    "commands": "page_commands", "history": "page_history", "settings": "settings",
}


class MainWindow(QMainWindow):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.pages = {}
        self._busy_depth = 0
        set_language(ctx.settings.get("language", "en"))

        self.setWindowTitle(tr("app_name"))
        self.resize(1180, 760)
        self.setMinimumSize(900, 600)

        central = QWidget()
        self.root_layout = QHBoxLayout(central)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        # ---- sidebar
        self.sidebar = QListWidget()
        self.sidebar.setProperty("role", "sidebar")
        self.sidebar.setFixedWidth(210)
        self.sidebar.setIconSize(self.sidebar.iconSize())
        for key in PAGE_ORDER:
            item = QListWidgetItem(tr(PAGE_TITLES[key]))
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.sidebar.addItem(item)
        self.sidebar.currentRowChanged.connect(self._page_changed)
        self.root_layout.addWidget(self.sidebar)

        # ---- content column
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack, 1)

        self.busy = BusyOverlay(content)
        content_layout.addWidget(self.busy)

        self.status = self.statusBar()
        self.status_label = QLabel("")
        self.status.addPermanentWidget(self.status_label)
        self.root_layout.addWidget(content, 1)
        self.setCentralWidget(central)

        self.toast = ToastManager(self)

        # ---- shortcuts
        for i, key in enumerate(PAGE_ORDER, 1):
            action = QAction(self)
            action.setShortcut(QKeySequence(f"Ctrl+{i}"))
            action.triggered.connect(lambda _=False, k=key: self.show_page(k))
            self.addAction(action)
        new_server = QAction(self)
        new_server.setShortcut(QKeySequence("Ctrl+N"))
        new_server.triggered.connect(self.open_new_server)
        self.addAction(new_server)
        new_session = QAction(self)
        new_session.setShortcut(QKeySequence("Ctrl+K"))
        new_session.triggered.connect(self.open_new_session_picker)
        self.addAction(new_session)
        quit_action = QAction(self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)
        self.addAction(quit_action)

        # ---- status refresh timer
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self.refresh_statusbar)
        self._status_timer.start(5000)

        self.apply_theme(ctx.settings.get("theme", "dark"))
        start = ctx.settings.get("start_page", "dashboard")
        self.show_page(start if start in PAGE_ORDER else "dashboard")
        self.refresh_statusbar()

    # ------------------------------------------------------------ navigation
    def _make_page(self, key: str) -> Page:
        from ssh_desk.gui.pages.commands import CommandsPage
        from ssh_desk.gui.pages.dashboard import DashboardPage
        from ssh_desk.gui.pages.files import FilesPage
        from ssh_desk.gui.pages.history import HistoryPage
        from ssh_desk.gui.pages.keys import KeysPage
        from ssh_desk.gui.pages.server_details import ServerDetailsPage
        from ssh_desk.gui.pages.servers import ServersPage
        from ssh_desk.gui.pages.settings import SettingsPage
        from ssh_desk.gui.pages.terminal_page import TerminalPage
        from ssh_desk.gui.pages.tunnels import TunnelsPage

        factories = {
            "dashboard": DashboardPage, "servers": ServersPage, "terminal": TerminalPage,
            "files": FilesPage, "keys": KeysPage, "tunnels": TunnelsPage,
            "commands": CommandsPage, "history": HistoryPage, "settings": SettingsPage,
            "details": ServerDetailsPage,
        }
        return factories[key](self.ctx, self)

    def _page_changed(self, row: int):
        if row < 0:
            return
        key = self.sidebar.item(row).data(Qt.ItemDataRole.UserRole)
        self.show_page(key)

    def show_page(self, key: str):
        if key not in self.pages:
            page = self._make_page(key)
            self.pages[key] = page
            self.stack.addWidget(page)
        page = self.pages[key]
        self.stack.setCurrentWidget(page)
        if key in PAGE_TITLES:
            for row in range(self.sidebar.count()):
                if self.sidebar.item(row).data(Qt.ItemDataRole.UserRole) == key:
                    self.sidebar.blockSignals(True)
                    self.sidebar.setCurrentRow(row)
                    self.sidebar.blockSignals(False)
                    break
        page.refresh()
        self.ctx.settings.set("last_page", key)

    # ------------------------------------------------------------ theme / language
    def apply_theme(self, theme: str):
        from ssh_desk.gui.theme import DARK, LIGHT

        palette = DARK if theme != "light" else LIGHT
        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.setStyleSheet(build_qss(palette))
        self.ctx.settings.set("theme", theme)

    def apply_language(self, lang: str):
        set_language(lang)
        self.ctx.settings.set("language", lang)
        direction = Qt.LayoutDirection.RightToLeft if is_rtl() else Qt.LayoutDirection.LeftToRight
        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.setLayoutDirection(direction)
        self.setLayoutDirection(direction)
        for row in range(self.sidebar.count()):
            key = self.sidebar.item(row).data(Qt.ItemDataRole.UserRole)
            self.sidebar.item(row).setText(tr(PAGE_TITLES[key]))
        self.setWindowTitle(tr("app_name"))
        for page in self.pages.values():
            page.retranslate()
        self.refresh_statusbar()

    # ------------------------------------------------------------ sessions/connections
    def connect_server(self, server_id: int, path_target=None, exec_cmd=None, saved_command=None):
        """Open a terminal session to a server (host key + auth handled first)."""
        try:
            server = self.ctx.servers.get(server_id)
            from ssh_desk.services.connection_service import CliHostKeyGate

            prepared = self.ctx.connections.prepare(
                server, path_target=path_target, exec_cmd=exec_cmd, saved_command=saved_command,
                gate=CliHostKeyGate(),
            )
        except SshDeskError as exc:
            hint = f"\n\n{exc.hint}" if exc.hint else ""
            QMessageBox.critical(self, tr("error"), f"{exc}{hint}")
            return
        self.show_page("terminal")
        label = server.alias + (f":{Path(path_target).name}" if path_target else "")
        if exec_cmd or saved_command:
            label = f"$ {server.alias}"
        self.pages["terminal"].open_session(prepared, label)

    def run_saved_command(self, server, cmd):
        self.connect_server(server.id, saved_command=cmd.command)

    def open_raw_terminal(self, argv: list, env: dict, label: str):
        self.show_page("terminal")
        self.pages["terminal"].open_session(
            type("P", (), {"argv": argv, "env": env, "remote_desc": label})(), label
        )

    def open_new_server(self):
        self.show_page("servers")
        self.pages["servers"].add_server()

    def open_edit_server(self, server_id: int):
        self.show_page("servers")
        page = self.pages["servers"]
        page.table.selectRow(0)
        # select the right row by alias
        server = self.ctx.servers.get(server_id)
        for row in range(page.table.rowCount()):
            if page.table.item(row, 1).text() == server.alias:
                page.table.selectRow(row)
                break
        page.edit_selected()

    def open_details(self, server_id: int):
        self.show_page("details")
        self.pages["details"].set_server(server_id)

    def open_new_session_picker(self):
        servers = self.ctx.servers.list_servers()
        if not servers:
            QMessageBox.information(self, tr("new_session"), tr("servers_empty"))
            return
        names = [f"{s.alias}  ({s.host})" for s in servers]
        choice, ok_flag = QInputDialog.getItem(self, tr("select_server"), tr("new_session"), names, 0, False)
        if not ok_flag:
            return
        index = names.index(choice)
        self.connect_server(servers[index].id)

    # ------------------------------------------------------------ busy / toasts
    def push_busy(self, label: str):
        self._busy_depth += 1
        self.busy.show_busy(label)

    def pop_busy(self):
        self._busy_depth = max(0, self._busy_depth - 1)
        if self._busy_depth == 0:
            self.busy.hide_busy()

    def toast_info(self, text: str):
        self.toast.info(text)

    def toast_success(self, text: str):
        self.toast.success(text)

    def toast_warning(self, text: str):
        self.toast.warning(text)

    def toast_error(self, text: str):
        self.toast.error(text)

    def refresh_statusbar(self):
        try:
            stats = self.ctx.servers.stats()
            text = f"{tr('statusbar_sessions', n=stats['active_sessions'])}   |   " \
                   f"{tr('statusbar_tunnels', n=stats['tunnels_running'])}"
            self.status_label.setText(text)
        except Exception:
            pass

    def closeEvent(self, event):
        for page in self.pages.values():
            if hasattr(page, "tabs"):  # terminal page
                while page.tabs.count():
                    page.close_tab(0)
        self.ctx.shutdown()
        super().closeEvent(event)
