"""Settings page: interface, SSH defaults, CLI command, keyring, backup/restore/import."""

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ssh_desk.core.exceptions import SshDeskError
from ssh_desk.gui.i18n import tr
from ssh_desk.gui.widgets_common import ConfirmDialog, Page


class SettingsPage(Page):
    def __init__(self, ctx, main):
        super().__init__(ctx, main)
        self.settings = ctx.settings
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        self.title = QLabel()
        self.title.setProperty("role", "title")
        root.addWidget(self.title)

        # ---- interface
        iface = QGroupBox(tr("theme") + " / " + tr("language"))
        form = QFormLayout(iface)
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(tr("dark"), "dark")
        self.theme_combo.addItem(tr("light"), "light")
        self.theme_combo.currentIndexChanged.connect(self._theme_changed)
        form.addRow(tr("theme"), self.theme_combo)
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("English", "en")
        self.lang_combo.addItem("فارسی", "fa")
        self.lang_combo.currentIndexChanged.connect(self._lang_changed)
        form.addRow(tr("language"), self.lang_combo)
        self.font_spin = QSpinBox()
        self.font_spin.setRange(6, 28)
        self.font_spin.setValue(int(self.settings.get("terminal_font_size", 11)))
        self.font_spin.valueChanged.connect(lambda v: self.settings.set("terminal_font_size", v))
        form.addRow(tr("terminal_font"), self.font_spin)
        root.addWidget(iface)

        # ---- ssh defaults
        ssh = QGroupBox("SSH")
        form2 = QFormLayout(ssh)
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(int(self.settings.get("default_port", 22)))
        self.port_spin.valueChanged.connect(lambda v: self.settings.set("default_port", v))
        form2.addRow(tr("default_port"), self.port_spin)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 600)
        self.timeout_spin.setValue(int(self.settings.get("connect_timeout", 15)))
        self.timeout_spin.valueChanged.connect(lambda v: self.settings.set("connect_timeout", v))
        form2.addRow(tr("timeout"), self.timeout_spin)
        self.keepalive_spin = QSpinBox()
        self.keepalive_spin.setRange(0, 3600)
        self.keepalive_spin.setValue(int(self.settings.get("keep_alive", 30)))
        self.keepalive_spin.valueChanged.connect(lambda v: self.settings.set("keep_alive", v))
        form2.addRow(tr("keepalive"), self.keepalive_spin)
        root.addWidget(ssh)

        # ---- cli
        cli = QGroupBox("CLI")
        form3 = QFormLayout(cli)
        cli_row = QHBoxLayout()
        self.cli_name = QLineEdit(self.settings.cli_command_name)
        self.btn_cli_apply = QPushButton(tr("apply"))
        self.btn_cli_apply.setProperty("role", "primary")
        self.btn_cli_apply.clicked.connect(self._apply_cli_name)
        self.btn_completions = QPushButton("completions")
        self.btn_completions.clicked.connect(self._install_completions)
        cli_row.addWidget(self.cli_name, 1)
        cli_row.addWidget(self.btn_cli_apply)
        cli_row.addWidget(self.btn_completions)
        form3.addRow(tr("cli_command_name"), cli_row)
        self.cli_hint = QLabel(f"$ {self.settings.cli_command_name} prod  •  $ {self.settings.cli_command_name} prod nginx")
        self.cli_hint.setProperty("role", "dim")
        form3.addRow("", self.cli_hint)
        root.addWidget(cli)

        # ---- security
        security = QGroupBox(tr("keyring_status"))
        form4 = QFormLayout(security)
        self.keyring_label = QLabel()
        form4.addRow(tr("keyring_status"), self.keyring_label)
        self.btn_purge = QPushButton(tr("purge_secrets"))
        self.btn_purge.setProperty("role", "danger")
        self.btn_purge.clicked.connect(self._purge_secrets)
        form4.addRow("", self.btn_purge)
        root.addWidget(security)

        # ---- data
        data = QGroupBox(tr("backup"))
        form5 = QFormLayout(data)
        data_row = QHBoxLayout()
        self.btn_backup = QPushButton(tr("backup"))
        self.btn_backup.clicked.connect(self._backup)
        self.btn_restore = QPushButton(tr("restore"))
        self.btn_restore.clicked.connect(self._restore)
        self.btn_import = QPushButton(tr("import_ssh_config"))
        self.btn_import.clicked.connect(self._import_ssh_config)
        self.include_secrets = QCheckBox(tr("include_secrets"))
        data_row.addWidget(self.btn_backup)
        data_row.addWidget(self.btn_restore)
        data_row.addWidget(self.btn_import)
        data_row.addWidget(self.include_secrets)
        data_row.addStretch(1)
        form5.addRow(data_row)
        self.paths_label = QLabel(f"DB: {ctx.db.path}\nConfig: {self.settings.path}\nData: {ctx.data_dir}")
        self.paths_label.setProperty("role", "dim")
        form5.addRow(self.paths_label)
        root.addWidget(data)
        root.addStretch(1)

    def retranslate(self):
        self.title.setText(tr("settings"))

    def refresh(self):
        available = self.ctx.credentials.available()
        self.keyring_label.setText(f"{'✔' if available else '✘'} {tr('keyring_ok') if available else tr('keyring_missing')}")
        theme = self.settings.get("theme", "dark")
        index = self.theme_combo.findData(theme)
        if index >= 0:
            self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentIndex(index)
            self.theme_combo.blockSignals(False)
        lang = self.settings.get("language", "en")
        index = self.lang_combo.findData(lang)
        if index >= 0:
            self.lang_combo.blockSignals(True)
            self.lang_combo.setCurrentIndex(index)
            self.lang_combo.blockSignals(False)

    def _theme_changed(self):
        theme = self.theme_combo.currentData()
        self.settings.set("theme", theme)
        self.main.apply_theme(theme)
        self.main.toast_success(tr("settings_saved"))

    def _lang_changed(self):
        lang = self.lang_combo.currentData()
        self.settings.set("language", lang)
        self.main.apply_language(lang)
        self.main.toast_success(tr("settings_saved"))

    def _apply_cli_name(self):
        name = self.cli_name.text().strip()
        current = self.settings.cli_command_name
        if name == current and self.settings.get("installed_cli_name"):
            return
        from ssh_desk.cli.shell_integration import install_cli_name

        try:
            previous = self.settings.get("installed_cli_name", "") or current
            install_cli_name(name, previous)
            self.settings.set("cli_command_name", name)
            self.settings.set("installed_cli_name", name)
            self.cli_hint.setText(f"$ {name} prod  •  $ {name} prod nginx")
            self.main.toast_success(tr("cli_renamed"))
        except SshDeskError as exc:
            QMessageBox.warning(self, tr("error"), str(exc))

    def _install_completions(self):
        from ssh_desk.cli.shell_integration import install_completions

        path = install_completions("bash", self.settings.cli_command_name)
        self.main.toast_success(f"bash → {path}")

    def _purge_secrets(self):
        if not ConfirmDialog.ask(self, tr("confirm"), tr("confirm_purge")):
            return
        try:
            count = self.ctx.credentials.purge_all()
            self.main.toast_success(f"{count} ✘")
        except SshDeskError as exc:
            self.main.toast_error(str(exc))

    def _backup(self):
        path, _ = QFileDialog.getSaveFileName(self, tr("backup"), "ssh-desk-backup.toml", "TOML (*.toml)")
        if not path:
            return
        try:
            report = self.ctx.transfer.export_toml(
                path, include_secrets=self.include_secrets.isChecked(), include_history=True
            )
            self.main.toast_success(f"{tr('backup')}: {report['file']}")
        except SshDeskError as exc:
            self.main.toast_error(str(exc))

    def _restore(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("restore"), "", "TOML (*.toml)")
        if not path:
            return
        try:
            report = self.ctx.transfer.import_toml(path, restore_secrets=not self.include_secrets.isChecked())
            self.main.toast_success(
                f"{tr('restore')}: {report['servers']} ✓, {report['skipped']} ⏭"
            )
        except SshDeskError as exc:
            self.main.toast_error(str(exc))

    def _import_ssh_config(self):
        try:
            rows = self.ctx.transfer.preview_ssh_config()
        except SshDeskError as exc:
            self.main.toast_error(str(exc))
            return
        if not rows:
            self.main.toast_info("0")
            return
        summary = "\n".join(
            f"• {r.entry.host} → {r.alias}" + ("  ✔" if r.exists else "") for r in rows[:20]
        )
        answer = QMessageBox.question(
            self, tr("import_ssh_config"),
            f"{len(rows)} hosts:\n\n{summary}\n\n{tr('apply')}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            for row in rows:
                row.selected = not row.exists
            report = self.ctx.transfer.apply_ssh_import(rows)
            self.main.toast_success(f"{report['created']} ✓")
