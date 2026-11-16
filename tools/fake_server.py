"""A small fake Minecraft RCON server for tests, screenshots and trying the app without a real server.

    python tools/fake_server.py --port 25575 --password test --players Notch,Alex,Steve

Then add a server in the app for ``localhost:25575`` with password ``test``.
"""

from __future__ import annotations

import argparse
import socket
import struct
import threading

DEFAULT_PLAYERS = ("Notch", "Alex", "Steve")

STATIC_REPLIES = {
    "time set day": "Set the time to 1000",
    "time set night": "Set the time to 13000",
    "weather clear": "Set the weather to clear",
    "weather rain": "Set the weather to rain",
    "weather thunder": "Set the weather to rain & thunder",
    "save-all": "Saving the game (this may take a moment!)§aSaved the game",
    "seed": "Seed: [§a-4172144997902289642§r]",
    "whitelist list": "There are 2 whitelisted player(s): Alex, Steve",
    "difficulty": "The difficulty is Normal",
    "long": "x" * 10_000,
}

# Vanilla "help" output, plus a few plugin-style commands the catalog does not know.
HELP = [
    "/advancement (grant|revoke)",
    "/ban <targets> [<reason>]",
    "/gamemode <gamemode> [<target>]",
    "/give <targets> <item> [<count>]",
    "/kick <targets> [<reason>]",
    "/list [uuids]",
    "/say <message>",
    "/stop",
    "/time (add|query|set)",
    "/spawn",
    "/warp <name>",
]


def _read(conn: socket.socket) -> tuple[int, int, str] | None:
    def exact(size: int) -> bytes | None:
        buf = b""
        while len(buf) < size:
            try:
                chunk = conn.recv(size - len(buf))
            except OSError:  # the client hung up abruptly; treat it like a normal close
                return None
            if not chunk:
                return None
            buf += chunk
        return buf

    head = exact(4)
    if head is None:
        return None
    data = exact(struct.unpack("<i", head)[0])
    if data is None:
        return None
    request_id, packet_type = struct.unpack("<ii", data[:8])
    return request_id, packet_type, data[8:-2].decode("utf-8")


def _send(conn: socket.socket, request_id: int, packet_type: int, payload: str) -> None:
    body = struct.pack("<ii", request_id, packet_type) + payload.encode("utf-8") + b"\x00\x00"
    conn.sendall(struct.pack("<i", len(body)) + body)


class FakeRconServer:
    def __init__(self, password: str = "test", host: str = "127.0.0.1", port: int = 0, players=DEFAULT_PLAYERS, max_players: int = 20) -> None:
        self.password = password
        self.players = list(players)
        self.max_players = max_players
        self.commands: list[str] = []
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((host, port))
        self._sock.listen()
        self.host, self.port = self._sock.getsockname()
        self._thread = threading.Thread(target=self._serve, daemon=True)

    # -- lifecycle -----------------------------------------------------------------------

    def start(self) -> "FakeRconServer":
        self._thread.start()
        return self

    def stop(self) -> None:
        # Shut down first: on Linux, close() alone doesn't wake a thread blocked in accept(),
        # and the port stays bound.
        try:
            self._sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self._sock.close()
        if self._thread.is_alive():
            self._thread.join(timeout=2)

    def __enter__(self) -> "FakeRconServer":
        return self.start()

    def __exit__(self, *exc_info: object) -> None:
        self.stop()

    # -- command handling --------------------------------------------------------------

    def _find(self, name: str) -> str | None:
        return next((p for p in self.players if p.lower() == name.lower()), None)

    def reply_for(self, command: str) -> str:
        if command in STATIC_REPLIES:
            return STATIC_REPLIES[command]
        words = command.split()
        root, args = words[0].lower(), words[1:]
        if root == "list":
            names = [f"{p} (069a79f4-44e9-4726-a5be-fca90e38aaf{i})" for i, p in enumerate(self.players)] if args[:1] == ["uuids"] else self.players
            return f"There are {len(self.players)} of a max of {self.max_players} players online: {', '.join(names)}"
        if root == "help":
            return "\n".join(HELP)
        if root == "say":
            return ""
        if root in ("kick", "ban") and args:
            player = self._find(args[0])
            if player is None:
                return "§cNo player was found"
            self.players.remove(player)
            reason = " ".join(args[1:]) or ("Kicked by an operator" if root == "kick" else "Banned by an operator")
            return f"{'Kicked' if root == 'kick' else 'Banned'} {player}: {reason}"
        if root in ("op", "deop") and args:
            player = self._find(args[0]) or args[0]
            return f"Made {player} a server operator" if root == "op" else f"Made {player} no longer a server operator"
        if root == "gamemode" and args:
            mode = args[0].title()
            if len(args) > 1:
                return f"Set {args[1]}'s game mode to {mode} Mode"
            return f"Set own game mode to {mode} Mode"
        if root == "give" and len(args) >= 2:
            count = args[2] if len(args) > 2 else "1"
            target = f"{len(self.players)} players" if args[0] == "@a" else args[0]
            return f"Gave {count} [{args[1].removeprefix('minecraft:').replace('_', ' ').title()}] to {target}"
        if root in ("tp", "teleport") and args:
            return f"Teleported {args[0]} to {' '.join(args[1:]) or 'you'}"
        if root == "msg" and len(args) >= 2:
            return f"You whisper to {args[0]}: {' '.join(args[1:])}"
        return f"§cUnknown or incomplete command, see below for error§r\n{command}§c§o<--[HERE]"

    def _serve(self) -> None:
        while True:
            try:
                conn, _ = self._sock.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn: socket.socket) -> None:
        try:
            self._session(conn)
        except OSError:
            pass  # client went away mid-reply

    def _session(self, conn: socket.socket) -> None:
        authed = False
        stopping = False
        with conn:
            while (packet := _read(conn)) is not None:
                request_id, packet_type, payload = packet
                if stopping:
                    # Like a real server, answer what is already in flight, then hang up.
                    _send(conn, request_id, 0, f"Unknown request {packet_type:x}")
                    return
                if packet_type == 3:
                    authed = payload == self.password
                    _send(conn, request_id if authed else -1, 2, "")
                elif not authed:
                    _send(conn, -1, 2, "")
                elif packet_type == 2:
                    self.commands.append(payload)
                    if payload == "stop":
                        _send(conn, request_id, 0, "Stopping the server")
                        stopping = True
                        continue
                    text = self.reply_for(payload)
                    # Like Minecraft, split replies into 4096-byte fragments.
                    for chunk in [text[i : i + 4096] for i in range(0, len(text), 4096)] or [""]:
                        _send(conn, request_id, 0, chunk)
                else:
                    _send(conn, request_id, 0, f"Unknown request {packet_type:x}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=25575)
    parser.add_argument("--password", default="test")
    parser.add_argument("--players", default=",".join(DEFAULT_PLAYERS), help="comma-separated online players")
    args = parser.parse_args()
    players = [p for p in args.players.split(",") if p]
    server = FakeRconServer(args.password, args.host, args.port, players)
    print(f"Fake RCON server on {server.host}:{server.port} (password {args.password!r}, players: {', '.join(players) or 'none'}). Ctrl+C to stop.")
    try:
        server._serve()
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()
