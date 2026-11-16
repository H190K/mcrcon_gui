# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-11-17

A ground-up rewrite. The separate Tkinter and WebView apps are replaced by one native desktop app.

### Added
- Native desktop app built with Qt (PySide6), with a neo-brutalist design in light and dark themes (or following the system). A navigation rail leads to four pages: Console, Servers, Settings and About; the Windows title bar follows the theme.
- Built-in RCON client written in Python, so the bundled `mcrcon.exe` is no longer needed. Handles multi-packet replies.
- Multiple saved servers, with several connected at the same time, each with its own console and command history.
- Tab completion for about 60 vanilla commands, their arguments, item/effect/enchantment/game-rule names, and online players; plugin commands discovered from `help`.
- Usage hint bar showing the syntax of the command being typed.
- Players panel with a right-click menu (message, teleport, game mode, op/deop, kick, ban).
- Automatic reconnect with back-off; round-trip time shown for every reply.
- Console filter, timestamps toggle, copy and export to file.
- Confirmation before `stop`, `kick`, `ban`, `ban-ip` and `kill`.
- Keyboard shortcuts for connecting, switching servers, clearing, filtering, exporting and theme.
- Automatic updates for the installed app: checks mcrcon.app at every start and every 24 hours, downloads and verifies the new installer, and installs on click or on exit. Manual check in About.
- Settings page (theme, timestamps, confirmations, automatic updates, data folder) and About page (links and open-source credits).
- Windows installer (per-user, no admin rights needed) and portable zip.
- New icon and installer artwork.

### Changed
- Settings moved to the per-user config folder, with atomic writes and an automatic backup. Settings from the old versions are imported on first start.
- Saved passwords are encrypted with Windows DPAPI on Windows.

### Removed
- The Tkinter (`rcon_gui_formc.py`) and WebView (`webviewmcrcongui.py`) apps and the bundled `mcrcon.exe`.

[Unreleased]: https://github.com/H190K/mcrcon_gui/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/H190K/mcrcon_gui/releases/tag/v0.1.0
