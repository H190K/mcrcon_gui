import socket

import pytest

from mcrcon_gui.core.rcon import MAX_COMMAND_BYTES, Packet, RconAuthError, RconClient, RconConnectionError


def test_packet_encoding_matches_protocol():
    data = Packet(7, 2, "list").encode()
    assert data == b"\x0e\x00\x00\x00" + b"\x07\x00\x00\x00" + b"\x02\x00\x00\x00" + b"list\x00\x00"


def test_command_round_trip(server):
    with RconClient(server.host, server.port, "secret") as rcon:
        assert rcon.command("list").startswith("There are 3 of a max of 20 players online")
        assert rcon.command("/time set day") == "Set the time to 1000"
    assert server.commands == ["list", "time set day"]


def test_multi_packet_reply_is_reassembled(server):
    with RconClient(server.host, server.port, "secret") as rcon:
        assert rcon.command("long") == "x" * 10_000
        # The connection is still in sync afterwards.
        assert rcon.command("seed").startswith("Seed:")


def test_empty_reply(server):
    with RconClient(server.host, server.port, "secret") as rcon:
        assert rcon.command("say hello") == ""


def test_unicode_round_trip(server):
    with RconClient(server.host, server.port, "secret") as rcon:
        rcon.command("say héllo ✓")
    assert server.commands[-1] == "say héllo ✓"


def test_wrong_password(server):
    client = RconClient(server.host, server.port, "nope")
    with pytest.raises(RconAuthError):
        client.connect()
    assert not client.connected


def test_unreachable_server():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    with pytest.raises(RconConnectionError):
        RconClient("127.0.0.1", port, "x", timeout=1).connect()


def test_command_requires_connection():
    with pytest.raises(RconConnectionError):
        RconClient("127.0.0.1", 1, "x").command("list")


def test_rejects_empty_and_oversized_commands(server):
    with RconClient(server.host, server.port, "secret") as rcon:
        with pytest.raises(ValueError):
            rcon.command("   ")
        with pytest.raises(ValueError):
            rcon.command("say " + "a" * MAX_COMMAND_BYTES)


def test_server_closing_connection_is_reported(server):
    rcon = RconClient(server.host, server.port, "secret", timeout=2)
    rcon.connect()
    rcon.command("stop")  # the fake server hangs up after replying
    with pytest.raises(RconConnectionError):
        rcon.command("list")
    assert not rcon.connected
