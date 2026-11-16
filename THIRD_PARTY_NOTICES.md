# Third-Party Notices

MCRCON GUI is MIT-licensed (see `LICENSE`). The distributed app bundles the following third-party components, each under its own license.

| Component | License | Source |
|---|---|---|
| **Qt 6 / PySide6** (Qt for Python) | GNU LGPL v3 | https://www.qt.io/qt-for-python — source: https://code.qt.io/cgit/pyside/pyside-setup.git |
| **Python** runtime | PSF License | https://www.python.org |
| **PyInstaller** bootloader | GPL v2 with bootloader exception (allows bundling into any app) | https://pyinstaller.org |
| **Archivo Black** font | SIL Open Font License 1.1 | https://fonts.google.com/specimen/Archivo+Black |
| **Space Mono** font | SIL Open Font License 1.1 | https://fonts.google.com/specimen/Space+Mono |

## About the LGPL (Qt / PySide6)

Qt and PySide6 are used unmodified, as dynamically loaded libraries. You may replace them with your own build: the full source of this app is available at https://github.com/H190K/mcrcon_gui, so you can install your own PySide6 and run or rebuild the app with `python tools/build.py`. The LGPL v3 text is available at https://www.gnu.org/licenses/lgpl-3.0.html.

## Fonts

The full OFL texts ship with the source in `src/mcrcon_gui/assets/fonts/`.

"Minecraft" is a trademark of Mojang Synergies AB. MCRCON GUI is an independent project and is not affiliated with or endorsed by Mojang or Microsoft.
