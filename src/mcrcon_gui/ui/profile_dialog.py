"""Add / edit a saved server."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..core.models import ACCENT_KEYS, ServerProfile
from .theme import display_font
from .widgets import BrutalButton


class ProfileDialog(QDialog):
    def __init__(self, profile: ServerProfile | None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._original = profile
        p = profile or ServerProfile()
        self.setWindowTitle("Edit server" if profile else "Add server")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)
        title = QLabel(("Edit server" if profile else "Add a server").upper())
        title.setFont(display_font(20))
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)

        def label(text: str, widget: QWidget) -> QLabel:
            lbl = QLabel(text.upper(), objectName="fieldLabel")
            lbl.setBuddy(widget)
            return lbl

        self.name = QLineEdit(p.name if profile else "")
        self.name.setPlaceholderText("Survival")
        self.host = QLineEdit(p.host)
        self.host.setPlaceholderText("localhost or play.example.com")
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(p.port)
        self.port.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.port.setFixedWidth(100)
        self.password = QLineEdit(p.password)
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("rcon.password from server.properties")
        reveal = BrutalButton("Show", "surface", compact=True)
        reveal.setCheckable(True)
        reveal.setFixedWidth(76)
        reveal.toggled.connect(
            lambda on: (self.password.setEchoMode(QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password), reveal.setText("Hide" if on else "Show"))
        )
        self.color = QComboBox()
        for key in ACCENT_KEYS:
            self.color.addItem(key.title(), key)
        self.color.setCurrentIndex(max(0, self.color.findData(p.color)))

        grid.addWidget(label("Name", self.name), 0, 0, 1, 2)
        grid.addWidget(label("Colour", self.color), 0, 2)
        grid.addWidget(self.name, 1, 0, 1, 2)
        grid.addWidget(self.color, 1, 2)
        grid.addWidget(label("Host", self.host), 2, 0, 1, 2)
        grid.addWidget(label("RCON port", self.port), 2, 2)
        grid.addWidget(self.host, 3, 0, 1, 2)
        grid.addWidget(self.port, 3, 2)
        grid.addWidget(label("Password", self.password), 4, 0, 1, 3)
        pw = QHBoxLayout()
        pw.addWidget(self.password, 1)
        pw.addWidget(reveal)
        grid.addLayout(pw, 5, 0, 1, 3)
        grid.setColumnStretch(0, 1)
        layout.addLayout(grid)

        self.remember = QCheckBox("Remember password")
        self.remember.setChecked(p.remember_password)
        self.auto_connect = QCheckBox("Connect when the app starts")
        self.auto_connect.setChecked(p.auto_connect)
        self.auto_reconnect = QCheckBox("Reconnect automatically if the connection drops")
        self.auto_reconnect.setChecked(p.auto_reconnect)
        for box in (self.remember, self.auto_connect, self.auto_reconnect):
            layout.addWidget(box)

        self.error = QLabel()
        self.error.setObjectName("hint")
        layout.addWidget(self.error)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = BrutalButton("Cancel", "surface", compact=True)
        cancel.clicked.connect(self.reject)
        save = BrutalButton("Save", "green", compact=True)
        save.setDefault(True)
        save.clicked.connect(self._save)
        save.setFixedWidth(110)
        cancel.setFixedWidth(110)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)
        (self.name if not profile else self.password).setFocus()

    def _save(self) -> None:
        if not self.host.text().strip():
            self.error.setText("Enter the server's host name or IP address.")
            self.host.setFocus()
            return
        self.accept()

    def result_profile(self) -> ServerProfile:
        base = self._original or ServerProfile()
        host = self.host.text().strip()
        return replace(
            base,
            name=self.name.text().strip() or host,
            host=host,
            port=self.port.value(),
            password=self.password.text(),
            remember_password=self.remember.isChecked(),
            auto_connect=self.auto_connect.isChecked(),
            auto_reconnect=self.auto_reconnect.isChecked(),
            color=self.color.currentData(),
        )
