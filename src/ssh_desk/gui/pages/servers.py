"""Servers page: searchable/sortable table with full CRUD, test and quick connect."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ssh_desk.core.events import TOPIC_SERVERS
from ssh_desk.core.exceptions import SshDeskError
from ssh_desk.gui.i18n import tr
from ssh_desk.gui.pages.server_dialog import ServerDialog
from ssh_desk.gui.widgets_common import ConfirmDialog, EmptyState, Page

_ALIAS_COL = 1


class ServersPage(Page):
    def __init__(self, ctx, main):
        super().__init__(ctx, main)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(10)

        header = QHBoxLayout()
        self.title = QLabel()
        self.title.setProperty("role", "title")
        header.addWidget(self.title)
        header.addStretch(1)
        self.btn_add = QPushButton()
        self.btn_add.setProperty("role", "primary")
        self.btn_add.clicked.connect(self.add_server)
        header.addWidget(self.btn_add)
        root.addLayout(header)

        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("search"))
        self.search.textChanged.connect(self.reload)
        self.search.setMinimumWidth(220)
        toolbar.addWidget(self.search)
        self.group_combo = QComboBox()
        self.group_combo.setMinimumWidth(140)
        self.group_combo.currentIndexChanged.connect(self.reload)
        toolbar.addWidget(self.group_combo)
        self.sort_combo = QComboBox()
        self.sort_combo.currentIndexChanged.connect(self.reload)
        toolbar.addWidget(self.sort_combo)
        self.fav_toggle = QPushButton("★")
        self.fav_toggle.setCheckable(True)
        self.fav_toggle.toggled.connect(self.reload)
        toolbar.addWidget(self.fav_toggle)
        toolbar.addStretch(1)
        self.btn_connect = QPushButton()
        self.btn_connect.setProperty("role", "primary")
        self.btn_connect.clicked.connect(lambda: self._with_selected(self.main.connect_server))
        toolbar.addWidget(self.btn_connect)
        self.btn_test = QPushButton()
        self.btn_test.clicked.connect(self.test_selected)
        toolbar.addWidget(self.btn_test)
        self.btn_edit = QPushButton()
        self.btn_edit.clicked.connect(self.edit_selected)
        toolbar.addWidget(self.btn_edit)
        self.btn_details = QPushButton()
        self.btn_details.clicked.connect(self.details_selected)
        toolbar.addWidget(self.btn_details)
        self.btn_delete = QPushButton()
        self.btn_delete.setProperty("role", "danger")
        self.btn_delete.clicked.connect(self.delete_selected)
        toolbar.addWidget(self.btn_delete)
        root.addLayout(toolbar)

        self.table = QTableWidget(0, 8)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(lambda _idx: self.details_selected())
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        root.addWidget(self.table, 1)

        self.empty = EmptyState("", self)
        self.empty.hide()
        self.ctx.events.subscribe(TOPIC_SERVERS, lambda _payload: QMeta_reload(self))
        self.retranslate()

    def retranslate(self):
        self.title.setText(tr("page_servers"))
        self.btn_add.setText(tr("add_server"))
        self.btn_connect.setText(tr("connect"))
        self.btn_test.setText(tr("test"))
        self.btn_edit.setText(tr("edit"))
        self.btn_details.setText(tr("details"))
        self.btn_delete.setText(tr("delete"))
        self.search.setPlaceholderText(tr("search"))
        self.table.setHorizontalHeaderLabels(
            ["★", tr("alias"), tr("name"), tr("host"), tr("port"), tr("username"), tr("group"), tr("status")]
        )
        self._rebuild_combos()

    def _rebuild_combos(self):
        current_group = self.group_combo.currentData() if self.group_combo.currentData() else None
        self.group_combo.blockSignals(True)
        self.group_combo.clear()
        self.group_combo.addItem(tr("all_groups"), None)
        for group in self.ctx.servers.list_groups():
            self.group_combo.addItem(group.name, group.id)
        index = self.group_combo.findData(current_group)
        self.group_combo.setCurrentIndex(max(0, index))
        self.group_combo.blockSignals(False)
        self.sort_combo.blockSignals(True)
        self.sort_combo.clear()
        self.sort_combo.addItem(tr("name"), "name")
        self.sort_combo.addItem(tr("alias"), "alias")
        self.sort_combo.addItem("Host", "host")
        self.sort_combo.setCurrentIndex(0)
        self.sort_combo.blockSignals(False)

    def refresh(self):
        self.reload()

    def reload(self, *_args):
        group_id = self.group_combo.currentData()
        servers = self.ctx.servers.list_servers(
            search=self.search.text().strip(),
            group_id=group_id,
            favorites_only=self.fav_toggle.isChecked(),
            sort=self.sort_combo.currentData() or "name",
        )
        active = {s["alias"] for s in _session_scan()}
        self.table.setRowCount(len(servers))
        for i, server in enumerate(servers):
            star = QTableWidgetItem("★" if server.favorite else "")
            star.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if server.favorite:
                star.setForeground(Qt.GlobalColor.yellow)
            self.table.setItem(i, 0, star)
            cells = [server.alias, server.name, server.host, str(server.port), server.username,
                     server.group.name if server.group else "-"]
            for j, value in enumerate(cells):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, server.id)
                self.table.setItem(i, j + 1, item)
            status_item = QTableWidgetItem("● " + tr("connected") if server.alias in active else "○")
            status_item.setForeground(Qt.GlobalColor.green if server.alias in active else Qt.GlobalColor.gray)
            self.table.setItem(i, 7, status_item)
        self.table.resizeColumnsToContents()
        self.empty.setVisible(len(servers) == 0)
        self.empty.setGeometry(self.table.rect())
        self.empty.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.empty.setGeometry(self.table.rect())

    def _selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, _ALIAS_COL)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _with_selected(self, fn):
        server_id = self._selected_id()
        if server_id is None:
            self.main.toast_warning(tr("servers_empty"))
            return
        fn(server_id)

    def add_server(self):
        dialog = ServerDialog(self.ctx, self)
        if dialog.exec() == ServerDialog.DialogCode.Accepted:
            self.reload()

    def edit_selected(self):
        server_id = self._selected_id()
        if server_id is None:
            return
        dialog = ServerDialog(self.ctx, self, server_id=server_id)
        if dialog.exec() == ServerDialog.DialogCode.Accepted:
            self.reload()

    def details_selected(self):
        server_id = self._selected_id()
        if server_id is not None:
            self.main.open_details(server_id)

    def test_selected(self):
        server_id = self._selected_id()
        if server_id is None:
            return
        self.btn_test.setEnabled(False)
        self.main.push_busy(tr("testing"))

        def job():
            server = self.ctx.servers.get(server_id)
            from ssh_desk.services.connection_service import CliHostKeyGate

            return self.ctx.connections.test(server, gate=CliHostKeyGate())

        def done(result):
            self.btn_test.setEnabled(True)
            if result.ok:
                self.main.toast_success(tr("connection_ok", ms=result.latency_ms))
            else:
                self.main.toast_error(f"{tr('connection_failed')}: {result.message}")

        def fail(exc):
            self.btn_test.setEnabled(True)
            self.main.toast_error(f"{tr('connection_failed')}: {exc}")

        self._run_worker("test", job, done, fail)

    def delete_selected(self):
        server_id = self._selected_id()
        if server_id is None:
            return
        server = self.ctx.servers.get(server_id)
        if ConfirmDialog.ask(self, tr("confirm"), tr("confirm_delete_server", name=server.alias)):
            try:
                self.ctx.servers.delete(server_id)
                self.main.toast_success(tr("server_deleted"))
            except SshDeskError as exc:
                self.main.toast_error(str(exc))
            self.reload()

    def duplicate_selected(self):
        server_id = self._selected_id()
        if server_id is None:
            return
        try:
            dup = self.ctx.servers.duplicate(server_id)
            self.main.toast_success(f"{tr('saved')}: {dup.alias}")
        except SshDeskError as exc:
            self.main.toast_error(str(exc))
        self.reload()

    def toggle_favorite(self):
        server_id = self._selected_id()
        if server_id is None:
            return
        self.ctx.servers.toggle_favorite(server_id)
        self.reload()

    def copy_alias(self):
        server_id = self._selected_id()
        if server_id is None:
            return
        server = self.ctx.servers.get(server_id)
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(server.alias)
        self.main.toast_info(tr("copied"))

    def _context_menu(self, pos):
        menu = QMenu(self)
        actions = {
            tr("connect"): lambda: self._with_selected(self.main.connect_server),
            tr("test"): self.test_selected,
            tr("details"): self.details_selected,
            tr("edit"): self.edit_selected,
            tr("duplicate"): self.duplicate_selected,
            tr("favorite"): self.toggle_favorite,
            tr("copy") + " alias": self.copy_alias,
            tr("delete"): self.delete_selected,
        }
        for text, handler in actions.items():
            action = QAction(text, self)
            action.triggered.connect(handler)
            menu.addAction(action)
        menu.exec(self.table.viewport().mapToGlobal(pos))


def _session_scan():
    from ssh_desk.utils.procs import list_sessions

    return list_sessions()


def QMeta_reload(page):
    # event bus callbacks arrive from arbitrary threads; schedule on the UI thread
    from PySide6.QtCore import QTimer

    QTimer.singleShot(0, page.reload)
