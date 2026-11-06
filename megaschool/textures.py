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

GRASS = np.array([145, 189, 89]) / 255.0      # plains grass colour
FOLIAGE = np.array([119, 171, 47]) / 255.0    # plains foliage colour
WATER = np.array([63, 118, 228]) / 255.0

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
}
EMISSIVE = {"ochre_froglight", "pearlescent_froglight", "verdant_froglight", "sea_lantern", "glowstone",
            "shroomlight", "lantern", "redstone_lamp[lit=true]", "jack_o_lantern"}


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
    if base.endswith("_slab") or base.endswith("_stairs"):
        return faces_for(base.rsplit("_", 1)[0].replace("brick", "bricks"))
    if base.endswith("_wall"):
        return faces_for(base[:-5] + "s")
    if base.endswith("_bars"):
        return faces_for(base)
    m = np.zeros((16, 16, 4), np.float32)
    m[..., :3] = (1.0, 0.0, 1.0)
    m[..., 3] = 1
    return (m, m, m)


def atlas():
    """Returns (T[n_tex,16,16,4], top[n_blocks], side[], bottom[], emissive[], cutout[])."""
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
    return (np.stack(texs), np.array(top), np.array(side), np.array(bot), np.array(emi), np.array(cut))
