"""School facilities and outdoor scenery, designed with minecraft-build-design
(github.com/yimeng-YM/minecraft-build-design, toolkit `mcbuild`).

Every function takes an mcbuild Frame F whose local (0, 0, 0) is the first air
block above the grass at the plot's north-west corner (world y = -60): the
ground is local y = -1 and a design may dig to y = -3 (bedrock is at -4).
Local axes: +x east, +y up, +z south.  The kit's rules pass sets connections,
stair shapes and leaf distances; `mcb verify` checks states, support, water
containment, light and walkability.  The palette favours warm lights for the
twilight version of the map."""
from __future__ import annotations

import math
import random

from mcbuild import shapes, nature, AIR

# ------------------------------------------------------------------ helpers


def fbm(seed, octaves=3):
    """Smooth 2-D value noise in about [-1, 1] (no numpy needed inside design scripts)."""
    rnd = random.Random(seed)
    tabs = [{} for _ in range(octaves)]

    def lattice(t, i, j):
        k = (i, j)
        if k not in tabs[t]:
            tabs[t][k] = rnd.uniform(-1, 1)
        return tabs[t][k]

    def one(t, x, z):
        i, j = math.floor(x), math.floor(z)
        fx, fz = x - i, z - j
        sx, sz = fx * fx * (3 - 2 * fx), fz * fz * (3 - 2 * fz)
        a = lattice(t, i, j) * (1 - sx) + lattice(t, i + 1, j) * sx
        b = lattice(t, i, j + 1) * (1 - sx) + lattice(t, i + 1, j + 1) * sx
        return a * (1 - sz) + b * sz

    def f(x, z):
        s, amp, tot = 0.0, 1.0, 0.0
        for t in range(octaves):
            s += amp * one(t, x * 2 ** t, z * 2 ** t)
            tot += amp
            amp *= 0.5
        return s / tot
    return f


def lamp(F, x, z, y=0):
    """Park lamp: stone foot, dark post, fence arms with two hanging lanterns."""
    F.put(x, y, z, 'polished_andesite')
    F.fill((x, y + 1, z), (x, y + 4, z), 'polished_blackstone_wall')
    F.fill((x, y + 5, z - 1), (x, y + 5, z + 1), 'dark_oak_fence')
    F.put(x, y + 4, z - 1, 'lantern[hanging=true]')
    F.put(x, y + 4, z + 1, 'lantern[hanging=true]')


def bench(F, x, z, facing='north', y=0, wood='spruce'):
    """3-seat bench: stairs (backrest away from `facing`) with trapdoor arms."""
    dx, dz = (1, 0) if facing in ('north', 'south') else (0, 1)
    for k in range(3):
        F.put(x + dx * k, y, z + dz * k, f'{wood}_stairs[facing={facing}]')
    if dx:
        F.put(x - 1, y, z, f'{wood}_trapdoor[open=true,facing=west]')
        F.put(x + 3, y, z, f'{wood}_trapdoor[open=true,facing=east]')
    else:
        F.put(x, y, z - 1, f'{wood}_trapdoor[open=true,facing=north]')
        F.put(x, y, z + 3, f'{wood}_trapdoor[open=true,facing=south]')


def floodlight(F, x, z, h=14):
    F.fill((x, 0, z), (x, h - 1, z), 'gray_concrete')
    F.fill((x - 1, h, z), (x + 1, h, z), 'iron_bars')
    F.fill((x - 1, h + 1, z), (x + 1, h + 1, z), 'sea_lantern')
    F.fill((x - 1, h + 2, z), (x + 1, h + 2, z), 'smooth_stone_slab[type=bottom]')


def willow(F, x, z, rng, height=None):
    """Weeping willow: trunk, round crown, curtains of leaves hanging to the ground."""
    h = height or rng.randint(6, 8)
    F.fill((x, 0, z), (x, h - 1, z), 'oak_log[axis=y]')
    leaf = 'oak_leaves[persistent=true]'
    r = 3.6
    for dx in range(-4, 5):
        for dy in range(-1, 3):
            for dz in range(-4, 5):
                d = math.sqrt(dx * dx + (dy * 1.6) ** 2 + dz * dz)
                if d <= r and not (dx == 0 and dz == 0 and dy < 1):
                    F.put(x + dx, h + dy, z + dz, leaf)
    for k in range(18):
        a = k / 18 * 2 * math.pi
        rr = 3.2 + 0.6 * rng.random()
        sx, sz = round(x + rr * math.cos(a)), round(z + rr * math.sin(a))
        drop = rng.randint(3, h - 1)
        F.fill((sx, h - drop, sz), (sx, h - 1, sz), leaf)


def broadleaf(F, x, z, rng, kind='oak'):
    log, leaf = {'oak': ('oak_log', 'oak_leaves'), 'birch': ('birch_log', 'birch_leaves'),
                 'cherry': ('cherry_log', 'cherry_leaves'), 'dark': ('dark_oak_log', 'dark_oak_leaves')}[kind]
    nature.round_tree(F, x, z, height=rng.randint(5, 8) if kind != 'birch' else rng.randint(7, 10),
                      radius=rng.uniform(2.6, 3.6) if kind != 'birch' else 2.2, rng=rng,
                      log=f'{log}[axis=y]', leaf=f'{leaf}[persistent=true]')


