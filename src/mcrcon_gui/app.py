"""Application entry point."""

from __future__ import annotations

import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from . import __version__
from .core import storage
from .ui import theme
from .ui.main_window import MainWindow
from .ui.session import SessionManager
from .ui.theme import ThemeManager
from .ui.updates import UpdateManager


def create_app(argv: list[str] | None = None) -> QApplication:
    app = QApplication.instance() or QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("MCRCON GUI")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("H190K")
    app.setStyle("Fusion")
    app.setFont(theme.load_fonts())
    app.setWindowIcon(QIcon(str(theme.ASSETS / "icon.png")))
    return app


def build_window(settings=None, mode: str | None = None) -> MainWindow:
    """Create the session manager, theme and main window (used by main(), tests and screenshots)."""
    settings = settings or storage.load()
    themes = ThemeManager(mode or settings.theme)
    themes.apply()
    manager = SessionManager(settings)
    updates = UpdateManager(settings, manager.request_save)
    window = MainWindow(manager, themes, updates)
    manager.start()
    if not os.environ.get("MCRCON_GUI_NO_UPDATE_CHECK"):
        updates.start()
    return window


def main() -> int:
    if sys.platform == "win32":
        # Give the app its own taskbar icon instead of python.exe's.
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("h190k.mcrcon-gui")
        except (AttributeError, OSError):
            pass
    app = create_app()
    window = build_window()
    window.show()
    return app.exec()
