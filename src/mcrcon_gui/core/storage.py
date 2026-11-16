"""Read and write settings as versioned JSON in the per-user config directory.

Writes are atomic (temp file + rename) and the previous file is kept as ``config.json.bak``,
which is used automatically if the main file is ever corrupted.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

from . import secrets
from .models import HISTORY_LIMIT, AppSettings, QuickCommand, ServerProfile

SCHEMA_VERSION = 2
APP_DIR_NAME = "mcrcon-gui"


def config_dir() -> Path:
    if override := os.environ.get("MCRCON_GUI_CONFIG_DIR"):
        return Path(override)
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_DIR_NAME


def config_path() -> Path:
    return config_dir() / "config.json"


# -- migrations ------------------------------------------------------------------------


def _legacy_file() -> dict | None:
    """The ``config.json`` the old Tkinter/WebView builds kept next to the program."""
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path.cwd()
    try:
        data = json.loads((base / "config.json").read_text(encoding="utf-8-sig"))  # tolerate a BOM from editors
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or "server_ip" not in data:
        return None
    password = str(data.get("password", ""))
    return {"host": data.get("server_ip"), "port": data.get("port"), "password": "" if password == "your_rcon_password_here" else password}


def migrate(data: dict) -> dict:
    """Bring any older settings dict up to the current schema."""
    if "server_ip" in data:
        data = {"host": data.get("server_ip"), "port": data.get("port"), "password": data.get("password", "")}
    if "version" not in data and "host" in data:  # v1: a single server
        profile = {
            "name": "Default",
            "host": data.get("host"),
            "port": data.get("port"),
            "password": data.get("password", ""),
            "remember_password": data.get("remember_password", True),
            "auto_connect": data.get("auto_connect", False),
            "history": data.get("history", []),
        }
        data = {"version": SCHEMA_VERSION, "profiles": [profile], "quick_commands": data.get("quick_commands")}
    data["version"] = SCHEMA_VERSION
    return data


# -- (de)serialisation -----------------------------------------------------------------


def _int(value: object, default: int, lo: int, hi: int) -> int:
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return number if lo <= number <= hi else default


def _profile_from(data: dict) -> ServerProfile:
    p = ServerProfile()
    p.id = str(data.get("id") or p.id)
    p.name = str(data.get("name") or p.name).strip() or p.name
    p.host = str(data.get("host") or p.host).strip() or p.host
    p.port = _int(data.get("port"), p.port, 1, 65535)
    p.password = secrets.unprotect(data.get("password", ""))
    p.remember_password = bool(data.get("remember_password", True))
    p.auto_connect = bool(data.get("auto_connect", False))
    p.auto_reconnect = bool(data.get("auto_reconnect", True))
    p.color = str(data.get("color", p.color))
    history = data.get("history", [])
    if isinstance(history, list):
        p.history = [str(h) for h in history if str(h).strip()][-HISTORY_LIMIT:]
    return p


def from_dict(data: dict) -> AppSettings:
    data = migrate(dict(data))
    s = AppSettings()
    if data.get("theme") in ("light", "dark", "system"):
        s.theme = data["theme"]
    s.show_timestamps = bool(data.get("show_timestamps", True))
    s.confirm_dangerous = bool(data.get("confirm_dangerous", True))
    s.auto_update = bool(data.get("auto_update", True))
    s.last_update_check = str(data.get("last_update_check", "") or "")
    quick = data.get("quick_commands")
    if isinstance(quick, list):
        parsed = [QuickCommand(str(q["label"]), str(q["command"])) for q in quick if isinstance(q, dict) and q.get("label") and q.get("command")]
        if parsed:
            s.quick_commands = parsed
    profiles = data.get("profiles")
    if isinstance(profiles, list):
        s.profiles = [_profile_from(p) for p in profiles if isinstance(p, dict)]
    s.active_profile_id = data.get("active_profile_id")
    window = data.get("window")
    if isinstance(window, dict):
        s.window = {"w": _int(window.get("w"), 1280, 800, 10000), "h": _int(window.get("h"), 860, 600, 10000)}
    s.ensure_default_profile()
    return s


def to_dict(s: AppSettings) -> dict:
    return {
        "version": SCHEMA_VERSION,
        "theme": s.theme,
        "show_timestamps": s.show_timestamps,
        "confirm_dangerous": s.confirm_dangerous,
        "auto_update": s.auto_update,
        "last_update_check": s.last_update_check,
        "active_profile_id": s.active_profile_id,
        "window": s.window,
        "quick_commands": [{"label": q.label, "command": q.command} for q in s.quick_commands],
        "profiles": [
            {
                "id": p.id,
                "name": p.name,
                "host": p.host,
                "port": p.port,
                "password": secrets.protect(p.password if p.remember_password else ""),
                "remember_password": p.remember_password,
                "auto_connect": p.auto_connect,
                "auto_reconnect": p.auto_reconnect,
                "color": p.color,
                "history": p.history,
            }
            for p in s.profiles
        ],
    }


# -- files -----------------------------------------------------------------------------


def _read(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))  # tolerate a BOM from editors
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def load() -> AppSettings:
    path = config_path()
    data = _read(path)
    if data is None:
        data = _read(path.with_name(path.name + ".bak"))
    if data is None and not path.exists():
        data = _legacy_file()
    return from_dict(data or {})


def save(settings: AppSettings) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(to_dict(settings), fh, indent=2)
        fh.flush()
        os.fsync(fh.fileno())
    if sys.platform != "win32":
        os.chmod(tmp, 0o600)
    if path.exists():
        shutil.copyfile(path, path.with_name(path.name + ".bak"))
    os.replace(tmp, path)
