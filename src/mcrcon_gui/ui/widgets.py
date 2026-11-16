"""Custom-painted widgets. Qt style sheets cannot draw hard offset shadows, so these paint themselves.

Colours are given as accent *keys* ("yellow", "surface", ...) and resolved against the
current theme at paint time, so every widget follows a theme switch with a repaint.
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFontMetrics, QKeyEvent, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QAbstractButton, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from . import theme
from .icons import draw_icon
from .theme import Theme, display_font, mono_font

LIGHT_FILLS = ("surface", "paper", "input_bg")


def resolve(key: str, t: Theme | None = None) -> str:
    """Accent key or theme token name -> colour. Raw "#rrggbb" values pass through."""
    t = t or theme.current()
    if key.startswith("#"):
        return key
    return getattr(t, key, t.yellow)


def _pen(color: str, width: float) -> QPen:
    pen = QPen(QColor(color), width)
    pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
    return pen


def draw_block(p: QPainter, rect: QRectF, fill: str, t: Theme, *, shadow: float = 0, border: float | None = None) -> None:
    """An outlined, flat block with an optional hard shadow."""
    border = t.border if border is None else border
    if shadow:
        p.fillRect(rect.translated(shadow, shadow), QColor(t.ink))
    p.fillRect(rect, QColor(fill))
    p.setPen(_pen(t.ink, border))
    p.setBrush(Qt.BrushStyle.NoBrush)
    half = border / 2
    p.drawRect(rect.adjusted(half, half, -half, -half))


# -- buttons ---------------------------------------------------------------------------


class BrutalButton(QPushButton):
    """A flat button with an outline and a hard shadow that "sinks" when pressed."""

    def __init__(
        self,
        text: str,
        color: str = "yellow",
        parent: QWidget | None = None,
        *,
        compact: bool = False,
        icon: str | None = None,
    ):
        super().__init__(text.upper(), parent)
        self._color = color
        self._compact = compact
        self._icon = icon
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(display_font(11 if compact else 13))
        self.setMinimumHeight(34 if compact else 44)

    def set_color(self, color: str) -> None:
        self._color = color
        self.update()

    def set_icon_name(self, icon: str | None) -> None:
        self._icon = icon
        self.update()

    def setText(self, text: str) -> None:  # noqa: N802 - Qt naming
        super().setText(text.upper())

    def sizeHint(self) -> QSize:  # noqa: N802
        pad = 26 if self._compact else 36
        icon = (16 if self._compact else 18) + 8 if self._icon else 0
        text = self.fontMetrics().horizontalAdvance(self.text()) if self.text() else -8
        return QSize(text + pad + icon + theme.current().shadow, self.minimumHeight())

    def paintEvent(self, event) -> None:  # noqa: N802
        t = theme.current()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = 4 if self._compact else t.shadow
        face = QRectF(0, 0, self.width() - s, self.height() - s)
        enabled = self.isEnabled()
        pressed = (self.isDown() or self.isChecked()) and enabled
        hovered = self.underMouse() and enabled and not pressed
        if pressed:
            face.translate(s, s)
        elif hovered:
            face.translate(-1, -1)

        fill = QColor(resolve(self._color, t)) if enabled else QColor(t.muted)
        if hovered:
            fill = fill.lighter(108) if t.dark or self._color not in LIGHT_FILLS else QColor(t.input_focus_bg)
        draw_block(p, face, fill.name(), t, shadow=0 if pressed or not enabled else s)

        fg = QColor(t.text if self._color in LIGHT_FILLS else t.on_accent)
        if not enabled:
            fg = QColor(t.muted_text)
        if self.hasFocus() and enabled:
            p.setPen(QPen(fg, 1, Qt.PenStyle.DashLine))
            p.drawRect(face.adjusted(5, 5, -6, -6))

        p.setFont(self.font())
        text_w = self.fontMetrics().horizontalAdvance(self.text()) if self.text() else 0
        icon_size = 16 if self._compact else 18
        gap = 8 if self._icon and text_w else 0
        total = text_w + (icon_size + gap if self._icon else 0)
        x = face.left() + (face.width() - total) / 2
        if self._icon:
            draw_icon(p, self._icon, QRectF(x, face.center().y() - icon_size / 2, icon_size, icon_size), fg, stroke=2.8)
            x += icon_size + gap
        p.setPen(fg)
        p.drawText(QRectF(x, face.top(), text_w + 2, face.height()), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())

    def enterEvent(self, event) -> None:  # noqa: N802
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self.update()
        super().leaveEvent(event)


class Toggle(QAbstractButton):
    """A neo-brutalist on/off switch."""

    def __init__(self, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(52, 28)
        self.toggled.connect(lambda _on: self.update())

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(52, 28)

    def paintEvent(self, event) -> None:  # noqa: N802
        t = theme.current()
        p = QPainter(self)
        on = self.isChecked()
        track = QRectF(0, 0, self.width() - 3, self.height() - 3)
        draw_block(p, track, t.green if on else t.input_bg, t, shadow=3, border=2.5)
        knob_w = track.height() - 8
        x = track.right() - knob_w - 4 if on else track.left() + 4
        knob = QRectF(x, track.top() + 4, knob_w, knob_w)
        p.fillRect(knob, QColor("#111111" if on else t.muted_text))
        if self.hasFocus():
            p.setPen(QPen(QColor(t.ink), 1, Qt.PenStyle.DashLine))
            p.drawRect(track.adjusted(-3, -3, 3, 3))


class Segmented(QWidget):
    """A row of mutually exclusive options, e.g. Light / Dark / System."""

    changed = Signal(str)

    def __init__(self, options: Sequence[tuple[str, str, str | None]], value: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._options = list(options)  # (value, label, icon)
        self._value = value
        self._hover = -1
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFont(display_font(11))
        self.setFixedHeight(40)

    def value(self) -> str:
        return self._value

    def set_value(self, value: str, emit: bool = False) -> None:
        if value != self._value:
            self._value = value
            self.update()
            if emit:
                self.changed.emit(value)

    def _segment_width(self) -> float:
        fm = QFontMetrics(self.font())
        widest = max(fm.horizontalAdvance(label.upper()) + (24 if icon else 0) for _v, label, icon in self._options)
        return widest + 30

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(int(self._segment_width() * len(self._options)) + 6, 40)

    def _index_at(self, x: float) -> int:
        w = (self.width() - 3) / len(self._options)
        return max(0, min(len(self._options) - 1, int(x // w)))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._hover = self._index_at(event.position().x())
        self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = -1
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self.set_value(self._options[self._index_at(event.position().x())][0], emit=True)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        values = [o[0] for o in self._options]
        i = values.index(self._value) if self._value in values else 0
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            step = -1 if event.key() == Qt.Key.Key_Left else 1
            self.set_value(values[(i + step) % len(values)], emit=True)
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        t = theme.current()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        body = QRectF(0, 0, self.width() - 3, self.height() - 3)
        draw_block(p, body, t.input_bg, t, shadow=3)
        w = body.width() / len(self._options)
        p.setFont(self.font())
        for i, (value, label, icon) in enumerate(self._options):
            seg = QRectF(body.left() + i * w, body.top(), w, body.height()).adjusted(3, 3, -3, -3)
            selected = value == self._value
            if selected:
                p.fillRect(seg, QColor(t.yellow))
            elif i == self._hover:
                p.fillRect(seg, QColor(t.input_focus_bg))
            fg = QColor(t.on_accent if selected else t.text)
            text = label.upper()
            text_w = p.fontMetrics().horizontalAdvance(text)
            total = text_w + (22 if icon else 0)
            x = seg.left() + (seg.width() - total) / 2
            if icon:
                draw_icon(p, icon, QRectF(x, seg.center().y() - 8, 16, 16), fg, stroke=2.8)
                x += 22
            p.setPen(fg)
            p.drawText(QRectF(x, seg.top(), text_w + 2, seg.height()), Qt.AlignmentFlag.AlignVCenter, text)
            if i:
                p.setPen(_pen(t.ink, 2))
                p.drawLine(QPointF(body.left() + i * w, body.top() + 3), QPointF(body.left() + i * w, body.bottom() - 3))
        if self.hasFocus():
            p.setPen(QPen(QColor(t.ink), 1, Qt.PenStyle.DashLine))
            p.drawRect(body.adjusted(-3, -3, 3, 3))


# -- containers ------------------------------------------------------------------------


class Card(QFrame):
    """An outlined panel with a hard shadow and a small titled header."""

    def __init__(self, title: str, accent: str = "yellow", parent: QWidget | None = None, *, icon: str | None = None):
        super().__init__(parent)
        self._accent = accent
        self._icon = icon
        t = theme.current()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(t.border, t.border, t.shadow + t.border, t.shadow + t.border)
        outer.setSpacing(0)

        self.header = QWidget()
        self.header_layout = QHBoxLayout(self.header)
        self.header_layout.setContentsMargins(16, 12, 14, 0)
        self.header_layout.setSpacing(10)
        self.tag = QLabel(title.upper())
        self.tag.setFont(display_font(12))
        self.header_layout.addSpacing(26 if icon else 18)
        self.header_layout.addWidget(self.tag)
        self.header_layout.addStretch(1)
        outer.addWidget(self.header)

        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(16, 12, 16, 16)
        self.body_layout.setSpacing(10)
        outer.addWidget(self.body, 1)
        self.apply_theme(t)

    def set_title(self, title: str) -> None:
        self.tag.setText(title.upper())

    def set_accent(self, accent: str) -> None:
        self._accent = accent
        self.update()

    def apply_theme(self, t: Theme) -> None:
        self.tag.setStyleSheet(f"QLabel {{ color:{t.text}; letter-spacing:1px; }}")

    def paintEvent(self, event) -> None:  # noqa: N802
        t = theme.current()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_block(p, QRectF(0, 0, self.width() - t.shadow, self.height() - t.shadow), t.surface, t, shadow=t.shadow)
        # The header marker: a small accent square (or icon tile) before the title.
        y = t.border + 12 + (self.tag.height() - 16) / 2
        x = t.border + 16
        if self._icon:
            tile = QRectF(x - 2, y - 3, 22, 22)
            draw_block(p, tile, resolve(self._accent, t), t, border=2)
            draw_icon(p, self._icon, tile.adjusted(4, 4, -4, -4), QColor(t.on_accent), stroke=3)
        else:
            draw_block(p, QRectF(x, y + 2, 12, 12), resolve(self._accent, t), t, border=2)


class DotBackground(QWidget):
    """Paper background with a faint dot grid, like graph paper."""

    SPACING = 22

    _tiles: dict[str, QPixmap] = {}

    @classmethod
    def _tile(cls, t: Theme) -> QPixmap:
        """One grid cell with its dot; painted as a brush so a repaint is a single fill call."""
        if t.name not in cls._tiles:
            tile = QPixmap(cls.SPACING, cls.SPACING)
            tile.fill(QColor(t.paper))
            painter = QPainter(tile)
            half = cls.SPACING // 2
            painter.fillRect(half, half, 2, 2, QColor(t.muted if not t.dark else "#2C2C36"))
            painter.end()
            cls._tiles[t.name] = tile
        return cls._tiles[t.name]

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.fillRect(event.rect(), QBrush(self._tile(theme.current())))


class PageHeader(QWidget):
    """A big page title with a highlighter stroke behind it, plus a subtitle."""

    def __init__(self, title: str, subtitle: str = "", accent: str = "yellow", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = title.upper()
        self._accent = accent
        self.title_font = display_font(32)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        self._title_space = QWidget()
        self._title_space.setFixedSize(QFontMetrics(self.title_font).horizontalAdvance(self._title) + 14, 48)
        layout.addWidget(self._title_space, 0, Qt.AlignmentFlag.AlignBottom)
        self.subtitle = QLabel(subtitle)
        self.subtitle.setObjectName("hint")
        self.subtitle.setFont(mono_font(12))
        layout.addWidget(self.subtitle, 0, Qt.AlignmentFlag.AlignBottom)
        layout.addStretch(1)
        self.actions = QHBoxLayout()
        self.actions.setSpacing(12)
        layout.addLayout(self.actions)

    def set_title(self, title: str) -> None:
        self._title = title.upper()
        self._title_space.setFixedWidth(QFontMetrics(self.title_font).horizontalAdvance(self._title) + 14)
        self.update()

    def set_accent(self, accent: str) -> None:
        self._accent = accent
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        t = theme.current()
        p = QPainter(self)
        geo = self._title_space.geometry()
        fm = QFontMetrics(self.title_font)
        width = fm.horizontalAdvance(self._title)
        base = geo.bottom() - 8
        # A highlighter stroke under the lower third of the letters.
        mark = QRectF(geo.left() + 4, base - fm.ascent() * 0.28, width + 10, fm.ascent() * 0.38)
        p.fillRect(mark, QColor(resolve(self._accent, t)))
        p.setFont(self.title_font)
        p.setPen(QColor(t.text))
        p.drawText(QPointF(geo.left(), base), self._title)


class Badge(QLabel):
    """A small outlined label used for connection state and counts."""

    def __init__(self, text: str = "", color: str = "surface", parent: QWidget | None = None):
        super().__init__(parent)
        self.setFont(display_font(11))
        self._color = color
        self.set(text, color)

    def set(self, text: str, color: str) -> None:
        self._color = color
        self.setText(text.upper())
        self.apply_theme(theme.current())

    def apply_theme(self, t: Theme) -> None:
        fg = t.text if self._color in LIGHT_FILLS else t.on_accent
        self.setStyleSheet(
            f"QLabel {{ background:{resolve(self._color, t)}; color:{fg}; border:{t.border}px solid {t.ink};"
            f" padding:6px 12px; letter-spacing:1px; }}"
        )


class Toast(QLabel):
    """A short-lived message in the bottom-right corner of its parent."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setFont(display_font(11))
        self.hide()
        self._timer = QTimer(self, singleShot=True, timeout=self.hide)
        self._color = "yellow"

    def show_message(self, text: str, color: str = "yellow", ms: int = 2600) -> None:
        self._color = color
        self.setText(text.upper())
        self.apply_theme(theme.current())
        self.adjustSize()
        parent = self.parentWidget()
        self.move(parent.width() - self.width() - 28, parent.height() - self.height() - 28)
        self.show()
        self.raise_()
        self._timer.start(ms)

    def apply_theme(self, t: Theme) -> None:
        self.setStyleSheet(
            f"QLabel {{ background:{resolve(self._color, t)}; color:{t.on_accent}; border:{t.border}px solid {t.ink};"
            f" padding:10px 16px; }}"
        )


