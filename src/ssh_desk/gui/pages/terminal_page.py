"""Terminal page: multi-tab real PTY sessions."""


from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
)

from ssh_desk.gui.i18n import tr
from ssh_desk.gui.terminal_widget import TerminalWidget
from ssh_desk.gui.widgets_common import EmptyState, Page


class TerminalPage(Page):
    def __init__(self, ctx, main):
        super().__init__(ctx, main)
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 8)

        toolbar = QHBoxLayout()
        self.btn_new = QPushButton(tr("new_session"))
        self.btn_new.setProperty("role", "primary")
        self.btn_new.clicked.connect(self.main.open_new_session_picker)
        toolbar.addWidget(self.btn_new)
        self.btn_kill = QPushButton(tr("end_session"))
        self.btn_kill.clicked.connect(self.close_current_tab)
        toolbar.addWidget(self.btn_kill)
        self.btn_copy = QPushButton(tr("copy"))
        self.btn_copy.clicked.connect(self._copy)
        toolbar.addWidget(self.btn_copy)
        self.btn_paste = QPushButton(tr("paste"))
        self.btn_paste.clicked.connect(self._paste)
        toolbar.addWidget(self.btn_paste)
        self.btn_font_plus = QPushButton("A+")
        self.btn_font_plus.setFixedWidth(44)
        self.btn_font_plus.clicked.connect(lambda: self._change_font(+1))
        toolbar.addWidget(self.btn_font_plus)
        self.btn_font_minus = QPushButton("A-")
        self.btn_font_minus.setFixedWidth(44)
        self.btn_font_minus.clicked.connect(lambda: self._change_font(-1))
        toolbar.addWidget(self.btn_font_minus)
        toolbar.addStretch(1)
        root.addLayout(toolbar)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        root.addWidget(self.tabs, 1)

        self.empty = EmptyState(tr("terminal_empty"), self)
        self.retranslate()

    def retranslate(self):
        self.btn_new.setText(tr("new_session"))
        self.btn_kill.setText(tr("end_session"))
        self.btn_copy.setText(tr("copy"))
        self.btn_paste.setText(tr("paste"))

    def refresh(self):
        self.empty.setVisible(self.tabs.count() == 0)
        self.empty.setGeometry(self.tabs.rect())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.empty.setGeometry(self.tabs.rect())

    # ------------------------------------------------------------- sessions
    def open_session(self, prepared, label: str) -> TerminalWidget | None:
        font_size = int(self.ctx.settings.get("terminal_font_size", 11))
        widget = TerminalWidget(prepared.argv, prepared.env, label, font_size)
        index = self.tabs.addTab(widget, f"▸ {label}")
        self.tabs.setCurrentIndex(index)
        widget.title_changed.connect(lambda title, w=widget: self._update_tab_title(w, title))
        widget.session_closed.connect(lambda code, w=widget: self._session_closed(w, code))
        widget.destroyed.connect(lambda *_: self.refresh())
        self.refresh()
        return widget

    def _update_tab_title(self, widget, title):
        index = self.tabs.indexOf(widget)
        if index >= 0:
            base = widget.label
            self.tabs.setTabText(index, f"▸ {base}" if not title else f"▸ {base} — {title[:24]}")

    def _session_closed(self, widget, code):
        index = self.tabs.indexOf(widget)
        if index >= 0:
            self.tabs.setTabText(index, f"⏹ {widget.label} ({code})")

    def current_widget(self) -> TerminalWidget | None:
        return self.tabs.currentWidget()

    def close_current_tab(self):
        if self.tabs.currentIndex() >= 0:
            self.close_tab(self.tabs.currentIndex())

    def close_tab(self, index: int):
        widget = self.tabs.widget(index)
        if not widget:
            return
        self.tabs.removeTab(index)
        widget.shutdown()
        widget.deleteLater()
        self.refresh()

    def _copy(self):
        widget = self.current_widget()
        if widget:
            QApplication_copy(widget)

    def _paste(self):
        widget = self.current_widget()
        if widget:
            widget.paste_clipboard()

    def _change_font(self, delta: int):
        widget = self.current_widget()
        if widget:
            widget.set_font_size(widget.font_size() + delta)
            self.ctx.settings.set("terminal_font_size", widget.font_size())


def QApplication_copy(widget):

    widget._copy_selection()
