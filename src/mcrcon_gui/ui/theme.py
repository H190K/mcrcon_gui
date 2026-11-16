"""Neo-brutalist themes: flat saturated colour, thick outlines, hard offset shadows.

Colours live in :class:`Theme` token sets. Custom-painted widgets read :func:`current`
at paint time, so switching theme only needs a repaint plus a new style sheet.
Fonts are set with QFont in code, never in the style sheet: a font rule in QSS would
override every ``setFont()`` call.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication, QWidget

ASSETS = Path(__file__).resolve().parent.parent / "assets"
DISPLAY_FONT = "Archivo Black"
MONO_FONT = "Space Mono"


@dataclass(frozen=True)
class Theme:
    name: str
    ink: str  # outlines and hard shadows
    paper: str  # window background
    surface: str  # cards
    text: str
    muted_text: str
    muted: str  # disabled fills
    input_bg: str
    input_focus_bg: str
    console_bg: str
    console_text: str
    header_bg: str
    header_text: str
    on_accent: str = "#111111"
    yellow: str = "#FFD23F"
    pink: str = "#FF6B9D"
    cyan: str = "#4CC9F0"
    green: str = "#3DDC97"
    red: str = "#FF5A5F"
    orange: str = "#FF9F1C"
    purple: str = "#B388FF"
    border: int = 3
    shadow: int = 5

    def accent(self, key: str) -> str:
        return getattr(self, key, self.yellow) if key in ("yellow", "pink", "cyan", "green", "red", "orange", "purple") else self.yellow

    @property
    def dark(self) -> bool:
        return self.name == "dark"


LIGHT = Theme(
    name="light",
    ink="#111111",
    paper="#FFF4E0",
    surface="#FFFFFF",
    text="#111111",
    muted_text="#5C5446",
    muted="#D9CFBF",
    input_bg="#FFFFFF",
    input_focus_bg="#FFF9D6",
    console_bg="#151515",
    console_text="#F2F2F2",
    header_bg="#FFD23F",
    header_text="#111111",
)

DARK = Theme(
    name="dark",
    ink="#F4F0E6",
    paper="#15151A",
    surface="#1F1F27",
    text="#F4F0E6",
    muted_text="#A39C8F",
    muted="#3A3A45",
    input_bg="#262630",
    input_focus_bg="#302C1E",
    console_bg="#0B0B0E",
    console_text="#F2F2F2",
    header_bg="#1F1F27",
    header_text="#FFD23F",
)

_current: Theme = LIGHT


def current() -> Theme:
    return _current


def _font(family: str, size: int) -> QFont:
    font = QFont(family)
    font.setPixelSize(size)
    return font


def load_fonts() -> QFont:
    """Register the bundled fonts and return the default UI font."""
    for font in sorted((ASSETS / "fonts").glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(font))
    return _font(MONO_FONT, 13)


def display_font(size: int) -> QFont:
    return _font(DISPLAY_FONT, size)


def mono_font(size: int = 13, bold: bool = False) -> QFont:
    font = _font(MONO_FONT, size)
    font.setBold(bold)
    return font


def palette_for(t: Theme) -> QPalette:
    p = QPalette()
    for role, color in (
        (QPalette.ColorRole.Window, t.paper),
        (QPalette.ColorRole.WindowText, t.text),
        (QPalette.ColorRole.Base, t.input_bg),
        (QPalette.ColorRole.AlternateBase, t.surface),
        (QPalette.ColorRole.Text, t.text),
        (QPalette.ColorRole.Button, t.surface),
        (QPalette.ColorRole.ButtonText, t.text),
        (QPalette.ColorRole.Highlight, t.yellow),
        (QPalette.ColorRole.HighlightedText, t.on_accent),
        (QPalette.ColorRole.ToolTipBase, t.ink),
        (QPalette.ColorRole.ToolTipText, t.paper),
        (QPalette.ColorRole.PlaceholderText, t.muted_text),
        (QPalette.ColorRole.Link, t.text),
    ):
        p.setColor(role, QColor(color))
    return p


def build_stylesheet(t: Theme) -> str:
    b = t.border
    return f"""