def arched_bridge(F, x0, z, length, width=2, y0=0, rise=4.0):
    """Hump-backed bridge along +x, walkable: heights in half blocks (slabs/stone)."""
    for i in range(length + 1):
        t = i / length
        hh = round(2 * rise * math.sin(math.pi * t))          # height in half blocks
        top = y0 + hh // 2
        half = hh % 2
        x = x0 + i
        for w in range(-width, width + 1):
            for yy in range(y0 - 1, top):
                F.put(x, yy, z + w, 'stone_bricks')
            if half:
                F.put(x, top, z + w, 'stone_brick_slab[type=bottom]')
        for w in (-width - 1, width + 1):
            for yy in range(y0 - 1, top + half):
                F.put(x, yy, z + w, 'stone_bricks')
            F.put(x, top + half, z + w, 'stone_brick_wall')
            if i % 12 == 6:
                F.put(x, top + half + 1, z + w, 'lantern')


# ------------------------------------------------------------------ campus lake
def lake_garden(F, W=200, D=220, seed=3):
    """校园湖: organic lake, island pavilion reached by a zig-zag boardwalk, a
    hump-backed bridge to a willow island, lily pads, a lamp-lit promenade."""
    rng = random.Random(seed)
    noise = fbm(seed)
    cx, cz = W // 2, D // 2 + 5
    F.cur = 'ground'
    F.fill((0, -1, 0), (W - 1, -1, D - 1), 'grass_block')
    walk = ['polished_andesite', 'polished_andesite', 'andesite', 'stone_bricks']
    bank = ['sand', 'gravel', 'mud', 'coarse_dirt']
    F.cur = 'lake'
    water = set()
    for x in range(W):
        for z in range(D):
            r = math.hypot((x - cx) / 74, (z - cz) / 72) + 0.16 * noise(x / 38, z / 38)
            if r < 1.0:
                F.put(x, -1, z, 'water'); F.put(x, -2, z, 'water')
                F.put(x, -3, z, rng.choice(['clay', 'clay', 'sand', 'gravel']))
                water.add((x, z))
            elif r < 1.07:
                F.put(x, -1, z, rng.choice(bank))
            elif 1.13 < r < 1.20:
                F.put(x, -1, z, rng.choice(walk))
    # islands
    def island(ix, iz, R):
        for x in range(ix - R - 3, ix + R + 4):
            for z in range(iz - R - 3, iz + R + 4):
                d = math.hypot(x - ix, z - iz) + 1.5 * noise(x / 5, z / 5)
                if d < R:
                    F.put(x, -3, z, 'dirt'); F.put(x, -2, z, 'dirt')
                    F.put(x, -1, z, 'grass_block' if d < R - 2 else rng.choice(bank))
                    water.discard((x, z))
    pix, piz = cx + 26, cz - 22
    island(pix, piz, 13)
    wix, wiz = cx - 36, cz + 16
    island(wix, wiz, 11)
    for (x, z) in list(water):
        if rng.random() < 0.035 and all((x + a, z + b) in water for a in (-1, 1) for b in (-1, 1)):
            F.put(x, 0, z, 'lily_pad')
    # pavilion (亭) on the main island: slab platform, red columns, hipped tile roof
    F.cur = 'pavilion'
    px, pz = pix - 4, piz - 4
    F.fill((px, 0, pz), (px + 8, 0, pz + 8), 'smooth_stone_slab[type=bottom]')
    for (a, b) in ((1, 1), (7, 1), (1, 7), (7, 7)):
        F.fill((px + a, 1, pz + b), (px + a, 4, pz + b), 'stripped_mangrove_log[axis=y]')
    F.fill((px + 1, 5, pz + 1), (px + 7, 5, pz + 7), 'stripped_mangrove_log[axis=x]')
    F.fill((px + 2, 5, pz + 2), (px + 6, 5, pz + 6), 'dark_oak_planks')
    top = shapes.hip_roof(F, px + 1, pz + 1, px + 7, pz + 7, 6, 'deepslate_tile_stairs', overhang=2,
                          fill='deepslate_tiles')
    F.put(px + 4, top, pz + 4, 'gold_block')
    F.put(px + 4, 4, pz + 4, 'lantern[hanging=true]')
    bench(F, px + 3, pz + 2, 'south')
    # zig-zag boardwalk from the island's east shore to the lake's east shore
    F.cur = 'boardwalk'
    x, z = pix + 11, piz
    for dx, dz, n in ((1, 0, 10), (0, 1, 6), (1, 0, 10), (0, -1, 6), (1, 0, 10), (0, 1, 4), (1, 0, 12)):
        for _ in range(n):
            x += dx; z += dz
            for a in (-1, 0, 1):
                F.put(x + (a if dz else 0), 0, z + (a if dx else 0), 'spruce_slab[type=bottom]')
                F.put(x + (a if dz else 0), -1, z + (a if dx else 0), 'spruce_planks' if (x + z) % 4 else 'spruce_log[axis=y]')
            if (x + z) % 5 == 0:
                for s in (-2, 2):
                    F.put(x + (s if dz else 0), 0, z + (s if dx else 0), 'spruce_fence')
    # hump-backed stone bridge from the west shore to the willow island
    F.cur = 'bridge'
    arched_bridge(F, wix - 46, wiz, 36, width=2, y0=0, rise=3.5)
    # trees: willows and cherries around the shore, big oaks in the corners
    F.cur = 'trees'
    for k in range(22):
        a = k / 22 * 2 * math.pi + 0.13 * math.sin(k * 7)
        r = 1.10 + 0.05 * math.sin(k * 3)
        tx, tz = round(cx + 74 * r * math.cos(a)), round(cz + 72 * r * math.sin(a))
        if k % 4 == 1:
            broadleaf(F, tx, tz, rng, 'cherry')
        else:
            willow(F, tx, tz, rng)
    willow(F, wix, wiz, rng, 8)
    for (tx, tz) in ((12, 14), (W - 14, 16), (14, D - 14), (W - 14, D - 16)):
        broadleaf(F, tx, tz, rng, 'oak')
    # promenade lamps and benches
    F.cur = 'lamps'
    for k in range(30):
        a = k / 30 * 2 * math.pi
        lx, lz = round(cx + 74 * 1.24 * math.cos(a)), round(cz + 72 * 1.24 * math.sin(a))
        lamp(F, lx, lz)
        if k % 3 == 1:
            bench(F, lx + 2, lz + 2, 'north')
    F.cur = 'ground'
    F.fill((cx - 2, -1, D - 30), (cx + 2, -1, D - 1), 'polished_andesite')
    return {'walk_start': (cx, 0, D - 3), 'walk_targets': {'pavilion': (px + 4, 1, pz + 4), 'willow_island': (wix + 6, 0, wiz)}}


