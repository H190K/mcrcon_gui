"""Plain data classes for servers, settings and the console log."""

from __future__ import annotations

import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime

HISTORY_LIMIT = 200
ACCENT_KEYS = ("yellow", "pink", "cyan", "green", "orange", "purple")


@dataclass
class QuickCommand:
    label: str
    command: str


DEFAULT_QUICK_COMMANDS = [
    QuickCommand("Day", "time set day"),
    QuickCommand("Night", "time set night"),
    QuickCommand("Clear", "weather clear"),
    QuickCommand("Rain", "weather rain"),
    QuickCommand("Thunder", "weather thunder"),
    QuickCommand("Players", "list"),
    QuickCommand("Save all", "save-all"),
    QuickCommand("Whitelist", "whitelist list"),
    QuickCommand("Seed", "seed"),
]


def new_id() -> str:
    return uuid.uuid4().hex


@dataclass
class ServerProfile:
    name: str = "My server"
    host: str = "localhost"
    port: int = 25575
    password: str = ""
    remember_password: bool = True
    auto_connect: bool = False
    auto_reconnect: bool = True
    color: str = "yellow"
    history: list[str] = field(default_factory=list)
    id: str = field(default_factory=new_id)

    def add_history(self, command: str) -> None:
        command = command.strip()
        if not command:
            return
        if command in self.history:
            self.history.remove(command)
        self.history.append(command)
        del self.history[:-HISTORY_LIMIT]

    def display(self) -> str:
        return f"{self.host}:{self.port}"


@dataclass
class AppSettings:
    theme: str = "system"  # "light" | "dark" | "system"
    show_timestamps: bool = True
    confirm_dangerous: bool = True
    auto_update: bool = True  # check every 24 h, download in the background, install on request/exit
    last_update_check: str = ""  # ISO timestamp
    quick_commands: list[QuickCommand] = field(default_factory=lambda: [QuickCommand(q.label, q.command) for q in DEFAULT_QUICK_COMMANDS])
    profiles: list[ServerProfile] = field(default_factory=list)
    active_profile_id: str | None = None
    window: dict = field(default_factory=lambda: {"w": 1280, "h": 860})

    def profile(self, profile_id: str | None) -> ServerProfile | None:
        return next((p for p in self.profiles if p.id == profile_id), None)

    def ensure_default_profile(self) -> ServerProfile:
        if not self.profiles:
            self.profiles.append(ServerProfile(name="Local server"))
        if self.profile(self.active_profile_id) is None:
            self.active_profile_id = self.profiles[0].id
        return self.profile(self.active_profile_id)  # type: ignore[return-value]


@dataclass
class ConsoleEntry:
    kind: str  # "command" | "output" | "system" | "ok" | "error"
    text: str
    at: datetime = field(default_factory=datetime.now)
    meta: str = ""  # e.g. round-trip time, shown muted after the text


class ConsoleLog:
    def __init__(self, max_entries: int = 5000) -> None:
        self.entries: deque[ConsoleEntry] = deque(maxlen=max_entries)

    def append(self, kind: str, text: str, meta: str = "") -> ConsoleEntry:
        entry = ConsoleEntry(kind, text, meta=meta)
        self.entries.append(entry)
        return entry

    def clear(self) -> None:
        self.entries.clear()

    def filtered(self, needle: str) -> list[ConsoleEntry]:
        needle = needle.lower()
        return [e for e in self.entries if needle in e.text.lower()]

    def to_text(self, timestamps: bool = True) -> str:
        from .formatting import strip_codes

        lines = []
        for e in self.entries:
            text = f"> /{e.text}" if e.kind == "command" else strip_codes(e.text)
            lines.append(f"[{e.at:%Y-%m-%d %H:%M:%S}] {text}" if timestamps else text)
        return "\n".join(lines) + "\n"


@dataclass
class PlayerList:
    online: int
    maximum: int
    names: list[str]
