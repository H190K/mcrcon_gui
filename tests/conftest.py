import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["MCRCON_GUI_NO_UPDATE_CHECK"] = "1"

from fake_server import FakeRconServer  # noqa: E402


@pytest.fixture
def server():
    with FakeRconServer(password="secret") as srv:
        yield srv


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    monkeypatch.setenv("MCRCON_GUI_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.chdir(tmp_path)
    return tmp_path / "config"


def pytest_sessionfinish(session, exitstatus):
    """Tear Qt down while Python is still fully alive.

    Left to interpreter shutdown, PySide on Python < 3.12 can free Qt objects in the wrong
    order and abort ("munmap_chunk(): invalid pointer") after every test has passed.
    """
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        return
    for widget in app.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    app.processEvents()
    if hasattr(app, "shutdown"):
        app.shutdown()
