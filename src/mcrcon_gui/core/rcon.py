"""Minimal, dependency-free implementation of the Source RCON protocol as used by Minecraft.

Packet layout (little-endian)::

    int32 length      # size of everything after this field
    int32 request_id
    int32 type        # 3 = login, 2 = command, 0 = response
    bytes payload     # UTF-8
    b"\\x00\\x00"     # payload terminator + empty string terminator

Minecraft splits long responses over several packets, but never says how many.
To know when a response is complete we send a second "sentinel" packet with an
unknown type right after the command. The server answers packets in order, so
once the sentinel's reply arrives, every fragment of the real reply has too.
"""

from __future__ import annotations

import itertools
import socket
import struct
import threading
from dataclasses import dataclass

SERVERDATA_RESPONSE_VALUE = 0
SERVERDATA_EXECCOMMAND = 2
SERVERDATA_AUTH = 3
SENTINEL_TYPE = 200  # any type the server does not understand

# Minecraft rejects incoming packets whose payload exceeds 1446 bytes.
MAX_COMMAND_BYTES = 1446
MAX_PACKET_BYTES = 4110  # 4096 payload + header + terminators, sent by the server


class RconError(Exception):
    """Base class for every error raised by :class:`RconClient`."""


class RconAuthError(RconError):
    """The server rejected the RCON password."""


class RconConnectionError(RconError):
    """The socket could not be opened, or was closed by the server."""


@dataclass(frozen=True)
class Packet:
    request_id: int
    type: int
    payload: str

    def encode(self) -> bytes:
        body = struct.pack("<ii", self.request_id, self.type) + self.payload.encode("utf-8") + b"\x00\x00"
        return struct.pack("<i", len(body)) + body


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        chunk = sock.recv(size - len(chunks))
        if not chunk:
            raise RconConnectionError("The server closed the connection.")
        chunks.extend(chunk)
    return bytes(chunks)


def read_packet(sock: socket.socket) -> Packet:
    (length,) = struct.unpack("<i", _recv_exact(sock, 4))
    if length < 10 or length > MAX_PACKET_BYTES * 4:
        raise RconConnectionError(f"Received a malformed packet (length {length}).")
    data = _recv_exact(sock, length)
    request_id, packet_type = struct.unpack("<ii", data[:8])
    payload = data[8:-2].decode("utf-8", errors="replace")
    return Packet(request_id, packet_type, payload)


class RconClient:
    """A thread-safe, persistent RCON connection.

    Usage::

        with RconClient("localhost", 25575, "secret") as rcon:
            print(rcon.command("list"))
    """

    def __init__(self, host: str, port: int, password: str, timeout: float = 5.0) -> None:
        self.host = host
        self.port = int(port)
        self.password = password
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._ids = itertools.count(1)
        self._lock = threading.Lock()

    # -- lifecycle -----------------------------------------------------------------

    @property
    def connected(self) -> bool:
        return self._sock is not None

    def connect(self) -> None:
        with self._lock:
            self._close_locked()
            self._sock = self._open_socket()
            try:
                self._authenticate_locked()
            except BaseException:
                self._close_locked()
                raise

    def close(self) -> None:
        with self._lock:
            self._close_locked()

    def __enter__(self) -> "RconClient":
        self.connect()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # -- commands ------------------------------------------------------------------

    def command(self, command: str) -> str:
        """Run ``command`` on the server and return its full (possibly multi-packet) reply."""
        command = command.strip().removeprefix("/")
        if not command:
            raise ValueError("Command is empty.")
        if len(command.encode("utf-8")) > MAX_COMMAND_BYTES:
            raise ValueError(f"Command is longer than {MAX_COMMAND_BYTES} bytes.")

        with self._lock:
            sock = self._require_socket()
            request_id = next(self._ids)
            sentinel_id = next(self._ids)
            parts: list[str] = []
            try:
                sock.sendall(Packet(request_id, SERVERDATA_EXECCOMMAND, command).encode())
                sock.sendall(Packet(sentinel_id, SENTINEL_TYPE, "").encode())
                self._collect_reply_locked(sock, request_id, sentinel_id, parts)
                return "".join(parts)
            except (OSError, RconConnectionError) as exc:  # socket.timeout is an OSError
                self._close_locked()
                if parts:
                    # e.g. after "stop": the reply arrived, then the server went away.
                    return "".join(parts)
                if isinstance(exc, RconConnectionError):
                    raise
                if isinstance(exc, socket.timeout):
                    raise RconConnectionError("The server did not answer in time.") from exc
                raise RconConnectionError(f"Connection lost ({exc}).") from exc

    # -- internals -----------------------------------------------------------------

    def _open_socket(self) -> socket.socket:
        try:
            addresses = socket.getaddrinfo(self.host, self.port, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise RconConnectionError(f"Could not resolve {self.host} ({exc}).") from exc
        # Minecraft listens on IPv4 by default, and on Windows a refused IPv6 attempt
        # (e.g. "localhost" -> ::1) takes seconds, so try IPv4 addresses first.
        addresses.sort(key=lambda info: info[0] != socket.AF_INET)
        error: OSError | None = None
        for family, kind, proto, _, address in addresses:
            sock = socket.socket(family, kind, proto)
            sock.settimeout(self.timeout)
            try:
                sock.connect(address)
                return sock
            except OSError as exc:
                sock.close()
                error = exc
        raise RconConnectionError(f"Could not reach {self.host}:{self.port} ({error}).")

    def _require_socket(self) -> socket.socket:
        if self._sock is None:
            raise RconConnectionError("Not connected.")
        return self._sock

    def _authenticate_locked(self) -> None:
        sock = self._require_socket()
        request_id = next(self._ids)
        try:
            sock.sendall(Packet(request_id, SERVERDATA_AUTH, self.password).encode())
            while True:
                packet = read_packet(sock)
                # Some servers send an empty RESPONSE_VALUE before the auth reply.
                if packet.type == SERVERDATA_RESPONSE_VALUE and packet.request_id == request_id:
                    continue
                break
        except socket.timeout as exc:
            raise RconConnectionError("The server did not answer the login in time.") from exc
        except OSError as exc:
            raise RconConnectionError(f"Connection lost during login ({exc}).") from exc
        if packet.request_id == -1:
            raise RconAuthError("Wrong RCON password.")
        if packet.request_id != request_id:
            raise RconConnectionError("Unexpected reply to the login request.")

    def _collect_reply_locked(self, sock: socket.socket, request_id: int, sentinel_id: int, parts: list[str]) -> None:
        while True:
            packet = read_packet(sock)
            if packet.request_id == sentinel_id:
                return
            if packet.request_id == request_id:
                parts.append(packet.payload)
            elif packet.request_id == -1:
                raise RconAuthError("The server no longer accepts this session.")

    def _close_locked(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None
