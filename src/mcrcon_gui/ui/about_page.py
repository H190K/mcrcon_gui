"""About: who made it, where it lives, that it's open source, and what it's built with."""

from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from .. import APP_WEBSITE, AUTHOR, AUTHOR_HANDLE, AUTHOR_URL, REPO_URL, __version__
from . import theme
from .theme import Theme, display_font, mono_font
from .widgets import BrutalButton, Card, PageHeader

CREDITS = [
    ("Qt 6 / PySide6", "https://www.qt.io/qt-for-python", "LGPL v3", "User interface toolkit"),
    ("Python", "https://www.python.org", "PSF License", "Language and runtime"),
    ("PyInstaller", "https://pyinstaller.org", "GPL v2 + bootloader exception", "Packages the app"),
    ("Inno Setup", "https://jrsoftware.org/isinfo.php", "Inno Setup License", "Windows installer"),
    ("Archivo Black", "https://fonts.google.com/specimen/Archivo+Black", "SIL OFL 1.1", "Display font"),
    ("Space Mono", "https://fonts.google.com/specimen/Space+Mono", "SIL OFL 1.1", "Interface and console font"),
]


def _open(url: str) -> None:
    QDesktopServices.openUrl(QUrl(url))


class AboutPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 22, 28, 18)
        outer.setSpacing(16)
        outer.addWidget(PageHeader("About", f"Version {__version__}", "green"))

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

        # -- identity --------------------------------------------------------------------
        hero = Card("MCRCON GUI", "yellow", icon="terminal")
        top = QHBoxLayout()
        top.setSpacing(22)
        icon = QLabel()
        icon.setPixmap(QIcon(str(theme.ASSETS / "icon.png")).pixmap(112, 112))
        top.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        text = QVBoxLayout()
        text.setSpacing(6)
        name = QLabel("MCRCON GUI")
        name.setFont(display_font(28))
        tagline = QLabel("A desktop control panel for Minecraft servers over RCON.")
        tagline.setFont(mono_font(13))
        self.byline = QLabel()
        self.byline.setOpenExternalLinks(True)
        self.byline.setFont(mono_font(13))
        text.addWidget(name)
        text.addWidget(tagline)
        text.addWidget(self.byline)
        text.addSpacing(8)
        links = QHBoxLayout()
        links.setSpacing(10)
        for label, icon_name, color, url in (
            ("mcrcon.app", "globe", "yellow", APP_WEBSITE),
            ("Source code", "github", "surface", REPO_URL),
            ("Report a bug", "bug", "surface", f"{REPO_URL}/issues/new/choose"),
        ):
            button = BrutalButton(label, color, compact=True, icon=icon_name)
            button.setToolTip(url)
            button.clicked.connect(lambda _=False, u=url: _open(u))
            links.addWidget(button)
        links.addStretch(1)
        text.addLayout(links)
        top.addLayout(text, 1)
        hero.body_layout.addLayout(top)
        col.addWidget(hero)

        # -- open source -----------------------------------------------------------------
        oss = Card("Completely open source", "green", icon="code")
        self.oss_text = QLabel()
        self.oss_text.setWordWrap(True)
        self.oss_text.setOpenExternalLinks(True)
        self.oss_text.setFont(mono_font(13))
        oss.body_layout.addWidget(self.oss_text)
        col.addWidget(oss)

        # -- credits ---------------------------------------------------------------------
        credits = Card("Built with", "purple", icon="heart")
        self.credit_grid = QGridLayout()
        self.credit_grid.setHorizontalSpacing(24)
        self.credit_grid.setVerticalSpacing(10)
        self._credit_labels: list[QLabel] = []
        for row, (name_, url, lic, what) in enumerate(CREDITS):
            link = QLabel()
            link.setOpenExternalLinks(True)
            link.setProperty("credit", (name_, url))
            link.setFont(display_font(12))
            lic_label = QLabel(lic)
            lic_label.setObjectName("hint")
            what_label = QLabel(what)
            what_label.setObjectName("hint")
            self.credit_grid.addWidget(link, row, 0)
            self.credit_grid.addWidget(lic_label, row, 1)
            self.credit_grid.addWidget(what_label, row, 2)
            self._credit_labels.append(link)
        self.credit_grid.setColumnStretch(2, 1)
        credits.body_layout.addLayout(self.credit_grid)
        legal = QLabel(
            "Full license texts ship as LICENSE and THIRD_PARTY_NOTICES.md in the install folder. "
            "Minecraft is a trademark of Mojang Synergies AB. MCRCON GUI is not affiliated with Mojang or Microsoft."
        )
        legal.setObjectName("hint")
        legal.setWordWrap(True)
        credits.body_layout.addSpacing(6)
        credits.body_layout.addWidget(legal)
        col.addWidget(credits)
        col.addStretch(1)
        self.apply_theme(theme.current())

    def apply_theme(self, t: Theme) -> None:
        link = f'style="color:{t.text}"'
        self.byline.setText(f'Made by <b>{AUTHOR}</b> (<a {link} href="{AUTHOR_URL}">{AUTHOR_HANDLE}</a>) · MIT License · free forever')
        self.oss_text.setText(
            f"Every line of MCRCON GUI is public on "
            f'<a {link} href="{REPO_URL}">GitHub</a> under the MIT License. Read the code, build it yourself, '
            f'<a {link} href="{REPO_URL}/issues">report issues</a> or '
            f'<a {link} href="{REPO_URL}/blob/main/CONTRIBUTING.md">send a pull request</a>. '
            f"There is no account, no telemetry and no ads: the only thing the app contacts besides your servers "
            f"is {APP_WEBSITE.removeprefix('https://')} to check for updates."
        )
        for label in self._credit_labels:
            name, url = label.property("credit")
            label.setText(f'<a {link} href="{url}">{name}</a>')
