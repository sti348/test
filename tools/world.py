"""The film's sets, as plain block data.  Shared by the datapack compiler
(fill/setblock commands) and the web preview (same boxes, meshed in three.js).

World layout (x = east, z = south, ground surface y = 64, actors stand at 65):
  * main forest road along z = 0 from x = -150 to 240 (Kino rides west)
  * a faint side track north at x = -79 leading to the flooded fortress ruins
  * plaza  x -120..-40, z -152..-72 (floor = waterlogged slabs at y 64)
  * keep   x -88..-72,  z -147..-131 (south door at x -80)
  * inn room for the flashback far away at x 300
"""
from __future__ import annotations

import math
import random

GROUND = 64
WATER_SLAB = "stone_brick_slab[type=bottom,waterlogged=true]"
MOSSY_SLAB = "mossy_stone_brick_slab[type=bottom,waterlogged=true]"
COBBLE_SLAB = "cobblestone_slab[type=bottom,waterlogged=true]"

# named spots used by the film script -------------------------------------
SPOTS = {
    "road_z": 0.0,
    "meet_x": 40.0,          # Kino meets the "bandits"
    "ambush_x": 118.0,       # where they wait for the truck
    "kino_stop": (2.0, -6.5),   # Hermes hidden among trees (north side)
    "snipe": (56.0, -2.0),   # Kino prone on the road edge, aiming east
    "barricade_x": -93.0,
    "branch_x": -86.0,       # side track to the ruins leaves the road here
    "plaza_south": -72.0,
    "keep_door_z": -131.0,
    "keep_x": -80.0,
    "sniper_tree": (-67.0, -64.0),
    "camp": (-84.0, -62.0),
    "inn": (300.0, 0.0),
}


class World:
    def __init__(self):
        self.b = {}
        self.trees = []        # (variant, x, y, z) -> placed with /place template in-game
        self.tree_keys = {}

    def place_tree(self, name, x, z):
        blocks = TREE_VARIANTS[name]
        y0 = GROUND + 1
        self.trees.append((name, x + TREE_MIN[name][0], y0 + TREE_MIN[name][1], z + TREE_MIN[name][2]))
        for (dx, dy, dz, st) in blocks:
            key = (x + dx, y0 + dy, z + dz)
            if "leaves" in st and self.b.get(key) is not None:
                continue
            self.b[key] = st
            self.tree_keys[key] = st

    PLANTS = ("short_grass", "fern", "dandelion", "poppy", "oxeye_daisy", "azure_bluet", "cornflower")

    def split(self):
        """-> (static blocks, plant blocks) excluding blocks that come from tree templates."""
        static, plants = {}, {}
        for k, v in self.b.items():
            if v is None or self.tree_keys.get(k) == v:
                continue
            (plants if v in self.PLANTS else static)[k] = v
        return static, plants

    def set(self, x, y, z, s):
        self.b[(x, y, z)] = s

    def get(self, x, y, z):
        return self.b.get((x, y, z))

    def fill(self, x1, y1, z1, x2, y2, z2, s):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    self.b[(x, y, z)] = s

    def clear(self, x1, y1, z1, x2, y2, z2):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    self.b.pop((x, y, z), None)


TRACK = [(-86.0, -3.0), (-86.0, -14.0), (-83.0, -28.0), (-80.0, -42.0), (-79.5, -56.0), (-79.5, -72.0)]


def track_points(step=0.5):
    """Dense points along the side track (for the ruts and the vehicles)."""
    out = []
    for (a, b) in zip(TRACK, TRACK[1:]):
        n = max(1, int(math.dist(a, b) / step))
        for k in range(n):
            u = k / n
            out.append((a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u))
    out.append(TRACK[-1])
    return out


def dist_to_track(x, z):
    best = 1e9
    for (a, b) in zip(TRACK, TRACK[1:]):
        ax, az = a
        bx, bz = b
        dx, dz = bx - ax, bz - az
        L2 = dx * dx + dz * dz
        u = max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / L2))
        best = min(best, math.hypot(x - (ax + dx * u), z - (az + dz * u)))
    return best


# ----------------------------------------------------------------------------
def in_plaza(x, z):
    return -120 <= x <= -40 and -152 <= z <= -72


