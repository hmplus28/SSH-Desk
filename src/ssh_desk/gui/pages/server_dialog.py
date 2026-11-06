"""Add/Edit server dialog with General / Authentication / Connection / Advanced tabs."""


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
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ssh_desk.core.exceptions import SshDeskError
from ssh_desk.gui.i18n import tr
from ssh_desk.utils.validation import PathInput, ServerInput


class ServerDialog(QDialog):
    def __init__(self, ctx, parent=None, server_id: int | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self.server_id = server_id
        self.server = ctx.servers.get(server_id) if server_id else None
        self.setWindowTitle(tr("edit_server") if self.server else tr("add_server"))
        self.setModal(True)
        self.setMinimumSize(640, 560)
        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: #e5484d;")

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_general(), tr("tab_general"))
        self.tabs.addTab(self._build_auth(), tr("tab_auth"))
        self.tabs.addTab(self._build_connection(), tr("tab_connection"))
        self.tabs.addTab(self._build_advanced(), tr("tab_advanced"))

        buttons = QDialogButtonBox()
        self.btn_save = QPushButton(tr("save"))
        self.btn_save.setProperty("role", "primary")
        self.btn_test = QPushButton(tr("test"))
        cancel = QPushButton(tr("cancel"))
        buttons.addButton(self.btn_test, QDialogButtonBox.ButtonRole.ActionRole)
        buttons.addButton(cancel, QDialogButtonBox.ButtonRole.RejectRole)
        buttons.addButton(self.btn_save, QDialogButtonBox.ButtonRole.AcceptRole)
        self.btn_test.clicked.connect(self._test_connection)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addWidget(self._error_label)
        layout.addWidget(buttons)
        if self.server:
            self._load()

    # ------------------------------------------------------------ tabs
    def _build_general(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.f_name = QLineEdit()
        self.f_alias = QLineEdit()
        self.f_host = QLineEdit()
        self.f_port = QSpinBox()
        self.f_port.setRange(1, 65535)
        self.f_port.setValue(int(self.ctx.settings.get("default_port", 22)))
        self.f_user = QLineEdit()
        self.f_desc = QPlainTextEdit()
        self.f_desc.setFixedHeight(64)
        self.f_tags = QLineEdit()
        self.f_tags.setPlaceholderText("web, production, ubuntu")
        self.f_group = QComboBox()
        self._fill_groups()
        form.addRow(tr("name"), self.f_name)
        form.addRow(tr("alias"), self.f_alias)
        form.addRow(tr("host"), self.f_host)
        form.addRow(tr("port"), self.f_port)
        form.addRow(tr("username"), self.f_user)
        form.addRow(tr("group"), self.f_group)
        form.addRow(tr("tags"), self.f_tags)
        form.addRow(tr("description"), self.f_desc)
        return page

    def _fill_groups(self):
        self.f_group.clear()
        self.f_group.addItem(tr("none"), None)
        for group in self.ctx.servers.list_groups():
            self.f_group.addItem(group.name, group.id)

    def _build_auth(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.f_auth = QComboBox()
        for value, label in (
            ("password", tr("auth_password")),
            ("key", tr("auth_key")),
            ("agent", tr("auth_agent")),
            ("interactive", tr("auth_interactive")),
        ):
            self.f_auth.addItem(label, value)
        self.f_auth.currentIndexChanged.connect(self._auth_changed)
        form.addRow(tr("auth_method"), self.f_auth)

        self.f_password = QLineEdit()
        self.f_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.f_store_secret = QCheckBox(tr("store_password"))
        self.f_store_secret.setChecked(True)
        form.addRow(tr("password"), self.f_password)
        form.addRow("", self.f_store_secret)

        self.f_key = QComboBox()
        for key in self.ctx.keys.list():
            self.f_key.addItem(f"{key.name} ({key.key_type})", key.private_key_path)
        self.f_key.setEditable(True)
        browse = QPushButton("...")
        browse.setFixedWidth(36)
        browse.clicked.connect(self._browse_key)
        key_row = QHBoxLayout()
        key_row.addWidget(self.f_key)
        key_row.addWidget(browse)
        form.addRow(tr("select_key"), key_row)
        self._auth_note = QLabel("")
        self._auth_note.setProperty("role", "dim")
        self._auth_note.setWordWrap(True)
        form.addRow("", self._auth_note)
        return page

    def _browse_key(self):
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(self, tr("select_key"), str(__import__("pathlib").Path.home() / ".ssh"))
        if path:
            self.f_key.setCurrentText(path)

    def _build_connection(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.f_default_path = QLineEdit()
        self.f_default_path.setPlaceholderText("/var/www")
        form.addRow(tr("default_path"), self.f_default_path)
        self.f_timeout = QSpinBox()
        self.f_timeout.setRange(1, 600)
        self.f_timeout.setValue(int(self.ctx.settings.get("connect_timeout", 15)))
        form.addRow(tr("timeout"), self.f_timeout)
        self.f_keepalive = QSpinBox()
        self.f_keepalive.setRange(0, 3600)
        self.f_keepalive.setValue(int(self.ctx.settings.get("keep_alive", 30)))
        form.addRow(tr("keepalive"), self.f_keepalive)
        self.f_compression = QCheckBox(tr("compression"))
        form.addRow("", self.f_compression)
        self.f_agent = QCheckBox(tr("forward_agent"))
        form.addRow("", self.f_agent)
        form.addRow(QLabel(tr("saved_paths")))
        self.paths_table = QTableWidget(0, 3)
        self.paths_table.setHorizontalHeaderLabels([tr("path_name"), tr("path_value"), tr("is_default")])
        self.paths_table.horizontalHeader().setStretchLastSection(True)
        self.paths_table.setColumnWidth(0, 140)
        self.paths_table.setColumnWidth(1, 320)
        self.paths_table.setFixedHeight(150)
        form.addRow(self.paths_table)
        path_buttons = QHBoxLayout()
        btn_add_path = QPushButton("+")
        btn_add_path.setFixedWidth(40)
        btn_add_path.clicked.connect(self._add_path_row)
        btn_del_path = QPushButton("−")
        btn_del_path.setFixedWidth(40)
        btn_del_path.clicked.connect(self._del_path_row)
        path_buttons.addWidget(btn_add_path)
        path_buttons.addWidget(btn_del_path)
        path_buttons.addStretch(1)
        form.addRow(path_buttons)
        return page

    def _add_path_row(self, name="", path="", is_default=False):
        row = self.paths_table.rowCount()
        self.paths_table.insertRow(row)
        self.paths_table.setItem(row, 0, QTableWidgetItem(name))
        self.paths_table.setItem(row, 1, QTableWidgetItem(path))
        default_item = QTableWidgetItem()
        default_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
        default_item.setCheckState(Qt.CheckState.Checked if is_default else Qt.CheckState.Unchecked)
        self.paths_table.setItem(row, 2, default_item)

    def _del_path_row(self):
        row = self.paths_table.currentRow()
        if row >= 0:
            self.paths_table.removeRow(row)

    def _build_advanced(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.f_jump = QComboBox()
        self.f_jump.addItem(tr("none"), None)
        for server in self.ctx.servers.list_servers():
            if self.server and server.id == self.server.id:
                continue
            self.f_jump.addItem(f"{server.alias} ({server.host})", server.id)
        form.addRow(tr("jump_host"), self.f_jump)
        self.f_pref_auth = QLineEdit()
        self.f_pref_auth.setPlaceholderText("publickey,password,keyboard-interactive")
        form.addRow(tr("preferred_auth"), self.f_pref_auth)
        self.f_custom = QPlainTextEdit()
        self.f_custom.setPlaceholderText("AddressFamily inet\nBindInterface eth0")
        self.f_custom.setFixedHeight(90)
        form.addRow(tr("custom_options"), self.f_custom)
        return page

    # ------------------------------------------------------------ helpers
    def _auth_changed(self):
        auth = self.f_auth.currentData()
        self.f_password.setEnabled(auth == "password")
        self.f_store_secret.setEnabled(auth == "password")
        self.f_key.setEnabled(auth == "key")
        notes = {
            "password": tr("auth_password"),
            "key": tr("auth_key"),
            "agent": tr("auth_agent"),
            "interactive": tr("auth_interactive"),
        }
        self._auth_note.setText(notes.get(auth, ""))

    def _load(self):
        s = self.server
        self.f_name.setText(s.name)
        self.f_alias.setText(s.alias)
        self.f_host.setText(s.host)
        self.f_port.setValue(s.port)
        self.f_user.setText(s.username)
        self.f_desc.setPlainText(s.description or "")
        self.f_tags.setText(", ".join(s.tags or []))
        if s.group_id:
            index = self.f_group.findData(s.group_id)
            self.f_group.setCurrentIndex(max(0, index))
        index = self.f_auth.findData(s.auth_type)
        self.f_auth.setCurrentIndex(max(0, index))
        if s.private_key_path:
            self.f_key.setCurrentText(s.private_key_path)
        if s.default_path:
            self.f_default_path.setText(s.default_path)
        self.f_timeout.setValue(s.connection_timeout)
        self.f_keepalive.setValue(s.keep_alive)
        self.f_compression.setChecked(bool(s.compression))
        self.f_agent.setChecked(bool(s.forward_agent))
        if s.jump_host_id:
            index = self.f_jump.findData(s.jump_host_id)
            self.f_jump.setCurrentIndex(max(0, index))
        if s.preferred_auth:
            self.f_pref_auth.setText(s.preferred_auth)
        for option in s.custom_options or []:
            self.f_custom.setPlainText(self.f_custom.toPlainText() + option + "\n")
        self.paths_table.setRowCount(0)
        for p in s.paths:
            self._add_path_row(p.name, p.path, p.is_default)
        self._auth_changed()

    def _collect(self) -> tuple[ServerInput | None, dict]:
        try:
            data = ServerInput(
                name=self.f_name.text().strip() or self.f_alias.text().strip(),
                alias=self.f_alias.text().strip(),
                host=self.f_host.text().strip(),
                port=self.f_port.value(),
                username=self.f_user.text().strip(),
                auth_type=self.f_auth.currentData(),
                default_path=self.f_default_path.text().strip() or None,
                connection_timeout=self.f_timeout.value(),
                keep_alive=self.f_keepalive.value(),
            )
        except Exception as exc:
            self._show_error(str(exc).replace("\n", " ")[:300])
            return None, {}
        paths = []
        for row in range(self.paths_table.rowCount()):
            name = self.paths_table.item(row, 0).text().strip()
            path = self.paths_table.item(row, 1).text().strip()
            is_default = self.paths_table.item(row, 2).checkState() == Qt.CheckState.Checked
            if name and path:
                paths.append(PathInput(name=name, path=path, is_default=is_default))
        custom = [line.strip() for line in self.f_custom.toPlainText().splitlines() if line.strip()]
        kwargs = dict(
            group_id=self.f_group.currentData(),
            jump_host_id=self.f_jump.currentData(),
            private_key_path=self.f_key.currentText().strip() if self.f_auth.currentData() == "key" else None,
            description=self.f_desc.toPlainText().strip(),
            tags=[t.strip() for t in self.f_tags.text().split(",") if t.strip()],
            compression=self.f_compression.isChecked(),
            forward_agent=self.f_agent.isChecked(),
            custom_options=custom,
            preferred_auth=self.f_pref_auth.text().strip() or None,
            paths=paths,
        )
        if self.f_auth.currentData() == "password" and self.f_password.text():
            kwargs["secret"] = self.f_password.text()
        return data, kwargs

    def _show_error(self, message: str):
        self._error_label.setText(f"✘ {message}")

    def _save(self):
        data, kwargs = self._collect()
        if data is None:
            return
        try:
            if self.server:
                self.ctx.servers.update(self.server.id, data, **kwargs)
            else:
                self.ctx.servers.create(data, **kwargs)
        except SshDeskError as exc:
            hint = f"\nhint: {exc.hint}" if exc.hint else ""
            self._show_error(f"{exc}{hint}")
            return
        self.accept()

    def _test_connection(self):
        data, kwargs = self._collect()
        if data is None:
            return
        self.btn_test.setEnabled(False)
        self._show_error("")
        self._error_label.setText(tr("testing"))
        password = kwargs.get("secret")
        temp_server = type("S", (), {})()
        for attr in ("host", "port", "username", "auth_type", "secret_ref", "private_key_path",
                     "connection_timeout", "keep_alive", "compression", "forward_agent",
                     "custom_options", "preferred_auth", "jump_host_id", "alias"):
            setattr(temp_server, attr, getattr(data, attr, None) or kwargs.get(attr))
        temp_server.secret_ref = None
        temp_server.host = data.host
        temp_server.port = data.port
        temp_server.username = data.username
        temp_server.auth_type = data.auth_type
        temp_server.private_key_path = kwargs.get("private_key_path")
        temp_server.connection_timeout = data.connection_timeout
        temp_server.keep_alive = data.keep_alive
        temp_server.jump_host_id = kwargs.get("jump_host_id")
        temp_server.custom_options = kwargs.get("custom_options", [])
        temp_server.preferred_auth = kwargs.get("preferred_auth")

        def job():
            if data.auth_type == "password" and password:
                return self.ctx.connections.test(temp_server, password_override=password)
            if data.auth_type == "key" and temp_server.private_key_path:
                key_record = self.ctx.keys.get_by_path(temp_server.private_key_path)
                if key_record and key_record.passphrase_ref:
                    temp_server.key_passphrase_ref = key_record.passphrase_ref
            from ssh_desk.services.connection_service import CliHostKeyGate

            return self.ctx.connections.test(temp_server, gate=CliHostKeyGate())

        def done(result):
            self.btn_test.setEnabled(True)
            self._error_label.setText("")
            if result.ok:
                QMessageBox.information(self, tr("test"), tr("connection_ok", ms=result.latency_ms))
            else:
                QMessageBox.warning(self, tr("test"), f"{tr('connection_failed')}: {result.message}")

        def fail(exc):
            self.btn_test.setEnabled(True)
            self._error_label.setText("")
            QMessageBox.critical(self, tr("test"), f"{type(exc).__name__}: {exc}")

        from ssh_desk.gui.widgets_common import GenericWorker

        worker = GenericWorker(job)
        worker.signals.done.connect(done)
        worker.signals.failed.connect(fail)
        worker.start()
        self._test_worker = worker
