"""Value lists used to complete command arguments (Java Edition, 1.21)."""

GAMEMODES = ["survival", "creative", "adventure", "spectator"]
DIFFICULTIES = ["peaceful", "easy", "normal", "hard"]
WEATHER = ["clear", "rain", "thunder"]
TIMESPEC = ["day", "night", "noon", "midnight"]
PLAYER_SELECTORS = ["@a", "@p", "@r", "@s"]
ENTITY_SELECTORS = PLAYER_SELECTORS + ["@e"]
DIMENSIONS = ["minecraft:overworld", "minecraft:the_nether", "minecraft:the_end"]
BOOLS = ["true", "false"]
COLORS = (
    "black dark_blue dark_green dark_aqua dark_red dark_purple gold gray dark_gray blue green aqua red light_purple yellow white reset"
).split()

_B, _I = "bool", "int"
GAMERULES = {
    **dict.fromkeys(
        """announceAdvancements blockExplosionDropDecay commandBlockOutput disableElytraMovementCheck disableRaids
        doDaylightCycle doEntityDrops doFireTick doImmediateRespawn doInsomnia doLimitedCrafting doMobLoot
        doMobSpawning doPatrolSpawning doTileDrops doTraderSpawning doVinesSpread doWardenSpawning doWeatherCycle
        drowningDamage enderPearlsVanishOnDeath fallDamage fireDamage forgiveDeadPlayers freezeDamage
        globalSoundEvents keepInventory lavaSourceConversion locatorBar logAdminCommands mobExplosionDropDecay
        mobGriefing naturalRegeneration projectilesCanBreakBlocks reducedDebugInfo sendCommandFeedback
        showDeathMessages spectatorsGenerateChunks tntExplodes tntExplosionDropDecay universalAnger
        waterSourceConversion""".split(),
        _B,
    ),
    **dict.fromkeys(
        """commandModificationBlockLimit maxCommandChainLength maxCommandForkCount maxEntityCramming minecartMaxSpeed
        playersNetherPortalCreativeDelay playersNetherPortalDefaultDelay playersSleepingPercentage randomTickSpeed
        snowAccumulationHeight spawnChunkRadius spawnRadius""".split(),
        _I,
    ),
}

_TIERS = ["diamond", "netherite", "iron", "golden", "stone", "wooden"]
_TOOLS = ["sword", "pickaxe", "axe", "shovel", "hoe"]
_ARMOR = ["helmet", "chestplate", "leggings", "boots"]

BLOCKS = sorted(
    set(
        """air stone cobblestone dirt grass_block sand gravel obsidian bedrock glass oak_log oak_planks torch lantern
        crafting_table furnace chest ender_chest shulker_box red_bed tnt redstone_torch repeater comparator piston
        sticky_piston observer hopper dispenser dropper lever stone_button command_block barrier structure_block spawner
        water lava glowstone sea_lantern end_stone netherrack deepslate white_wool white_concrete oak_leaves slime_block
        honey_block magma_block ice packed_ice blue_ice snow_block hay_block bookshelf anvil enchanting_table
        brewing_stand iron_block gold_block diamond_block emerald_block netherite_block stone_bricks bricks
        quartz_block terracotta prismarine glass_pane iron_bars ladder scaffolding oak_fence oak_door oak_trapdoor
        oak_stairs oak_slab campfire soul_sand end_portal_frame light beacon""".split()
    )
)

ITEMS = sorted(
    set(
        [f"{t}_{tool}" for t in _TIERS for tool in _TOOLS]
        + [f"{t}_{a}" for t in ("diamond", "netherite", "iron", "golden", "chainmail", "leather") for a in _ARMOR]
        + """diamond netherite_ingot netherite_scrap iron_ingot gold_ingot copper_ingot emerald lapis_lazuli quartz
        amethyst_shard echo_shard heart_of_the_sea nether_star dragon_egg dragon_breath golden_apple
        enchanted_golden_apple golden_carrot bow arrow spectral_arrow crossbow trident shield elytra mace
        totem_of_undying ender_pearl ender_eye blaze_rod blaze_powder bread apple carrot potato baked_potato
        cooked_beef cooked_porkchop cooked_chicken cooked_mutton cooked_salmon cake cookie pumpkin_pie milk_bucket
        water_bucket lava_bucket bucket fishing_rod compass recovery_compass clock map book writable_book
        enchanted_book name_tag saddle lead flint_and_steel redstone experience_bottle firework_rocket string stick
        coal charcoal wheat wheat_seeds bone_meal bone leather feather snowball egg spyglass potion splash_potion
        lingering_potion shears brush wind_charge""".split()
        + BLOCKS
    )
)

EFFECTS = """speed slowness haste mining_fatigue strength instant_health instant_damage jump_boost nausea regeneration
resistance fire_resistance water_breathing invisibility blindness night_vision hunger weakness poison wither
health_boost absorption saturation glowing levitation luck unluck slow_falling conduit_power dolphins_grace bad_omen
hero_of_the_village darkness trial_omen raid_omen wind_charged weaving oozing infested""".split()

ENCHANTMENTS = """sharpness smite bane_of_arthropods knockback fire_aspect looting sweeping_edge efficiency silk_touch
unbreaking fortune mending protection fire_protection blast_protection projectile_protection thorns respiration
aqua_affinity depth_strider frost_walker feather_falling soul_speed swift_sneak power punch flame infinity
luck_of_the_sea lure loyalty impaling riptide channeling multishot piercing quick_charge density breach wind_burst
binding_curse vanishing_curse""".split()

ENTITY_TYPES = """zombie skeleton creeper spider cave_spider enderman witch slime magma_cube blaze ghast wither_skeleton
piglin piglin_brute hoglin zoglin zombified_piglin warden phantom drowned husk stray bogged breeze pillager vindicator
evoker ravager guardian elder_guardian shulker silverfish endermite wither ender_dragon villager wandering_trader
iron_golem snow_golem cow pig sheep chicken horse donkey mule wolf cat ocelot parrot rabbit fox panda polar_bear bee
axolotl goat frog allay camel sniffer armadillo dolphin squid glow_squid turtle cod salmon bat llama mooshroom strider
armor_stand item_frame boat minecart tnt lightning_bolt firework_rocket experience_orb item""".split()