QWidget {{ color: {t.text}; }}
QMainWindow, QDialog, #root {{ background: {t.paper}; }}
QLabel#fieldLabel {{ font-family: "{DISPLAY_FONT}"; font-size: 11px; letter-spacing: 1px; }}
QLabel#hint {{ color: {t.muted_text}; font-size: 11px; }}
QLineEdit, QSpinBox, QComboBox {{
    background: {t.input_bg};
    border: {b}px solid {t.ink};
    padding: 6px 9px;
    min-height: 22px;
    selection-background-color: {t.yellow};
    selection-color: {t.on_accent};
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ background: {t.input_focus_bg}; }}
QLineEdit:disabled, QSpinBox:disabled {{ background: {t.muted}; color: {t.muted_text}; }}
QSpinBox::up-button, QSpinBox::down-button {{ width: 0px; border: none; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {t.surface}; border: {b}px solid {t.ink};
    selection-background-color: {t.yellow}; selection-color: {t.on_accent};
}}
QCheckBox {{ spacing: 9px; }}
QCheckBox::indicator {{ width: 14px; height: 14px; border: {b}px solid {t.ink}; background: {t.input_bg}; }}
QCheckBox::indicator:checked {{ background: {t.ink}; image: none; }}
QTextBrowser#console {{
    background: {t.console_bg};
    color: {t.console_text};
    border: {b}px solid {t.ink};
    padding: 10px;
    selection-background-color: {t.yellow};
    selection-color: #111111;
}}
QProgressBar {{ background: {t.input_bg}; border: 2px solid {t.ink}; }}
QProgressBar::chunk {{ background: {t.green}; }}
QListWidget {{ background: transparent; border: none; outline: none; }}
QListWidget#suggestions {{ background: {t.surface}; }}
QListWidget#suggestions::item {{ padding: 3px 8px; border: none; }}
QListWidget#suggestions::item:selected {{ background: {t.yellow}; color: {t.on_accent}; }}
QListWidget#players::item {{ padding: 6px 4px; border-bottom: 2px solid {t.muted}; }}
QListWidget#players::item:selected, QListWidget#players::item:hover {{ background: {t.input_focus_bg}; color: {t.text}; }}
QScrollBar:vertical {{ background: transparent; width: 14px; border-left: {b}px solid {t.ink}; }}
QScrollBar::handle:vertical {{ background: {t.yellow}; border: 2px solid #111111; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0px; width: 0px; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
QToolTip {{ background: {t.ink}; color: {t.paper}; border: 2px solid {t.yellow}; padding: 4px 6px; }}
QMenu {{ background: {t.surface}; border: {b}px solid {t.ink}; padding: 4px; }}
QMenu::item {{ padding: 6px 22px 6px 12px; }}
QMenu::item:selected {{ background: {t.yellow}; color: {t.on_accent}; }}
QMenu::separator {{ height: 2px; background: {t.ink}; margin: 4px 6px; }}
QDialog QPushButton, QMessageBox QPushButton, QInputDialog QPushButton, QDialogButtonBox QPushButton {{
    background: {t.yellow}; color: {t.on_accent}; border: {b}px solid {t.ink}; padding: 8px 20px; min-width: 64px; font-weight: 700;
}}
QDialog QPushButton:hover, QMessageBox QPushButton:hover {{ background: {QColor(t.yellow).lighter(112).name()}; }}
QDialog QPushButton:pressed, QMessageBox QPushButton:pressed {{ background: {t.orange}; }}
"""


class ThemeManager(QObject):
    """Owns the active theme and re-skins the whole app when it changes."""

    changed = Signal(object)  # Theme
    MODES = ("light", "dark", "system")

    def __init__(self, mode: str = "system") -> None:
        super().__init__()
        self.mode = mode if mode in self.MODES else "system"
        hints = QGuiApplication.styleHints()
        if hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(self._system_changed)

    def resolve(self) -> Theme:
        if self.mode == "light":
            return LIGHT
        if self.mode == "dark":
            return DARK
        scheme = getattr(QGuiApplication.styleHints(), "colorScheme", lambda: Qt.ColorScheme.Light)()
        return DARK if scheme == Qt.ColorScheme.Dark else LIGHT

    def set_mode(self, mode: str) -> None:
        self.mode = mode if mode in self.MODES else "system"
        self.apply()

    def cycle(self) -> str:
        self.set_mode(self.MODES[(self.MODES.index(self.mode) + 1) % len(self.MODES)])
        return self.mode

    def _system_changed(self, *_: object) -> None:
        if self.mode == "system":
            self.apply()

    def apply(self) -> None:
        global _current
        _current = self.resolve()
        app = QApplication.instance()
        if app is not None:
            app.setPalette(palette_for(_current))
            app.setStyleSheet(build_stylesheet(_current))
            for widget in app.allWidgets():
                if hasattr(widget, "apply_theme"):
                    widget.apply_theme(_current)
                QWidget.update(widget)  # item views overload update(index), so call the base
        self.changed.emit(_current)
