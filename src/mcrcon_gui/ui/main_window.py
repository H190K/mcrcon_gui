"""The main window: a navigation rail and four pages (Console, Servers, Settings, About)."""

from __future__ import annotations

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMainWindow, QMessageBox, QStackedWidget, QWidget

from .. import APP_WEBSITE, __version__
from ..core.completion import CompletionEngine
from ..core.models import ACCENT_KEYS
from . import theme
from .about_page import AboutPage
from .console_page import ConsolePage
from .profile_dialog import ProfileDialog
from .server_page import ServerPage
from .servers_page import ServersPage
from .session import Session, SessionManager
from .settings_page import SettingsPage
from .theme import Theme, ThemeManager
from .updates import UpdateManager
from .widgets import DotBackground, NavRail, Toast
from .winutil import style_title_bar

DANGEROUS = {"stop", "ban", "ban-ip", "kick", "kill"}
CONSOLE, SERVERS, SETTINGS, ABOUT = range(4)


class MainWindow(QMainWindow):
    def __init__(self, manager: SessionManager, themes: ThemeManager, updates: UpdateManager | None = None) -> None:
        super().__init__()
        self.manager = manager
        self.settings = manager.settings
        self.themes = themes
        self.updates = updates or UpdateManager(manager.settings, manager.request_save, self_install=False)
        self.engine = CompletionEngine()
        self.pages: dict[str, ServerPage] = {}
        self._installing = False

        self.setWindowTitle("MCRCON GUI")
        self.setWindowIcon(QIcon(str(theme.ASSETS / "icon.png")))
        self.setMinimumSize(1200, 760)
        self.resize(max(self.settings.window.get("w", 1360), 1200), max(self.settings.window.get("h", 880), 760))

        self._build()
        for session in manager.ordered():
            self._add_page(session)
        manager.session_added.connect(self._on_session_added)
        manager.session_removed.connect(self._on_session_removed)
        manager.active_changed.connect(self._show_active)
        themes.changed.connect(self._on_theme)
        self.updates.state_changed.connect(self._on_update_state)
        self._shortcuts()
        self._show_active(self.settings.active_profile_id)
        self.rail.select(CONSOLE)

    # -- layout --------------------------------------------------------------------------

    def _build(self) -> None:
        root = DotBackground()
        root.setObjectName("root")
        self.setCentralWidget(root)
        row = QHBoxLayout(root)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        logo = QLabel()
        logo.setPixmap(QIcon(str(theme.ASSETS / "icon.png")).pixmap(56, 56))
        logo.setToolTip(f"MCRCON GUI {__version__}")
        self.rail = NavRail(logo)
        self.rail.add_page("Console", "terminal", tooltip="Console (Ctrl+K)")
        self.rail.add_page("Servers", "server", tooltip="Saved servers")
        self.rail.add_page("Settings", "settings", bottom=True, tooltip="Settings (Ctrl+,)")
        self.rail.add_page("About", "info", bottom=True, tooltip="About, credits (F1)")
        self.rail.footer.setText(f"v{__version__}")
        self.rail.selected.connect(self._show_page)
        row.addWidget(self.rail)

        self.stack = QStackedWidget()
        row.addWidget(self.stack, 1)

        self.console_page = ConsolePage(self.manager)
        cp = self.console_page
        cp.tabs.selected.connect(self.manager.set_active)
        cp.tabs.toggle_requested.connect(self._toggle_server)
        cp.tabs.add_requested.connect(self.add_server)
        cp.players.run_command.connect(lambda cmd: self.active_session().run(cmd))
        cp.players.insert_text.connect(self._insert_into_command)
        cp.players.confirm.connect(self._confirm_then)
        for button in cp.quick_buttons:
            button.clicked.connect(lambda _=False, b=button: self.submit(self.active_session(), b.property("command")))
        cp.stop_button.clicked.connect(lambda: self.submit(self.active_session(), "stop"))
        cp.broadcast_input.returnPressed.connect(self._broadcast)
        cp.broadcast_button.clicked.connect(self._broadcast)
        cp.update_button.clicked.connect(self._update_clicked)

        self.servers_page = ServersPage(self.manager)
        self.servers_page.add_requested.connect(self.add_server)
        self.servers_page.edit_requested.connect(self.edit_server)
        self.servers_page.remove_requested.connect(self.remove_server)
        self.servers_page.toggle_requested.connect(self._toggle_server_from_list)
        self.servers_page.open_requested.connect(self._open_console)

        self.settings_page = SettingsPage(self.settings, self.updates)
        self.settings_page.theme_changed.connect(self.set_theme)
        self.settings_page.timestamps_changed.connect(self._set_timestamps)
        self.settings_page.changed.connect(self.manager.request_save)
        self.settings_page.install_requested.connect(self.install_update)

        self.about_page = AboutPage()
        for page in (self.console_page, self.servers_page, self.settings_page, self.about_page):
            self.stack.addWidget(page)
        self.toast = Toast(root)

    # convenience aliases used by tests and the screenshot tool
    @property
    def players(self):
        return self.console_page.players

    @property
    def broadcast_input(self) -> QLineEdit:
        return self.console_page.broadcast_input

    def _shortcuts(self) -> None:
        def bind(seq: str, fn) -> None:
            QShortcut(QKeySequence(seq), self, activated=fn)

        bind("Ctrl+K", self._focus_command)
        bind("Ctrl+L", lambda: self.active_session().clear_log())
        bind("Ctrl+F", lambda: (self.rail.select(CONSOLE), self.active_page().filter.setFocus()))
        bind("Ctrl+E", lambda: self.active_page().export_log())
        bind("Ctrl+N", self.add_server)
        bind("Ctrl+,", lambda: self.rail.select(SETTINGS))
        bind("F1", lambda: self.rail.select(ABOUT))
        bind("Ctrl+Shift+T", self.cycle_theme)
        bind("Ctrl+Return", lambda: self.active_page().toggle_connection())
        bind("Ctrl+Tab", lambda: self._switch_relative(1))
        bind("Ctrl+Shift+Tab", lambda: self._switch_relative(-1))
        for n in range(1, 10):
            bind(f"Ctrl+{n}", lambda n=n: self._switch_index(n - 1))

    def _show_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        if index == CONSOLE:
            QTimer.singleShot(0, lambda: self.active_page().input.setFocus())
        elif index == SERVERS:
            self.servers_page.rebuild()

    def _focus_command(self) -> None:
        self.rail.select(CONSOLE)
        self.active_page().input.setFocus()

    # -- server pages --------------------------------------------------------------------

    def _add_page(self, session: Session) -> None:
        page = ServerPage(session, self.engine, self.settings, self.console_page.stack)
        page.toast.connect(self.show_toast)
        page.connect_requested.connect(self.connect_session)
        page.edit_requested.connect(self.edit_server)
        page.command_submitted.connect(self.submit)
        self.pages[session.profile.id] = page
        self.console_page.stack.addWidget(page)
        session.state_changed.connect(lambda state, s=session: self._on_session_state(s, state))
        session.players_changed.connect(lambda players, s=session: self._on_players(s, players))
        session.entry_added.connect(lambda _e: self.console_page.tabs.refresh())
        session.auth_failed.connect(lambda s=session: self.show_toast(f"{s.profile.name}: wrong password", "red"))

    def _on_session_added(self, session: Session) -> None:
        self._add_page(session)
        self.console_page.tabs.rebuild()
        self.servers_page.rebuild()

    def _on_session_removed(self, profile_id: str) -> None:
        page = self.pages.pop(profile_id, None)
        if page is not None:
            self.console_page.stack.removeWidget(page)
            page.deleteLater()
        self.console_page.tabs.rebuild()
        self.servers_page.rebuild()

    def _show_active(self, profile_id: str | None) -> None:
        page = self.pages.get(profile_id or "")
        if page is None:
            return
        self.console_page.stack.setCurrentWidget(page)
        self.console_page.tabs.refresh()
        self._sync_active()
        if self.stack.currentIndex() == CONSOLE:
            page.input.setFocus()

    def _sync_active(self) -> None:
        session = self.active_session()
        online = session.online
        cp = self.console_page
        cp.players.set_players(session.players, online)
        for widget in (*cp.quick_buttons, cp.stop_button, cp.broadcast_input, cp.broadcast_button):
            widget.setEnabled(online)
        count = sum(1 for s in self.manager.sessions.values() if s.online)
        total = len(self.manager.sessions)
        cp.header.subtitle.setText(f"{count} of {total} server{'s' if total != 1 else ''} connected")
        self.setWindowTitle(f"{session.profile.name} · MCRCON GUI")

    def _on_session_state(self, session: Session, state: str) -> None:
        self.console_page.tabs.refresh()
        self._sync_active()
        if session is not self.active_session() and state == "offline" and session.last_error:
            self.show_toast(f"{session.profile.name}: disconnected", "red")

    def _on_players(self, session: Session, players) -> None:
        self.console_page.tabs.refresh()
        if session is self.active_session():
            self.console_page.players.set_players(players, session.online)

    def active_session(self) -> Session:
        return self.manager.active()

    def active_page(self) -> ServerPage:
        return self.pages[self.active_session().profile.id]

    def _switch_index(self, index: int) -> None:
        sessions = self.manager.ordered()
        if 0 <= index < len(sessions):
            self.manager.set_active(sessions[index].profile.id)
            self.rail.select(CONSOLE)

    def _switch_relative(self, step: int) -> None:
        ids = [s.profile.id for s in self.manager.ordered()]
        current = ids.index(self.settings.active_profile_id) if self.settings.active_profile_id in ids else 0
        self._switch_index((current + step) % len(ids))

    # -- actions -------------------------------------------------------------------------

    def connect_session(self, session: Session) -> None:
        password = None
        if not session.profile.password:
            text, ok = QInputDialog.getText(self, f"Connect to {session.profile.name}", "RCON password:", QLineEdit.EchoMode.Password)
            if not ok:
                return
            password = text
            if session.profile.remember_password:
                session.profile.password = text
                self.manager.request_save()
        session.connect_server(password)

    def _toggle_server(self, profile_id: str) -> None:
        self.manager.set_active(profile_id)
        self.pages[profile_id].toggle_connection()

    def _toggle_server_from_list(self, profile_id: str) -> None:
        session = self.manager.sessions.get(profile_id)
        if session is None:
            return
        if session.state in ("online", "reconnecting"):
            session.disconnect_server()
        else:
            self.connect_session(session)

    def _open_console(self, profile_id: str) -> None:
        self.manager.set_active(profile_id)
        self.rail.select(CONSOLE)

    def submit(self, session: Session, command: str) -> None:
        command = command.strip().removeprefix("/")
        if not command:
            return
        root = command.split()[0].lower()
        if root in DANGEROUS and self.settings.confirm_dangerous:
            self._confirm_then(f"Run /{root}?", f"/{command}\n\non {session.profile.name}", lambda: session.run(command))
            return
        session.run(command)
        self.manager.request_save()  # history changed

    def _confirm_then(self, title: str, question: str, callback) -> None:
        answer = QMessageBox.question(
            self, title, question, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )
        if answer == QMessageBox.StandardButton.Yes:
            callback()

    def _broadcast(self) -> None:
        message = self.broadcast_input.text().strip()
        if message:
            self.active_session().run(f"say {message}")
            self.broadcast_input.clear()

    def _insert_into_command(self, text: str) -> None:
        line = self.active_page().input
        current = line.text()
        line.setText(f"{current}{'' if not current or current.endswith(' ') else ' '}{text} ")
        line.setFocus()

    def add_server(self) -> None:
        dialog = ProfileDialog(None, self)
        used = {p.color for p in self.settings.profiles}
        free = next((c for c in ACCENT_KEYS if c not in used), "yellow")
        dialog.color.setCurrentIndex(dialog.color.findData(free))
        if dialog.exec():
            session = self.manager.add_profile(dialog.result_profile())
            self.manager.set_active(session.profile.id)
            self.show_toast(f"Added {session.profile.name}", "green")

    def edit_server(self, profile_id: str | None) -> None:
        session = self.manager.sessions.get(profile_id or "")
        if session is None:
            return
        dialog = ProfileDialog(session.profile, self)
        if not dialog.exec():
            return
        # Update in place: the session, page and history all share this object.
        for key, value in vars(dialog.result_profile()).items():
            setattr(session.profile, key, value)
        self.manager.update_profile(session.profile)
        self.pages[session.profile.id].update_profile()
        self.console_page.tabs.rebuild()
        self.servers_page.rebuild()
        self.show_toast("Server saved", "green")

    def remove_server(self, profile_id: str | None) -> None:
        session = self.manager.sessions.get(profile_id or "")
        if session is None:
            return
        if len(self.manager.sessions) == 1:
            self.show_toast("Keep at least one server", "orange")
            return
        answer = QMessageBox.question(self, "Remove server", f"Remove {session.profile.name} from the list?")
        if answer == QMessageBox.StandardButton.Yes:
            self.manager.remove_profile(session.profile.id)

    def set_theme(self, mode: str) -> None:
        self.settings.theme = mode
        self.themes.set_mode(mode)
        self.manager.request_save()

    def cycle_theme(self) -> None:
        modes = ThemeManager.MODES
        self.set_theme(modes[(modes.index(self.themes.mode) + 1) % len(modes)])

    def _set_timestamps(self, on: bool) -> None:
        for page in self.pages.values():
            page.set_timestamps(on)
        self.manager.request_save()

    def show_toast(self, text: str, color: str = "yellow") -> None:
        self.toast.show_message(text, color)

    # -- updates -------------------------------------------------------------------------

    def _on_update_state(self, state: str, message: str) -> None:
        button = self.console_page.update_button
        settings_nav = self.rail.buttons[SETTINGS]
        if state == "ready":
            button.setText(f"Install {self.updates.info.version}")
            button.set_color("green")
            button.setToolTip(f"{message} It also installs automatically when you close the app.")
            button.show()
            settings_nav.set_badge("1")
            self.show_toast(f"Update {self.updates.info.version} downloaded", "green")
        elif state == "available":
            button.setText(f"Get {self.updates.info.version}")
            button.set_color("cyan")
            button.setToolTip(message)
            button.show()
            settings_nav.set_badge("1")
        elif state == "up_to_date":
            button.hide()
            settings_nav.set_badge("")

    def _update_clicked(self) -> None:
        if self.updates.state == "ready":
            self.install_update()
        else:
            QDesktopServices.openUrl(QUrl(f"{APP_WEBSITE}/download/"))

    def install_update(self) -> None:
        online = [s.profile.name for s in self.manager.sessions.values() if s.online]
        if online:
            answer = QMessageBox.question(
                self,
                "Install update",
                f"Installing closes the app and disconnects {', '.join(online)}.\n"
                "MCRCON GUI reopens when it's done. Continue?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        if self.updates.install_now():
            self._installing = True
            self.close()
        else:
            self.show_toast(self.updates.message or "Couldn't start the installer", "red")

    # -- theme & window ------------------------------------------------------------------

    def _on_theme(self, t: Theme) -> None:
        self.settings_page.theme.set_value(self.themes.mode)
        for page in self.pages.values():
            page.apply_theme(t)
            page.hint.show_completion(page.hint._completion)
        self._style_frame(t)

    def _style_frame(self, t: Theme) -> None:
        # Native title bar and 1px border in the rail's colour, so the frame looks like part of the app.
        style_title_bar(int(self.winId()), dark=t.dark, caption=t.surface, text=t.text, border=t.ink)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._style_frame(theme.current())
        QTimer.singleShot(0, lambda: self.active_page().input.setFocus())

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self.settings.window = {"w": self.width(), "h": self.height()}
        if not self._installing:
            self.updates.install_on_exit()
        self.manager.shutdown()
        super().closeEvent(event)
