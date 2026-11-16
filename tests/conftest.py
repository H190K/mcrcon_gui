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
