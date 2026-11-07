"""The new map regions beyond the campus.  The world has no height limit any
more (y -1024 .. 2032, Nether 0 .. 1024), so:

  east   海上群岛学校  an enclosed sea with beaches, an archipelago of school
                       islands linked by bridges, a 480-block lighthouse school
         海底玻璃球学校 a trench down to y -800 with glass-sphere schools on its
                       floor, glass tunnels between them and a lift tube up
  west   超大型天坑学校 a 950-block-wide sinkhole down to y -900: three ledges
                       of cliff schools, cascading waterfalls, a 1,100-block
                       tower from the floor to above the rim, bridges across
         巨型地狱门     the giant Nether portal on the sinkhole's campus side
  north  超大型空岛学校 five sky islands, each higher than the last (y 400 ..
                       1720), the highest End-style; waterfalls, spiral
                       stairways and sky bridges
  Nether 地狱学校       a cavern 600 blocks tall around the other half of the
                       portal: lava lakes, basalt pillars, lavafalls, giant
                       fungi, glowstone and the infernal academy

Buildings come from mcbuild (mcbuild_regions.py); the landforms are numpy."""
from __future__ import annotations

import math

import numpy as np

from anvil import B
from buildings import Piece
import iconic as ic
import monuments as mon

GROUND = -61
SEA = -62                        # top water block of the sea

# ------------------------------------------------------------------ noise


def _hash(i, j, seed):
    h = (i.astype(np.int64) * 73856093) ^ (j.astype(np.int64) * 19349663) ^ (seed * 83492791)
    h = (h ^ (h >> 13)) * 1274126177
    return ((h & 0xFFFF).astype(np.float64) / 32767.5) - 1.0


def vnoise(x, z, scale, seed):
    """Smooth value noise in [-1, 1] on world coordinates (seamless across tiles)."""
    fx, fz = x / scale, z / scale
    i, j = np.floor(fx).astype(np.int64), np.floor(fz).astype(np.int64)
    u, v = fx - i, fz - j
    u, v = u * u * (3 - 2 * u), v * v * (3 - 2 * v)
    a, b = _hash(i, j, seed), _hash(i + 1, j, seed)
    c, d = _hash(i, j + 1, seed), _hash(i + 1, j + 1, seed)
    return (a * (1 - u) + b * u) * (1 - v) + (c * (1 - u) + d * u) * v


def fbm(x, z, scale, seed, octaves=4):
    s, amp, tot = 0.0, 1.0, 0.0
    for k in range(octaves):
        s = s + amp * vnoise(x, z, scale / 2 ** k, seed + 17 * k)
        tot += amp
        amp *= 0.5
    return s / tot


def _grid(m, x0, z0):
    dz, dx = m["ground"].shape
    zs, xs = np.mgrid[z0:z0 + dz, x0:x0 + dx]
    return xs.astype(np.float64), zs.astype(np.float64)


def smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ east: sea, islands, trench
OCEAN = (2048, -1800, 4800, 1300)
ISLANDS = [
    # name, x, z, R, plateau radius, plateau top y, school
    ("main", 2900, -250, 470, 360, -55, "sea_campus"),          # giant bow academy, library, dorms
    ("lighthouse", 3560, 720, 110, 60, -57, "lighthouse_school"),
    ("dorm", 2420, 760, 170, 125, -56, "sea_dorms"),
    ("library", 2480, -1250, 170, 125, -56, "sea_library"),
    ("annex", 3400, -1200, 150, 100, -55, "sea_academy"),
    ("c", 3700, -560, 70, 0, -58, "island_classroom"),
    ("e", 2350, 150, 60, 0, -58, "island_classroom"),
    ("f", 3300, 450, 55, 0, -59, None),
    ("g", 2300, -650, 45, 0, -59, None),
]
SPHERES = [("dome_school_big", 4150, -150, 130), ("sphere_dorm", 4480, 480, 105), ("sphere_library", 3960, -780, 105)]
SEABED_DEEP = -800


class Ocean:
    bbox = OCEAN

    def apply(self, m, x0, z0):
        xs, zs = _grid(m, x0, z0)
        X0, Z0, X1, Z1 = OCEAN
        inside = (xs >= X0) & (xs < X1) & (zs >= Z0) & (zs < Z1)
        if not inside.any():
            return
        n = fbm(xs, zs, 220, 5)
        depth = 2 + 46 * smooth((xs - 2060) / 240) + 10 * n
        depth = depth + (-SEABED_DEEP + SEA - 48) * smooth((xs - 3430) / 260) + 18 * fbm(xs, zs, 90, 9) * smooth((xs - 3500) / 200)
        edge = np.minimum.reduce([xs - X0, X1 - xs, zs - Z0, Z1 - zs])
        depth = depth * smooth(edge / 170)
        ground = np.round(GROUND - depth).astype(np.int32)
        for (_, ix, iz, R, pr, top, _s) in ISLANDS:
            r = np.hypot(xs - ix, zs - iz) * (1 + 0.12 * fbm(xs, zs, 40, ix))
            prof = np.where(r < pr, top, top - (top - SEA + 60) * ((np.maximum(r - pr, 0) / max(1, R - pr)) ** 1.5))
            ground = np.maximum(ground, np.round(prof).astype(np.int32))
        g = np.where(inside, ground, m["ground"])
        m["ground"][:] = g
        wet = inside & (g < SEA)
        m["fluid"][wet] = SEA
        m["fluid_id"][wet] = B("water")
        sand, gravel, clay, grass = B("sand"), B("gravel"), B("clay"), B("grass_block")
        nb = fbm(xs, zs, 30, 21)
        bed = np.where(nb > 0.25, gravel, np.where(nb < -0.3, clay, sand)).astype(np.uint16)
        top = np.where(g <= -59, np.where(g < -64, bed, sand), grass).astype(np.uint16)
        m["top"][inside] = top[inside]
        m["sub"][inside & (g <= -59)] = sand


def island_top(name):
    for it in ISLANDS:
        if it[0] == name:
            return it
    raise KeyError(name)


# ------------------------------------------------------------------ west: sinkhole
SX, SZ = -2950, -450
SINK = (SX - 490, SZ - 490, SX + 490, SZ + 490)
LEDGES = [(290, -900), (335, -720), (380, -520), (425, -300)]     # (outer radius, top y)


