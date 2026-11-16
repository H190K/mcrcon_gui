"""The main page: server tabs, the selected server's console, and players / quick actions / broadcast."""

from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget

from ..core.models import AppSettings
from .players_panel import PlayersPanel
from .server_tabs import ServerTabs
from .session import SessionManager
from .widgets import BrutalButton, Card, PageHeader

QUICK_ICONS = {
    "time set day": "sun",
    "time set night": "moon",
    "weather clear": "sun",
    "weather rain": "refresh",
    "weather thunder": "bolt",
    "list": "users",
    "save-all": "download",
    "whitelist list": "check",
    "seed": "globe",
}


class ConsolePage(QWidget):
    def __init__(self, manager: SessionManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        settings: AppSettings = manager.settings
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 18)
        root.setSpacing(16)

        self.header = PageHeader("Console", "Run commands on your Minecraft servers")
        self.update_button = BrutalButton("Install update", "green", compact=True, icon="update")
        self.update_button.hide()
        self.header.actions.addWidget(self.update_button)
        root.addWidget(self.header)

        self.tabs = ServerTabs(manager)
        root.addWidget(self.tabs)

        body = QHBoxLayout()
        body.setSpacing(22)
        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)

        right = QVBoxLayout()
        right.setSpacing(18)
        self.players = PlayersPanel()
        right.addWidget(self.players, 1)

        quick = Card("Quick actions", "cyan", icon="bolt")
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(12)
        self.quick_buttons: list[BrutalButton] = []
        for i, q in enumerate(settings.quick_commands):
            button = BrutalButton(q.label, "surface", compact=True, icon=QUICK_ICONS.get(q.command))
            button.setToolTip(f"/{q.command}")
            button.setProperty("command", q.command)
            grid.addWidget(button, i // 2, i % 2)
            self.quick_buttons.append(button)
        quick.body_layout.addLayout(grid)
        self.stop_button = BrutalButton("Stop server", "red", compact=True, icon="stop")
        self.stop_button.setToolTip("/stop (asks for confirmation first)")
        quick.body_layout.addWidget(self.stop_button)
        right.addWidget(quick)

        self.broadcast_input = self.players.broadcast_input
        self.broadcast_button = self.players.broadcast_button

        right_box = QWidget()
        right_box.setLayout(right)
        right_box.setFixedWidth(318)
        body.addWidget(right_box)
        root.addLayout(body, 1)