# ------------------------------------------------------------------ pool, tennis, ping-pong
def sports_park(F, W=200, D=220, seed=5):
    """室外游泳池 (50 x 25, lanes, underwater lights, diving tower, bleachers,
    pool house), four fenced tennis courts, a ping-pong court, fitness bars."""
    rng = random.Random(seed)
    px0, pz0, PW, PL = 30, 40, 25, 50
    F.cur = 'ground'
    F.fill((0, -1, 0), (W - 1, -1, D - 1), 'grass_block')
    for x in range(px0 - 14, px0 + PW + 15):
        for z in range(pz0 - 14, pz0 + PL + 23):
            F.put(x, -1, z, 'polished_diorite' if rng.random() < 0.15 else 'smooth_stone')
    F.cur = 'pool'
    F.fill((px0 - 1, -3, pz0 - 1), (px0 + PW, -2, pz0 + PL), 'light_blue_concrete')
    F.fill((px0, -2, pz0), (px0 + PW - 1, -1, pz0 + PL - 1), 'water')
    for i in range(8):
        F.fill((px0 + 2 + 3 * i, -3, pz0 + 2), (px0 + 2 + 3 * i, -3, pz0 + PL - 3), 'blue_concrete')
    shapes.walls(F, (px0 - 1, -1, pz0 - 1), (px0 + PW, -1, pz0 + PL), 'smooth_quartz')
    for z in range(pz0 + 4, pz0 + PL - 2, 6):
        F.put(px0 - 1, -2, z, 'sea_lantern'); F.put(px0 + PW, -2, z, 'sea_lantern')
    for i in range(8):
        F.put(px0 + 2 + 3 * i, 0, pz0 - 2, 'smooth_quartz_stairs[facing=north]')
    # diving tower at the south end: 3 m and 10 m boards, stair up from the deck
    F.cur = 'diving'
    for x in (px0 + 8, px0 + PW - 9):
        F.fill((x, 0, pz0 + PL + 4), (x, 9, pz0 + PL + 4), 'white_concrete')
    F.fill((px0 + 8, 3, pz0 + PL - 2), (px0 + PW - 9, 3, pz0 + PL + 4), 'smooth_quartz_slab[type=top]')
    F.fill((px0 + 8, 9, pz0 + PL - 4), (px0 + PW - 9, 9, pz0 + PL + 7), 'smooth_quartz_slab[type=top]')
    for z in range(pz0 + PL - 4, pz0 + PL + 8):                  # side rails; the jump edge stays open
        F.put(px0 + 8, 10, z, 'iron_bars'); F.put(px0 + PW - 9, 10, z, 'iron_bars')
    shapes.stair_flight(F, (px0 + 12, 0, pz0 + PL + 17), 'north', 10, 'quartz_stairs', support='smooth_quartz')
    # bleachers on the west side, facing east
    F.cur = 'bleachers'
    for r in range(6):
        for z in range(pz0, pz0 + PL):
            for y in range(r):
                F.put(px0 - 8 - r, y, z, 'light_gray_concrete')
            F.put(px0 - 8 - r, r, z, 'blue_concrete' if (z >> 2) & 1 else 'white_concrete')
    # fence with a gate, floodlights, lifeguard chair, pool house
    F.cur = 'fence'
    shapes.walls(F, (px0 - 15, 0, pz0 - 15), (px0 + PW + 15, 1, pz0 + PL + 23), 'iron_bars')
    F.fill((px0 + 10, 0, pz0 + PL + 23), (px0 + 14, 1, pz0 + PL + 23), AIR)
    F.cur = 'lights'
    for (x, z) in ((px0 - 14, pz0 - 14), (px0 + PW + 14, pz0 - 14), (px0 - 14, pz0 + PL + 22), (px0 + PW + 14, pz0 + PL + 22)):
        floodlight(F, x, z)
    F.fill((px0 + PW + 3, 0, pz0 + 24), (px0 + PW + 3, 2, pz0 + 24), 'white_concrete')
    F.put(px0 + PW + 3, 3, pz0 + 24, 'red_concrete')
    F.cur = 'pool_house'
    hx0, hz0 = 58, 116
    F.fill((hx0, 0, hz0), (hx0 + 34, 5, hz0 + 10), 'white_concrete')
    F.fill((hx0 + 1, 1, hz0 + 1), (hx0 + 33, 4, hz0 + 9), AIR)
    F.fill((hx0 + 1, 1, hz0), (hx0 + 33, 3, hz0), 'glass_pane')
    F.double_door(hx0 + 16, 1, hz0, 'south', wood='birch')
    for x in range(hx0 + 4, hx0 + 32, 6):
        F.hanging_lantern(x, 4, hz0 + 5, chain=0)
    shapes.flat_roof(F, hx0, hz0, hx0 + 34, hz0 + 10, 6, 'smooth_stone_slab[type=bottom]', overhang=2)
    # four tennis courts
    F.cur = 'tennis'
    for k in range(4):
        tennis_court(F, 118, 8 + 48 * k)
    # ping-pong court + fitness bars
    F.cur = 'pingpong'
    F.fill((10, -1, 140), (92, -1, 208), 'smooth_stone')
    for i in range(6):
        for j in range(4):
            pingpong(F, 16 + 12 * i, 146 + 16 * j)
    for i in range(5):
        fitness(F, 18 + 14 * i, 128)
    floodlight(F, 10, 140); floodlight(F, 92, 208)
    # path, lamps, birch rows
    F.cur = 'path'
    F.fill((100, -1, 0), (105, -1, D - 1), 'smooth_stone')
    for k in range(9):
        lamp(F, 102, 10 + 24 * k)
    F.cur = 'trees'
    for z in range(6, D - 6, 14):
        broadleaf(F, 4, z, rng, 'birch'); broadleaf(F, W - 4, z, rng, 'birch')
    return {'walk_start': (102, 0, D - 3), 'walk_targets': {'pool_deck': (px0 + 2, 0, pz0 + PL + 10),
                                                           'diving_10m': (px0 + 12, 10, pz0 + PL + 1)}}


