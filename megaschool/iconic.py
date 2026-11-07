"""Teaching buildings that are not boxes.

A small massing engine turns a volume (boolean M[y, z, x]) into a building:
a facade skin on the outer layer (patterned by an along-the-facade coordinate
U and the floor rhythm), a dark interior layer behind it with some lit
classrooms, roofs and parapets on every top surface, and - where a building
has them - open corridors (外廊) cut into one face: floor slabs, a parapet,
columns, ceiling lights and a back wall with classroom windows and doors.

The building types are loosely modelled on real campus landmarks (none is a
copy): a bow-shaped kilometre-long hall, a Gothic "cathedral of learning", a
cocoon tower in a white diagrid, twin towers joined into a gate, a ring
with corridors on its inner face, a stepped terrace block, a wave-shaped slab
and a chain of linked teaching-and-lab blocks.

Every generator returns A[y, z, x] (uint16, 0 = leave as is) of a size the
caller can compute without building it (see the *_size helpers)."""
from __future__ import annotations

import math

import numpy as np

from anvil import B
from schemes import SCHEMES

FH = 8                      # floor height: giant storeys, so a tall building has few, large floors
WIN = (2, 6)                # window rows within a storey (sill row 1, lintel row 7)
GROUP = 40                  # window groups repeat every 40 blocks (60 % glass, 40 % solid pier)


def H_of(floors):
    return floors * FH + 1


def _hash(*a):
    """Deterministic pseudo-random [0, 1) for integer arrays."""
    with np.errstate(over="ignore"):
        return _hash_(*a)


def _hash_(*a):
    h = np.zeros(np.broadcast(*a).shape, np.uint64)
    for k, v in enumerate(a):
        h ^= (np.asarray(v).astype(np.int64).astype(np.uint64) + np.uint64(0x9E3779B97F4A7C15 * (k + 1) % (1 << 63))) * np.uint64(0xBF58476D1CE4E5B9)
        h ^= h >> np.uint64(29)
    h *= np.uint64(0x94D049BB133111EB)
    h ^= h >> np.uint64(32)
    return (h & np.uint64(0xFFFFFF)).astype(np.float64) / float(1 << 24)


def erode(M):
    """4-neighbour erosion in the horizontal plane (all layers at once)."""
    E = M.copy()
    E[:, 1:, :] &= M[:, :-1, :]
    E[:, :-1, :] &= M[:, 1:, :]
    E[:, :, 1:] &= M[:, :, :-1]
    E[:, :, :-1] &= M[:, :, 1:]
    E[:, 0, :] = E[:, -1, :] = False
    E[:, :, 0] = E[:, :, -1] = False
    return E


class Look:
    """Materials of one building (a scheme plus a few extra roles)."""

    def __init__(self, scheme, **over):
        theme = THEMES.get(scheme)
        sc = SCHEMES[theme[0] if theme else scheme]
        self.wall, self.accent, self.band, self.rail = sc.wall, sc.accent, sc.band, sc.rail
        self.column, self.floor, self.glass, self.back = sc.column, sc.floor, sc.glass, sc.back
        self.lit, self.door, self.roof, self.trim = sc.lit, sc.door, sc.roof, sc.trim
        self.plinth = B("polished_deepslate")
        self.light = B("ochre_froglight")             # corridor ceiling lights
        for k, v in over.items():
            setattr(self, k, B(v) if isinstance(v, str) else v)
        if theme:                                     # an environment theme wins over a type's own look
            for k, v in theme[1].items():
                setattr(self, k, B(v))


