"""SSH keys page: generate, import, export, delete, install guide."""

import shutil
import subprocess
from pathlib import Path

from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ssh_desk.core.events import TOPIC_KEYS
from ssh_desk.core.exceptions import SshDeskError
from ssh_desk.gui.i18n import tr
from ssh_desk.gui.widgets_common import ConfirmDialog, EmptyState, Page


class GenerateKeyDialog(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle(tr("generate_key"))
        form = QFormLayout(self)
        self.name = QLineEdit()
        self.key_type = QComboBox()
        self.key_type.addItems(["ed25519", "rsa", "ecdsa"])
        self.comment = QLineEdit()
        self.comment.setText(f"{__import__('getpass').getuser()}@ssh-desk")
        self.passphrase = QLineEdit()
        self.passphrase.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow(tr("name"), self.name)
        form.addRow(tr("key_type"), self.key_type)
        form.addRow("Comment", self.comment)
        form.addRow(tr("passphrase"), self.passphrase)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)


class ImportKeyDialog(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle(tr("import_key"))
        form = QFormLayout(self)
        self.name = QLineEdit()
        self.path = QLineEdit()
        browse = QPushButton("...")
        browse.setFixedWidth(40)
        browse.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addWidget(self.path)
        row.addWidget(browse)
        self.copy_box = QCheckBox("Copy into SSH Desk storage (0600)")
        form.addRow(tr("name"), self.name)
        form.addRow("Private key", row)
        form.addRow("", self.copy_box)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("import_key"), str(Path.home() / ".ssh"))
        if path:
            self.path.setText(path)
            if not self.name.text():
                self.name.setText(Path(path).name)


class KeysPage(Page):
    def __init__(self, ctx, main):
        super().__init__(ctx, main)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        header = QHBoxLayout()
        self.title = QLabel()
        self.title.setProperty("role", "title")
        header.addWidget(self.title)
        header.addStretch(1)
        self.btn_generate = QPushButton(tr("generate_key"))
        self.btn_generate.setProperty("role", "primary")
        self.btn_generate.clicked.connect(self.generate)
        header.addWidget(self.btn_generate)
        self.btn_import = QPushButton(tr("import_key"))
        self.btn_import.clicked.connect(self.import_key)
        header.addWidget(self.btn_import)
        self.btn_export = QPushButton(tr("export_pub"))
        self.btn_export.clicked.connect(self.export_pub)
        header.addWidget(self.btn_export)
        self.btn_guide = QPushButton(tr("install_guide"))
        self.btn_guide.clicked.connect(self.install_guide)
        header.addWidget(self.btn_guide)
        self.btn_delete = QPushButton(tr("delete"))
        self.btn_delete.setProperty("role", "danger")
        self.btn_delete.clicked.connect(self.delete_key)
        header.addWidget(self.btn_delete)
        root.addLayout(header)

        self.table = QTableWidget(0, 4)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)
        self.empty = EmptyState(tr("keys_empty"), self)
        self.ctx.events.subscribe(TOPIC_KEYS, lambda _p: self._schedule_reload())
        self.retranslate()

    def retranslate(self):
        self.title.setText(tr("page_keys"))
        self.table.setHorizontalHeaderLabels([tr("name"), tr("key_type"), tr("fingerprint"), tr("path")])

    def _schedule_reload(self):
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, self.refresh)

    def refresh(self):
        keys = self.ctx.keys.list()
        self.table.setRowCount(len(keys))
        for i, key in enumerate(keys):
            self.table.setItem(i, 0, QTableWidgetItem(key.name))
            self.table.setItem(i, 1, QTableWidgetItem(key.key_type))
            fp = QTableWidgetItem(key.fingerprint or "-")
            fp.setFont(__import__("PySide6.QtGui", fromlist=["QFont"]).QFont("DejaVu Sans Mono"))
            self.table.setItem(i, 2, fp)
            self.table.setItem(i, 3, QTableWidgetItem(key.private_key_path))
        self.table.resizeColumnsToContents()
        self.empty.setVisible(len(keys) == 0)
        self.empty.setGeometry(self.table.rect())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.empty.setGeometry(self.table.rect())

    def _selected(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        return self.ctx.keys.list()[row]

    def generate(self):
        dialog = GenerateKeyDialog(self.ctx, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            key = self.ctx.keys.generate(
                name=dialog.name.text().strip(),
                key_type=dialog.key_type.currentText(),
                comment=dialog.comment.text().strip(),
                passphrase=dialog.passphrase.text(),
            )
            self.main.toast_success(f"{tr('saved')}: {key.name}")
        except SshDeskError as exc:
            self.main.toast_error(str(exc))
        self.refresh()

    def import_key(self):
        dialog = ImportKeyDialog(self.ctx, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            key = self.ctx.keys.import_key(
                name=dialog.name.text().strip(),
                private_path=dialog.path.text().strip(),
                copy_into_store=dialog.copy_box.isChecked(),
            )
            self.main.toast_success(f"{tr('saved')}: {key.name}")
        except SshDeskError as exc:
            self.main.toast_error(str(exc))
        self.refresh()

    def export_pub(self):
        key = self._selected()
        if not key:
            return
        try:
            public = self.ctx.keys.export_public(key.id)
        except SshDeskError as exc:
            self.main.toast_error(str(exc))
            return
        path, _ = QFileDialog.getSaveFileName(self, tr("export_pub"), f"{key.name}.pub")
        if path:
            Path(path).write_text(public + "\n")
            self.main.toast_success(f"→ {path}")

    def delete_key(self):
        key = self._selected()
        if not key:
            return
        if not ConfirmDialog.ask(self, tr("confirm"), tr("confirm_delete_key", name=key.name)):
            return
        self.ctx.keys.delete(key.id, delete_files=bool(key.stored_copy))
        self.refresh()

    def install_guide(self):
        key = self._selected()
        if not key:
            return
        servers = self.ctx.servers.list_servers()
        if not servers:
            self.main.toast_error(tr("servers_empty"))
            return
        from PySide6.QtWidgets import QInputDialog

        names = [s.alias for s in servers]
        alias, ok_flag = QInputDialog.getItem(self, tr("install_guide"), tr("select_server"), names, 0, False)
        if not ok_flag:
            return
        server = next(s for s in servers if s.alias == alias)
        try:
            public = self.ctx.keys.export_public(key.id)
        except SshDeskError as exc:
            self.main.toast_error(str(exc))
            return
        pub_file = Path(self.ctx.data_dir / "tmp-pub-key.pub")
        pub_file.write_text(public + "\n")
        command = f"ssh-copy-id -i {pub_file} -p {server.port} {server.username}@{server.host}"
        box = QMessageBox(self)
        box.setWindowTitle(tr("install_guide"))
        box.setText(f"{tr('copy_id_cmd')}\n\n<code>{command}</code>")
        run_btn = box.addButton(tr("run"), QMessageBox.ButtonRole.ActionRole)
        box.addButton(tr("close"), QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is run_btn:
            self._run_ssh_copy_id(command)

    def _run_ssh_copy_id(self, command: str):
        argv = shlex_split(command)
        if not shutil.which(argv[0]):
            self.main.toast_error("ssh-copy-id not found")
            return
        self.main.open_raw_terminal(argv, [], "ssh-copy-id")


def shlex_split(command: str):
    import shlex

    return shlex.split(command)
