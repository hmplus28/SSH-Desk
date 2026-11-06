"""Common GUI building blocks: Page base class, workers, empty states, dialogs."""

import threading
import traceback
from typing import Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ssh_desk.core.exceptions import HostKeyChangedError, HostKeyUnknownError
from ssh_desk.gui.i18n import tr


class Page(QWidget):
    """Base page: refreshes on show, supports retranslation and background jobs."""

    def __init__(self, ctx, main_window):
        super().__init__()
        self.ctx = ctx
        self.main = main_window
        self._busy_count = 0

    def showEvent(self, event):
        self.refresh()
        super().showEvent(event)

    def refresh(self):
        pass

    def retranslate(self):
        pass

    # ---- background worker helper -------------------------------------
    def run_worker(self, label: str, fn, on_done=None, on_error=None):
        self._run_worker(label, fn, on_done, on_error, self)

    def _run_worker(self, label, fn, on_done, on_error, widget):
        worker = GenericWorker(fn, widget)
        worker.signals.done.connect(lambda result: self._worker_finished(worker, on_done, result))
        worker.signals.failed.connect(lambda exc_info: self._worker_failed(worker, on_error, exc_info))
        self.main.push_busy(label)
        worker.start()
        return worker

    def _worker_finished(self, worker, callback, result):
        self.main.pop_busy()
        if callback:
            callback(result)

    def _worker_failed(self, worker, callback, exc_info):
        self.main.pop_busy()
        exc_type, exc, tb = exc_info
        if callback:
            callback(exc)
            return
        self.main.toast_error(f"{exc_type.__name__}: {exc}")


class GenericWorker(QThread):
    class Signals(QObject):
        done = Signal(object)
        failed = Signal(object)

    def __init__(self, fn, widget=None):
        super().__init__()
        self.fn = fn
        self.signals = self.Signals()
        self.widget = widget

    def run(self):
        try:
            result = self.fn()
            self.signals.done.emit(result)
        except Exception as exc:  # noqa: BLE001 - forwarded to UI thread
            if self.widget is not None:
                self.widget._last_tb = traceback.format_exc()
            self.signals.failed.emit((type(exc), exc, traceback.format_exc()))


class EmptyState(QFrame):
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setProperty("role", "card")
        layout = QVBoxLayout(self)
        layout.addStretch(1)
        icon = QLabel("⌁")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size: 42px; border: none; background: transparent;")
        self.label = QLabel(text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(True)
        self.label.setStyleSheet("color: palette(mid); font-size: 14px; border: none; background: transparent;")
        layout.addWidget(icon)
        layout.addWidget(self.label)
        layout.addStretch(1)

    def setText(self, text: str):
        self.label.setText(text)


class HostKeyDialog(QDialog):
    """Fingerprint confirmation for unknown host keys."""

    def __init__(self, host: str, entries, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("hostkey_unknown_title"))
        self.setModal(True)
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        message = QLabel(tr("hostkey_unknown_msg", host=host))
        message.setWordWrap(True)
        layout.addWidget(message)
        self.entries = entries
        for entry in entries:
            row = QLabel(f"<code style='font-family: monospace;'>{entry.key_type}&nbsp;&nbsp;{entry.fingerprint}</code>")
            row.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(row)
        buttons = QDialogButtonBox()
        self.accept_btn = QPushButton(tr("hostkey_accept"))
        self.accept_btn.setProperty("role", "primary")
        reject_btn = QPushButton(tr("hostkey_reject"))
        reject_btn.setProperty("role", "danger")
        buttons.addButton(self.accept_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(reject_btn, QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class HostKeyGate(QObject):
    """Bridge for asking host-key questions from worker threads via modal dialogs."""

    def __init__(self, main_window):
        super().__init__(main_window)
        self.main = main_window

    def on_unknown(self, server, entries) -> bool:
        decision = {"value": False}
        event = threading.Event()

        def ask():
            dialog = HostKeyDialog(f"{server.host}:{server.port}", entries, self.main)
            decision["value"] = dialog.exec() == QDialog.DialogCode.Accepted
            event.set()

        from PySide6.QtCore import QMetaObject, Qt as QtConst, Q_ARG, Slot

        self._invoke(ask)
        event.wait()
        return decision["value"]

    def on_changed(self, server, expected, actual) -> bool:
        # A changed host key is a security incident: never silently accepted in GUI.
        raise HostKeyChangedError(
            f"Host key of '{server.host}' has changed!",
            expected=[e.fingerprint for e in expected],
            actual=[e.fingerprint for e in actual],
            hint="If this change is legitimate, remove the old key from "
            "~/.local/share/ssh-desk/known_hosts (or run ssh-keygen -R).",
        )

    @staticmethod
    def _invoke(fn):
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, fn)


class SecretConfirmDialog(QDialog):
    """Reveal-a-secret confirmation: user must type the server alias."""

    def __init__(self, alias: str, parent=None):
        super().__init__(parent)
        self.alias = alias
        self.setWindowTitle(tr("confirm"))
        self.setModal(True)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr("confirm_reveal", alias=alias)))
        self.input = QLineEdit()
        layout.addWidget(self.input)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accepted_value(self) -> bool:
        return self.input.text().strip().lower() == self.alias.lower()


class ConfirmDialog(QDialog):
    @staticmethod
    def ask(parent, title: str, text: str, danger: bool = True) -> bool:
        box = QMessageBox(parent)
        box.setIcon(QMessageBox.Icon.Warning if danger else QMessageBox.Icon.Question)
        box.setWindowTitle(title)
        box.setText(text)
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        return box.exec() == QMessageBox.StandardButton.Yes


class BusyOverlay(QWidget):
    """Thin busy indicator shown at the bottom of the window during workers."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.bar = QProgressBar()
        self.bar.setRange(0, 0)
        self.bar.setFixedHeight(6)
        self.bar.setTextVisible(False)
        self.label = QLabel("")
        self.label.setProperty("role", "dim")
        self.label.setStyleSheet("padding: 2px 10px;")
        layout.addWidget(self.bar)
        layout.addWidget(self.label)
        self.hide()

    def show_busy(self, text: str):
        self.label.setText(text)
        self.show()

    def hide_busy(self):
        self.hide()


def make_row(widgets) -> QFrame:
    frame = QFrame()
    frame.setProperty("role", "card")
    return frame