def clear_zone(x, z):
    """Where no trees may grow (roads, track, plaza, camp, hiding spot)."""
    if abs(z) <= 5 and -160 <= x <= 250:
        return True
    if -76 <= z <= -2 and dist_to_track(x, z) <= 4.2:
        return True
    if -124 <= x <= -36 and -156 <= z <= -69:
        return True
    if abs(x - 2) <= 2 and -9 <= z <= -5:   # Hermes' hiding spot
        return True
    if abs(x + 84) <= 5 and -66 <= z <= -58:  # enemy camp clearing
        return True
    return False


def tree(w, rng, x, z, kind, h=None):
    y0 = GROUND + 1
    log = {"oak": "oak_log[axis=y]", "birch": "birch_log[axis=y]", "spruce": "spruce_log[axis=y]"}[kind]
    leaf = {"oak": "oak_leaves[persistent=true]", "birch": "birch_leaves[persistent=true]",
            "spruce": "spruce_leaves[persistent=true]"}[kind]
    if kind == "spruce":
        h = h or rng.randint(7, 10)
        for y in range(h):
            w.set(x, y0 + y, z, log)
        top = y0 + h
        r = 0
        for y in range(top, y0 + 2, -1):
            for dx in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    if abs(dx) + abs(dz) <= r + (1 if r >= 2 else 0) and (dx or dz or y >= top - 0):
                        if not (dx == 0 and dz == 0 and y < top):
                            w.set(x + dx, y, z + dz, leaf)
            r = (r + 1) if r < 2 else (1 if r == 2 and (top - y) % 3 == 2 else 2)
        w.set(x, top, z, leaf)
        w.set(x, top + 1, z, leaf)
        return
    h = h or (rng.randint(5, 7) if kind == "birch" else rng.randint(4, 6))
    for y in range(h):
        w.set(x, y0 + y, z, log)
    top = y0 + h - 1
    # vanilla-like blob: two wide layers, two narrow layers
    for y in range(top - 2, top + 2):
        rad = 2 if y <= top - 1 else 1
        for dx in range(-rad, rad + 1):
            for dz in range(-rad, rad + 1):
                corner = abs(dx) == rad and abs(dz) == rad
                if corner and (y == top + 1 or rng.random() < 0.5):
                    continue
                if dx == 0 and dz == 0 and y <= top:
                    continue
                if w.get(x + dx, y, z + dz) is None:
                    w.set(x + dx, y, z + dz, leaf)
    if kind == "oak" and rng.random() < 0.35:   # a bigger, rounder crown now and then
        for dx, dz in ((3, 0), (-3, 0), (0, 3), (0, -3)):
            if w.get(x + dx, top - 1, z + dz) is None:
                w.set(x + dx, top - 1, z + dz, leaf)


def big_oak(w, x, z, h=11, branch_dir=(1, 0), branch_y=None, branch_len=4):
    y0 = GROUND + 1
    for y in range(h):
        for dx in (0, 1):
            for dz in (0, 1):
                w.set(x + dx, y0 + y, z + dz, "oak_log[axis=y]")
    by = branch_y or (y0 + h - 4)
    axis = "x" if branch_dir[0] else "z"
    for k in range(1, branch_len + 1):
        w.set(x + branch_dir[0] * (k + (1 if branch_dir[0] > 0 else 0)), by, z + branch_dir[1] * (k + (1 if branch_dir[1] > 0 else 0)),
              f"oak_log[axis={axis}]")
    top = y0 + h
    rng = random.Random(x * 31 + z)
    for y in range(top - 3, top + 3):
        rad = 4 if y < top + 1 else (3 if y == top + 1 else 2)
        for dx in range(-rad, rad + 2):
            for dz in range(-rad, rad + 2):
                cx, cz = dx - 0.5, dz - 0.5
                if cx * cx + cz * cz <= rad * rad + 1 and rng.random() < 0.93:
                    if w.get(x + dx, y, z + dz) is None:
                        w.set(x + dx, y, z + dz, "oak_leaves[persistent=true]")


# ----------------------------------------------------------------------------
TREE_VARIANTS = {}
TREE_MIN = {}


def _make_variants():
    for kind, n in (("birch", 6), ("oak", 6), ("spruce", 4)):
        for i in range(n):
            tmp = World()
            tree(tmp, random.Random(f"{kind}-{i}"), 0, 0, kind)
            name = f"{kind}_{i}"
            TREE_VARIANTS[name] = [(x, y - (GROUND + 1), z, st) for (x, y, z), st in tmp.b.items()]
            TREE_MIN[name] = (min(b[0] for b in TREE_VARIANTS[name]), 0, min(b[2] for b in TREE_VARIANTS[name]))


