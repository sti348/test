"""Block textures for the preview renderer, read from a Minecraft client jar
extracted into build/tex (never committed)."""
from __future__ import annotations

import functools
import os

import numpy as np
from PIL import Image

import anvil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, "build", "tex", "assets", "minecraft", "textures", "block")

GRASS = np.array([0x5a, 0x8f, 0x5e]) / 255.0  # twilight grass (twilight.py GRASS)
FOLIAGE = np.array([0x4f, 0x8a, 0x55]) / 255.0  # twilight foliage
WATER = np.array([0x3b, 0x5f, 0xb0]) / 255.0

SPECIAL = {
    "grass_block": (("grass_block_top", GRASS), "grass_block_side", "dirt"),
    "smooth_sandstone": ("sandstone_top",) * 3,
    "cut_sandstone": ("sandstone_top", "cut_sandstone", "sandstone_top"),
    "smooth_quartz": ("quartz_block_bottom",) * 3,
    "smooth_stone_slab": ("smooth_stone",) * 3,
    "stone_brick_wall": ("stone_bricks",) * 3,
    "quartz_block": ("quartz_block_top", "quartz_block_side", "quartz_block_bottom"),
    "quartz_pillar": ("quartz_pillar_top", "quartz_pillar", "quartz_pillar_top"),
    "water": (("water_still", WATER),) * 3,
    "oak_leaves": (("oak_leaves", FOLIAGE),) * 3,
    "dark_oak_leaves": (("dark_oak_leaves", FOLIAGE),) * 3,
    "birch_leaves": (("birch_leaves", np.array([128, 167, 85]) / 255.0),) * 3,
    "bookshelf": ("oak_planks", "bookshelf", "oak_planks"),
    "sandstone": ("sandstone_top", "sandstone", "sandstone_bottom"),
    "grass": (("short_grass", GRASS),) * 3,
    "short_grass": (("short_grass", GRASS),) * 3,
    "fern": (("fern", GRASS),) * 3,
    "tall_grass": (("tall_grass_bottom", GRASS),) * 3,
    "large_fern": (("large_fern_bottom", GRASS),) * 3,
    "lily_pad": (("lily_pad", np.array([32, 128, 48]) / 255.0),) * 3,
    "lava": ("lava_still",) * 3,
    "magma_block": ("magma",) * 3,
    "fire": ("fire_0",) * 3,
    "soul_fire": ("soul_fire_0",) * 3,
    "cave_vines": ("cave_vines",) * 3,
    "cave_air": ("glass",) * 3,
    "azalea": ("azalea_top", "azalea_side", "azalea_top"),
}
EMISSIVE = {"ochre_froglight", "pearlescent_froglight", "verdant_froglight", "sea_lantern", "glowstone",
            "shroomlight", "lantern", "redstone_lamp[lit=true]", "jack_o_lantern", "lava", "magma_block",
            "soul_lantern", "soul_fire", "fire", "nether_portal", "crying_obsidian", "end_rod", "glow_lichen"}


def _load(name):
    p = os.path.join(TEX, name + ".png")
    if not os.path.exists(p):
        return None
    im = Image.open(p).convert("RGBA")
    a = np.asarray(im, np.float32) / 255.0
    return a[:16, :16]          # first frame of animated strips


def _resolve(spec):
    tint = None
    if isinstance(spec, tuple):
        spec, tint = spec
    t = _load(spec)
    if t is None:
        return None
    t = t.copy()
    if tint is not None:
        t[..., :3] *= tint
    return t


_STRIP = ("_slab", "_stairs", "_wall", "_fence", "_carpet", "_pane", "_trapdoor", "_door")


