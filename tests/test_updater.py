"""Updater: manifest parsing, download + verification over a local HTTP server, and the scheduling logic."""

import http.server
import json
import threading
import time
from datetime import datetime, timedelta
from functools import partial

import pytest
from PySide6.QtWidgets import QApplication

from mcrcon_gui.core import updater
from mcrcon_gui.core.models import AppSettings
from mcrcon_gui.core.updater import UpdateError, UpdateInfo

PAYLOAD = b"MZ fake installer " * 5000


@pytest.fixture
def http_root(tmp_path):
    """Serve tmp_path over http://127.0.0.1 (loopback HTTP is the only non-HTTPS URL the updater accepts)."""
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(tmp_path))
    handler.log_message = lambda *a: None
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield tmp_path, f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def write_release(root, version="9.9.9", payload=PAYLOAD, sha=None):
    (root / "setup.exe").write_bytes(payload)
    manifest = {
        "version": version,
        "url": "setup.exe",
        "sha256": sha or updater.sha256_file(root / "setup.exe"),
        "size": len(payload),
        "notes": ["Faster", "Fixes"],
    }
    (root / "latest.json").write_text(json.dumps(manifest))


# -- versions & manifest ---------------------------------------------------------------


@pytest.mark.parametrize(
    "remote, local, newer",
    [("0.2.0", "0.1.0", True), ("0.1.0", "0.1.0", False), ("1.0", "1.0.0", False), ("v0.10.0", "0.9.9", True), ("0.1.0-beta", "0.1.1", False)],
)
def test_is_newer(remote, local, newer):
    assert updater.is_newer(remote, local) is newer


def test_parse_manifest_resolves_relative_url():
    info = updater.parse_manifest({"version": "1.2.3", "url": "setup.exe", "sha256": "a" * 64, "size": 5}, "https://mcrcon.app/update/latest.json")
    assert info.url == "https://mcrcon.app/update/setup.exe"


@pytest.mark.parametrize(
    "manifest",
    [
        {"version": "1.0", "url": "http://evil.example/setup.exe", "sha256": "a" * 64},  # not https
        {"version": "1.0", "url": "setup.exe", "sha256": "xyz"},
        {"version": "nope", "url": "setup.exe", "sha256": "a" * 64},
        {"url": "setup.exe", "sha256": "a" * 64},
    ],
)
def test_parse_manifest_rejects_bad_input(manifest):
    with pytest.raises(UpdateError):
        updater.parse_manifest(manifest, "https://mcrcon.app/update/latest.json")


# -- network (local server) ------------------------------------------------------------


def test_check_and_download(http_root, tmp_path_factory):
    root, base = http_root
    write_release(root)
    info = updater.check_for_update("0.1.0", manifest_urls=[f"{base}/latest.json"])
    assert info is not None and info.version == "9.9.9" and info.notes == ["Faster", "Fixes"]
    assert updater.check_for_update("9.9.9", manifest_urls=[f"{base}/latest.json"]) is None

    seen = []
    path = updater.download_installer(info, tmp_path_factory.mktemp("dl"), on_progress=lambda d, t: seen.append(d))
    assert path.read_bytes() == PAYLOAD
    assert seen and seen[-1] == len(PAYLOAD)


def test_download_rejects_tampered_installer(http_root, tmp_path_factory):
    root, base = http_root
    write_release(root, sha="0" * 64)
    info = updater.check_for_update("0.1.0", manifest_urls=[f"{base}/latest.json"])
    dest = tmp_path_factory.mktemp("dl")
    with pytest.raises(UpdateError, match="SHA-256"):
        updater.download_installer(info, dest)
    assert not list(dest.iterdir())  # nothing half-downloaded left behind


def test_unreachable_server_raises():
    with pytest.raises(UpdateError):
        updater.check_for_update("0.1.0", timeout=2, manifest_urls=["http://127.0.0.1:9/latest.json"])


def test_frozen_detection_is_false_in_tests():
    assert updater.can_self_install() is False


# -- UpdateManager ---------------------------------------------------------------------


@pytest.fixture(scope="module")
def app():
    from mcrcon_gui.app import create_app

    return create_app([])


def wait_for(predicate, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        QApplication.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return False


INFO = UpdateInfo("9.9.9", "https://mcrcon.app/x.exe", "a" * 64, 10)


def make_manager(tmp_path, *, checker, self_install=True, settings=None):
    from mcrcon_gui.ui.updates import UpdateManager

    saved = []
    downloader = lambda info, on_progress=None, cancel=None: tmp_path / "setup.exe"  # noqa: E731
    manager = UpdateManager(settings or AppSettings(), lambda: saved.append(1), checker=checker, downloader=downloader, self_install=self_install)
    return manager, saved


def test_manager_downloads_when_installed(app, tmp_path):
    manager, saved = make_manager(tmp_path, checker=lambda: INFO)
    states = []
    manager.state_changed.connect(lambda s, m: states.append(s))
    manager.check(manual=False)
    assert wait_for(lambda: manager.state == "ready")
    assert states == ["checking", "downloading", "ready"]
    assert manager.installer == tmp_path / "setup.exe"
    assert saved and manager.settings.last_update_check


def test_manager_only_notifies_for_portable_builds(app, tmp_path):
    manager, _ = make_manager(tmp_path, checker=lambda: INFO, self_install=False)
    manager.check()
    assert wait_for(lambda: manager.state == "available")
    assert manager.installer is None


def test_manager_up_to_date_and_errors(app, tmp_path):
    manager, _ = make_manager(tmp_path, checker=lambda: None)
    manager.check()
    assert wait_for(lambda: manager.state == "up_to_date")

    def boom():
        raise UpdateError("offline")

    manager, _ = make_manager(tmp_path, checker=boom)
    manager.check(manual=True)
    assert wait_for(lambda: manager.state == "error")
    assert "offline" in manager.message


def test_checks_on_every_launch_and_every_24_hours(app, tmp_path):
    calls = []
    settings = AppSettings(last_update_check=datetime.now().isoformat(timespec="seconds"))
    manager, _ = make_manager(tmp_path, checker=lambda: calls.append(1), settings=settings)

    manager.check_on_launch()  # a launch always checks, even right after a previous check
    assert wait_for(lambda: manager.state == "up_to_date")
    assert len(calls) == 1

    manager.check_if_due()  # the hourly tick: last check was just now, so nothing happens
    QApplication.processEvents()
    assert len(calls) == 1

    settings.last_update_check = (datetime.now() - timedelta(hours=25)).isoformat(timespec="seconds")
    manager.check_if_due()  # open for more than 24 h: check again
    assert wait_for(lambda: len(calls) == 2)


def test_auto_update_off_disables_scheduled_checks(app, tmp_path):
    calls = []
    manager, _ = make_manager(tmp_path, checker=lambda: calls.append(1), settings=AppSettings(auto_update=False))
    manager.check_on_launch()
    manager.check_if_due()
    QApplication.processEvents()
    assert calls == []
