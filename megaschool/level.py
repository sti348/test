"""level.dat for a superflat world (1.20.1 format; newer versions upgrade it)."""
from __future__ import annotations

import time

import nbt
from nbt import Byte, Double, Float, Int, List, Long

GAME_RULES = {
    "doDaylightCycle": "false",
    "doWeatherCycle": "false",
    "doMobSpawning": "false",
    "doPatrolSpawning": "false",
    "doTraderSpawning": "false",
    "doInsomnia": "false",
    "doFireTick": "false",
    "mobGriefing": "false",
    "randomTickSpeed": "0",
    "spawnRadius": "0",
    "keepInventory": "true",
    "announceAdvancements": "false",
    "commandBlockOutput": "false",
}


def flat_generator(min_y=-1024, ground=-61):
    """Superflat columns that meet the generated map: grass at `ground` on two
    dirt layers on stone, bedrock at the (extended) bottom of the world."""
    layers = [("minecraft:bedrock", 1), ("minecraft:stone", ground - min_y - 3), ("minecraft:dirt", 2),
              ("minecraft:grass_block", 1)]
    return {
        "type": "minecraft:flat",
        "settings": {
            "biome": "minecraft:plains",
            "features": Byte(0),
            "lakes": Byte(0),
            "layers": List([{"block": b, "height": Int(h)} for b, h in layers]),
            "structure_overrides": List([], elem_tag=8),
        },
    }


def write_level_dat(path, name, spawn, angle=180.0, day_time=1000, datapacks=("vanilla",), seed=20260901):
    sx, sy, sz = spawn
    data = {
        "DataVersion": Int(3465),
        "version": Int(19133),
        "Version": {"Id": Int(3465), "Name": "1.20.1", "Series": "main", "Snapshot": Byte(0)},
        "LevelName": name,
        "GameType": Int(1),
        "Difficulty": Byte(0),
        "DifficultyLocked": Byte(0),
        "hardcore": Byte(0),
        "allowCommands": Byte(1),
        "initialized": Byte(1),
        "LastPlayed": Long(int(time.time() * 1000)),
        "SpawnX": Int(sx), "SpawnY": Int(sy), "SpawnZ": Int(sz),
        "SpawnAngle": Float(angle),
        "Time": Long(day_time),
        "DayTime": Long(day_time),
        "raining": Byte(0), "rainTime": Int(10 ** 8),
        "thundering": Byte(0), "thunderTime": Int(10 ** 8),
        "clearWeatherTime": Int(10 ** 8),
        "WanderingTraderSpawnChance": Int(25),
        "WanderingTraderSpawnDelay": Int(24000),
        "WasModded": Byte(0),
        "ServerBrands": List(["vanilla"]),
        "BorderCenterX": Double(0.0), "BorderCenterZ": Double(0.0),
        "BorderSize": Double(59999968.0),
        "BorderSafeZone": Double(5.0), "BorderWarningBlocks": Double(5.0),
        "BorderWarningTime": Double(15.0), "BorderDamagePerBlock": Double(0.2),
        "BorderSizeLerpTarget": Double(59999968.0), "BorderSizeLerpTime": Long(0),
        "GameRules": dict(GAME_RULES),
        "DataPacks": {"Enabled": List(list(datapacks)), "Disabled": List([], elem_tag=8)},
        "DragonFight": {"NeedsStateScanning": Byte(1), "DragonKilled": Byte(0), "PreviouslyKilled": Byte(0)},
        "WorldGenSettings": {
            "seed": Long(seed),
            "generate_features": Byte(0),
            "bonus_chest": Byte(0),
            "dimensions": {
                "minecraft:overworld": {"type": "minecraft:overworld", "generator": flat_generator()},
                "minecraft:the_nether": {"type": "minecraft:the_nether", "generator": {
                    "type": "minecraft:noise", "settings": "minecraft:nether",
                    "biome_source": {"type": "minecraft:multi_noise", "preset": "minecraft:nether"}}},
                "minecraft:the_end": {"type": "minecraft:the_end", "generator": {
                    "type": "minecraft:noise", "settings": "minecraft:end",
                    "biome_source": {"type": "minecraft:the_end"}}},
            },
        },
    }
    nbt.write_gzip(path, {"Data": data})
