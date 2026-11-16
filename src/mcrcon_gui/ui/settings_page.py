"""Settings: appearance, console behaviour, updates and where data is stored."""

from __future__ import annotations

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QScrollArea, QVBoxLayout, QWidget

from .. import __version__
from ..core import storage
from ..core.models import AppSettings
from .theme import display_font, mono_font
from .updates import UpdateManager
from .widgets import BrutalButton, Card, PageHeader, Segmented, Toggle


def setting_row(title: str, description: str, control: QWidget) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(18)
    text = QVBoxLayout()
    text.setSpacing(2)
    name = QLabel(title)
    name.setFont(display_font(13))
    desc = QLabel(description)
    desc.setObjectName("hint")
    desc.setWordWrap(True)
    text.addWidget(name)
    text.addWidget(desc)
    row.addLayout(text, 1)
    row.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
    return row


class SettingsPage(QWidget):
    theme_changed = Signal(str)
    timestamps_changed = Signal(bool)
    changed = Signal()
    install_requested = Signal()

    def __init__(self, settings: AppSettings, updates: UpdateManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.updates = updates
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 22, 28, 18)
        outer.setSpacing(16)
        outer.addWidget(PageHeader("Settings", "Saved automatically", "cyan"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; }")
        content = QWidget()
        col = QVBoxLayout(content)
        col.setContentsMargins(0, 0, 12, 12)
        col.setSpacing(20)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        # -- appearance ----------------------------------------------------------------
        look = Card("Appearance", "yellow", icon="sun")
        self.theme = Segmented([("light", "Light", "sun"), ("dark", "Dark", "moon"), ("system", "System", "monitor")], settings.theme)
        self.theme.setFixedWidth(390)
        self.theme.changed.connect(self.theme_changed)
        look.body_layout.addLayout(setting_row("Theme", "System follows your Windows light/dark setting. Ctrl+Shift+T cycles.", self.theme))
        col.addWidget(look)

        # -- console -------------------------------------------------------------------
        console = Card("Console", "purple", icon="terminal")
        self.timestamps = Toggle(settings.show_timestamps)
        self.timestamps.toggled.connect(self.timestamps_changed)
        self.confirm = Toggle(settings.confirm_dangerous)
        self.confirm.toggled.connect(self._set_confirm)
        console.body_layout.addLayout(setting_row("Timestamps", "Show the time next to every line of output.", self.timestamps))
        console.body_layout.addLayout(
            setting_row("Ask before risky commands", "Confirm /stop, /kick, /ban, /ban-ip and /kill before sending them.", self.confirm)
        )
        col.addWidget(console)

        # -- updates -------------------------------------------------------------------
        upd = Card("Updates", "green", icon="update")
        self.auto = Toggle(settings.auto_update)
        self.auto.toggled.connect(self._set_auto)
        upd.body_layout.addLayout(
            setting_row(
                "Automatic updates",
                "Check when the app starts and every 24 hours, download new versions in the background, "
                "and install them when you close the app.",
                self.auto,
            )
        )
        status_row = QHBoxLayout()
        status_row.setSpacing(10)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setFont(mono_font(12))
        self.check_button = BrutalButton("Check now", "yellow", compact=True, icon="refresh")
        self.check_button.clicked.connect(lambda: self.updates.check(manual=True))
        self.install_button = BrutalButton("Install & restart", "green", compact=True, icon="update")
        self.install_button.clicked.connect(self.install_requested)
        self.download_button = BrutalButton("Download page", "cyan", compact=True, icon="globe")
        self.download_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://mcrcon.app/download/")))
        status_row.addWidget(self.status, 1)
        status_row.addWidget(self.check_button)
        status_row.addWidget(self.install_button)
        status_row.addWidget(self.download_button)
        upd.body_layout.addLayout(status_row)
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(12)
        upd.body_layout.addWidget(self.bar)
        col.addWidget(upd)

        # -- data ----------------------------------------------------------------------
        data = Card("Your data", "orange", icon="folder")
        self.path_label = path = QLabel(str(storage.config_path()))
        path.setFont(mono_font(12))
        path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        path.setWordWrap(True)
        open_folder = BrutalButton("Open folder", "surface", compact=True, icon="folder")
        open_folder.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(storage.config_dir()))))
        data.body_layout.addLayout(
            setting_row(
                "Settings file",
                "Servers, history and preferences. Passwords are encrypted with your Windows account. "
                "Quick action buttons can be edited here (quick_commands).",
                open_folder,
            )
        )
        data.body_layout.addWidget(path)
        col.addWidget(data)
        col.addStretch(1)

        updates.state_changed.connect(self._on_update_state)
        updates.progress.connect(self._on_progress)
        self._on_update_state(updates.state, updates.message)

    def _set_confirm(self, on: bool) -> None:
        self.settings.confirm_dangerous = on
        self.changed.emit()

    def _set_auto(self, on: bool) -> None:
        self.settings.auto_update = on
        self.changed.emit()
        self._on_update_state(self.updates.state, self.updates.message)

    def _on_update_state(self, state: str, message: str) -> None:
        default = f"Version {__version__}. " + (
            "Updates are checked when the app starts and every 24 hours." if self.settings.auto_update else "Automatic updates are off."
        )
        self.status.setText(message or default)
        self.check_button.setEnabled(state not in ("checking", "downloading"))
        self.install_button.setVisible(state == "ready")
        self.download_button.setVisible(state == "available")
        self.bar.setVisible(state == "downloading")

    def _on_progress(self, done: int, total: int) -> None:
        self.bar.setRange(0, total or 0)
        self.bar.setValue(done)