def build_forest(w, rng):
    # ground: grass over dirt
    areas = [(-150, 240, -48, 48), (-160, -8, -190, -49)]
    for (x1, x2, z1, z2) in areas:
        w.fill(x1, GROUND - 1, z1, x2, GROUND - 1, z2, "dirt")
        w.fill(x1, GROUND, z1, x2, GROUND, z2, "grass_block")
    # the black-earth road
    for x in range(-150, 241):
        for z in range(-3, 4):
            r = rng.random()
            s = "coarse_dirt" if r < 0.72 else ("rooted_dirt" if r < 0.86 else "podzol")
            if abs(z) == 3 and rng.random() < 0.45:
                s = "grass_block"
            w.set(x, GROUND, z, s)
    # faint track to the ruins: two wheel ruts through the grass
    done = set()
    for (px, pz) in track_points(0.5):
        for off in (-1.1, 1.1):
            x, z = int(math.floor(px + off)), int(math.floor(pz))
            if (x, z) in done:
                continue
            done.add((x, z))
            w.set(x, GROUND, z, "coarse_dirt" if rng.random() < 0.8 else "dirt")
    # trees
    for gx in range(-156, 246, 4):
        for gz in range(-188, 47, 4):
            x = gx + rng.randint(0, 3)
            z = gz + rng.randint(0, 3)
            if clear_zone(x, z):
                continue
            # thin the far forest (never seen by the camera)
            if (abs(z) > 34 and z > -60) and rng.random() < 0.55:
                continue
            if rng.random() < 0.18:
                continue
            r = rng.random()
            kind = "birch" if r < 0.55 else ("oak" if r < 0.9 else "spruce")
            n = 4 if kind == "spruce" else 6
            w.place_tree(f"{kind}_{rng.randrange(n)}", x, z)
    # undergrowth near what the camera sees
    flowers = ["dandelion", "poppy", "oxeye_daisy", "azure_bluet", "cornflower"]
    for (x1, x2, z1, z2) in areas:
        for x in range(x1, x2 + 1):
            for z in range(z1, z2 + 1):
                near = abs(z) < 26 or (-110 < x < -55 and z > -80) or (-135 < x < -25 and -170 < z < -55)
                if not near or in_plaza(x, z):
                    continue
                if w.get(x, GROUND, z) != "grass_block" or w.get(x, GROUND + 1, z) is not None:
                    continue
                r = rng.random()
                if r < 0.16:
                    w.set(x, GROUND + 1, z, "short_grass")
                elif r < 0.20:
                    w.set(x, GROUND + 1, z, "fern")
                elif r < 0.212:
                    w.set(x, GROUND + 1, z, rng.choice(flowers))


def stone(rng, p_moss=0.25, p_crack=0.12):
    r = rng.random()
    if r < p_moss:
        return "mossy_stone_bricks"
    if r < p_moss + p_crack:
        return "cracked_stone_bricks"
    return "stone_bricks"


def floor_slab(rng):
    r = rng.random()
    return WATER_SLAB if r < 0.7 else (MOSSY_SLAB if r < 0.9 else COBBLE_SLAB)


def ruin_house(w, rng, x1, z1, x2, z2, hmax=4, door=None, keep_whole=False):
    for x in range(x1, x2 + 1):
        for z in range(z1, z2 + 1):
            edge = x in (x1, x2) or z in (z1, z2)
            if not edge:
                continue
            if door and (x, z) in door:
                continue
            h = hmax if keep_whole else max(0, int(hmax - rng.random() * hmax * 1.25 + (1 if (x + z) % 4 == 0 else 0)))
            h = min(hmax, h)
            for y in range(GROUND, GROUND + max(1, h)):
                w.set(x, y, z, stone(rng, 0.35, 0.18))
            if h >= 2 and rng.random() < 0.25:
                w.set(x, GROUND + h, z, "stone_brick_slab[type=bottom]")


