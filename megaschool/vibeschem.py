"""Bridge to VibeSchem (github.com/SimoneRecchia/minecraft-schematic-lab).

VibeSchem compiles BuildSpecs: it validates every block against the target
version (1.20.1 here) and sets block states the way the game would (glass
panes and walls connect, doors get their upper half, stairs get corners,
rotated copies rotate their states).  We use it for

  * facade modules: one floor x one bay of every facade style, compiled in
    a 3x3 tiling and in all four orientations; the centre tile is cut out,
    so its edge states match the repetition it is tiled into;
  * props and small buildings: trees, lamps, benches, bike sheds, hoops,
    the guard house and the shops outside the gate.

`python3 vibeschem.py sync` talks to a running VibeSchem server and writes
vibeschem_cache.json.gz (committed), so generate.py never needs VibeSchem.
`python3 vibeschem.py export <dir>` exports .schem / .litematic files of the
landmark builds for players."""
from __future__ import annotations

import base64
import gzip
import json
import os
import sys
import urllib.request
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "vibeschem_cache.json.gz")
SPECS = os.path.join(HERE, "vibeschem_specs")
VERSION = "1.20.1"
URL = os.environ.get("VIBESCHEM_URL", "http://127.0.0.1:8765")

# ------------------------------------------------------------------ client


