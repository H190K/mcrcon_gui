"""Tests for the Qt-free core: formatting, player parsing, storage, secrets, grammar and completion."""

import json
import subprocess
import sys

import pytest

from mcrcon_gui.core import secrets, storage
from mcrcon_gui.core.commands import CATALOG, COMMANDS
from mcrcon_gui.core.commands.grammar import C, parse_branch
from mcrcon_gui.core.completion import CompletionContext, CompletionEngine
from mcrcon_gui.core.formatting import strip_codes, to_html
from mcrcon_gui.core.models import HISTORY_LIMIT, AppSettings, ServerProfile
from mcrcon_gui.core.players import parse_help_reply, parse_list_reply

# -- architecture ----------------------------------------------------------------------


def test_core_does_not_import_qt():
    code = (
        "import sys, pkgutil, importlib, mcrcon_gui.core as c\n"
        "for m in pkgutil.walk_packages(c.__path__, 'mcrcon_gui.core.'): importlib.import_module(m.name)\n"
        "assert not any(k.startswith('PySide6') for k in sys.modules), 'core imported Qt'\n"
    )
    subprocess.run([sys.executable, "-c", code], check=True, env={**__import__("os").environ, "PYTHONPATH": sys.path[0]})


# -- formatting ------------------------------------------------------------------------


def test_strip_codes():
    assert strip_codes("§aGreen §lbold§r plain") == "Green bold plain"


def test_to_html_colours_escapes_and_resets():
    out = to_html("§c<b>&§r ok")
    assert "color:#ff5555" in out and "&lt;b&gt;&amp;" in out and out.endswith(" ok")
    assert to_html("§lbold§aplain").count("font-weight:700") == 1
    assert to_html("a\nb") == "a<br>b"


# -- players ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "reply, expected",
    [
        ("There are 3 of a max of 20 players online: Notch, Alex, Steve", (3, 20, ["Notch", "Alex", "Steve"])),
        ("There are 0 of a max of 20 players online: ", (0, 20, [])),
        ("There are 2/10 players online:\nAlex, Steve", (2, 10, ["Alex", "Steve"])),
        ("There are 2 out of maximum 50 players online.\ndefault: Alex, §cSteve", (2, 50, ["Alex", "Steve"])),
        ("There are 1 of a max of 20 players online: Notch (069a79f4-44e9-4726-a5be-fca90e38aaf5)", (1, 20, ["Notch"])),
    ],
)
def test_parse_list_reply(reply, expected):
    players = parse_list_reply(reply)
    assert (players.online, players.maximum, players.names) == expected


def test_parse_list_reply_rejects_other_text():
    assert parse_list_reply("Unknown command") is None


def test_parse_help_reply():
    vanilla = "/advancement (grant|revoke)\n/ban <targets> [<reason>]\n/warp <name>"
    bukkit = "§e/spawn: §fTeleport to spawn\n/home: Go home"
    assert parse_help_reply(vanilla) == {"advancement", "ban", "warp"}
    assert parse_help_reply(bukkit) == {"spawn", "home"}


# -- storage & secrets -----------------------------------------------------------------


def test_settings_round_trip(isolated_config):
    settings = AppSettings(theme="dark", profiles=[ServerProfile(name="A", host="mc.example.com", port=25580, password="pw")])
    settings.profiles[0].add_history("list")
    storage.save(settings)
    loaded = storage.load()
    p = loaded.profiles[0]
    assert (loaded.theme, p.name, p.host, p.port, p.password, p.history) == ("dark", "A", "mc.example.com", 25580, "pw", ["list"])
    assert not storage.config_path().with_name("config.json.tmp").exists()


def test_password_is_not_stored_in_plain_text_on_windows(isolated_config):
    storage.save(AppSettings(profiles=[ServerProfile(password="s3cret-pw")]))
    raw = storage.config_path().read_text()
    if sys.platform == "win32":
        assert "s3cret-pw" not in raw
        assert '"scheme": "dpapi"' in raw


def test_password_dropped_when_not_remembered(isolated_config):
    storage.save(AppSettings(profiles=[ServerProfile(password="pw", remember_password=False)]))
    data = json.loads(storage.config_path().read_text())
    assert data["profiles"][0]["password"] == {"scheme": "none", "data": ""}


def test_migrates_v1_config(isolated_config):
    storage.config_path().parent.mkdir(parents=True)
    v1 = {"host": "10.0.0.5", "port": 25576, "password": "pw", "remember_password": True, "auto_connect": True,
          "history": ["list", "seed"], "quick_commands": [{"label": "Day", "command": "time set day"}]}
    storage.config_path().write_text(json.dumps(v1))
    s = storage.load()
    p = s.profiles[0]
    assert (p.host, p.port, p.password, p.auto_connect, p.history) == ("10.0.0.5", 25576, "pw", True, ["list", "seed"])
    assert [q.command for q in s.quick_commands] == ["time set day"]
    assert s.active_profile_id == p.id
    storage.save(s)
    assert json.loads(storage.config_path().read_text())["version"] == storage.SCHEMA_VERSION