@functools.lru_cache(None)
def faces_for(base):
    if base in SPECIAL:
        return tuple(_resolve(s) for s in SPECIAL[base])
    for cand in ((base,) * 3, (base + "_top", base + "_side", base + "_bottom"),
                 (base + "_top", base + "_side", base + "_top"), (base + "_top", base, base + "_top"),
                 (base + "_top", base, base + "_bottom")):
        ts = [_load(c) for c in cand]
        if all(t is not None for t in ts):
            return tuple(ts)
    if base.endswith("_door"):
        t = _load(base + "_bottom")
        if t is not None:
            return (t, t, t)
    if base.endswith("_carpet"):
        for cand in (base[:-7] + "_wool", base[:-7] + "_block"):
            if _load(cand) is not None:
                return faces_for(cand)
    if base.endswith("_pane"):
        return faces_for(base[:-5])
    for suf in _STRIP:
        if base.endswith(suf):
            root = base[: -len(suf)]
            for cand in (root, root + "s", root + "_planks", root + "_block"):
                if cand in SPECIAL or _load(cand) is not None or _load(cand + "_top") is not None:
                    return faces_for(cand)
    m = np.zeros((16, 16, 4), np.float32)
    m[..., :3] = (1.0, 0.0, 1.0)
    m[..., 3] = 1
    return (m, m, m)


FULL = (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)


def shape_for(name):
    """Collision-ish box (x0,y0,z0,x1,y1,z1) inside the cell for partial blocks."""
    base = name.split("[")[0].split(":")[-1]
    props = {}
    if "[" in name:
        for kv in name[name.index("[") + 1:-1].split(","):
            k, v = kv.split("=")
            props[k] = v
    t = 3 / 16
    if base.endswith("_slab"):
        return {"bottom": (0, 0, 0, 1, .5, 1), "top": (0, .5, 0, 1, 1, 1)}.get(props.get("type", "bottom"), FULL)
    if base.endswith("_carpet") or base == "lily_pad":
        return (0, 0, 0, 1, 1 / 16, 1)
    if base.endswith("_pane") or base == "iron_bars":
        ew = props.get("east") == "true" or props.get("west") == "true"
        ns = props.get("north") == "true" or props.get("south") == "true"
        if ew and not ns:
            return (0, 0, 7 / 16, 1, 1, 9 / 16)
        if ns and not ew:
            return (7 / 16, 0, 0, 9 / 16, 1, 1)
        if ew and ns:
            return (0, 0, 7 / 16, 1, 1, 9 / 16)
        return (7 / 16, 0, 7 / 16, 9 / 16, 1, 9 / 16)
    if base.endswith("_door"):
        f = props.get("facing", "north")
        return {"south": (0, 0, 0, 1, 1, t), "north": (0, 0, 1 - t, 1, 1, 1),
                "east": (0, 0, 0, t, 1, 1), "west": (1 - t, 0, 0, 1, 1, 1)}[f]
    if base.endswith("_trapdoor"):
        if props.get("open") == "true":
            f = props.get("facing", "north")
            return {"south": (0, 0, 0, 1, 1, t), "north": (0, 0, 1 - t, 1, 1, 1),
                    "east": (0, 0, 0, t, 1, 1), "west": (1 - t, 0, 0, 1, 1, 1)}[f]
        return (0, 1 - t, 0, 1, 1, 1) if props.get("half") == "top" else (0, 0, 0, 1, t, 1)
    if base.endswith("_wall"):
        return (.25, 0, .25, .75, 1, .75)
    if base.endswith("_fence"):
        return (6 / 16, 0, 6 / 16, 10 / 16, 1, 10 / 16)
    if base in ("lantern", "soul_lantern"):
        return (5 / 16, .05, 5 / 16, 11 / 16, .6, 11 / 16)
    return FULL


def atlas():
    """Returns (T[n_tex,16,16,4], top[n_blocks], side[], bottom[], emissive[], cutout[], shapes[n,6])."""
    names = anvil.all_names()
    texs = []
    top, side, bot, emi, cut = [], [], [], [], []
    for n in names:
        base = n.split("[")[0].split(":")[1]
        if base == "air":
            top.append(0); side.append(0); bot.append(0); emi.append(False); cut.append(True)
            if not texs:
                texs.append(np.zeros((16, 16, 4), np.float32))
            continue
        ft = faces_for(base)
        ids = []
        for t in ft:
            texs.append(t)
            ids.append(len(texs) - 1)
        top.append(ids[0]); side.append(ids[1]); bot.append(ids[2])
        emi.append(base in EMISSIVE or n.split(":")[1] in EMISSIVE)
        cut.append(bool(min(t[..., 3].min() for t in ft) < 0.5))
    shapes = np.array([shape_for(n) for n in names], np.float64)
    return (np.stack(texs), np.array(top), np.array(side), np.array(bot), np.array(emi), np.array(cut), shapes)
