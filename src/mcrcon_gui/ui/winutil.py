"""Small Windows integrations via ctypes (safe no-ops elsewhere)."""

from __future__ import annotations

import sys

IS_WINDOWS = sys.platform == "win32"

DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19  # Windows 10 1809-1909
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_BORDER_COLOR = 34  # Windows 11+
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36


def _colorref(hex_color: str) -> int:
    value = hex_color.lstrip("#")
    r, g, b = int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
    return r | (g << 8) | (b << 16)


def style_title_bar(hwnd: int, *, dark: bool, caption: str, text: str, border: str | None = None) -> None:
    """Make the native title bar and window border match the app theme.

    Attribute 20 switches the frame to dark mode; 34-36 set border, caption and caption-text
    colours on Windows 11 (older systems silently ignore them).
    """
    if not IS_WINDOWS or not hwnd:
        return
    try:
        import ctypes
        from ctypes import wintypes

        set_attr = ctypes.windll.dwmapi.DwmSetWindowAttribute
        set_attr.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
        set_attr.restype = ctypes.c_long
        flag = ctypes.c_int(1 if dark else 0)
        if set_attr(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(flag), ctypes.sizeof(flag)) != 0:
            set_attr(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE_OLD, ctypes.byref(flag), ctypes.sizeof(flag))
        for attr, colour in ((DWMWA_CAPTION_COLOR, caption), (DWMWA_TEXT_COLOR, text), (DWMWA_BORDER_COLOR, border)):
            if colour:
                value = wintypes.DWORD(_colorref(colour))
                set_attr(hwnd, attr, ctypes.byref(value), ctypes.sizeof(value))
    except Exception:  # noqa: BLE001 - cosmetic only
        pass


def set_app_user_model_id(app_id: str) -> None:
    """Give the app its own taskbar identity and icon instead of python.exe's."""
    if not IS_WINDOWS:
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(ctypes.c_wchar_p(app_id))
    except Exception:  # noqa: BLE001
        pass
