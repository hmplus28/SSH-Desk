"""Qt application bootstrap with global exception handling."""

import logging
import sys

log = logging.getLogger("ssh_desk.gui")


def run_gui(ctx) -> int:
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setApplicationName("SSH Desk")
    app.setOrganizationName("ssh-desk")
    app.setDesktopFileName("ssh-desk")

    def excepthook(exc_type, exc, tb):
        log.error("unhandled GUI exception", exc_info=(exc_type, exc, tb))
        try:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.critical(
                None, "SSH Desk", f"{exc_type.__name__}: {exc}\n\nSee log: ~/.local/share/ssh-desk/logs/"
            )
        except Exception:
            pass

    sys.excepthook = excepthook

    from ssh_desk.gui.main_window import MainWindow

    window = MainWindow(ctx)
    window.show()
    code = app.exec()
    return code