def tennis_court(F, x0, z0):
    F.fill((x0, -1, z0), (x0 + 71, -1, z0 + 39), 'green_terracotta')
    F.fill((x0 + 11, -1, z0 + 7), (x0 + 60, -1, z0 + 32), 'blue_terracotta')
    for a, b in (((11, 7), (60, 32)), ((11, 10), (60, 29)), ((22, 10), (49, 29))):
        shapes.walls(F, (x0 + a[0], -1, z0 + a[1]), (x0 + b[0], -1, z0 + b[1]), 'white_concrete')
    F.fill((x0 + 22, -1, z0 + 19), (x0 + 49, -1, z0 + 20), 'white_concrete')
    F.fill((x0 + 35, 0, z0 + 6), (x0 + 36, 0, z0 + 33), 'white_stained_glass_pane')
    F.put(x0 + 35, 0, z0 + 5, 'polished_blackstone_wall'); F.put(x0 + 35, 0, z0 + 34, 'polished_blackstone_wall')
    shapes.walls(F, (x0, 0, z0), (x0 + 71, 3, z0 + 39), 'iron_bars')
    F.fill((x0 + 34, 0, z0 + 39), (x0 + 37, 2, z0 + 39), AIR)
    floodlight(F, x0 + 1, z0 + 1); floodlight(F, x0 + 70, z0 + 38)


def pingpong(F, x, z):
    for a, b in ((0, 0), (0, 4), (2, 0), (2, 4)):
        F.put(x + a, 0, z + b, 'polished_blackstone_wall')
    F.fill((x, 1, z), (x + 2, 1, z + 4), 'warped_slab[type=bottom]')
    F.fill((x, 2, z + 2), (x + 2, 2, z + 2), 'white_stained_glass_pane')


def fitness(F, x, z):
    F.fill((x, 0, z), (x, 2, z), 'blue_concrete'); F.fill((x + 4, 0, z), (x + 4, 2, z), 'blue_concrete')
    F.fill((x + 1, 2, z), (x + 3, 2, z), 'iron_bars')
    for a in (0, 2):
        F.fill((x + a, 0, z + 4), (x + a, 1, z + 4), 'yellow_concrete')
        F.fill((x + a, 0, z + 8), (x + a, 1, z + 8), 'yellow_concrete')
        F.fill((x + a, 1, z + 5), (x + a, 1, z + 7), 'iron_bars')


