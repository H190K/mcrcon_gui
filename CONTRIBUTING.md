# Contributing to MCRCON GUI

Thanks for helping out. Bug reports, ideas, docs fixes and code are all welcome.

## Before you start

- **Bugs and ideas:** open an [issue](https://github.com/H190K/mcrcon_gui/issues/new/choose) first, so we can agree on the approach before you write code.
- **Small fixes** (typos, an obvious bug, a missing command in the completion catalog) can go straight to a pull request.
- **Security problems:** please email instead, see [SECURITY.md](SECURITY.md).

## Development setup

```bash
git clone https://github.com/H190K/mcrcon_gui.git
cd mcrcon_gui
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Run the app:

```bash
mcrcon-gui          # or: python -m mcrcon_gui
```

You don't need a Minecraft server. Start the fake one in another terminal and connect to `localhost:25575` with password `test`:

```bash
python tools/fake_server.py --port 25575 --password test --players Notch,Alex,Steve
```

## Tests

```bash
python -m pytest
```

The suite covers the RCON protocol, storage and migrations, the completion engine, and the UI itself (driven headlessly against the fake server). CI runs it on Windows, macOS and Linux. Please add a test with any fix or feature.

## How the code is organised

```
src/mcrcon_gui/
├── app.py              entry point: creates the QApplication, theme and main window
├── core/               plain Python, no Qt (a test enforces this)
│   ├── rcon.py         RCON protocol client
│   ├── models.py       ServerProfile, AppSettings, ConsoleLog, ...
│   ├── storage.py      settings file: load/save, atomic writes, migrations
│   ├── secrets.py      password protection (DPAPI on Windows)
│   ├── players.py      parses `list` and `help` replies
│   ├── completion.py   the completion engine
│   ├── updater.py      update check, download, SHA-256 verification, installer launch
│   └── commands/       command grammar, catalog and value lists
└── ui/                 Qt widgets
    ├── main_window.py  navigation rail + the four pages, wiring
    ├── console_page.py server tabs, players, quick actions
    ├── server_page.py  one server's console and command line
    ├── servers_page.py / settings_page.py / about_page.py
    ├── command_input.py  Tab completion, suggestion popup, hint bar
    ├── session.py      one Session (worker thread + console log) per server
    ├── updates.py      when to check, download and install updates
    ├── theme.py        light/dark tokens and the style sheet
    ├── widgets.py      custom-painted buttons, cards, toggles, segmented control, nav rail
    ├── icons.py        the line icon set (SVG, drawn for this app)
    └── winutil.py      title bar colours on Windows
tools/                  fake server, build, screenshots, icon art
```

A few rules that keep things working:

- **Network I/O never runs on the UI thread.** Each `Session` owns a `RconWorker` on its own `QThread`, and they talk only through queued signals.
- **No font rules in the global style sheet.** Fonts are set in code (`theme.display_font()` / `mono_font()`). A QSS font rule would override every `setFont()` call.
- **Scope widget style sheets** (`QLabel { ... }`, `#name { ... }`). An unscoped `setStyleSheet("background: ...")` cascades into every child.
- **Colours come from the theme**, read at paint time through `theme.current()`, so both themes keep working.

## Adding or fixing a command in the completion catalog

Commands live in `src/mcrcon_gui/core/commands/catalog.py`, one line each:

```python
C("give", "<target:player> <item:item> [count:int]", desc="Give an item to a player"),
```

- `<name:type>` required argument, `[name:type]` optional
- `(a|b|c)` a choice of fixed words
- `<name:(a|b)>` an argument with a fixed set of values
- several strings = several alternative branches

Argument types are listed in `ArgType` (`grammar.py`); value lists such as items and game rules are in `data.py`. Add a test case in `tests/test_core.py` for anything non-trivial.

## Changing the UI

If you change how the app looks, regenerate the README screenshots:

```bash
python tools/screenshots.py
```

The icon and installer artwork are drawn in code by `tools/make_art.py`.

## Building a release

```bash
python tools/build.py
```

This produces `dist/MCRCON GUI/` and a portable zip. The Windows installer is built by the maintainer with [Inno Setup 6](https://jrsoftware.org/isinfo.php) from a local script; `build.py` skips that step when the script is not present.

## Publishing an update (maintainer)

The installed app polls `https://mcrcon.app/update/latest.json` at every start and every 24 hours. To ship a new version:

1. Bump `__version__` in `src/mcrcon_gui/__init__.py` and add the release to `CHANGELOG.md`.
2. `python tools/build.py`, then publish a GitHub release tagged `v<version>` with the setup exe, the portable zip and `SHA256SUMS.txt`.
3. In the private `mcrcon-website` repo, update `update/latest.json` (version, URLs, `sha256`, `size`, notes) and the changelog in `src/data/site.json`, run `npm run build && npm test`, and push. Cloudflare Pages deploys it and every installed copy picks the update up.

Publish the GitHub release **before** pushing the manifest: the app downloads from the release URL. To test an update end to end first, point a copy at a local feed with the `MCRCON_GUI_UPDATE_MANIFEST` environment variable.

## Pull requests

- Keep each PR focused on one change.
- Match the surrounding style. Type hints, `from __future__ import annotations`, short docstrings that explain *why*.
- Make sure `python -m pytest` passes.
- Describe what changed and how you tested it; add before/after screenshots for UI changes.
- Add a line to `CHANGELOG.md` under *Unreleased*.

By contributing you agree that your work is released under the [MIT License](LICENSE) and that you'll follow the [Code of Conduct](CODE_OF_CONDUCT.md).
