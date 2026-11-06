"""Connection history page with filters."""

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ssh_desk.gui.i18n import tr
from ssh_desk.gui.widgets_common import ConfirmDialog, EmptyState, Page
from ssh_desk.cli.output import fmt_duration


class HistoryPage(Page):
    def __init__(self, ctx, main):
        super().__init__(ctx, main)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        header = QHBoxLayout()
        self.title = QLabel()
        self.title.setProperty("role", "title")
        header.addWidget(self.title)
        header.addStretch(1)
        self.server_filter = QComboBox()
        self.server_filter.addItem(tr("all_groups"), None)
        for server in ctx.servers.list_servers():
            self.server_filter.addItem(server.alias, server.id)
        self.server_filter.currentIndexChanged.connect(self.refresh)
        header.addWidget(self.server_filter)
        self.status_filter = QComboBox()
        for value, label in (("", tr("all_groups")), ("connected", tr("connected")), ("closed", tr("closed")),
                             ("failed", tr("failed"))):
            self.status_filter.addItem(label, value)
        self.status_filter.currentIndexChanged.connect(self.refresh)
        header.addWidget(self.status_filter)
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(5, 500)
        self.limit_spin.setValue(50)
        self.limit_spin.valueChanged.connect(self.refresh)
        header.addWidget(self.limit_spin)
        self.btn_clear = QPushButton(tr("clear_history"))
        self.btn_clear.setProperty("role", "danger")
        self.btn_clear.clicked.connect(self.clear_history)
        header.addWidget(self.btn_clear)
        root.addLayout(header)

        self.table = QTableWidget(0, 5)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        root.addWidget(self.table, 1)
        self.empty = EmptyState(tr("history_empty"), self)
        self.retranslate()

    def retranslate(self):
        self.title.setText(tr("page_history"))
        self.table.setHorizontalHeaderLabels([tr("page_servers"), tr("when"), tr("duration"), tr("status"), tr("error")])

    def refresh(self, *_args):
        server_id = self.server_filter.currentData()
        status = self.status_filter.currentData() or ""
        rows = self.ctx.history.list(server_id=server_id, status=status, limit=self.limit_spin.value())
        self.table.setRowCount(len(rows))
        for i, h in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(h.server_alias))
            self.table.setItem(i, 1, QTableWidgetItem(h.connected_at.strftime("%Y-%m-%d %H:%M:%S")))
            self.table.setItem(i, 2, QTableWidgetItem(fmt_duration(h.duration_seconds)))
            self.table.setItem(i, 3, QTableWidgetItem(h.status))
            error_item = QTableWidgetItem((h.error_message or "-")[:70])
            error_item.setToolTip(h.error_message or "")
            self.table.setItem(i, 4, error_item)
        self.table.resizeColumnsToContents()
        self.empty.setVisible(len(rows) == 0)
        self.empty.setGeometry(self.table.rect())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.empty.setGeometry(self.table.rect())

    def clear_history(self):
        if ConfirmDialog.ask(self, tr("confirm"), tr("confirm_clear_history")):
            self.ctx.history.clear()
            self.refresh()
