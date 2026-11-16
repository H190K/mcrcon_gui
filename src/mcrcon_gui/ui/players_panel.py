"""Online players of the active server, with a right-click menu of common actions."""

from __future__ import annotations

import zlib

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QStyle,
    QStyledItemDelegate,
    QWidget,
)

from ..core.commands.data import GAMEMODES
from ..core.models import PlayerList
from . import theme
from .theme import display_font, mono_font
from .widgets import BrutalButton, Card

_AVATAR_COLORS = ["#FFD23F", "#FF6B9D", "#4CC9F0", "#3DDC97", "#FF9F1C", "#B388FF", "#FF5A5F"]


def _name_bits(name: str) -> int:
    """A stable per-name number (zlib, not hashlib, so the build needs no OpenSSL)."""
    return zlib.crc32(name.lower().encode())


def _avatar_color(name: str) -> str:
    return _AVATAR_COLORS[_name_bits(name) % len(_AVATAR_COLORS)]


class _PlayerDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index) -> None:
        t = theme.current()
        name = index.data(Qt.ItemDataRole.DisplayRole)
        rect = option.rect
        painter.save()
        if option.state & (QStyle.StateFlag.State_Selected | QStyle.StateFlag.State_MouseOver):
            painter.fillRect(rect, QColor(t.input_focus_bg))
        # A pixel avatar: a 4x4 pattern derived from the name, inside an outlined square.
        size = 24
        box = QRect(rect.left() + 4, rect.center().y() - size // 2, size, size)
        painter.fillRect(box, QColor(_avatar_color(name)))
        bits = _name_bits(name) >> 3
        cell = size // 4
        for i in range(8):  # mirror left half to right for a face-like symmetric pattern
            if (bits >> (i * 3)) % 3 == 0:
                x, y = i % 2, i // 2
                for cx in (x, 3 - x):
                    painter.fillRect(box.left() + cx * cell, box.top() + y * cell, cell, cell, QColor(0, 0, 0, 70))
        pen = QPen(QColor(t.ink), 2)
        painter.setPen(pen)
        painter.drawRect(box.adjusted(1, 1, -1, -1))
        painter.setFont(mono_font(13, bold=True))
        painter.setPen(QColor(t.text))
        painter.drawText(rect.adjusted(size + 14, 0, -6, 0), Qt.AlignmentFlag.AlignVCenter, name)
        painter.setPen(QPen(QColor(t.muted), 2))
        painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())
        painter.restore()

    def sizeHint(self, option, index) -> QSize:  # noqa: N802
        return QSize(200, 36)


class PlayersPanel(Card):
    run_command = Signal(str)
    insert_text = Signal(str)
    confirm = Signal(str, str, object)  # title, question, callback — the window asks

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Players", "green", parent, icon="users")
        self.list = QListWidget()
        self.list.setObjectName("players")
        self.list.setItemDelegate(_PlayerDelegate(self.list))
        self.list.setMouseTracking(True)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._menu)
        self.list.itemDoubleClicked.connect(lambda item: self.insert_text.emit(item.text()))
        self.list.setMinimumHeight(110)
        self.empty = QLabel("Not connected")
        self.empty.setObjectName("hint")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setFont(display_font(11))
        self.empty.setMinimumHeight(60)
        self.list.setToolTip("Right-click a player for actions. Double-click to insert the name.")
        self.body_layout.addWidget(self.list, 1)
        self.body_layout.addWidget(self.empty)

        # Broadcast to everyone on the server (/say).
        row = QHBoxLayout()
        row.setSpacing(8)
        self.broadcast_input = QLineEdit()
        self.broadcast_input.setPlaceholderText("Say to everyone…")
        self.broadcast_button = BrutalButton("", "yellow", compact=True, icon="megaphone")
        self.broadcast_button.setFixedWidth(46)
        self.broadcast_button.setToolTip("Broadcast with /say")
        row.addWidget(self.broadcast_input, 1)
        row.addWidget(self.broadcast_button)
        self.body_layout.addLayout(row)
        self.names: list[str] = []
        self.set_players(None, online=False)

    def set_players(self, players: PlayerList | None, online: bool) -> None:
        self.names = players.names if players else []
        self.list.clear()
        for name in self.names:
            self.list.addItem(QListWidgetItem(name))
        if players is None:
            self.set_title("Players")
            self.empty.setText("Waiting for player list…" if online else "Not connected")
        else:
            self.set_title(f"Players · {players.online}/{players.maximum}")
            self.empty.setText("Nobody online" if not self.names else "")
        self.list.setVisible(bool(self.names))
        self.empty.setVisible(not self.names)

    def _menu(self, pos: QPoint) -> None:
        item = self.list.itemAt(pos)
        if item is None:
            return
        name = item.text()
        menu = QMenu(self)
        menu.addAction("Message…", lambda: self._ask(f"Message {name}", "Message:", lambda text: f"msg {name} {text}"))
        tp = menu.addMenu("Teleport to")
        for other in self.names:
            if other != name:
                tp.addAction(other, lambda o=other: self.run_command.emit(f"tp {name} {o}"))
        tp.setEnabled(len(self.names) > 1)
        gm = menu.addMenu("Game mode")
        for mode in GAMEMODES:
            gm.addAction(mode.title(), lambda m=mode: self.run_command.emit(f"gamemode {m} {name}"))
        menu.addSeparator()
        menu.addAction("Make operator", lambda: self.run_command.emit(f"op {name}"))
        menu.addAction("Remove operator", lambda: self.run_command.emit(f"deop {name}"))
        menu.addSeparator()
        menu.addAction("Kick…", lambda: self._ask(f"Kick {name}", "Reason (optional):", lambda r: f"kick {name} {r}".strip(), confirm=True))
        menu.addAction("Ban…", lambda: self._ask(f"Ban {name}", "Reason (optional):", lambda r: f"ban {name} {r}".strip(), confirm=True))
        menu.addSeparator()
        menu.addAction("Insert name into command", lambda: self.insert_text.emit(name))
        menu.addAction("Copy name", lambda: QGuiApplication.clipboard().setText(name))
        menu.exec(self.list.viewport().mapToGlobal(pos))

    def _ask(self, title: str, label: str, build, confirm: bool = False) -> None:
        text, ok = QInputDialog.getText(self, title, label)
        if not ok:
            return
        command = build(text.strip())
        if confirm:
            self.confirm.emit(title, f"Run /{command} ?", lambda: self.run_command.emit(command))
        elif text.strip():
            self.run_command.emit(command)
