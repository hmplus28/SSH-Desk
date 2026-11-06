"""Saved commands page: define and run ready-made commands per server or globally."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ssh_desk.core.exceptions import SshDeskError
from ssh_desk.gui.i18n import tr
from ssh_desk.gui.widgets_common import ConfirmDialog, EmptyState, Page
from ssh_desk.utils.validation import CommandInput


class CommandDialog(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle(tr("new_command"))
        form = QFormLayout(self)
        self.name = QLineEdit()
        self.server_combo = QComboBox()
        self.server_combo.addItem(tr("global_cmd"), None)
        for server in ctx.servers.list_servers():
            self.server_combo.addItem(server.alias, server.id)
        self.command = QPlainTextEdit()
        self.command.setFixedHeight(80)
        self.description = QLineEdit()
        self.category = QLineEdit()
        self.category.setPlaceholderText("maintenance, deploy, monitoring")
        self.confirm_box = QCheckBox(tr("requires_confirm"))
        form.addRow(tr("name"), self.name)
        form.addRow(tr("page_servers"), self.server_combo)
        form.addRow(tr("command"), self.command)
        form.addRow(tr("description"), self.description)
        form.addRow(tr("category"), self.category)
        form.addRow("", self.confirm_box)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self):
        return (
            CommandInput(
                name=self.name.text().strip(),
                command=self.command.toPlainText().strip(),
                description=self.description.text().strip(),
                category=self.category.text().strip(),
                requires_confirmation=self.confirm_box.isChecked(),
            ),
            self.server_combo.currentData(),
        )


class CommandsPage(Page):
    def __init__(self, ctx, main):
        super().__init__(ctx, main)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        header = QHBoxLayout()
        self.title = QLabel()
        self.title.setProperty("role", "title")
        header.addWidget(self.title)
        header.addStretch(1)
        self.btn_new = QPushButton(tr("new_command"))
        self.btn_new.setProperty("role", "primary")
        self.btn_new.clicked.connect(self.new_command)
        header.addWidget(self.btn_new)
        self.btn_edit = QPushButton(tr("edit"))
        self.btn_edit.clicked.connect(self.edit_command)
        header.addWidget(self.btn_edit)
        self.btn_run = QPushButton(tr("run"))
        self.btn_run.setProperty("role", "primary")
        self.btn_run.clicked.connect(self.run_command)
        header.addWidget(self.btn_run)
        self.btn_delete = QPushButton(tr("delete"))
        self.btn_delete.setProperty("role", "danger")
        self.btn_delete.clicked.connect(self.delete_command)
        header.addWidget(self.btn_delete)
        root.addLayout(header)

        self.table = QTableWidget(0, 5)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)
        self.empty = EmptyState(tr("commands_empty"), self)
        self.retranslate()

    def retranslate(self):
        self.title.setText(tr("page_commands"))
        self.table.setHorizontalHeaderLabels([tr("name"), tr("command"), tr("page_servers"), tr("category"), "🔒"])

    def refresh(self):
        commands = self.ctx.servers.list_commands("any")
        self.table.setRowCount(len(commands))
        for i, cmd in enumerate(commands):
            server_alias = "-"
            if cmd.server_id:
                try:
                    server_alias = self.ctx.servers.get(cmd.server_id).alias
                except SshDeskError:
                    server_alias = "?"
            self.table.setItem(i, 0, QTableWidgetItem(cmd.name))
            self.table.setItem(i, 1, QTableWidgetItem(cmd.command[:80]))
            self.table.setItem(i, 2, QTableWidgetItem(server_alias))
            self.table.setItem(i, 3, QTableWidgetItem(cmd.category or "-"))
            lock = QTableWidgetItem("🔒" if cmd.requires_confirmation else "")
            lock.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 4, lock)
        self.table.resizeColumnsToContents()
        self.empty.setVisible(len(commands) == 0)
        self.empty.setGeometry(self.table.rect())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.empty.setGeometry(self.table.rect())

    def _selected(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        return self.ctx.servers.list_commands("any")[row]

    def new_command(self):
        dialog = CommandDialog(self.ctx, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data, server_id = dialog.values()
            try:
                self.ctx.servers.create_command(data, server_id=server_id)
            except SshDeskError as exc:
                self.main.toast_error(str(exc))
            self.refresh()

    def edit_command(self):
        cmd = self._selected()
        if not cmd:
            return
        dialog = CommandDialog(self.ctx, self)
        dialog.name.setText(cmd.name)
        dialog.command.setPlainText(cmd.command)
        dialog.description.setText(cmd.description or "")
        dialog.category.setText(cmd.category or "")
        dialog.confirm_box.setChecked(cmd.requires_confirmation)
        if cmd.server_id:
            index = dialog.server_combo.findData(cmd.server_id)
            dialog.server_combo.setCurrentIndex(max(0, index))
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data, server_id = dialog.values()
        try:
            self.ctx.servers.update_command(cmd.id, data, server_id=server_id)
        except SshDeskError as exc:
            self.main.toast_error(str(exc))
        self.refresh()

    def delete_command(self):
        cmd = self._selected()
        if not cmd:
            return
        if ConfirmDialog.ask(self, tr("confirm"), f"{cmd.name} - {tr('delete')}?"):
            self.ctx.servers.delete_command(cmd.id)
            self.refresh()

    def run_command(self):
        cmd = self._selected()
        if not cmd:
            return
        if cmd.server_id is None:
            servers = self.ctx.servers.list_servers()
            if not servers:
                self.main.toast_error(tr("servers_empty"))
                return
            from PySide6.QtWidgets import QInputDialog

            names = [s.alias for s in servers]
            alias, ok_flag = QInputDialog.getItem(self, tr("select_server"), tr("select_server"), names, 0, False)
            if not ok_flag:
                return
            server = next(s for s in servers if s.alias == alias)
        else:
            server = self.ctx.servers.get(cmd.server_id)
        if cmd.requires_confirmation:
            if not ConfirmDialog.ask(self, tr("confirm"),
                                     tr("confirm_run_command", server=server.alias, command=cmd.command)):
                return
        self.main.run_saved_command(server, cmd)
