"""Real terminal widget: OpenSSH over a kernel PTY rendered through a VT100 emulator (pyte).

- Interactive shell, colors, arrow keys, Ctrl+C/D, vim/nano (alternate screen), resize (SIGWINCH)
- Mouse selection + clipboard copy/paste
- One TerminalWidget per tab.
"""

import fcntl
import os
import pty
import re
import shlex
import signal
import struct
import subprocess
import termios
from typing import Optional

import pyte
from PySide6.QtCore import Qt, QTimer, QSocketNotifier, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QClipboard
from PySide6.QtWidgets import QApplication, QWidget

from ssh_desk.gui.i18n import tr

ANSI_16 = {
    "black": "#2e333d", "red": "#e5484d", "green": "#46c078", "brown": "#e8a33d",
    "yellow": "#e8a33d", "blue": "#4f8cff", "magenta": "#c059e0", "cyan": "#29b3c0",
    "white": "#c8ccd4", "default": None,
}
_TITLE_RE = re.compile(rb"\x1b\](0|2);[^\x07\x1b]*(\x07|\x1b\\)")


def _xterm256(index: int) -> str:
    if index < 16:
        base = [
            "#2e333d", "#e5484d", "#46c078", "#e8a33d", "#4f8cff", "#c059e0", "#29b3c0", "#c8ccd4",
            "#5b6270", "#ff6b6b", "#5fd68f", "#ffbe5c", "#6ba1ff", "#d477f0", "#4fd0dd", "#eef1f6",
        ]
        return base[index]
    if index < 232:
        index -= 16
        levels = (0, 95, 135, 175, 215, 255)
        r = levels[index // 36]
        g = levels[(index % 36) // 6]
        b = levels[index % 6]
        return f"#{r:02x}{g:02x}{b:02x}"
    gray = 8 + (index - 232) * 10
    return f"#{gray:02x}{gray:02x}{gray:02x}"


class TerminalWidget(QWidget):
    title_changed = Signal(str)
    session_closed = Signal(int)  # exit code
    session_error = Signal(str)

    def __init__(self, argv: list, env: dict, label: str, font_point_size: int = 11, parent=None):
        super().__init__(parent)
        self.argv = argv
        self.env = env
        self.label = label
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.IBeamCursor)
        self._font = QFont("DejaVu Sans Mono")
        self._font.setStyleHint(QFont.StyleHint.Monospace)
        self._font.setPointSize(font_point_size)
        self._metrics = QFontMetricsF(self._font)
        self._cell_w = self._metrics.horizontalAdvance("M")
        self._cell_h = self._metrics.height() + 2

        self.columns, self.lines = 80, 24
        self.screen = pyte.Screen(self.columns, self.lines)
        self.stream = pyte.ByteStream(self.screen)
        self.screen.set_mode(pyte.modes.LNM)

        self.master: Optional[int] = None
        self.process: Optional[subprocess.Popen] = None
        self.notifier: Optional[QSocketNotifier] = None
        self._selection: Optional[tuple[int, int, int, int]] = None  # r1,c1,r2,c2
        self._selecting = False
        self._anchor = None
        self._exit_code: Optional[int] = None
        self._closed = False
        self._palette_bg = QColor("#14161b")
        self._palette_fg = QColor("#e7eaf0")

        self._spawn()
        self.resizeEvent(None)

    # ------------------------------------------------------------- spawn
    def _spawn(self):
        master, slave = pty.openpty()
        size = struct.pack("HHHH", self.lines, self.columns, 0, 0)
        fcntl.ioctl(slave, termios.TIOCSWINSZ, size)

        def preexec():
            os.setsid()
            fcntl.ioctl(slave, termios.TIOCSCTTY, 0)
            signal.signal(signal.SIGPIPE, signal.SIG_DFL)

        env = {**os.environ, **self.env, "TERM": "xterm-256color", "COLORTERM": "truecolor"}
        self.process = subprocess.Popen(
            self.argv, stdin=slave, stdout=slave, stderr=slave,
            preexec_fn=preexec, env=env, close_fds=True,
        )
        os.close(slave)
        self.master = master
        fcntl.fcntl(master, fcntl.F_SETFL, fcntl.fcntl(master, fcntl.F_GETFL) | os.O_NONBLOCK)
        self.notifier = QSocketNotifier(master, QSocketNotifier.Type.Read, self)
        self.notifier.activated.connect(self._read_pty)

    # ------------------------------------------------------------- pty read
    def _read_pty(self):
        try:
            while True:
                data = os.read(self.master, 65536)
                if not data:
                    break
                title_match = _TITLE_RE.search(data)
                if title_match:
                    raw = title_match.group(0)
                    inner = re.sub(rb"^\x1b\](0|2);", b"", raw)
                    inner = inner.rstrip(b"\x07").rstrip(b"\x1b\\")
                    self.title_changed.emit(inner.decode(errors="replace"))
                    data = _TITLE_RE.sub(b"", data)
                self.stream.feed(data)
                self.update()
        except BlockingIOError:
            return
        except OSError:
            self._finish()
        self._check_exit()

    def _check_exit(self):
        if self.process and self.process.poll() is not None:
            self._finish()

    def _finish(self):
        if self._closed:
            return
        self._closed = True
        if self.notifier:
            self.notifier.setEnabled(False)
        code = self.process.poll() if self.process else 0
        if code is None:
            code = 0
        self._exit_code = code
        self.session_closed.emit(code)
        self.update()

    # ------------------------------------------------------------- sizing
    def resizeEvent(self, event):
        if self.width() < 40 or self.height() < 40:
            if event is not None:
                super().resizeEvent(event)
            return
        cols = max(20, min(500, int(self.width() / self._cell_w) - 1))
        rows = max(5, min(300, int(self.height() / self._cell_h) - 1))
        if (cols, rows) != (self.columns, self.lines):
            self.columns, self.lines = cols, rows
            try:
                self.screen.resize(rows, cols)
            except Exception:
                pass
            if self.master is not None:
                try:
                    size = struct.pack("HHHH", rows, cols, 0, 0)
                    fcntl.ioctl(self.master, termios.TIOCSWINSZ, size)
                except OSError:
                    pass
        if event is not None:
            super().resizeEvent(event)

    # ------------------------------------------------------------- painting
    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setFont(self._font)
        painter.fillRect(self.rect(), self._palette_bg)

        if self._closed and self._exit_code is not None:
            painter.setPen(QColor("#9aa3b2"))
            painter.drawText(12, self._cell_h + 8, tr("session_ended", code=self._exit_code))
            painter.end()
            return

        screen = self.screen
        cursor_visible = 25 in getattr(screen, "mode", {25})
        for row in range(self.lines):
            y = (row + 1) * self._cell_h
            for col in range(self.columns):
                char = screen.buffer.get((col, row))
                if char is None:
                    continue
                data = char.data
                if not data or data == " ":
                    continue
                fg, bg = self._colors_for(char)
                if self._in_selection(row, col):
                    fg, bg = bg, fg
                if bg is not None:
                    painter.fillRect(int(col * self._cell_w), int(y - self._cell_h + (self._cell_h - self._metrics.height())),
                                     int(self._cell_w) + 1, int(self._metrics.height()) + 2, bg)
                if char.bold:
                    font = painter.font()
                    font.setBold(True)
                    painter.setFont(font)
                if fg is not None:
                    painter.setPen(QColor(fg))
                else:
                    painter.setPen(self._palette_fg)
                painter.drawText(int(col * self._cell_w), int(y - (self._cell_h - self._metrics.ascent()) - 2), data)
                if char.bold:
                    font = painter.font()
                    font.setBold(False)
                    painter.setFont(font)

        if cursor_visible and not self._closed:
            cx = screen.cursor.x
            cy = screen.cursor.y
            if cy < self.lines and cx < self.columns:
                pen = QColor("#4f8cff")
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(int(cx * self._cell_w), int((cy) * self._cell_h), int(self._cell_w), int(self._cell_h))
        painter.end()

    def _colors_for(self, char):
        fg = self._resolve_color(char.fg, self._palette_fg.name())
        bg = self._resolve_color(char.bg, None)
        if char.reverse:
            fg, bg = bg, fg
        return fg, bg

    @staticmethod
    def _resolve_color(value, fallback):
        if not value or value in ("default",):
            return fallback
        if value in ANSI_16:
            return ANSI_16[value]
        if value.isdigit():
            return _xterm256(int(value))
        if value.startswith("fg-") or value.startswith("bg-"):
            inner = value[3:]
            if inner.isdigit():
                return _xterm256(int(inner))
            return ANSI_16.get(inner, fallback)
        return ANSI_16.get(value, fallback)

    def _in_selection(self, row: int, col: int) -> bool:
        if not self._selection:
            return False
        r1, c1, r2, c2 = self._selection
        if (row, col) < (r1, c1) or (row, col) > (r2, c2):
            return False
        if row == r1 and row == r2:
            return c1 <= col <= c2
        if row == r1:
            return col >= c1
        if row == r2:
            return col <= c2
        return True

    # ------------------------------------------------------------- input
    def keyPressEvent(self, event):
        if self._closed:
            return
        key = event.key()
        mods = event.modifiers()
        text = event.text()

        # selection escape
        if key in (Qt.Key.Key_Escape,) and self._selection:
            self._selection = None
            self.update()
            self._write(b"\x1b")
            return

        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
        alt = bool(mods & Qt.KeyboardModifier.AltModifier)
        shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)

        if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self._write(b"\r")
        elif key == Qt.Key.Key_Backspace:
            self._write(b"\x7f")
        elif key == Qt.Key.Key_Tab:
            self._write(b"\t")
        elif key == Qt.Key.Key_Backtab:
            self._write(b"\x1b[Z")
        elif key == Qt.Key.Key_Up and not shift:
            self._write(b"\x1b[A")
        elif key == Qt.Key.Key_Down and not shift:
            self._write(b"\x1b[B")
        elif key == Qt.Key.Key_Right and not shift:
            self._write(b"\x1b[C")
        elif key == Qt.Key.Key_Left and not shift:
            self._write(b"\x1b[D")
        elif key == Qt.Key.Key_Home:
            self._write(b"\x1b[H")
        elif key == Qt.Key.Key_End:
            self._write(b"\x1b[F")
        elif key == Qt.Key.Key_PageUp:
            self._write(b"\x1b[5~")
        elif key == Qt.Key.Key_PageDown:
            self._write(b"\x1b[6~")
        elif key == Qt.Key.Key_Delete:
            self._write(b"\x1b[3~")
        elif key == Qt.Key.Key_Insert:
            self._write(b"\x1b[2~")
        elif ctrl and not alt:
            code = text.upper()
            if key == Qt.Key.Key_C and self._selection:
                self._copy_selection()
                return
            if key == Qt.Key.Key_V and not shift:
                self.paste_clipboard()
                return
            mapping = {
                "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7, "H": 8, "I": 9,
                "J": 10, "K": 11, "L": 12, "M": 13, "N": 14, "O": 15, "P": 16, "Q": 17,
                "R": 18, "S": 19, "T": 20, "U": 21, "V": 22, "W": 23, "X": 24, "Y": 25, "Z": 26,
                " ": 0, "@": 0, "[": 27, "\\": 28, "]": 29, "^": 30, "_": 31, "?": 127,
            }
            if code in mapping:
                self._write(bytes([mapping[code]]))
        elif key == Qt.Key.Key_F1:
            self._write(b"\x1bOP")
        elif key == Qt.Key.Key_F2:
            self._write(b"\x1bOQ")
        elif key == Qt.Key.Key_F3:
            self._write(b"\x1bOR")
        elif key == Qt.Key.Key_F4:
            self._write(b"\x1bOS")
        elif key == Qt.Key.Key_F5:
            self._write(b"\x1b[15~")
        elif key == Qt.Key.Key_F6:
            self._write(b"\x1b[17~")
        elif key == Qt.Key.Key_F7:
            self._write(b"\x1b[18~")
        elif key == Qt.Key.Key_F8:
            self._write(b"\x1b[19~")
        elif key == Qt.Key.Key_F9:
            self._write(b"\x1b[20~")
        elif key == Qt.Key.Key_F10:
            self._write(b"\x1b[21~")
        elif key == Qt.Key.Key_F11:
            self._write(b"\x1b[23~")
        elif key == Qt.Key.Key_F12:
            self._write(b"\x1b[24~")
        elif alt and text:
            self._write(b"\x1b" + text.encode("utf-8"))
        elif text:
            self._selection = None
            self._write(text.encode("utf-8"))

    def _write(self, data: bytes):
        if self.master is None or self._closed:
            return
        try:
            os.write(self.master, data)
        except OSError:
            self._finish()

    # ------------------------------------------------------------- mouse
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = self._cell_pos(event)
            self._anchor = pos
            self._selecting = True
            self._selection = (pos[0], pos[1], pos[0], pos[1])
            self.update()
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.paste_clipboard()

    def mouseMoveEvent(self, event):
        if self._selecting and self._anchor:
            pos = self._cell_pos(event)
            r1, c1 = self._anchor
            r2, c2 = pos
            if (r2, c2) < (r1, c1):
                r1, c1, r2, c2 = r2, c2, r1, c1
            self._selection = (r1, c1, r2, c2)
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._selecting:
            self._selecting = False
            self._copy_selection()

    def _cell_pos(self, event):
        col = max(0, min(self.columns - 1, int(event.position().x() / self._cell_w)))
        row = max(0, min(self.lines - 1, int(event.position().y() / self._cell_h)))
        return row, col

    def _copy_selection(self):
        if not self._selection:
            return
        r1, c1, r2, c2 = self._selection
        lines = []
        for row in range(r1, r2 + 1):
            chars = []
            for col in range(c1, (c2 + 1) if row == r2 else self.columns):
                char = self.screen.buffer.get((col, row))
                chars.append(char.data if char else " ")
            lines.append("".join(chars).rstrip())
        text = "\n".join(lines)
        if text.strip():
            QApplication.clipboard().setText(text, QClipboard.Mode.Selection)
            QApplication.clipboard().setText(text)

    def paste_clipboard(self):
        text = QApplication.clipboard().text()
        if text:
            self._write(text.replace("\r\n", "\r").replace("\n", "\r").encode("utf-8"))

    # ------------------------------------------------------------- lifecycle
    def set_font_size(self, point_size: int):
        point_size = max(6, min(28, point_size))
        self._font.setPointSize(point_size)
        self._metrics = QFontMetricsF(self._font)
        self._cell_w = self._metrics.horizontalAdvance("M")
        self._cell_h = self._metrics.height() + 2
        self.resizeEvent(None)
        self.update()

    def font_size(self) -> int:
        return self._font.pointSize()

    def shutdown(self):
        """Terminate the child and free all resources."""
        self._closed = True
        if self.notifier:
            self.notifier.setEnabled(False)
            self.notifier.deleteLater()
            self.notifier = None
        if self.process and self.process.poll() is None:
            try:
                os.killpg(self.process.pid, signal.SIGTERM)
            except (OSError, ProcessLookupError):
                try:
                    self.process.terminate()
                except OSError:
                    pass
            QTimer.singleShot(1500, self._kill_hard)
        if self.master is not None:
            try:
                os.close(self.master)
            except OSError:
                pass
            self.master = None

    def _kill_hard(self):
        try:
            if self.process and self.process.poll() is None:
                os.killpg(self.process.pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass

    @property
    def title(self) -> str:
        return self._title if hasattr(self, "_title") else self.label

    @title.setter
    def title(self, value: str):
        self._title = value or self.label
