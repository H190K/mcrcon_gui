"""Render the app icon and installer artwork with Qt, so they always match the theme.

    python tools/make_art.py

Writes src/mcrcon_gui/assets/icon.png + icon.ico, and build/installer/wizard*.bmp for Inno Setup.
The icon is an original voxel "grass block" (pixel-textured, thick outlines, hard shadow)
with a terminal badge — a nod to Minecraft without using any of its assets.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PIL import Image  # noqa: E402
from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QColor,
    QFont,
    QGuiApplication,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QTransform,
)

from mcrcon_gui.ui import theme  # noqa: E402
from mcrcon_gui.ui.theme import LIGHT  # noqa: E402

INK = QColor(LIGHT.ink)
GRASS = ["#5DBB3F", "#4FA834", "#6CCB4A", "#57B23A"]
GRASS_SIDE = ["#4FA834", "#5DBB3F", "#46992E"]
DIRT = ["#9A6B43", "#8A5D38", "#A87A50", "#7D5331"]
TEXELS = 8


def _texture(kind: str, seed: int) -> list[list[str]]:
    """An 8x8 grid of colours. Deterministic so the icon never changes between builds."""
    rng = random.Random(seed)
    if kind == "top":
        return [[rng.choice(GRASS) for _ in range(TEXELS)] for _ in range(TEXELS)]
    drips = [rng.choice([2, 2, 3, 3, 4]) for _ in range(TEXELS)]
    return [[rng.choice(GRASS_SIDE) if row < drips[col] else rng.choice(DIRT) for col in range(TEXELS)] for row in range(TEXELS)]


def _face(p: QPainter, origin: QPointF, u: QPointF, v: QPointF, texture: list[list[str]], shade: float) -> QPolygonF:
    """Paint a pixel texture onto the parallelogram origin + s*u + t*v, return its outline."""
    p.save()
    p.setTransform(QTransform(u.x(), u.y(), v.x(), v.y(), origin.x(), origin.y()), True)
    step = 1 / TEXELS
    for row in range(TEXELS):
        for col in range(TEXELS):
            color = QColor(texture[row][col])
            if shade != 1:
                color = color.darker(int(100 / shade))
            # Slight overlap hides hairline seams between texels.
            p.fillRect(QRectF(col * step, row * step, step * 1.02, step * 1.02), color)
    p.restore()
    return QPolygonF([origin, origin + u, origin + u + v, origin + v])


def paint_icon(p: QPainter, size: float) -> None:
    u = size / 64  # design on a 64-unit grid
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    small = size <= 32
    outline = (3.2 if small else 2.6) * u

    # Isometric cube.
    top = QPointF(29 * u, 3 * u)
    half_w, rise, height = 25 * u, 12.5 * u, 27 * u
    left = QPointF(top.x() - half_w, top.y() + rise)
    right = QPointF(top.x() + half_w, top.y() + rise)
    center = QPointF(top.x(), top.y() + 2 * rise)

    silhouette = QPolygonF([top, right, right + QPointF(0, height), center + QPointF(0, height), left + QPointF(0, height), left])
    shadow = 3.5 * u
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(INK)
    p.drawPolygon(silhouette.translated(shadow, shadow))

    faces = [
        _face(p, left, top - left, center - left, _texture("top", 1), 1.0),
        _face(p, left, center - left, QPointF(0, height), _texture("side", 2), 0.92),
        _face(p, center, right - center, QPointF(0, height), _texture("side", 3), 0.78),
    ]
    pen = QPen(INK, outline)
    # Bevel: the cube's acute corners would otherwise grow long miter spikes.
    pen.setJoinStyle(Qt.PenJoinStyle.BevelJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    for face in faces:
        p.drawPolygon(face)

    # Terminal badge in the bottom-right corner.
    badge = QRectF(35 * u, 37 * u, 25 * u, 21 * u)
    bshadow = 3 * u
    p.setPen(Qt.PenStyle.NoPen)
    p.fillRect(badge.translated(bshadow, bshadow), INK)
    p.fillRect(badge, QColor(LIGHT.yellow))
    bpen = QPen(INK, outline)
    bpen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
    p.setPen(bpen)
    p.drawRect(badge.adjusted(outline / 2, outline / 2, -outline / 2, -outline / 2))

    # ">_" drawn as strokes (not text) so it stays crisp at 16 px.
    stroke = QPen(INK, (3.4 if small else 3) * u)
    stroke.setCapStyle(Qt.PenCapStyle.SquareCap)
    stroke.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
    p.setPen(stroke)
    chevron = QPainterPath(QPointF(40.5 * u, 42.5 * u))
    chevron.lineTo(46.5 * u, 47.5 * u)
    chevron.lineTo(40.5 * u, 52.5 * u)
    p.drawPath(chevron)
    p.drawLine(QPointF(49.5 * u, 52.5 * u), QPointF(55 * u, 52.5 * u))


def render_icon(size: int) -> QImage:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    paint_icon(p, size)
    p.end()
    return image


def _qimage_to_pil(image: QImage) -> Image.Image:
    image = image.convertToFormat(QImage.Format.Format_RGBA8888)
    return Image.frombuffer("RGBA", (image.width(), image.height()), bytes(image.constBits()), "raw", "RGBA", 0, 1)


def render_wizard(width: int, height: int) -> QImage:
    """Tall side banner for the installer's welcome and finish pages."""
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(QColor(LIGHT.yellow))
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = width / 164
    p.fillRect(QRectF(width - 4 * s, 0, 4 * s, height), INK)

    icon = 120 * s
    p.save()
    p.translate((width - icon) / 2 - 4 * s, 34 * s)
    paint_icon(p, icon)
    p.restore()

    def tag(text: str, y: float, bg: str, fg: str, px: int) -> None:
        font = QFont(theme.DISPLAY_FONT)
        font.setPixelSize(int(px * s))
        p.setFont(font)
        w = p.fontMetrics().horizontalAdvance(text) + 18 * s
        h = px * s + 14 * s
        box = QRectF((width - w) / 2 - 4 * s, y, w, h)
        p.fillRect(box.translated(4 * s, 4 * s), INK)
        p.fillRect(box, QColor(bg))
        pen = QPen(INK, 3 * s)
        pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        p.setPen(pen)
        p.drawRect(box.adjusted(1.5 * s, 1.5 * s, -1.5 * s, -1.5 * s))
        p.setPen(QColor(fg))
        p.drawText(box, Qt.AlignmentFlag.AlignCenter, text)

    tag("MCRCON", 178 * s, LIGHT.ink, LIGHT.yellow, 22)
    tag("GUI", 222 * s, LIGHT.pink, LIGHT.ink, 16)
    font = QFont(theme.MONO_FONT)
    font.setPixelSize(int(11 * s))
    p.setFont(font)
    p.setPen(INK)
    p.drawText(QRectF(0, height - 34 * s, width - 4 * s, 20 * s), Qt.AlignmentFlag.AlignCenter, "by H190K")
    p.end()
    return image


def render_wizard_small(size: int) -> QImage:
    image = QImage(size, size, QImage.Format.Format_RGB32)
    image.fill(QColor("#FFFFFF"))
    p = QPainter(image)
    paint_icon(p, size)
    p.end()
    return image


def main() -> None:
    QGuiApplication(sys.argv)
    theme.load_fonts()
    assets = theme.ASSETS
    render_icon(512).save(str(assets / "icon.png"))

    # Each .ico size is rendered separately (not downscaled) so small sizes stay sharp.
    sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    frames = [_qimage_to_pil(render_icon(s)) for s in sizes]
    frames[-1].save(assets / "icon.ico", format="ICO", sizes=[(s, s) for s in sizes], append_images=frames[:-1])

    out = ROOT / "build" / "installer"
    out.mkdir(parents=True, exist_ok=True)
    for scale in (1, 2):
        suffix = "" if scale == 1 else f"@{scale}x"
        render_wizard(164 * scale, 314 * scale).save(str(out / f"wizard{suffix}.bmp"))
        render_wizard_small(55 * scale).save(str(out / f"wizard-small{suffix}.bmp"))
    print(f"Wrote icon.png, icon.ico and installer artwork to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
