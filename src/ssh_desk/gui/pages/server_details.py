"""Server details page: full info, masked password with secure reveal, paths, history."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ssh_desk.core.exceptions import SshDeskError
from ssh_desk.gui.i18n import tr
from ssh_desk.gui.widgets_common import Page, SecretConfirmDialog


class ServerDetailsPage(Page):
    def __init__(self, ctx, main):
        super().__init__(ctx, main)
        self.server = None
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)

        header = QHBoxLayout()
        self.title = QLabel()
        self.title.setProperty("role", "title")
        header.addWidget(self.title)
        header.addStretch(1)
        self.btn_edit = QPushButton(tr("edit"))
        self.btn_edit.clicked.connect(self._edit)
        header.addWidget(self.btn_edit)
        self.btn_connect = QPushButton(tr("connect"))
        self.btn_connect.setProperty("role", "primary")
        self.btn_connect.clicked.connect(self._connect)
        header.addWidget(self.btn_connect)
        root.addLayout(header)

        self.grid = QGridLayout()
        self.grid.setContentsMargins(0, 8, 0, 8)
        root.addLayout(self.grid)
        self._rows = []

        secret_row = QHBoxLayout()
        self.secret_label = QLabel("••••••••••")
        secret_row.addWidget(self.secret_label)
        self.btn_reveal = QPushButton(tr("show_password"))
        self.btn_reveal.clicked.connect(self._reveal)
        secret_row.addWidget(self.btn_reveal)
        self.btn_copy = QPushButton(tr("copy"))
        self.btn_copy.clicked.connect(self._copy_secret)
        self.btn_copy.hide()
        secret_row.addWidget(self.btn_copy)
        secret_row.addStretch(1)
        root.addLayout(secret_row)

        self.paths_title = QLabel()
        self.paths_title.setProperty("role", "subtitle")
        root.addWidget(self.paths_title)
        self.paths_table = QTableWidget(0, 3)
        self.paths_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.paths_table.verticalHeader().setVisible(False)
        self.paths_table.horizontalHeader().setStretchLastSection(True)
        self.paths_table.setFixedHeight(120)
        root.addWidget(self.paths_table)

        self.history_title = QLabel()
        self.history_title.setProperty("role", "subtitle")
        root.addWidget(self.history_title)
        self.history_table = QTableWidget(0, 5)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.history_table, 1)
        self._reveal_timer = QTimer(self)
        self._reveal_timer.setSingleShot(True)
        self._reveal_timer.timeout.connect(self._hide_secret)

    def set_server(self, server_id: int):
        self.server = self.ctx.servers.get(server_id)
        self.refresh()

    def _add_field(self, label: str, value: str):
        row = len(self._rows)
        name = QLabel(label)
        name.setProperty("role", "dim")
        name.setFixedWidth(170)
        val = QLabel(value)
        val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.grid.addWidget(name, row, 0)
        self.grid.addWidget(val, row, 1)
        self._rows.append((name, val))

    def refresh(self):
        if not self.server:
            return
        try:
            self.server = self.ctx.servers.get(self.server.id)
        except SshDeskError:
            self.main.show_page("servers")
            return
        for widget in self._rows:
            widget[0].deleteLater()
            widget[1].deleteLater()
        self._rows = []
        s = self.server
        self.title.setText(f"{s.name} ({s.alias})")
        self._add_field(tr("alias"), s.alias)
        self._add_field(tr("host"), f"{s.host}:{s.port}")
        self._add_field(tr("username"), s.username)
        self._add_field(tr("auth_method"), s.auth_type)
        if s.private_key_path:
            self._add_field("Key", s.private_key_path)
        self._add_field(tr("default_path"), s.default_path or "-")
        self._add_field(tr("group"), s.group.name if s.group else "-")
        self._add_field(tr("tags"), ", ".join(s.tags or []) or "-")
        if s.jump_host_id:
            jump = self.ctx.servers.get(s.jump_host_id)
            self._add_field(tr("jump_host"), jump.alias)
        last = self.ctx.servers.last_connection(s.id)
        if last:
            self._add_field(tr("last_connection"), f"{last.connected_at:%Y-%m-%d %H:%M} ({last.status})")
        if s.description:
            self._add_field(tr("description"), s.description)

        self.secret_label.setText("••••••••••")
        self.btn_reveal.setText(tr("show_password"))
        self.btn_copy.hide()

        self.paths_table.setHorizontalHeaderLabels([tr("path_name"), tr("path_value"), tr("is_default")])
        self.paths_table.setRowCount(len(s.paths))
        for i, p in enumerate(s.paths):
            self.paths_table.setItem(i, 0, QTableWidgetItem(p.name))
            self.paths_table.setItem(i, 1, QTableWidgetItem(p.path))
            self.paths_table.setItem(i, 2, QTableWidgetItem("*" if p.is_default else ""))
        self.paths_table.resizeColumnsToContents()

        self.history_table.setHorizontalHeaderLabels(
            [tr("when"), tr("status"), tr("duration"), tr("error"), ""]
        )
        history = self.ctx.history.list(server_id=s.id, limit=10)
        self.history_table.setRowCount(len(history))
        for i, h in enumerate(history):
            self.history_table.setItem(i, 0, QTableWidgetItem(h.connected_at.strftime("%Y-%m-%d %H:%M")))
            self.history_table.setItem(i, 1, QTableWidgetItem(h.status))
            self.history_table.setItem(i, 2, QTableWidgetItem(f"{h.duration_seconds or 0}s"))
            self.history_table.setItem(i, 3, QTableWidgetItem((h.error_message or "-")[:60]))
        self.history_table.resizeColumnsToContents()

    def _hide_secret(self):
        self.secret_label.setText("••••••••••")
        self.btn_reveal.setText(tr("show_password"))
        self.btn_copy.hide()

    def _reveal(self):
        if not self.server:
            return
        if self.secret_label.text() != "••••••••••":
            self._hide_secret()
            return
        dialog = SecretConfirmDialog(self.server.alias, self)
        if dialog.exec() != SecretConfirmDialog.DialogCode.Accepted or not dialog.accepted_value():
            return
        try:
            secret = self.ctx.credentials.get_server_password(self.server)
        except SshDeskError as exc:
            self.main.toast_error(str(exc))
            return
        if secret:
            self.secret_label.setText(secret)
            self.btn_reveal.setText(tr("hide_password"))
            self.btn_copy.show()
            self._reveal_timer.start(20000)
        else:
            self.main.toast_warning(tr("none"))

    def _copy_secret(self):
        from PySide6.QtWidgets import QApplication

        if not self.server:
            return
        try:
            secret = self.ctx.credentials.get_server_password(self.server)
        except SshDeskError as exc:
            self.main.toast_error(str(exc))
            return
        if secret:
            QApplication.clipboard().setText(secret)
            self.main.toast_success(tr("password_copied"))
            clear_after = int(self.ctx.settings.get("clear_clipboard_after", 30))
            QTimer.singleShot(clear_after * 1000, lambda: QApplication.clipboard().clear())

    def _connect(self):
        if self.server:
            self.main.connect_server(self.server.id)

    def _edit(self):
        if self.server:
            self.main.open_edit_server(self.server.id)
