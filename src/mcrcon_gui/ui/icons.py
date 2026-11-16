"""A small set of square-capped line icons (24x24), drawn for this app and rendered with QtSvg."""

from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# Path data only; stroke, caps and colour are added in icon_svg().
ICONS: dict[str, str] = {
    "terminal": '<rect x="2.5" y="4" width="19" height="16"/><path d="M6.5 9l3.5 3-3.5 3M12 15.5h5.5"/>',
    "server": '<rect x="3" y="3.5" width="18" height="7"/><rect x="3" y="13.5" width="18" height="7"/>'
    '<path d="M7 7h.01M7 17h.01M11 7h6M11 17h6"/>',
    "settings": '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/>'
    '<rect x="14" y="4" width="4" height="4"/><rect x="8" y="10" width="4" height="4"/><rect x="16" y="16" width="4" height="4"/>',
    "info": '<rect x="3" y="3" width="18" height="18"/><path d="M12 11v6M12 7.5v.01"/>',
    "users": '<rect x="5" y="4" width="8" height="8"/><path d="M2.5 20.5v-2.5a3.5 3.5 0 0 1 3.5-3.5h6a3.5 3.5 0 0 1 3.5 3.5v2.5"/>'
    '<path d="M16 4.5h3.5v7H16M18 14.5h.5a3 3 0 0 1 3 3v3"/>',
    "plug": '<path d="M9 3v5M15 3v5M6 8h12v4a6 6 0 0 1-12 0zM12 18v3"/>',
    "power": '<path d="M12 3v8M7 6a7.5 7.5 0 1 0 10 0"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "edit": '<path d="M4 20h4l11-11-4-4L4 16zM13 7l4 4"/>',
    "trash": '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v5M14 11v5"/>',
    "copy": '<rect x="8" y="8" width="13" height="13"/><path d="M16 8V3H3v13h5"/>',
    "download": '<path d="M12 3v12M7 10l5 5 5-5M4 20h16"/>',
    "eraser": '<path d="M3 20h18M7 17l-4-4 9-9 8 8-5 5zM8 8l8 8"/>',
    "search": '<rect x="4" y="4" width="11" height="11"/><path d="M15 15l5.5 5.5"/>',
    "send": '<path d="M3 11l18-8-8 18-2-8z M11 13l10-10"/>',
    "sun": '<rect x="8" y="8" width="8" height="8"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2"/>',
    "moon": '<path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z"/>',
    "monitor": '<rect x="3" y="4" width="18" height="12"/><path d="M8 20h8M12 16v4"/>',
    "refresh": '<path d="M20 11a8 8 0 0 0-14.5-4.5L4 8M4 4v4h4M4 13a8 8 0 0 0 14.5 4.5L20 16M20 20v-4h-4"/>',
    "update": '<path d="M12 21V9M7 14l5-5 5 5M4 4h16"/>',
    "globe": '<rect x="3" y="3" width="18" height="18"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/>',
    "code": '<path d="M8 7l-5 5 5 5M16 7l5 5-5 5M14 4l-4 16"/>',
    "bug": '<rect x="7" y="7" width="10" height="13"/><path d="M9 7V4h6v3M3 11h4M17 11h4M3 17h4M17 17h4M12 11v9"/>',
    "heart": '<path d="M12 20s-8-5-8-11a4 4 0 0 1 8-1 4 4 0 0 1 8 1c0 6-8 11-8 11z"/>',
    "folder": '<path d="M3 6h7l2 2h9v11H3z"/>',
    "megaphone": '<path d="M3 10v4h3l9 5V5L6 10zM18 9a4 4 0 0 1 0 6M7 14l1.5 6h3L10 15"/>',
    "bolt": '<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>',
    "stop": '<rect x="5" y="5" width="14" height="14"/>',
    "check": '<path d="M4 12l5 5L20 6"/>',
    "x": '<path d="M5 5l14 14M19 5L5 19"/>',
    "chevron": '<path d="M9 5l7 7-7 7"/>',
    "github": '<path d="M9 19c-4 1.5-4-2-6-2.5M15 21v-3.5c0-1 .1-1.4-.5-2 2.8-.3 5.5-1.4 5.5-6a4.6 4.6 0 0 0-1.3-3.2 4.2 4.2 0 0 0-.1-3.2s-1.1-.3-3.5 1.3a12 12 0 0 0-6.2 0C6.5 2.8 5.4 3.1 5.4 3.1a4.2 4.2 0 0 0-.1 3.2A4.6 4.6 0 0 0 4 9.5c0 4.6 2.7 5.7 5.5 6-.6.6-.6 1.2-.5 2V21"/>',
}


def icon_svg(name: str, color: str, stroke: float = 2.4) -> bytes:
    body = ICONS.get(name, ICONS["info"])
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{stroke}" stroke-linecap="square" stroke-linejoin="miter">'
        f"{body}</svg>"
    ).encode()


@lru_cache(maxsize=512)
def icon_pixmap(name: str, color: str, size: int, dpr: float = 1.0, stroke: float = 2.4) -> QPixmap:
    px = max(1, round(size * dpr))
    pixmap = QPixmap(px, px)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    QSvgRenderer(QByteArray(icon_svg(name, color, stroke))).render(painter, QRectF(0, 0, px, px))
    painter.end()
    pixmap.setDevicePixelRatio(dpr)
    return pixmap


def draw_icon(p: QPainter, name: str, rect: QRectF, color: QColor | str, stroke: float = 2.4) -> None:
    color = QColor(color).name()
    dpr = round(p.device().devicePixelRatioF() * 4) / 4 if p.device() else 1.0
    pixmap = icon_pixmap(name, color, int(rect.width()), dpr, stroke)
    p.drawPixmap(rect.topLeft(), pixmap)


def make_icon(name: str, color: str, size: int = 20) -> QIcon:
    icon = QIcon()
    for dpr in (1.0, 2.0):
        icon.addPixmap(icon_pixmap(name, color, size, dpr))
    return icon
