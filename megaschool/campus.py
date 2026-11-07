"""Campus layout: where every building, tree and ground surface goes.

World coordinates: x east, z south, the gate is on the south edge, the player
spawns outside it looking north up the central axis."""
from __future__ import annotations

import math

import numpy as np

from anvil import B
import buildings as bd
import iconic as ic
import monuments as mon
import landmarks as lm
from buildings import GROUND_Y, Piece

HALF = 2048                  # world spans x in [-HALF, HALF), z in [-HALF, SOUTH_EDGE)
LOT, ROAD = 192, 32
PITCH = LOT + ROAD
ZOFF = -48                   # lot grid shift so the gate has an outer plaza
GATE_Z = 880                 # perimeter wall line (south)
FLAG_Z = 770
NORTH_Z = -HALF + 16
WEST_X, EAST_X = -HALF + 32, HALF - 32
SOUTH_ZONE = 528             # z >= this is hand-laid (avenue, playground ...)
SOUTH_EDGE = 1100            # the world extends past the gate for the approach
STREET_Z = GATE_Z + 154
SPAWN = (0, GROUND_Y, STREET_Z + 31)
WEST_GAP = (250, 350)        # opening in the west wall toward the giant Nether portal

MAX_FLOORS = 82

# ground blocks
GRASS = B("grass_block")
ASPHALT = B("gray_concrete")
LINE = B("white_concrete")
WALK = B("smooth_stone")
PAVE = B("polished_andesite")
PAVE2 = B("stone_bricks")
PLAZA = B("smooth_quartz")
TRACK = B("red_terracotta")
MOSS = B("moss_block")
COURT = B("blue_terracotta")
COURT_EDGE = B("green_terracotta")
WATER = B("water")


class Layout:
    def __init__(self):
        self.pieces: list[Piece] = []
        self.ground: list[tuple] = []     # painter's list of ground features

    def add(self, p: Piece):
        self.pieces.append(p)
        return p

    def rect(self, x0, z0, x1, z1, block):
        self.ground.append(("rect", int(x0), int(z0), int(x1), int(z1), block))

    def fn(self, x0, z0, x1, z1, f):
        self.ground.append(("fn", int(x0), int(z0), int(x1), int(z1), f))


# ---------------------------------------------------------------- helpers
def floors_for(x, z, rng, scale=1.0):
    """Buildings get taller the further they are from the gate; every lot also
    gets a random height class so the far skyline is not one flat wall."""
    d = math.hypot(x, z - GATE_Z)
    t = min(1.0, d / 1400)
    n = 26 + 52 * t + rng.integers(-6, 7)
    if d > 500:
        n *= float(rng.choice([0.55, 0.75, 0.9, 1.0, 1.0, 1.1, 1.15]))
    return int(max(14, min(MAX_FLOORS, n * scale)))


def place(_lay, _name, _fn, _size, _x, _z, _seed, y=GROUND_Y, **kw):
    return _lay.add(Piece(_name, int(_x), int(y), int(_z), _size, _fn, _seed, kw=kw))


def _sz(fn, kw):
    """Size of a generator's output (cheap generators are just run once)."""
    return fn(np.random.default_rng(0), **kw).shape


# ---------------------------------------------------------------- VibeSchem props
def _vs_prop(rng, prop):
    import vibeschem
    return vibeschem.prop(prop).copy()


def vs_place(L, prop, x, z, y=GROUND_Y):
    """Place a VibeSchem-compiled prop with its spec point [0,0,0] at (x, y, z)."""
    import vibeschem
    if not vibeschem.has_cache():
        return False
    key = prop if "/" in prop else "prop/" + prop
    A, (ox, oy, oz) = vibeschem.load()[key]
    name = key.split("/")[1].split("_")[0] if key.startswith("prop/") else key.split("/")[1]
    L.add(Piece(name, int(x) + ox, int(y) + oy, int(z) + oz, A.shape, _vs_prop, 0, kw={"prop": key}))
    return True


def mcb_place(L, name, x, z, y=GROUND_Y):
    """Place a facility designed and verified with minecraft-build-design (mcbuild);
    its local (0, 0, 0) lands at (x, y, z)."""
    import mcbuild_bridge
    if not mcbuild_bridge.has_cache():
        return False
    A, (ox, oy, oz) = mcbuild_bridge.load()[name]
    L.add(Piece(name, int(x) + ox, int(y) + oy, int(z) + oz, A.shape, _mcb_piece, 0, kw={"name": name}))
    return True


def _mcb_piece(rng, name):
    import mcbuild_bridge
    return mcbuild_bridge.load()[name][0].copy()


VS_TREES = {"oak": ["tree_oak_%d" % i for i in range(6)] + ["tree_big_oak_%d" % i for i in range(3)],
            "birch": ["tree_birch_%d" % i for i in range(3)],
            "cherry": ["tree_cherry_%d" % i for i in range(3)],
            "dark": ["tree_big_oak_%d" % i for i in range(3)] + ["tree_bush_0", "tree_bush_1"]}


