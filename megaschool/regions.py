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
    ("main", 2850, -200, 150, 92, -55, "sea_academy"),
    ("lighthouse", 3250, 520, 64, 34, -57, "lighthouse_school"),
    ("a", 2500, 380, 46, 0, -58, "island_classroom"),
    ("b", 2560, -820, 52, 0, -58, "island_classroom"),
    ("c", 3080, -1050, 58, 0, -57, "island_classroom"),
    ("d", 3300, -560, 44, 0, -58, "island_classroom"),
    ("e", 2700, 820, 40, 0, -58, "island_classroom"),
    ("f", 2380, -360, 34, 0, -59, None),
    ("g", 3400, 120, 30, 0, -59, None),
]
SPHERES = [("dome_school_big", 4150, -150, 130), ("dome_school_small", 4470, 470, 85), ("dome_school_small", 3960, -760, 85)]
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
    # x, z, R, top y, school, rock
    (-520, -2650, 190, 400, "sky_academy_white", "stone"),
    (430, -2950, 170, 720, "sky_academy_sand", "sandstone"),
    (-400, -3300, 160, 1040, "sky_academy_stone", "stone"),
    (480, -3560, 150, 1360, "sky_academy_brick", "stone"),
    (0, -3150, 180, 1720, "end_academy", "end"),
]
END_ISLAND = SKY[-1]


def sky_island(rng, R, rock, iseed):
    """A floating island: flat-topped plateau, rough rim, an inverted rocky cone
    beneath with strata, hanging roots and moss.  Local y = 0 is the top surface."""
    depth = int(R * 1.25)
    n = 2 * R + 1
    A = np.zeros((depth + 4, n, n), np.uint16)
    zs, xs = np.mgrid[0:n, 0:n].astype(np.float64)
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


def sky_island_size(R):
    depth = int(R * 1.25)
    return (depth + 4, 2 * R + 1, 2 * R + 1)


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
ACADEMY_NE = (-280, -230)                  # centre of the infernal academy


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
        for (cx, cz, rad) in ((GATE_NE[0], GATE_NE[1], 70), (ACADEMY_NE[0], ACADEMY_NE[1], 125)):
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


def _p(out, name, x, y, z, size, fn, seed=0, **kw):
    out.append(Piece(name, int(x), int(y), int(z), size, fn, abs(int(seed)), kw=kw))


def overworld():
    """-> (pieces, landforms) for the new overworld regions."""
    rng = np.random.default_rng(7)
    out, lands = [], [Ocean(), Sinkhole()]
    # --- archipelago
    for (name, ix, iz, R, pr, top, school) in ISLANDS:
        if school == "sea_academy":
            place_mcb_center(out, school, ix, top + 1, iz)
        elif school == "lighthouse_school":
            place_mcb_center(out, school, ix, top + 1, iz)
        elif school == "island_classroom":
            place_mcb(out, school, ix - 15, top + 1 - 4, iz - 10)
    for (a, b) in (("main", "lighthouse"), ("main", "a"), ("main", "b"), ("main", "d"), ("b", "c"), ("a", "e"), ("main", "f"), ("lighthouse", "g")):
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
    # --- glass spheres on the trench floor, tunnels, lift tube and pontoon
    sph = []
    floor = SEABED_DEEP - 20 + int(SPHERES[0][3] * 0.45)      # common floor level of the three spheres
    for (name, sx, sz, R) in SPHERES:
        y = floor - int(R * 0.45)
        place_mcb_center(out, name, sx, y, sz)
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
    # --- sinkhole: tower, ledge schools, bridges, waterfalls
    floor = LEDGES[0][1] + 1
    place_mcb_center(out, "pit_tower", SX, floor, SZ)
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
    # --- sky islands, stairways, bridges, waterfalls, little rocks
    for k, (x, z, R, top, school, rock) in enumerate(SKY):
        sz_ = sky_island_size(R)
        _p(out, "sky_island", x - R, top - sz_[0] + 4, z - R, sz_, sky_island, k, R=R, rock=rock, iseed=k + 1)
        place_mcb_center(out, school, x, top + 1, z)
        for j in range(14):
            rr = int(rng.integers(8, 22))
            a = rng.uniform(0, 2 * math.pi)
            d = R + rng.uniform(25, 110)
            ty = top + int(rng.integers(-120, 40))
            s2 = sky_island_size(rr)
            _p(out, "sky_rock", x + d * math.cos(a) - rr, ty - s2[0] + 4, z + d * math.sin(a) - rr, s2, sky_island,
               100 + 20 * k + j, R=rr, rock=rock, iseed=100 + 20 * k + j)
        if rock != "end":
            for a in (0.4, 3.3):
                fx, fz = x + (R - 8) * math.cos(a), z + (R - 8) * math.sin(a)
                h = top - GROUND - 1
                _p(out, "waterfall", fx, GROUND + 1, fz, (h, 1, 5), column, 0, h=h, kind="water", w=5)
                lands.append(Pond(fx + 2, fz, 14))
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
    place_mcb_center(out, "infernal_academy", ax, NETHER_FLOOR, az)
    X0, Z0, X1, Z1 = NETHER_BOX
    spots = []
    for _ in range(400):
        x, z = rng.integers(X0 + 100, X1 - 100), rng.integers(Z0 + 100, Z1 - 100)
        if math.hypot(x - ax, z - az) < 150 or math.hypot(x - gx, z - gz) < 90:
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
        if math.hypot(x - ax, z - az) < 140 or math.hypot(x - gx, z - gz) < 80:
            continue
        _p(out, "lavafall", x, 30, z, (600, 1, 3), column, 0, h=600, kind="lava", w=3)
    for j in range(60):                                     # glowstone hanging under the ceiling
        x, z = rng.integers(X0 + 100, X1 - 100), rng.integers(Z0 + 100, Z1 - 100)
        r = int(rng.integers(3, 8))
        c = nether_ceil(x, z)                               # hang from the ceiling (cluster's upper half)
        _p(out, "glowstone", x - r, c - 2 * r + 1, z - r, (2 * r + 1, 2 * r + 1, 2 * r + 1), glow_cluster, j, r=r)
    for j in range(70):                                     # giant fungi
        x, z = rng.integers(X0 + 90, X1 - 90), rng.integers(Z0 + 90, Z1 - 90)
        if math.hypot(x - ax, z - az) < 135 or math.hypot(x - gx, z - gz) < 80:
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
