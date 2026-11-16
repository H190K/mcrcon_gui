"""The command line: history, Tab completion, a suggestion popup and a usage hint bar.

Keys
    Tab / Shift+Tab   complete, then cycle through candidates (forward / backward)
    Up / Down         move in the popup when it is open, otherwise walk the history
    Enter             accept the highlighted candidate if you picked one, otherwise send
    Esc               close the popup; press again to clear the line
    Ctrl+Space        open the popup
"""

from __future__ import annotations

import html
import os
from typing import Callable

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QStyle,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)

from ..core.completion import Candidate, Completion, CompletionContext, CompletionEngine
from . import theme
from .theme import Theme, display_font, mono_font

MAX_VISIBLE_ROWS = 9
ROW_HEIGHT = 26
_KIND_TAGS = {"player": "PLAYER", "selector": "SELECTOR", "command": "CMD"}


def _common_prefix(words: list[str]) -> str:
    prefix = os.path.commonprefix([w.lower() for w in words])
    return words[0][: len(prefix)] if words else ""


class _CandidateDelegate(QStyledItemDelegate):
    """Draws the candidate on the left and its detail, muted, on the right."""

    def paint(self, painter: QPainter, option, index) -> None:
        t = theme.current()
        candidate: Candidate = index.data(Qt.ItemDataRole.UserRole)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        rect = option.rect
        painter.save()
        if selected:
            painter.fillRect(rect, QColor(t.yellow))
        painter.setFont(mono_font(13, bold=selected))
        painter.setPen(QColor(t.on_accent if selected else t.text))
        text_rect = rect.adjusted(10, 0, -10, 0)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, candidate.text)
        detail = _KIND_TAGS.get(candidate.kind, "") if not candidate.detail or candidate.kind == "player" else candidate.detail
        if detail:
            painter.setFont(mono_font(10))
            painter.setPen(QColor(t.on_accent if selected else t.muted_text))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, detail.upper())
        painter.restore()

    def sizeHint(self, option, index) -> QSize:  # noqa: N802
        return QSize(200, ROW_HEIGHT)


class SuggestionPopup(QFrame):
    """A floating list. It is a child widget, not a popup window, so it never steals focus."""

    activated = Signal(int)

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("suggestionPopup")
        layout = QVBoxLayout(self)
        t = theme.current()
        layout.setContentsMargins(t.border, t.border, t.border + 4, t.border + 4)
        layout.setSpacing(0)
        self.header = QLabel()
        self.header.setFont(display_font(10))
        layout.addWidget(self.header)
        self.list = QListWidget()
        self.list.setObjectName("suggestions")
        self.list.setItemDelegate(_CandidateDelegate(self.list))
        self.list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.itemClicked.connect(lambda item: self.activated.emit(self.list.row(item)))
        layout.addWidget(self.list)
        self.candidates: list[Candidate] = []
        self.hide()
        self.apply_theme(t)

    def apply_theme(self, t: Theme) -> None:
        self.header.setStyleSheet(
            f"QLabel {{ background:{t.ink}; color:{t.paper}; padding:5px 10px; letter-spacing:1px; }}"
        )

    def set_candidates(self, candidates: list[Candidate], title: str) -> None:
        self.candidates = candidates
        self.header.setText(f"{title.upper()}  ·  {len(candidates)}")
        self.list.clear()
        for c in candidates:
            item = QListWidgetItem(c.text)
            item.setData(Qt.ItemDataRole.UserRole, c)
            self.list.addItem(item)
        self.list.setCurrentRow(-1)

    def current(self) -> int:
        return self.list.currentRow()

    def select(self, row: int) -> None:
        if self.candidates:
            self.list.setCurrentRow(row % len(self.candidates))
            self.list.scrollToItem(self.list.currentItem())

    def place(self, anchor: QPoint, width: int = 340) -> None:
        rows = min(len(self.candidates), MAX_VISIBLE_ROWS)
        height = rows * ROW_HEIGHT + self.header.sizeHint().height() + 2 * theme.current().border + 8
        parent = self.parentWidget()
        x = max(8, min(anchor.x(), parent.width() - width - 8))
        self.setGeometry(QRect(x, anchor.y() - height - 6, width, height))
        self.show()
        self.raise_()

    def paintEvent(self, event) -> None:  # noqa: N802
        t = theme.current()
        p = QPainter(self)
        face = QRect(0, 0, self.width() - 4, self.height() - 4)
        p.fillRect(face.translated(4, 4), QColor(t.ink))
        p.fillRect(face, QColor(t.surface))
        pen = QPen(QColor(t.ink), t.border)
        pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        p.setPen(pen)
        half = t.border / 2
        p.drawRect(face.toRectF().adjusted(half, half, -half, -half))