# Environment themes for the schools outside the campus: (base scheme, role -> block)
THEMES = {
    "t_sea": ("blue_white", dict(wall="white_concrete", accent="light_blue_terracotta", band="light_blue_concrete",
                                 column="white_concrete", glass="light_blue_stained_glass", back="blue_terracotta",
                                 roof="light_blue_concrete", trim="smooth_quartz", plinth="prismarine_bricks",
                                 light="sea_lantern", lit="sea_lantern")),
    "t_sky": ("blue_white", dict(wall="smooth_quartz", accent="quartz_bricks", band="chiseled_quartz_block",
                                 column="quartz_block", glass="light_blue_stained_glass", back="light_blue_terracotta",
                                 roof="quartz_bricks", trim="chiseled_quartz_block", plinth="quartz_bricks",
                                 light="pearlescent_froglight", lit="pearlescent_froglight")),
    "t_sky_sand": ("cream_brick", dict(wall="smooth_sandstone", accent="cut_sandstone", band="chiseled_sandstone",
                                       column="cut_sandstone", glass="yellow_stained_glass", back="brown_terracotta",
                                       roof="smooth_sandstone", trim="chiseled_sandstone", plinth="sandstone",
                                       light="ochre_froglight")),
    "t_sky_stone": ("brutal", dict(wall="stone_bricks", accent="mossy_stone_bricks", band="chiseled_stone_bricks",
                                   column="polished_andesite", glass="gray_stained_glass", back="black_concrete",
                                   roof="stone_bricks", trim="smooth_stone", plinth="polished_deepslate")),
    "t_sky_brick": ("red_brick", dict(wall="bricks", accent="smooth_quartz", band="smooth_quartz", column="smooth_quartz",
                                      glass="glass", back="gray_concrete", roof="dark_prismarine", trim="smooth_quartz",
                                      plinth="polished_blackstone_bricks")),
    "t_end": ("brutal", dict(wall="purpur_block", accent="end_stone_bricks", band="end_stone_bricks", rail="purpur_block",
                             column="end_stone_bricks", floor="end_stone_bricks", glass="magenta_stained_glass",
                             back="obsidian", lit="pearlescent_froglight", roof="purpur_block", trim="end_stone_bricks",
                             plinth="obsidian", light="pearlescent_froglight", door="crying_obsidian")),
    "t_nether": ("brutal", dict(wall="nether_bricks", accent="red_nether_bricks", band="polished_blackstone_bricks",
                                rail="polished_blackstone_bricks", column="polished_blackstone", floor="polished_blackstone",
                                glass="red_stained_glass", back="black_concrete", lit="shroomlight", roof="blackstone",
                                trim="gilded_blackstone", plinth="polished_blackstone_bricks", light="shroomlight",
                                door="crimson_planks")),
    "t_desert": ("cream_brick", dict(wall="smooth_sandstone", accent="cut_red_sandstone", band="cut_sandstone",
                                     rail="smooth_sandstone", column="cut_sandstone", floor="smooth_sandstone",
                                     glass="orange_stained_glass", back="brown_terracotta", lit="ochre_froglight",
                                     roof="sandstone", trim="chiseled_sandstone", plinth="red_sandstone",
                                     light="ochre_froglight", door="acacia_planks")),
    "t_cliff": ("brutal", dict(wall="stone_bricks", accent="mossy_stone_bricks", band="smooth_stone",
                               column="polished_andesite", glass="glass", back="black_concrete", lit="ochre_froglight",
                               roof="moss_block", trim="smooth_stone", plinth="polished_deepslate")),
    "t_glass": ("gray_modern", dict(wall="white_concrete", accent="light_gray_concrete", band="white_concrete",
                                    column="white_concrete", glass="light_blue_stained_glass", back="cyan_terracotta",
                                    lit="sea_lantern", roof="white_concrete", trim="smooth_quartz", light="sea_lantern")),
}