# -- navigation ------------------------------------------------------------------------


class NavButton(QAbstractButton):
    def __init__(self, text: str, icon: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setText(text.upper())
        self._icon = icon
        self._badge = ""
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(80, 70)
        self.setFont(display_font(10))

    def set_badge(self, text: str) -> None:
        self._badge = text
        self.update()

    def enterEvent(self, event) -> None:  # noqa: N802
        self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        t = theme.current()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        body = QRectF(2, 2, self.width() - 8, self.height() - 8)
        if self.isChecked():
            draw_block(p, body, t.yellow, t, shadow=4)
            fg = QColor(t.on_accent)
        else:
            if self.underMouse():
                p.fillRect(body, QColor(t.input_focus_bg))
            fg = QColor(t.text if self.underMouse() else t.muted_text)
        draw_icon(p, self._icon, QRectF(body.center().x() - 11, body.top() + 11, 22, 22), fg, stroke=2.6)
        p.setFont(self.font())
        p.setPen(fg)
        p.drawText(QRectF(body.left(), body.top() + 38, body.width(), 18), Qt.AlignmentFlag.AlignHCenter, self.text())
        if self._badge:
            chip = QRectF(body.right() - 22, body.top() - 2, 24, 18)
            draw_block(p, chip, t.pink, t, border=2)
            p.setFont(display_font(9))
            p.setPen(QColor(t.on_accent))
            p.drawText(chip, Qt.AlignmentFlag.AlignCenter, self._badge)
        if self.hasFocus():
            p.setPen(QPen(fg, 1, Qt.PenStyle.DashLine))
            p.drawRect(body.adjusted(4, 4, -4, -4))


class NavRail(QWidget):
    """The left navigation column: logo, page buttons, and pinned buttons at the bottom."""

    selected = Signal(int)

    def __init__(self, logo: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(104)
        self.buttons: list[NavButton] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12 + theme.current().border, 14)
        layout.setSpacing(8)
        layout.addWidget(logo, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(14)
        self._top = QVBoxLayout()
        self._top.setSpacing(8)
        layout.addLayout(self._top)
        layout.addStretch(1)
        self._bottom = QVBoxLayout()
        self._bottom.setSpacing(8)
        layout.addLayout(self._bottom)
        self.footer = QLabel()
        self.footer.setFont(display_font(10))
        self.footer.setObjectName("hint")
        self.footer.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(6)
        layout.addWidget(self.footer)

    def add_page(self, text: str, icon: str, *, bottom: bool = False, tooltip: str = "") -> NavButton:
        button = NavButton(text, icon, self)
        button.setToolTip(tooltip or text.title())
        index = len(self.buttons)
        button.clicked.connect(lambda _=False, i=index: self.select(i))
        (self._bottom if bottom else self._top).addWidget(button, 0, Qt.AlignmentFlag.AlignHCenter)
        self.buttons.append(button)
        return button

    def select(self, index: int) -> None:
        for i, button in enumerate(self.buttons):
            button.setChecked(i == index)
        self.selected.emit(index)

    def paintEvent(self, event) -> None:  # noqa: N802
        t = theme.current()
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(t.surface))
        p.fillRect(QRect(self.width() - t.border, 0, t.border, self.height()), QColor(t.ink))
