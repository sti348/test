"""Building generators.  Every generator returns a uint16 array A[y, z, x]
(0 = leave as is) in local coordinates; Piece places it in the world."""
from __future__ import annotations


import numpy as np

from anvil import B
import facades as fc
import font
from schemes import SCHEMES

GROUND_Y = -60          # first air block above the grass


class Piece:
    """Something placed in the world: origin (x, y, z) of A[0,0,0] + size."""
    __slots__ = ("x", "y", "z", "h", "dz", "dx", "fn", "kw", "seed", "name")

    def __init__(self, name, x, y, z, size, fn, seed=0, kw=None, **extra):
        kw = dict(kw or {}, **extra)
        self.name = name
        self.x, self.y, self.z = x, y, z
        self.h, self.dz, self.dx = size
        self.fn, self.kw, self.seed = fn, kw, seed

    def build(self):
        A = self.fn(np.random.default_rng(self.seed), **self.kw)
        assert A.shape == (self.h, self.dz, self.dx), (self.name, A.shape, (self.h, self.dz, self.dx))
        return A

    @property
    def x1(self):
        return self.x + self.dx

    @property
    def z1(self):
        return self.z + self.dz

    @property
    def top(self):
        return self.y + self.h


def paste(A, S, y, z, x):
    """Paste S into A at (y,z,x), nonzero only, clipped."""
    h, dz, dx = S.shape
    ya, za, xa = max(0, y), max(0, z), max(0, x)
    yb, zb, xb = min(A.shape[0], y + h), min(A.shape[1], z + dz), min(A.shape[2], x + dx)
    if ya >= yb or za >= zb or xa >= xb:
        return
    src = S[ya - y:yb - y, za - z:zb - z, xa - x:xb - x]
    dst = A[ya:yb, za:zb, xa:xb]
    m = src != 0
    dst[m] = src[m]


# ---------------------------------------------------------------- face placement
def put_face(A, side, F, y0=0):
    """Place facade F[y,u,d] on one side of A (whose footprint is A.shape[1:])."""
    H, W, D = F.shape
    _, dz, dx = A.shape
    sl = slice(y0, y0 + H)
    if side == "N":
        assert W == dx
        S = F.transpose(0, 2, 1)                      # (H, D, W): z=d, x=u
        dst = A[sl, 0:D, :]
    elif side == "S":
        assert W == dx
        S = F.transpose(0, 2, 1)[:, ::-1, :]
        dst = A[sl, dz - D:dz, :]
    elif side == "W":
        assert W == dz
        S = F                                          # (H, W=z, D=x)
        dst = A[sl, :, 0:D]
    else:
        assert W == dz
        S = F[:, :, ::-1]
        dst = A[sl, :, dx - D:dx]
    m = S != 0
    dst[m] = S[m]


MIRROR = {"N": True, "S": False, "W": False, "E": True}


def face_width(side, dx, dz):
    return dx if side in "NS" else dz


# ---------------------------------------------------------------- rooftop furniture
def water_tank(r=4, h=7):
    A = np.zeros((h + 3, 2 * r + 1, 2 * r + 1), np.uint16)
    zz, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disk = zz ** 2 + xx ** 2 <= r * r + r
    for y in range(3, h + 3):
        A[y][disk] = B("light_gray_concrete") if y < h + 2 else B("smooth_stone_slab")
    for (a, b) in ((1, 1), (1, 2 * r - 1), (2 * r - 1, 1), (2 * r - 1, 2 * r - 1)):
        A[0:3, a, b] = B("iron_bars")
    return A


def mast(h):
    A = np.zeros((h, 1, 1), np.uint16)
    A[:, 0, 0] = B("iron_bars")
    A[-1, 0, 0] = B("red_concrete")
    return A


