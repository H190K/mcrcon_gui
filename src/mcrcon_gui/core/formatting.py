"""Turn Minecraft's legacy "§" formatting codes into HTML for the console view."""

from __future__ import annotations

import html
import re

SECTION = "§"

# Foreground colours from the Minecraft wiki, nudged slightly for legibility on black.
COLORS = {
    "0": "#4a4a4a",  # black (lifted so it is visible on the console background)
    "1": "#3b5bff",
    "2": "#22b14c",
    "3": "#14b8b8",
    "4": "#e03131",
    "5": "#b83bd6",
    "6": "#ffaa00",
    "7": "#bdbdbd",
    "8": "#7a7a7a",
    "9": "#6b8cff",
    "a": "#55ff55",
    "b": "#55ffff",
    "c": "#ff5555",
    "d": "#ff55ff",
    "e": "#ffff55",
    "f": "#ffffff",
}

STYLES = {
    "l": "font-weight:700",
    "m": "text-decoration:line-through",
    "n": "text-decoration:underline",
    "o": "font-style:italic",
}

_CODE = re.compile(SECTION + r"([0-9a-fk-or])", re.IGNORECASE)


def strip_codes(text: str) -> str:
    """Remove every formatting code, e.g. for copying plain text."""
    return _CODE.sub("", text)


def to_html(text: str) -> str:
    """Convert ``text`` to HTML spans. Newlines become ``<br>``; everything else is escaped."""
    out: list[str] = []
    color: str | None = None
    styles: list[str] = []
    pos = 0

    def flush(segment: str) -> None:
        if not segment:
            return
        escaped = html.escape(segment).replace("\n", "<br>")
        css = ([f"color:{color}"] if color else []) + styles
        out.append(f'<span style="{";".join(css)}">{escaped}</span>' if css else escaped)

    for match in _CODE.finditer(text):
        flush(text[pos : match.start()])
        pos = match.end()
        code = match.group(1).lower()
        if code in COLORS:
            # In Minecraft a colour code also resets any active style.
            color, styles = COLORS[code], []
        elif code in STYLES:
            if STYLES[code] not in styles:
                styles.append(STYLES[code])
        elif code == "r":
            color, styles = None, []
        # "k" (obfuscated) is ignored: rendering random glyphs in a log is not useful.
    flush(text[pos:])
    return "".join(out)