# ------------------------------------------------------------------ auditorium
def auditorium(F, W=200, D=220, seed=7):
    """大礼堂: dark podium with a wide flight of steps, twelve 42-block
    columns, tall slit windows between pilasters, a lit hall inside and a
    heavy hipped roof."""
    rng = random.Random(seed)
    x0, x1, z0, z1 = 30, 170, 60, 170
    H = 46
    wall = ['smooth_quartz'] * 6 + ['calcite'] * 3 + ['polished_diorite']
    base = ['polished_deepslate'] * 5 + ['deepslate_bricks'] * 2 + ['cobbled_deepslate']
    F.cur = 'ground'
    F.fill((0, -1, 0), (W - 1, -1, D - 1), 'grass_block')
    for x in range(x0 - 10, x1 + 11):
        for z in range(8, z0 - 20):
            F.put(x, -1, z, rng.choice(['polished_andesite', 'polished_andesite', 'smooth_stone', 'andesite']))
    F.cur = 'podium'
    for x in range(x0 - 4, x1 + 5):
        for z in range(z0 - 22, z1 + 5):
            for y in range(0, 5):
                F.put(x, y, z, rng.choice(base))
    # steps up the podium (stairs are walkable), between dark cheek walls
    for k in range(5):                                       # row k: a stair at height k, then a full block
        z = z0 - 23 - 2 * (4 - k)
        if k:
            F.fill((x0 + 30, 0, z), (x1 - 30, k - 1, z + 1), 'polished_deepslate')
        F.fill((x0 + 30, k, z), (x1 - 30, k, z), 'polished_deepslate_stairs[facing=south]')
        F.fill((x0 + 30, k, z + 1), (x1 - 30, k, z + 1), 'polished_deepslate')
    F.cur = 'hall'
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            if x in (x0, x1) or z in (z0, z1):
                for y in range(5, 5 + H):
                    F.put(x, y, z, rng.choice(wall))
    F.fill((x0 + 1, 4, z0 + 1), (x1 - 1, 4, z1 - 1), 'dark_oak_planks')     # floor flush with the doorways
    F.fill((x0 + 1, 5, z0 + 1), (x1 - 1, 4 + H, z1 - 1), AIR)
    F.fill((x0 + 1, 5 + H, z0 + 1), (x1 - 1, 5 + H, z1 - 1), 'smooth_quartz')
    for x in range(x0 + 6, x1 - 4, 10):
        for z in range(z0 + 6, z1 - 4, 10):
            F.hanging_lantern(x, 4 + H, z, chain=2)
    for z in range(z0 + 30, z1 - 8, 3):                     # rows of seats facing the stage (north)
        F.fill((x0 + 20, 5, z), (x1 - 20, 5, z), 'red_terracotta')
        F.fill((x0 + 76, 5, z), (x0 + 82, 5, z), AIR)           # centre aisle
    F.fill((x0 + 30, 5, z0 + 6), (x1 - 30, 6, z0 + 16), 'dark_oak_planks')
    # pilasters and slit windows on all sides
    for x in range(x0, x1 + 1, 10):
        for z in (z0 - 1, z1 + 1):
            F.fill((x, 5, z), (x + 1, 4 + H, z), 'quartz_pillar[axis=y]')
    for z in range(z0, z1 + 1, 10):
        for x in (x0 - 1, x1 + 1):
            F.fill((x, 5, z), (x, 4 + H, z + 1), 'quartz_pillar[axis=y]')
    for x in range(x0 + 5, x1 - 3, 10):
        for z in (z0, z1):
            F.fill((x, 10, z), (x + 1, H - 4, z), 'gray_stained_glass_pane')
            F.fill((x, 9, z), (x + 1, 9, z), 'polished_deepslate')
            F.fill((x, H - 3, z), (x + 1, H - 3, z), 'polished_deepslate')
    for z in range(z0 + 5, z1 - 3, 10):
        for x in (x0, x1):
            F.fill((x, 10, z), (x, H - 4, z + 1), 'gray_stained_glass_pane')
    # colonnade, entablature with a dark shadow line, portal and doors
    F.cur = 'colonnade'
    for i in range(12):
        cx = x0 + 4 + 12 * i
        F.fill((cx - 1, 5, z0 - 17), (cx + 4, 5, z0 - 12), 'polished_deepslate')
        F.fill((cx, 6, z0 - 16), (cx + 3, 4 + H, z0 - 13), 'quartz_pillar[axis=y]')
    F.fill((x0 - 4, 4 + H, z0 - 19), (x1 + 4, 4 + H, z1 + 4), 'polished_deepslate_slab[type=top]')
    F.fill((x0 - 3, 5 + H, z0 - 18), (x1 + 3, 12 + H, z1 + 3), 'smooth_quartz')
    F.fill((x0 - 2, 5 + H, z0 - 17), (x1 + 2, 11 + H, z1 + 2), 'smooth_quartz')
    F.fill((x0 + 50, 5, z0), (x1 - 50, 20, z0), 'polished_deepslate')
    F.fill((x0 + 50, 18, z0 - 1), (x1 - 50, 18, z0 - 1), 'polished_deepslate')        # canopy carrying the lanterns
    for x in range(x0 + 54, x1 - 52, 6):
        F.fill((x, 7, z0), (x + 2, 16, z0), 'black_stained_glass_pane')
        F.double_door(x, 5, z0, 'south', wood='dark_oak')
        F.hanging_lantern(x + 1, 17, z0 - 1, chain=0)
    F.cur = 'roof'
    shapes.hip_roof(F, x0 - 3, z0 - 18, x1 + 3, z1 + 3, 13 + H, 'deepslate_tile_stairs', overhang=2,
                    fill='polished_deepslate')
    F.cur = 'garden'
    for x in range(x0 - 6, x1 + 7, 16):
        broadleaf(F, x, 4, rng, 'oak'); lamp(F, x + 8, 4)
    for z in range(z0 - 10, D - 6, 13):
        broadleaf(F, x0 - 16, z, rng, 'oak'); broadleaf(F, x1 + 16, z, rng, 'oak')
        lamp(F, x0 - 9, z + 6); lamp(F, x1 + 9, z + 6)
    for x in range(x0, x1 + 1, 12):
        F.fill((x, 5, z0 - 21), (x, 5, z0 - 21), 'polished_blackstone_wall')
        F.put(x, 6, z0 - 21, 'lantern')
    mid = (x0 + x1) // 2
    return {'walk_start': (mid, 0, 10), 'walk_targets': {'portico': (mid + 3, 5, z0 - 8), 'hall': (x0 + 79, 5, z0 + 24)}}


# ------------------------------------------------------------------ greenhouse
def greenhouse(F, W=200, D=220, seed=11):
    """植物园: three glass barrel vaults (palms, cherries, flowers inside, warm
    lanterns), a hedged garden, a pond and lamp-lit gravel walks."""
    rng = random.Random(seed)
    F.cur = 'ground'
    F.fill((0, -1, 0), (W - 1, -1, D - 1), 'grass_block')
    gravel = ['gravel', 'gravel', 'gravel', 'coarse_dirt', 'packed_mud']
    for x in range(W):
        for z in range(20, 24):
            F.put(x, -1, z, rng.choice(gravel))
    for x in range(97, 103):
        for z in range(D):
            F.put(x, -1, z, rng.choice(gravel))
    for k, (x0, w, l, h) in enumerate(((16, 31, 96, 15), (84, 33, 120, 19), (153, 31, 96, 15))):
        F.cur = f'vault_{k}'
        vault(F, rng, x0, 32, w, l, h)
    F.cur = 'garden'
    for x in range(8, W - 8):
        if 94 < x < 106:
            continue
        F.put(x, 0, 160, 'azalea_leaves[persistent=true]'); F.put(x, 0, 206, 'azalea_leaves[persistent=true]')
    for z in range(160, 207):
        F.put(8, 0, z, 'azalea_leaves[persistent=true]'); F.put(W - 9, 0, z, 'azalea_leaves[persistent=true]')
    for x in range(36, 69):
        for z in range(170, 197):
            d = math.hypot((x - 52) / 13, (z - 183) / 10)
            if d < 1:
                F.put(x, -1, z, 'water'); F.put(x, -2, z, 'water'); F.put(x, -3, z, 'clay')
            elif d < 1.15:
                F.put(x, -1, z, 'smooth_stone')
    spots = [(x, z) for x in range(110, 189) for z in range(166, 201) if rng.random() < 0.3]
    nature.flowers(F, spots, rng)
    for k in range(8):
        lamp(F, 95, 8 + 26 * k); lamp(F, 104, 8 + 26 * k)
    return {'walk_start': (99, 0, D - 3), 'walk_targets': {'central_vault': (99, 0, 90)}}


