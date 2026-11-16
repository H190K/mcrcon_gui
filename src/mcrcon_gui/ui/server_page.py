"""One server's console: status strip, console output, hint bar and command line."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from ..core.completion import CompletionContext, CompletionEngine
from ..core.models import ConsoleEntry
from . import theme
from .command_input import CommandLineEdit, HintBar, SuggestionPopup
from .console import ConsoleView
from .session import Session
from .theme import Theme, display_font, mono_font
from .widgets import Badge, BrutalButton, Card, Toggle

STATE_BADGES = {
    "online": ("● Online", "green"),
    "connecting": ("Connecting…", "orange"),
    "reconnecting": ("Reconnecting…", "orange"),
    "offline": ("○ Offline", "surface"),
}


class ServerPage(QWidget):
    toast = Signal(str, str)
    connect_requested = Signal(object)  # Session — the window may need to ask for a password
    edit_requested = Signal(str)
    command_submitted = Signal(object, str)  # Session, command — the window confirms dangerous ones

    def __init__(self, session: Session, engine: CompletionEngine, settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.session = session
        self.settings = settings
        page = QVBoxLayout(self)
        page.setContentsMargins(0, 0, 0, 0)
        page.setSpacing(14)

        # -- status strip ---------------------------------------------------------------
        strip = QHBoxLayout()
        strip.setSpacing(12)
        self.state_badge = Badge()
        self.address_label = QLabel()
        self.address_label.setObjectName("hint")
        self.address_label.setFont(mono_font(12))
        strip.addWidget(self.state_badge)
        strip.addWidget(self.address_label)
        strip.addStretch(1)
        self.edit_button = BrutalButton("Edit", "surface", compact=True, icon="edit")
        self.edit_button.setToolTip("Edit this server")
        self.edit_button.clicked.connect(lambda: self.edit_requested.emit(self.session.profile.id))
        self.connect_button = BrutalButton("Connect", "green", icon="plug")
        self.connect_button.setMinimumWidth(170)
        self.connect_button.setToolTip("Connect / disconnect (Ctrl+Enter)")
        self.connect_button.clicked.connect(self.toggle_connection)
        strip.addWidget(self.edit_button)
        strip.addWidget(self.connect_button)
        page.addLayout(strip)

        # -- console card ---------------------------------------------------------------
        self.card = Card("Console", "purple", icon="terminal")
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter…  Ctrl+F")
        self.filter.setClearButtonEnabled(True)
        self.filter.setFixedWidth(190)
        self.filter.textChanged.connect(self._apply_filter)
        stamp_label = QLabel("Time")
        stamp_label.setObjectName("hint")
        self.timestamps = Toggle(settings.show_timestamps)
        self.timestamps.setToolTip("Show timestamps")
        self.timestamps.toggled.connect(self._toggle_timestamps)
        hl = self.card.header_layout
        hl.addWidget(self.filter)
        hl.addSpacing(4)
        hl.addWidget(stamp_label)
        hl.addWidget(self.timestamps)
        for text, icon, slot, tip in (
            ("", "copy", self.copy_log, "Copy the console"),
            ("", "download", self.export_log, "Export to a file (Ctrl+E)"),
            ("", "eraser", self.session.clear_log, "Clear (Ctrl+L)"),
        ):
            button = BrutalButton(text, "surface", compact=True, icon=icon)
            button.setFixedWidth(44)
            button.setToolTip(tip)
            button.clicked.connect(slot)
            hl.addWidget(button)

        lay = self.card.body_layout
        self.console = ConsoleView()
        self.console.show_timestamps = settings.show_timestamps
        lay.addWidget(self.console, 1)
        self.hint = HintBar()
        lay.addWidget(self.hint)

        self.popup = SuggestionPopup(self)
        row = QHBoxLayout()
        row.setSpacing(10)
        self.prompt = QLabel("/")
        self.prompt.setFont(display_font(18))
        self.prompt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.prompt.setFixedSize(40, 40)
        self.input = CommandLineEdit(self.popup, self.hint, self._context, engine)
        self.input.history = session.profile.history
        self.input.setPlaceholderText("Type a command. Tab completes, e.g. gamemode creative Alex")
        self.input.submitted.connect(lambda text: self.command_submitted.emit(self.session, text))
        self.send_button = BrutalButton("Send", "yellow", icon="send")
        self.send_button.setFixedWidth(120)
        self.send_button.clicked.connect(self.input._submit)
        row.addWidget(self.prompt)
        row.addWidget(self.input, 1)
        row.addWidget(self.send_button)
        lay.addLayout(row)
        page.addWidget(self.card, 1)

        session.entry_added.connect(self._on_entry)
        session.log_cleared.connect(self.console.clear)
        session.state_changed.connect(self._on_state)
        self.update_profile()
        self._on_state(session.state)
        self.console.render_entries(session.log.entries)
        self.hint.show_completion(None)
        self.apply_theme(theme.current())

    # -- helpers -------------------------------------------------------------------------

    def _context(self) -> CompletionContext:
        s = self.session
        return CompletionContext(players=s.players.names if s.players else [], extra_commands=s.known_commands)

    def update_profile(self) -> None:
        p = self.session.profile
        self.address_label.setText(f"{p.display()}  ·  RCON")
        self.card.set_accent(p.color)
        self.card.set_title(f"Console · {p.name}")

    def apply_theme(self, t: Theme) -> None:
        self.prompt.setStyleSheet(f"QLabel {{ background:{t.ink}; color:{t.paper}; }}")

    def _on_entry(self, entry: ConsoleEntry) -> None:
        self.console.add_entry(entry)

    def _on_state(self, state: str) -> None:
        text, color = STATE_BADGES.get(state, STATE_BADGES["offline"])
        self.state_badge.set(text, color)
        online = state == "online"
        busy = state in ("connecting", "reconnecting")
        if online:
            label, color, icon = "Disconnect", "red", "power"
        elif state == "reconnecting":
            label, color, icon = "Stop retrying", "red", "x"
        elif busy:
            label, color, icon = "Connecting…", "orange", "plug"
        else:
            label, color, icon = "Connect", "green", "plug"
        self.connect_button.setText(label)
        self.connect_button.set_color(color)
        self.connect_button.set_icon_name(icon)
        self.connect_button.setEnabled(state != "connecting")
        self.send_button.setEnabled(online)

    def toggle_connection(self) -> None:
        if self.session.state in ("online", "reconnecting"):
            self.session.disconnect_server()
        else:
            self.connect_requested.emit(self.session)

    def _apply_filter(self, text: str) -> None:
        self.console.filter_text = text.strip()
        self.console.render_entries(self.session.log.entries)

    def _toggle_timestamps(self, on: bool) -> None:
        self.set_timestamps(on)

    def set_timestamps(self, on: bool) -> None:
        self.settings.show_timestamps = on
        if self.timestamps.isChecked() != on:
            self.timestamps.blockSignals(True)
            self.timestamps.setChecked(on)
            self.timestamps.blockSignals(False)
        self.console.show_timestamps = on
        self.console.render_entries(self.session.log.entries)

    def copy_log(self) -> None:
        QGuiApplication.clipboard().setText(self.session.log.to_text(self.console.show_timestamps))
        self.toast.emit("Console copied", "yellow")

    def export_log(self) -> None:
        name = f"{self.session.profile.name}-{datetime.now():%Y%m%d-%H%M%S}.log".replace(" ", "_")
        path, _ = QFileDialog.getSaveFileName(self, "Export console", str(Path.home() / name), "Log files (*.log *.txt)")
        if not path:
            return
        try:
            Path(path).write_text(self.session.log.to_text(True), encoding="utf-8")
        except OSError as exc:
            self.toast.emit(f"Export failed: {exc}", "red")
            return
        self.toast.emit("Console exported", "green")

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self.popup.isVisible():
            self.input.show_suggestions()

    def hideEvent(self, event) -> None:  # noqa: N802
        self.popup.hide()
        super().hideEvent(event)
