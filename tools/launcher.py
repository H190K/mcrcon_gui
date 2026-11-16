"""PyInstaller entry point (a package's __main__ can't be frozen directly because of its relative imports).

A windowed app has no console, so a crash at startup would vanish silently. Write it to
crash.log in the settings folder and tell the user where it is.
"""

import os
import sys
import traceback
from pathlib import Path


def _crash_log() -> Path:
    base = os.environ.get("MCRCON_GUI_CONFIG_DIR") or (
        Path(os.environ.get("APPDATA", Path.home())) / "mcrcon-gui" if sys.platform == "win32" else Path.home() / ".config" / "mcrcon-gui"
    )
    path = Path(base) / "crash.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


try:
    from mcrcon_gui.app import main

    sys.exit(main())
except SystemExit:
    raise
except BaseException:
    log = _crash_log()
    log.write_text(traceback.format_exc(), encoding="utf-8")
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, f"MCRCON GUI crashed while starting.\n\nDetails were saved to:\n{log}", "MCRCON GUI", 0x10)
    raise