class Sinkhole:
    bbox = SINK

    def apply(self, m, x0, z0):
        xs, zs = _grid(m, x0, z0)
        r = np.hypot(xs - SX, zs - SZ) + 14 * fbm(xs, zs, 60, 31)
        g = m["ground"].copy()
        top = m["top"].copy()
        moss, grass, podzol = B("moss_block"), B("grass_block"), B("podzol")
        nl = fbm(xs, zs, 25, 33)
        for k, (ro, y) in reversed(list(enumerate(LEDGES))):
            sel = r < ro
            g[sel] = y
            top[sel] = np.where(nl[sel] > 0.2, moss, np.where(nl[sel] < -0.4, podzol, grass))
        # a lake on the floor
        a = np.arctan2(zs - SZ, xs - SX)
        lake = (r > 110) & (r < 250) & (np.cos(a - 0.6) > 0.55 + 0.25 * fbm(xs, zs, 40, 35))
        g[lake] = -903
        m["fluid"][lake] = -900
        m["fluid_id"][lake] = B("water")
        top[lake] = B("clay")
        m["ground"][:] = g
        m["top"][:] = top


# ------------------------------------------------------------------ north: sky islands
SKY = [
    # x, z, R, top y, theme, rock
    (-1000, -2650, 380, 400, "t_sky", "stone"),
    (800, -2800, 340, 720, "t_sky_sand", "sandstone"),
    (-900, -3450, 330, 1040, "t_sky_stone", "stone"),
    (950, -3560, 320, 1360, "t_sky_brick", "stone"),
    (0, -3150, 360, 1720, "t_end", "end"),
]
END_ISLAND = SKY[-1]


