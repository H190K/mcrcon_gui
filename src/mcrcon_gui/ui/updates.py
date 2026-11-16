"""Background update checks for the installed Windows app.

On every launch, every 24 hours while running, and on demand, the app fetches the manifest
from mcrcon.app. If a newer version exists and this is an installed build, the installer
is downloaded and verified in the background. It runs when the user clicks *Install update*, or silently when the
app is closed. Portable and source builds only get a notice with a download link.
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QTimer, Signal

from .. import __version__
from ..core import updater
from ..core.models import AppSettings
from ..core.updater import UpdateError, UpdateInfo

CHECK_EVERY = timedelta(hours=24)
FIRST_CHECK_DELAY_MS = 8_000  # let the window settle before touching the network
TICK_MS = 60 * 60 * 1000  # re-evaluate hourly, so a laptop that slept still checks on time


class UpdateManager(QObject):
    # idle | checking | up_to_date | available | downloading | ready | error
    state_changed = Signal(str, str)
    progress = Signal(int, int)
    _report = Signal(str, str)  # from worker threads; queued so state only changes on the GUI thread
    _checked = Signal()

    def __init__(
        self,
        settings: AppSettings,
        save: Callable[[], None],
        *,
        checker: Callable[[], UpdateInfo | None] = updater.check_for_update,
        downloader: Callable[..., Path] = updater.download_installer,
        self_install: bool | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self._save = save
        self._checker = checker
        self._downloader = downloader
        self.self_install = updater.can_self_install() if self_install is None else self_install
        self.state = "idle"
        self.message = ""
        self.info: UpdateInfo | None = None
        self.installer: Path | None = None
        self._busy = False
        self._cancel = threading.Event()
        self._timer = QTimer(self, interval=TICK_MS, timeout=self.check_if_due)
        self._report.connect(self._apply)
        self._checked.connect(self._record_check)

    # -- scheduling ----------------------------------------------------------------------

    def start(self) -> None:
        """Check on every launch, then again whenever the app has been open 24 h since the last check."""
        self._timer.start()
        QTimer.singleShot(FIRST_CHECK_DELAY_MS, self.check_on_launch)

    def check_on_launch(self) -> None:
        if self.settings.auto_update:
            self.check(manual=False)

    def due(self) -> bool:
        try:
            last = datetime.fromisoformat(self.settings.last_update_check)
        except ValueError:
            return True
        return datetime.now() - last >= CHECK_EVERY

    def check_if_due(self) -> None:
        if self.settings.auto_update and self.due() and self.state not in ("ready", "downloading"):
            self.check(manual=False)

    # -- actions -------------------------------------------------------------------------

    def check(self, manual: bool = True) -> None:
        if self._busy:
            return
        self._busy = True
        self._apply("checking", "Checking for updates…")
        threading.Thread(target=self._check_worker, args=(manual,), daemon=True).start()

    def install_now(self) -> bool:
        """Start the installer (silent, relaunches the app). The caller must quit right after."""
        if self.installer is None:
            return False
        try:
            updater.launch_installer(self.installer, silent=True, relaunch=True)
        except UpdateError as exc:
            self._apply("error", str(exc))
            return False
        return True

    def install_on_exit(self) -> None:
        """Called when the app closes: apply a downloaded update without relaunching."""
        self._cancel.set()
        if self.state == "ready" and self.installer is not None and self.settings.auto_update:
            try:
                updater.launch_installer(self.installer, silent=True, relaunch=False)
            except UpdateError:
                pass

    # -- workers (background threads; signals are queued to the GUI thread) ----------------

    def _check_worker(self, manual: bool) -> None:
        try:
            info = self._checker()
        except UpdateError as exc:
            self._busy = False
            self._finish_check()
            self._set("error", f"Couldn't check for updates. {exc}" if manual else "")
            return
        self._finish_check()
        if info is None:
            self._busy = False
            self._set("up_to_date", f"You're on the latest version ({__version__}).")
            return
        self.info = info
        if not self.self_install:
            self._busy = False
            self._set("available", f"Version {info.version} is available.")
            return
        self._download_worker(info)

    def _download_worker(self, info: UpdateInfo) -> None:
        self._set("downloading", f"Downloading version {info.version}…")
        try:
            path = self._downloader(info, on_progress=self.progress.emit, cancel=self._cancel)
        except UpdateError as exc:
            self._busy = False
            self._set("error", f"Update download failed. {exc}")
            return
        self.installer = path
        self._busy = False
        self._set("ready", f"Version {info.version} is ready to install.")

    def _finish_check(self) -> None:
        self._checked.emit()

    def _record_check(self) -> None:
        self.settings.last_update_check = datetime.now().isoformat(timespec="seconds")
        self._save()

    def _set(self, state: str, message: str) -> None:
        """Report a state from a worker thread."""
        self._report.emit(state, message)

    def _apply(self, state: str, message: str) -> None:
        self.state = state
        self.message = message
        self.state_changed.emit(state, message)