def vault(F, rng, x0, z0, w, l, h):
    c = (w - 1) / 2
    F.fill((x0, -1, z0), (x0 + w - 1, 0, z0 + l - 1), 'bricks')
    F.fill((x0 + 1, -1, z0 + 1), (x0 + w - 2, -1, z0 + l - 2), 'grass_block')
    F.fill((x0 + 1, 0, z0 + 1), (x0 + w - 2, 0, z0 + l - 2), AIR)
    prof = [round(h * math.sqrt(max(0.0, 1 - ((x - c) / c) ** 2))) for x in range(w)]
    for z in range(z0, z0 + l):
        for i in range(w):
            lo = min(prof[i], max(prof[i - 1] if i else 0, prof[i + 1] if i < w - 1 else 0) + 1)
            for yy in range(min(lo, prof[i]), prof[i] + 1):
                F.put(x0 + i, yy + 1, z, 'white_concrete' if (z - z0) % 6 == 0 else 'glass')
    for z in (z0, z0 + l - 1):
        for i in range(w):
            for yy in range(1, prof[i] + 1):
                door = abs(i - c) < 2 and yy < 4
                F.put(x0 + i, yy, z, AIR if door else ('white_concrete' if i % 5 == 0 else 'glass'))
            if abs(i - c) < 2:                                   # doorway flush with the walk
                F.put(x0 + i, 0, z, AIR)
                F.put(x0 + i, -1, z, 'gravel')
    for k in range(6):
        tx, tz = x0 + 4 + rng.randint(0, w - 9), z0 + 6 + k * ((l - 12) // 6)
        kind = rng.choice(['palm', 'cherry', 'oak'])
        if kind == 'palm':
            nature.palm(F, tx, tz, rng.randint(7, min(11, h - 4)), lean=(rng.choice((-1, 0, 1)), 0))
        else:
            broadleaf(F, tx, tz, rng, kind)
    spots = [(x, z) for x in range(x0 + 1, x0 + w - 1) for z in range(z0 + 1, z0 + l - 1) if rng.random() < 0.12]
    nature.flowers(F, spots, rng)
    for z in range(z0 + 5, z0 + l - 3, 10):
        F.hanging_lantern(x0 + round(c), h, z, chain=0)


# ------------------------------------------------------------------ small facilities
def walkway(F, L=180):
    """风雨廊: covered walk, a lantern under every bay, benches between posts."""
    F.cur = 'walkway'
    F.fill((0, -1, 0), (4, -1, L - 1), 'smooth_stone')
    for z in range(0, L, 6):
        F.fill((0, 0, z), (0, 3, z), 'white_concrete'); F.fill((4, 0, z), (4, 3, z), 'white_concrete')
    F.fill((-1, 4, -1), (5, 4, L), 'smooth_stone_slab[type=bottom]')
    shapes.walls(F, (0, 4, 0), (4, 4, L - 1), 'smooth_quartz')
    for z in range(3, L, 6):
        F.put(2, 3, z, 'lantern[hanging=true]')
    for z in range(8, L - 4, 24):
        for k in range(3):
            F.put(1, 0, z + k, 'spruce_stairs[facing=east]')
    return {'walk_start': (2, 0, -2), 'walk_targets': {'end': (2, 0, L - 2)}}


def fountain(F, R=12):
    c = R + 2
    F.cur = 'fountain'
    shapes.disc(F, (c, -1, c), R + 2, 'smooth_quartz')
    shapes.disc(F, (c, -1, c), R, 'water')
    shapes.disc(F, (c, -2, c), R, 'light_blue_terracotta')
    shapes.ring(F, (c, 0, c), R, 'smooth_quartz_slab[type=bottom]')
    shapes.ring(F, (c, -1, c), R + 1, 'smooth_quartz')
    shapes.disc(F, (c, -1, c), 3, 'polished_deepslate')
    shapes.disc(F, (c, 0, c), 3, 'polished_deepslate')
    F.fill((c - 1, 1, c - 1), (c + 1, 7, c + 1), 'quartz_pillar[axis=y]')
    F.put(c, 8, c, 'sea_lantern')
    for k in range(12):
        a = k / 12 * 2 * math.pi
        F.put(round(c + (R - 1) * math.cos(a)), -2, round(c + (R - 1) * math.sin(a)), 'sea_lantern')
    return {}


def bus_stop(F):
    F.cur = 'bus_stop'
    F.fill((-1, -1, -1), (9, -1, 3), 'smooth_stone')
    F.fill((1, 0, 2), (7, 2, 2), 'glass_pane')
    for x in (0, 8):
        F.fill((x, 0, 2), (x, 2, 2), 'polished_blackstone_wall')
    F.fill((-1, 3, 0), (9, 3, 2), 'smooth_stone_slab[type=bottom]')
    F.fill((9, 0, 1), (9, 2, 2), 'sea_lantern')
    F.fill((2, 0, 1), (6, 0, 1), 'spruce_slab[type=bottom]')
    F.fill((-3, 0, 0), (-3, 3, 0), 'iron_bars'); F.put(-3, 4, 0, 'blue_concrete')
    return {}


def bus(F, x, z):
    """School bus 3 x 12 x 5, nose to the north, headlights on."""
    F.fill((x, 1, z), (x + 2, 3, z + 11), 'yellow_concrete')
    F.fill((x, 2, z + 1), (x, 2, z + 10), 'black_stained_glass_pane')
    F.fill((x + 2, 2, z + 1), (x + 2, 2, z + 10), 'black_stained_glass_pane')
    F.fill((x, 2, z), (x + 2, 2, z), 'black_stained_glass_pane')
    F.fill((x, 4, z + 1), (x + 2, 4, z + 10), 'smooth_quartz_slab[type=bottom]')
    F.fill((x, 0, z + 1), (x + 2, 0, z + 10), 'black_concrete')
    for a, b in ((0, 2), (2, 2), (0, 9), (2, 9)):
        F.put(x + a, 0, z + b, 'coal_block')
    F.put(x, 1, z, 'ochre_froglight'); F.put(x + 2, 1, z, 'ochre_froglight')
    F.put(x, 1, z + 11, 'red_concrete'); F.put(x + 2, 1, z + 11, 'red_concrete')
    F.fill((x, 1, z + 1), (x, 1, z + 10), 'black_concrete'); F.fill((x + 2, 1, z + 1), (x + 2, 1, z + 10), 'black_concrete')


def bus_lot(F, W=300, D=80, seed=13):
    rng = random.Random(seed)
    F.cur = 'lot'
    F.fill((0, -1, 0), (W - 1, -1, D - 1), 'gray_concrete')
    shapes.walls(F, (0, -1, 0), (W - 1, -1, D - 1), 'smooth_stone')
    for x in range(6, W - 6, 6):
        F.fill((x, -1, 4), (x, -1, 18), 'yellow_concrete'); F.fill((x, -1, D - 19), (x, -1, D - 5), 'yellow_concrete')
    F.cur = 'buses'
    for x in range(8, W - 8, 6):
        if rng.random() < 0.8:
            bus(F, x + 1, 5)
        if rng.random() < 0.7:
            bus(F, x + 1, D - 17)
    F.cur = 'lamps'
    for x in range(10, W, 30):
        lamp(F, x, D // 2)
    return {}


def car_park(F, W=300, D=80, seed=17):
    rng = random.Random(seed)
    F.cur = 'lot'
    F.fill((0, -1, 0), (W - 1, -1, D - 1), 'gray_concrete')
    shapes.walls(F, (0, -1, 0), (W - 1, -1, D - 1), 'smooth_stone')
    rows = (4, D - 9, D // 2 - 7, D // 2 + 2)
    for x in range(4, W - 4, 3):
        for z in rows:
            F.fill((x, -1, z - 1), (x, -1, z + 5), 'white_concrete')
    F.cur = 'cars'
    for x in range(5, W - 5, 3):
        for z in rows:
            if rng.random() < 0.62:
                c = rng.choice(['white', 'black', 'gray', 'light_gray', 'red', 'blue'])
                F.fill((x, 0, z), (x + 1, 0, z + 4), f'{c}_concrete')
                F.fill((x, 1, z + 1), (x + 1, 1, z + 3), 'gray_stained_glass_pane')
                F.fill((x, 2, z + 1), (x + 1, 2, z + 3), 'smooth_stone_slab[type=bottom]')
                F.put(x, 0, z, 'ochre_froglight'); F.put(x + 1, 0, z, 'ochre_froglight')
    F.cur = 'lamps'
    for x in range(12, W, 24):
        lamp(F, x, 14); lamp(F, x, D - 15)
    F.cur = 'trees'
    for x in range(6, W, 12):
        broadleaf(F, x, D // 2, rng, 'oak')
    return {}


def water_tower(F):
    """巨型水塔 centred on local (0, 0): eight legs with cross bracing, a shaft
    with a ladder, a 70-wide tank 250 blocks up, warning lights on top."""
    R, TOP, TH = 30, 250, 52
    legs = [(round(R * math.cos(k * math.pi / 4)), round(R * math.sin(k * math.pi / 4))) for k in range(8)]
    F.cur = 'base'
    shapes.disc(F, (0, -1, 0), R + 6, 'polished_andesite')
    F.cur = 'legs'
    for (x, z) in legs:
        shapes.cylinder(F, (x, 0, z), 4, 6, 'polished_deepslate')
        shapes.cylinder(F, (x, 0, z), 2, TOP, 'light_gray_concrete')
    F.cur = 'bracing'
    for y in range(36, TOP, 36):
        for i in range(8):
            (xa, za), (xb, zb) = legs[i], legs[(i + 1) % 8]
            shapes.line(F, (xa, y, za), (xb, y, zb), 'light_gray_concrete')
            shapes.line(F, (xa, y + 1, za), (xb, y + 1, zb), 'light_gray_concrete')
            shapes.line(F, (xa, y, za), (0, y, 0), 'gray_concrete')
            shapes.line(F, (xa, y - 36, za), (xb, y, zb), 'iron_bars')
    F.cur = 'shaft'
    shapes.cylinder(F, (0, 0, 0), 4, TOP, 'light_gray_concrete', hollow=True)
    F.fill((0, 0, -5), (0, TOP - 1, -5), 'ladder[facing=north]')
    F.cur = 'tank'
    shapes.disc(F, (0, TOP, 0), R + 6, 'smooth_stone_slab[type=top]')
    shapes.ring(F, (0, TOP + 1, 0), R + 6, 'iron_bars')
    shapes.cylinder(F, (0, TOP + 1, 0), R + 4, TH, 'white_concrete', hollow=True, thickness=2)
    for k in range(4):
        shapes.ring(F, (0, TOP + 6 + 13 * k, 0), R + 5, 'gray_concrete')
    shapes.disc(F, (0, TOP + TH, 0), R + 4, 'light_gray_concrete')
    for k in range(1, 12):
        shapes.disc(F, (0, TOP + TH + k, 0), max(1, round((R + 4) * math.sqrt(1 - (k / 12) ** 2))), 'light_gray_concrete')
    F.fill((-1, TOP + TH + 12, -1), (1, TOP + TH + 14, 1), 'red_concrete')
    for (x, y, z) in ((0, TOP + TH + 15, 0), (R + 4, TOP + TH, 0), (-R - 4, TOP + TH, 0), (0, TOP + TH, R + 4), (0, TOP + TH, -R - 4)):
        F.put(x, y, z, 'shroomlight')
    return {}


def twilight_grove(F, W=192, D=192, seed=19):
    """暮色树林: a dim wood of dark oaks and birches with glow lichen on the
    trunks, mossy ground, ferns and mushrooms, a winding lantern-lit path and
    a stone clearing - a small nod to the Twilight Forest."""
    rng = random.Random(seed)
    noise = fbm(seed)
    F.cur = 'ground'
    for x in range(W):
        for z in range(D):
            n = noise(x / 14, z / 14)
            F.put(x, -1, z, 'moss_block' if n > 0.15 else ('podzol' if n < -0.25 else 'grass_block'))
    # winding path through the wood, lamps along it
    F.cur = 'path'
    pts = [(0, D // 2)]
    for k in range(1, 9):
        pts.append((k * W // 8, D // 2 + round(40 * math.sin(k * 1.3 + seed))))
    path_cells = set()
    for (xa, za), (xb, zb) in zip(pts, pts[1:]):
        n = max(abs(xb - xa), abs(zb - za))
        for i in range(n + 1):
            x = round(xa + (xb - xa) * i / n); z = round(za + (zb - za) * i / n)
            for a in range(-1, 2):
                for b in range(-1, 2):
                    if 0 <= x + a < W and 0 <= z + b < D:
                        F.put(x + a, -1, z + b, rng.choice(['mossy_cobblestone', 'cobblestone', 'moss_block', 'coarse_dirt']))
                        path_cells.add((x + a, z + b))
    for (x, z) in pts[1:-1]:
        lamp(F, x + 3, z)
    # clearing with a ring of stones and benches
    F.cur = 'clearing'
    cx, cz = W // 2, D // 2 - 30
    for x in range(cx - 12, cx + 13):
        for z in range(cz - 12, cz + 13):
            d = math.hypot(x - cx, z - cz)
            if d < 11:
                F.put(x, -1, z, 'mossy_stone_bricks' if d > 9 else 'grass_block')
                path_cells.add((x, z))
    for k in range(8):
        a = k / 8 * 2 * math.pi
        sx, sz = round(cx + 9 * math.cos(a)), round(cz + 9 * math.sin(a))
        F.fill((sx, 0, sz), (sx, 1 + k % 2, sz), 'mossy_stone_bricks')
        F.put(sx, 2 + k % 2, sz, 'lantern')
    bench(F, cx - 1, cz + 4, 'south'); bench(F, cx - 1, cz - 4, 'north')
    # the wood
    F.cur = 'trees'
    trunks = []
    for _ in range(150):
        x, z = rng.randint(4, W - 5), rng.randint(4, D - 5)
        if any(abs(x - a) < 2 and abs(z - b) < 2 for a, b in path_cells) or any(abs(x - a) + abs(z - b) < 7 for a, b in trunks):
            continue
        trunks.append((x, z))
        broadleaf(F, x, z, rng, 'dark' if rng.random() < 0.6 else 'birch')
        for face, (dx, dz) in (('south', (0, -1)), ('north', (0, 1)), ('east', (-1, 0)), ('west', (1, 0))):
            for y in range(0, 4):
                if rng.random() < 0.35 and F.get(x + dx, y, z + dz) is None:
                    F.put(x + dx, y, z + dz, f'glow_lichen[{face}=true]')
    F.cur = 'undergrowth'
    for _ in range(900):
        x, z = rng.randint(1, W - 2), rng.randint(1, D - 2)
        if (x, z) in path_cells or F.get(x, 0, z) is not None:
            continue
        k = rng.random()
        if k < 0.5:
            F.put(x, 0, z, 'fern')
        elif k < 0.7:
            F.put(x, 0, z, 'moss_carpet')
        elif k < 0.8:
            F.tall(x, 0, z, 'large_fern')
        elif k < 0.9:
            F.put(x, 0, z, 'brown_mushroom' if F.at(x, -1, z).short in ('podzol', 'moss_block') else 'fern')
        else:
            F.put(x, 0, z, 'azalea')
    return {'walk_start': (1, 0, D // 2), 'walk_targets': {'clearing': (cx, 0, cz)}}


DESIGNS = {
    # name: (function, site box margin/size, title)
    'lake_garden': (lake_garden, (200, 220), '校园湖'),
    'sports_park': (sports_park, (200, 220), '游泳池与运动场'),
    'auditorium': (auditorium, (200, 220), '大礼堂'),
    'greenhouse': (greenhouse, (200, 220), '植物园温室'),
    'walkway': (walkway, (5, 180), '风雨连廊'),
    'fountain': (fountain, (29, 29), '喷泉'),
    'bus_stop': (bus_stop, (10, 4), '公交站'),
    'bus_lot': (bus_lot, (300, 80), '校车停车场'),
    'car_park': (car_park, (300, 80), '停车场'),
    'water_tower': (water_tower, (0, 0), '巨型水塔'),
    'twilight_grove': (twilight_grove, (192, 192), '暮色树林'),
}
