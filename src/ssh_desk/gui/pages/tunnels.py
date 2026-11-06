"""Tunnels page: create/start/stop local, remote and dynamic (SOCKS) forwards."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ssh_desk.core.exceptions import SshDeskError
from ssh_desk.gui.i18n import tr
from ssh_desk.gui.widgets_common import ConfirmDialog, EmptyState, Page
from ssh_desk.utils.validation import TunnelInput


class TunnelDialog(QDialog):
    def __init__(self, ctx, parent=None, server_id=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle(tr("new_tunnel"))
        form = QFormLayout(self)
        self.name = QLineEdit()
        self.server_combo = QComboBox()
        for server in ctx.servers.list_servers():
            self.server_combo.addItem(server.alias, server.id)
        if server_id:
            index = self.server_combo.findData(server_id)
            self.server_combo.setCurrentIndex(max(0, index))
        self.ttype = QComboBox()
        self.ttype.addItem(tr("local_fwd"), "local")
        self.ttype.addItem(tr("remote_fwd"), "remote")
        self.ttype.addItem(tr("dynamic_fwd"), "dynamic")
        self.ttype.currentIndexChanged.connect(self._type_changed)
        self.local_host = QLineEdit("127.0.0.1")
        self.local_port = QSpinBox()
        self.local_port.setRange(1, 65535)
        self.local_port.setValue(8080)
        self.remote_host = QLineEdit("localhost")
        self.remote_port = QSpinBox()
        self.remote_port.setRange(1, 65535)
        self.remote_port.setValue(80)
        form.addRow(tr("name"), self.name)
        form.addRow(tr("page_servers"), self.server_combo)
        form.addRow(tr("tunnel_type"), self.ttype)
        form.addRow(tr("local_bind"), self.local_host)
        form.addRow(tr("local_port"), self.local_port)
        self.remote_host_label = QLabel(tr("remote_target"))
        form.addRow(self.remote_host_label, self.remote_host)
        self.remote_port_label = QLabel(tr("remote_port"))
        form.addRow(self.remote_port_label, self.remote_port)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        self._type_changed()

    def _type_changed(self):
        dynamic = self.ttype.currentData() == "dynamic"
        for widget in (self.remote_host, self.remote_port, self.remote_host_label, self.remote_port_label):
            widget.setEnabled(not dynamic)

    def values(self):
        return (
            self.name.text().strip(),
            self.server_combo.currentData(),
            TunnelInput(
                tunnel_type=self.ttype.currentData(),
                local_host=self.local_host.text().strip() or "127.0.0.1",
                local_port=self.local_port.value(),
                remote_host=None if self.ttype.currentData() == "dynamic" else self.remote_host.text().strip(),
                remote_port=None if self.ttype.currentData() == "dynamic" else self.remote_port.value(),
            ),
        )


class TunnelsPage(Page):
    def __init__(self, ctx, main):
        super().__init__(ctx, main)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        header = QHBoxLayout()
        self.title = QLabel()
        self.title.setProperty("role", "title")
        header.addWidget(self.title)
        header.addStretch(1)
        self.btn_new = QPushButton(tr("new_tunnel"))
        self.btn_new.setProperty("role", "primary")
        self.btn_new.clicked.connect(self.new_tunnel)
        header.addWidget(self.btn_new)
        self.btn_edit = QPushButton(tr("edit"))
        self.btn_edit.clicked.connect(self.edit_tunnel)
        header.addWidget(self.btn_edit)
        self.btn_start = QPushButton(tr("start"))
        self.btn_start.setProperty("role", "primary")
        self.btn_start.clicked.connect(self.start_tunnel)
        header.addWidget(self.btn_start)
        self.btn_stop = QPushButton(tr("stop"))
        self.btn_stop.clicked.connect(self.stop_tunnel)
        header.addWidget(self.btn_stop)
        self.btn_delete = QPushButton(tr("delete"))
        self.btn_delete.setProperty("role", "danger")
        self.btn_delete.clicked.connect(self.delete_tunnel)
        header.addWidget(self.btn_delete)
        root.addLayout(header)

        self.table = QTableWidget(0, 5)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)
        self.empty = EmptyState(tr("tunnels_empty"), self)
        self.retranslate()

    def retranslate(self):
        self.title.setText(tr("page_tunnels"))
        self.table.setHorizontalHeaderLabels([tr("name"), tr("page_servers"), tr("tunnel_type"), tr("path"), tr("status")])

    def refresh(self):
        try:
            self.ctx.tunnels.refresh_all()
        except SshDeskError:
            pass
        tunnels = self.ctx.tunnels.list()
        self.table.setRowCount(len(tunnels))
        for i, tunnel in enumerate(tunnels):
            binding = (f"socks5://{tunnel.local_host}:{tunnel.local_port}"
                       if tunnel.tunnel_type == "dynamic"
                       else f"{tunnel.local_host}:{tunnel.local_port} → {tunnel.remote_host}:{tunnel.remote_port}")
            self.table.setItem(i, 0, QTableWidgetItem(tunnel.name))
            try:
                server_alias = self.ctx.servers.get(tunnel.server_id).alias
            except SshDeskError:
                server_alias = "?"
            self.table.setItem(i, 1, QTableWidgetItem(server_alias))
            self.table.setItem(i, 2, QTableWidgetItem(tunnel.tunnel_type))
            self.table.setItem(i, 3, QTableWidgetItem(binding))
            status = QTableWidgetItem("● " + tunnel.status)
            status.setForeground(Qt.GlobalColor.green if tunnel.status == "running" else Qt.GlobalColor.gray)
            self.table.setItem(i, 4, status)
        self.table.resizeColumnsToContents()
        self.empty.setVisible(len(tunnels) == 0)
        self.empty.setGeometry(self.table.rect())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.empty.setGeometry(self.table.rect())

    def _selected(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        return self.ctx.tunnels.list()[row]

    def _run_bg(self, job, done):
        from ssh_desk.gui.widgets_common import GenericWorker

        worker = GenericWorker(job)
        worker.signals.done.connect(done)
        worker.signals.failed.connect(lambda exc: self.main.toast_error(f"{type(exc).__name__}: {exc}"))
        worker.start()
        self._workers = getattr(self, "_workers", []) + [worker]

    def new_tunnel(self):
        dialog = TunnelDialog(self.ctx, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name, server_id, data = dialog.values()
        try:
            self.ctx.tunnels.create(server_id, name, data)
        except SshDeskError as exc:
            self.main.toast_error(str(exc))
        self.refresh()

    def edit_tunnel(self):
        tunnel = self._selected()
        if not tunnel:
            return
        if tunnel.status == "running":
            self.main.toast_warning(tr("stop"))
            return
        dialog = TunnelDialog(self.ctx, self, server_id=tunnel.server_id)
        dialog.name.setText(tunnel.name)
        dialog.ttype.setCurrentIndex(["local", "remote", "dynamic"].index(tunnel.tunnel_type))
        dialog.local_host.setText(tunnel.local_host)
        dialog.local_port.setValue(tunnel.local_port)
        if tunnel.remote_host:
            dialog.remote_host.setText(tunnel.remote_host)
        if tunnel.remote_port:
            dialog.remote_port.setValue(tunnel.remote_port)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name, _server_id, data = dialog.values()
        try:
            self.ctx.tunnels.update(tunnel.id, name, data)
        except SshDeskError as exc:
            self.main.toast_error(str(exc))
        self.refresh()

    def start_tunnel(self):
        tunnel = self._selected()
        if not tunnel:
            return
        self._run_bg(lambda: self.ctx.tunnels.start(tunnel.id),
                     lambda _r: (self.refresh(), self.main.toast_success(tr("tunnel_started"))))

    def stop_tunnel(self):
        tunnel = self._selected()
        if not tunnel:
            return
        self._run_bg(lambda: self.ctx.tunnels.stop(tunnel.id),
                     lambda _r: (self.refresh(), self.main.toast_success(tr("tunnel_stopped"))))

    def delete_tunnel(self):
        tunnel = self._selected()
        if not tunnel:
            return
        if ConfirmDialog.ask(self, tr("confirm"), f"{tunnel.name} - {tr('delete')}?"):
            try:
                self.ctx.tunnels.delete(tunnel.id)
            except SshDeskError as exc:
                self.main.toast_error(str(exc))
            self.refresh()

