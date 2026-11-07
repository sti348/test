"""School buildings for the new map regions, designed with minecraft-build-design
(mcbuild): the sea academy and lighthouse of the archipelago, the glass-sphere
schools on the sea floor, the tower and cliff schools of the giant sinkhole, the
academies on the sky islands (the top one End-style) and the Nether school with
the giant Nether portal (one half per dimension).

Same conventions as mcbuild_designs.py: local (0, 0, 0) is the first air block
above the design's own ground (local y = -1).  `cave_air` is used where a design
must carve water or rock (the glass spheres): it is air in game but survives
the export so the generator can paste it over the sea."""
from __future__ import annotations

import math
import random

from mcbuild import shapes, nature, AIR

from mcbuild_designs import lamp, broadleaf

CARVE = "cave_air"


def step_up(F, x, y, z, facing, width=1):
    """A stair block in front of a raised doorway (walkers climb half blocks)."""
    dx, dz = (1, 0) if facing in ('north', 'south') else (0, 1)
    for k in range(-(width // 2), width // 2 + 1):
        F.put(x + dx * k, y, z + dz * k, f'stone_brick_stairs[facing={facing}]')


def stepped_plinth(F, rects, mats):
    """Stacked rectangles, one block per level, edged with stairs facing inward."""
    for k, ((xa, za, xb, zb), mat) in enumerate(zip(rects, mats)):
        F.fill((xa, k, za), (xb, k, zb), mat)
        for x in range(xa, xb + 1):
            F.put(x, k, za, 'polished_blackstone_brick_stairs[facing=south]')
            F.put(x, k, zb, 'polished_blackstone_brick_stairs[facing=north]')
        for z in range(za + 1, zb):
            F.put(xa, k, z, 'polished_blackstone_brick_stairs[facing=east]')
            F.put(xb, k, z, 'polished_blackstone_brick_stairs[facing=west]')


def _ring_windows(F, cx, cz, r, y0, y1, step, glass, every=4):
    """Window slots around a cylinder wall of radius r."""
    for y in range(y0, y1, step):
        for k in range(int(2 * math.pi * r / every)):
            a = k * every / r
            x, z = round(cx + r * math.cos(a)), round(cz + r * math.sin(a))
            F.fill((x, y, z), (x, y + 1, z), glass)


# ------------------------------------------------------------------ archipelago
def sea_academy(F, W=160, D=160, seed=31):
    """海上学院: white-and-blue courtyard school on the main island - a domed
    great hall, four arcaded wings, a fountain court, palms and lamps."""
    rng = random.Random(seed)
    F.cur = 'ground'
    F.fill((0, -1, 0), (W - 1, -1, D - 1), 'smooth_sandstone')
    cx, cz = W // 2, D // 2
    wall, trim, roof = 'white_concrete', 'smooth_quartz', 'blue_terracotta'
    # four wings around the court, arcade on the court side
    F.cur = 'wings'
    for (x0, z0, x1, z1) in ((20, 20, W - 21, 40), (20, D - 41, W - 21, D - 21), (20, 41, 40, D - 42), (W - 41, 41, W - 21, D - 42)):
        F.fill((x0, 0, z0), (x1, 24, z1), wall)
        F.fill((x0 + 1, 0, z0 + 1), (x1 - 1, 23, z1 - 1), AIR)
        for y in range(-1, 24, 5):
            if y > 0:
                shapes.walls(F, (x0, y, z0), (x1, y, z1), trim)
            F.fill((x0 + 1, y, z0 + 1), (x1 - 1, y, z1 - 1), 'birch_planks')
        for y in range(2, 24, 5):
            for x in range(x0 + 2, x1 - 1, 4):
                for z in (z0, z1):
                    F.fill((x, y, z), (x + 1, y + 1, z), 'light_blue_stained_glass_pane')
            for z in range(z0 + 2, z1 - 1, 4):
                for x in (x0, x1):
                    F.fill((x, y, z), (x, y + 1, z + 1), 'light_blue_stained_glass_pane')
        for y in range(4, 24, 5):
            for x in range(x0 + 3, x1 - 2, 8):
                for z in range(z0 + 3, z1 - 2, 8):
                    F.put(x, y, z, 'sea_lantern')
        shapes.flat_roof(F, x0, z0, x1, z1, 25, roof, rim=trim, overhang=1)
        F.fill((x0, 0, z0 + (z1 - z0) // 2), (x0, 2, z0 + (z1 - z0) // 2), AIR)
    # doors from the court into the wings
    for (x, z, f) in ((cx, 40, 'north'), (cx, D - 41, 'south'), (40, cz, 'west'), (W - 41, cz, 'east')):
        F.door(x, 0, z, f, wood='birch')
    # domed great hall in the middle of the court
    F.cur = 'hall'
    shapes.cylinder(F, (cx, 0, cz), 18, 22, wall, hollow=True, thickness=2)
    F.fill((cx - 17, 0, cz - 17), (cx + 17, 0, cz + 17), AIR)
    shapes.disc(F, (cx, -1, cz), 16, 'smooth_quartz')
    _ring_windows(F, cx, cz, 18, 4, 20, 7, 'light_blue_stained_glass', every=5)
    for k in range(1, 18):
        r = round(18 * math.sqrt(1 - (k / 18) ** 2))
        if r <= 3:
            shapes.disc(F, (cx, 21 + k, cz), max(1, r), roof)
        else:
            shapes.ring(F, (cx, 21 + k, cz), r, roof)
            shapes.ring(F, (cx, 21 + k, cz), r - 1, roof)
    F.fill((cx, 39, cz), (cx, 43, cz), 'gold_block')
    for k in range(8):
        a = k * math.pi / 4
        lamp(F, round(cx + 9 * math.cos(a)), round(cz + 9 * math.sin(a)))
    F.fill((cx - 1, 0, cz + 17), (cx + 1, 2, cz + 19), AIR)
    # fountain, palms, lamps, benches in the court
    F.cur = 'court'
    for (fx, fz) in ((cx, cz + 26), (cx, cz - 26)):
        shapes.disc(F, (fx, -1, fz), 5, 'water'); shapes.ring(F, (fx, 0, fz), 5, 'smooth_quartz_slab[type=bottom]')
        F.put(fx, 0, fz, 'sea_lantern')
    for (px, pz) in ((50, 50), (W - 51, 50), (50, D - 51), (W - 51, D - 51)):
        F.put(px, -1, pz, 'grass_block')
        nature.palm(F, px, pz, rng.randint(8, 11), lean=(rng.choice((-1, 1)), 0))
    for k in range(8):
        a = k * math.pi / 4 + math.pi / 8
        lamp(F, round(cx + 28 * math.cos(a)), round(cz + 28 * math.sin(a)))
    # outside: palms and lamps along the wall
    for x in range(10, W - 9, 20):
        for z in (8, D - 9):
            F.put(x, -1, z, 'grass_block')
            nature.palm(F, x, z, rng.randint(7, 10), lean=(0, rng.choice((-1, 1))))
            lamp(F, x + 10, z)
    return {'walk_start': (cx, 0, 2), 'walk_targets': {'court': (cx + 6, 0, cz + 24), 'hall': (cx + 4, 0, cz + 4)}}


def lighthouse_school(F, H=480, seed=37):
    """灯塔教学楼: a 480-block lighthouse with classrooms - red and white bands,
    a gallery every 40 blocks, a spiral stair all the way up, the lamp room on top."""
    R = 18
    c = R + 8
    F.cur = 'base'
    F.fill((0, -1, 0), (2 * c, -1, 2 * c), 'smooth_stone')
    shapes.disc(F, (c, 0, c), R + 6, 'polished_andesite')
    F.cur = 'tower'
    for y in range(1, H):
        mat = 'red_concrete' if (y // 40) % 2 else 'white_concrete'
        shapes.ring(F, (c, y, c), R, mat)
        shapes.ring(F, (c, y, c), R - 1, mat)
    _ring_windows(F, c, c, R, 6, H - 10, 10, 'glass_pane', every=6)
    for y in range(40, H, 40):                              # floors + gallery rings with railings
        shapes.disc(F, (c, y, c), R - 2, 'smooth_quartz')
        shapes.ring(F, (c, y, c), R + 2, 'smooth_quartz_slab[type=top]')
        shapes.ring(F, (c, y, c), R + 1, 'smooth_quartz_slab[type=top]')
        shapes.ring(F, (c, y + 1, c), R + 2, 'iron_bars')
        for k in range(6):
            a = k * math.pi / 3
            F.put(round(c + (R - 4) * math.cos(a)), y - 1, round(c + (R - 4) * math.sin(a)), 'sea_lantern')
    # ladder shaft on the inner north wall, a hole through every floor
    F.cur = 'ladder'
    F.fill((c, 1, c - R + 2), (c, H - 1, c - R + 2), 'ladder[facing=south]')
    for y in range(40, H, 40):
        F.put(c, y, c - R + 2, 'ladder[facing=south]')
    F.cur = 'door'
    F.fill((c - 1, 1, c + R - 1), (c + 1, 3, c + R), AIR)
    # lamp room
    F.cur = 'lantern'
    shapes.disc(F, (c, H, c), R + 3, 'smooth_quartz')
    shapes.ring(F, (c, H + 1, c), R + 3, 'iron_bars')
    shapes.cylinder(F, (c, H + 1, c), R - 6, 14, 'yellow_stained_glass', hollow=True)
    shapes.cylinder(F, (c, H + 1, c), 4, 12, 'sea_lantern')
    for k in range(1, 9):
        shapes.ring(F, (c, H + 14 + k, c), max(1, R - 6 - 2 * k), 'red_concrete' if k < 8 else 'gold_block')
    return {}


def island_classroom(F, seed=41):
    """小岛教室: a timber classroom on stilts with a deck and a jetty."""
    F.cur = 'stilts'
    for x in range(0, 31, 6):
        for z in range(0, 21, 5):
            F.fill((x, -6, z), (x, 2, z), 'stripped_spruce_log[axis=y]')
    F.fill((-2, 3, -2), (32, 3, 22), 'spruce_planks')
    F.cur = 'house'
    F.fill((2, 4, 2), (28, 9, 18), 'white_terracotta')
    F.fill((3, 4, 3), (27, 8, 17), AIR)
    for x in range(4, 27, 4):
        F.fill((x, 6, 2), (x + 1, 7, 2), 'glass_pane'); F.fill((x, 6, 18), (x + 1, 7, 18), 'glass_pane')
    F.door(15, 4, 18, 'north', wood='spruce')
    for x in range(5, 26, 5):
        F.hanging_lantern(x, 8, 10, chain=0)
        for z in (6, 10, 14):
            F.put(x, 4, z, 'spruce_stairs[facing=north]')
    shapes.gable_roof(F, 2, 2, 28, 18, 10, 'dark_prismarine_stairs', ridge='x', overhang=1, gable='white_terracotta')
    F.cur = 'deck'
    for x in range(-2, 33):
        F.put(x, 4, -2, 'spruce_fence')
        if not 13 <= x <= 17:
            F.put(x, 4, 22, 'spruce_fence')
    lamp(F, -2, 22, y=4); lamp(F, 32, 22, y=4)
    F.fill((14, 3, 23), (16, 3, 50), 'spruce_slab[type=top]')
    for z in range(25, 51, 5):
        F.fill((14, -6, z), (14, 2, z), 'stripped_spruce_log[axis=y]'); F.fill((16, -6, z), (16, 2, z), 'stripped_spruce_log[axis=y]')
    return {}


# ------------------------------------------------------------------ undersea glass spheres
def dome_school(F, R=130, seed=43):
    """海底玻璃球学校: a glass sphere on the sea floor (centre R above the
    design's base), air inside (cave_air carves the sea), a grassy disc floor
    with a ring of lit school buildings, gardens and a central tower up to the
    top of the dome.  Local (0,0,0) = the sphere's lowest point."""
    rng = random.Random(seed)
    c, cy = R, R
    fy = int(R * 0.45)                                   # floor level inside
    fr = int(math.sqrt(R * R - (cy - fy) ** 2)) - 3      # floor radius
    F.cur = 'shell'
    R2o, R2i = R * R, (R - 2.5) ** 2
    for y in range(0, 2 * R + 1):
        dy = y - cy
        rr = R2o - dy * dy
        if rr < 0:
            continue
        ro = math.sqrt(rr)
        ri = math.sqrt(max(0.0, R2i - dy * dy)) if R2i - dy * dy > 0 else -1
        n = int(ro) + 1
        for dx in range(-n, n + 1):
            for dz in range(-n, n + 1):
                d2 = dx * dx + dz * dz
                if d2 <= rr:
                    if ri < 0 or d2 > ri * ri:
                        rib = (abs(dx) < 1 or abs(dz) < 1 or abs(dy) < 1 or abs(abs(dx) - abs(dz)) < 1)
                        F.put(c + dx, y, c + dz, 'white_concrete' if rib else 'glass')
                    elif y > fy:
                        F.put(c + dx, y, c + dz, CARVE)
    # floor: a slab of earth with grass, an inner ring road
    F.cur = 'floor'
    for y in range(fy - 6, fy + 1):
        rr = int(math.sqrt(max(0, R2i - (y - cy) ** 2)))
        shapes.disc(F, (c, y, c), rr, 'dirt' if y < fy else 'grass_block')
    shapes.ring(F, (c, fy, c), int(fr * 0.55), 'smooth_stone', thickness=4)
    shapes.disc(F, (c, fy, c), 14, 'smooth_quartz')
    # central tower to the top of the dome
    F.cur = 'tower'
    th = 2 * R - fy - 8
    for y in range(fy + 1, fy + th):
        shapes.ring(F, (c, y, c), 7, 'white_concrete' if (y - fy) % 12 else 'light_blue_concrete')
    _ring_windows(F, c, c, 7, fy + 4, fy + th - 4, 6, 'light_blue_stained_glass', every=3)
    for y in range(fy + 6, fy + th, 12):
        shapes.disc(F, (c, y, c), 6, 'sea_lantern')
    F.fill((c - 1, fy + 1, c + 7), (c + 1, fy + 3, c + 7), CARVE)
    # ring of school buildings around the road
    F.cur = 'schools'
    nb = max(5, int(2 * math.pi * fr * 0.75 / 34))
    for k in range(nb):
        a = 2 * math.pi * k / nb
        bx, bz = round(c + fr * 0.75 * math.cos(a)), round(c + fr * 0.75 * math.sin(a))
        h = rng.choice((10, 15, 20))
        F.fill((bx - 8, fy + 1, bz - 6), (bx + 8, fy + h, bz + 6), 'white_concrete')
        F.fill((bx - 7, fy + 1, bz - 5), (bx + 7, fy + h - 1, bz + 5), CARVE)
        for y in range(fy + 3, fy + h - 1, 5):
            for x in range(bx - 6, bx + 7, 3):
                F.put(x, y, bz - 6, 'light_blue_stained_glass'); F.put(x, y, bz + 6, 'light_blue_stained_glass')
            F.fill((bx - 7, y + 2, bz - 5), (bx + 7, y + 2, bz + 5), 'smooth_stone')
            F.put(bx, y + 1, bz, 'sea_lantern')
        F.fill((bx - 9, fy + h + 1, bz - 7), (bx + 9, fy + h + 1, bz + 7), 'cyan_terracotta')
        F.fill((bx - 1, fy + 1, bz - 6), (bx, fy + 2, bz - 6), CARVE)
    # gardens and lamps
    F.cur = 'garden'
    for k in range(int(fr / 2)):
        a = rng.uniform(0, 2 * math.pi); r = rng.uniform(18, fr * 0.5)
        tx, tz = round(c + r * math.cos(a)), round(c + r * math.sin(a))
        if F.get(tx, fy, tz) is not None and F.get(tx, fy, tz).short == 'grass_block':
            h = rng.randint(5, 7)
            F.fill((tx, fy + 1, tz), (tx, fy + h, tz), 'cherry_log[axis=y]' if k % 3 == 0 else 'oak_log[axis=y]')
            leaf = 'cherry_leaves[persistent=true]' if k % 3 == 0 else 'oak_leaves[persistent=true]'
            for dx in range(-3, 4):
                for dy in range(-1, 3):
                    for dz in range(-3, 4):
                        if dx * dx + (dy * 1.4) ** 2 + dz * dz <= 9 and not (dx == 0 and dz == 0 and dy < 1):
                            F.put(tx + dx, fy + h + dy, tz + dz, leaf)
    for k in range(int(2 * math.pi * fr * 0.55 / 12)):
        a = k * 12 / (fr * 0.55)
        lamp(F, round(c + (fr * 0.55 + 3) * math.cos(a)), round(c + (fr * 0.55 + 3) * math.sin(a)), y=fy + 1)
    return {}


# ------------------------------------------------------------------ sinkhole
def pit_tower(F, H=1100, seed=47):
    """天坑中央塔楼: a square school tower 64 wide rising from the pit floor to
    above the rim - setback crowns every 100 blocks, lit galleries, a stair core."""
    W = 64
    F.cur = 'base'
    F.fill((-6, -1, -6), (W + 5, -1, W + 5), 'polished_deepslate')
    F.cur = 'tower'
    wall = ['light_gray_concrete', 'white_concrete', 'light_gray_concrete', 'smooth_stone']
    for y in range(0, H):
        mat = wall[(y // 25) % len(wall)]
        lvl = y % 100
        if lvl < 2:
            mat = 'polished_deepslate'
        shapes.walls(F, (0, y, 0), (W - 1, y, W - 1), mat)
        if y % 5 in (2, 3) and lvl > 4:
            for k in range(3, W - 3, 4):
                for (x, z) in ((k, 0), (k, W - 1), (0, k), (W - 1, k)):
                    F.put(x, y, z, 'gray_stained_glass_pane')
    for y in range(5, H, 5):
        F.fill((1, y, 1), (W - 2, y, W - 2), 'smooth_stone')
        if y % 25 == 0:
            for (x, z) in ((16, 16), (47, 16), (16, 47), (47, 47)):
                F.put(x, y - 1, z, 'ochre_froglight')
    for y in range(100, H, 100):                         # galleries: a ring balcony with lamps
        F.fill((-4, y, -4), (W + 3, y, W + 3), 'polished_deepslate')
        shapes.walls(F, (-4, y + 1, -4), (W + 3, y + 1, W + 3), 'polished_deepslate_wall')
        for k in range(-4, W + 4, 12):
            for (x, z) in ((k, -4), (k, W + 3), (-4, k), (W + 3, k)):
                F.put(x, y + 2, z, 'lantern')
    # ladder shaft against the inner north wall, through every floor
    F.cur = 'ladder'
    F.fill((33, 1, 1), (33, H - 1, 1), 'ladder[facing=south]')
    F.fill((27, 1, 0), (30, 4, 0), AIR)
    F.cur = 'crown'
    shapes.flat_roof(F, 0, 0, W - 1, W - 1, H, 'polished_deepslate', rim='polished_deepslate_wall', overhang=2)
    F.fill((24, H + 1, 24), (39, H + 20, 39), 'light_gray_concrete')
    F.fill((30, H + 21, 30), (33, H + 40, 33), 'polished_deepslate')
    F.put(31, H + 41, 31, 'shroomlight')
    return {}


def cliff_school(F, seed=53):
    """崖壁教学楼: a stepped classroom block for the sinkhole ledges - three
    terraces back into the cliff, a lit arcade on every level, rooftop garden."""
    F.cur = 'ground'
    F.fill((0, -1, 0), (35, -1, 27), 'stone_bricks')
    F.cur = 'block'
    for k, (z1, h) in enumerate(((27, 8), (18, 16), (9, 24))):
        F.fill((0, 0, 0), (35, h, z1), 'white_concrete')
        F.fill((1, h - 8 + 1 if h > 8 else 1, 1), (34, h - 1, z1 - 1), AIR)
        for x in range(2, 34, 4):
            F.fill((x, h - 6, z1), (x + 1, h - 4, z1), 'glass_pane')
        F.fill((0, h, 0), (35, h, z1), 'smooth_stone_slab[type=bottom]' if k == 2 else 'moss_block')
        for x in range(3, 34, 8):
            F.put(x, h - 1, z1 - 2, 'ochre_froglight')
    F.door(17, 1, 27, 'north', wood='dark_oak')
    lamp(F, 1, 27 + 1); lamp(F, 34, 27 + 1)
    for x in range(2, 34, 6):
        F.put(x, 9, 24, 'azalea'); F.put(x + 3, 17, 15, 'flowering_azalea')
    return {}


# ------------------------------------------------------------------ sky islands
def sky_academy(F, W=120, D=120, style='white', seed=59):
    """空岛学院: a hilltop academy for the sky islands - a tall central keep with
    a spire, two arcaded halls, a cloister garden; palette per island."""
    rng = random.Random(seed)
    pal = {
        'white': ('smooth_quartz', 'quartz_pillar[axis=y]', 'deepslate_tile_stairs', 'cyan_stained_glass_pane'),
        'sand': ('smooth_sandstone', 'cut_sandstone', 'dark_oak_stairs', 'orange_stained_glass_pane'),
        'stone': ('stone_bricks', 'polished_andesite', 'deepslate_tile_stairs', 'light_blue_stained_glass_pane'),
        'brick': ('bricks', 'smooth_quartz', 'dark_prismarine_stairs', 'white_stained_glass_pane'),
    }[style]
    wall, trim, roof, glass = pal
    F.cur = 'ground'
    F.fill((0, -1, 0), (W - 1, -1, D - 1), 'grass_block')
    cx, cz = W // 2, D // 2
    F.cur = 'halls'
    for (x0, z0, x1, z1) in ((10, 14, W - 11, 34), (10, D - 35, W - 11, D - 15)):
        F.fill((x0, 0, z0), (x1, 17, z1), wall)
        F.fill((x0 + 1, 0, z0 + 1), (x1 - 1, 16, z1 - 1), AIR)
        F.fill((x0 + 1, 0, z0 + 1), (x1 - 1, 0, z1 - 1), 'polished_andesite')
        for x in range(x0, x1 + 1, 5):
            F.fill((x, 0, z0 - 1), (x, 16, z0 - 1), trim); F.fill((x, 0, z1 + 1), (x, 16, z1 + 1), trim)
        for x in range(x0 + 2, x1 - 1, 5):
            for z in (z0, z1):
                F.fill((x, 3, z), (x + 1, 13, z), glass)
        for x in range(x0 + 4, x1 - 2, 8):
            F.hanging_lantern(x, 16, (z0 + z1) // 2, chain=2)
        shapes.gable_roof(F, x0, z0, x1, z1, 18, roof, ridge='x', overhang=2, gable=wall)
        dz_ = z1 if z0 < cz else z0
        F.door(cx, 1, dz_, 'north' if z0 < cz else 'south', wood='dark_oak')
        step_up(F, cx, 0, dz_ + (1 if z0 < cz else -1), 'north' if z0 < cz else 'south')
    # central keep with a spire
    F.cur = 'keep'
    k0, k1 = cx - 11, cx + 11
    F.fill((k0, 0, k0 + (cz - cx)), (k1, 60, k1 + (cz - cx)), wall)
    F.fill((k0 + 1, 1, k0 + 1 + (cz - cx)), (k1 - 1, 59, k1 - 1 + (cz - cx)), AIR)
    for y in range(6, 58, 8):
        for k in range(k0 + 3, k1 - 2, 4):
            for (x, z) in ((k, k0), (k, k1), (k0, k), (k1, k)):
                F.fill((x, y, z + (cz - cx)), (x, y + 3, z + (cz - cx)), glass)
        F.fill((k0 + 1, y - 1, k0 + 1 + (cz - cx)), (k1 - 1, y - 1, k1 - 1 + (cz - cx)), 'polished_andesite')
        F.put(cx, y + 2, cz, 'ochre_froglight')
    shapes.walls(F, (k0 - 1, 61, k0 - 1 + (cz - cx)), (k1 + 1, 62, k1 + 1 + (cz - cx)), trim)
    shapes.pyramid_roof(F, k0, k0 + (cz - cx), k1, k1 + (cz - cx), 61, roof, overhang=1, fill=wall)
    F.fill((cx, 73, cz), (cx, 80, cz), 'lightning_rod')
    F.door(cx, 1, k1 + (cz - cx), 'north', wood='dark_oak')
    step_up(F, cx, 0, k1 + (cz - cx) + 1, 'north')
    # cloister garden, lamps, trees at the edge
    F.cur = 'garden'
    for x in range(14, W - 14, 3):
        for z in (40, D - 41):
            if rng.random() < 0.5:
                F.put(x, 0, z, rng.choice(['poppy', 'cornflower', 'allium', 'azure_bluet', 'oxeye_daisy']))
    for k in range(0, W, 16):
        lamp(F, k + 4, 5); lamp(F, k + 4, D - 6)
        broadleaf(F, k + 10, 2, rng, 'birch' if style == 'white' else 'oak')
        broadleaf(F, k + 10, D - 3, rng, 'birch' if style == 'white' else 'oak')
    return {'walk_start': (cx, 0, 2), 'walk_targets': {'keep': (cx - 4, 1, cz + 4)}}


def end_academy(F, W=140, D=140, seed=61):
    """末地学院: purpur and end-stone academy on the highest island - towers
    with purple glass, end-rod lights, obsidian pillars, chorus gardens."""
    rng = random.Random(seed)
    F.cur = 'ground'
    F.fill((0, -1, 0), (W - 1, -1, D - 1), 'end_stone')
    cx, cz = W // 2, D // 2
    F.cur = 'plaza'
    shapes.disc(F, (cx, -1, cz), 30, 'purpur_block')
    shapes.ring(F, (cx, -1, cz), 30, 'end_stone_bricks', thickness=2)
    F.cur = 'towers'
    for k in range(6):
        a = k * math.pi / 3
        tx, tz = round(cx + 46 * math.cos(a)), round(cz + 46 * math.sin(a))
        h = 50 + 10 * (k % 3)
        F.fill((tx - 5, 0, tz - 5), (tx + 5, h, tz + 5), 'purpur_block')
        F.fill((tx - 4, 0, tz - 4), (tx + 4, h - 1, tz + 4), AIR)
        for y in range(4, h - 2, 6):
            for (dx, dz) in ((0, -5), (0, 5), (-5, 0), (5, 0)):
                F.fill((tx + dx, y, tz + dz), (tx + dx, y + 3, tz + dz), 'magenta_stained_glass')
            F.fill((tx - 4, y - 1, tz - 4), (tx + 4, y - 1, tz + 4), 'end_stone_bricks')
            F.put(tx, y, tz, 'end_rod')
        shapes.pyramid_roof(F, tx - 5, tz - 5, tx + 5, tz + 5, h + 1, 'purpur_stairs', overhang=1, fill='purpur_block')
        F.fill((tx, h + 8, tz), (tx, h + 14, tz), 'end_rod')
        F.fill((tx - 1, 0, tz + 5 if tz < cz else tz - 5), (tx + 1, 2, tz + 5 if tz < cz else tz - 5), AIR)
    F.cur = 'hall'
    F.fill((cx - 16, 0, cz - 16), (cx + 16, 30, cz + 16), 'end_stone_bricks')
    F.fill((cx - 15, 0, cz - 15), (cx + 15, 29, cz + 15), AIR)
    for y in range(4, 28, 6):
        for k in range(cx - 13, cx + 14, 4):
            for (x, z) in ((k, cz - 16), (k, cz + 16), (cx - 16, k), (cx + 16, k)):
                F.fill((x, y, z), (x, y + 3, z), 'purple_stained_glass')
    for x in range(cx - 12, cx + 13, 6):
        for z in range(cz - 12, cz + 13, 6):
            F.fill((x, 20, z), (x, 29, z), 'end_rod')
    shapes.pyramid_roof(F, cx - 16, cz - 16, cx + 16, cz + 16, 31, 'purpur_stairs', overhang=2, fill='purpur_block')
    F.fill((cx - 1, 0, cz + 16), (cx + 1, 2, cz + 16), AIR)
    F.cur = 'pillars'
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        px, pz = round(cx + 62 * math.cos(a)), round(cz + 62 * math.sin(a))
        shapes.cylinder(F, (px, 0, pz), 3, 40 + 8 * k, 'obsidian')
        F.put(px, 40 + 8 * k, pz, 'crying_obsidian'); F.put(px, 41 + 8 * k, pz, 'end_rod')
    F.cur = 'chorus'
    for _ in range(40):
        x, z = rng.randint(6, W - 7), rng.randint(6, D - 7)
        if F.get(x, -1, z) is None or F.get(x, -1, z).short != 'end_stone' or F.get(x, 0, z) is not None:
            continue
        h = rng.randint(3, 7)
        for y in range(h):
            F.put(x, y, z, 'chorus_plant')
        F.put(x, h, z, 'chorus_flower')
    return {'walk_start': (cx, 0, 4), 'walk_targets': {'hall': (cx + 4, 0, cz + 4)}}


# ------------------------------------------------------------------ Nether
def infernal_academy(F, W=200, D=200, seed=67):
    """地狱学院: a blackstone ziggurat school on a basalt plinth ringed by a lava
    moat - four stepped tiers of lit nether-brick classrooms, gilded trim, soul
    lanterns, a great stair to a crimson-and-warped crown."""
    cx, cz = W // 2, D // 2
    F.cur = 'ground'
    F.fill((0, -1, 0), (W - 1, -1, D - 1), 'blackstone')
    F.cur = 'moat'
    for x in range(W):
        for z in range(D):
            d = max(abs(x - cx), abs(z - cz))
            if 84 <= d <= 92:
                F.put(x, -1, z, 'lava'); F.put(x, -2, z, 'magma_block')
            elif d == 83 or d == 93:
                F.put(x, -1, z, 'polished_blackstone_bricks')
    F.fill((cx - 3, -1, cz + 83), (cx + 3, -1, cz + 93), 'polished_blackstone_bricks')
    F.cur = 'ziggurat'
    tiers = [(78, 18), (62, 18), (46, 18), (30, 18)]
    y = 0
    for k, (r, h) in enumerate(tiers):
        mat = 'nether_bricks' if k % 2 == 0 else 'red_nether_bricks'
        F.fill((cx - r, y, cz - r), (cx + r, y + h - 1, cz + r), mat)
        F.fill((cx - r + 1, y, cz - r + 1), (cx + r - 1, y + h - 2, cz + r - 1), AIR)
        for yy in range(y + 3, y + h - 2, 6):
            for j in range(-r + 3, r - 2, 5):
                for (x, z) in ((cx + j, cz - r), (cx + j, cz + r), (cx - r, cz + j), (cx + r, cz + j)):
                    F.fill((x, yy, z), (x, yy + 2, z), 'orange_stained_glass_pane')
            F.fill((cx - r + 1, yy - 1, cz - r + 1), (cx + r - 1, yy - 1, cz + r - 1), 'polished_blackstone')
            for j in range(-r + 6, r - 5, 12):
                for i in range(-r + 6, r - 5, 12):
                    if yy + 5 < y + h - 1:
                        F.put(cx + j, yy + 4, cz + i, 'shroomlight')     # under the floor above
        F.fill((cx - r, y + h - 1, cz - r), (cx + r, y + h - 1, cz + r), 'polished_blackstone')
        shapes.walls(F, (cx - r, y + h - 1, cz - r), (cx + r, y + h - 1, cz + r), 'gilded_blackstone')
        shapes.walls(F, (cx - r, y + h, cz - r), (cx + r, y + h, cz + r), 'polished_blackstone_brick_wall')
        for j in range(-r, r + 1, 10):
            for (x, z) in ((cx + j, cz - r), (cx + j, cz + r), (cx - r, cz + j), (cx + r, cz + j)):
                if not (z == cz + r and abs(j) <= 6):           # the grand stair cuts through here
                    F.put(x, y + h + 1, z, 'soul_lantern')
        y += h
    # great stair up the south face to the top
    F.cur = 'stair'
    for i in range(y):                                   # one step per block, cut into the tiers
        z = cz + 96 - i
        F.fill((cx - 4, i, z), (cx + 4, i, z), 'polished_blackstone_brick_stairs[facing=north]')
        if i:
            F.fill((cx - 4, 0, z), (cx + 4, i - 1, z), 'polished_blackstone_bricks')
        F.fill((cx - 4, i + 1, z), (cx + 4, i + 4, z), AIR)
        for x in (cx - 5, cx + 5):
            F.fill((x, 0, z), (x, i, z), 'polished_blackstone_bricks'); F.put(x, i + 1, z, 'polished_blackstone_brick_wall')
            if i % 8 == 0:
                F.put(x, i + 2, z, 'soul_lantern')
    F.cur = 'crown'
    F.fill((cx - 10, y, cz - 10), (cx + 10, y + 20, cz + 10), 'crimson_planks')
    F.fill((cx - 9, y, cz - 9), (cx + 9, y + 19, cz + 9), AIR)
    for yy in range(y + 3, y + 19, 5):
        for j in range(-8, 9, 4):
            for (x, z) in ((cx + j, cz - 10), (cx + j, cz + 10), (cx - 10, cz + j), (cx + 10, cz + j)):
                F.fill((x, yy, z), (x, yy + 2, z), 'red_stained_glass')
    shapes.pyramid_roof(F, cx - 10, cz - 10, cx + 10, cz + 10, y + 21, 'warped_stairs', overhang=2, fill='warped_planks')
    F.put(cx, y + 32, cz, 'shroomlight')
    F.fill((cx - 1, y, cz + 10), (cx + 1, y + 2, cz + 10), AIR)
    F.cur = 'braziers'
    for k in range(16):
        a = k * math.pi / 8
        bx, bz = round(cx + 96 * math.cos(a)), round(cz + 96 * math.sin(a))
        if 0 <= bx < W and 0 <= bz < D:
            F.put(bx, 0, bz, 'soul_soil'); F.put(bx, 1, bz, 'soul_fire')
            F.put(bx + 1, 0, bz, 'polished_blackstone_wall'); F.put(bx + 1, 1, bz, 'soul_lantern')
    return {'walk_start': (cx, 0, D - 1), 'walk_targets': {'crown': (cx + 3, y, cz + 3)}}


def nether_gate(F, iw=40, ih=70, nether=False, seed=71):
    """巨型地狱门: an obsidian frame 6 thick (1 at the threshold) around a
    40 x 70 Nether portal - axis z, so you walk through it along x - with
    crying-obsidian veins, a stepped blackstone plinth and soul-fire braziers.
    On the overworld side the ground around it is scorched into netherrack.
    Local x of the portal plane = PX; the portal spans z from PZ0."""
    rng = random.Random(seed)
    t, E = 6, 30                                         # frame thickness, plinth/scorch margin
    x0, z0 = E, E                                         # frame's west / north edge
    L = iw + 2 * t
    F.cur = 'plinth'
    F.fill((x0 - 18, -1, z0 - 18), (x0 + t + 17, -1, z0 + L + 17), 'blackstone')
    stepped_plinth(F, [(x0 - 12 + 3 * k, z0 - 12 + 3 * k, x0 + t + 11 - 3 * k, z0 + L + 11 - 3 * k) for k in range(3)],
                   ['polished_blackstone_bricks', 'blackstone', 'polished_blackstone_bricks'])
    base = 3
    F.cur = 'frame'
    for z in range(z0, z0 + L):
        for y in range(base, base + ih + t + 1):
            if t <= z - z0 < iw + t and base + 1 <= y < base + 1 + ih:
                continue
            for dx in range(t):
                vein = (z * 7 + y * 3 + dx) % 23 == 0
                F.put(x0 + dx, y, z, 'crying_obsidian' if vein else 'obsidian')
    F.cur = 'portal'
    px = x0 + t // 2
    F.fill((px, base + 1, z0 + t), (px, base + ih, z0 + t + iw - 1), 'nether_portal[axis=z]')
    for dx in range(t):
        if x0 + dx != px:
            F.fill((x0 + dx, base + 1, z0 + t), (x0 + dx, base + ih, z0 + t + iw - 1), AIR)
    F.fill((x0, base, z0 + t), (x0 + t - 1, base, z0 + t + iw - 1), 'obsidian')
    for z in range(z0 + t, z0 + t + iw):                 # a step up onto the threshold from both sides
        F.put(x0 - 1, base, z, 'polished_blackstone_brick_stairs[facing=east]')
        F.put(x0 + t, base, z, 'polished_blackstone_brick_stairs[facing=west]')
    F.cur = 'braziers'
    for z in (z0 - 6, z0 + L + 5):
        for xx in (x0 - 6, x0 + t + 5):
            F.fill((xx, 3, z), (xx, 5, z), 'polished_blackstone_wall')
            F.put(xx, 6, z, 'soul_soil'); F.put(xx, 7, z, 'soul_fire')
    if not nether:
        F.cur = 'scorch'
        for x in range(0, x0 + t + E):
            for z in range(0, z0 + L + E):
                if F.get(x, -1, z) is not None and F.get(x, -1, z).short != 'blackstone':
                    continue
                d = math.hypot(x - (x0 + t / 2), (z - (z0 + L / 2)) * 0.55)
                if d < 40 and rng.random() < max(0.0, 1.0 - d / 40) ** 0.7:
                    F.put(x, -1, z, rng.choice(['netherrack', 'netherrack', 'magma_block', 'crimson_nylium', 'soul_soil']))
    return {'walk_start': (x0 - 16, 0, z0 + L // 2), 'walk_targets': {'threshold': (x0 + t // 2 - 2, base + 1, z0 + L // 2)}}


REGION_DESIGNS = {
    # name: (function, (W, D, H), title, kwargs)
    'sea_academy': (sea_academy, (160, 160, 50), '海上学院', {}),
    'lighthouse_school': (lighthouse_school, (52, 52, 520), '灯塔教学楼', {}),
    'island_classroom': (island_classroom, (36, 52, 20), '小岛教室', {}),
    'dome_school_big': (dome_school, (262, 262, 262), '海底玻璃球学校（大）', {'R': 130}),
    'dome_school_small': (dome_school, (172, 172, 172), '海底玻璃球学校（小）', {'R': 85, 'seed': 44}),
    'pit_tower': (pit_tower, (76, 76, 1150), '天坑中央塔楼', {}),
    'cliff_school': (cliff_school, (36, 30, 26), '崖壁教学楼', {}),
    'cliff_school_t1': (cliff_school, (36, 30, 26), '崖壁教学楼（转 90°）', {'_turns': 1}),
    'cliff_school_t2': (cliff_school, (36, 30, 26), '崖壁教学楼（转 180°）', {'_turns': 2}),
    'cliff_school_t3': (cliff_school, (36, 30, 26), '崖壁教学楼（转 270°）', {'_turns': 3}),

    'sky_academy_white': (sky_academy, (120, 120, 85), '空岛学院（白）', {'style': 'white'}),
    'sky_academy_sand': (sky_academy, (120, 120, 85), '空岛学院（砂岩）', {'style': 'sand', 'seed': 60}),
    'sky_academy_stone': (sky_academy, (120, 120, 85), '空岛学院（石）', {'style': 'stone', 'seed': 62}),
    'sky_academy_brick': (sky_academy, (120, 120, 85), '空岛学院（红砖）', {'style': 'brick', 'seed': 63}),
    'end_academy': (end_academy, (140, 140, 90), '末地学院', {}),
    'infernal_academy': (infernal_academy, (200, 200, 110), '地狱学院', {}),
    'nether_gate_overworld': (nether_gate, (66, 112, 90), '巨型地狱门（主世界）', {}),
    'nether_gate_nether': (nether_gate, (66, 112, 90), '巨型地狱门（下界）', {'nether': True}),
}
