"""Headless UI tests: drive the real widgets against the fake server."""

import time

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from fake_server import FakeRconServer
from mcrcon_gui.app import build_window, create_app
from mcrcon_gui.core import storage
from mcrcon_gui.core.models import AppSettings, ServerProfile
from mcrcon_gui.ui import theme
from mcrcon_gui.ui.session import Session


@pytest.fixture(scope="module")
def app():
    return create_app([])


def wait_until(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        QApplication.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return False


def make_settings(*servers, password="secret"):
    profiles = [ServerProfile(name=f"S{i}", host="127.0.0.1", port=s.port, password=password) for i, s in enumerate(servers)]
    settings = AppSettings(profiles=profiles, theme="light")
    settings.active_profile_id = profiles[0].id
    return settings


@pytest.fixture
def window(app, server):
    win = build_window(make_settings(server), mode="light")
    win.settings.confirm_dangerous = False
    win.show()
    yield win
    win.close()


def connect(window):
    window.active_page().toggle_connection()
    assert wait_until(lambda: window.active_session().online)
    assert wait_until(lambda: window.active_session().players is not None)


# -- session ---------------------------------------------------------------------------


def test_session_connect_run_and_poll(app, server):
    session = Session(ServerProfile(host="127.0.0.1", port=server.port, password="secret"))
    try:
        session.connect_server()
        assert wait_until(lambda: session.online)
        assert wait_until(lambda: session.players is not None and session.players.names == ["Notch", "Alex", "Steve"])
        assert wait_until(lambda: "warp" in session.known_commands)  # discovered through `help`
        session.run("time set day")
        assert wait_until(lambda: any(e.text == "Set the time to 1000" for e in session.log.entries))
        assert session.profile.history == ["time set day"]
    finally:
        session.dispose()


def test_stop_does_not_trigger_reconnect(app, server):
    session = Session(ServerProfile(host="127.0.0.1", port=server.port, password="secret", auto_reconnect=True))
    try:
        session.connect_server()
        assert wait_until(lambda: session.online)
        session.run("stop")
        assert wait_until(lambda: session.state == "offline")
        QApplication.processEvents()
        assert session.state == "offline"
    finally:
        session.dispose()


def test_auto_reconnect_after_drop(app):
    first = FakeRconServer("secret").start()
    port = first.port
    session = Session(ServerProfile(host="127.0.0.1", port=port, password="secret", auto_reconnect=True))
    try:
        session.connect_server()
        assert wait_until(lambda: session.online)
        session._expect_drop = False
        session._worker._client._sock.close()  # simulate the network dropping
        first.stop()
        second = FakeRconServer("secret", port=port).start()
        session.refresh_players()
        assert wait_until(lambda: session.state == "reconnecting", 3)
        assert wait_until(lambda: session.online, 8)
        second.stop()
    finally:
        session.dispose()


# -- window ----------------------------------------------------------------------------


def test_starts_offline(window):
    page = window.active_page()
    assert not window.active_session().online
    assert not page.send_button.isEnabled()
    assert page.connect_button.text() == "CONNECT"


def test_connect_send_and_players(window, server):
    connect(window)
    assert window.players.names == ["Notch", "Alex", "Steve"]
    page = window.active_page()
    page.input.setText("/time set night")
    page.input._submit()
    assert wait_until(lambda: "Set the time to 13000" in page.console.toPlainText())
    window.broadcast_input.setText("hello")
    window._broadcast()
    assert wait_until(lambda: "say hello" in server.commands)


def test_kick_from_players_panel_refreshes_list(window, server):
    connect(window)
    window.players.run_command.emit("kick Notch griefing")
    assert wait_until(lambda: "Notch" not in window.players.names, 4)


def test_wrong_password(app, server):
    win = build_window(make_settings(server, password="nope"), mode="light")
    try:
        win.active_page().toggle_connection()
        assert wait_until(lambda: "Wrong RCON password" in win.active_page().console.toPlainText())
        assert win.active_session().state == "offline"
    finally:
        win.close()


def test_two_servers_at_once_keep_separate_consoles(app):
    with FakeRconServer("secret") as a, FakeRconServer("secret", players=["Jeb_"]) as b:
        win = build_window(make_settings(a, b), mode="light")
        try:
            first, second = win.manager.ordered()
            first.connect_server()
            second.connect_server()
            assert wait_until(lambda: first.online and second.online)
            first.run("seed")
            second.run("difficulty")
            assert wait_until(lambda: "Seed:" in win.pages[first.profile.id].console.toPlainText())
            assert wait_until(lambda: "Normal" in win.pages[second.profile.id].console.toPlainText())
            assert "Normal" not in win.pages[first.profile.id].console.toPlainText()
            win._switch_index(1)
            assert win.active_session() is second
            assert wait_until(lambda: win.players.names == ["Jeb_"])
        finally:
            win.close()


def test_tab_completion_in_command_line(window, server):
    connect(window)
    line = window.active_page().input
    line.setFocus()
    line.setText("kill Al")
    QTest.keyClick(line, Qt.Key.Key_Tab)
    assert line.text() == "kill Alex "

    line.setText("gamemode ")
    QTest.keyClick(line, Qt.Key.Key_Tab)  # opens the popup and previews the first candidate
    assert window.active_page().popup.isVisible()
    assert line.text() == "gamemode adventure"
    QTest.keyClick(line, Qt.Key.Key_Tab)
    assert line.text() == "gamemode creative"
    QTest.keyClick(line, Qt.Key.Key_Backtab)
    assert line.text() == "gamemode adventure"
    QTest.keyClick(line, Qt.Key.Key_Return)  # accepts the candidate, does not send
    assert line.text() == "gamemode adventure "
    assert "gamemode adventure" not in server.commands
    QTest.keyClick(line, Qt.Key.Key_Escape)
    QTest.keyClick(line, Qt.Key.Key_Escape)
    assert line.text() == ""


def test_history_with_arrow_keys(window):
    connect(window)
    page = window.active_page()
    for cmd in ("seed", "list"):
        page.input.setText(cmd)
        page.input._submit()
    QTest.keyClick(page.input, Qt.Key.Key_Up)
    assert page.input.text() == "list"
    QTest.keyClick(page.input, Qt.Key.Key_Up)
    assert page.input.text() == "seed"
    QTest.keyClick(page.input, Qt.Key.Key_Down)
    assert page.input.text() == "list"


def test_theme_switch(window):
    window.themes.set_mode("dark")
    assert theme.current().name == "dark"
    assert theme.DARK.paper.lower() in QApplication.instance().styleSheet().lower()
    window.themes.set_mode("light")
    assert theme.current().name == "light"


def test_export_log(window, tmp_path, monkeypatch):
    connect(window)
    window.active_session().run("seed")
    assert wait_until(lambda: "Seed" in window.active_page().console.toPlainText())
    target = tmp_path / "out.log"
    monkeypatch.setattr("mcrcon_gui.ui.server_page.QFileDialog.getSaveFileName", lambda *a, **k: (str(target), ""))
    window.active_page().export_log()
    assert "> /seed" in target.read_text()


def test_settings_saved_on_close(app, server):
    win = build_window(make_settings(server), mode="light")
    win.show()
    win.active_page().toggle_connection()
    assert wait_until(lambda: win.active_session().online)
    win.active_session().run("seed")
    win.close()
    loaded = storage.load()
    assert loaded.profiles[0].history == ["seed"]
    assert loaded.profiles[0].password == "secret"
