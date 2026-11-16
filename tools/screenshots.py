"""Regenerate the README screenshots by driving the real window against two fake servers.

    python tools/screenshots.py

Writes docs/screenshots/{light,dark,completion,multi-server,servers,settings,about}.png.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
os.environ["MCRCON_GUI_CONFIG_DIR"] = tempfile.mkdtemp()
os.environ["MCRCON_GUI_NO_UPDATE_CHECK"] = "1"
if sys.platform == "win32":
    # FreeType renders greyscale text; ClearType's coloured fringes look odd in scaled screenshots.
    os.environ.setdefault("QT_QPA_PLATFORM", "windows:fontengine=freetype")

from PySide6.QtWidgets import QApplication  # noqa: E402

from fake_server import FakeRconServer  # noqa: E402
from mcrcon_gui.app import build_window, create_app  # noqa: E402
from mcrcon_gui.core.models import AppSettings, ServerProfile  # noqa: E402

OUT = ROOT / "docs" / "screenshots"
SIZE = (1360, 860)


def pump(seconds: float = 0.3) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        QApplication.processEvents()
        time.sleep(0.01)


def wait_for(predicate, timeout: float = 5.0) -> None:
    end = time.monotonic() + timeout
    while not predicate() and time.monotonic() < end:
        pump(0.05)


def shoot(window, name: str) -> None:
    pump(0.4)
    path = OUT / name
    window.grab().save(str(path))
    print(f"saved {path.relative_to(ROOT)}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in ("offline.png", "connected.png"):
        (OUT / old).unlink(missing_ok=True)
    app = create_app(sys.argv)
    survival = FakeRconServer("hunter2", port=25575, players=["Notch", "Alex", "Steve", "Herobrine_"]).start()
    creative = FakeRconServer("hunter2", port=25576, players=["Jeb_", "Dinnerbone"]).start()
    settings = AppSettings(
        theme="light",
        profiles=[
            ServerProfile(name="Survival", host="localhost", port=survival.port, password="hunter2", color="yellow"),
            ServerProfile(name="Creative", host="localhost", port=creative.port, password="hunter2", color="pink"),
            ServerProfile(name="Lobby", host="hub.example.net", port=25575, color="cyan", auto_reconnect=False),
        ],
    )
    settings.active_profile_id = settings.profiles[0].id
    window = build_window(settings, mode="light")
    # The real path is a temp folder containing the local user name; show the usual location instead.
    window.settings_page.path_label.setText(r"C:\Users\you\AppData\Roaming\mcrcon-gui\config.json")
    window.resize(*SIZE)
    window.show()

    sessions = window.manager.ordered()
    survival_session, creative_session = sessions[0], sessions[1]
    for s in (survival_session, creative_session):
        s.connect_server()
    wait_for(lambda: all(s.online and s.players for s in (survival_session, creative_session)))

    for cmd in ("time set day", "weather clear", "give @a diamond_sword 1", "gamemode creative Alex", "save-all", "seed", "tp @s ~ ~10 ~"):
        survival_session.run(cmd)
        pump(0.12)
    window.broadcast_input.setText("Server restarts in 10 minutes!")
    window._broadcast()
    for cmd in ("difficulty", "give Jeb_ beacon 4", "time set night"):
        creative_session.run(cmd)
        pump(0.12)
    pump(0.5)

    page = window.active_page()
    page.input.setText("give Notch diamond_pickaxe ")
    page.input.setFocus()
    page.input.refresh()
    page.popup.hide()
    shoot(window, "light.png")

    window.themes.set_mode("dark")
    shoot(window, "dark.png")

    page.input.setText("kill ")
    page.input.setCursorPosition(len(page.input.text()))
    page.input._tab(backwards=False)
    shoot(window, "completion.png")
    page.popup.hide()

    window.themes.set_mode("light")
    window.manager.set_active(creative_session.profile.id)
    window.active_page().input.setText("")
    window.active_page().hint.show_completion(None)
    shoot(window, "multi-server.png")

    window.rail.select(1)
    shoot(window, "servers.png")
    window.rail.select(2)
    shoot(window, "settings.png")
    window.themes.set_mode("dark")
    window.rail.select(3)
    shoot(window, "about.png")
    window.themes.set_mode("light")
    window.rail.select(0)

    window.close()
    survival.stop()
    creative.stop()
    app.quit()


if __name__ == "__main__":
    main()
