"""The terminal-style console that renders a session's :class:`ConsoleLog`."""

from __future__ import annotations

import html

from PySide6.QtWidgets import QTextBrowser, QWidget

from ..core.formatting import to_html
from ..core.models import ConsoleEntry
from .theme import mono_font

# The console is dark in both themes, so its colours are fixed.
_COLORS = {
    "stamp": "#6F6F6F",
    "command": "#FFD23F",
    "system": "#4CC9F0",
    "ok": "#3DDC97",
    "error": "#FF5A5F",
    "meta": "#5E5E5E",
}
_INDENT = "&nbsp;" * 11  # width of "[HH:MM:SS] "


class ConsoleView(QTextBrowser):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("console")
        self.setOpenLinks(False)
        self.setFont(mono_font(12))
        self.document().setMaximumBlockCount(5000)
        self.show_timestamps = True
        self.filter_text = ""

    def render_entries(self, entries) -> None:
        self.setUpdatesEnabled(False)
        self.clear()
        needle = self.filter_text.lower()
        for entry in entries:
            if not needle or needle in entry.text.lower():
                self.append(self._entry_html(entry))
        self.setUpdatesEnabled(True)
        self._scroll_to_end()

    def add_entry(self, entry: ConsoleEntry) -> None:
        if self.filter_text and self.filter_text.lower() not in entry.text.lower():
            return
        bar = self.verticalScrollBar()
        at_bottom = bar.value() >= bar.maximum() - 4
        self.append(self._entry_html(entry))
        if at_bottom or entry.kind == "command":
            self._scroll_to_end()

    def _scroll_to_end(self) -> None:
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _entry_html(self, e: ConsoleEntry) -> str:
        c = _COLORS
        if e.kind == "command":
            body = f'<span style="color:{c["command"]}; font-weight:700">› /{html.escape(e.text)}</span>'
        elif e.kind == "output":
            body = to_html(e.text) if e.text.strip() else f'<span style="color:{c["meta"]}">(no response)</span>'
        else:
            mark = {"ok": "✔ ", "error": "✖ "}.get(e.kind, "")
            body = f'<span style="color:{c.get(e.kind, c["system"])}">{mark}{html.escape(e.text)}</span>'
        if e.meta:
            body += f' <span style="color:{c["meta"]}">· {html.escape(e.meta)}</span>'
        if not self.show_timestamps:
            return body
        # Continuation lines line up under the text, past the timestamp.
        body = body.replace("<br>", "<br>" + _INDENT)
        return f'<span style="color:{c["stamp"]}">[{e.at:%H:%M:%S}]</span> {body}'
