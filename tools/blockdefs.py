"""How the web preview draws each block state (textures come from vanilla)."""
from __future__ import annotations


def parse(state):
    if "[" in state:
        name, rest = state[:-1].split("[", 1)
        props = dict(kv.split("=") for kv in rest.split(","))
    else:
        name, props = state, {}
    return name, props


CUBE_TEX = {
    "dirt": "dirt", "coarse_dirt": "coarse_dirt", "rooted_dirt": "rooted_dirt", "stone_bricks": "stone_bricks",
    "mossy_stone_bricks": "mossy_stone_bricks", "cracked_stone_bricks": "cracked_stone_bricks",
    "cobblestone": "cobblestone", "mossy_cobblestone": "mossy_cobblestone", "smooth_stone": "smooth_stone",
    "oak_planks": "oak_planks", "spruce_planks": "spruce_planks", "glass": "glass", "stone": "stone",
}
SLAB_TEX = {"stone_brick_slab": "stone_bricks", "mossy_stone_brick_slab": "mossy_stone_bricks",
            "cobblestone_slab": "cobblestone", "spruce_slab": "spruce_planks"}
STAIR_TEX = {"stone_brick_stairs": "stone_bricks", "spruce_stairs": "spruce_planks"}
PLANT_TINT = {"short_grass": "grass", "fern": "grass"}
LEAF_TINT = {"oak_leaves": "foliage", "birch_leaves": "birch", "spruce_leaves": "spruce"}


def define(state):
    name, p = parse(state)
    d = {"shape": "cube", "tex": {}, "water": p.get("waterlogged") == "true"}
    six = lambda t: {f: t for f in ("up", "down", "north", "south", "east", "west")}
    if name in CUBE_TEX:
        d["tex"] = six(CUBE_TEX[name])
        if name == "glass":
            d["alpha"] = "cutout"
            d["opaque"] = False
    elif name == "grass_block":
        d["tex"] = {**six("grass_block_side#tinted"), "up": "grass_block_top", "down": "dirt"}
        d["tint_up"] = "grass"
    elif name == "podzol":
        d["tex"] = {**six("podzol_side"), "up": "podzol_top", "down": "dirt"}
    elif name.endswith("_log"):
        ax = p.get("axis", "y")
        side, top = name, name + "_top"
        t = six(side)
        ends = {"y": ("up", "down"), "x": ("east", "west"), "z": ("north", "south")}[ax]
        for e in ends:
            t[e] = top
        d["tex"] = t
        d["axis"] = ax
    elif name in LEAF_TINT:
        d["tex"] = six(name)
        d["tint"] = LEAF_TINT[name]
        d["alpha"] = "cutout"
        d["leaves"] = True
    elif name in SLAB_TEX:
        d["shape"] = "slab_" + p.get("type", "bottom")
        d["tex"] = six(SLAB_TEX[name])
        d["opaque"] = False
    elif name in STAIR_TEX:
        d["shape"] = "stairs"
        d["facing"] = p.get("facing", "north")
        d["tex"] = six(STAIR_TEX[name])
        d["opaque"] = False
    elif name.endswith("_carpet"):
        d["shape"] = "carpet"
        d["tex"] = six(name.replace("_carpet", "_wool"))
        d["opaque"] = False
    elif name in PLANT_TINT or name in ("dandelion", "poppy", "oxeye_daisy", "azure_bluet", "cornflower"):
        d["shape"] = "cross"
        d["tex"] = {"cross": name}
        if name in PLANT_TINT:
            d["tint"] = PLANT_TINT[name]
        d["opaque"] = False
    elif name == "campfire":
        d["shape"] = "campfire"
        d["lit"] = p.get("lit", "true") == "true"
        d["tex"] = {"log": "campfire_log_lit" if d["lit"] else "campfire_log", "fire": "campfire_fire"}
        d["opaque"] = False
    elif name == "lantern":
        d["shape"] = "lantern"
        d["tex"] = {"lantern": "lantern"}
        d["opaque"] = False
    elif name == "barrel":
        d["tex"] = {**six("barrel_side"), "up": "barrel_top", "down": "barrel_bottom"}
    elif name == "light":
        d["shape"] = "none"
        d["opaque"] = False
    else:
        raise KeyError(f"no preview definition for {state}")
    d.setdefault("opaque", True)
    return d