def plant(L, rng, x, z, kind="oak"):
    """A tree: one of VibeSchem's procedural trees (falls back to the built-in one)."""
    seed = int(rng.integers(1 << 30))
    if vs_place(L, VS_TREES[kind][seed % len(VS_TREES[kind])], x, z):
        return
    tr = bd.tree(np.random.default_rng(seed), kind)
    h, dz, dx = tr.shape
    L.add(Piece("tree", int(x) - dx // 2, GROUND_Y, int(z) - dz // 2, tr.shape, bd.tree, seed, kind=kind))


def lamp_at(L, x, z):
    if not vs_place(L, "lamp", x, z):
        L.add(Piece("lamp", int(x), GROUND_Y, int(z), (6, 1, 1), bd.lamp, 0))


def trees_along(L, rng, x0, z0, x1, z1, spacing=12, kinds=("oak",), lamps=True):
    """Row of trees (and lamps between them) along a line (axis-aligned)."""
    n = max(1, int(math.hypot(x1 - x0, z1 - z0) // spacing))
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t
        z = z0 + (z1 - z0) * t
        plant(L, rng, x, z, str(kinds[rng.integers(len(kinds))]))
        if lamps and i < n and i % 2 == 0:
            lamp_at(L, x + (x1 - x0) / n / 2, z + (z1 - z0) / n / 2)


def lot_ground(L, x0, z0, x1, z1):
    L.rect(x0, z0, x1, z1, GRASS)
    L.rect(x0, z0, x1, z0 + 5, WALK)
    L.rect(x0, z1 - 5, x1, z1, WALK)
    L.rect(x0, z0, x0 + 5, z1, WALK)
    L.rect(x1 - 5, z0, x1, z1, WALK)


def lot_trees(L, rng, x0, z0, x1, z1):
    trees_along(L, rng, x0 + 8, z0 + 2, x1 - 8, z0 + 2)
    trees_along(L, rng, x0 + 8, z1 - 3, x1 - 8, z1 - 3)
    trees_along(L, rng, x0 + 2, z0 + 14, x0 + 2, z1 - 14, lamps=False)
    trees_along(L, rng, x1 - 3, z0 + 14, x1 - 3, z1 - 14, lamps=False)


# ---------------------------------------------------------------- landmark-style teaching buildings
def _seed(rng):
    return int(rng.integers(1 << 30))


def lot_gothic(L, rng, x0, z0, x1, z1, namer):
    """学习塔: a stone Gothic tower with unbroken ribs (cathedral-of-learning style)."""
    f = floors_for((x0 + x1) / 2, (z0 + z1) / 2, rng, 1.0)
    floors = int(np.clip(48 + (f - 26) * 0.65, 48, 80))
    W = 96 if x1 - x0 >= 170 else 80
    cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
    place(L, "gothic", ic.gothic_tower, ic.gothic_size(W, floors), cx - W // 2, cz - W // 2, _seed(rng), W=W,
          floors=floors, seed=_seed(rng))


def lot_cocoon(L, rng, x0, z0, x1, z1, namer):
    """茧形塔: an egg-shaped tower in a white diamond lattice."""
    f = floors_for((x0 + x1) / 2, (z0 + z1) / 2, rng, 1.0)
    floors = int(np.clip(30 + f // 2, 40, 70))
    W = int(min(x1 - x0, z1 - z0) - 40) // 2 * 2
    W = min(W, 112)
    cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
    sch = str(rng.choice(["gray_modern", "gray_modern", "blue_white", "brutal"]))
    place(L, "cocoon", ic.cocoon_tower, ic.cocoon_size(W, floors), cx - W // 2, cz - W // 2, _seed(rng), W=W,
          floors=floors, scheme=sch, seed=_seed(rng))


def lot_twin(L, rng, x0, z0, x1, z1, namer):
    """双塔门楼: twin slab towers joined at the top into a giant gate."""
    f = floors_for((x0 + x1) / 2, (z0 + z1) / 2, rng, 1.0)
    floors = int(np.clip(25 + f // 2, 35, 65))
    Tw, Td, gap = 50, 32, 44
    dx = 2 * Tw + gap
    cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
    sch = str(rng.choice(["gray_modern", "tile_gray", "white_red", "brutal"]))
    place(L, "twin", ic.twin_gate, ic.twin_size(Tw, Td, gap, floors), cx - dx // 2, cz - Td // 2, _seed(rng),
          Tw=Tw, Td=Td, gap=gap, floors=floors, scheme=sch, seed=_seed(rng))
    # a forecourt in front of the gate opening
    L.rect(cx - gap // 2, cz + Td // 2, cx + gap // 2, z1 - 6, PLAZA)


def lot_ring(L, rng, x0, z0, x1, z1, namer):
    """环形外廊楼: a drum of classrooms, every floor's corridor on its inner face."""
    f = floors_for((x0 + x1) / 2, (z0 + z1) / 2, rng, 1.0)
    floors = int(np.clip(f * 0.375, 12, 30))
    O = int(min(x1 - x0, z1 - z0) - 14) // 2 * 2
    cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
    sch = SCHEME_POOL[rng.integers(len(SCHEME_POOL))]
    place(L, "ring", ic.ring_hall, ic.ring_size(O, floors), cx - O // 2, cz - O // 2, _seed(rng), O=O,
          floors=floors, scheme=sch, seed=_seed(rng))
    def court(xs, zs):
        d = np.hypot(xs - cx + 0.5, zs - cz + 0.5)
        return d < O / 2 - 26, np.where((d.astype(int) // 6) % 2 == 0, GRASS, MOSS).astype(np.uint16)
    L.fn(cx - O // 2, cz - O // 2, cx + O // 2, cz + O // 2, court)
    for k in range(10):
        a = 2 * math.pi * k / 10
        plant(L, rng, int(cx + (O / 2 - 46) * math.cos(a)), int(cz + (O / 2 - 46) * math.sin(a)),
              "cherry" if k % 2 else "oak")


def lot_terrace(L, rng, x0, z0, x1, z1, namer):
    """退台楼: a long block stepping back on both sides, corridors and planters on every terrace."""
    f = floors_for((x0 + x1) / 2, (z0 + z1) / 2, rng, 1.0)
    tf = int(np.clip(f // 12, 2, 6))
    Lx, Dz = x1 - x0 - 16, z1 - z0 - 30
    tiers = 6
    step = max(5, (Dz // 2 - 12) // tiers)
    sch = str(rng.choice(["cream_brick", "white_red", "ochre", "red_brick", "blue_white"]))
    place(L, "terrace", ic.terrace, ic.terrace_size(Lx, Dz, tiers, tf), x0 + 8, z0 + 15, _seed(rng), L=Lx,
          Dbase=Dz, tiers=tiers, tier_floors=tf, step=step, scheme=sch, seed=_seed(rng))


def lot_wave(L, rng, x0, z0, x1, z1, namer):
    """波浪楼: a slab bent into one full sine wave, corridors along its south face."""
    f = floors_for((x0 + x1) / 2, (z0 + z1) / 2, rng, 1.0)
    Lx = x1 - x0 - 16
    amp, Dp = 22, 24
    f = max(10, f // 2)
    n = 2 if z1 - z0 >= 170 else 1
    sch = SCHEME_POOL[rng.integers(len(SCHEME_POOL))]
    dz = ic.wave_size(Lx, amp, Dp, f)[1]
    for k in range(n):
        zz = z0 + 8 + k * (z1 - z0 - 16 - dz) // max(1, n - 1) if n > 1 else (z0 + z1 - dz) // 2
        ff = max(10, f - 4 * (n - 1 - k))
        place(L, "wave", ic.wave_slab, ic.wave_size(Lx, amp, Dp, ff), x0 + 8, zz, _seed(rng), L=Lx, amp=amp,
              wl=Lx, Dp=Dp, floors=ff, scheme=sch, seed=_seed(rng), corridor="S" if k == n - 1 else "N")


def lot_bow(L, rng, x0, z0, x1, z1, namer):
    """小弯弓楼: a lot-sized bow, concave side (open corridors) facing south."""
    f = floors_for((x0 + x1) / 2, (z0 + z1) / 2, rng, 1.0)
    W = x1 - x0 - 12
    R, D = 150, 28
    f = max(10, f // 2)
    half = math.degrees(math.asin(min(0.99, (W / 2 - 6) / (R + D))))
    cxw, czw = (x0 + x1) / 2, z0 + 10 + R + D
    dx, dz = W, int(R + D - (R) * math.cos(math.radians(half))) + 8
    hh = ic.H_of(f + 4) + 2
    sch = SCHEME_POOL[rng.integers(len(SCHEME_POOL))]
    lx0, lz0 = int(cxw - W / 2), z0 + 6
    place(L, "bow", ic.arc_segment, (hh, dz, dx), lx0, lz0, _seed(rng), dx=dx, dz=dz, hh=hh,
          cx=cxw - lx0, cz=czw - lz0, R=R, D=D, a0=-half, a1=half, steps=[(90, f)], scheme=sch,
          end_towers=((-half + 1.5, 3), (half - 1.5, 3)), seed=_seed(rng))


LANDMARK_LOTS = {"gothic": lot_gothic, "cocoon": lot_cocoon, "twin": lot_twin, "ring": lot_ring,
                 "terrace": lot_terrace, "wave": lot_wave, "bow": lot_bow}


# ---------------------------------------------------------------- the bow-shaped main hall + tower of learning
ARC_C = (0, 1370)            # centre of the main hall's circle
ARC_R, ARC_D = 920, 36       # inner radius (concave face toward the gate), depth
ARC_HALF = 36                # degrees each side
ARC_STEPS = [(4.5, 35), (14, 32), (24, 29), (90, 25)]
TOWER_W, TOWER_FLOORS = 112, 80


def arc_z(x, r=ARC_R):
    return ARC_C[1] - math.sqrt(r * r - x * x)


def main_hall(L, rng):
    cxw, czw = ARC_C
    tz = int(arc_z(0, ARC_R + ARC_D / 2))
    hole = (-TOWER_W // 2 - 2, tz - TOWER_W // 2 - 2, TOWER_W // 2 + 2, tz + TOWER_W // 2 + 2)
    gates = [-21.0, -6.9, 6.9, 21.0]
    edges = list(np.linspace(-ARC_HALF, ARC_HALF, 11))
    hh = ic.H_of(35 + 7) + 2
    for k, (a0, a1) in enumerate(zip(edges[:-1], edges[1:])):
        pts = []
        for t in np.linspace(a0, a1, 24):
            for rr in (ARC_R - 6, ARC_R + ARC_D + 6):
                pts.append((cxw + rr * math.sin(math.radians(t)), czw - rr * math.cos(math.radians(t))))
        xs_, zs_ = zip(*pts)
        X0, X1 = int(math.floor(min(xs_))) - 2, int(math.ceil(max(xs_))) + 2
        Z0, Z1 = int(math.floor(min(zs_))) - 2, int(math.ceil(max(zs_))) + 2
        ends = []
        if k == 0:
            ends.append((-ARC_HALF + 1.4, 7))
        if k == len(edges) - 2:
            ends.append((ARC_HALF - 1.4, 7))
        a1e = a1 + (0.0001 if k == len(edges) - 2 else 0)
        place(L, "main", ic.arc_segment, (hh, Z1 - Z0, X1 - X0), X0, Z0, 500 + k, dx=X1 - X0, dz=Z1 - Z0, hh=hh,
              cx=cxw - X0, cz=czw - Z0, R=ARC_R, D=ARC_D, a0=float(a0), a1=float(a1e), steps=ARC_STEPS,
              scheme="white_red", style="grid", gates=tuple(g for g in gates if a0 <= g < a1),
              hole=(hole[0] - X0, hole[1] - Z0, hole[2] - X0, hole[3] - Z0), end_towers=tuple(ends), seed=500 + k)
    place(L, "learning_tower", ic.gothic_tower, ic.gothic_size(TOWER_W, TOWER_FLOORS), -TOWER_W // 2,
          tz - TOWER_W // 2, 7, W=TOWER_W, floors=TOWER_FLOORS, seed=7)
    # forecourt: the crescent between the hall and the avenue, paved in rings
    def forecourt(xs, zs):
        r = np.hypot(xs - cxw, zs - czw)
        m = (r < ARC_R - 1) & (zs < 652)
        ring = (np.floor((ARC_R - r) / 6).astype(int) % 2 == 0)
        out = np.where(ring, PAVE, PLAZA).astype(np.uint16)
        out[np.abs(xs) < 22] = PLAZA
        return m, out
    L.fn(-560, 440, 560, 652, forecourt)
    # rows of trees following the curve
    for rr in (ARC_R - 40, ARC_R - 80):
        for t in np.arange(-ARC_HALF + 2, ARC_HALF - 1, 2.2):
            x = cxw + rr * math.sin(math.radians(t))
            z = czw - rr * math.cos(math.radians(t))
            if abs(x) < 70 or z > 640:
                continue
            plant(L, rng, int(x), int(z), "cherry" if int(t * 10) % 3 == 0 else "oak")
    # behind the hall: a lawn with groves
    L.rect(-544, 304, 544, 600, GRASS)
    for _ in range(140):
        x = int(rng.integers(-530, 530))
        z = int(rng.integers(312, 590))
        if z < arc_z(x, ARC_R + ARC_D) - 14:
            plant(L, rng, x, z, "birch" if rng.random() < 0.3 else "oak")


SCHEME_POOL = ["white_red", "white_red", "cream_brick", "blue_white", "gray_modern", "red_brick", "brutal",
               "ochre", "tile_gray"]
NAMES = ["明德楼", "致远楼", "博学楼", "求是楼", "笃行楼", "格物楼", "至善楼", "思源楼", "弘毅楼", "敏行楼",
         "启智楼", "尚志楼", "知行楼", "厚德楼", "崇文楼", "立人楼", "励志楼", "进德楼", "修远楼", "文渊楼",
         "日新楼", "躬行楼", "明理楼", "浩然楼"]


class Namer:
    def __init__(self, rng):
        self.rng = rng
        self.names = list(rng.permutation(NAMES))
        self.i = 0

    def name(self):
        n = self.names[self.i % len(self.names)]
        self.i += 1
        return n


# ---------------------------------------------------------------- lot types
def lot_slabs(L, rng, x0, z0, x1, z1, namer, n=3):
    W, Dd = x1 - x0, z1 - z0
    Ls = W - 16
    Dp = 20
    sch = SCHEME_POOL[rng.integers(len(SCHEME_POOL))]
    corr = "S" if rng.random() < 0.5 else "N"
    pitch = (Dd - 16) / n
    base = floors_for((x0 + x1) / 2, (z0 + z1) / 2, rng, 1.0)
    zs = []
    hs = []
    for k in range(n):
        zz = int(z0 + 8 + k * pitch + (pitch - (Dp + 6)) / 2)
        f = max(14, min(MAX_FLOORS, base + int(rng.integers(-8, 9)) - (n - 1 - k) * 0 ))
        H = bd.floors_h(f)
        motto = sign = None          # no slogans: the architecture alone has to loom
        kw = dict(L=Ls, Dp=Dp, H=H, scheme=sch, corridor_side=corr, name=namer.name(), motto=motto, sign=sign,
                  accent_every=int(rng.choice([0, 0, 8, 10])), lit=0.02)
        place(L, "slab", bd.slab, bd.slab_size(Ls, Dp, H), x0 + 8, zz, int(rng.integers(1 << 30)), **kw)
        zs.append(zz)
        hs.append(H)
    # skybridges (连廊) between consecutive slabs at several levels
    bx = x0 + 8 + Ls // 2 - 6 + int(rng.integers(-40, 41))
    for k in range(n - 1):
        za = zs[k] + 3 + Dp - 1
        zb = zs[k + 1] + 3 + 1
        span = zb - za
        top = min(hs[k], hs[k + 1]) - 12
        step = int(rng.choice([40, 48, 60]))
        for y in range(16, top, step):
            nf = int(rng.integers(2, 4))
            kw = dict(length=span, width=12, n_floors=nf, scheme=sch, axis="z")
            sz = (bd.floors_h(nf) + 2, span, 12)
            place(L, "bridge", bd.skybridge, sz, bx, za, int(rng.integers(1 << 30)), y=GROUND_Y + y - y % 4, **kw)


def lot_courtyard(L, rng, x0, z0, x1, z1, namer):
    O = min(x1 - x0, z1 - z0) - 16
    base = floors_for((x0 + x1) / 2, (z0 + z1) / 2, rng, 1.0)
    hs = tuple(bd.floors_h(max(14, min(MAX_FLOORS, base + int(rng.integers(-10, 11))))) for _ in range(4))
    sch = SCHEME_POOL[rng.integers(len(SCHEME_POOL))]
    kw = dict(O=O, R=24, heights=hs, scheme=sch)
    place(L, "courtyard", bd.courtyard, (max(hs) + 3 + 40, O, O), x0 + 8, z0 + 8, int(rng.integers(1 << 30)), **kw)
    # courtyard garden
    c0, c1 = x0 + 8 + 24, x0 + 8 + O - 24
    d0, d1 = z0 + 8 + 24, z0 + 8 + O - 24
    L.rect(c0, d0, c1, d1, GRASS)
    L.rect((c0 + c1) // 2 - 3, d0, (c0 + c1) // 2 + 3, d1, PAVE)
    L.rect(c0, (d0 + d1) // 2 - 3, c1, (d0 + d1) // 2 + 3, PAVE)
    for _ in range(14):
        tx = int(rng.integers(c0 + 4, c1 - 8))
        tz = int(rng.integers(d0 + 4, d1 - 8))
        plant(L, rng, tx, tz, "cherry" if rng.random() < 0.3 else "oak")


def lot_towers(L, rng, x0, z0, x1, z1, namer):
    W = 56
    sch = SCHEME_POOL[rng.integers(len(SCHEME_POOL))]
    style = rng.choice(["windows", "curtain", "ribbon"])
    for (fx, fz) in ((0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)):
        cx = int(x0 + (x1 - x0) * fx)
        cz = int(z0 + (z1 - z0) * fz)
        f = floors_for(cx, cz, rng, 1.05)
        H = bd.floors_h(min(MAX_FLOORS, f + int(rng.integers(0, 10))))
        sign = None
        kw = dict(W=W, H=H, scheme=sch, tiers=int(rng.integers(2, 4)), style=str(style), sign=sign)
        place(L, "tower", bd.tower, (H + 43, W, W), cx - W // 2, cz - W // 2, int(rng.integers(1 << 30)), **kw)


def lot_dorms(L, rng, x0, z0, x1, z1, namer, n=5):
    Ls = x1 - x0 - 30
    Dp = 16
    sch = SCHEME_POOL[rng.integers(len(SCHEME_POOL))]
    pitch = (z1 - z0 - 16) / n
    base = floors_for((x0 + x1) / 2, (z0 + z1) / 2, rng, 0.85)
    for k in range(n):
        zz = int(z0 + 8 + k * pitch + (pitch - Dp) / 2)
        H = bd.floors_h(max(14, min(MAX_FLOORS, base + int(rng.integers(-4, 5)))))
        kw = dict(L=Ls, Dp=Dp, H=H, scheme=sch)
        place(L, "dorm", bd.dorm, (H + 3 + 30, Dp, Ls), x0 + 15, zz, int(rng.integers(1 << 30)), **kw)
    # bike sheds along the west edge
    for k in range(n - 1):
        zz = int(z0 + 8 + (k + 1) * pitch - 3)
        if not vs_place(L, "bike_shed", x0 + 21, zz + 1):
            place(L, "bikes", bd.bike_shed, (4, 5, 40), x0 + 20, zz, int(rng.integers(1 << 30)), length=40)


def lot_lab(L, rng, x0, z0, x1, z1, namer):
    dx, dz = x1 - x0 - 24, z1 - z0 - 60
    sch = SCHEME_POOL[rng.integers(len(SCHEME_POOL))]
    f = floors_for((x0 + x1) / 2, (z0 + z1) / 2, rng, 0.8)
    H = bd.floors_h(f)
    label = rng.choice(["实验楼", "科技楼", "艺术楼", "行政楼", "信息楼"])
    kw = dict(dx=dx, dz=dz, H=H, scheme=sch, name=str(label))
    place(L, "lab", bd.lab, (H + 3 + 40, dz, dx), x0 + 12, z0 + 30, int(rng.integers(1 << 30)), **kw)


def lot_gym(L, rng, x0, z0, x1, z1, namer):
    dx, dz = x1 - x0 - 16, z1 - z0 - 40
    kw = dict(dx=dx, dz=dz, wall_h=61, vault_h=70, scheme="gray_modern")
    place(L, "gym", bd.gym, (61 + 70 + 2, dz, dx), x0 + 8, z0 + 20, int(rng.integers(1 << 30)), **kw)


def lot_canteen(L, rng, x0, z0, x1, z1, namer):
    dx, dz = x1 - x0 - 24, z1 - z0 - 50
    kw = dict(dx=dx, dz=dz, H=81, scheme="tile_gray")
    place(L, "canteen", bd.canteen, (81 + 3 + 30, dz, dx), x0 + 12, z0 + 25, int(rng.integers(1 << 30)), **kw)


def lot_garden(L, rng, x0, z0, x1, z1, namer, globe=False):
    cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
    L.rect(x0 + 5, cz - 3, x1 - 5, cz + 3, PAVE)
    L.rect(cx - 3, z0 + 5, cx + 3, z1 - 5, PAVE)
    def pond(xs, zs):
        d = ((xs - (cx + 45)) / 30.0) ** 2 + ((zs - (cz + 45)) / 20.0) ** 2
        return d < 1, WATER
    L.fn(cx + 10, cz + 20, cx + 80, cz + 70, pond)
    if globe:
        g = lm.globe(np.random.default_rng(7))
        L.rect(cx - 40, cz - 40, cx + 40, cz + 40, PLAZA)
        place(L, "globe", lm.globe, g.shape, cx - g.shape[2] // 2, cz - g.shape[1] // 2, 7)
    for _ in range(60):
        tx = int(rng.integers(x0 + 10, x1 - 10))
        tz = int(rng.integers(z0 + 10, z1 - 10))
        if abs(tx - cx) < 46 and abs(tz - cz) < 46 and globe:
            continue
        if abs(tx - cx) < 6 or abs(tz - cz) < 6:
            continue
        if (cx + 10 < tx < cx + 80) and (cz + 20 < tz < cz + 70):
            continue
        plant(L, rng, tx, tz, str(rng.choice(["oak", "oak", "birch", "cherry", "dark"])))
    for k in range(8):
        bx = cx + 10 + 14 * k if k < 4 else cx - 16 - 14 * (k - 4)
        vs_place(L, "bench", bx, cz - 6)


# ---------------------------------------------------------------- the south zone
def track_fn(cx, cz, straight, r_in, r_out, lanes=8):
    def f(xs, zs):
        dx = np.maximum(np.abs(xs - cx) - straight / 2, 0)
        d = np.sqrt(dx ** 2 + (zs - cz) ** 2)
        on = (d >= r_in) & (d < r_out)
        out = np.full(xs.shape, TRACK, np.uint16)
        lw = (r_out - r_in) / lanes
        lines = np.abs(((d - r_in) / lw) - np.round((d - r_in) / lw)) * lw < 0.5
        out[lines & on] = LINE
        # start / finish line
        out[on & (np.abs(xs - (cx + straight / 4)) < 0.6) & (zs > cz)] = LINE
        inside = d < r_in
        stripe = ((xs - cx) // 12) % 2 == 0
        field = np.where(stripe, GRASS, MOSS).astype(np.uint16)
        # pitch markings (x3 scale football pitch)
        pw, ph = 2 * (straight / 2 + r_in * 0.55), r_in * 1.5
        ax, az = np.abs(xs - cx), np.abs(zs - cz)
        border = ((np.abs(ax - pw / 2) < 0.6) & (az <= ph / 2)) | ((np.abs(az - ph / 2) < 0.6) & (ax <= pw / 2))
        half = (np.abs(xs - cx) < 0.6) & (az <= ph / 2)
        circ = np.abs(np.sqrt((xs - cx) ** 2 + (zs - cz) ** 2) - 27) < 0.7
        box = ((np.abs(ax - (pw / 2 - 50)) < 0.6) & (az <= 60)) | ((np.abs(az - 60) < 0.6) & (ax >= pw / 2 - 50) & (ax <= pw / 2))
        field[(border | half | circ | box) & inside] = LINE
        res = np.where(on, out, field)
        return on | inside, res.astype(np.uint16)
    return f


def courts_fn(x0, z0, x1, z1, cw=15, cl=28, gx=6, gz=7):
    def f(xs, zs):
        u = (xs - x0) % (cw + gx)
        v = (zs - z0) % (cl + gz)
        inside = (u < cw) & (v < cl)
        out = np.full(xs.shape, COURT_EDGE, np.uint16)
        out[inside] = COURT
        line = inside & ((u == 0) | (u == cw - 1) | (v == 0) | (v == cl - 1) | (v == cl // 2))
        cc = inside & (np.abs(np.hypot(u - cw / 2 + 0.5, v - cl / 2 + 0.5) - 2) < 0.5)
        key = inside & ((v < 6) | (v >= cl - 6)) & (np.abs(u - cw / 2 + 0.5) <= 2.5)
        arc = inside & (np.abs(np.hypot(u - cw / 2 + 0.5, np.minimum(v, cl - 1 - v) - 1.5) - 6.7) < 0.5)
        out[key] = B("orange_terracotta")
        out[line | cc | arc] = LINE
        return np.ones(xs.shape, bool), out
    return f


def south_zone(L, rng, namer):
    # ---- outside the gate: approach plaza, a normal-sized town street with small shops
    L.rect(-HALF, GATE_Z + 2, HALF, SOUTH_EDGE, GRASS)
    L.rect(-HALF, GATE_Z + 2, HALF, GATE_Z + 8, WALK)
    L.rect(-170, GATE_Z + 2, 170, STREET_Z, PAVE)
    def approach(xs, zs):
        m = (np.abs(xs) < 160)
        out = np.where(((xs // 8 + zs // 8) % 2 == 0), PLAZA, PAVE).astype(np.uint16)
        out[np.abs(xs) < 24] = PLAZA
        return m, out
    L.fn(-160, GATE_Z + 8, 160, STREET_Z - 6, approach)
    for x in (-150, -110, -70, 70, 110, 150):
        trees_along(L, rng, x, GATE_Z + 60, x, STREET_Z - 14, spacing=12, kinds=("oak", "cherry"), lamps=x in (-70, 70))
    for xa, xb in ((-HALF + 4, -180), (180, HALF - 4)):
        trees_along(L, rng, xa, GATE_Z + 14, xb, GATE_Z + 14, spacing=12)
    L.rect(-HALF, STREET_Z - 6, HALF, STREET_Z, WALK)
    L.rect(-HALF, STREET_Z, HALF, STREET_Z + 28, ASPHALT)
    L.rect(-HALF, STREET_Z + 28, HALF, STREET_Z + 36, WALK)
    def dashes(xs, zs):
        return ((zs == STREET_Z + 14) & ((xs // 6) % 2 == 0)), LINE
    L.fn(-HALF, STREET_Z + 14, HALF, STREET_Z + 15, dashes)
    def zebra(xs, zs):
        return (np.abs(xs) < 14) & ((xs // 2) % 2 == 0), LINE
    L.fn(-14, STREET_Z + 2, 14, STREET_Z + 26, zebra)
    trees_along(L, rng, -HALF + 6, STREET_Z - 3, -30, STREET_Z - 3, spacing=10)
    trees_along(L, rng, 30, STREET_Z - 3, HALF - 6, STREET_Z - 3, spacing=10)
    # shops (human scale) across the street; spawn is on their sidewalk
    x = -HALF + 10
    k = 0
    while x < HALF - 30:
        w = int(rng.integers(9, 17))
        if abs(x + w / 2) < 24:
            x += w + 2
            continue
        import vibeschem
        if vibeschem.has_cache():
            name = "shop_%d" % int(rng.integers(10))
            w = vibeschem.load()["prop/" + name][0].shape[2]
            vs_place(L, name, x, STREET_Z + 39)
        else:
            seed = int(rng.integers(1 << 30))
            place(L, "shop", shop, (12, 12, w), x, STREET_Z + 36, seed, w=w, label=SHOPS[k % len(SHOPS)])
        x += w + 1
        k += 1
    # ---- perimeter wall with the gate
    for xa, xb in ((WEST_X, -140), (140, EAST_X)):
        place(L, "wall", wall_seg, (5, 2, xb - xa), xa, GATE_Z, 0, n=xb - xa, axis="x")
    place(L, "wall", wall_seg, (5, GATE_Z - NORTH_Z, 2), EAST_X, NORTH_Z, 0, n=GATE_Z - NORTH_Z, axis="z")
    # the west wall has a gap facing the giant Nether portal and the sinkhole
    for za, zb in ((NORTH_Z, WEST_GAP[0]), (WEST_GAP[1], GATE_Z)):
        place(L, "wall", wall_seg, (5, zb - za, 2), WEST_X - 2, za, 0, n=zb - za, axis="z")
    place(L, "wall", wall_seg, (5, 2, EAST_X - WEST_X), WEST_X, NORTH_Z - 2, 0, n=EAST_X - WEST_X, axis="x")
    # the school gate: a triumphal arch astride the avenue (no lettering)
    g = mon.triumphal_size()
    place(L, "gate", mon.triumphal_arch, g, -g[2] // 2, GATE_Z - g[1] // 2, 11)
    if not vs_place(L, "guard_house", 150, GATE_Z + 5):
        place(L, "guard", lm.guard_house, (6, 8, 12), 150, GATE_Z - 14, 0)
    # ---- central avenue + flag plaza
    L.rect(-128, 640, 128, GATE_Z, GRASS)
    L.rect(-28, 640, 28, GATE_Z + 2, PAVE)
    L.rect(-22, 640, 22, GATE_Z + 2, PLAZA)
    fz = FLAG_Z
    def plaza(xs, zs):
        d = np.hypot(xs - 0, zs - fz)
        m = d < 56
        out = np.where((d.astype(int) // 4) % 2 == 0, PLAZA, PAVE).astype(np.uint16)
        return m, out
    L.fn(-60, fz - 60, 60, fz + 60, plaza)
    for x in (-40, 40):
        trees_along(L, rng, x, fz + 66, x, GATE_Z - 64, spacing=10)
        trees_along(L, rng, x, 672, x, fz - 66, spacing=10)
    for x in (-96, 96):
        trees_along(L, rng, x, 650, x, GATE_Z - 64, spacing=14, kinds=("oak", "cherry"), lamps=False)
    place(L, "flag", lm.flagpole, _sz(lm.flagpole, {}), -12, fz - 12, 3)
    for z in range(fz + 75, GATE_Z - 64, 20):
        vs_place(L, "bench", -34, z)
        vs_place(L, "bench", 32, z)
    # covered walkways (风雨廊) both sides of the avenue, the fountain, a bus stop
    mcb_place(L, "walkway", -72, 680)
    mcb_place(L, "walkway", 66, 680)
    mcb_place(L, "fountain", -14, GATE_Z + 60)
    mcb_place(L, "bus_stop", 30, STREET_Z + 29)
    mcb_place(L, "bus_lot", -700, GATE_Z + 25)
    mcb_place(L, "car_park", 400, GATE_Z + 25)
    # ---- main hall: a kilometre-long bow embracing the forecourt, the tower of learning at its apex
    main_hall(L, rng)
    # ---- teaching-building rows on both sides of the avenue (the "canyon")
    za, zb = 652, GATE_Z - 8
    k = 0
    xa = 150
    while xa + 120 < EAST_X:
        xb = min(xa + 200, EAST_X - 6)
        for side, (a, b) in enumerate(((xa, xb), (-xb, -xa))):
            fac = {(0, 1): "lake_garden", (0, 0): "sports_park", (1, 1): "auditorium", (1, 0): "greenhouse"}.get((k, side))
            if fac and mcb_place(L, fac, a, za):
                continue
            lot_ground(L, a, za, b, zb)
            if side == 1 and k == 3:
                courts(L, a, za, b, zb)
                continue
            kind = ["wave", "twin", "terrace", "cocoon", "bow", "ring", "slabs", "gothic", "dorms"][(k * 2 + side * 5) % 9]
            if kind in LANDMARK_LOTS:
                LANDMARK_LOTS[kind](L, rng, a, za, b, zb, namer)
            elif kind == "slabs":
                lot_slabs(L, rng, a, za, b, zb, namer, n=3)
            elif kind == "dorms":
                lot_dorms(L, rng, a, za, b, zb, namer, n=6)
            elif kind == "courtyard":
                lot_courtyard(L, rng, a, za, b, zb, namer)
            else:
                lot_towers(L, rng, a, za, b, zb, namer)
            lot_trees(L, rng, a, za, b, zb)
        xa += 232
        k += 1
    L.rect(150, SOUTH_ZONE, EAST_X, 652, GRASS)
    L.rect(-EAST_X, SOUTH_ZONE, -150, 652, GRASS)
    for sgn in (-1, 1):
        trees_along(L, rng, sgn * 570, 620, sgn * (EAST_X - 10), 620, kinds=("oak", "birch"))


def courts(L, x0, z0, x1, z1):
    """Basketball courts at real scale - dozens of them."""
    cx0, cz0, cx1, cz1 = x0 + 6, z0 + 6, x1 - 6, z1 - 6
    L.fn(cx0 - 2, cz0 - 2, cx1 + 2, cz1 + 2, courts_fn(cx0, cz0, cx1, cz1))
    for x in range(cx0, cx1 - 14, 21):
        for z in range(cz0, cz1 - 28, 35):
            if not (vs_place(L, "hoop_s", x + 7, z - 2) and vs_place(L, "hoop_n", x + 7, z + 29)):
                place(L, "hoop", bd.hoop, (5, 3, 3), x + 6, z - 1, 0, facing=1)
                place(L, "hoop", bd.hoop, (5, 3, 3), x + 6, z + 26, 0, facing=-1)


def playground(L, rng, x0, z0, x1, z1):
    """400 m track at 3x scale with a grandstand and floodlight masts."""
    L.rect(x0, z0, x1, z1, PAVE)
    tcx, tcz = (x0 + x1) // 2, z1 - 150
    L.fn(tcx - 270, tcz - 142, tcx + 270, tcz + 142, track_fn(tcx, tcz, 253, 110, 139))
    gs = dict(length=330, depth=32, H=36, roof_h=62)
    place(L, "stand", lm.grandstand, (65, 32, 330), tcx - 165, tcz - 142 - 34, 9, **gs)
    for (fx, fz) in ((tcx - 290, tcz - 150), (tcx + 290, tcz - 150), (tcx - 290, tcz + 140), (tcx + 290, tcz + 140)):
        place(L, "floodlight", lm.floodlight, (164, 12, 12), fx - 6, fz - 6, 0)
    for gx in (tcx - 192, tcx + 192):
        place(L, "goal", goal, (8, 22, 3), gx - 1, tcz - 11, 0, flip=gx > tcx)


SHOPS = ["文具", "书店", "超市", "奶茶", "早餐", "复印", "眼镜", "面馆", "水果", "书店", "文具", "包子"]


def shop(rng, w, label):
    """临街小店: 2-3 storeys, real scale - the only normal-sized buildings around."""
    h = int(rng.choice([7, 7, 10]))
    A = np.zeros((12, 12, w), np.uint16)
    wall = B(str(rng.choice(["white_terracotta", "light_gray_concrete", "smooth_sandstone", "bricks", "white_concrete"])))
    A[:h, 2:12, :] = wall
    A[1:4, 2, 1:w - 1] = B("glass")
    A[1:3, 2, w // 2] = B("dark_oak_planks")
    A[5:7, 2, 1:w - 1:3] = B("glass")
    if h > 7:
        A[8:9, 2, 1:w - 1:3] = B("glass")
    sign = B(str(rng.choice(["red_concrete", "blue_concrete", "yellow_concrete", "green_concrete", "orange_concrete"])))
    A[4, 1, :] = sign
    awn = B(str(rng.choice(["red_wool", "blue_wool", "white_wool", "green_wool"])))
    A[3, 0:2, 1:w - 1] = awn
    A[h, 2:12, :] = B("smooth_stone_slab")
    return A[:, ::-1, :].copy()   # storefront faces north (-z)


def wall_seg(rng, n, axis="x"):
    A = np.zeros((5, 2, n), np.uint16)
    A[0:2, :, :] = B("bricks")
    A[2, :, :] = B("smooth_quartz")
    A[3:5, 0, :] = B("iron_bars")
    A[0:5, :, ::12] = B("bricks")
    A[5 - 1, :, ::12] = B("smooth_quartz")
    if axis == "z":
        A = A.transpose(0, 2, 1).copy()
    return A


def sliding_gate(rng, n):
    A = np.zeros((2, 1, n), np.uint16)
    A[:, 0, : n // 2 - 30] = B("iron_bars")
    A[1, 0, : n // 2 - 30] = B("iron_bars")
    A[:, 0, : n // 2 - 30:8] = B("light_blue_terracotta")
    return A


def goal(rng, flip=False):
    A = np.zeros((8, 22, 3), np.uint16)
    w = B("white_concrete")
    A[0:7, 0, 1] = w
    A[0:7, 21, 1] = w
    A[7, :, 1] = w
    A[0:8, :, 0 if not flip else 2] = np.where(A[0:8, :, 1] == 0, B("iron_bars"), 0)
    return A


# ---------------------------------------------------------------- whole campus
ENDLESS_ROW = -4
LINKED_ROW = -7              # the chain of linked teaching-and-lab blocks


def endless_segment(rng, dx, H, arch, first, last, char):
    """One 224-block piece of the endless teaching building (长廊楼)."""
    sc = __import__("schemes").SCHEMES["white_red"]
    D = 40
    faces = {"S": ("corridor", dict(accent_every=10, lit=0.02)), "N": ("windows", dict(accent_every=10, ac=0.1))}
    if char:
        faces["S"][1]["text"] = [dict(s=char, y_top=40, u_center=dx // 2 - 16, px=56, fg=B("white_concrete"),
                                      bg=B("red_terracotta"), bold=1)]
    if first:
        faces["W"] = ("windows", dict(ac=0, pilaster=False))
    if last:
        faces["E"] = ("windows", dict(ac=0, pilaster=False))
    A = bd.box(rng, dx, D, H, sc, faces, extra=30, piers=first or last)
    if arch:
        a0, a1 = arch
        ah = 48
        A[:ah, :, a0:a1] = 0
        A[ah:ah + 2, :, a0:a1] = sc.trim
        A[:ah, 1:D - 1, a0] = sc.wall
        A[:ah, 1:D - 1, a1 - 1] = sc.wall
        A[ah - 1, 1:D - 1, a0:a1] = sc.wall
    return A


def observatory(rng, R=60, H=100):
    n = 2 * R + 3
    A = np.zeros((H + R + 4, n, n), np.uint16)
    c = n // 2
    zz, xx = np.mgrid[0:n, 0:n] - c
    d = np.sqrt(zz ** 2 + xx ** 2)
    ring = (d <= R) & (d > R - 2)
    for y in range(H):
        A[y][ring] = B("white_concrete") if (y // 4) % 6 else B("light_gray_concrete")
    A[H][d <= R] = B("smooth_quartz")
    yy = np.arange(R + 1)[:, None, None]
    shell = (np.sqrt(zz[None] ** 2 + xx[None] ** 2 + yy ** 2) <= R) & (np.sqrt(zz[None] ** 2 + xx[None] ** 2 + yy ** 2) > R - 2.2)
    slit = (np.abs(xx) < 5)[None] & (zz[None] > 0)
    A[H + 1:H + R + 2][shell & ~slit] = B("white_concrete")
    A[H + 1:H + R + 2][shell & slit] = B("black_concrete")
    return A


def build(seed=20260901):
    rng = np.random.default_rng(seed)
    L = Layout()
    namer = Namer(rng)
    # base surfaces: everything inside the wall is asphalt (roads emerge between lots)
    L.rect(WEST_X, NORTH_Z, EAST_X, GATE_Z, ASPHALT)
    ioffs = range(-9, 10)
    roffs = range(-10, 3)
    xs_lines = [i * PITCH + LOT // 2 + ROAD // 2 for i in range(-10, 10)]
    zs_lines = [r * PITCH + ZOFF + LOT // 2 + ROAD // 2 for r in range(-11, 3)]
    def grid_lines(xs, zs):
        m = np.zeros(xs.shape, bool)
        for xl in xs_lines:
            m |= (xs == xl) & ((zs // 6) % 2 == 0) & (zs < SOUTH_ZONE)
        for zl in zs_lines:
            m |= (zs == zl) & ((xs // 6) % 2 == 0) & (zl < SOUTH_ZONE)
        return m, LINE
    L.fn(WEST_X, NORTH_Z, EAST_X, GATE_Z, grid_lines)

    south_zone(L, rng, namer)

    special = {(0, 1): "library", (-2, 1): "gym", (-2, 0): "canteen", (0, -1): "garden_globe",
               (-5, -2): "garden", (5, -6): "garden", (-7, -8): "garden", (3, -9): "garden", (8, 0): "garden",
               (-8, 1): "garden", (0, -6): "gym", (6, -2): "canteen", (0, -8): "water_tower", (-4, -6): "observatory",
               (7, -8): "observatory"}
    pg = {(i, r) for i in (2, 3, 4) for r in (0, 1)}
    playground(L, rng, 2 * PITCH - LOT // 2, 0 * PITCH + ZOFF - LOT // 2, 4 * PITCH + LOT // 2, 1 * PITCH + ZOFF + LOT // 2)
    # the endless building: one segment per lot column, arches where the roads pass
    ez = ENDLESS_ROW * PITCH + ZOFF
    Hend = bd.floors_h(76)
    cols = [i for i in ioffs if (i * PITCH - LOT // 2) >= WEST_X - 100 and (i * PITCH + LOT // 2) <= EAST_X + 100]
    for k, i in enumerate(cols):
        x0 = max(i * PITCH - PITCH // 2, WEST_X + 40)
        x1 = min(i * PITCH + PITCH // 2, EAST_X - 40)
        first, last = k == 0, k == len(cols) - 1
        arch = None
        ra = i * PITCH + LOT // 2 - x0
        if not last and ra + ROAD <= x1 - x0:
            arch = (ra, ra + ROAD)
        ch = None
        place(L, "endless", endless_segment, (Hend + 3 + 30, 40, x1 - x0), x0, ez - 20, 1000 + k,
              dx=x1 - x0, H=Hend, arch=arch, first=first, last=last, char=ch)
        # left-of-arch road gap on the west of the segment is also covered (segments abut)
    for r in roffs:
        for i in ioffs:
            rng = np.random.default_rng([seed, i + 100, r + 100])      # per-lot, so edits stay local
            cx = i * PITCH
            cz = r * PITCH + ZOFF
            x0, x1 = max(cx - LOT // 2, WEST_X + 6), min(cx + LOT // 2, EAST_X - 6)
            z0, z1 = max(cz - LOT // 2, NORTH_Z + 6), min(cz + LOT // 2, SOUTH_ZONE - 4)
            if x1 - x0 < 110 or z1 - z0 < 110:
                L.rect(x0, z0, x1, z1, GRASS)
                continue
            if r == 2 and -2 <= i <= 2:
                continue          # main building
            if (i, r) in pg:
                continue
            lot_ground(L, x0, z0, x1, z1)
            if r == LINKED_ROW:
                valid = [j for j in ioffs if min(j * PITCH + LOT // 2, EAST_X - 6) - max(j * PITCH - LOT // 2, WEST_X + 6) >= 110]
                first, last = i == valid[0], i == valid[-1]
                w = x1 - x0
                dxs = w if last else w + ROAD
                Bd, fl = 34, 22
                dz = ic.linked_size(dxs, Bd, fl)[1]
                zz = (z0 + z1) // 2 - dz // 2
                L.rect(x0 + 5, z0 + 5, x1 - 5, z1 - 5, GRASS)
                L.rect(x0, zz + dz, x1 + (0 if last else ROAD), zz + dz + 14, PLAZA)
                place(L, "linked", ic.linked_segment, ic.linked_size(dxs, Bd, fl), x0, zz, int(rng.integers(1 << 30)),
                      dx=dxs, blocks=2, Bd=Bd, floors=fl, scheme="tile_gray", seed=int(rng.integers(1 << 30)),
                      first=first, last=last, road=(None, None) if last else (w, w + ROAD))
                trees_along(L, rng, x0 + 6, zz + dz + 24, x1 - 6, zz + dz + 24, spacing=10)
                trees_along(L, rng, x0 + 6, zz - 12, x1 - 6, zz - 12, spacing=10)
                continue
            if r == ENDLESS_ROW:
                # linear park along the endless building
                L.rect(x0 + 5, z0 + 5, x1 - 5, z1 - 5, GRASS)
                L.rect(x0, ez + 20, x1, ez + 34, PLAZA)
                trees_along(L, rng, x0 + 6, ez + 44, x1 - 6, ez + 44, spacing=10)
                trees_along(L, rng, x0 + 6, ez - 30, x1 - 6, ez - 30, spacing=10)
                continue
            kind = special.get((i, r))
            if kind is None:
                rr = rng.random()
                kinds = [("slabs", .14), ("courtyard", .08), ("towers", .05), ("dorms", .13), ("lab", .05),
                         ("gothic", .07), ("cocoon", .09), ("twin", .09), ("ring", .08), ("terrace", .08),
                         ("wave", .08), ("bow", .06)]
                acc = 0.0
                for kind, p in kinds:
                    acc += p
                    if rr < acc:
                        break
            if kind == "library":
                lb = _sz(lm.library, {})
                place(L, "library", lm.library, lb, cx - lb[2] // 2, z1 - lb[1] - 4, 21)
                L.rect(x0, z1 - 50, x1, z1, PLAZA)
            elif kind == "gym":
                lot_gym(L, rng, x0, z0, x1, z1, namer)
            elif kind == "canteen":
                lot_canteen(L, rng, x0, z0, x1, z1, namer)
            elif kind == "garden" and x1 - x0 >= 192 and z1 - z0 >= 192 and mcb_place(L, "twilight_grove", x0, z0):
                continue                     # 暮色树林 (mcbuild); it brings its own edge planting
            elif kind.startswith("garden"):
                lot_garden(L, rng, x0, z0, x1, z1, namer, globe=kind == "garden_globe")
            elif kind == "water_tower":
                L.rect(x0 + 5, z0 + 5, x1 - 5, z1 - 5, PLAZA)
                mcb_place(L, "water_tower", cx, cz)
            elif kind == "observatory":
                place(L, "observatory", observatory, (164, 123, 123), cx - 61, cz - 61, 0)
            elif kind in LANDMARK_LOTS:
                LANDMARK_LOTS[kind](L, rng, x0, z0, x1, z1, namer)
            else:
                {"slabs": lot_slabs, "courtyard": lot_courtyard, "towers": lot_towers,
                 "dorms": lot_dorms, "lab": lot_lab}[kind](L, rng, x0, z0, x1, z1, namer)
            lot_trees(L, rng, x0, z0, x1, z1)
    return L


# ---------------------------------------------------------------- rasterising
def paint_ground(L, x0, z0, dx, dz):
    G = np.full((dz, dx), GRASS, np.uint16)
    for f in L.ground:
        kind, a0, b0, a1, b1, v = f
        xa, xb = max(a0, x0), min(a1, x0 + dx)
        za, zb = max(b0, z0), min(b1, z0 + dz)
        if xa >= xb or za >= zb:
            continue
        if kind == "rect":
            G[za - z0:zb - z0, xa - x0:xb - x0] = v
        else:
            zs, xs = np.mgrid[za:zb, xa:xb]
            m, val = v(xs, zs)
            sub = G[za - z0:zb - z0, xa - x0:xb - x0]
            if np.ndim(val) == 0:
                sub[m] = val
            else:
                sub[m] = val[m]
    return G


class Index:
    """Bucket pieces by 256-block cells for fast region queries."""
    CELL = 256

    def __init__(self, pieces):
        self.cells = {}
        for k, p in enumerate(pieces):
            for cx in range(p.x // self.CELL, (p.x1 - 1) // self.CELL + 1):
                for cz in range(p.z // self.CELL, (p.z1 - 1) // self.CELL + 1):
                    self.cells.setdefault((cx, cz), []).append(k)
        self.pieces = pieces

    def query(self, x0, z0, dx, dz):
        ks = set()
        for cx in range(x0 // self.CELL, (x0 + dx - 1) // self.CELL + 1):
            for cz in range(z0 // self.CELL, (z0 + dz - 1) // self.CELL + 1):
                ks.update(self.cells.get((cx, cz), ()))
        out = []
        for k in sorted(ks):
            p = self.pieces[k]
            if p.x < x0 + dx and p.x1 > x0 and p.z < z0 + dz and p.z1 > z0:
                out.append(p)
        return out


def compose(L, index, x0, z0, dx, dz):
    """Voxel array V[y, z, x] (y from -64) for a rectangle of the world."""
    V = np.zeros((384, dz, dx), np.uint16)
    V[0] = B("bedrock")
    V[1:3] = B("dirt")
    V[3] = paint_ground(L, x0, z0, dx, dz)
    for p in index.query(x0, z0, dx, dz):
        A = p.build()
        bd.paste(V, A, p.y + 64, p.z - z0, p.x - x0)
    return V
