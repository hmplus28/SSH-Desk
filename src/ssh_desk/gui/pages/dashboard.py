"""Dashboard: stats, favorites quick-connect, recent connections, SSH engine status."""

import shutil
import subprocess

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ssh_desk.gui.i18n import tr
from ssh_desk.gui.widgets_common import Page


class StatCard(QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.setProperty("role", "statCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        self.value = QLabel("0")
        self.value.setProperty("role", "statValue")
        self.title = QLabel(title)
        self.title.setProperty("role", "dim")
        layout.addWidget(self.value)
        layout.addWidget(self.title)

    def set_value(self, value, title=None):
        self.value.setText(str(value))
        if title:
            self.title.setText(title)


class DashboardPage(Page):
    def __init__(self, ctx, main):
        super().__init__(ctx, main)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(14)

        header = QHBoxLayout()
        self.title = QLabel()
        self.title.setProperty("role", "title")
        header.addWidget(self.title)
        header.addStretch(1)
        self.btn_new = QPushButton()
        self.btn_new.setProperty("role", "primary")
        self.btn_new.clicked.connect(self.main.open_new_server)
        header.addWidget(self.btn_new)
        self.btn_terminal = QPushButton()
        self.btn_terminal.clicked.connect(self.main.open_new_session_picker)
        header.addWidget(self.btn_terminal)
        root.addLayout(header)

        stats = QGridLayout()
        stats.setSpacing(12)
        self.card_total = StatCard("")
        self.card_sessions = StatCard("")
        self.card_favorites = StatCard("")
        self.card_tunnels = StatCard("")
        for i, card in enumerate((self.card_total, self.card_sessions, self.card_favorites, self.card_tunnels)):
            stats.addWidget(card, 0, i)
        root.addLayout(stats)

        ssh_row = QHBoxLayout()
        self.ssh_label = QLabel()
        self.ssh_label.setProperty("role", "dim")
        ssh_row.addWidget(self.ssh_label)
        ssh_row.addStretch(1)
        root.addLayout(ssh_row)

        self.favorites_title = QLabel()
        self.favorites_title.setProperty("role", "subtitle")
        root.addWidget(self.favorites_title)
        self.fav_row = QHBoxLayout()
        self.fav_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        root.addLayout(self.fav_row)

        self.recent_title = QLabel()
        self.recent_title.setProperty("role", "subtitle")
        root.addWidget(self.recent_title)
        self.recent_table = QTableWidget(0, 5)
        self.recent_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.recent_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.recent_table.verticalHeader().setVisible(False)
        self.recent_table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.recent_table, 1)
        self.retranslate()

    def retranslate(self):
        self.title.setText(tr("page_dashboard"))
        self.btn_new.setText(tr("add_server"))
        self.btn_terminal.setText(tr("new_session"))
        self.favorites_title.setText(tr("quick_connect"))
        self.recent_title.setText(tr("recent_connections"))
        self.card_total.set_value(self.card_total.value.text(), tr("stat_total_servers"))
        self.card_sessions.set_value(self.card_sessions.value.text(), tr("stat_active_sessions"))
        self.card_favorites.set_value(self.card_favorites.value.text(), tr("stat_favorites"))
        self.card_tunnels.set_value(self.card_tunnels.value.text(), tr("stat_tunnels"))
        self._fill_recent_headers()

    def _fill_recent_headers(self):
        self.recent_table.setHorizontalHeaderLabels(
            [tr("alias"), tr("host"), tr("when"), tr("duration"), tr("status")]
        )

    def refresh(self):
        stats = self.ctx.servers.stats()
        self.card_total.set_value(stats["total_servers"], tr("stat_total_servers"))
        self.card_sessions.set_value(stats["active_sessions"], tr("stat_active_sessions"))
        self.card_favorites.set_value(stats["favorites"], tr("stat_favorites"))
        self.card_tunnels.set_value(stats["tunnels_running"], tr("stat_tunnels"))

        if shutil.which("ssh"):
            self.ssh_label.setText(f"✔ {tr('ssh_ready')}")
        else:
            self.ssh_label.setText(f"✘ {tr('ssh_missing')}")

        # favorites quick connect
        while self.fav_row.count():
            item = self.fav_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        favorites = [s for s in self.ctx.servers.list_servers() if s.favorite][:6]
        if not favorites:
            favorites = self.ctx.servers.recent_servers(6)
        if not favorites:
            empty = QLabel(tr("dash_empty"))
            empty.setProperty("role", "dim")
            self.fav_row.addWidget(empty)
        for server in favorites:
            chip = QPushButton(f"▸ {server.alias}")
            chip.setToolTip(f"{server.username}@{server.host}:{server.port}")
            chip.clicked.connect(lambda _=False, sid=server.id: self.main.connect_server(sid))
            self.fav_row.addWidget(chip)

        self._fill_recent_headers()
        rows = self.ctx.history.recent(10)
        self.recent_table.setRowCount(len(rows))
        for i, h in enumerate(rows):
            values = [h.server_alias, "", h.connected_at.strftime("%Y-%m-%d %H:%M"),
                      str(h.duration_seconds or 0) + "s", h.status]
            server = None
            try:
                server = self.ctx.servers.get(h.server_id) if h.server_id else None
            except Exception:
                server = None
            if server:
                values[1] = f"{server.username}@{server.host}:{server.port}"
            for j, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.recent_table.setItem(i, j, item)
        self.recent_table.resizeColumnsToContents()
