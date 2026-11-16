"""Parse replies of the ``list`` and ``help`` commands."""

from __future__ import annotations

import re

from .formatting import strip_codes
from .models import PlayerList

# Covers vanilla ("There are 3 of a max of 20 players online: a, b"),
# older vanilla ("3/20") and Bukkit/Paper ("There are 3 out of maximum 20 players online.").
_LIST = re.compile(r"There are (\d+)\D+?(\d+) players online[:.]?\s*(.*)", re.IGNORECASE | re.DOTALL)
_HELP_LINE = re.compile(r"^\s*/?([A-Za-z0-9_:\-]+)")


def parse_list_reply(text: str) -> PlayerList | None:
    match = _LIST.search(strip_codes(text))
    if not match:
        return None
    online, maximum, rest = match.groups()
    names = []
    # Paper puts groups on their own lines ("default: Alex, Steve"); take everything after a colon.
    for chunk in re.split(r"[,\n]", rest):
        chunk = chunk.split(":", 1)[-1] if ":" in chunk and not chunk.strip().startswith("(") else chunk
        name = re.sub(r"\s*\(.*?\)\s*$", "", chunk).strip()
        if name and re.fullmatch(r"[A-Za-z0-9_.\-*]{1,32}", name):
            names.append(name)
    return PlayerList(int(online), int(maximum), names)


def parse_help_reply(text: str) -> set[str]:
    commands = set()
    for line in strip_codes(text).splitlines():
        match = _HELP_LINE.match(line)
        if match and line.lstrip().startswith("/"):
            commands.add(match.group(1).rstrip(":").lower())
    return commands