def test_imports_legacy_config(isolated_config, tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"server_ip": "1.2.3.4", "port": "25575", "password": "your_rcon_password_here"}))
    p = storage.load().profiles[0]
    assert (p.host, p.port, p.password) == ("1.2.3.4", 25575, "")


def test_corrupt_file_falls_back_to_backup(isolated_config):
    storage.save(AppSettings(profiles=[ServerProfile(name="First")]))
    storage.save(AppSettings(profiles=[ServerProfile(name="Second")]))  # first is now the .bak
    storage.config_path().write_text("{broken")
    assert storage.load().profiles[0].name == "First"


def test_invalid_values_fall_back_to_defaults():
    s = storage.from_dict({"version": 2, "theme": "neon", "profiles": [{"host": "", "port": "abc"}], "quick_commands": "x"})
    assert s.theme == "system"
    assert (s.profiles[0].host, s.profiles[0].port) == ("localhost", 25575)
    assert len(s.quick_commands) == 9


def test_history_dedupes_and_is_capped():
    p = ServerProfile()
    for i in range(HISTORY_LIMIT + 10):
        p.add_history(f"cmd {i}")
    p.add_history("cmd 50")
    assert len(p.history) == HISTORY_LIMIT and p.history[-1] == "cmd 50" and p.history.count("cmd 50") == 1


def test_secrets_round_trip_and_garbage():
    assert secrets.unprotect(secrets.protect("hunter2")) == "hunter2"
    assert secrets.unprotect(secrets.protect("")) == ""
    assert secrets.unprotect({"scheme": "dpapi", "data": "bm90IHZhbGlk"}) == ""
    assert secrets.unprotect("legacy-plain") == "legacy-plain"


# -- grammar ---------------------------------------------------------------------------


def test_every_catalog_command_parses_and_names_are_unique():
    names = [n for c in COMMANDS for n in (c.name, *c.aliases)]
    assert len(names) == len(set(names)) == len(CATALOG)
    assert len(COMMANDS) >= 60


def test_grammar_rejects_unknown_types():
    with pytest.raises(ValueError):
        parse_branch("<x:spaceship>")


def test_grammar_merges_branches():
    cmd = C("time", "set <v:timespec>", "add <t:time>", "query (daytime|day)")
    assert [c.literal for c in cmd.root.children] == ["set", "add", "query"]


# -- completion ------------------------------------------------------------------------

ENGINE = CompletionEngine()
CTX = CompletionContext(players=["player1", "Alex", "Notch"], extra_commands={"warp", "spawn"})


def texts(line: str, ctx: CompletionContext = CTX) -> list[str]:
    return [c.text for c in ENGINE.complete(line, ctx=ctx).candidates]


@pytest.mark.parametrize(
    "line, expected",
    [
        ("/game", ["gamemode", "gamerule"]),
        ("kill play", ["player1"]),
        ("gamemode ", ["adventure", "creative", "spectator", "survival"]),
        ("gamerule keepInventory ", ["false", "true"]),
        ("gamerule randomTickSpeed ", []),
        ("say hel", []),
        ("execute as @a run gam", ["gamemode", "gamerule"]),
        ("help wh", ["whitelist"]),
        ("gamerule doM", ["doMobLoot", "doMobSpawning"]),
        ("time ", ["add", "query", "set"]),
        ("xp add Alex 5 ", ["levels", "points"]),
        ("unknowncmd x", []),
        ("wa", ["warp"]),
        ("effect give @a minecraft:spe", ["speed"]),
    ],
)
def test_completion_candidates(line, expected):
    assert texts(line) == expected


def test_player_candidates_come_before_selectors():
    out = texts("gamemode creative ")
    assert out[:3] == ["player1", "Alex", "Notch"]
    assert "@a" in out and "@e" not in out  # @e is for entities, not players


def test_teleport_offers_players_and_position():
    out = texts("tp Notch ")
    assert "Alex" in out and "~ ~ ~" in out


def test_hint_marks_current_argument():
    c = ENGINE.complete("gamemode creative ", ctx=CTX)
    assert c.hint == "gamemode <mode> *[target]*"
    assert c.description == "Set a player's game mode"
    assert ENGINE.complete("gamemode ", ctx=CTX).values == "survival | creative | adventure | spectator"


def test_replacement_span():
    line = "give Al"
    c = ENGINE.complete(line, ctx=CTX)
    assert line[c.start : c.end] == "Al"
    c = ENGINE.complete("give Alex ", ctx=CTX)
    assert c.start == c.end == len("give Alex ")


def test_settings_file_with_bom_is_read(isolated_config):
    storage.config_path().parent.mkdir(parents=True)
    storage.config_path().write_bytes(b"\xef\xbb\xbf" + json.dumps({"version": 2, "theme": "light"}).encode())
    assert storage.load().theme == "light"
