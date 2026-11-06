"""Files page: two-pane SFTP file manager (local <-> remote) with full operations."""

import os
from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFileSystemModel,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from ssh_desk.gui.i18n import tr
from ssh_desk.gui.widgets_common import ConfirmDialog, EmptyState, Page


def _fmt_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return str(value)


class FilesPage(Page):
    def __init__(self, ctx, main):
        super().__init__(ctx, main)
        self.session = None
        self.server = None
        self.remote_path = "/"
        self.watcher = QFileSystemWatcher(self)
        self.watcher.fileChanged.connect(self._watched_file_changed)
        self._pending_upload = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 10)
        bar = QHBoxLayout()
        self.server_combo = QComboBox()
        for server in ctx.servers.list_servers():
            self.server_combo.addItem(f"{server.alias} ({server.host})", server.id)
        self.btn_connect = QPushButton(tr("connect"))
        self.btn_connect.setProperty("role", "primary")
        self.btn_connect.clicked.connect(self._connect)
        self.btn_disconnect = QPushButton(tr("disconnect"))
        self.btn_disconnect.clicked.connect(self._disconnect)
        self.btn_disconnect.hide()
        bar.addWidget(QLabel(tr("select_server")))
        bar.addWidget(self.server_combo, 1)
        bar.addWidget(self.btn_connect)
        bar.addWidget(self.btn_disconnect)
        root.addLayout(bar)

        self.status_label = QLabel(tr("files_not_connected"))
        self.status_label.setProperty("role", "dim")
        root.addWidget(self.status_label)

        panes = QHBoxLayout()
        # local pane
        local_box = QVBoxLayout()
        local_head = QHBoxLayout()
        local_head.addWidget(QLabel(tr("local")))
        local_head.addStretch(1)
        local_box.addLayout(local_head)
        self.local_model = QFileSystemModel(self)
        self.local_model.setRootPath(str(Path.home()))
        self.local_tree = QTreeView()
        self.local_tree.setModel(self.local_model)
        self.local_tree.setRootIndex(self.local_model.index(str(Path.home())))
        for col in (1, 2, 3):
            self.local_tree.hideColumn(col)
        self.local_tree.doubleClicked.connect(self._local_double_clicked)
        local_box.addWidget(self.local_tree, 1)
        # remote pane
        remote_box = QVBoxLayout()
        remote_head = QHBoxLayout()
        remote_head.addWidget(QLabel(tr("remote")))
        self.btn_up = QPushButton("↑")
        self.btn_up.setFixedWidth(36)
        self.btn_up.clicked.connect(self._go_up)
        self.path_edit = QLineEdit()
        self.path_edit.returnPressed.connect(self._load_remote)
        btn_refresh = QPushButton("⟳")
        btn_refresh.setFixedWidth(36)
        btn_refresh.clicked.connect(self._load_remote)
        remote_head.addWidget(self.btn_up)
        remote_head.addWidget(self.path_edit, 1)
        remote_head.addWidget(btn_refresh)
        remote_box.addLayout(remote_head)
        self.remote_table = QTableWidget(0, 4)
        self.remote_table.verticalHeader().setVisible(False)
        self.remote_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.remote_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.remote_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.remote_table.customContextMenuRequested.connect(self._remote_menu)
        self.remote_table.doubleClicked.connect(self._remote_double_clicked)
        remote_box.addWidget(self.remote_table, 1)
        left = QWidget(); left.setLayout(local_box)
        right = QWidget(); right.setLayout(remote_box)
        panes.addWidget(left, 1)
        panes.addWidget(right, 1)
        root.addLayout(panes, 1)

        actions = QHBoxLayout()
        self.btn_upload = QPushButton(tr("upload"))
        self.btn_upload.clicked.connect(self._upload)
        self.btn_download = QPushButton(tr("download"))
        self.btn_download.clicked.connect(self._download)
        self.btn_mkdir = QPushButton(tr("mkdir"))
        self.btn_mkdir.clicked.connect(self._mkdir)
        self.btn_edit = QPushButton(tr("edit_file"))
        self.btn_edit.clicked.connect(self._edit_remote)
        self.btn_transfer = QPushButton(tr("transfer_to"))
        self.btn_transfer.clicked.connect(self._transfer)
        for btn in (self.btn_upload, self.btn_download, self.btn_mkdir, self.btn_edit, self.btn_transfer):
            actions.addWidget(btn)
        actions.addStretch(1)
        root.addLayout(actions)

        self.empty = EmptyState(tr("files_not_connected"), self)
        self.retranslate()
        self._set_actions_enabled(False)

    def retranslate(self):
        self.remote_table.setHorizontalHeaderLabels([tr("name"), tr("size"), tr("modified"), tr("permissions")])
        self.remote_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

    def _set_actions_enabled(self, enabled: bool):
        for btn in (self.btn_upload, self.btn_download, self.btn_mkdir, self.btn_edit, self.btn_transfer, self.btn_up):
            btn.setEnabled(enabled)

    def refresh(self):
        pass

    # ------------------------------------------------------------- connect
    def _connect(self):
        server_id = self.server_combo.currentData()
        if not server_id:
            return
        self.btn_connect.setEnabled(False)
        self.status_label.setText(tr("loading"))

        def job():
            server = self.ctx.servers.get(server_id)
            from ssh_desk.gui.widgets_common import HostKeyGate

            session = self.ctx.sftp.connect(server, gate=HostKeyGate(self.main))
            return session

        def done(session):
            self.btn_connect.setEnabled(True)
            self.session = session
            self.server = session.server
            self.btn_disconnect.show()
            self.status_label.setText(f"✔ {tr('files_connected')}: {self.server.alias}")
            self._set_actions_enabled(True)
            self.remote_path = self.server.default_path or "/"
            self._load_remote()

        def fail(exc):
            self.btn_connect.setEnabled(True)
            self.status_label.setText(f"✘ {type(exc).__name__}: {exc}")
            self.main.toast_error(str(exc))

        self._run_worker("sftp", job, done, fail)

    def _disconnect(self):
        if self.server:
            self.ctx.sftp.disconnect(self.server.id)
        self.session = None
        self.server = None
        self.btn_disconnect.hide()
        self.btn_connect.setEnabled(True)
        self.status_label.setText(tr("files_not_connected"))
        self.remote_table.setRowCount(0)
        self._set_actions_enabled(False)

    # ------------------------------------------------------------- navigation
    def _load_remote(self):
        if not self.session:
            return
        path = self.path_edit.text().strip() or self.remote_path
        self.remote_table.setRowCount(0)
        self.status_label.setText(tr("loading"))

        def job():
            return path, self.session.list_dir(path)

        def done(result):
            path, entries = result
            self.remote_path = path
            self.path_edit.setText(path)
            self.status_label.setText(f"✔ {self.server.alias}:{path}")
            self.remote_table.setRowCount(len(entries))
            for i, entry in enumerate(entries):
                name_item = QTableWidgetItem(("📁 " if entry.is_dir else "") + entry.name)
                name_item.setData(Qt.ItemDataRole.UserRole, entry)
                self.remote_table.setItem(i, 0, name_item)
                self.remote_table.setItem(i, 1, QTableWidgetItem("-" if entry.is_dir else _fmt_size(entry.size)))
                import datetime as _dt

                mtime = _dt.datetime.fromtimestamp(entry.mtime).strftime("%Y-%m-%d %H:%M") if entry.mtime else "-"
                self.remote_table.setItem(i, 2, QTableWidgetItem(mtime))
                self.remote_table.setItem(i, 3, QTableWidgetItem(entry.permissions))
            self.remote_table.resizeColumnsToContents()
            self.remote_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        def fail(exc):
            self.status_label.setText(f"✘ {exc}")
            self.main.toast_error(str(exc))

        self._run_worker("ls", job, done, fail)

    def _go_up(self):
        if not self.session:
            return
        parent = os.path.dirname(self.remote_path.rstrip("/")) or "/"
        self.path_edit.setText(parent)
        self._load_remote()

    def _remote_double_clicked(self, index):
        entry = self.remote_table.item(index.row(), 0).data(Qt.ItemDataRole.UserRole)
        if entry and entry.is_dir:
            self.path_edit.setText(f"{self.remote_path.rstrip('/')}/{entry.name}")
            self._load_remote()

    def _local_double_clicked(self, index):
        path = self.local_model.filePath(index)
        if path and os.path.isdir(path):
            self.local_tree.setRootIndex(self.local_model.index(path))

    def _selected_remote(self):
        row = self.remote_table.currentRow()
        if row < 0:
            return None
        return self.remote_table.item(row, 0).data(Qt.ItemDataRole.UserRole)

    def _remote_full(self, name: str) -> str:
        return f"{self.remote_path.rstrip('/')}/{name}"

    def _local_cwd(self) -> str:
        index = self.local_tree.rootIndex()
        return self.local_model.filePath(index) or str(Path.home())

    def _selected_local(self) -> str:
        indexes = self.local_tree.selectedIndexes()
        if not indexes:
            return self._local_cwd()
        return self.local_model.filePath(indexes[0])

    # ------------------------------------------------------------- operations
    def _with_progress(self, label, job, done):

        self.btn_connect.setEnabled(False)

        def wrapped_done(result):
            self.btn_connect.setEnabled(True)
            done(result)

        def wrapped_fail(exc):
            self.btn_connect.setEnabled(True)
            self.main.toast_error(f"{type(exc).__name__}: {exc}")

        self._run_worker(label, job, wrapped_done, wrapped_fail)

    def _upload(self):
        if not self.session:
            return
        path, _ = QFileDialog.getOpenFileName(self, tr("upload"), self._local_cwd())
        if not path:
            return
        remote = self._remote_full(os.path.basename(path))
        job = lambda: self.session.upload(path, remote, self._progress)
        self._with_progress("upload", job, lambda _r: (self._load_remote(), self.main.toast_success(tr("saved"))))

    def _download(self):
        if not self.session:
            return
        entry = self._selected_remote()
        if not entry:
            return
        remote = self._remote_full(entry.name)
        local, _ = QFileDialog.getSaveFileName(self, tr("download"), str(Path.home() / entry.name))
        if not local:
            return
        job = lambda: self.session.download(remote, local, self._progress)
        self._with_progress("download", job, lambda _r: self.main.toast_success(tr("saved")))

    def _progress(self, done_bytes, total):
        if total:
            percent = int(done_bytes * 100 / total)
            self.status_label.setText(f"{percent}%  ({_fmt_size(done_bytes)} / {_fmt_size(total)})")

    def _mkdir(self):
        if not self.session:
            return
        name, ok_flag = QInputDialog.getText(self, tr("mkdir"), tr("name"))
        if not ok_flag or not name.strip():
            return
        job = lambda: self.session.mkdir(self._remote_full(name.strip()))
        self._with_progress("mkdir", job, lambda _r: self._load_remote())

    def _rename_entry(self):
        entry = self._selected_remote()
        if not entry:
            return
        new_name, ok_flag = QInputDialog.getText(self, tr("rename"), tr("name"), text=entry.name)
        if not ok_flag or not new_name.strip() or new_name == entry.name:
            return
        job = lambda: self.session.rename(self._remote_full(entry.name), self._remote_full(new_name.strip()))
        self._with_progress("rename", job, lambda _r: self._load_remote())

    def _delete_entry(self):
        entry = self._selected_remote()
        if not entry:
            return
        if not ConfirmDialog.ask(self, tr("confirm"), tr("confirm_delete_file", name=entry.name)):
            return
        remote = self._remote_full(entry.name)
        if entry.is_dir and not entry.is_link:
            job = lambda: self.session.remove_tree(remote, lambda p: self.status_label.setText(p))
        else:
            job = lambda: self.session.remove_file(remote)
        self._with_progress("delete", job, lambda _r: self._load_remote())

    def _chmod_entry(self):
        entry = self._selected_remote()
        if not entry:
            return
        mode, ok_flag = QInputDialog.getText(self, tr("chmod"), "0o644", text=oct(entry.permissions and 0 or 0))
        if not ok_flag:
            return
        try:
            mode_value = int(mode, 8)
        except ValueError:
            self.main.toast_error(tr("invalid_octal"))
            return
        job = lambda: self.session.chmod(self._remote_full(entry.name), mode_value)
        self._with_progress("chmod", job, lambda _r: self._load_remote())

    def _edit_remote(self):
        if not self.session:
            return
        entry = self._selected_remote()
        if not entry or entry.is_dir:
            return
        remote = self._remote_full(entry.name)
        from ssh_desk.services.sftp_service import open_local_temp

        local = open_local_temp(suffix=Path(entry.name).suffix or ".txt")

        def done(_r):
            self._pending_upload[str(local)] = remote
            self.watcher.addPath(str(local))
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices

            QDesktopServices.openUrl(QUrl.fromLocalFile(str(local)))

        self._with_progress("download", lambda: self.session.download(remote, str(local)), done)

    def _watched_file_changed(self, path):
        remote = self._pending_upload.get(path)
        if not remote or not self.session:
            return
        answer = QMessageBox.question(self, tr("upload"), f"{path}\n→ {remote} ?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self._with_progress("upload", lambda: self.session.upload(path, remote), lambda _r: self._load_remote())

    def _transfer(self):
        entry = self._selected_remote()
        if not entry or not self.session:
            return
        servers = [s for s in self.ctx.servers.list_servers() if not self.server or s.id != self.server.id]
        if not servers:
            self.main.toast_error(tr("no_other_server"))
            return
        names = [s.alias for s in servers]
        name, ok_flag = QInputDialog.getItem(self, tr("transfer_to"), tr("select_server"), names, 0, False)
        if not ok_flag:
            return
        target_server = next(s for s in servers if s.alias == name)
        dst_path, ok_flag = QInputDialog.getText(self, tr("transfer_to"), tr("path"),
                                                 text=f"{target_server.default_path or '/tmp'}/{entry.name}")
        if not ok_flag or not dst_path.strip():
            return
        src_server = self.server

        def job():
            from ssh_desk.gui.widgets_common import HostKeyGate

            return self.ctx.sftp.transfer(
                src_server, self._remote_full(entry.name), target_server, dst_path.strip(),
                self._progress, gate=HostKeyGate(self.main),
            )

        self._with_progress("transfer", job, lambda r: self.main.toast_success(f"→ {r}"))

    def _remote_menu(self, pos):
        from PySide6.QtGui import QAction
        from PySide6.QtWidgets import QMenu

        menu = QMenu(self)
        actions = [
            (tr("download"), self._download),
            (tr("upload"), self._upload),
            (tr("rename"), self._rename_entry),
            (tr("chmod"), self._chmod_entry),
            (tr("delete"), self._delete_entry),
            (tr("transfer_to"), self._transfer),
            (tr("edit_file"), self._edit_remote),
        ]
        for text, handler in actions:
            action = QAction(text, self)
            action.triggered.connect(handler)
            menu.addAction(action)
        menu.exec(self.remote_table.viewport().mapToGlobal(pos))
