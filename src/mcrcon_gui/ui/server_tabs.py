"""Server tabs across the top of the console page, each showing its live connection state."""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton, QHBoxLayout, QWidget

from . import theme
from .icons import draw_icon
from .session import Session, SessionManager
from .theme import display_font, mono_font
from .widgets import draw_block, resolve

STATE_COLORS = {"online": "green", "connecting": "orange", "reconnecting": "orange", "offline": "muted"}


class ServerTab(QAbstractButton):
    def __init__(self, session: Session, manager: SessionManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.session = session
        self.manager = manager
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(50)
        self.setToolTip(f"{session.profile.name}: {session.profile.display()}\nDouble-click to connect or disconnect")

    def _right_text(self) -> str:
        s = self.session
        if s.online and s.players is not None:
            return f"{s.players.online}/{s.players.maximum}"
        if s.state in ("connecting", "reconnecting"):
            return "…"
        return ""

    def sizeHint(self) -> QSize:  # noqa: N802
        name = QFontMetrics(display_font(12)).horizontalAdvance(self.session.profile.name.upper())
        address = QFontMetrics(mono_font(10)).horizontalAdvance(self.session.profile.display())
        right = QFontMetrics(display_font(11)).horizontalAdvance(self._right_text() or "0/00")
        unread = 32 if self.session.unread else 0
        return QSize(max(160, 38 + max(name, address) + 18 + right + unread + 16), 50)

    def enterEvent(self, event) -> None:  # noqa: N802
        self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        t = theme.current()
        s = self.session
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        active = s.profile.id == self.manager.settings.active_profile_id
        body = QRectF(0, 0, self.width() - 4, self.height() - 4)
        if active:
            draw_block(p, body, resolve(s.profile.color, t), t, shadow=4)
        else:
            draw_block(p, body, t.input_focus_bg if self.underMouse() else t.surface, t, border=2)
        fg = QColor(t.on_accent if active else t.text)
        sub = QColor(t.on_accent if active else t.muted_text)

        dot = QRectF(body.left() + 14, body.center().y() - 6, 12, 12)
        p.fillRect(dot, QColor(resolve(STATE_COLORS.get(s.state, "muted"), t)))
        p.setPen(QPen(QColor(t.ink if not active else "#111111"), 2))
        p.drawRect(dot)

        p.setFont(display_font(12))
        p.setPen(fg)
        p.drawText(QRectF(dot.right() + 12, body.top() + 6, body.width(), 20), Qt.AlignmentFlag.AlignLeft, s.profile.name.upper())
        p.setFont(mono_font(10))
        p.setPen(sub)
        p.drawText(QRectF(dot.right() + 12, body.top() + 25, body.width() - 60, 16), Qt.AlignmentFlag.AlignLeft, s.profile.display())

        right = QRectF(body.left(), body.top(), body.width() - 12, body.height())
        p.setFont(display_font(11))
        p.setPen(fg)
        p.drawText(right, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self._right_text())
        if s.unread and not active:
            used = p.fontMetrics().horizontalAdvance(self._right_text())
            chip = QRectF(right.right() - used - 32, body.center().y() - 9, 24, 18)
            draw_block(p, chip, t.pink, t, border=2)
            p.setFont(display_font(9))
            p.setPen(QColor(t.on_accent))
            p.drawText(chip, Qt.AlignmentFlag.AlignCenter, str(min(s.unread, 99)))


class AddTab(QAbstractButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(54, 50)
        self.setToolTip("Add a server (Ctrl+N)")

    def enterEvent(self, event) -> None:  # noqa: N802
        self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        t = theme.current()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        body = QRectF(0, 0, self.width() - 4, self.height() - 4)
        pen = QPen(QColor(t.ink), 2, Qt.PenStyle.DashLine)
        if self.underMouse():
            p.fillRect(body, QColor(t.input_focus_bg))
        p.setPen(pen)
        p.drawRect(body.adjusted(1, 1, -1, -1))
        draw_icon(p, "plus", QRectF(body.center().x() - 10, body.center().y() - 10, 20, 20), QColor(t.text), stroke=3)


class ServerTabs(QWidget):
    selected = Signal(str)
    toggle_requested = Signal(str)
    add_requested = Signal()

    def __init__(self, manager: SessionManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.manager = manager
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(10)
        self.tabs: list[ServerTab] = []
        self.rebuild()

    def rebuild(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.tabs = []
        for session in self.manager.ordered():
            tab = ServerTab(session, self.manager)
            tab.clicked.connect(lambda _=False, pid=session.profile.id: self.selected.emit(pid))
            tab.mouseDoubleClickEvent = lambda _e, pid=session.profile.id: self.toggle_requested.emit(pid)  # type: ignore[method-assign]
            self._layout.addWidget(tab)
            self.tabs.append(tab)
        add = AddTab()
        add.clicked.connect(self.add_requested)
        self._layout.addWidget(add)
        self._layout.addStretch(1)

    def refresh(self) -> None:
        for tab in self.tabs:
            tab.updateGeometry()
            tab.update()