def sky_island(rng, R, rock, iseed, tile=None):
    """A floating island: flat-topped plateau, rough rim, an inverted rocky cone
    beneath with strata, hanging roots and moss.  Local y = 0 is the top surface.
    tile = (x0, z0, x1, z1) in local cells builds just that part (big islands
    are placed as several pieces)."""
    depth = sky_depth(R)
    n = 2 * R + 1
    tx0, tz0, tx1, tz1 = tile if tile else (0, 0, n, n)
    A = np.zeros((depth + 4, tz1 - tz0, tx1 - tx0), np.uint16)
    zs, xs = np.mgrid[tz0:tz1, tx0:tx1].astype(np.float64)
    wx, wz = xs - R, zs - R
    seed = iseed
    r = np.hypot(wx, wz) * (1 + 0.15 * fbm(xs + seed * 31, zs, 40, seed))
    under = depth * (1 - np.clip(r / R, 0, 1)) ** 0.8 * (0.75 + 0.25 * fbm(xs, zs + seed, 25, seed + 3))
    top_bump = np.round(2 * fbm(xs, zs, 30, seed + 5)).astype(int)
    on = r < R
    if rock == "end":
        mats = [B("end_stone")] * 3 + [B("end_stone_bricks")]
        surf, sub = B("end_stone"), B("end_stone")
    elif rock == "sandstone":
        mats = [B("sandstone"), B("smooth_sandstone"), B("terracotta"), B("orange_terracotta")]
        surf, sub = B("grass_block"), B("dirt")
    else:
        mats = [B("stone"), B("andesite"), B("tuff"), B("stone"), B("diorite")]
        surf, sub = B("grass_block"), B("dirt")
    for y in range(depth + 1):
        yy = depth - y                       # array row (top surface at row depth)
        sel = on & (under >= y)
        A[yy][sel] = mats[(y // 9) % len(mats)]
    for y in range(1, 4):
        sel = on & (under >= y)
        A[depth - y][sel] = sub
    A[depth][on] = surf
    # a little relief: lift some of the surface
    hill = on & (top_bump > 0) & (r < R * 0.85)
    A[depth + 1][hill] = surf
    A[depth][hill] = sub
    # hanging roots / vines under the rim
    if rock != "end":
        rim = on & (r > R * 0.7)
        cand = np.argwhere(rim & (rng.random(rim.shape) < 0.02))
        for (z, x) in cand:
            u = int(under[z, x])
            for k in range(1, rng.integers(4, 14)):
                row = depth - u - k
                if row < 0:
                    break
                A[row, z, x] = B("hanging_roots") if k == 1 else B("cave_vines")
    return A[::1]


def sky_depth(R):
    return int(R * 1.25) if R < 120 else int(150 + (R - 120) * 0.8)


def sky_island_size(R, tile=None):
    n = 2 * R + 1
    tx0, tz0, tx1, tz1 = tile if tile else (0, 0, n, n)
    return (sky_depth(R) + 4, tz1 - tz0, tx1 - tx0)


def place_sky_island(out, name, x, top, z, R, rock, iseed, tiles=1):
    """Place an island centred on (x, z) with its surface at `top`, in tiles x tiles pieces."""
    n = 2 * R + 1
    cuts = np.linspace(0, n, tiles + 1).astype(int)
    for a in range(tiles):
        for b in range(tiles):
            t = (int(cuts[a]), int(cuts[b]), int(cuts[a + 1]), int(cuts[b + 1]))
            sz = sky_island_size(R, t)
            _p(out, name, x - R + t[0], top - sz[0] + 4, z - R + t[1], sz, sky_island, iseed * 100 + a * 10 + b,
               R=R, rock=rock, iseed=iseed, tile=t)


def spiral_stair(rng, h, r_in=5, r_out=9, mat="polished_andesite", rail="andesite_wall"):
    """Walkable spiral (half-block steps) around a pillar, a rail and lanterns."""
    n = 2 * r_out + 3
    c = n // 2
    A = np.zeros((h + 3, n, n), np.uint16)
    A[:h + 1, c - 2:c + 3, c - 2:c + 3] = B("stone_bricks")
    full_name = "purpur_block" if mat == "purpur" else mat
    slab, full, railb, lan = B(f"{mat}_slab[type=bottom]"), B(full_name), B(rail), B("lantern")
    steps = 2 * h
    per_turn = 64
    for i in range(steps):
        a = 2 * math.pi * i / per_turn
        y = i // 2
        for rr in np.arange(r_in, r_out + 0.5, 0.5):
            x, z = c + int(round(rr * math.cos(a))), c + int(round(rr * math.sin(a)))
            A[y, z, x] = slab if i % 2 else full
            if y > 0 and A[y - 1, z, x] == 0:
                A[y - 1, z, x] = full
        x, z = c + int(round((r_out + 1) * math.cos(a))), c + int(round((r_out + 1) * math.sin(a)))
        A[y, z, x] = full
        A[y + 1, z, x] = railb
        if i % 48 == 0:
            A[y + 2, z, x] = lan
    return A


def spiral_size(h, r_out=9):
    n = 2 * r_out + 3
    return (h + 3, n, n)


def deck_bridge(rng, length, width=5, axis="x", mat="stone_bricks", rail="stone_brick_wall", lamps=16, carve_ends=0):
    """Straight bridge deck (along +x or +z) with walls, lanterns and optional
    cave-air doorways cut at both ends (into tower walls)."""
    A = np.zeros((6, width + 2, length), np.uint16)
    A[0, 1:width + 1, :] = B(mat)
    A[0, 0, :] = A[0, width + 1, :] = B(mat)
    A[1, 0, :] = A[1, width + 1, :] = B(rail)
    A[2, 0, ::lamps] = A[2, width + 1, ::lamps] = B("lantern")
    if carve_ends:
        for sl in (slice(0, carve_ends), slice(length - carve_ends, length)):
            A[1:5, 1:width + 1, sl] = B("cave_air")
            A[1:3, 0, sl] = A[1:3, width + 1, sl] = B("cave_air")
    if axis == "z":
        A = A.transpose(0, 2, 1).copy()
    return A


def column(rng, h, kind="water", w=3):
    """A falling fluid column (waterfall / lavafall) with a source on top."""
    A = np.zeros((h, 1, w), np.uint16)
    fall, src = B(f"{kind}[level=8]"), B(kind)
    A[:, 0, :] = fall
    A[-1, 0, :] = src
    return A


def glass_tube(rng, length, r=4, axis="x"):
    """Horizontal glass tunnel: glass ring, air inside (carves water), slab floor, lights."""
    n = 2 * r + 1
    A = np.zeros((n, n, length), np.uint16)
    yy, zz = np.mgrid[0:n, 0:n] - r
    d = np.hypot(yy, zz)
    ring = (d <= r) & (d > r - 1.5)
    inner = d <= r - 1.5
    A[ring] = B("glass")
    A[inner] = B("cave_air")
    A[r - 2, r - 1:r + 2, :] = B("smooth_quartz_slab[type=bottom]")
    A[r - 3, r - 2:r + 3, :] = B("smooth_quartz")
    A[n - 2, r, ::8] = B("sea_lantern")
    if axis == "z":
        A = A.transpose(0, 2, 1).copy()
    return A


def lift_tube(rng, h, r=4):
    """Vertical glass tube with a ladder, from a sphere's top to the sea surface."""
    n = 2 * r + 1
    A = np.zeros((h, n, n), np.uint16)
    zz, xx = np.mgrid[0:n, 0:n] - r
    d = np.hypot(zz, xx)
    A[:, (d <= r) & (d > r - 1.5)] = B("glass")
    A[:, d <= r - 1.5] = B("cave_air")
    A[:, r - 2, r] = B("smooth_quartz")
    A[:, r - 1, r] = B("ladder[facing=south]")
    A[::12, r + 1, r] = B("sea_lantern")
    return A


def pontoon(rng):
    """A floating glass pavilion over the lift tube (sea surface)."""
    A = np.zeros((10, 21, 21), np.uint16)
    A[0, :, :] = B("smooth_quartz")
    A[1:7, 0, :] = A[1:7, 20, :] = B("glass")
    A[1:7, :, 0] = A[1:7, :, 20] = B("glass")
    A[1:3, 0, 9:12] = B("cave_air")
    A[7, :, :] = B("smooth_quartz_slab[type=bottom]")
    A[6, 4::6, 4::6] = B("sea_lantern")
    A[1:7, 1:20, 1:20][A[1:7, 1:20, 1:20] == 0] = B("cave_air")
    A[0, 8:13, 8:13] = B("cave_air")
    return A


# ------------------------------------------------------------------ Nether
NETHER_BOX = (-820, -560, 260, 620)
GATE_OW = (-2240, 300)                     # portal plane x, centre z (overworld)
GATE_NE = (GATE_OW[0] // 8, GATE_OW[1] // 8)
NETHER_FLOOR = 64
ACADEMY_NE = (-280, -230)                  # centre of the giant ziggurat academy
NE_LIBRARY = (60, -250)
NE_DORMS = [((-620, -250), "z"), ((-300, 360), "x")]
NE_ANNEX = (40, 300)                       # the mcbuild infernal academy
NETHER_FLAT = [(GATE_NE[0], GATE_NE[1], 70), (ACADEMY_NE[0], ACADEMY_NE[1], 270), (NE_LIBRARY[0], NE_LIBRARY[1], 130),
               (-620, -250, 150), (-300, 360, 160), (NE_ANNEX[0], NE_ANNEX[1], 150)]


def nether_ground(x, z):
    """Floor height of the cavern at a point (same formula as NetherCavern)."""
    xs, zs = np.array([[float(x)]]), np.array([[float(z)]])
    n = fbm(xs, zs, 70, 41)
    g = NETHER_FLOOR - 4 + np.round(14 * n)
    if fbm(xs, zs, 110, 43)[0, 0] < -0.22:
        g = 26 + np.round(4 * n)
    return int(g[0, 0])


def nether_ceil(x, z):
    xs, zs = np.array([[float(x)]]), np.array([[float(z)]])
    return int((560 + np.round(70 * fbm(xs, zs, 80, 45) + 25 * vnoise(xs, zs, 9, 47)))[0, 0])


class NetherCavern:
    bbox = NETHER_BOX

    def apply(self, m, x0, z0):
        xs, zs = _grid(m, x0, z0)
        X0, Z0, X1, Z1 = NETHER_BOX
        inside = (xs >= X0) & (xs < X1) & (zs >= Z0) & (zs < Z1)
        n = fbm(xs, zs, 70, 41)
        g = NETHER_FLOOR - 4 + np.round(14 * n).astype(np.int32)
        lakes = fbm(xs, zs, 110, 43) < -0.22
        g = np.where(lakes, 26 + np.round(4 * n).astype(np.int32), g)
        # flat plaza around the gate and the academy, and the causeway between
        for (cx, cz, rad) in NETHER_FLAT:
            g = np.where(np.hypot(xs - cx, zs - cz) < rad, NETHER_FLOOR - 1, g)
        g = np.where((np.abs(xs - GATE_NE[0]) < 8) & (zs < GATE_NE[1]) & (zs > ACADEMY_NE[1]), NETHER_FLOOR - 1, g)
        ceil = 560 + np.round(70 * fbm(xs, zs, 80, 45) + 25 * vnoise(xs, zs, 9, 47)).astype(np.int32)
        edge = np.minimum.reduce([xs - X0, X1 - xs, zs - Z0, Z1 - zs])
        ceil = np.where(edge < 90, np.round(g + 8 + (ceil - g - 8) * smooth(edge / 90)).astype(np.int32), ceil)
        m["ground"][inside] = g[inside]
        m["ceil"][inside] = ceil[inside]
        lava = inside & (g < 38)
        m["fluid"][lava] = 38
        m["fluid_id"][lava] = B("lava")
        nk = fbm(xs, zs, 20, 49)
        top = np.where(nk > 0.35, B("crimson_nylium"), np.where(nk < -0.35, B("warped_nylium"),
                       np.where(nk > 0.15, B("soul_soil"), B("netherrack")))).astype(np.uint16)
        top = np.where(g == NETHER_FLOOR - 1, B("polished_blackstone_bricks"), top)
        m["top"][inside] = top[inside]
        m["sub"][inside] = B("netherrack")


def basalt_pillar(rng, h, r):
    n = 2 * r + 5
    A = np.zeros((h, n, n), np.uint16)
    zz, xx = np.mgrid[0:n, 0:n] - n // 2
    d = np.hypot(zz, xx)
    for y in range(h):
        t = abs(y - h / 2) / (h / 2)
        rr = r * (0.75 + 0.45 * t * t) + rng.uniform(-0.6, 0.6)
        sel = d <= rr
        A[y][sel] = B("basalt") if (y // 7) % 3 else B("polished_basalt")
        vein = sel & (d > rr - 1.2) & (rng.random(sel.shape) < 0.03)
        A[y][vein] = B("magma_block")
    return A


def huge_fungus(rng, h, cap, kind="crimson"):
    n = 2 * cap + 3
    c = n // 2
    A = np.zeros((h + cap + 2, n, n), np.uint16)
    stem = B(f"{kind}_stem")
    wart = B("nether_wart_block" if kind == "crimson" else "warped_wart_block")
    A[:h, c - 1:c + 2, c - 1:c + 2] = stem
    zz, xx = np.mgrid[0:n, 0:n] - c
    for k in range(cap + 1):
        rr = cap * math.sqrt(max(0.0, 1 - (k / (cap + 0.5)) ** 2))
        ring = np.hypot(zz, xx) <= rr
        A[h - 2 + k][ring] = wart
        if k < cap // 2:
            hole = np.hypot(zz, xx) <= rr - 2
            A[h - 2 + k][hole] = 0
    sl = (rng.random((n, n)) < 0.05) & (np.hypot(zz, xx) <= cap - 1)
    A[h - 3][sl] = B("shroomlight")
    return A


def glow_cluster(rng, r):
    n = 2 * r + 1
    A = np.zeros((n, n, n), np.uint16)
    zz, yy, xx = np.mgrid[0:n, 0:n, 0:n] - r
    d = np.sqrt(zz * zz + (yy * 0.7) ** 2 + xx * xx)
    A[(d <= r) & (rng.random(d.shape) < 0.7) & (yy >= 0)] = B("glowstone")
    return A


# ------------------------------------------------------------------ assembling
def _mcb(name):
    import mcbuild_bridge
    return mcbuild_bridge.load()[name]


def _mcb_piece(rng, name):
    return _mcb(name)[0].copy()


def place_mcb(out, name, x, y, z):
    """mcbuild design with local (0, 0, 0) at world (x, y, z)."""
    A, (ox, oy, oz) = _mcb(name)
    out.append(Piece(name, int(x) + ox, int(y) + oy, int(z) + oz, A.shape, _mcb_piece, 0, kw={"name": name}))


def place_mcb_center(out, name, cx, y, cz):
    """mcbuild design centred on (cx, cz) horizontally, its local y = 0 at y."""
    A, (ox, oy, oz) = _mcb(name)
    out.append(Piece(name, int(cx) - A.shape[2] // 2, int(y) + oy, int(cz) - A.shape[1] // 2, A.shape, _mcb_piece, 0,
                     kw={"name": name}))


def _p(out, name, x, y, z, size, fn, _seed=0, **kw):
    out.append(Piece(name, int(x), int(y), int(z), size, fn, abs(int(_seed)), kw=kw))


def glass_sphere(rng, R, content="dorm"):
    """A glass sphere on the sea floor (local 0 = its lowest point), air inside,
    a grassy floor disc at 0.45 R holding a dormitory ring or a domed library."""
    n = 2 * R + 1
    zz, yy, xx = np.mgrid[0:n, 0:n, 0:n] - R
    d = np.sqrt(xx * xx + yy * yy + zz * zz)
    A = np.zeros((n, n, n), np.uint16)
    A[d < R - 2] = B("cave_air")
    shell = (d >= R - 2) & (d < R + 0.5)
    ang = np.degrees(np.arctan2(zz, xx))
    rib = shell & ((np.mod(ang + 360, 15) < 1.6) | (np.mod(yy + 400, 16) < 1))
    A[shell] = B("light_blue_stained_glass")
    A[rib] = B("white_concrete")
    A = A.transpose(1, 0, 2).copy()                     # mgrid order was (z, y, x) -> (y, z, x)
    fy = int(R * 0.45)
    rad = math.sqrt(R * R - (R - fy) ** 2) - 2
    zs, xs = np.mgrid[0:n, 0:n] - R
    disc = np.hypot(xs, zs) < rad
    for k in range(4):
        A[fy - k][disc & (A[fy - k] == B("cave_air"))] = B("white_concrete") if k else B("grass_block")
    A[fy][disc & (np.mod(np.hypot(xs, zs).astype(int), 18) < 3)] = B("smooth_quartz")
    # floor lamps every 9 blocks: no sky light reaches 800 blocks under the sea (found dark in Horizon)
    A[fy][disc & (np.mod(xs, 9) == 4) & (np.mod(zs, 9) == 4)] = B("sea_lantern")
    if content == "dorm":
        O = int(2 * rad - 24) // 2 * 2
        D = ic.ring_hall(rng, O=O, thick=22, floors=7, scheme="t_glass", seed=int(rng.integers(1 << 30)), lit=0.15)
    else:
        D = ic.library_hall(rng, W=124, D=96, floors=6, dome=True, scheme="t_glass", seed=int(rng.integers(1 << 30)),
                            lit=0.2)
    h, dz, dx = D.shape
    from buildings import paste
    paste(A, D, fy + 1, R - dz // 2, R - dx // 2)
    # lamps around the disc
    for k in range(24):
        a_ = 2 * math.pi * k / 24
        x, z = int(R + (rad - 6) * math.cos(a_)), int(R + (rad - 6) * math.sin(a_))
        A[fy + 1:fy + 4, z, x] = B("white_concrete")
        A[fy + 4, z, x] = B("sea_lantern")
    return A


def place_arc(out, name, cx, y, cz, R, D, a0, a1, steps, scheme, nseg=6, gates=(), end_extra=4):
    """A bow-shaped hall around the circle centred (cx, cz), split into pieces."""
    edges = np.linspace(a0, a1, nseg + 1)
    top = max(f for _, f in steps) + end_extra
    hh = ic.H_of(top) + 2
    for k in range(nseg):
        b0, b1 = float(edges[k]), float(edges[k + 1])
        pts = [(cx + rr * math.sin(math.radians(t)), cz - rr * math.cos(math.radians(t)))
               for t in np.linspace(b0, b1, 16) for rr in (R - 6, R + D + 6)]
        xs_, zs_ = zip(*pts)
        X0, X1 = int(math.floor(min(xs_))) - 2, int(math.ceil(max(xs_))) + 2
        Z0, Z1 = int(math.floor(min(zs_))) - 2, int(math.ceil(max(zs_))) + 2
        ends = []
        if k == 0:
            ends.append((a0 + 1.6, end_extra))
        if k == nseg - 1:
            ends.append((a1 - 1.6, end_extra))
        _p(out, name, X0, y, Z0, (hh, Z1 - Z0, X1 - X0), ic.arc_segment, 900 + k, dx=X1 - X0, dz=Z1 - Z0, hh=hh,
           cx=cx - X0, cz=cz - Z0, R=R, D=D, a0=b0, a1=b1 + (1e-4 if k == nseg - 1 else 0), steps=steps,
           scheme=scheme, gates=tuple(g for g in gates if b0 <= g < b1), end_towers=tuple(ends), seed=900 + k)


def place_center(out, name, fn, size, cx, y, cz, _seed, **kw):
    _p(out, name, cx - size[2] // 2, y, cz - size[1] // 2, size, fn, _seed, **kw)


def school_ensemble(out, rng, theme, cx, y, cz, R, kind):
    """A super-large school for a plateau of radius ~R at height y: a giant
    teaching building of the given kind, a domed library and a dormitory,
    all in the environment's theme."""
    sd = lambda: int(rng.integers(1 << 30))
    if kind == "bow":
        Ra = int(R * 0.62)
        place_arc(out, "academy", cx, y, cz + int(R * 0.18), Ra, 38, -56, 56, [(18, 28), (36, 25), (90, 22)], theme,
                  gates=(0.0,))
        lib_at, dorm_at = (cx, cz + int(R * 0.12)), (cx, cz + int(R * 0.55))
    elif kind == "ziggurat":
        L = int(R * 1.05)
        sz = ic.terrace_size(L, L, 6, 4)
        place_center(out, "academy", ic.terrace, sz, cx, y, cz - int(R * 0.18), sd(), L=L, Dbase=L, tiers=6,
                     tier_floors=4, step=max(8, L // 14), scheme=theme, seed=sd(), square=True)
        lib_at, dorm_at = (cx - int(R * 0.42), cz + int(R * 0.52)), (cx + int(R * 0.40), cz + int(R * 0.55))
    elif kind == "ring":
        O = int(R * 1.05) // 2 * 2
        sz = ic.ring_size(O, 20)
        place_center(out, "academy", ic.ring_hall, sz, cx, y, cz - int(R * 0.2), sd(), O=O, thick=30, floors=20,
                     scheme=theme, seed=sd())
        lib_at, dorm_at = (cx - int(R * 0.42), cz + int(R * 0.55)), (cx + int(R * 0.40), cz + int(R * 0.58))
    elif kind == "gothic":
        W = int(R * 0.36)
        sz = ic.gothic_size(W, 56)
        place_center(out, "academy", ic.gothic_tower, sz, cx, y, cz - int(R * 0.25), sd(), W=W, floors=56,
                     scheme=theme, seed=sd())
        lib_at, dorm_at = (cx - int(R * 0.38), cz + int(R * 0.35)), (cx + int(R * 0.35), cz + int(R * 0.45))
    elif kind == "spires":                         # three Gothic spires of different heights (End)
        # the End island is near the top of the world: keep every spire under y 2032
        fmax = max(10, ((2030 - y - 70) - 1) // ic.FH)
        for (dx, dz, W, f) in ((0, -int(R * 0.28), int(R * 0.3), fmax), (-int(R * 0.4), -int(R * 0.02), int(R * 0.22), fmax - 6),
                               (int(R * 0.4), -int(R * 0.02), int(R * 0.22), fmax - 6)):
            sz = ic.gothic_size(W, f)
            place_center(out, "academy", ic.gothic_tower, sz, cx + dx, y, cz + dz, sd(), W=W, floors=f, scheme=theme,
                         seed=sd())
        lib_at, dorm_at = (cx - int(R * 0.30), cz + int(R * 0.45)), (cx + int(R * 0.32), cz + int(R * 0.48))
    Wl = int(R * 0.42) // 2 * 2
    Dl = int(Wl * 0.72)
    place_center(out, "library", ic.library_hall, ic.library_size(Wl, Dl, 8), lib_at[0], y, lib_at[1], sd(),
                 W=Wl, D=Dl, floors=8, scheme=theme, seed=sd())
    Ld = int(R * 0.5)
    place_center(out, "dorm", ic.dorm_block, ic.dorm_size(Ld, 30, 14), dorm_at[0], y, dorm_at[1], sd(),
                 L=Ld, D=30, floors=14, scheme=theme, seed=sd())


DESERT = (2300, -4060, 5060, -1950)
PYR = (3650, -3000)                    # pyramid centre
OASIS = (3120, -2260, 80)
DESERT_FLAT = [(PYR[0], PYR[1], 480), (3250, -2470, 160), (3990, -2450, 200),
               (OASIS[0], OASIS[1], OASIS[2] + 50)]


class Desert:
    """Dunes all round, flattened where the school stands; sand on sandstone."""
    bbox = DESERT

    def apply(self, m, x0, z0):
        xs, zs = _grid(m, x0, z0)
        X0, Z0, X1, Z1 = DESERT
        inside = (xs >= X0) & (xs < X1) & (zs >= Z0) & (zs < Z1)
        if not inside.any():
            return
        edge = np.minimum.reduce([xs - X0, X1 - xs, zs - Z0, Z1 - zs]).astype(np.float64)
        dune = 9 * (1 + np.sin((xs * 0.8 + zs * 0.35) / 34 + 3 * fbm(xs, zs, 120, 61))) + 10 * fbm(xs, zs, 90, 63)
        flat = np.zeros(xs.shape)
        for (cx, cz, r) in DESERT_FLAT:
            flat = np.maximum(flat, 1 - smooth((np.hypot(xs - cx, zs - cz) - r) / 70))
        # the processional avenue from the south to the pyramid
        avenue = (zs < -2100) & (zs > PYR[1])
        flat = np.maximum(flat, (1 - smooth((np.abs(xs - PYR[0]) - 70) / 50)) * avenue)
        h = np.maximum(0, dune) * smooth(edge / 240) * (1 - flat)
        g = np.round(GROUND + h).astype(np.int32)
        m["ground"][inside] = g[inside]
        top = np.full(xs.shape, B("sand"), np.uint16)
        top[(np.abs(xs - PYR[0]) < 22) & (zs > PYR[1]) & (zs < -2100)] = B("cut_sandstone")
        top[(np.hypot(xs - PYR[0], zs - PYR[1]) < 330) & (np.hypot(xs - PYR[0], zs - PYR[1]) >= 290)] = B("smooth_sandstone")
        od = np.hypot(xs - OASIS[0], zs - OASIS[1]) + 8 * fbm(xs, zs, 20, 65)
        water = inside & (od < OASIS[2])
        g2 = np.where(water, GROUND - 4, g)
        m["ground"][water] = g2[water]
        m["fluid"][water] = GROUND - 1
        m["fluid_id"][water] = B("water")
        top[(od >= OASIS[2]) & (od < OASIS[2] + 14)] = B("grass_block")
        m["top"][inside] = top[inside]
        m["sub"][inside] = B("sandstone")


def desert(out, rng):
    """The desert school: the pyramid, an avenue of obelisks, a temple-like
    library, three dormitories and an oasis with palms."""
    px, pz = PYR
    B_ = mon.PYR_B
    cuts = np.linspace(0, B_, 5).astype(int)
    for a in range(4):
        for b in range(4):
            t = (int(cuts[a]), int(cuts[b]), int(cuts[a + 1]), int(cuts[b + 1]))
            _p(out, "pyramid", px - B_ // 2 + t[0], GROUND + 1, pz - B_ // 2 + t[1], mon.pyramid_tile_size(*t),
               mon.pyramid, 0, tx0=t[0], tz0=t[1], tx1=t[2], tz1=t[3])
    ob = mon.obelisk(rng).shape
    for z in range(pz + B_ // 2 + 60, -2120, 90):
        for sx in (-44, 44):
            _p(out, "obelisk", px + sx - ob[2] // 2, GROUND + 1, z, ob, mon.obelisk, 0)
    # four great obelisks at the pyramid's corners
    for (sx, sz) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        big = mon.obelisk(rng, w=14, h=200).shape
        _p(out, "obelisk", px + sx * (B_ // 2 + 40) - big[2] // 2, GROUND + 1, pz + sz * (B_ // 2 + 40) - big[1] // 2,
           big, mon.obelisk, 0, w=14, h=200)
    sd = lambda: int(rng.integers(1 << 30))
    place_center(out, "library", ic.library_hall, ic.library_size(200, 140, 9, False), 3250, GROUND + 1, -2470, sd(),
                 W=200, D=140, floors=9, dome=False, scheme="t_desert", seed=sd())
    for k, z in enumerate((-2560, -2450, -2340)):
        place_center(out, "dorm", ic.dorm_block, ic.dorm_size(240, 34, 12), 3990, GROUND + 1, z, sd(),
                     L=240, D=34, floors=12, scheme="t_desert", seed=sd())
    ox, oz, orad = OASIS
    for k in range(26):
        a = 2 * math.pi * k / 26 + rng.uniform(-0.1, 0.1)
        r = orad + rng.uniform(2, 12)
        p = mon.palm(rng)
        _p(out, "palm", ox + r * math.cos(a) - p.shape[2] // 2, GROUND + 1, oz + r * math.sin(a) - p.shape[1] // 2,
           p.shape, _palm, k, h=p.shape[0] - 6)


def _palm(rng, h):
    return mon.palm(rng, h)


def overworld():
    """-> (pieces, landforms) for the new overworld regions."""
    rng = np.random.default_rng(7)
    out, lands = [], [Ocean(), Sinkhole(), Desert()]
    # --- archipelago: the main island carries a giant school, others a dorm
    # quarter, a library, an annex and small classrooms
    for (name, ix, iz, R, pr, top, school) in ISLANDS:
        if school == "sea_campus":
            school_ensemble(out, rng, "t_sea", ix, top + 1, iz, pr, "bow")
        elif school == "sea_dorms":
            for dz in (-42, 42):
                place_center(out, "dorm", ic.dorm_block, ic.dorm_size(200, 30, 16), ix, top + 1, iz + dz,
                             int(rng.integers(1 << 30)), L=200, D=30, floors=16, scheme="t_sea",
                             seed=int(rng.integers(1 << 30)))
        elif school == "sea_library":
            place_center(out, "library", ic.library_hall, ic.library_size(180, 130, 10), ix, top + 1, iz,
                         int(rng.integers(1 << 30)), W=180, D=130, floors=10, scheme="t_sea", seed=5)
        elif school in ("sea_academy", "lighthouse_school"):
            place_mcb_center(out, school, ix, top + 1, iz)
        elif school == "island_classroom":
            place_mcb(out, school, ix - 15, top + 1 - 4, iz - 10)
    for (a, b) in (("main", "lighthouse"), ("main", "dorm"), ("main", "library"), ("library", "annex"), ("main", "e"),
                   ("main", "g"), ("main", "f"), ("lighthouse", "f"), ("annex", "c")):
        _, ax, az, aR, apr, atop, _s = island_top(a)
        _, bx, bz, bR, bpr, btop, _s = island_top(b)
        y = -56
        a_edge = (apr + 4) if apr else int(aR * 0.55)        # start outside the school
        b_edge = (bpr + 4) if bpr else int(bR * 0.45)
        sx = 1 if bx > ax else -1
        xa = ax + sx * a_edge                               # along x at a's z, from a's rim to b's x
        x0, x1 = sorted((xa, bx))
        if x1 - x0 > 2:
            _p(out, "bridge", x0, y, az - 3, (6, 7, x1 - x0), deck_bridge, 0, length=x1 - x0)
            for k in range(0, x1 - x0, 24):
                _p(out, "pier", x0 + k, SEA - 60, az - 1, (60 + y - SEA, 3, 3), _pillar, 0, h=60 + y - SEA)
        szn = 1 if bz > az else -1                          # along z at b's x, to b's rim
        zb = bz - szn * b_edge
        z0, z1 = sorted((az, zb))
        if z1 - z0 > 2:
            _p(out, "bridge", bx - 3, y, z0, (6, z1 - z0, 7), deck_bridge, 0, length=z1 - z0, axis="z")
            for k in range(0, z1 - z0, 24):
                _p(out, "pier", bx - 1, SEA - 60, z0 + k, (60 + y - SEA, 3, 3), _pillar, 0, h=60 + y - SEA)
    # --- glass spheres on the trench floor (school, dormitories, library), tunnels, lift tube and pontoon
    sph = []
    floor = SEABED_DEEP - 20 + int(SPHERES[0][3] * 0.45)      # common floor level of the three spheres
    for (name, sx, sz, R) in SPHERES:
        y = floor - int(R * 0.45)
        if name.startswith("dome_school"):
            place_mcb_center(out, name, sx, y, sz)
        else:
            n = 2 * R + 1
            _p(out, name, sx - R, y, sz - R, (n, n, n), glass_sphere, 31 + len(sph), R=R,
               content="dorm" if name == "sphere_dorm" else "library")
        sph.append((sx, sz, R, y))
    (bx_, bz_, bR, by_) = sph[0]
    fy = floor + 1                                           # standing level inside
    for (sx, sz, R, y) in sph[1:]:
        s1 = 1 if sx > bx_ else -1
        xa = bx_ + s1 * int(0.835 * bR - 3)                  # leave the big sphere through its shell
        x0, x1 = sorted((xa, sx))
        _p(out, "tube", x0, fy - 2, bz_ - 4, (9, 9, x1 - x0), glass_tube, 0, length=x1 - x0)
        s2 = 1 if sz > bz_ else -1
        zb = sz - s2 * int(0.835 * R - 3)
        z0, z1 = sorted((bz_ - 4 * s2, zb))
        _p(out, "tube", sx - 4, fy - 2, z0, (9, z1 - z0, 9), glass_tube, 0, length=z1 - z0, axis="z")
    _p(out, "lift", bx_ - 4, fy, bz_ - 4, (SEA + 8 - fy, 9, 9), lift_tube, 0, h=SEA + 8 - fy)
    _p(out, "pontoon", bx_ - 10, SEA + 1, bz_ - 10, (10, 21, 21), pontoon, 0)
    # --- sinkhole: tower, ledge schools, a library and dormitories on the floor, bridges, waterfalls
    floor = LEDGES[0][1] + 1
    place_mcb_center(out, "pit_tower", SX, floor, SZ)
    place_center(out, "library", ic.library_hall, ic.library_size(150, 100, 8), SX - 190, floor, SZ, 41,
                 W=150, D=100, floors=8, scheme="t_cliff", seed=41)
    place_center(out, "dorm", ic.dorm_block, ic.dorm_size(180, 30, 14), SX, floor, SZ - 212, 42,
                 L=180, D=30, floors=14, scheme="t_cliff", seed=42)
    place_center(out, "dorm", ic.dorm_block, ic.dorm_size(180, 30, 14), SX - 70, floor, SZ + 198, 43,
                 L=180, D=30, floors=14, scheme="t_cliff", seed=43)
    for k, (ro, ytop) in enumerate(LEDGES[1:]):
        ri = LEDGES[k][0]
        rm = (ri + ro) / 2
        nb = int(2 * math.pi * rm / 70)
        for j in range(nb):
            a = 2 * math.pi * (j + 0.5 * k) / nb
            ox, oz = math.cos(a), math.sin(a)
            # the tall back of the school faces outward (against the cliff)
            if abs(oz) >= abs(ox):
                variant = "cliff_school" if oz < 0 else "cliff_school_t2"
            else:
                variant = "cliff_school_t1" if ox > 0 else "cliff_school_t3"
            place_mcb_center(out, variant, SX + rm * ox, ytop + 1, SZ + rm * oz)
    for (ytop, r_end) in ((LEDGES[1][1], LEDGES[0][0] + 10), (LEDGES[2][1], LEDGES[1][0] + 10),
                         (LEDGES[3][1], LEDGES[2][0] + 10), (GROUND, LEDGES[3][0] + 30)):
        L = r_end - 30
        _p(out, "pit_bridge", SX + 30, ytop, SZ - 3, (6, 7, L), deck_bridge, 0, length=L, carve_ends=4)
        _p(out, "pit_bridge", SX - 30 - L, ytop, SZ - 3, (6, 7, L), deck_bridge, 0, length=L, carve_ends=4)
        _p(out, "pit_bridge", SX - 3, ytop, SZ + 30, (6, L, 7), deck_bridge, 0, length=L, axis="z", carve_ends=4)
        _p(out, "pit_bridge", SX - 3, ytop, SZ - 30 - L, (6, L, 7), deck_bridge, 0, length=L, axis="z", carve_ends=4)
    for j, a in enumerate((0.9, 2.3, 3.9, 5.2)):
        for k in range(len(LEDGES) - 1, -1, -1):
            ro, ytop = LEDGES[k]
            upper = LEDGES[k + 1][1] if k + 1 < len(LEDGES) else GROUND
            r = ro - 3
            x, z = SX + r * math.cos(a), SZ + r * math.sin(a)
            h = upper - ytop
            _p(out, "waterfall", x, ytop + 1, z, (h, 1, 5), column, 0, h=h, kind="water", w=5)
    # --- the giant Nether portal west of the campus
    px, pz = GATE_OW
    place_mcb(out, "nether_gate_overworld", px - 33, GROUND + 1, pz - 56)
    # --- sky islands: a giant school on each, waterfalls, stairways, bridges, little rocks
    kinds = ["ziggurat", "ring", "gothic", "bow", "spires"]
    for k, (x, z, R, top, theme, rock) in enumerate(SKY):
        place_sky_island(out, "sky_island", x, top, z, R, rock, k + 1, tiles=3)
        school_ensemble(out, rng, theme, x, top + 1, z, int(R * 0.86), kinds[k])
        for j in range(16):
            rr = int(rng.integers(10, 30))
            a = rng.uniform(0, 2 * math.pi)
            d = R + rng.uniform(30, 160)
            ty = top + int(rng.integers(-160, 40))
            s2 = sky_island_size(rr)
            _p(out, "sky_rock", x + d * math.cos(a) - rr, ty - s2[0] + 4, z + d * math.sin(a) - rr, s2, sky_island,
               100 + 20 * k + j, R=rr, rock=rock, iseed=100 + 20 * k + j)
        if rock != "end":
            for a in (0.4, 3.3):
                fx, fz = x + (R - 10) * math.cos(a), z + (R - 10) * math.sin(a)
                h = top - GROUND - 1
                _p(out, "waterfall", fx, GROUND + 1, fz, (h, 1, 5), column, 0, h=h, kind="water", w=5)
                lands.append(Pond(fx + 2, fz, 16))
    # spiral stairway from the ground to the first island, then island to island
    x0, z0, R0, t0 = SKY[0][:4]
    sx, sz = x0, z0 + R0 + 14
    h = t0 - GROUND
    _p(out, "sky_stair", sx - 10, GROUND + 1, sz - 10, spiral_size(h), spiral_stair, 0, h=h)
    _p(out, "sky_bridge", sx - 3, t0, z0 + R0 - 30, (6, 34, 7), deck_bridge, 0, length=34, axis="z")
    for (a, b) in zip(SKY[:-1], SKY[1:]):
        ax, az, aR, at = a[:4]
        bx, bz, bR, bt = b[:4]
        dx, dz = bx - ax, bz - az
        d = math.hypot(dx, dz)
        ux, uz = dx / d, dz / d
        tx, tz = ax + ux * (aR - 20), az + uz * (aR - 20)      # stair tower near a's rim, toward b
        hh = bt - at
        _p(out, "sky_stair", tx - 10, at + 1, tz - 10, spiral_size(hh), spiral_stair, 0, h=hh,
           mat="purpur" if b[5] == "end" else "polished_andesite",
           rail="end_stone_brick_wall" if b[5] == "end" else "andesite_wall")
        ex, ez = bx - ux * (bR - 20), bz - uz * (bR - 20)       # bridge at b's height from the tower to b
        if abs(ex - tx) >= abs(ez - tz):
            x_a, x_b = sorted((tx, ex))
            _p(out, "sky_bridge", x_a, bt, tz - 3, (6, 7, int(x_b - x_a)), deck_bridge, 0, length=int(x_b - x_a))
            z_a, z_b = sorted((tz, ez))
            _p(out, "sky_bridge", ex - 3, bt, z_a, (6, max(1, int(z_b - z_a)), 7), deck_bridge, 0, length=max(1, int(z_b - z_a)), axis="z")
        else:
            z_a, z_b = sorted((tz, ez))
            _p(out, "sky_bridge", tx - 3, bt, z_a, (6, int(z_b - z_a), 7), deck_bridge, 0, length=int(z_b - z_a), axis="z")
            x_a, x_b = sorted((tx, ex))
            _p(out, "sky_bridge", x_a, bt, ez - 3, (6, 7, max(1, int(x_b - x_a))), deck_bridge, 0, length=max(1, int(x_b - x_a)))
    # --- the desert school
    desert(out, rng)
    return out, lands


class Pond:
    def __init__(self, x, z, r):
        self.x, self.z, self.r = x, z, r
        self.bbox = (int(x - r - 1), int(z - r - 1), int(x + r + 2), int(z + r + 2))

    def apply(self, m, x0, z0):
        xs, zs = _grid(m, x0, z0)
        d = np.hypot(xs - self.x, zs - self.z)
        sel = d < self.r
        m["ground"][sel] = np.minimum(m["ground"][sel], GROUND - 3)
        m["fluid"][sel] = GROUND - 1
        m["top"][sel] = B("gravel")
        m["top"][(d >= self.r) & (d < self.r + 2)] = B("mossy_cobblestone")


def _pillar(rng, h):
    A = np.zeros((h, 3, 3), np.uint16)
    A[:] = B("stone_bricks")
    return A


def nether():
    """-> (pieces, landforms) for the Nether school."""
    rng = np.random.default_rng(11)
    out, lands = [], [NetherCavern()]
    gx, gz = GATE_NE
    place_mcb(out, "nether_gate_nether", gx - 33, NETHER_FLOOR, gz - 56)
    ax, az = ACADEMY_NE
    # the giant ziggurat academy, a library, two dormitories, the mcbuild academy as an annex
    L = 360
    place_center(out, "academy", ic.terrace, ic.terrace_size(L, L, 7, 5), ax, NETHER_FLOOR, az, 51, L=L, Dbase=L,
                 tiers=7, tier_floors=5, step=24, scheme="t_nether", seed=51, square=True, lit=0.14)
    place_center(out, "library", ic.library_hall, ic.library_size(180, 130, 10), NE_LIBRARY[0], NETHER_FLOOR,
                 NE_LIBRARY[1], 52, W=180, D=130, floors=10, scheme="t_nether", seed=52, lit=0.2)
    for k, ((dx_, dz_), axis) in enumerate(NE_DORMS):
        place_center(out, "dorm", ic.dorm_block, ic.dorm_size(240, 32, 18, axis), dx_, NETHER_FLOOR, dz_, 53 + k,
                     L=240, D=32, floors=18, scheme="t_nether", seed=53 + k, axis=axis, lit=0.12)
    place_mcb_center(out, "infernal_academy", NE_ANNEX[0], NETHER_FLOOR, NE_ANNEX[1])

    def busy(x, z, pad):
        return any(math.hypot(x - cx, z - cz) < rad + pad for (cx, cz, rad) in NETHER_FLAT)
    X0, Z0, X1, Z1 = NETHER_BOX
    spots = []
    for _ in range(400):
        x, z = rng.integers(X0 + 100, X1 - 100), rng.integers(Z0 + 100, Z1 - 100)
        if busy(x, z, 30):
            continue
        if any(math.hypot(x - a, z - b) < 90 for a, b, _ in spots):
            continue
        spots.append((x, z, int(rng.integers(8, 18))))
        if len(spots) >= 18:
            break
    for (x, z, r) in spots:                                 # basalt pillars floor to ceiling
        _p(out, "basalt_pillar", x - r - 2, 20, z - r - 2, (640, 2 * r + 5, 2 * r + 5), basalt_pillar, int(x * 7 + z),
           h=640, r=r)
    for j in range(12):                                     # lavafalls from the ceiling
        x, z = rng.integers(X0 + 120, X1 - 120), rng.integers(Z0 + 120, Z1 - 120)
        if busy(x, z, 20):
            continue
        _p(out, "lavafall", x, 30, z, (600, 1, 3), column, 0, h=600, kind="lava", w=3)
    for j in range(60):                                     # glowstone hanging under the ceiling
        x, z = rng.integers(X0 + 100, X1 - 100), rng.integers(Z0 + 100, Z1 - 100)
        r = int(rng.integers(3, 8))
        c = nether_ceil(x, z)                               # hang from the ceiling (cluster's upper half)
        _p(out, "glowstone", x - r, c - 2 * r + 1, z - r, (2 * r + 1, 2 * r + 1, 2 * r + 1), glow_cluster, j, r=r)
    for j in range(70):                                     # giant fungi
        x, z = rng.integers(X0 + 90, X1 - 90), rng.integers(Z0 + 90, Z1 - 90)
        if busy(x, z, 15):
            continue
        g = nether_ground(x, z)
        if g < 38:                                          # not in the lava lakes
            continue
        h, cap = int(rng.integers(18, 42)), int(rng.integers(6, 12))
        kind = "warped" if x > -150 else "crimson"
        n = 2 * cap + 3
        _p(out, "fungus", x - n // 2, g + 1, z - n // 2, (h + cap + 2, n, n), huge_fungus, j, h=h, cap=cap, kind=kind)
    return out, lands


def overworld_biome(cx, cz, sy):
    """Per-section biome: plains (twilight overrides) everywhere, the_end around
    the highest sky island."""
    x, z = cx * 16 + 8, cz * 16 + 8
    ex, ez, eR, et = END_ISLAND[:4]
    if sy * 16 >= et - 260 and abs(x - ex) < eR + 160 and abs(z - ez) < eR + 160:
        return "minecraft:the_end"
    return "minecraft:plains"


def nether_biome(cx, cz, sy):
    return "minecraft:warped_forest" if cx * 16 > -150 else "minecraft:crimson_forest"
