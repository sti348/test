"""日食之海 (Eclipse Sea): the floating islands of the visual-novel key art
vn/locations/eclipse_sea/key.webp, rebuilt as a blockout in the Minecraft world.

The painting is a tall view from someone floating on their back in the sea,
looking up (west) at gothic school halls on floating islands stacked at very
different heights; the topmost island hides the sun.  Its layout was read off
the picture (direction and elevation angle of every island) and turned into
positions: the camera floats at CAM, facing west (the campus behind it, open
sea to the horizon), and each island is placed by its distance ahead (d), its
offset to the right (l, = north) and its height.

West of the campus, x -6100 .. -2150, z -4600 .. -1150: open sea.  In game:
/function wuya:tp/eclipse (sets a late morning, so the real sun stands just
behind the hall on the overhead island, as in the painting)."""
from __future__ import annotations

import math

import numpy as np

from anvil import B
import iconic as ic

SEA = -62
BOX = (-6100, -4600, -2150, -1150)          # x0, z0, x1, z1 of the sea
CAM = (-2500, -2600)                        # where the viewer floats; looks west (-x)
SUN_TIME = 5700                             # late morning: the sun ~85 degrees up in the east, just above the hall on B

# Read off the key art (vertical-panorama projection, 114 degrees tall, looking west and
# 53 degrees up): for every island the elevation angle of its hall and of the bottom
# of its rock, and its direction; turned into distance ahead (d), offset to the right
# (l, north), top surface height, radius and rock depth.
#   halls: (side, length, floors) - side "e" = the east rim, toward the camera
#   falls: the rim the waterfalls drop from ("front" = toward the camera)
ISLANDS = [
    # name        d     l    top    R   depth  halls                         falls
    ("A_top",   -500, -250, 1990, 450, None, [],                            None),     # the mass above everything, behind-left
    ("B_crown",  360,    0, 1700, 580, None, [("e", 320, 14)],              "front"),  # fills the upper half; its far-rim hall hides the sun
    ("H_left",   577, -210, 1450, 140, 200,  [("e", 150, 8)],               None),
    ("F_small", 1044, -136, 1500,  76, 140,  [("e", 70, 6)],                None),
    ("C_right",  900,  210, 1250, 230, 520,  [("e", 260, 12)],              "back"),
    ("D_left",   760, -165,  760, 200, 420,  [("e", 300, 11)],              "back"),
    ("E_rlow",   974,  252,  520, 180, 300,  [("e", 220, 10)],              "back"),
    ("g1",      1274,   45,  900,  50, 110,  [("e", 50, 5)],                None),
    ("g2",      1315,  -92,  700,  45, 100,  [("e", 40, 5)],                None),
    ("g3",      1412,  124,  600,  40,  90,  [("e", 40, 4)],                None),
    ("g4",      1381, -145,  500,  35,  80,  [],                            None),
    ("g5",      1277,  180, 1100,  55, 120,  [("e", 50, 5)],                None),
]

LOOK = ic.Look("brutal", wall="polished_andesite", accent="stone_bricks", band="smooth_stone",
               column="light_gray_concrete", glass="gray_stained_glass", back="black_concrete",
               lit="ochre_froglight", roof="deepslate_tiles", trim="smooth_stone", plinth="polished_deepslate")


def world_xz(d, l):
    """Ahead = west (-x), right = north (-z)."""
    return CAM[0] - d, CAM[1] - l


# ------------------------------------------------------------------ the sea
class EclipseSea:
    bbox = BOX

    def apply(self, m, x0, z0):
        from regions import _grid, fbm, smooth, GROUND
        xs, zs = _grid(m, x0, z0)
        X0, Z0, X1, Z1 = BOX
        inside = (xs >= X0) & (xs < X1) & (zs >= Z0) & (zs < Z1)
        if not inside.any():
            return
        edge = np.minimum.reduce([xs - X0, X1 - xs, zs - Z0, Z1 - zs]).astype(np.float64)
        depth = (4 + 36 * smooth(edge / 260) + 8 * fbm(xs, zs, 160, 81)) * smooth(edge / 120)
        g = np.round(GROUND - depth).astype(np.int32)
        m["ground"][inside] = g[inside]
        wet = inside & (g < SEA)
        m["fluid"][wet] = SEA
        m["fluid_id"][wet] = B("water")
        nb = fbm(xs, zs, 40, 83)
        bed = np.where(nb > 0.2, B("gravel"), B("sand")).astype(np.uint16)
        top = np.where(g < SEA, bed, B("sand")).astype(np.uint16)
        m["top"][inside] = top[inside]
        m["sub"][inside] = B("sand")