class HintBar(QLabel):
    """Shows the usage of the command being typed, with the current argument highlighted."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFont(mono_font(12))
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setMinimumHeight(24)
        self._completion: Completion | None = None
        self.apply_theme(theme.current())

    def show_completion(self, completion: Completion | None) -> None:
        self._completion = completion
        t = theme.current()
        if completion is None or not completion.hint:
            self.setText(f'<span style="color:{t.muted_text}">Tab completes · ↑↓ history · Ctrl+Space suggestions</span>')
            return
        parts = []
        for word in completion.hint.split(" "):
            if word.startswith("*") and word.endswith("*") and len(word) > 2:
                parts.append(
                    f'<span style="background:{t.yellow}; color:{t.on_accent}; font-weight:700">&nbsp;{html.escape(word[1:-1])}&nbsp;</span>'
                )
            else:
                parts.append(html.escape(word))
        extra = " &nbsp;·&nbsp; ".join(html.escape(x) for x in (completion.values, completion.description) if x)
        muted = f'&nbsp;&nbsp;<span style="color:{t.muted_text}">{extra}</span>' if extra else ""
        self.setText(f'<span style="color:{t.text}">/{" ".join(parts)}</span>{muted}')

    def apply_theme(self, t: Theme) -> None:
        self.setStyleSheet("QLabel { padding: 2px 2px; }")
        self.show_completion(self._completion)


class CommandLineEdit(QLineEdit):
    """A line edit with history and grammar-aware completion."""

    submitted = Signal(str)

    def __init__(
        self,
        popup: SuggestionPopup,
        hint: HintBar,
        context: Callable[[], CompletionContext],
        engine: CompletionEngine,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.popup = popup
        self.hint = hint
        self._context = context
        self._engine = engine
        self.history: list[str] = []
        self._history_index: int | None = None
        self._draft = ""
        self._completion: Completion | None = None
        self._cycling = False  # Tab/arrow navigation is previewing candidates in the line
        self.setFont(mono_font(13))
        self.textEdited.connect(self._on_edited)
        self.popup.activated.connect(self._accept_row)

    # -- completion ----------------------------------------------------------------------

    def _compute(self) -> Completion:
        return self._engine.complete(self.text(), self.cursorPosition(), self._context())

    def _on_edited(self, _text: str = "") -> None:
        self._cycling = False
        self._history_index = None
        self.refresh()

    def refresh(self, force_popup: bool = False) -> None:
        completion = self._compute()
        self._completion = completion
        self.hint.show_completion(completion)
        partial = self.text()[completion.start : completion.end]
        candidates = completion.candidates
        exact = len(candidates) == 1 and candidates[0].text.lower() == partial.lower()
        if candidates and not exact and (force_popup or self.text().strip()):
            self.show_suggestions(completion)
        else:
            self.popup.hide()

    def show_suggestions(self, completion: Completion | None = None) -> None:
        completion = completion or self._compute()
        self._completion = completion
        if not completion.candidates:
            self.popup.hide()
            return
        title = completion.arg_name or ("command" if completion.start <= 1 else "options")
        self.popup.set_candidates(completion.candidates, title)
        x = self.fontMetrics().horizontalAdvance(self.text()[: completion.start]) + 8
        anchor = self.mapTo(self.popup.parentWidget(), QPoint(min(x, self.width() - 120), 0))
        self.popup.place(anchor)

    def _preview(self, row: int) -> None:
        """Write the highlighted candidate into the line so Tab-Tab-Tab visibly rotates."""
        c = self._completion
        if c is None or not c.candidates:
            return
        self.popup.select(row)
        candidate = c.candidates[self.popup.current()]
        text = self.text()
        self.setText(text[: c.start] + candidate.text + text[c.end :])
        c.end = c.start + len(candidate.text)
        self.setCursorPosition(c.end)
        self._cycling = True

    def _insert(self, candidate_text: str, space: bool) -> None:
        c = self._completion
        if c is None:
            return
        text = self.text()
        insert = candidate_text + (" " if space and not text[c.end :].startswith(" ") else "")
        self.setText(text[: c.start] + insert + text[c.end :])
        self.setCursorPosition(c.start + len(insert))
        self._cycling = False
        self.refresh()

    def _accept_row(self, row: int) -> None:
        c = self._completion
        if c is not None and 0 <= row < len(c.candidates):
            self._insert(c.candidates[row].text, space=True)
            self.setFocus()

    def _tab(self, backwards: bool) -> None:
        if self._cycling and self.popup.isVisible():
            self._preview(self.popup.current() + (-1 if backwards else 1))
            return
        completion = self._compute()
        self._completion = completion
        self.hint.show_completion(completion)
        candidates = completion.candidates
        if not candidates:
            return
        if len(candidates) == 1:
            self._insert(candidates[0].text, space=True)
            return
        partial = self.text()[completion.start : completion.end]
        prefix = _common_prefix([c.text for c in candidates])
        if len(prefix) > len(partial):
            self._insert(prefix, space=False)
            return
        self.show_suggestions(completion)
        self._preview(len(candidates) - 1 if backwards else 0)

    # -- keys ----------------------------------------------------------------------------

    def event(self, event) -> bool:
        # Tab would otherwise move focus to the next widget before keyPressEvent sees it.
        if event.type() == event.Type.KeyPress and event.key() in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            self._tab(backwards=event.key() == Qt.Key.Key_Backtab or bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier))
            return True
        return super().event(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        key = event.key()
        popup_open = self.popup.isVisible()
        if key == Qt.Key.Key_Space and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.refresh(force_popup=True)
            return
        if key in (Qt.Key.Key_Up, Qt.Key.Key_Down) and popup_open:
            step = -1 if key == Qt.Key.Key_Up else 1
            current = self.popup.current()
            if current < 0:  # nothing highlighted yet: start at the top (Down) or bottom (Up)
                row = 0 if step > 0 else len(self.popup.candidates) - 1
            else:
                row = current + step
            self._preview(row)
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._cycling and popup_open and self.popup.current() >= 0:
                self._insert(self.popup.candidates[self.popup.current()].text, space=True)
                return
            self.popup.hide()
            self._submit()
            return
        if key == Qt.Key.Key_Escape:
            if popup_open:
                self.popup.hide()
                self._cycling = False
            else:
                self.clear()
                self._history_index = None
                self.hint.show_completion(None)
            return
        if key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            self._walk_history(-1 if key == Qt.Key.Key_Up else 1)
            return
        super().keyPressEvent(event)
        if key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Home, Qt.Key.Key_End):
            self._cycling = False
            self.refresh()

    def focusOutEvent(self, event) -> None:  # noqa: N802
        self.popup.hide()
        self._cycling = False
        super().focusOutEvent(event)

    # -- history / submit ----------------------------------------------------------------

    def _walk_history(self, step: int) -> None:
        if not self.history:
            return
        if self._history_index is None:
            if step > 0:
                return
            self._draft = self.text()
            self._history_index = len(self.history)
        self._history_index += step
        if self._history_index >= len(self.history):
            self._history_index = None
            self.setText(self._draft)
        else:
            self._history_index = max(0, self._history_index)
            self.setText(self.history[self._history_index])
        self.hint.show_completion(self._compute() if self.text() else None)

    def _submit(self) -> None:
        text = self.text().strip()
        if text:
            self._history_index = None
            self._cycling = False
            self.submitted.emit(text)
            self.clear()
            self.hint.show_completion(None)
