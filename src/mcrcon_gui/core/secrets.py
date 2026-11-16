"""Protect saved RCON passwords.

On Windows passwords are encrypted with DPAPI, which ties them to the current Windows
user account. Elsewhere there is no OS facility we can use without extra dependencies,
so they are stored as plain text in a file only the user can read. We deliberately do
not "obfuscate" them: base64 or XOR would look like protection without being any.
"""

from __future__ import annotations

import base64
import sys

_ENTROPY = b"mcrcon-gui"


def _dpapi(data: bytes, encrypt: bool) -> bytes:
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):  # noqa: N801 - Win32 name
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    def blob(raw: bytes) -> DATA_BLOB:
        buf = ctypes.create_string_buffer(raw, len(raw))
        return DATA_BLOB(len(raw), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    source, entropy, out = blob(data), blob(_ENTROPY), DATA_BLOB()
    fn = crypt32.CryptProtectData if encrypt else crypt32.CryptUnprotectData
    # 0x1 = CRYPTPROTECT_UI_FORBIDDEN: never show a prompt.
    if not fn(ctypes.byref(source), None, ctypes.byref(entropy), None, None, 0x1, ctypes.byref(out)):
        raise OSError("DPAPI call failed")
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        kernel32.LocalFree(out.pbData)


def protect(text: str) -> dict:
    """Return the JSON-ready form of ``text``."""
    if not text:
        return {"scheme": "none", "data": ""}
    if sys.platform == "win32":
        try:
            encrypted = _dpapi(text.encode("utf-8"), encrypt=True)
            return {"scheme": "dpapi", "data": base64.b64encode(encrypted).decode("ascii")}
        except (OSError, AttributeError, ValueError):
            pass
    return {"scheme": "plain", "data": text}


def unprotect(value: object) -> str:
    """Inverse of :func:`protect`. Anything unreadable becomes an empty password."""
    if isinstance(value, str):  # v1 files stored the bare string
        return value
    if not isinstance(value, dict):
        return ""
    scheme, data = value.get("scheme"), value.get("data", "")
    if scheme == "plain" and isinstance(data, str):
        return data
    if scheme == "dpapi" and sys.platform == "win32":
        try:
            return _dpapi(base64.b64decode(data), encrypt=False).decode("utf-8")
        except (OSError, AttributeError, ValueError):
            return ""
    return ""