# ------------------------------------------------------------------ gothic halls
def gothic_hall(rng, L=200, D=40, floors=10, towers=True, seed=0, lit=0.3):
    """A long gothic school hall: unbroken stone ribs and tall lancet windows
    (lit warm), a steep slate roof, pinnacles along the eaves and two towers
    with spires at the ends (the halls on the rims in the key art)."""
    H = ic.H_of(floors)
    roof = D // 2 + 4
    tw = min(28, L // 6) if towers else 0
    th = H + roof + (60 if towers else 0)
    hh = th + 30
    M = np.zeros((hh, D, L), bool)
    M[:H, :, :] = True
    zs, xs = np.mgrid[0:D, 0:L]
    for k in range(roof):                                      # gable roof along x
        M[H + k][np.abs(zs + 0.5 - D / 2) < D / 2 - k] = True
    for x0 in ((0, L - tw) if towers else ()):
        M[:th, :, x0:x0 + tw] = True
    U = xs.astype(np.float64)
    A = ic.skin(M, U, LOOK, style="gothic", bay=16, lit=lit, seed=seed, plinth=ic.H_of(1), crown=0)
    # roof slopes in slate
    for k in range(roof):
        band = M[H + k] & ~(M[H + k + 1] if H + k + 1 < hh else np.zeros_like(M[0]))
        A[H + k][band] = LOOK.roof
    # pinnacles on the eaves every 16
    for x in range(8, L - 8, 16):
        for z in (0, D - 1):
            A[H:H + 10, z, x] = LOOK.column
            A[H + 10, z, x] = LOOK.trim
    if towers:                                                 # spires on the end towers
        for x0 in (0, L - tw):
            c = x0 + tw / 2
            for k in range(30):
                hw = (tw / 2) * (1 - k / 30)
                if hw < 0.5:
                    break
                sel = (np.abs(xs + 0.5 - c) < hw) & (np.abs(zs + 0.5 - D / 2) < min(hw, D / 2))
                A[th + k][sel] = LOOK.roof
    return A


def gothic_hall_size(L=200, D=40, floors=10, towers=True):
    H = ic.H_of(floors)
    th = H + D // 2 + 4 + (60 if towers else 0)
    return (th + 30, D, L)


# ------------------------------------------------------------------ pieces
def pieces(out, rng):
    from regions import place_sky_island, column, _p
    for k, (name, d, l, top, R, depth, halls, falls) in enumerate(ISLANDS):
        x, z = world_xz(d, l)
        tiles = 4 if R > 400 else 3 if R > 200 else 2 if R > 90 else 1
        place_sky_island(out, "eclipse_island", x, top, z, R, "dark", 500 + k, tiles=tiles, depth=depth)
        for (side, L, floors) in halls:
            D = max(24, min(44, L // 6))
            sz = gothic_hall_size(L, D, floors)
            hx = int(x + R - D // 2 - 3)                       # east rim, facade flush with the rock edge
            _p(out, "eclipse_hall", hx - D // 2, top + 1, z - L // 2, (sz[0], sz[2], sz[1]), _hall_z, 600 + k,
               L=L, D=D, floors=floors)
        if falls:
            # "front" = the west rim of an island overhead (seen hanging under it),
            # "back" = the east rim of an island ahead (the side facing the camera)
            base = math.pi if falls == "front" else 0.0
            for da in (-0.45, 0.4):
                a = base + da
                fx, fz = x + (R - 6) * math.cos(a), z + (R - 6) * math.sin(a)
                h = int(min(top - SEA - 80, 220 + R * 0.7))
                _p(out, "eclipse_fall", fx, top - h + 1, fz, (h, 1, 5), column, 0, h=h, kind="water", w=5)


def _hall_x(rng, L, D, floors):
    return gothic_hall(rng, L=L, D=D, floors=floors, seed=int(rng.integers(1 << 30)))


def _hall_z(rng, L, D, floors):
    A = gothic_hall(rng, L=L, D=D, floors=floors, seed=int(rng.integers(1 << 30)))
    return A.transpose(0, 2, 1)[:, ::-1, :].copy()


def viewpoint():
    x, z = CAM
    return (x + 0.5, SEA + 1, z + 0.5, 90, -55, "日食之海（躺在海面仰望空岛；时间设为上午）")


# ------------------------------------------------------------------ preview of just this area
def coarse_grid(s=4, y0=-64, y1=2032):
    """The islands, halls and falls of this area on an s-block grid, plus the sea
    plane; pieces are built one by one and subsampled at once (the full-resolution
    compose of an area this tall does not fit in memory)."""
    import render
    rng = np.random.default_rng(7)
    out = []
    pieces(out, rng)
    X0, Z0, X1, Z1 = BOX
    X1 += 450                                                  # island A reaches over the shore
    nx, nz, ny = (X1 - X0) // s, (Z1 - Z0) // s, (y1 - y0) // s
    V = np.zeros((ny, nz, nx), np.uint16)
    for p in out:
        A = p.build()
        # first indices inside A that land on the grid
        oy, oz, ox = (-(p.y - y0)) % s, (-(p.z - Z0)) % s, (-(p.x - X0)) % s
        S = A[oy::s, oz::s, ox::s]
        gy, gz, gx = (p.y + oy - y0) // s, (p.z + oz - Z0) // s, (p.x + ox - X0) // s
        ya, za, xa = max(0, gy), max(0, gz), max(0, gx)
        yb, zb, xb = min(ny, gy + S.shape[0]), min(nz, gz + S.shape[1]), min(nx, gx + S.shape[2])
        if ya >= yb or za >= zb or xa >= xb:
            continue
        src = S[ya - gy:yb - gy, za - gz:zb - gz, xa - gx:xb - gx]
        dst = V[ya:yb, za:zb, xa:xb]
        mask = (src != 0) & (src != B("cave_air"))
        dst[mask] = src[mask]
    k = (SEA - y0) // s
    V[k][V[k] == 0] = B("water")
    return render.Grid(V, X0, Z0, y0, s)


def preview(out_png, w=384, h=960, s=4, proj="pano"):
    import render
    import textures
    from PIL import Image
    G = coarse_grid(s)
    x, z = CAM
    eye = (x + 0.5, SEA + 1 + s, z + 0.5)                      # above the coarse water layer
    img = render.render(G, eye, 90, -53, w=w, h=h, fov=114, tex=textures.atlas(), maxdist=4500, haze=0.00012,
                        proj=proj)
    Image.fromarray(img).save(out_png)
    return out_png
