"""A tiny grammar for describing command syntax, used for completion and hints.

Each command is written as one or more *branches*, space-separated tokens:

    literal           a fixed word, e.g. ``set``
    (a|b|c)           one of several fixed words
    <name:type>       a required argument
    [name:type]       an optional argument
    <name:type...>    a greedy argument that swallows the rest of the line

``type`` is an :class:`ArgType` name in lower case, or ``(a|b)`` for an inline choice.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class ArgType(Enum):
    PLAYER = "player"
    ENTITY = "entity"
    GAMEMODE = "gamemode"
    DIFFICULTY = "difficulty"
    GAMERULE = "gamerule"
    GAMERULE_VALUE = "gamerule_value"
    ITEM = "item"
    BLOCK = "block"
    EFFECT = "effect"
    ENCHANTMENT = "enchantment"
    ENTITY_TYPE = "entity_type"
    BOOL = "bool"
    INT = "int"
    FLOAT = "float"
    WORD = "word"
    MESSAGE = "message"
    JSON = "json"
    POS = "pos"
    COORD = "coord"
    TIME = "time"
    TIMESPEC = "timespec"
    WEATHER = "weather"
    DIMENSION = "dimension"
    COLOR = "color"
    OBJECTIVE = "objective"
    TEAM = "team"
    COMMAND = "command"
    COMMAND_NAME = "command_name"
    CHOICE = "choice"  # inline (a|b) value set


GREEDY_TYPES = {ArgType.MESSAGE, ArgType.JSON, ArgType.COMMAND}


@dataclass
class Node:
    literal: str | None = None
    arg: str | None = None
    type: ArgType | None = None
    choices: tuple[str, ...] = ()
    optional: bool = False
    greedy: bool = False
    children: list["Node"] = field(default_factory=list)

    @property
    def is_literal(self) -> bool:
        return self.literal is not None

    def label(self) -> str:
        if self.literal is not None:
            return self.literal
        suffix = "..." if self.greedy else ""
        return f"[{self.arg}{suffix}]" if self.optional else f"<{self.arg}{suffix}>"

    def key(self) -> tuple:
        return (self.literal, self.arg, self.type, self.choices)


@dataclass
class Command:
    name: str
    root: Node
    description: str = ""
    aliases: tuple[str, ...] = ()


_TOKEN = re.compile(r"(\([^)]*\)|<[^>]*>|\[[^\]]*\]|\S+)")


def _parse_token(token: str) -> list[Node]:
    """One DSL token -> one node, or several sibling literal nodes for ``(a|b)``."""
    if token.startswith("(") and token.endswith(")"):
        return [Node(literal=word) for word in token[1:-1].split("|")]
    if token[0] in "<[":
        optional = token[0] == "["
        inner = token[1:-1]
        greedy = inner.endswith("...")
        inner = inner.removesuffix("...")
        name, _, type_name = inner.partition(":")
        if type_name.startswith("("):
            node = Node(arg=name, type=ArgType.CHOICE, choices=tuple(type_name[1:-1].split("|")), optional=optional)
        else:
            try:
                arg_type = ArgType(type_name or "word")
            except ValueError as exc:
                raise ValueError(f"Unknown argument type {type_name!r} in {token!r}") from exc
            node = Node(arg=name, type=arg_type, optional=optional, greedy=greedy or arg_type in GREEDY_TYPES)
        return [node]
    return [Node(literal=token)]


def parse_branch(branch: str) -> list[list[Node]]:
    """Return the branch as a list of steps; each step is a list of alternative nodes."""
    return [_parse_token(t) for t in _TOKEN.findall(branch)]


def _merge(parent: Node, steps: list[list[Node]]) -> None:
    if not steps:
        return
    first, rest = steps[0], steps[1:]
    for alternative in first:
        existing = next((c for c in parent.children if c.key() == alternative.key()), None)
        if existing is None:
            parent.children.append(alternative)
            existing = alternative
        _merge(existing, [[Node(**{**n.__dict__, "children": []}) for n in step] for step in rest])


def C(name: str, *branches: str, desc: str = "", aliases: tuple[str, ...] = ()) -> Command:  # noqa: N802
    root = Node(literal=name)
    for branch in branches or ("",):
        _merge(root, parse_branch(branch))
    return Command(name, root, desc, aliases)
