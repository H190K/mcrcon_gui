"""Client-side command completion.

Vanilla RCON has no completion API (Brigadier suggestions are only sent to game clients),
so completion is driven by the static grammar in :mod:`.commands` plus live data: the
online players from ``list`` and extra command names from ``help``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .commands import CATALOG, ArgType, Command, Node
from .commands import data

MAX_CANDIDATES = 60
_NUMBER = re.compile(r"[-+]?\d+(\.\d+)?$")
_INTEGER = re.compile(r"[-+]?\d+$")
_COORD = re.compile(r"[~^]?[-+]?(\d+(\.\d*)?|\.\d+)?$")


@dataclass
class CompletionContext:
    players: list[str] = field(default_factory=list)
    extra_commands: set[str] = field(default_factory=set)
    objectives: list[str] = field(default_factory=list)
    teams: list[str] = field(default_factory=list)


@dataclass
class Candidate:
    text: str
    detail: str = ""
    kind: str = "literal"  # literal | player | selector | value | command


@dataclass
class Completion:
    candidates: list[Candidate]
    start: int  # the span of text[...] that a chosen candidate replaces
    end: int
    hint: str = ""  # usage, current argument wrapped in *stars*
    arg_name: str | None = None
    description: str = ""
    values: str = ""  # e.g. "survival | creative | adventure | spectator"


@dataclass
class _State:
    node: Node
    path: tuple[Node, ...]
    pending: int = 0  # tokens still owed to a multi-token argument (a position takes 3)
    command: Command | None = None

    @property
    def greedy(self) -> bool:
        return self.node.greedy and self.node.type is not ArgType.COMMAND


_STATIC_VALUES = {
    ArgType.GAMEMODE: data.GAMEMODES,
    ArgType.DIFFICULTY: data.DIFFICULTIES,
    ArgType.WEATHER: data.WEATHER,
    ArgType.TIMESPEC: data.TIMESPEC,
    ArgType.DIMENSION: data.DIMENSIONS,
    ArgType.COLOR: data.COLORS,
    ArgType.BOOL: data.BOOLS,
    ArgType.GAMERULE: list(data.GAMERULES),
    ArgType.ITEM: data.ITEMS,
    ArgType.BLOCK: data.BLOCKS,
    ArgType.EFFECT: data.EFFECTS,
    ArgType.ENCHANTMENT: data.ENCHANTMENTS,
    ArgType.ENTITY_TYPE: data.ENTITY_TYPES,
}
_KIND_ORDER = {"literal": 0, "command": 0, "player": 1, "value": 2, "selector": 3}


class CompletionEngine:
    def __init__(self, catalog: dict[str, Command] = CATALOG) -> None:
        self.catalog = catalog
        # A virtual root whose children are every command name (aliases share the real children).
        self._roots = Node(children=[Node(literal=name, children=cmd.root.children) for name, cmd in catalog.items()])

    # -- public ------------------------------------------------------------------------

    def complete(self, text: str, cursor: int | None = None, ctx: CompletionContext | None = None) -> Completion:
        ctx = ctx or CompletionContext()
        cursor = len(text) if cursor is None else cursor
        before = text[:cursor]
        offset = len(before) - len(before.lstrip())
        if before[offset : offset + 1] == "/":
            offset += 1
        tokens = [(m.start() + offset, m.group()) for m in re.finditer(r"\S+", before[offset:])]

        if not tokens or before[-1:].isspace():
            partial, start, done = "", cursor, tokens
        else:
            (start, partial), done = tokens[-1], tokens[:-1]

        if not done:
            return self._complete_root(partial, start, cursor, ctx)

        states = [_State(self._roots, ())]
        for _, token in done:
            states = self._advance(states, token)
            if not states:
                return Completion([], start, cursor)

        candidates: list[Candidate] = []
        for state in states:
            if state.pending or state.greedy:
                continue
            prev = done[-1][1]
            for child in state.node.children:
                candidates.extend(self._values(child, ctx, prev))
        candidates = self._filter(candidates, partial)

        current, rest_state = self._current_node(states, partial)
        command = rest_state.command if rest_state else None
        values = ""
        if current is not None and not current.is_literal:
            options = current.choices or _STATIC_VALUES.get(current.type, [])  # type: ignore[arg-type]
            if 0 < len(options) <= 8:
                values = " | ".join(options)
        return Completion(
            candidates=candidates,
            start=start,
            end=cursor,
            hint=self._usage(rest_state, current) if rest_state else "",
            arg_name=current.arg if current is not None else None,
            description=command.description if command else "",
            values=values,
        )

    # -- walking -----------------------------------------------------------------------

    def _advance(self, states: list[_State], token: str) -> list[_State]:
        out: list[_State] = []
        for state in states:
            if state.pending:
                out.append(_State(state.node, state.path, state.pending - 1, state.command))
                continue
            if state.greedy:
                out.append(state)
                continue
            for child in state.node.children:
                if child.type is ArgType.COMMAND:
                    # "execute ... run <command>": continue the walk from the command roots.
                    out.extend(self._advance([_State(self._roots, state.path + (child,), 0, state.command)], token))
                elif self._matches(child, token):
                    command = state.command
                    if state.node is self._roots:
                        command = self.catalog.get(child.literal or "")
                    pending = 2 if child.type is ArgType.POS else 0
                    out.append(_State(child, state.path + (child,), pending, command))
        return out

    @staticmethod
    def _matches(node: Node, token: str) -> bool:
        if node.is_literal:
            return token.lower() == node.literal.lower()  # type: ignore[union-attr]
        if node.greedy:
            return True
        t = node.type
        if t is ArgType.BOOL:
            return token in ("true", "false")
        if t is ArgType.INT:
            return bool(_INTEGER.match(token))
        if t in (ArgType.FLOAT, ArgType.TIME):
            return bool(_NUMBER.match(token.rstrip("dst"))) if t is ArgType.TIME else bool(_NUMBER.match(token))
        if t is ArgType.CHOICE:
            return token in node.choices
        if t in (ArgType.POS, ArgType.COORD):
            return bool(_COORD.match(token))
        return True  # names, items, values: be lenient, the server validates

    # -- candidates --------------------------------------------------------------------

    def _complete_root(self, partial: str, start: int, end: int, ctx: CompletionContext) -> Completion:
        names = {name: "command" for name in self.catalog}
        for extra in ctx.extra_commands:
            names.setdefault(extra, "command")
        candidates = self._filter([Candidate(n, self._describe(n), "command") for n in names], partial)
        command = self.catalog.get(partial.lower())
        state = _State(command.root, (command.root,), 0, command) if command else None
        return Completion(
            candidates=candidates,
            start=start,
            end=end,
            hint=self._usage(state, None) if state else "",
            description=command.description if command else "",
        )

    def _describe(self, name: str) -> str:
        command = self.catalog.get(name)
        return command.description if command else "server command"

    def _values(self, node: Node, ctx: CompletionContext, prev: str) -> list[Candidate]:
        if node.is_literal:
            return [Candidate(node.literal, "", "literal")]  # type: ignore[arg-type]
        t = node.type
        players = [Candidate(p, "online", "player") for p in ctx.players]
        if t is ArgType.PLAYER:
            return players + [Candidate(s, "selector", "selector") for s in data.PLAYER_SELECTORS]
        if t is ArgType.ENTITY:
            return players + [Candidate(s, "selector", "selector") for s in data.ENTITY_SELECTORS]
        if t is ArgType.CHOICE:
            return [Candidate(c, node.arg or "", "value") for c in node.choices]
        if t is ArgType.GAMERULE_VALUE:
            return [Candidate(b, "", "value") for b in data.BOOLS] if data.GAMERULES.get(prev) == "bool" else []
        if t in (ArgType.COMMAND, ArgType.COMMAND_NAME):
            names = sorted(set(self.catalog) | ctx.extra_commands)
            return [Candidate(n, self._describe(n), "command") for n in names]
        if t is ArgType.OBJECTIVE:
            return [Candidate(o, "objective", "value") for o in ctx.objectives]
        if t is ArgType.TEAM:
            return [Candidate(o, "team", "value") for o in ctx.teams]
        if t is ArgType.POS:
            return [Candidate("~ ~ ~", "your position", "value")]
        if t is ArgType.GAMERULE:
            return [Candidate(r, data.GAMERULES[r], "value") for r in data.GAMERULES]
        return [Candidate(v, "", "value") for v in _STATIC_VALUES.get(t, [])]  # type: ignore[arg-type]

    @staticmethod
    def _filter(candidates: list[Candidate], partial: str) -> list[Candidate]:
        needle = partial.lower().removeprefix("minecraft:")
        seen: set[str] = set()
        out = []
        for c in candidates:
            key = c.text.lower()
            if key in seen or not key.removeprefix("minecraft:").startswith(needle):
                continue
            seen.add(key)
            out.append(c)
        # Players keep their server order; everything else is alphabetical within its kind.
        out.sort(key=lambda c: (_KIND_ORDER.get(c.kind, 2), "" if c.kind == "player" else c.text.lower()))
        return out[:MAX_CANDIDATES]

    # -- hints -------------------------------------------------------------------------

    def _current_node(self, states: list[_State], partial: str) -> tuple[Node | None, _State | None]:
        """The grammar node the cursor is on, and the state it hangs off (for the usage line)."""
        for state in states:
            if state.pending or state.greedy:
                return state.node, state
        needle = partial.lower()
        fallback: tuple[Node | None, _State | None] = (None, states[0] if states else None)
        for state in states:
            for child in state.node.children:
                if child.is_literal:
                    if needle and child.literal.lower().startswith(needle):  # type: ignore[union-attr]
                        return child, state
                elif child.type is not ArgType.COMMAND and fallback[0] is None:
                    fallback = (child, state)
        # Only fixed words follow: no single "current" node; the usage line lists them all.
        return fallback

    @staticmethod
    def _usage(state: _State, current: Node | None) -> str:
        parts = [n.label() if not n.is_literal else n.literal for n in state.path if n.literal is not None or n.arg]
        if state.pending or state.greedy:
            parts[-1] = f"*{parts[-1]}*"
            return " ".join(parts)  # type: ignore[arg-type]
        node = state.node
        if current is not None:
            parts.append(f"*{current.label()}*")
            node = current
        # Continue along the first branch to show what comes next.
        for _ in range(10):
            if not node.children:
                break
            literals = [c for c in node.children if c.is_literal]
            if len(literals) > 1:
                parts.append("(" + "|".join(c.literal for c in literals[:6]) + ")")  # type: ignore[misc]
                break
            node = node.children[0]
            parts.append(node.label())
        return " ".join(p for p in parts if p)
