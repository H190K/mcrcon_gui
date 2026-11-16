"""Vanilla Java Edition commands, written in the grammar from :mod:`.grammar`.

Adding a command is one ``C(...)`` line. Server/plugin commands that are not listed here
are still offered as names after the app asks the server for ``help``.
"""

from __future__ import annotations

from .grammar import C, Command

_SOUND_SOURCES = "(master|music|record|weather|block|hostile|neutral|player|ambient|voice)"

COMMANDS: list[Command] = [
    C("advancement", "(grant|revoke) <targets:player> everything", "(grant|revoke) <targets:player> (only|from|through|until) <advancement:word>", desc="Give or take advancements"),
    C("ban", "<target:player> [reason:message]", desc="Ban a player"),
    C("ban-ip", "<target:word> [reason:message]", desc="Ban an IP address"),
    C("banlist", "", "ips", "players", desc="Show banned players or IPs"),
    C("clear", "[target:player] [item:item] [maxCount:int]", desc="Clear items from inventories"),
    C("clone", "<begin:pos> <end:pos> <destination:pos> [mask:(replace|masked)] [mode:(force|move|normal)]", desc="Copy blocks to another place"),
    C("damage", "<target:entity> <amount:float>", desc="Damage entities"),
    C(
        "data",
        "get entity <target:entity> [path:word]",
        "get block <pos:pos> [path:word]",
        "merge entity <target:entity> <nbt:json>",
        "merge block <pos:pos> <nbt:json>",
        "remove entity <target:entity> <path:word>",
        "remove block <pos:pos> <path:word>",
        desc="Read or change NBT data",
    ),
    C("defaultgamemode", "<mode:gamemode>", desc="Set the default game mode for new players"),
    C("deop", "<target:player>", desc="Remove operator status"),
    C("difficulty", "[level:difficulty]", desc="Show or set the difficulty"),
    C(
        "effect",
        "give <target:entity> <effect:effect> [seconds:int] [amplifier:int] [hideParticles:bool]",
        "clear [target:entity] [effect:effect]",
        desc="Add or remove status effects",
    ),
    C("enchant", "<target:entity> <enchantment:enchantment> [level:int]", desc="Enchant the held item"),
    C(
        "execute",
        "as <target:entity> run <command:command>",
        "at <target:entity> run <command:command>",
        "in <dimension:dimension> run <command:command>",
        "run <command:command>",
        desc="Run a command as / at another entity",
    ),
    C(
        "experience",
        "(add|set) <target:player> <amount:int> [unit:(levels|points)]",
        "query <target:player> <unit:(levels|points)>",
        desc="Add, set or query experience",
        aliases=("xp",),
    ),
    C("fill", "<from:pos> <to:pos> <block:block> [mode:(replace|destroy|hollow|keep|outline)]", desc="Fill a region with a block"),
    C("forceload", "add <from:coord> <to:coord>", "remove <from:coord> <to:coord>", "remove all", "query", desc="Keep chunks loaded"),
    C("function", "<name:word>", desc="Run a datapack function"),
    C("gamemode", "<mode:gamemode> [target:player]", desc="Set a player's game mode"),
    C("gamerule", "<rule:gamerule> [value:gamerule_value]", desc="Show or change a game rule"),
    C("give", "<target:player> <item:item> [count:int]", desc="Give an item to a player"),
    C("help", "[command:command_name]", desc="List commands"),
    C("kick", "<target:player> [reason:message]", desc="Kick a player"),
    C("kill", "[target:entity]", desc="Kill entities"),
    C("list", "", "uuids", desc="List online players"),
    C("locate", "(structure|biome|poi) <name:word>", desc="Find the nearest structure or biome"),
    C("me", "<action:message>", desc="Send an action message"),
    C("msg", "<target:player> <message:message>", desc="Private message a player", aliases=("tell", "w")),
    C("op", "<target:player>", desc="Make a player an operator"),
    C("pardon", "<target:word>", desc="Unban a player"),
    C("pardon-ip", "<target:word>", desc="Unban an IP address"),
    C("particle", "<name:word> [pos:pos]", desc="Spawn particles"),
    C("playsound", f"<sound:word> <source:{_SOUND_SOURCES}> <target:player> [pos:pos] [volume:float] [pitch:float]", desc="Play a sound"),
    C("recipe", "(give|take) <targets:player> <recipe:word>", desc="Give or take recipes"),
    C("reload", desc="Reload datapacks"),
    C("ride", "<target:entity> mount <vehicle:entity>", "<target:entity> dismount", desc="Make an entity ride another"),
    C("save-all", "", "flush", desc="Save the world"),
    C("save-off", desc="Turn off automatic saving"),
    C("save-on", desc="Turn on automatic saving"),
    C("say", "<message:message>", desc="Broadcast a message"),
    C(
        "scoreboard",
        "objectives list",
        "objectives add <objective:word> <criteria:word> [displayName:message]",
        "objectives remove <objective:objective>",
        "objectives setdisplay <slot:(list|sidebar|belowName)> [objective:objective]",
        "players list [target:entity]",
        "players (set|add|remove) <target:entity> <objective:objective> <score:int>",
        "players reset <target:entity> [objective:objective]",
        "players get <target:entity> <objective:objective>",
        desc="Manage scoreboard objectives and scores",
    ),
    C("seed", desc="Show the world seed"),
    C("setblock", "<pos:pos> <block:block> [mode:(destroy|keep|replace)]", desc="Place a block"),
    C("setworldspawn", "[pos:pos]", desc="Set the world spawn"),
    C("spawnpoint", "[target:player] [pos:pos]", desc="Set a player's spawn point"),
    C("spectate", "[target:entity] [player:player]", desc="Spectate an entity"),
    C("stop", desc="Stop the server"),
    C("stopsound", "<target:player>", desc="Stop sounds"),
    C("summon", "<entity:entity_type> [pos:pos]", desc="Summon an entity"),
    C("tag", "<target:entity> (add|remove) <name:word>", "<target:entity> list", desc="Manage entity tags"),
    C(
        "team",
        "list [team:team]",
        "add <team:word> [displayName:message]",
        "remove <team:team>",
        "empty <team:team>",
        "join <team:team> [members:entity]",
        "leave <members:entity>",
        "modify <team:team> color <value:color>",
        "modify <team:team> (friendlyFire|seeFriendlyInvisibles) <value:bool>",
        "modify <team:team> (nametagVisibility|deathMessageVisibility) <value:(always|never|hideForOtherTeams|hideForOwnTeam)>",
        "modify <team:team> collisionRule <value:(always|never|pushOtherTeams|pushOwnTeam)>",
        "modify <team:team> (prefix|suffix) <value:json>",
        desc="Manage teams",
    ),
    C("teammsg", "<message:message>", desc="Message your team", aliases=("tm",)),
    C(
        "teleport",
        "<destination:entity>",
        "<location:pos>",
        "<target:entity> <destination:entity>",
        "<target:entity> <location:pos>",
        desc="Teleport entities",
        aliases=("tp",),
    ),
    C("tellraw", "<target:player> <json:json>", desc="Send a JSON message"),
    C("tick", "query", "rate <rate:float>", "freeze", "unfreeze", "step [time:time]", "sprint <time:time>", desc="Control the game tick rate"),
    C("time", "set <value:timespec>", "add <time:time>", "query (daytime|gametime|day)", desc="Change or query the time"),
    C(
        "title",
        "<target:player> (clear|reset)",
        "<target:player> (title|subtitle|actionbar) <text:json>",
        "<target:player> times <fadeIn:time> <stay:time> <fadeOut:time>",
        desc="Show a title on screen",
    ),
    C("weather", "<type:weather> [duration:time]", desc="Change the weather"),
    C("whitelist", "(on|off|list|reload)", "(add|remove) <target:player>", desc="Manage the whitelist"),
    C(
        "worldborder",
        "(set|add) <distance:float> [time:int]",
        "center <x:coord> <z:coord>",
        "get",
        "damage (amount|buffer) <value:float>",
        "warning (distance|time) <value:int>",
        desc="Manage the world border",
    ),
]


def build_catalog(commands: list[Command]) -> dict[str, Command]:
    catalog: dict[str, Command] = {}
    for command in commands:
        for name in (command.name, *command.aliases):
            if name in catalog:
                raise ValueError(f"Duplicate command name {name!r}")
            catalog[name] = command
    return catalog


CATALOG = build_catalog(COMMANDS)
