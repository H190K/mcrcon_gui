"""One :class:`Session` per server profile, and a :class:`SessionManager` that owns them all.

Each session has its own worker thread: RCON is blocking request/response, so a slow
or stopping server must never hold up commands sent to another one.
"""

from __future__ import annotations

import itertools

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from ..core import storage
from ..core.models import AppSettings, ConsoleLog, PlayerList, ServerProfile
from ..core.players import parse_help_reply, parse_list_reply
from .worker import RconWorker

PLAYER_POLL_MS = 30_000
RECONNECT_DELAYS = (2, 4, 8, 16, 30, 30)  # seconds
CONNECT_TIMEOUT = 5.0
_REFRESH_AFTER = {"kick", "ban", "pardon", "op", "deop", "whitelist"}


class Session(QObject):
    state_changed = Signal(str)  # offline | connecting | online | reconnecting
    entry_added = Signal(object)  # ConsoleEntry
    log_cleared = Signal()
    players_changed = Signal(object)  # PlayerList | None
    commands_discovered = Signal(object)  # set[str]
    auth_failed = Signal()

    _request_open = Signal(str, int, str, float)
    _request_close = Signal()
    _request_run = Signal(int, str)

    def __init__(self, profile: ServerProfile, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.profile = profile
        self.state = "offline"
        self.players: PlayerList | None = None
        self.log = ConsoleLog()
        self.known_commands: set[str] = set()
        self.unread = 0
        self.last_error = ""
        self._password = profile.password
        self._tickets = itertools.count(1)
        self._silent: set[int] = set()
        self._expect_drop = False
        self._attempt = 0

        self._thread = QThread()
        self._worker = RconWorker()
        self._worker.moveToThread(self._thread)
        self._request_open.connect(self._worker.open)
        self._request_close.connect(self._worker.close)
        self._request_run.connect(self._worker.run)
        self._worker.connected.connect(self._on_connected)
        self._worker.connect_failed.connect(self._on_connect_failed)
        self._worker.disconnected.connect(self._on_disconnected)
        self._worker.reply.connect(self._on_reply)
        self._worker.failed.connect(self._on_failed)
        self._thread.start()

        self._poll = QTimer(self, interval=PLAYER_POLL_MS, timeout=self.refresh_players)
        self._retry = QTimer(self, singleShot=True, timeout=self._reconnect_now)
        self.log.append("system", f"Ready. Press CONNECT to open an RCON session to {profile.display()} (EDIT changes the address).")

    # -- public API ----------------------------------------------------------------------

    @property
    def online(self) -> bool:
        return self.state == "online"

    def connect_server(self, password: str | None = None) -> None:
        if self.state in ("online", "connecting"):
            return
        self._retry.stop()
        self._attempt = 0
        if password is not None:
            self._password = password
        self._open("Connecting")

    def disconnect_server(self) -> None:
        self._retry.stop()
        self._attempt = 0
        if self.state == "online":
            self._request_close.emit()
        elif self.state == "reconnecting":
            self._set_state("offline")
            self.log_line("system", "Stopped reconnecting.")

    def run(self, command: str, *, silent: bool = False) -> int:
        command = command.strip().removeprefix("/")
        if not command:
            return 0
        if not self.online:
            self.log_line("error", "Not connected. Press CONNECT first.")
            return 0
        ticket = next(self._tickets)
        if silent:
            self._silent.add(ticket)
        else:
            self.log_line("command", command)
            self.profile.add_history(command)
        if command.split()[0].lower() == "stop":
            self._expect_drop = True
        self._request_run.emit(ticket, command)
        return ticket

    def refresh_players(self) -> None:
        if self.online:
            self.run("list", silent=True)

    def log_line(self, kind: str, text: str, meta: str = "") -> None:
        self.entry_added.emit(self.log.append(kind, text, meta))

    def clear_log(self) -> None:
        self.log.clear()
        self.log_cleared.emit()

    def set_password(self, password: str) -> None:
        self._password = password

    def dispose(self) -> None:
        self._poll.stop()
        self._retry.stop()
        self._thread.quit()
        self._thread.wait(6000)
        self._worker.shutdown()

    # -- internals -----------------------------------------------------------------------

    def _open(self, verb: str) -> None:
        p = self.profile
        self._set_state("connecting" if verb == "Connecting" else "reconnecting")
        self.log_line("system", f"{verb} to {p.host}:{p.port}…")
        self._request_open.emit(p.host, p.port, self._password, CONNECT_TIMEOUT)

    def _reconnect_now(self) -> None:
        self._open(f"Reconnecting (attempt {self._attempt}/{len(RECONNECT_DELAYS)})")

    def _schedule_reconnect(self) -> bool:
        if not self.profile.auto_reconnect or self._attempt >= len(RECONNECT_DELAYS):
            return False
        delay = RECONNECT_DELAYS[self._attempt]
        self._attempt += 1
        self._set_state("reconnecting")
        self.log_line("system", f"Retrying in {delay}s…")
        self._retry.start(delay * 1000)
        return True

    def _set_state(self, state: str) -> None:
        if state != self.state:
            self.state = state
            if state != "online":
                self._poll.stop()
            self.state_changed.emit(state)

    def _on_connected(self, host: str, port: int) -> None:
        self._attempt = 0
        self._expect_drop = False
        self.last_error = ""
        self._set_state("online")
        self.log_line("ok", f"Connected to {host}:{port}.")
        self._poll.start()
        self.refresh_players()
        self.run("help", silent=True)

    def _on_connect_failed(self, message: str, auth: bool) -> None:
        self.last_error = message
        self.log_line("error", f"Connection failed: {message}")
        if auth:
            self._set_state("offline")
            self.auth_failed.emit()
        elif self._attempt == 0 or not self._schedule_reconnect():
            self._set_state("offline")

    def _on_disconnected(self, reason: str) -> None:
        self.players = None
        self.players_changed.emit(None)
        if not reason:
            self._set_state("offline")
            self.log_line("system", "Disconnected.")
            return
        self.log_line("error", f"Disconnected: {reason}")
        if self._expect_drop:
            self._expect_drop = False
            self._set_state("offline")
        elif not self._schedule_reconnect():
            self._set_state("offline")

    def _on_reply(self, ticket: int, command: str, response: str, ms: float) -> None:
        silent = ticket in self._silent
        self._silent.discard(ticket)
        root = command.split()[0].lower()
        if root == "list":
            players = parse_list_reply(response)
            if players is not None:
                self.players = players
                self.players_changed.emit(players)
        elif root == "help" and silent:
            found = parse_help_reply(response)
            if found:
                self.known_commands = found
                self.commands_discovered.emit(found)
        if root in _REFRESH_AFTER and not silent:
            QTimer.singleShot(400, self.refresh_players)
        if not silent:
            self.unread += 1
            self.log_line("output", response.rstrip() or "", meta=f"{ms:.0f} ms")
        if root == "stop" and self.online:
            # The server is shutting down; close our side now instead of waiting to notice.
            self._expect_drop = False
            self._retry.stop()
            self._request_close.emit()

    def _on_failed(self, ticket: int, command: str, message: str) -> None:
        if ticket in self._silent:
            self._silent.discard(ticket)
            return
        self.log_line("error", f"/{command} failed: {message}")


class SessionManager(QObject):
    session_added = Signal(object)  # Session
    session_removed = Signal(str)  # profile id
    active_changed = Signal(str)

    def __init__(self, settings: AppSettings, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        settings.ensure_default_profile()
        self.sessions: dict[str, Session] = {}
        self._save_timer = QTimer(self, singleShot=True, interval=500, timeout=self.save_now)
        for profile in settings.profiles:
            self._create(profile)

    def _create(self, profile: ServerProfile) -> Session:
        session = Session(profile, self)
        session.state_changed.connect(lambda _s: self.request_save())
        self.sessions[profile.id] = session
        return session

    # -- profiles ------------------------------------------------------------------------

    def add_profile(self, profile: ServerProfile) -> Session:
        self.settings.profiles.append(profile)
        session = self._create(profile)
        self.session_added.emit(session)
        self.request_save()
        return session

    def remove_profile(self, profile_id: str) -> None:
        session = self.sessions.pop(profile_id, None)
        if session is None:
            return
        session.dispose()
        self.settings.profiles = [p for p in self.settings.profiles if p.id != profile_id]
        self.session_removed.emit(profile_id)
        if self.settings.active_profile_id == profile_id and self.settings.profiles:
            self.set_active(self.settings.profiles[0].id)
        self.request_save()

    def update_profile(self, profile: ServerProfile) -> None:
        session = self.sessions.get(profile.id)
        if session is not None:
            session.set_password(profile.password)
        self.request_save()

    def set_active(self, profile_id: str) -> None:
        if profile_id in self.sessions and profile_id != self.settings.active_profile_id:
            self.settings.active_profile_id = profile_id
            self.sessions[profile_id].unread = 0
            self.active_changed.emit(profile_id)
            self.request_save()

    def active(self) -> Session:
        return self.sessions[self.settings.ensure_default_profile().id]

    def ordered(self) -> list[Session]:
        return [self.sessions[p.id] for p in self.settings.profiles if p.id in self.sessions]

    # -- lifecycle -----------------------------------------------------------------------

    def start(self) -> None:
        for session in self.ordered():
            if session.profile.auto_connect and session.profile.password:
                session.connect_server()

    def request_save(self) -> None:
        self._save_timer.start()

    def save_now(self) -> None:
        self._save_timer.stop()
        try:
            storage.save(self.settings)
        except OSError:
            pass  # never crash over a settings write; the next save will retry

    def shutdown(self) -> None:
        self.save_now()
        for session in self.sessions.values():
            session.dispose()