def build_ruins(w, rng):
    # plaza: stone base + flooded slab floor
    w.fill(-120, GROUND - 1, -152, -40, GROUND - 1, -72, "stone_bricks")
    for x in range(-120, -39):
        for z in range(-152, -71):
            w.set(x, GROUND, z, floor_slab(rng))
    # a low curb keeps the water in; broken in places (grass around is level)
    for x in range(-121, -38):
        for z in (-153, -71):
            if not (-82 <= x <= -76 and z == -71):
                w.set(x, GROUND, z, stone(rng, 0.5, 0.2))
    for z in range(-153, -70):
        for x in (-121, -39):
            w.set(x, GROUND, z, stone(rng, 0.5, 0.2))
    # the avenue entrance from the track: grass/earth ramp level with the slab
    for x in range(-82, -75):
        w.set(x, GROUND, -71, "coarse_dirt")

    # ruined houses both sides of the avenue ------------------------------
    houses = [
        (-100, -84, -94, -76, 3), (-110, -98, -101, -90, 4), (-99, -118, -92, -110, 3),
        (-114, -140, -104, -130, 4), (-66, -86, -59, -78, 3), (-58, -104, -49, -95, 4),
        (-67, -122, -60, -114, 3), (-56, -142, -47, -133, 4), (-96, -150, -91, -144, 2),
        (-92, -106, -88, -100, 4),   # the wall the cannon barrel smashes (east wall x=-88)
        (-72, -110, -69, -104, 3),   # Hermes hides behind this one
    ]
    for (x1, z1, x2, z2, h) in houses:
        door = {((x1 + x2) // 2, z2), ((x1 + x2) // 2 + 1, z2)} if (x1 + x2) % 2 == 0 else {((x1 + x2) // 2, z1)}
        ruin_house(w, rng, x1, z1, x2, z2, h, door=door, keep_whole=(x1 == -92))
    # rubble
    for _ in range(90):
        x = rng.randint(-118, -42)
        z = rng.randint(-150, -74)
        if abs(x + 80) <= 3 or (-89 <= x <= -71 and -148 <= z <= -130):
            continue
        w.set(x, GROUND, z, rng.choice(["cobblestone", "mossy_cobblestone", "stone_brick_slab[type=bottom,waterlogged=true]",
                                        "mossy_stone_bricks"]))

    # the keep --------------------------------------------------------------
    X1, X2, Z1, Z2 = -88, -72, -147, -131
    TOP = GROUND + 7            # walls y 64..71
    for x in range(X1, X2 + 1):
        for z in range(Z1, Z2 + 1):
            edge = x in (X1, X2) or z in (Z1, Z2)
            if edge:
                for y in range(GROUND, TOP + 1):
                    w.set(x, y, z, stone(rng, 0.22, 0.10))
            w.set(x, TOP + 1, z, "stone_bricks")                        # roof
    # parapet + merlons
    for x in range(X1, X2 + 1):
        for z in range(Z1, Z2 + 1):
            if x in (X1, X2) or z in (Z1, Z2):
                w.set(x, TOP + 2, z, stone(rng, 0.2, 0.1))
                if (x + z) % 2 == 0:
                    w.set(x, TOP + 3, z, stone(rng, 0.2, 0.1))
    # interior walls: cross corridors (x -81..-79, z -140..-138)
    for z in list(range(-136, -131)) + list(range(-146, -141)):
        for y in range(GROUND, TOP + 1):
            w.set(-82, y, z, stone(rng, 0.1, 0.1))
            w.set(-78, y, z, stone(rng, 0.1, 0.1))
    for x in list(range(-87, -82)) + list(range(-77, -72)):
        for y in range(GROUND, TOP + 1):
            w.set(x, y, -137, stone(rng, 0.1, 0.1))
            w.set(x, y, -141, stone(rng, 0.1, 0.1))
    # doors (air above the flooded floor)
    def door(x, z, h=2, wide=1, axis="x"):
        for k in range(wide):
            for y in range(GROUND, GROUND + h + 1):
                xx, zz = (x + k, z) if axis == "x" else (x, z + k)
                w.set(xx, y, zz, floor_slab(rng) if y == GROUND else None)
                if y > GROUND:
                    w.b.pop((xx, y, zz), None)
    door(-81, Z2, h=3, wide=3)              # main south entrance
    door(-80, Z1, h=2)                      # north
    door(X1, -139, h=2, axis="z")           # west
    door(X2, -139, h=2, axis="z")           # east
    door(-82, -134, h=2, axis="z")          # SW room (bodies) -> blocked below
    door(-78, -134, h=2, axis="z")          # SE room (the gathering room)
    door(-82, -144, h=2, axis="z")          # NW room (weapons, firewood)
    door(-78, -144, h=2, axis="z")          # NE room (stairs)
    # windows (light)
    for (x, z) in ((-85, Z2), (-75, Z2), (-85, Z1), (-75, Z1), (X1, -134), (X1, -144), (X2, -134), (X2, -144)):
        for y in (GROUND + 3, GROUND + 4):
            w.b.pop((x, y, z), None)
    # flooded floor inside
    for x in range(X1 + 1, X2):
        for z in range(Z1 + 1, Z2):
            if w.get(x, GROUND, z) is None:
                w.set(x, GROUND, z, floor_slab(rng))
    # SW room: bodies under rubble, doorway walled up with loose stones
    for x in range(-87, -82):
        for z in range(-136, -131):
            w.set(x, GROUND, z, "cobblestone")
            w.set(x, GROUND + 1, z, rng.choice(["cobblestone", "mossy_cobblestone", "cobblestone"]))
            if rng.random() < 0.55:
                w.set(x, GROUND + 2, z, rng.choice(["cobblestone", "mossy_cobblestone"]))
    for y in (GROUND + 1, GROUND + 2):
        w.set(-82, y, -134, "mossy_cobblestone" if y == GROUND + 2 else "cobblestone")
    # NW room: firewood stacked on stones, weapons on a stone shelf
    for x in range(-87, -84):
        for z in range(-146, -143):
            w.set(x, GROUND, z, "stone_bricks")
            w.set(x, GROUND + 1, z, "oak_log[axis=x]")
            if z != -143:
                w.set(x, GROUND + 2, z, "oak_log[axis=x]")
    for x in range(-86, -82):
        w.set(x, GROUND, -142, "stone_bricks")
    # SE room: stone platforms used as beds/tables + old fire pit
    for (x1, z1, x2, z2) in ((-77, -136, -76, -134), (-74, -136, -73, -135)):
        w.fill(x1, GROUND, z1, x2, GROUND, z2, "smooth_stone")
    w.set(-75, GROUND, -133, "campfire[lit=false,waterlogged=false]")
    # NE room: stair to the roof
    steps = [(-73, -142), (-73, -143), (-73, -144), (-73, -145), (-73, -146), (-74, -146), (-75, -146), (-76, -146)]
    for k, (x, z) in enumerate(steps):
        facing = "north" if z > -146 or x == -73 else "west"
        if k < 5:
            facing = "north"
        else:
            facing = "west"
        w.set(x, GROUND + k, z, f"stone_brick_stairs[facing={facing},half=bottom,waterlogged={'true' if k == 0 else 'false'}]")
        for y in range(GROUND, GROUND + k):
            w.set(x, y, z, "stone_bricks")
    for x in range(-77, -72):
        for z in range(-146, -143):
            w.b.pop((x, TOP + 1, z), None)          # stairwell opening in the roof
    w.set(-77, TOP + 1, -146, "stone_brick_stairs[facing=west,half=bottom,waterlogged=false]")
    # hidden light sources (invisible light blocks)
    for (x, z) in ((-80, -134), (-80, -139), (-80, -144), (-84, -139), (-76, -139), (-75, -134), (-85, -144), (-75, -144)):
        w.set(x, GROUND + 3, z, "light[level=13]")

    # enemy camp at the forest edge: fire + logs to sit on -------------------
    cx, cz = SPOTS["camp"]
    cx, cz = int(cx), int(cz)
    w.set(cx, GROUND + 1, cz, "campfire[lit=true]")
    w.set(cx - 2, GROUND + 1, cz, "spruce_log[axis=z]")
    w.set(cx + 2, GROUND + 1, cz, "spruce_log[axis=z]")
    for x in range(cx - 4, cx + 5):
        for z in range(cz - 3, cz + 4):
            if w.get(x, GROUND + 1, z) in ("short_grass", "fern"):
                w.b.pop((x, GROUND + 1, z))
    # sniper's tree with a thick branch reaching toward the ruins
    tx, tz = SPOTS["sniper_tree"]
    big_oak(w, int(tx), int(tz), h=12, branch_dir=(0, -1), branch_y=GROUND + 6, branch_len=4)


def build_inn(w):
    """A cheap inn room (flashback).  Interior 9 x 7, walls of planks."""
    x0, z0 = int(SPOTS["inn"][0]), int(SPOTS["inn"][1])
    X1, X2, Z1, Z2 = x0 - 5, x0 + 5, z0 - 4, z0 + 4
    w.fill(X1 - 3, GROUND - 1, Z1 - 3, X2 + 3, GROUND, Z2 + 3, "dirt")
    for x in range(X1, X2 + 1):
        for z in range(Z1, Z2 + 1):
            w.set(x, GROUND, z, "spruce_planks")
            edge = x in (X1, X2) or z in (Z1, Z2)
            for y in range(GROUND + 1, GROUND + 5):
                if edge:
                    w.set(x, y, z, "oak_planks" if y > GROUND + 1 else "stripped_spruce_log[axis=y]")
            w.set(x, GROUND + 5, z, "spruce_planks")
    for x in (X1, X2):
        for z in (Z1, Z2):
            for y in range(GROUND + 1, GROUND + 5):
                w.set(x, y, z, "spruce_log[axis=y]")
    # window on the north wall, door on the south wall
    for x in (x0 - 1, x0, x0 + 1):
        for y in (GROUND + 2, GROUND + 3):
            w.set(x, y, Z1, "glass")
    w.set(x0 + 3, GROUND + 1, Z2, "spruce_planks")
    # bed (slab frame + carpets), table, stools
    for z in (z0 - 3, z0 - 2):
        w.set(X1 + 1, GROUND + 1, z, "spruce_slab[type=bottom]")
        w.set(X1 + 2, GROUND + 1, z, "spruce_slab[type=bottom]")
    w.set(X1 + 1, GROUND + 2, z0 - 3, "white_carpet")
    w.set(X1 + 2, GROUND + 2, z0 - 3, "red_carpet")
    w.set(X1 + 1, GROUND + 2, z0 - 2, "white_carpet")
    w.set(X1 + 2, GROUND + 2, z0 - 2, "red_carpet")
    w.set(x0 + 2, GROUND + 1, z0 - 1, "spruce_planks")
    w.set(x0 + 2, GROUND + 2, z0 - 1, "lantern[hanging=false]")
    w.set(x0 + 1, GROUND + 1, z0 - 1, "spruce_stairs[facing=east,half=bottom]")
    w.set(x0 + 3, GROUND + 1, z0 - 1, "spruce_stairs[facing=west,half=bottom]")
    w.set(X2 - 1, GROUND + 1, z0 + 2, "barrel[facing=up]")
    for (x, z) in ((x0, z0), (x0 - 3, z0 + 1), (x0 + 2, z0 + 2)):
        w.set(x, GROUND + 4, z, "light[level=14]")


def build():
    if not TREE_VARIANTS:
        _make_variants()
    rng = random.Random(7)
    w = World()
    build_forest(w, rng)
    build_ruins(w, rng)
    build_inn(w)
    return w


# dynamic set changes used by the film -------------------------------------
def barricade_blocks():
    """A felled tree lying across the road (placed/removed during the film)."""
    x = int(SPOTS["barricade_x"])
    out = []
    for z in range(-5, 7):
        out.append((x, GROUND + 1, z, "oak_log[axis=z]"))
    for (dx, dz) in ((-1, 6), (0, 7), (1, 6), (-1, 7), (1, 7), (0, 8), (-2, 7), (2, 7), (0, 6)):
        out.append((x + dx, GROUND + 1, dz + 1, "oak_leaves[persistent=true]"))
        if abs(dx) < 2:
            out.append((x + dx, GROUND + 2, dz + 1, "oak_leaves[persistent=true]"))
    return out


def smashed_wall():
    """East wall of the ruin at x=-88 that the flying barrel breaks."""
    out = []
    for z in range(-105, -101):
        for y in range(GROUND + 1, GROUND + 4):
            out.append((-88, y, z, None))
    return out


def rubble_cleared():
    """Stones lifted off the bodies in the SW room (and the doorway)."""
    out = [(-82, GROUND + 1, -134, None), (-82, GROUND + 2, -134, None)]
    for x in range(-86, -83):
        for z in range(-135, -133):
            out.append((x, GROUND + 2, z, None))
            out.append((x, GROUND + 1, z, None))
    return out


if __name__ == "__main__":
    w = build()
    print(len(w.b), "blocks")
