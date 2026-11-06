"""Toast notifications (top-right overlay with fade in/out)."""

from PySide6.QtCore import QPropertyAnimation, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from ssh_desk.gui.i18n import current_language

_COLORS = {
    "info": ("#4f8cff", "#eaf1ff"),
    "success": ("#2fbf71", "#e9fbf2"),
    "error": ("#e5484d", "#fdeced"),
    "warning": ("#e8a33d", "#fdf5e7"),
}


class Toast(QFrame):
    def __init__(self, text: str, kind: str = "info", parent=None):
        super().__init__(parent)
        self.kind = kind
        accent, bg = _COLORS.get(kind, _COLORS["info"])
        self.setStyleSheet(
            f"QFrame {{ background: {bg}; border: 1px solid {accent}; border-radius: 10px; }}"
            "QLabel { background: transparent; border: none; color: #1d2330; font-size: 13px; }"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        label = QLabel(text)
        label.setWordWrap(True)
        layout.addWidget(label)
        self.setFixedHeight(46)
        self.adjustSize()

    def enterEvent(self, event):  # keep visible while hovered
        super().enterEvent(event)


class ToastManager(QWidget):
    def __init__(self, window: QWidget):
        super().__init__(window)
        self.parent_window = window
        self._toasts: list[Toast] = []

    def _place(self, toast: Toast, index: int):
        toast.adjustSize()
        margin = 16
        y = margin + index * (toast.height() + 8)
        x = self.parent_window.width() - toast.width() - margin
        if current_language() == "fa":
            x = margin
        toast.move(x, y)

    def notify(self, text: str, kind: str = "info", timeout: int = 3500):
        toast = Toast(text, kind, self.parent_window)
        toast.show()
        self._toasts.append(toast)
        self._relayout()
        eff = QPropertyAnimation(toast, b"windowOpacity")
        eff.setDuration(1)
        QTimer.singleShot(timeout, lambda: self._dismiss(toast))

    def _dismiss(self, toast: Toast):
        if toast in self._toasts:
            self._toasts.remove(toast)
        toast.hide()
        toast.deleteLater()
        self._relayout()

    def _relayout(self):
        for i, toast in enumerate(self._toasts):
            self._place(toast, i)

    # convenience API used by pages
    def info(self, text: str):
        self.notify(text, "info")

    def success(self, text: str):
        self.notify(text, "success")

    def error(self, text: str):
        self.notify(text, "error", timeout=6000)

    def warning(self, text: str):
        self.notify(text, "warning", timeout=5000)