def rooftop_sign(text, px, fg, frame=B("iron_bars")):
    bm = font.text(text, px, max(2, px // 5), bold=1)[::-1]   # bottom-up
    h, w = bm.shape
    legs = 4
    A = np.zeros((h + legs, 3, w), np.uint16)
    A[legs:, 1, :][bm] = fg
    # scaffold behind the letters
    for x in range(0, w, 4):
        A[:legs + h, 2, x] = frame
    A[legs, 2, :] = frame
    A[legs + h // 2, 2, :] = frame
    return A


def rooftop(A, sc, rng, H, inset, dz, dx, sign=None):
    """Mechanical penthouse, tanks, masts and maybe a sign on the roof at y=H+1."""
    y = H + 1
    room_h = A.shape[0] - y
    if room_h < 3:
        return
    # penthouse(s)
    for _ in range(rng.integers(1, 3)):
        pw = int(min(dx - 2 * inset - 4, rng.integers(10, 26)))
        pd = int(min(dz - 2 * inset - 4, rng.integers(8, 16)))
        if pw < 6 or pd < 6:
            break
        ph = int(min(room_h - 1, rng.integers(6, 11)))
        px = int(rng.integers(inset + 2, dx - inset - pw - 1))
        pz = int(rng.integers(inset + 2, dz - inset - pd - 1))
        A[y:y + ph, pz:pz + pd, px:px + pw] = sc.wall
        A[y + ph - 1, pz:pz + pd, px:px + pw] = sc.trim
        A[y + 1:y + ph - 2, pz, px + 2:px + pw - 2:3] = B("gray_concrete")
    for _ in range(rng.integers(0, 4)):
        t = water_tank(int(rng.integers(3, 6)), int(rng.integers(5, 9)))
        if t.shape[0] > room_h or t.shape[1] + 2 * inset + 4 > min(dz, dx):
            continue
        tz = int(rng.integers(inset + 2, dz - inset - t.shape[1] - 1))
        tx = int(rng.integers(inset + 2, dx - inset - t.shape[2] - 1))
        paste(A, t, y, tz, tx)
    for _ in range(rng.integers(0, 3)):
        mh = int(min(room_h, rng.integers(10, 36)))
        mz = int(rng.integers(inset + 2, dz - inset - 2))
        mx = int(rng.integers(inset + 2, dx - inset - 2))
        A[y:y + mh, mz, mx] = B("iron_bars")
        A[y + mh - 1, mz, mx] = B("red_concrete")
    if sign:
        txt, px, fg, side = sign
        s = rooftop_sign(txt, px, fg)
        if s.shape[0] <= room_h and s.shape[2] <= dx - 2 * inset:
            sx = (dx - s.shape[2]) // 2
            if side == "S":
                paste(A, s[:, ::-1, :], y, dz - inset - 4, sx)
            else:
                paste(A, s[:, :, ::-1], y, inset + 1, sx)


# ---------------------------------------------------------------- box
def box(rng, dx, dz, H, sc, faces, extra=0, parapet=2, roof=True, piers=True, sign=None,
        furniture=True, base=None):
    """One rectangular block.  faces: side -> (style, kwargs) or None.
    H = facade height; roof slab at H, parapet above, `extra` rows for rooftop stuff."""
    A = np.zeros((H + 1 + parapet + extra, dz, dx), np.uint16)
    depth = 1
    for side in ("W", "E", "N", "S"):
        spec = faces.get(side)
        if spec is None:
            continue
        style, kw = spec
        kw = dict(kw)
        text = kw.pop("text", None)
        F = fc.face(style, H, face_width(side, dx, dz), sc, rng, side, **kw)
        if text:
            for t in text:
                t = dict(t)
                t.setdefault("mirror", MIRROR[side])
                fc.letters(F, **t)
        if base:
            base(F, side)
        depth = max(depth, F.shape[2])
        put_face(A, side, F)
    if piers:
        p = min(depth, dx // 2, dz // 2)
        for (za, xa) in ((1, 1), (1, dx - p), (dz - p, 1), (dz - p, dx - p)):
            A[:H, za:za + p - 1, xa:xa + p - 1] = sc.wall
    if roof:
        A[H, 1:dz - 1, 1:dx - 1] = sc.roof
        A[H, 1, 1:dx - 1] = A[H, dz - 2, 1:dx - 1] = sc.trim
        A[H, 1:dz - 1, 1] = A[H, 1:dz - 1, dx - 2] = sc.trim
        for k in range(1, parapet + 1):
            A[H + k, 1, 1:dx - 1] = A[H + k, dz - 2, 1:dx - 1] = sc.trim
            A[H + k, 1:dz - 1, 1] = A[H + k, 1:dz - 1, dx - 2] = sc.trim
        if furniture and extra:
            rooftop(A, sc, rng, H + parapet - 1, 3, dz, dx, sign)
    return A


def floors_h(n, fh=4):
    return n * fh + 1


# ---------------------------------------------------------------- building types
def slab(rng, L, Dp, H, scheme, corridor_side="S", towers=True, name=None, motto=None, sign=None,
         axis="x", extra=40, lit=0.02, ac=0.15, accent_every=0, k=1):
    """教学楼: long block, open corridors on one side, windows on the other,
    stair towers at both ends (2 floors higher) with the building name."""
    sc = SCHEMES[scheme]
    tw = 14 if towers else 0                       # tower width along L
    td = Dp + 6                                    # towers stick out
    body = L - 2 * tw
    other = {"S": "N", "N": "S"}[corridor_side]
    faces = {corridor_side: ("corridor", dict(lit=lit, accent_every=accent_every)),
             other: ("windows", dict(lit=lit, ac=ac, accent_every=accent_every)),
             "E": ("windows", dict(lit=lit, ac=0, pilaster=False)),
             "W": ("windows", dict(lit=lit, ac=0, pilaster=False))}
    if motto:
        txt, px, ytop = motto
        faces[corridor_side][1]["text"] = [dict(s=txt, y_top=ytop, u_center=body // 2, px=px,
                                                fg=B("white_concrete"), bg=sc.accent if scheme != "red_brick" else B("red_concrete"))]
    th = H + 8
    total_h = th + 1 + 2 + extra
    A = np.zeros((total_h, td, L), np.uint16)
    core = box(rng, body, Dp, H, sc, faces, extra=extra + 8, sign=sign)
    paste(A, core[:total_h], 0, 3, tw)
    if towers:
        for i, x0 in enumerate((0, L - tw)):
            tf = {s: ("stair", {}) for s in "NSEW"}
            if name:
                tf[corridor_side] = ("stair", dict(text=[dict(s=name, y_top=12, u_center=tw // 2, px=11, fg=B("gold_block"),
                                                              vertical=True, gap=3, d_fg=0, d_bg=1)]))
            t = box(rng, tw, td, th, sc, tf, extra=0, parapet=1, furniture=False)
            paste(A, t, 0, 0, x0)
    if axis == "z":
        A = A.transpose(0, 2, 1)[:, :, ::-1].copy()
    return A


def slab_size(L, Dp, H, extra=40, axis="x"):
    h = H + 8 + 1 + 2 + extra
    return (h, Dp + 6, L) if axis == "x" else (h, L, Dp + 6)


def skybridge(rng, length, width, n_floors, scheme, axis="z"):
    """连廊 between two slabs (length runs across the gap)."""
    sc = SCHEMES[scheme]
    H = floors_h(n_floors)
    if axis == "z":
        A = box(rng, width, length, H, sc, {"E": ("ribbon", {}), "W": ("ribbon", {})}, parapet=1, piers=False,
                furniture=False)
    else:
        A = box(rng, length, width, H, sc, {"N": ("ribbon", {}), "S": ("ribbon", {})}, parapet=1, piers=False,
                furniture=False)
    return A


def tower(rng, W, H, scheme, tiers=3, style="windows", sign=None, extra=40):
    """Square tower with setbacks."""
    sc = SCHEMES[scheme]
    A = np.zeros((H + 3 + extra, W, W), np.uint16)
    y = 0
    w = W
    hs = np.diff(np.round(np.linspace(0, H, tiers + 1)).astype(int))
    for i, h in enumerate(hs):
        h = int(h) - int(h) % 4 + 1 if i < tiers - 1 else H - y
        last = i == tiers - 1
        st = style if not (i == 0 and style == "curtain") else "ribbon"
        faces = {s: (st, {"lit": 0.02} if st != "windows" else {"lit": 0.02, "ac": 0.1}) for s in "NSEW"}
        bx = box(rng, w, w, h, sc, faces, extra=(extra if last else 0), parapet=2 if last else 1,
                 furniture=last, sign=sign if last else None)
        off = (W - w) // 2
        paste(A, bx[:A.shape[0] - y], y, off, off)
        y += h
        w = max(16, int(w * 0.78)) // 2 * 2 + (W % 2)
    return A


def courtyard(rng, O, R, heights, scheme, names=None, extra=40):
    """回字形教学楼: four wings around a courtyard, corridors face inside.
    heights: (south, east, north, west) facade heights."""
    sc = SCHEMES[scheme]
    Hmax = max(heights)
    A = np.zeros((Hmax + 3 + extra, O, O), np.uint16)
    hS, hE, hN, hW = heights
    win = ("windows", dict(ac=0.12))
    cor = ("corridor", {})
    # wings: N and S full width; E and W between them
    s = box(rng, O, R, hS, sc, {"S": win, "N": cor, "E": win, "W": win}, extra=extra)
    n = box(rng, O, R, hN, sc, {"N": win, "S": cor, "E": win, "W": win}, extra=extra)
    e = box(rng, R, O - 2 * R + 2, hE, sc, {"E": win, "W": cor}, extra=extra)
    w = box(rng, R, O - 2 * R + 2, hW, sc, {"W": win, "E": cor}, extra=extra)
    for part, z, x in ((e, R - 1, O - R), (w, R - 1, 0), (n, 0, 0), (s, O - R, 0)):
        paste(A, part[:A.shape[0]], 0, z, x)
    return A


def dorm(rng, L, Dp, H, scheme, extra=30, axis="x"):
    """宿舍楼: balconies with laundry on the south, windows north."""
    sc = SCHEMES[scheme]
    faces = {"S": ("balcony", {}), "N": ("windows", dict(bay=6, ac=0.3, pilaster=False)),
             "E": ("stair", {}), "W": ("stair", {})}
    A = box(rng, L, Dp, H, sc, faces, extra=extra)
    if axis == "z":
        A = A.transpose(0, 2, 1)[:, :, ::-1].copy()
    return A


def lab(rng, dx, dz, H, scheme, name=None, extra=40):
    """实验楼: ribbon windows behind vertical fins, name on the south face."""
    sc = SCHEMES[scheme]
    f = ("ribbon", dict(fins=3))
    faces = {s: f for s in "NSEW"}
    if name:
        faces["S"] = ("ribbon", dict(fins=3, text=[dict(s=name, y_top=16, u_center=dx // 2, px=24,
                                                         fg=B("white_concrete"), bg=sc.accent, bold=1)]))
    return box(rng, dx, dz, H, sc, faces, extra=extra)


def gym(rng, dx, dz, wall_h, vault_h, scheme):
    """体育馆: barrel vault along x with skylight stripes, glass gable ends."""
    sc = SCHEMES[scheme]
    A = np.zeros((wall_h + vault_h + 2, dz, dx), np.uint16)
    faces = {"N": ("ribbon", dict(spandrel=sc.accent)), "S": ("ribbon", dict(spandrel=sc.accent)),
             "E": ("curtain", {}), "W": ("curtain", {})}
    bx = box(rng, dx, dz, wall_h, sc, faces, roof=False, parapet=0, piers=True)
    paste(A, bx, 0, 0, 0)
    # vault cross-section in (z, y): ellipse z in [-a, a], height vault_h
    a = dz / 2 - 0.5
    zc = (dz - 1) / 2
    zz = np.arange(dz) - zc
    prof = vault_h * np.sqrt(np.clip(1 - (zz / a) ** 2, 0, 1))
    roofm = B("light_gray_concrete")
    sky = B("glass")
    for z in range(dz):
        ytop = int(prof[z])
        ynext = int(min(prof[z - 1] if z > 0 else 0, prof[z + 1] if z < dz - 1 else 0))
        for yy in range(min(ytop, ynext), ytop + 1):
            y = wall_h + yy
            if y < A.shape[0]:
                row = np.full(dx, roofm, np.uint16)
                row[(np.arange(dx) // 6) % 4 == 0] = sky
                row[:2] = row[-2:] = sc.trim
                A[y, z, :] = row
    # gable ends
    for x in (0, 1, dx - 2, dx - 1):
        for z in range(dz):
            top = int(prof[z])
            A[wall_h:wall_h + top, z, x] = sc.glass if (z % 4 and x in (0, dx - 1)) else sc.column
    A[wall_h:wall_h + vault_h, :, 2] = np.where(A[wall_h:wall_h + vault_h, :, 1] != 0, B("black_concrete"), 0)
    A[wall_h:wall_h + vault_h, :, dx - 3] = np.where(A[wall_h:wall_h + vault_h, :, dx - 2] != 0, B("black_concrete"), 0)
    return A


def canteen(rng, dx, dz, H, scheme, label="食堂", extra=30):
    sc = SCHEMES[scheme]
    faces = {s: ("curtain", {}) for s in "NEW"}
    faces["S"] = ("curtain", dict(text=[dict(s=label, y_top=6, u_center=dx // 2, px=min(H - 14, 40),
                                             fg=B("red_concrete"), bg=B("white_concrete"), bold=1)]))
    return box(rng, dx, dz, H, sc, faces, extra=extra)


# ---------------------------------------------------------------- small props
LEAVES = {"oak": B("oak_leaves[persistent=true]"), "birch": B("birch_leaves[persistent=true]"),
          "cherry": B("cherry_leaves[persistent=true]"), "dark": B("dark_oak_leaves[persistent=true]")}
LOGS = {"oak": B("oak_log"), "birch": B("birch_log"), "cherry": B("cherry_log"), "dark": B("dark_oak_log")}


def tree(rng, kind="oak", size=1.0):
    if kind == "birch":       # tall narrow (poplar-ish)
        h = int(rng.integers(8, 12) * size)
        A = np.zeros((h + 3, 5, 5), np.uint16)
        zz, xx = np.mgrid[-2:3, -2:3]
        for y in range(3, h + 3):
            r = 1.6 if y < h else 1.0
            A[y][(zz ** 2 + xx ** 2) <= r * r + rng.random((5, 5)) * 1.2] = LEAVES["birch"]
        A[:h, 2, 2] = LOGS["birch"]
        return A
    r = int(rng.integers(2, 4) * size) + 1
    h = int(rng.integers(3, 5) * size) + 1
    n = 2 * r + 1
    A = np.zeros((h + r + 2, n, n), np.uint16)
    yy, zz, xx = np.mgrid[0:A.shape[0], -r:r + 1, -r:r + 1]
    cy = h + r * 0.4
    d = ((yy - cy) / (r * 0.8)) ** 2 + (zz / r) ** 2 + (xx / r) ** 2
    A[(d <= 1.0 + 0.35 * rng.random(A.shape)) & (yy >= h - 1)] = LEAVES[kind]
    A[:h + 1, r, r] = LOGS[kind]
    return A


def lamp(rng, h=5):
    A = np.zeros((h + 1, 1, 1), np.uint16)
    A[:h, 0, 0] = B("stone_brick_wall")
    A[h, 0, 0] = B("lantern")
    return A


def hoop(rng, facing):
    """Basketball hoop at real scale (pole + backboard); facing: +1 / -1 along x."""
    A = np.zeros((5, 3, 3), np.uint16)
    px = 0 if facing > 0 else 2
    A[0:4, 1, px] = B("gray_concrete")
    A[3:5, 0:3, 1] = B("white_concrete")
    A[3, 1, 2 - px] = B("red_concrete")
    return A


def bike_shed(rng, length):
    L = length
    """自行车棚: thin posts, blue roof, rows of bikes (dark blocks)."""
    A = np.zeros((4, 5, L), np.uint16)
    A[0:3, 0, ::6] = B("iron_bars")
    A[0:3, 4, ::6] = B("iron_bars")
    A[3, :, :] = B("blue_terracotta")
    for x in range(1, L - 1, 2):
        if rng.random() < 0.7:
            A[0, 2, x] = B(["black_concrete", "red_concrete", "blue_concrete", "white_concrete"][rng.integers(4)])
    return A
