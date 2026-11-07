"""Twilight-Forest-style twilight for the whole world, as data-pack overrides.

The overworld dimension type gets ambient light (so even unlit ground stays
readable, like the Twilight Forest's perpetual dusk) and the plains biome -
the only biome the map uses - gets violet sky and fog, deep teal grass and
leaves, dark blue water and slowly drifting glints like fireflies.

Every game version has its own file format, so each override is the
*vanilla* file of that format group (vendored from misode/mcmeta in
vanilla/) with only those values changed, shipped as a pack overlay for the
matching pack formats.  Chunks keep referencing minecraft:plains, so with the
data pack disabled the world simply looks vanilla again."""
from __future__ import annotations

import copy
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
VANILLA = os.path.join(HERE, "vanilla")

AMBIENT = 0.2                 # vanilla overworld 0.0, nether 0.1
# No height limit: the overworld runs from -1024 to the game's maximum of 2032,
# the Nether from 0 to 1024 (vanilla: -64..320 and 0..256).
OW_MIN_Y, OW_HEIGHT = -1024, 3056
NETHER_MIN_Y, NETHER_HEIGHT = 0, 1024
NETHER_AMBIENT = 0.35         # vanilla Nether 0.1
SKY = "#8a7cd8"               # lavender-violet (the game darkens it with the time of day)
FOG = "#a497d8"
WATER = "#3b5fb0"
WATER_FOG = "#1a1f4a"
GRASS = "#5a8f5e"             # deep teal-green, like the Twilight Forest
FOLIAGE = "#4f8a55"
AMBIENT_COLOR = "#3a3352"     # 1.21.11+: tint of the darkest light
PARTICLE = "minecraft:glow"   # exists in every supported version; drifts like a firefly
PARTICLE_P = 0.0012

# (first pack format, last pack format, vanilla file) - groups of identical vanilla files
DIM_GROUPS = [(15, 40, "1.20.1"), (41, 79, "1.20.5"), (80, 93, "1.21.6"), (94, 100, "1.21.11"),
              (101, 120, "26.1"), (121, 1000, "26.3")]
BIOME_GROUPS = [(15, 17, "1.20.1"), (18, 56, "1.20.2"), (57, 60, "1.21.2"), (61, 70, "1.21.4"),
                (71, 93, "1.21.5"), (94, 120, "1.21.11"), (121, 1000, "26.3")]


def _hex(s):
    return int(s.lstrip("#"), 16)


def dimension(ver):
    d = json.load(open(os.path.join(VANILLA, f"{ver}_dimension_type_overworld.json")))
    d = copy.deepcopy(d)
    d["ambient_light"] = AMBIENT
    d["min_y"], d["height"], d["logical_height"] = OW_MIN_Y, OW_HEIGHT, OW_HEIGHT
    if "attributes" in d:
        # only touch attributes this version already defines (1.21.11 has no
        # ambient_light_color - an unknown key stops the world from loading)
        a = d["attributes"]
        for k, v in (("minecraft:visual/ambient_light_color", AMBIENT_COLOR),
                     ("minecraft:visual/fog_color", FOG), ("minecraft:visual/sky_color", SKY)):
            if k in a:
                a[k] = v
    return d


NETHER_GROUPS = [(15, 93, "1.20.1"), (94, 100, "1.21.11"), (101, 120, "26.1"), (121, 1000, "26.3")]


def nether(ver):
    d = copy.deepcopy(json.load(open(os.path.join(VANILLA, f"{ver}_dimension_type_the_nether.json"))))
    d["min_y"], d["height"], d["logical_height"] = NETHER_MIN_Y, NETHER_HEIGHT, NETHER_HEIGHT
    # vanilla 0.1: inspected in Horizon, the Nether school's unlit walls read as black even
    # 40 blocks away; like the overworld's twilight, a higher floor of ambient light
    d["ambient_light"] = NETHER_AMBIENT
    return d


def biome(ver):
    d = copy.deepcopy(json.load(open(os.path.join(VANILLA, f"{ver}_worldgen_biome_plains.json"))))
    e = d["effects"]
    if "attributes" not in d:              # <= 1.21.10: colours are integers in "effects"
        e["sky_color"] = _hex(SKY)
        e["fog_color"] = _hex(FOG)
        e["water_color"] = _hex(WATER)
        e["water_fog_color"] = _hex(WATER_FOG)
        e["grass_color"] = _hex(GRASS)
        e["foliage_color"] = _hex(FOLIAGE)
        e["particle"] = {"options": {"type": PARTICLE}, "probability": PARTICLE_P}
    else:                                  # 1.21.11+: visual attributes, hex strings
        a = d["attributes"]
        a["minecraft:visual/sky_color"] = SKY
        a["minecraft:visual/fog_color"] = FOG
        a["minecraft:visual/water_fog_color"] = WATER_FOG
        parts = [{"particle": {"type": PARTICLE}, "probability": PARTICLE_P}]
        a["minecraft:visual/ambient_particles"] = parts if ver == "1.21.11" else {"argument": parts, "modifier": "append"}
        e["water_color"] = WATER
        e["grass_color"] = GRASS
        e["foliage_color"] = FOLIAGE
    return d


def _w(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1)


def write(dst):
    """Write base files (pack format 15 = 1.20.1) and overlays; returns overlay entries."""
    entries = []
    for lo, hi, ver in DIM_GROUPS:
        root = dst if lo == 15 else os.path.join(dst, f"tw_dim_{lo}")
        _w(os.path.join(root, "data", "minecraft", "dimension_type", "overworld.json"), dimension(ver))
        if lo != 15:
            entries.append({"formats": [lo, hi], "min_format": lo, "max_format": hi, "directory": f"tw_dim_{lo}"})
    for lo, hi, ver in NETHER_GROUPS:
        root = dst if lo == 15 else os.path.join(dst, f"tw_nether_{lo}")
        _w(os.path.join(root, "data", "minecraft", "dimension_type", "the_nether.json"), nether(ver))
        if lo != 15:
            entries.append({"formats": [lo, hi], "min_format": lo, "max_format": hi, "directory": f"tw_nether_{lo}"})
    for lo, hi, ver in BIOME_GROUPS:
        root = dst if lo == 15 else os.path.join(dst, f"tw_biome_{lo}")
        _w(os.path.join(root, "data", "minecraft", "worldgen", "biome", "plains.json"), biome(ver))
        if lo != 15:
            entries.append({"formats": [lo, hi], "min_format": lo, "max_format": hi, "directory": f"tw_biome_{lo}"})
    return entries
