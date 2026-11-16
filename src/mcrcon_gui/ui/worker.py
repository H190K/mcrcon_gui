"""Runs all network I/O for one server on a background thread so the window never freezes."""

from __future__ import annotations

import time

from PySide6.QtCore import QObject, Signal, Slot

from ..core.rcon import RconAuthError, RconClient, RconError


class RconWorker(QObject):
    """Lives on a QThread. Its session talks to it only through queued signals."""

    connected = Signal(str, int)
    connect_failed = Signal(str, bool)  # message, is_auth_error
    disconnected = Signal(str)  # reason, empty when the user asked for it
    reply = Signal(int, str, str, float)  # ticket, command, response, round-trip ms
    failed = Signal(int, str, str)  # ticket, command, error message

    def __init__(self) -> None:
        super().__init__()
        self._client: RconClient | None = None

    @Slot(str, int, str, float)
    def open(self, host: str, port: int, password: str, timeout: float) -> None:
        self._drop()
        client = RconClient(host, port, password, timeout=timeout)
        try:
            client.connect()
        except RconAuthError:
            self.connect_failed.emit("Wrong RCON password. Check rcon.password in server.properties.", True)
            return
        except RconError as exc:
            self.connect_failed.emit(str(exc), False)
            return
        self._client = client
        self.connected.emit(host, port)

    @Slot()
    def close(self) -> None:
        if self._client is not None:
            self._drop()
            self.disconnected.emit("")

    @Slot(int, str)
    def run(self, ticket: int, command: str) -> None:
        if self._client is None:
            self.failed.emit(ticket, command, "Not connected.")
            return
        started = time.perf_counter()
        try:
            response = self._client.command(command)
        except ValueError as exc:
            self.failed.emit(ticket, command, str(exc))
        except RconError as exc:
            # Any protocol error leaves the socket in an unknown state, so drop it.
            self._drop()
            self.failed.emit(ticket, command, str(exc))
            self.disconnected.emit(str(exc))
        else:
            self.reply.emit(ticket, command, response, (time.perf_counter() - started) * 1000)
            if not self._client.connected:  # the server hung up right after replying (e.g. "stop")
                self._client = None
                self.disconnected.emit("The server closed the connection.")

    def shutdown(self) -> None:
        self._drop()

    def _drop(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