def _req(path, body=None, raw=False):
    data = None if body is None else json.dumps(body).encode()
    r = urllib.request.Request(URL + path, data=data, headers={"content-type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(r, timeout=300) as f:
            b = f.read()
            if f.headers.get("content-encoding") == "gzip":
                b = gzip.decompress(b)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"VibeSchem {path}: {e.code} {e.read().decode()[:3000]}")
    return b if raw else json.loads(b)


def compile_spec(spec):
    """-> (V[y,z,x] palette indices, palette list, origin [x,y,z])."""
    out = _req("/api/build", {"spec": spec, "newProject": False})
    h = out["build"]
    sx, sy, sz = h["size"]
    vol = np.frombuffer(_req("/api/build/volume?buildId=" + h["buildId"], raw=True), "<u2")
    V = vol.reshape(sy, sz, sx).copy()
    return V, h["palette"], h["origin"], out["summary"]


def render(views="iso", size=900):
    return _req(f"/api/render.png?views={views}&size={size}", raw=True)


# ------------------------------------------------------------------ module specs
FH = 4


def _slab(name):
    return {"white_concrete": "smooth_quartz_slab", "smooth_quartz": "smooth_quartz_slab",
            "smooth_sandstone": "smooth_sandstone_slab", "polished_andesite": "polished_andesite_slab",
            "bricks": "brick_slab", "stone_bricks": "stone_brick_slab", "cut_sandstone": "cut_sandstone_slab",
            }.get(name, "smooth_stone_slab")


def scheme_palette(sc):
    n = sc.names
    door = {"dark_oak_planks": "dark_oak_door"}.get(n["door"], "spruce_door")
    return {
        "wall": n["wall"], "accent": n["accent"], "band": n["band"], "rail": n["rail"], "column": n["column"],
        "floor": n["floor"], "back": n["back"], "trim": n["trim"], "roof": n["roof"],
        "pane": "glass_pane",
        "frame": "gray_concrete" if n["wall"] != "polished_andesite" else "stone_bricks",
        "cap": _slab(n["rail"]) + "[type=bottom]",
        "sill": _slab(n["trim"]) + "[type=top]",
        "door": door,
    }


class Mod:
    """Tiny DSL: cells addressed as (d, yl, u); d=0 outermost.  Emits BuildSpec
    ops for a south-facing module (outside = +z): x = u, y = yl, z = D-1-d."""

    def __init__(self, bay, D):
        self.bay, self.D, self.ops = bay, D, []

    def box(self, d, y, u, block, oid=None):
        d0, d1 = (d, d) if isinstance(d, int) else d
        y0, y1 = (y, y) if isinstance(y, int) else y
        u0, u1 = (u, u) if isinstance(u, int) else u
        self.ops.append({"id": oid or f"op{len(self.ops)}", "type": "box",
                         "from": [u0, y0, self.D - 1 - d1], "to": [u1, y1, self.D - 1 - d0], "block": block})


def mod_corridor():
    """外廊: projecting floor ledge, solid parapet with a slab handrail, columns
    proud of everything, classroom door + transom + high windows behind."""
    m = Mod(10, 6)
    b = 9
    m.box(5, (0, 3), (0, b), "wall", "back_wall")
    m.box(4, (0, 3), (0, b), "wall", "class_wall")
    m.box((4, 5), 1, 2, "back", "door_back")
    m.box((4, 5), 2, 2, "back")
    m.box(4, 1, 2, "door[facing=south]", "door")
    m.box(4, 3, 2, "pane", "transom")
    m.box(5, 3, 2, "back")
    m.box(4, (2, 3), (4, 8), "pane", "windows")
    m.box(5, (2, 3), (4, 8), "back", "interior")
    m.box((2, 3), 0, (0, b), "floor", "corridor_floor")
    m.box(1, 0, (0, b), "band", "slab_edge")
    m.box(1, 1, (1, b), "rail", "parapet")
    m.box(1, 2, (1, b), "cap", "handrail")
    m.box(1, (1, 3), 0, "column", "column")
    m.box(0, (0, 3), 0, "column", "pilaster")
    m.box(0, 0, (1, b), "sill", "drip_ledge")
    return m


def mod_windows():
    """外窗: proud grid of pilasters + floor bands, wall infill, recessed panes
    with a dark mullion, slab sills."""
    m = Mod(8, 4)
    b = 7
    m.box(3, (0, 3), (0, b), "wall", "back_wall")
    m.box(2, (0, 3), (0, b), "wall", "inner_wall")
    m.box(1, (0, 3), (0, b), "wall", "wall")
    m.box(1, (2, 3), (2, 6), "air", "opening")
    m.box(2, (2, 3), (2, 6), "pane", "panes")
    m.box(2, (2, 3), 4, "frame", "mullion")
    m.box(3, (2, 3), (2, 6), "back", "interior")
    m.box(0, 0, (0, b), "band", "floor_band")
    m.box(0, (0, 3), 0, "column", "pilaster")
    m.box(0, 1, (2, 6), "sill", "sill")
    return m


def mod_balcony():
    """宿舍阳台: balcony slab + parapet + handrail, divider walls, glass door
    and window behind."""
    m = Mod(6, 5)
    b = 5
    m.box(4, (0, 3), (0, b), "wall", "back_wall")
    m.box(3, (0, 3), (0, b), "back")
    m.box(2, (0, 3), (0, b), "wall", "room_wall")
    m.box(2, 1, 2, "door[facing=south]", "balcony_door")
    m.box(2, (2, 3), (3, 4), "pane", "window")
    m.box(2, 3, 2, "pane", "transom")
    m.box(1, 0, (0, b), "floor", "balcony_floor")
    m.box(0, 0, (0, b), "band", "slab_edge")
    m.box(0, 1, (1, b), "rail", "parapet")
    m.box(0, 2, (1, b), "cap", "handrail")
    m.box((0, 1), (0, 3), 0, "wall", "divider")
    return m


def mod_ribbon():
    """带形窗: solid spandrel, continuous panes between thin mullions."""
    m = Mod(4, 4)
    m.box(3, (0, 3), (0, 3), "wall", "back_wall")
    m.box(2, (0, 3), (0, 3), "back", "interior")
    m.box(1, (0, 1), (0, 3), "band", "spandrel")
    m.box(1, (2, 3), (0, 3), "pane", "ribbon")
    m.box(1, (2, 3), 0, "column", "mullion")
    m.box(0, 1, (0, 3), "sill", "sill")
    return m


def mod_curtain():
    """玻璃幕墙: frame grid with panes, dark interior."""
    m = Mod(3, 3)
    m.box(2, (0, 3), (0, 2), "back", "interior")
    m.box(1, (0, 3), (0, 2), "pane", "glass")
    m.box(1, 0, (0, 2), "column", "transom")
    m.box(1, (0, 3), 0, "column", "mullion")
    m.box(0, 0, (0, 2), "sill", "floor_ledge")
    return m


MODULES = {"corridor": mod_corridor, "windows": mod_windows, "balcony": mod_balcony,
           "ribbon": mod_ribbon, "curtain": mod_curtain}
ROT = {"S": 0, "W": 90, "N": 180, "E": 270}


def module_spec(style, sc, side):
    m = MODULES[style]()
    spec = {
        "name": f"{style}-{sc.name}-{side}",
        "minecraftVersion": VERSION,
        "description": f"VibeSchem facade module '{style}' ({sc.name}), 3x3 tiled, facing {side}",
        "palette": scheme_palette(sc),
        "components": {"bay": {"operations": m.ops}},
        "operations": [{"id": "tiles", "type": "group", "rotate": ROT[side], "operations": [
            {"id": "rows", "type": "group", "repeat": {"count": 3, "offset": [0, FH, 0]}, "operations": [
                {"id": "row", "type": "place", "component": "bay", "at": [0, 0, 0],
                 "repeat": {"count": 3, "offset": [m.bay, 0, 0]}}]}]}],
    }
    return spec, m


def extract_module(V, pal, m, side):
    """Centre tile of the 3x3 compile as F[y, u, d] in generator conventions."""
    bay, D = m.bay, m.D
    want = (3 * FH, D, 3 * bay) if side in "NS" else (3 * FH, 3 * bay, D)
    assert V.shape == want, (side, V.shape, want)
    T = V[FH:2 * FH]
    if side == "S":
        F = T[:, ::-1, bay:2 * bay].transpose(0, 2, 1)       # z = D-1-d, x = u
    elif side == "N":
        F = T[:, :, bay:2 * bay].transpose(0, 2, 1)          # z = d
    elif side == "W":
        F = T[:, bay:2 * bay, :]                              # z = u, x = d
    else:
        F = T[:, bay:2 * bay, ::-1]                           # x = D-1-d
    return F


# ------------------------------------------------------------------ props
def tree_spec(kind, seed):
    return {"name": f"tree-{kind}-{seed}", "minecraftVersion": VERSION, "seed": seed,
            "operations": [{"id": "tree", "type": "tree", "at": [0, 0, 0], "kind": kind}]}


TREES = [("oak", s) for s in range(6)] + [("big_oak", s) for s in range(3)] + \
        [("birch", s) for s in range(3)] + [("cherry", s) for s in range(3)] + [("bush", s) for s in range(2)]

PROPS = {
    # 路灯: post with a hanging lantern on an arm
    "lamp": {"name": "lamp", "minecraftVersion": VERSION, "operations": [
        {"id": "base", "type": "blocks", "block": "polished_andesite", "at": [[0, 0, 0]]},
        {"id": "post", "type": "box", "from": [0, 1, 0], "to": [0, 4, 0], "block": "polished_blackstone_wall"},
        {"id": "arm", "type": "blocks", "block": "dark_oak_fence", "at": [[0, 5, 0], [1, 5, 0]]},
        {"id": "lantern", "type": "blocks", "block": "lantern[hanging=true]", "at": [[1, 4, 0]]}]},
    # 长椅: stairs seat with trapdoor arms
    "bench": {"name": "bench", "minecraftVersion": VERSION, "operations": [
        {"id": "seat", "type": "box", "from": [0, 0, 0], "to": [2, 0, 0], "block": "spruce_stairs[facing=north]"},
        {"id": "arms", "type": "blocks", "block": "spruce_trapdoor[open=true,facing=east]", "at": [[-1, 0, 0]]},
        {"id": "arms2", "type": "blocks", "block": "spruce_trapdoor[open=true,facing=west]", "at": [[3, 0, 0]]}]},
    # 自行车棚: posts, slab roof, bikes as a row of fences + trapdoors
    "bike_shed": {"name": "bike_shed", "minecraftVersion": VERSION, "palette": {"roof": "blue_terracotta"},
                  "operations": [
        {"id": "posts", "type": "group", "repeat": {"count": 7, "offset": [6, 0, 0]}, "operations": [
            {"type": "box", "from": [0, 0, 0], "to": [0, 2, 0], "block": "iron_bars"},
            {"type": "box", "from": [0, 0, 4], "to": [0, 2, 4], "block": "iron_bars"}]},
        {"id": "roof", "type": "box", "from": [-1, 3, -1], "to": [37, 3, 5], "block": "smooth_stone_slab[type=bottom]"},
        {"id": "roof_edge", "type": "box", "from": [-1, 3, 5], "to": [37, 3, 5], "block": "blue_terracotta"},
        {"id": "bikes", "type": "script", "code":
            "for (let x = 1; x < 36; x += 2) { if (chance(0.7)) { set(x, 0, 2, pick(['black_carpet','red_carpet','blue_carpet','white_carpet'])); set(x, 0, 1, 'iron_bars'); set(x, 0, 3, 'iron_bars'); } }"}]},
    # 篮球架: pole, backboard, red rim (faces +x)
    "hoop": {"name": "hoop", "minecraftVersion": VERSION, "operations": [
        {"id": "pole", "type": "box", "from": [0, 0, 1], "to": [0, 3, 1], "block": "gray_concrete"},
        {"id": "arm", "type": "blocks", "block": "gray_concrete", "at": [[1, 3, 1]]},
        {"id": "board", "type": "box", "from": [1, 4, 0], "to": [1, 5, 2], "block": "white_concrete"},
        {"id": "rim", "type": "blocks", "block": "red_stained_glass_pane", "at": [[2, 4, 1]]}]},
    # 门卫室: guard house with a flat overhanging roof and a ribbon window
    "guard_house": {"name": "guard_house", "minecraftVersion": VERSION,
                    "palette": {"wall": {"mix": {"white_concrete": 5, "white_terracotta": 1}, "scale": 2}},
                    "operations": [
        {"id": "plinth", "type": "box", "from": [-1, 0, -1], "to": [12, 0, 8], "block": "polished_andesite"},
        {"id": "walls", "type": "box", "from": [0, 1, 0], "to": [11, 4, 7], "block": "wall", "walls": True, "inner": "air"},
        {"id": "glass", "type": "box", "from": [1, 2, 7], "to": [10, 3, 7], "block": "glass_pane"},
        {"id": "glass_w", "type": "box", "from": [0, 2, 1], "to": [0, 3, 6], "block": "glass_pane"},
        {"id": "door", "type": "blocks", "block": "iron_door[facing=north]", "at": [[5, 1, 0]]},
        {"id": "roof", "type": "roof", "shape": "flat", "from": [0, 5, 0], "to": [11, 5, 7], "block": "smooth_stone_slab", "overhang": 1, "eaves": "smooth_quartz_stairs"},
        {"id": "sign", "type": "box", "from": [2, 4, 8], "to": [9, 4, 8], "block": "blue_concrete"},
        {"id": "lamp", "type": "blocks", "block": "lantern[hanging=true]", "at": [[3, 4, 9], [8, 4, 9]]}]},
}


def shop_spec(i, w, h, seed, wall, sign, awning):
    """临街小店 at real scale: storefront facing -z (north, toward the school)."""
    return {
        "name": f"shop-{i}", "minecraftVersion": VERSION, "seed": seed,
        "palette": {"wall": {"mix": {wall: 5, "white_terracotta": 1}, "scale": 2}, "sign": sign, "awning": awning,
                    "awning_trim": awning.replace("_wool", "_carpet"), "trim": "smooth_stone_slab"},
        "operations": [
            {"id": "body", "type": "box", "from": [0, 0, 0], "to": [w - 1, h - 1, 9], "block": "wall"},
            {"id": "inside", "type": "box", "from": [1, 1, 1], "to": [w - 2, 2, 8], "block": "air"},
            {"id": "front_glass", "type": "box", "from": [1, 1, 0], "to": [w - 2, 2, 0], "block": "glass_pane"},
            {"id": "door", "type": "blocks", "block": "dark_oak_door[facing=north]", "at": [[w // 2, 1, 0]]},
            {"id": "floor", "type": "box", "from": [1, 0, 1], "to": [w - 2, 0, 8], "block": "smooth_stone"},
            {"id": "shelf", "type": "box", "from": [1, 1, 8], "to": [w - 2, 2, 8], "block": "bookshelf"},
            {"id": "lights", "type": "box", "from": [2, 2, 4], "to": [2, 2, 4], "block": "lantern[hanging=true]"},
            {"id": "signboard", "type": "box", "from": [0, 3, -1], "to": [w - 1, 3, -1], "block": "sign"},
            {"id": "awning", "type": "box", "from": [1, 3, -2], "to": [w - 2, 3, -2], "block": "awning"},
            {"id": "awning_edge", "type": "box", "from": [1, 2, -2], "to": [w - 2, 2, -2], "block": "awning_trim"},
            {"id": "upper_windows", "type": "script", "args": {"w": w, "h": h}, "code":
                "for (let y = 5; y < args.h - 1; y += 3) for (let x = 1; x < args.w - 1; x += 3) { set(x, y, 0, 'glass_pane'); set(x + 1, y, 0, 'glass_pane'); set(x, y - 1, -1, 'smooth_stone_slab[type=top]'); set(x + 1, y - 1, -1, 'smooth_stone_slab[type=top]'); if (chance(0.3)) set(x, y, -1, 'iron_block'); }"},
            {"id": "roof", "type": "roof", "shape": "flat", "from": [0, h, 0], "to": [w - 1, h, 9], "block": "trim", "overhang": 0},
            {"id": "parapet", "type": "box", "from": [0, h + 1, 0], "to": [w - 1, h + 1, 0], "block": "smooth_quartz_slab"},
        ]}


def shop_variants():
    rng = np.random.default_rng(11)
    walls = ["white_terracotta", "light_gray_concrete", "smooth_sandstone", "bricks", "white_concrete"]
    signs = ["red_concrete", "blue_concrete", "yellow_concrete", "green_concrete", "orange_concrete"]
    awns = ["red_wool", "blue_wool", "white_wool", "green_wool", "yellow_wool"]
    out = []
    for i in range(10):
        w = int(rng.integers(9, 16))
        h = int(rng.choice([7, 7, 10]))
        spec = shop_spec(i, w, h, int(rng.integers(1 << 20)), walls[i % 5], signs[(i * 3) % 5], awns[(i * 2) % 5])
        out.append(spec)
    return out


# ------------------------------------------------------------------ whole buildings (for export)
def _text_layers(oid, text, px, top_left, block, vertical=False, gap=None, bold=1):
    """Giant lettering as a VibeSchem `layers` op in the xy plane (faces +z).
    top_left = [x, y of the top row, z]; layers' origin is the bottom row."""
    import font
    bm = font.text(text, px, max(2, px // 5) if gap is None else gap, bold=bold, vertical=vertical)
    rows = ["".join("#" if v else "." for v in r) for r in bm]
    x, y, z = top_left
    return {"id": oid, "type": "layers", "origin": [x, y - len(rows) + 1, z], "plane": "xy",
            "legend": {"#": block}, "layers": [rows]}


def teaching_spec(floors=50, scheme="white_red", name="明德楼", motto="天道酬勤", sign="高考加油"):
    """教学楼: 16 corridor bays on the south, windows on the north, stair towers
    with the building's name, motto banner and a rooftop sign."""
    from schemes import SCHEMES
    sc = SCHEMES[scheme]
    H = FH * floors
    body0, L = 14, 160
    Dp = 20
    corr, win = mod_corridor(), mod_windows()
    ops = [
        {"id": "south_corridors", "type": "group", "repeat": {"count": floors, "offset": [0, FH, 0]}, "operations": [
            {"id": "corridor_row", "type": "place", "component": "corridor", "at": [body0, 0, Dp - corr.D],
             "repeat": {"count": L // corr.bay, "offset": [corr.bay, 0, 0]}}]},
        {"id": "north_windows", "type": "group", "repeat": {"count": floors, "offset": [0, FH, 0]}, "operations": [
            {"id": "window_row", "type": "place", "component": "windows", "rotate": 180,
             "at": [body0 + win.bay - 1, 0, win.D - 1], "repeat": {"count": L // win.bay, "offset": [win.bay, 0, 0]}}]},
        {"id": "roof_slab", "type": "box", "from": [body0, H, 0], "to": [body0 + L - 1, H, Dp - 1], "block": "roof"},
        {"id": "parapet", "type": "box", "from": [body0, H + 1, 0], "to": [body0 + L - 1, H + 2, Dp - 1], "block": "trim", "walls": True},
        {"id": "penthouse", "type": "box", "from": [body0 + 60, H + 1, 4], "to": [body0 + 84, H + 8, 14], "block": "wall"},
        {"id": "penthouse_roof", "type": "roof", "shape": "flat", "from": [body0 + 60, H + 9, 4], "to": [body0 + 84, H + 9, 14], "block": "trim", "overhang": 1},
    ]
    for k, x0 in enumerate((0, body0 + L)):
        ops += [
            {"id": f"tower_{k}", "type": "box", "from": [x0, 0, -3], "to": [x0 + 13, H + 8, Dp + 2], "block": "accent"},
            {"id": f"tower_{k}_cap", "type": "box", "from": [x0 - 1, H + 9, -4], "to": [x0 + 14, H + 9, Dp + 3], "block": "trim"},
            {"id": f"tower_{k}_edges", "type": "group", "symmetry": {"x": x0 + 6.5}, "operations": [
                {"type": "box", "from": [x0, 0, Dp + 3], "to": [x0, H + 8, Dp + 3], "block": "wall"},
                {"type": "box", "from": [x0, 0, -4], "to": [x0, H + 8, -4], "block": "wall"}]},
            {"id": f"tower_{k}_slits", "type": "script", "args": {"x": x0 + 6, "h": H, "z1": Dp + 2},
             "code": "for (let y = 3; y < args.h; y += 4) { for (const x of [args.x, args.x + 1]) { set(x, y, args.z1, 'pane'); set(x, y + 1, args.z1, 'pane'); set(x, y, -3, 'pane'); set(x, y + 1, -3, 'pane'); } }"},
        ]
        ops.append(_text_layers(f"tower_{k}_name", name, 11, [x0 + 1, H - 4, Dp + 3], "gold_block", vertical=True, gap=3, bold=0))
    # motto banner on the corridor side
    import font
    bm = font.text(motto, 16, 3, bold=1)
    bh, bw = bm.shape
    bx = body0 + (L - bw) // 2
    top = H - 20
    ops.append({"id": "banner", "type": "box", "from": [bx - 4, top - bh - 4, Dp - 2], "to": [bx + bw + 3, top + 3, Dp - 1], "block": "accent"})
    ops.append(_text_layers("motto", motto, 16, [bx, top, Dp - 1], "white_concrete", gap=3))
    # rooftop sign with a scaffold behind it
    sm = font.text(sign, 22, 4, bold=1)
    sh, sw = sm.shape
    sx = body0 + (L - sw) // 2
    ops.append({"id": "sign_frame", "type": "group", "repeat": {"count": sw // 4 + 1, "offset": [4, 0, 0]}, "operations": [
        {"type": "box", "from": [sx, H + 1, Dp - 3], "to": [sx, H + 4 + sh, Dp - 3], "block": "iron_bars"}]})
    ops.append(_text_layers("roof_sign", sign, 22, [sx, H + 3 + sh, Dp - 4], "red_concrete", gap=4))
    pal = scheme_palette(sc)
    return {"name": f"教学楼-{name}", "minecraftVersion": VERSION,
            "description": f"无涯中学的一栋外廊式教学楼：{floors} 层，{L // corr.bay} 间教室/层，楼梯间竖写楼名。",
            "palette": pal, "components": {"corridor": {"operations": corr.ops}, "windows": {"operations": win.ops}},
            "operations": ops, "anchor": [body0 + L // 2, 0, Dp + 6]}


def dorm_spec(floors=30, scheme="blue_white"):
    """宿舍楼: balconies on the south, windows on the north, solid stair ends."""
    from schemes import SCHEMES
    sc = SCHEMES[scheme]
    H = FH * floors
    L, Dp = 144, 16
    bal, win = mod_balcony(), mod_windows()
    ops = [
        {"id": "balconies", "type": "group", "repeat": {"count": floors, "offset": [0, FH, 0]}, "operations": [
            {"id": "balcony_row", "type": "place", "component": "balcony", "at": [0, 0, Dp - bal.D],
             "repeat": {"count": L // bal.bay, "offset": [bal.bay, 0, 0]}}]},
        {"id": "north_windows", "type": "group", "repeat": {"count": floors, "offset": [0, FH, 0]}, "operations": [
            {"id": "window_row", "type": "place", "component": "windows", "rotate": 180,
             "at": [win.bay - 1, 0, win.D - 1], "repeat": {"count": L // win.bay, "offset": [win.bay, 0, 0]}}]},
        {"id": "ends", "type": "group", "symmetry": {"x": (L - 1) / 2}, "operations": [
            {"type": "box", "from": [-3, 0, 0], "to": [-1, H + 2, Dp - 1], "block": "accent"}]},
        {"id": "roof", "type": "box", "from": [-3, H, 0], "to": [L + 2, H, Dp - 1], "block": "roof"},
        {"id": "parapet", "type": "box", "from": [-3, H + 1, 0], "to": [L + 2, H + 2, Dp - 1], "block": "trim", "walls": True},
        {"id": "laundry", "type": "script", "args": {"L": L, "f": floors, "z": Dp - 2},
         "code": "for (let f = 1; f < args.f; f++) for (let x = 1; x < args.L; x += 6) if (chance(0.25)) { const c = pick(['white_wool','light_blue_wool','pink_wool','yellow_wool','red_wool']); for (let k = 0; k < randInt(1, 3); k++) set(x + 1 + k, f * 4 + 2, args.z, c); }"},
    ]
    return {"name": "宿舍楼", "minecraftVersion": VERSION, "seed": 3,
            "description": f"无涯中学的一栋宿舍楼：{floors} 层，阳台上晾着衣服。",
            "palette": scheme_palette(sc), "components": {"balcony": {"operations": bal.ops}, "windows": {"operations": win.ops}},
            "operations": ops, "anchor": [L // 2, 0, Dp + 4]}


EXPORTS = {
    "teaching_building": lambda: teaching_spec(),
    "dorm": lambda: dorm_spec(),
}


def export(outdir, formats=("schem", "litematic")):
    os.makedirs(outdir, exist_ok=True)
    os.makedirs(SPECS, exist_ok=True)
    for key, mk in EXPORTS.items():
        spec = mk()
        with open(os.path.join(SPECS, f"export_{key}.json"), "w") as f:
            json.dump(spec, f, indent=1, ensure_ascii=False)
        V, pal, origin, summary = compile_spec(spec)
        print(summary.splitlines()[0])
        open(os.path.join(outdir, f"{key}.png"), "wb").write(render("iso", 1100))
        for fmt in formats:
            b = _req(f"/api/export/{fmt}", raw=True)
            ext = {"schem": "schem", "litematic": "litematic"}[fmt]
            p = os.path.join(outdir, f"无涯中学_{ {'teaching_building': '教学楼', 'dorm': '宿舍楼'}[key] }.{ext}")
            open(p, "wb").write(b)
            print("  ->", p, f"{len(b) / 1e3:.0f} kB")


# ------------------------------------------------------------------ cache
def _pack(V, pal, origin):
    return {"shape": list(V.shape), "palette": pal, "origin": origin,
            "data": base64.b64encode(zlib.compress(V.astype("<u2").tobytes(), 9)).decode()}


def _unpack(e):
    V = np.frombuffer(zlib.decompress(base64.b64decode(e["data"])), "<u2").reshape(e["shape"])
    return V, e["palette"], e["origin"]


_LOADED = None


def load():
    """name -> (A[y,z,x] in this process's block registry ids, origin)."""
    global _LOADED
    if _LOADED is None:
        from anvil import B
        raw = json.loads(gzip.decompress(open(CACHE, "rb").read()))
        _LOADED = {}
        for k, e in raw.items():
            V, pal, origin = _unpack(e)
            lut = np.array([0 if p == "minecraft:air" else B(p.replace("minecraft:", "", 1)) for p in pal], np.uint16)
            _LOADED[k] = (lut[V], origin)
    return _LOADED


def module(style, scheme, side):
    return load()[f"mod/{style}/{scheme}/{side}"][0]


def prop(name):
    return load()["prop/" + name][0]


def has_cache():
    return os.path.exists(CACHE)


# ------------------------------------------------------------------ sync
def all_specs():
    from schemes import SCHEMES
    specs = {}
    for style in MODULES:
        for scn, sc in SCHEMES.items():
            for side in "SNWE":
                spec, m = module_spec(style, sc, side)
                specs[f"mod/{style}/{scn}/{side}"] = (spec, ("module", style, side, m))
    for kind, seed in TREES:
        specs[f"prop/tree_{kind}_{seed}"] = (tree_spec(kind, seed), ("prop",))
    for k, s in PROPS.items():
        specs["prop/" + k] = (s, ("prop",))
    for name, rot in (("hoop_s", 90), ("hoop_n", 270)):
        h = PROPS["hoop"]
        specs["prop/" + name] = ({"name": name, "minecraftVersion": VERSION, "operations": [
            {"id": "rot", "type": "group", "rotate": rot, "operations": h["operations"]}]}, ("prop",))
    for i, s in enumerate(shop_variants()):
        specs[f"prop/shop_{i}"] = (s, ("prop",))
    return specs


def sync(names=None):
    os.makedirs(SPECS, exist_ok=True)
    out = {}
    if os.path.exists(CACHE):
        out = json.loads(gzip.decompress(open(CACHE, "rb").read()))
    for key, (spec, info) in all_specs().items():
        if names and not any(key.startswith(n) for n in names):
            continue
        V, pal, origin, summary = compile_spec(spec)
        if info[0] == "module":
            _, style, side, m = info
            V = np.ascontiguousarray(extract_module(V, pal, m, side))
            origin = [0, 0, 0]
        out[key] = _pack(V, pal, origin)
        if key.endswith("/S") or info[0] == "prop":
            with open(os.path.join(SPECS, key.replace("/", "_") + ".json"), "w") as f:
                json.dump(spec, f, indent=1, ensure_ascii=False)
        print(f"  {key:40s} {summary.splitlines()[0][:90]}", flush=True)
    with open(CACHE, "wb") as f:
        f.write(gzip.compress(json.dumps(out, separators=(",", ":")).encode(), 9))
    print(f"cache: {CACHE} ({os.path.getsize(CACHE) / 1e3:.0f} kB, {len(out)} entries)")


if __name__ == "__main__":
    if sys.argv[1] == "sync":
        sync(sys.argv[2:] or None)
    elif sys.argv[1] == "export":
        export(sys.argv[2])
