"""Servers: every saved server as a card, with connect / edit / remove."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from .session import Session, SessionManager
from .theme import mono_font
from .widgets import Badge, BrutalButton, Card, PageHeader

STATE_TEXT = {
    "online": ("● Online", "green"),
    "connecting": ("Connecting…", "orange"),
    "reconnecting": ("Reconnecting…", "orange"),
    "offline": ("○ Offline", "surface"),
}


class ServerCard(Card):
    def __init__(self, page: "ServersPage", session: Session) -> None:
        super().__init__(session.profile.name, session.profile.color, icon="server")
        self.session = session
        self.state = Badge()
        self.header_layout.addWidget(self.state)
        p = session.profile
        address = QLabel(p.display())
        address.setFont(mono_font(14))
        flags = []
        flags.append("auto-connect" if p.auto_connect else "manual connect")
        flags.append("auto-reconnect" if p.auto_reconnect else "no auto-reconnect")
        flags.append("password saved" if p.password and p.remember_password else "password asked")
        detail = QLabel(" · ".join(flags))
        detail.setObjectName("hint")
        self.players = QLabel()
        self.players.setObjectName("hint")
        self.body_layout.addWidget(address)
        self.body_layout.addWidget(detail)
        self.body_layout.addWidget(self.players)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.connect_button = BrutalButton("Connect", "green", compact=True, icon="plug")
        self.connect_button.clicked.connect(lambda: page.toggle_requested.emit(p.id))
        open_console = BrutalButton("Console", "yellow", compact=True, icon="terminal")
        open_console.clicked.connect(lambda: page.open_requested.emit(p.id))
        edit = BrutalButton("", "surface", compact=True, icon="edit")
        edit.setFixedWidth(44)
        edit.setToolTip("Edit")
        edit.clicked.connect(lambda: page.edit_requested.emit(p.id))
        remove = BrutalButton("", "surface", compact=True, icon="trash")
        remove.setFixedWidth(44)
        remove.setToolTip("Remove")
        remove.clicked.connect(lambda: page.remove_requested.emit(p.id))
        row.addWidget(self.connect_button)
        row.addWidget(open_console)
        row.addStretch(1)
        row.addWidget(edit)
        row.addWidget(remove)
        self.body_layout.addSpacing(4)
        self.body_layout.addLayout(row)
        session.state_changed.connect(lambda _s: self.refresh())
        session.players_changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        s = self.session
        text, color = STATE_TEXT.get(s.state, STATE_TEXT["offline"])
        self.state.set(text, color)
        online = s.state in ("online", "reconnecting")
        self.connect_button.setText("Disconnect" if online else "Connect")
        self.connect_button.set_color("red" if online else "green")
        self.connect_button.set_icon_name("power" if online else "plug")
        if s.online and s.players is not None:
            names = ", ".join(s.players.names[:6]) + ("…" if len(s.players.names) > 6 else "")
            self.players.setText(f"{s.players.online}/{s.players.maximum} online{': ' + names if names else ''}")
        else:
            self.players.setText(s.last_error and f"Last error: {s.last_error}" or "Not connected")


class ServersPage(QWidget):
    toggle_requested = Signal(str)
    open_requested = Signal(str)
    edit_requested = Signal(str)
    remove_requested = Signal(str)
    add_requested = Signal()

    def __init__(self, manager: SessionManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.manager = manager
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 22, 28, 18)
        outer.setSpacing(16)
        self.header = PageHeader("Servers", "", "pink")
        add = BrutalButton("Add server", "yellow", icon="plus")
        add.clicked.connect(self.add_requested)
        self.header.actions.addWidget(add)
        outer.addWidget(self.header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; }")
        self.content = QWidget()
        self.grid = QGridLayout(self.content)
        self.grid.setContentsMargins(0, 0, 12, 12)
        self.grid.setSpacing(20)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.content)
        outer.addWidget(scroll, 1)
        self.rebuild()

    def rebuild(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        sessions = self.manager.ordered()
        for i, session in enumerate(sessions):
            self.grid.addWidget(ServerCard(self, session), i // 2, i % 2)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)
        for row in range(self.grid.rowCount()):
            self.grid.setRowStretch(row, 0)
        self.grid.setRowStretch((len(sessions) + 1) // 2, 1)  # cards keep their height; spare space goes below
        count = len(sessions)
        self.header.subtitle.setText(f"{count} saved server{'s' if count != 1 else ''}. Several can be connected at once.")