def skin(M, U, look, style="grid", bay=8, lit=0.03, seed=0, plinth=0, crown=0, piers2d=None,
         dc=None, cd=3, corridor_open_ground=False, top_trim=True):
    """Turn the volume M into blocks.  U: (z, x) along-facade coordinate.
    dc: (z, x) depth from the corridor face (inf/None = no corridor)."""
    h = M.shape[0]
    A = np.zeros(M.shape, np.uint16)
    E1 = erode(M)
    outer = M & ~E1
    second = E1 & ~erode(E1)
    # --- outer skin
    y, z, x = np.nonzero(outer)
    u = U[z, x]
    r = y % FH
    b = np.full(len(y), look.wall, np.uint16)
    # Few, large openings instead of a grid of holes: windows are gathered
    # into wide groups (long horizontal slots or tall vertical strips)
    # separated by broad solid piers, and every few floors a solid belt.
    fl = y // FH
    gp = np.mod(u, GROUP)
    in_group = (gp >= GROUP * 0.2) & (gp < GROUP * 0.8)
    belt = np.mod(fl, 5) == 4
    if style == "grid":                       # long window slots in groups, solid piers and belts
        b[(r >= WIN[0]) & (r <= WIN[1]) & in_group & ~belt] = look.glass
        b[(r == 0) & in_group] = look.band
    elif style == "ribbon":                   # continuous bands, interrupted only by big piers
        b[(r >= WIN[0]) & (r <= WIN[1]) & (np.mod(u, GROUP) >= 6) & ~belt] = look.glass
        b[r == 0] = look.band
    elif style == "fins":                     # tall glass strips between broad fins
        strip = np.mod(u, 20) >= 12
        b[strip & (np.mod(fl, 8) != 7)] = look.glass
        b[strip & (r == 0) & (np.mod(fl, 8) != 7)] = look.back
    elif style == "gothic":                   # unbroken vertical piers, dark spandrels
        b[:] = look.glass
        b[(r <= 1) & (np.mod(fl, 3) != 0)] = look.back
        b[(r <= 1) & (np.mod(fl, 3) == 0)] = look.band
        b[np.mod(u, 8) < 4] = look.column
    elif style == "diagrid":                  # white diamond lattice over dark glass
        P = bay * 3.0
        k = 0.9
        d1 = np.mod(u + y * k, P)
        d2 = np.mod(u - y * k, P)
        b[:] = look.glass
        b[(d1 < 2.0) | (d2 < 2.0)] = look.column
        b[(r == 0) & (np.mod(fl, 6) == 0)] = look.band
    A[y, z, x] = b
    if piers2d is not None:
        P3 = outer & piers2d[None]
        A[P3] = look.column
    if plinth:
        A[:plinth][outer[:plinth]] = look.plinth
    if crown:
        # cornice: the top `crown` rows of every column of the volume
        top = np.zeros(M.shape[1:], np.int32)
        any_ = M.any(axis=0)
        top[any_] = h - np.argmax(M[::-1], axis=0)[any_]          # first empty row from the top
        Y = np.arange(h)[:, None, None]
        cm = outer & (Y >= (top[None] - crown)) & (Y < top[None])
        A[cm] = look.trim
    # --- interior layer behind the skin, some classrooms lit
    y, z, x = np.nonzero(second)
    on = _hash(y // FH, np.floor(U[z, x] / bay).astype(np.int64), seed) < lit
    A[y, z, x] = np.where(on, look.lit, look.back).astype(np.uint16)
    # --- open corridors (only the columns of cells near the corridor face)
    if dc is not None:
        zi, xi = np.nonzero(np.isfinite(dc) & (dc < cd + 2))
        if len(zi):
            sub = M[:, zi, xi]
            col = A[:, zi, xi]
            d = dc[zi, xi][None]
            u = U[zi, xi][None]
            Y = np.arange(h)[:, None]
            R = Y % FH
            mu = np.mod(u, bay)
            C = sub & (d < cd)
            if not corridor_open_ground:
                C &= Y >= FH
            # big solid frames: a 6-wide pier every GROUP blocks and a solid belt
            # storey every 5th floor, so the corridors read as large panels
            C &= ~((np.mod(u, GROUP) < 6) | (np.mod(Y // FH, 5) == 4))
            col[C] = 0
            col[C & (R == 0)] = look.floor
            col[C & (R == 0) & (d >= 1) & (d < 2) & (mu >= bay // 2) & (mu < bay // 2 + 1) & (Y > FH)] = look.light
            col[C & (d < 1) & (R >= 1) & (R <= 2)] = look.rail
            col[C & (d < 2) & (np.mod(u, bay * 2) < 3)] = look.column
            g0 = 0 if corridor_open_ground else FH
            Wb = sub & (d >= cd) & (d < cd + 1) & (Y >= g0)
            alt = np.mod(np.floor(u / bay), 2) == 0
            wb = np.where((R >= WIN[0]) & (R <= WIN[1] - 1) & (mu >= 2) & (mu < bay - 6) & alt, look.glass,
                          np.where((R >= 1) & (R <= 5) & (mu >= bay - 4) & (mu < bay - 1), look.door,
                                   np.where(R == 0, look.floor, look.wall))).astype(np.uint16)
            col[Wb] = wb[Wb]
            Bk = sub & (d >= cd + 1) & (d < cd + 2) & (Y >= g0)
            on = _hash(np.broadcast_to(Y // FH, Bk.shape), np.broadcast_to(np.floor(u / bay).astype(np.int64), Bk.shape),
                       seed + 7) < lit * 4
            col[Bk] = np.where(on, look.lit, look.back).astype(np.uint16)[Bk]
            A[:, zi, xi] = col
    # --- roofs and parapets on every top surface
    T = M.copy()
    T[:-1] &= ~M[1:]
    A[T] = look.roof
    A[T & outer] = look.trim
    if top_trim:
        P = np.zeros(M.shape, bool)
        P[1:] = T[:-1] & outer[:-1]
        P &= ~M
        A[P] = look.trim
    return A


def yy(h):
    return np.arange(h)[:, None, None]


# ================================================================ bow-shaped hall (弯弓形)
def _steps(steps, t):
    """steps: [(|angle| below which, floors), ...] in increasing angle."""
    for amax, f in steps:
        if abs(t) < amax:
            return f
    return steps[-1][1]


def arc_segment(rng, dx, dz, hh, cx, cz, R, D, a0, a1, steps, scheme="white_red", style="grid",
                gates=(), hole=None, end_towers=(), seed=0, lit=0.03, bay=16):
    """One piece of a hall bent along a circle (centre (cx, cz) in local
    coordinates, inner radius R, depth D, angles a0..a1 in degrees, 0 = the
    point of the arc nearest -z, positive toward +x).  The concave side has
    open corridors on every floor.  steps: [(|deg| limit, floors), ...].
    gates: angles (deg) of ground-level passages; hole: local rect cleared
    (x0, z0, x1, z1); end_towers: angles where taller stair towers stand."""
    look = Look(scheme)
    zs, xs = np.mgrid[0:dz, 0:dx]
    ddx, ddz = xs + 0.5 - cx, zs + 0.5 - cz
    r = np.hypot(ddx, ddz)
    th = np.degrees(np.arctan2(ddx, -ddz))
    F2 = (r >= R) & (r < R + D) & (th >= a0) & (th < a1)
    Hm = np.zeros((dz, dx), np.int32)
    tv = np.round(th).astype(int)
    for t in np.unique(tv[F2]):
        Hm[F2 & (tv == t)] = H_of(_steps(steps, float(t)))
    for (ta, extra) in end_towers:             # stair towers: thicker, taller, cut flush
        sel = (np.abs(th - ta) < 1.4) & (r >= R - 4) & (r < R + D + 4)
        Hm[sel] = np.maximum(Hm[sel], H_of(_steps(steps, ta) + extra))
        F2 |= sel
    M = yy(hh) < Hm[None]
    for g in gates:                            # passages 18 wide, 7 floors tall
        sel = np.abs((th - g) * math.pi / 180 * R) < 9
        M[:H_of(4) - 1, sel] = False
    if hole is not None:
        x0, z0, x1, z1 = hole
        M[:, max(0, z0):max(0, z1), max(0, x0):max(0, x1)] = False
    U = np.radians(th) * R
    dc = np.where(F2, r - R, np.inf)
    # giant piers on the convex face every 40 blocks, 3 thick
    piers = (r >= R + D - 3) & (np.mod(U, 40) < 3)
    A = skin(M, U, look, style=style, bay=bay, lit=lit, seed=seed, plinth=H_of(1), crown=9, piers2d=piers,
             dc=dc, cd=6)
    # gate vaults: dark soffit with a lit band
    for g in gates:
        sel = (np.abs((th - g) * math.pi / 180 * R) < 9) & F2
        A[H_of(4) - 1, sel] = look.plinth
        A[H_of(4) - 2, sel & (np.mod(U, 6) < 1)] = look.light
    return A


# ================================================================ Gothic tower (学习大教堂)
def gothic_tower(rng, W=104, floors=75, scheme="brutal", seed=0, lit=0.03):
    """A stone tower with unbroken vertical ribs: a broad base block, the
    shaft with chamfered corners, three setbacks, pinnacles on every step
    and a stepped pyramidal crown."""
    look = Look(scheme, column="polished_andesite", wall="stone_bricks", band="chiseled_stone_bricks",
                glass="gray_stained_glass", back="black_concrete", roof="stone_bricks", trim="smooth_stone",
                plinth="polished_deepslate")
    H = H_of(floors)
    crown_h = 70
    hh = H + crown_h
    A_M = np.zeros((hh, W, W), bool)
    zs, xs = np.mgrid[0:W, 0:W]
    c = (W - 1) / 2
    ax, az = np.abs(xs - c), np.abs(zs - c)
    tiers = [(0, H_of(7), W / 2, 14),                # (y0, y1, half width, chamfer)
             (H_of(7), int(H * 0.80), W * 0.36, 10),
             (int(H * 0.80), int(H * 0.88), W * 0.30, 8),
             (int(H * 0.88), int(H * 0.95), W * 0.24, 6),
             (int(H * 0.95), H, W * 0.18, 4)]
    for (y0, y1, hw, ch) in tiers:
        f = (ax <= hw) & (az <= hw) & (ax + az <= 2 * hw - ch)
        A_M[y0:y1, f] = True
    # crown: stepped pyramid to a spire
    for k in range(crown_h):
        hw = W * 0.16 * (1 - k / crown_h) ** 1.4
        if hw < 0.6:
            break
        A_M[H + k, (ax <= hw) & (az <= hw)] = True
    # U: perimeter-ish coordinate of a square (x on N/S faces, z on E/W faces)
    U = np.where(ax >= az, zs, xs).astype(np.float64)
    A = skin(A_M, U, look, style="gothic", bay=16, lit=lit, seed=seed, plinth=H_of(2), crown=0)
    # pinnacles on the corners and along the edge of every setback
    for (y0, y1, hw, ch) in tiers[:-1]:
        f = (ax <= hw) & (az <= hw) & (ax + az <= 2 * hw - ch)
        ring = f & ~((ax <= hw - 1) & (az <= hw - 1) & (ax + az <= 2 * hw - ch - 2))
        pin = ring & ((np.mod(xs + zs, 6) == 0) | (ax + az >= 2 * hw - ch - 1))
        for k in range(6):
            sel = pin & ~A_M[min(hh - 1, y1 + k)]
            A[y1 + k][sel] = look.column if k < 5 else look.trim
    # pointed lancet entrance on the south face
    e0 = int(c) - 7
    for k in range(H_of(3)):
        w = 7 if k < H_of(2) else max(0, int(7 * (1 - (k - H_of(2)) / (H_of(1) + 1))))
        A[k, W - 4:W, int(c) - w:int(c) + w + 1] = 0
        A[k, W - 5, int(c) - w:int(c) + w + 1] = look.lit if k % 4 == 2 else look.back
    A[0, W - 5:W, e0:e0 + 15] = look.floor
    # spire tip light
    A[hh - 1, int(c), int(c)] = B("sea_lantern") if A_M[hh - 2, int(c), int(c)] else 0
    return A


def gothic_size(W=104, floors=75):
    return (H_of(floors) + 70, W, W)


# ================================================================ cocoon tower (茧形塔)
def cocoon_tower(rng, W=84, floors=55, scheme="gray_modern", seed=0, lit=0.03):
    """An egg-shaped tower: an elliptical plan that swells to its widest a
    third of the way up and closes to a rounded tip, wrapped in a white
    diamond lattice over dark glass.  A low lens-shaped podium at its foot."""
    look = Look(scheme, column="white_concrete", glass="gray_stained_glass", back="black_concrete",
                band="white_concrete", roof="white_concrete", trim="white_concrete", lit="sea_lantern",
                plinth="white_concrete")
    H = H_of(floors)
    hh = H + 8
    zs, xs = np.mgrid[0:W, 0:W]
    c = (W - 1) / 2
    M = np.zeros((hh, W, W), bool)
    for y in range(hh):
        t = y / H
        if t <= 1.0:
            s = 0.66 + 0.34 * math.sin(math.pi * min(1.0, t / 0.68) * 0.5) ** 0.8
            if t > 0.68:
                q = (t - 0.68) / 0.32
                s = math.sqrt(max(0.0, 1 - q * q)) * 1.0
        else:
            s = 0
        a, b = (W / 2 - 1) * s, (W / 2 - 1) * s * 0.72
        if a < 1:
            continue
        M[y] = ((xs - c) / a) ** 2 + ((zs - c) / b) ** 2 <= 1
    th = np.arctan2(zs - c, xs - c)
    U = th * (W / 2 * 0.86)
    A = skin(M, U, look, style="diagrid", bay=10, lit=lit, seed=seed, crown=0)
    return A


def cocoon_size(W=84, floors=55):
    return (H_of(floors) + 8, W, W)


# ================================================================ twin towers joined into a gate (双塔门楼)
def twin_gate(rng, Tw=52, Td=30, gap=44, floors=60, scheme="gray_modern", seed=0, lit=0.03):
    """Two slab towers side by side; their top fifth is one block bridging the
    gap, so the pair reads as a gigantic gate.  A low hall with a tall
    opening joins their feet.  White vertical fins over dark glass."""
    look = Look(scheme, column="white_concrete", glass="gray_stained_glass", back="black_concrete",
                band="light_gray_concrete", roof="light_gray_concrete", trim="white_concrete")
    H = H_of(floors)
    dx = 2 * Tw + gap
    dz = Td
    hh = H + 16
    M = np.zeros((hh, dz, dx), bool)
    M[:H, :, :Tw] = True
    M[:H, :, Tw + gap:] = True
    yb = H_of(int(floors * 0.72))
    M[yb:H, 2:dz - 2, :] = True                       # the bridge
    M[:H_of(5), 4:dz - 4, Tw:Tw + gap] = True         # hall between the feet
    M[:H_of(4), 4:dz - 4, Tw + 8:Tw + gap - 8] = False   # its tall opening
    # stepped crowns
    M[H:H + 8, 3:dz - 3, 3:Tw - 3] = True
    M[H:H + 8, 3:dz - 3, Tw + gap + 3:dx - 3] = True
    M[H + 8:H + 16, 6:dz - 6, 8:Tw - 8] = True
    M[H + 8:H + 16, 6:dz - 6, Tw + gap + 8:dx - 8] = True
    zs, xs = np.mgrid[0:dz, 0:dx]
    U = xs.astype(np.float64) + zs
    A = skin(M, U, look, style="fins", bay=16, lit=lit, seed=seed, plinth=H_of(1), crown=0)
    # the bridge's underside lit, and a band of light where it meets the towers
    A[yb, 2:dz - 2, Tw:Tw + gap] = look.plinth
    A[yb, 4:dz - 4:4, Tw + 2:Tw + gap - 2:4] = look.light
    return A


def twin_size(Tw=52, Td=30, gap=44, floors=60):
    return (H_of(floors) + 16, Td, 2 * Tw + gap)


# ================================================================ ring with inner corridors (环形外廊楼)
def ring_hall(rng, O=176, thick=26, floors=22, scheme="white_red", seed=0, lit=0.03):
    """A drum: a ring of classrooms whose inner face is open corridors on
    every floor (rings of light at dusk); punched windows and giant piers
    outside, four ground-level gateways."""
    look = Look(scheme)
    H = H_of(floors)
    zs, xs = np.mgrid[0:O, 0:O]
    c = (O - 1) / 2
    r = np.hypot(xs - c, zs - c)
    Ro = O / 2 - 1
    Ri = Ro - thick
    F2 = (r <= Ro) & (r > Ri)
    # a crown: the outer 6 blocks rise 3 floors higher every 30 degrees
    th = np.degrees(np.arctan2(zs - c, xs - c))
    Hm = np.where(F2, H, 0)
    Hm = np.where(F2 & (r > Ro - 6) & (np.mod(th + 360, 30) < 15), H_of(floors + 2), Hm)
    M = yy(Hm.max() + 1) < Hm[None]
    for a in (0, 90, 180, 270):                         # gateways
        sel = np.abs(((th - a + 180) % 360) - 180) * math.pi / 180 * Ri < 7
        M[:H_of(2) - 1, sel] = False
    U = np.radians(th) * Ro
    dc = np.where(F2, r - Ri, np.inf)                   # measured from the inner face outward
    piers = (r > Ro - 3) & (np.mod(U, 36) < 3)
    A = skin(M, U, look, style="grid", bay=16, lit=lit, seed=seed, plinth=H_of(1), crown=5, piers2d=piers,
             dc=dc, cd=6)
    return A


def ring_size(O=176, floors=22):
    return (H_of(floors + 2) + 1, O, O)


# ================================================================ stepped terrace block (退台梯形楼)
def terrace(rng, L=176, Dbase=120, tiers=6, tier_floors=4, step=9, scheme="cream_brick", seed=0, lit=0.03,
            square=False):
    """A long block stepping back on both long sides like a ziggurat: every
    tier's edge is an open corridor with a planted parapet."""
    look = Look(scheme)
    Ht = H_of(tiers * tier_floors)
    dz, dx = Dbase, L
    zs, xs = np.mgrid[0:dz, 0:dx]
    dmid = np.abs(zs + 0.5 - dz / 2)
    if square:                                   # ziggurat: steps on all four sides
        dmid = np.maximum(dmid, np.abs(xs + 0.5 - dx / 2) - (dx - dz) / 2)
    Hm = np.zeros((dz, dx), np.int32)
    for k in range(tiers):
        half = dz / 2 - k * step
        sel = dmid < half
        Hm[sel] = H_of((k + 1) * tier_floors)
    if not square:
        Hm[(xs < 2) | (xs >= dx - 2)] = 0
    M = yy(Ht + 2) < Hm[None]
    U = xs.astype(np.float64)
    # corridor depth: distance from the nearest tier edge, but only on the
    # top `tier_floors` floors of each tier (where that edge is the facade)
    edge = np.zeros((dz, dx))
    for k in range(tiers):
        half = dz / 2 - k * step
        edge = np.where(dmid < half, half - dmid, edge)
    A = skin(M, U, look, style="grid", bay=16, lit=lit, seed=seed, plinth=H_of(1), crown=0)
    # cut corridors tier by tier (each tier only on its exposed floors)
    for k in range(tiers):
        half = dz / 2 - k * step
        y0, y1 = H_of(k * tier_floors), H_of((k + 1) * tier_floors)
        band = (dmid < half) & (dmid >= half - 5) & ((xs >= 2) & (xs < dx - 2) | square)
        sub = M[y0:y1] & band[None]
        sub[:FH] &= k > 0
        Y = yy(y1 - y0)
        R = (Y + y0) % FH
        A[y0:y1][sub] = 0
        A[y0:y1][sub & (R == 0)] = look.floor
        d = (half - dmid)[None]
        A[y0:y1][sub & (d < 1) & (R >= 1) & (R <= 2)] = look.rail
        A[y0:y1][sub & (d < 2) & (np.mod(xs, 32)[None] < 3)] = look.column
        A[y0:y1][sub & (R == 0) & (d >= 1) & (d < 2) & (np.mod(xs, 16)[None] == 8) & (Y > 0)] = look.light
        # back wall: windows and doors
        wb = M[y0:y1] & ((dmid >= half - 6) & (dmid < half - 5))[None]
        m_ = np.mod(xs, 16)[None]
        alt = (np.mod(xs // 16, 2) == 0)[None]
        blk = np.where((R >= WIN[0]) & (R <= WIN[1] - 1) & (m_ >= 2) & (m_ < 10) & alt, look.glass,
                       np.where((R >= 1) & (R <= 5) & (m_ >= 12) & (m_ < 15), look.door, np.where(R == 0, look.floor, look.wall)))
        A[y0:y1][wb] = blk.astype(np.uint16)[wb] if wb.any() else A[y0:y1][wb]
    # planters on every terrace (the roof strip in front of the next tier)
    T = M.copy()
    T[:-1] &= ~M[1:]
    yv, zv, xv = np.nonzero(T)
    keep = (yv + 1 < A.shape[0]) & (A[np.minimum(yv + 1, A.shape[0] - 1), zv, xv] == look.trim)
    A[yv[keep] + 1, zv[keep], xv[keep]] = B("moss_block")
    leaf = keep & (np.mod(xv, 3) != 0) & (yv + 2 < A.shape[0])
    A[yv[leaf] + 2, zv[leaf], xv[leaf]] = B("azalea_leaves[distance=1,persistent=true,waterlogged=false]")
    return A


def terrace_size(L=176, Dbase=120, tiers=6, tier_floors=4):
    return (H_of(tiers * tier_floors) + 2, Dbase, L)


# ================================================================ wave slab (波浪形外廊楼)
def wave_slab(rng, L=176, amp=22, wl=176, Dp=24, floors=24, scheme="blue_white", seed=0, lit=0.03,
              corridor="S"):
    """A slab whose plan follows one full sine wave; open corridors along
    its south (or north) face, ribbon windows behind the other."""
    look = Look(scheme)
    H = H_of(floors)
    dz = 2 * amp + Dp + 2
    zs, xs = np.mgrid[0:dz, 0:L]
    zc = dz / 2 + amp * np.sin(2 * math.pi * xs / wl)
    d = zs + 0.5 - zc
    F2 = (np.abs(d) < Dp / 2) & (xs >= 1) & (xs < L - 1)
    Hm = np.where(F2, H, 0)
    # the crests rise: +6 floors where the wave is at its extremes
    Hm = np.where(F2 & (np.abs(np.sin(2 * math.pi * xs / wl)) > 0.85), H_of(floors + 3), Hm)
    M = yy(H_of(floors + 3) + 2) < Hm[None]
    U = xs.astype(np.float64)
    if corridor == "S":
        dc = np.where(F2, Dp / 2 - d, np.inf)
    else:
        dc = np.where(F2, Dp / 2 + d, np.inf)
    A = skin(M, U, look, style="ribbon", bay=16, lit=lit, seed=seed, plinth=H_of(1), crown=4, dc=dc, cd=6)
    return A


def wave_size(L=176, amp=22, Dp=24, floors=24):
    return (H_of(floors + 3) + 2, 2 * amp + Dp + 2, L)


# ================================================================ linked teaching-and-lab chain (超长连体楼)
def linked_segment(rng, dx, blocks=2, Bw=56, Bd=34, floors=22, scheme="tile_gray", seed=0, lit=0.03,
                   first=False, last=False, road=(None, None)):
    """One lot's worth of the chain: `blocks` teaching blocks (corridors on
    the south face) on a continuous 3-floor podium with a ground arcade,
    linked at four levels by glazed bridges that run on over the roads to
    the next segment.  road: local x-range of the road this segment spans
    (the podium becomes an arch there)."""
    look = Look(scheme)
    H = H_of(floors)
    dz = Bd + 16
    hh = H + 10
    M = np.zeros((hh, dz, dx), bool)
    zs, xs = np.mgrid[0:dz, 0:dx]
    pitch = dx / blocks
    centres = [int(pitch * (k + 0.5)) for k in range(blocks)]
    for cxk in centres:
        M[:H, 8:8 + Bd, cxk - Bw // 2:cxk + Bw // 2] = True
        M[H:H + 10, 12:12 + Bd - 8, cxk - Bw // 2 + 6:cxk + Bw // 2 - 6] = True     # rooftop lantern
    x0 = 0 if not first else 4
    x1 = dx if not last else dx - 4
    pod = H_of(2)
    M[:pod, 4:dz - 4, x0:x1] = True
    M[:H_of(1) - 1, dz - 10:dz - 4, x0:x1] = False                           # arcade
    ra, rb = road
    if ra is not None:
        M[:H_of(2) - 1, :, ra:rb] = False                                    # arch over the road
        M[H_of(2) - 1:pod + FH, 4:dz - 4, ra:rb] = True
    # glazed bridges at four levels (12 wide, 2 floors), run the whole length
    for f in (6, 11, 16, floors - 2):
        y0 = H_of(f) - 1
        M[y0:y0 + H_of(1), 14:14 + 12, x0:x1] = True
    U = xs.astype(np.float64)
    dc = np.where((zs >= 8 + Bd - 4) & (zs < 8 + Bd), (8 + Bd) - zs - 0.5, np.inf)
    A = skin(M, U, look, style="grid", bay=16, lit=lit, seed=seed, plinth=0, crown=0, dc=dc, cd=4)
    # bridges: ribbon glass on their sides
    for f in (6, 11, 16, floors - 2):
        y0 = H_of(f) - 1
        for zz in (14, 25):
            seg = A[y0 + 1:y0 + H_of(1) - 1, zz, x0:x1]
            seg[(seg != 0) & (seg != look.band)] = look.glass
    # arcade columns
    A[:H_of(1) - 1, dz - 5, x0:x1:12] = look.column
    return A


def linked_size(dx, Bd=34, floors=22):
    return (H_of(floors) + 10, Bd + 16, dx)


# ================================================================ dormitory (宿舍楼)
def dorm_block(rng, L=200, D=32, floors=20, scheme="cream_brick", seed=0, lit=0.05, axis="x", laundry=0.25):
    """A giant dormitory slab: a corridor along the north face, deep balconies
    on the south face (one per 16-block room, laundry hanging on some), solid
    stair cores at both ends and every 64 blocks."""
    look = Look(scheme)
    H = H_of(floors)
    dz, dx = D + 4, L
    hh = H + 10
    M = np.zeros((hh, dz, dx), bool)
    M[:H, 0:D, :] = True
    zs, xs = np.mgrid[0:dz, 0:dx]
    cores = (np.mod(xs - 8, 64) < 12) | (xs < 12) | (xs >= dx - 12)
    M[H:H + 10, 2:D - 2, :][np.broadcast_to(cores[2:D - 2][None] & (xs[2:D - 2] % 64 < 20)[None], (10, D - 4, dx))] = True
    U = xs.astype(np.float64)
    dc = np.where((zs < 4) & ~cores, zs + 0.5, np.inf)           # north corridor
    A = skin(M, U, look, style="grid", bay=16, lit=lit, seed=seed, plinth=H_of(1), crown=0, dc=dc, cd=4)
    # balconies: slabs and parapets projecting 4 blocks on the south face
    for x in range(dx):
        if cores[0, x]:
            A[:H, D - 1, x] = look.accent
            continue
        mu = x % 16
        for y in range(FH, H - 1):
            r = y % FH
            if r == 0:
                A[y, D:D + 4, x] = look.floor
            elif r in (1, 2):
                A[y, D + 3, x] = look.rail
            if mu == 0:
                A[y, D:D + 4, x] = look.wall                            # dividers between rooms
            elif r in (2, 3, 4, 5, 6) and 4 <= mu < 12:
                A[y, D - 1, x] = look.glass if r <= 5 else A[y, D - 1, x]
    for y in range(FH + 3, H - 1, FH):                                  # laundry
        for x0 in range(2, dx - 12, 16):
            if cores[0, x0] or rng.random() > laundry:
                continue
            col = B(["white_wool", "light_blue_wool", "pink_wool", "yellow_wool", "lime_wool"][int(rng.integers(5))])
            A[y, D + 1, x0 + 3:x0 + 3 + int(rng.integers(3, 8))] = col
    if axis == "z":
        A = A.transpose(0, 2, 1)[:, :, ::-1].copy()
    return A


def dorm_size(L=200, D=32, floors=20, axis="x"):
    h = H_of(floors) + 10
    return (h, D + 4, L) if axis == "x" else (h, L, D + 4)


# ================================================================ library (图书馆)
def library_hall(rng, W=160, D=110, floors=10, dome=True, scheme="cream_brick", seed=0, lit=0.08):
    """A monumental library: a stepped podium, a colonnade of giant columns
    across the front (south), tall reading-room windows between solid piers,
    an attic and a dome (or a flat crown) over the central reading room."""
    look = Look(scheme)
    H = H_of(floors)
    pod = 9
    R = int(min(W, D) * 0.32) if dome else 0
    hh = pod + H + 8 + (R + 14 if dome else 0)
    A = np.zeros((hh, D, W), np.uint16)
    # podium, three steps on the front
    A[:pod, 6:D, 4:W - 4] = look.plinth
    for k in range(3):
        A[:3 * (k + 1), 6 - 2 * k - 2:6 - 2 * k, 4:W - 4] = look.trim
    # the hall block (set back 18 from the front for the colonnade)
    M = np.zeros((H + 6, D - 24, W - 16), bool)
    M[:H] = True
    M[H:H + 6, 3:-3, 3:-3] = True                                       # attic
    zs, xs = np.mgrid[0:D - 24, 0:W - 16]
    U = np.where(np.abs(zs - (D - 24) / 2) / (D - 24) > np.abs(xs - (W - 16) / 2) / (W - 16), xs, zs).astype(float)
    hall = skin(M, U, look, style="fins", bay=16, lit=lit, seed=seed, crown=4)
    from buildings import paste
    paste(A, hall, pod, 22, 8)
    # colonnade: giant square columns with capitals and bases, entablature over them
    cy0, cy1 = pod, pod + H
    for x in range(10, W - 12, 16):
        A[cy0:cy1, 8:14, x:x + 6] = look.column
        A[cy0:cy0 + 3, 7:15, x - 1:x + 7] = look.trim
        A[cy1 - 4:cy1, 7:15, x - 1:x + 7] = look.trim
    A[cy1:cy1 + 6, 6:22, 6:W - 6] = look.wall
    A[cy1, 6, 6:W - 6] = look.trim
    A[cy1 + 5, 6:22, 6:W - 6] = look.trim
    A[cy1 - 1, 15:22, 10:W - 10:8] = look.light                           # portico ceiling lights
    # tall doors in the hall's front wall
    for x in range(W // 2 - 24, W // 2 + 24, 16):
        A[pod:pod + 3 * FH, 22, x + 4:x + 12] = look.door
    if dome:
        cyd = pod + H + 6
        cx, cz = W / 2, 22 + (D - 24) / 2
        ys, zz, xx = np.mgrid[0:R + 14, 0:D, 0:W]
        drum = (np.hypot(xx + 0.5 - cx, zz + 0.5 - cz) < R + 2) & (ys < 12)
        rr = np.sqrt((xx + 0.5 - cx) ** 2 + (zz + 0.5 - cz) ** 2 + ((ys - 12).clip(0)) ** 2)
        cap = (rr < R) & (rr >= R - 3) & (ys >= 12)
        sub = A[cyd:cyd + R + 14]
        ring = drum & (np.hypot(xx + 0.5 - cx, zz + 0.5 - cz) >= R - 1)
        sub[ring] = look.column
        win = ring & (ys >= 3) & (ys < 10) & (np.mod(np.degrees(np.arctan2(zz - cz, xx - cx)) + 360, 15) < 7)
        sub[win] = look.glass
        sub[cap] = look.roof
        rib = cap & (np.mod(np.degrees(np.arctan2(zz - cz, xx - cx)) + 360, 30) < 3)
        sub[rib] = look.trim
        top = int(cyd + 12 + R)
        if top < hh:
            A[top - 2:hh, int(cz), int(cx)] = look.trim
            A[min(hh - 1, top + 1), int(cz), int(cx)] = look.light
    return A


def library_size(W=160, D=110, floors=10, dome=True):
    R = int(min(W, D) * 0.32) if dome else 0
    return (9 + H_of(floors) + 8 + (R + 14 if dome else 0), D, W)
