"""One-off landmark structures: gate, flagpole, main building, grandstand,
floodlights, library, globe, stairs."""
from __future__ import annotations

import math

import numpy as np

from anvil import B
import buildings as bd
import facades as fc
import font
from schemes import SCHEMES


def gate(rng, span=280, pylon=40, depth=30, H=221, beam_h=50, beam_y=160, name="无涯中学", motto="厚德博学"):
    """校门: two pylons and a beam with the school name in gold."""
    sc = SCHEMES["white_red"]
    A = np.zeros((H + 4, depth, span), np.uint16)
    for x0 in (0, span - pylon):
        faces = {s: ("blank", dict(grid=8)) for s in "NSEW"}
        p = bd.box(rng, pylon, depth, H, sc, faces, parapet=1, piers=False, furniture=False)
        bd.paste(A, p, 0, 0, x0)
        # vertical red stripe on the outward-facing (south) side
        A[8:H - 8, depth - 2, x0 + pylon // 2 - 3:x0 + pylon // 2 + 3] = sc.accent
    bw = span - 2 * pylon
    beam = np.zeros((beam_h, depth - 4, bw), np.uint16)
    beam[:] = B("red_terracotta")
    beam[0, :, :] = beam[-1, :, :] = sc.trim
    gold = B("gold_block")
    px = beam_h - 14
    for side, txt in (("S", name), ("N", motto)):
        bm = font.text(txt, px, px // 4, bold=1)[::-1]
        if side == "N":
            bm = bm[:, ::-1]
        h, w = bm.shape
        y0 = (beam_h - h) // 2
        x0 = (bw - w) // 2
        z = beam.shape[1] - 1 if side == "S" else 0
        sl = beam[y0:y0 + h, z, x0:x0 + w]
        sl[bm] = gold
    bd.paste(A, beam, beam_y, 2, pylon)
    # roof slab over the whole gate
    A[beam_y + beam_h, 2:depth - 2, pylon:span - pylon] = sc.trim
    return A


def guard_house(rng):
    A = np.zeros((6, 8, 12), np.uint16)
    A[0:4, :, :] = B("white_concrete")
    A[1:3, 1:7, 1:11] = 0
    A[1:3, 0, 2:10] = B("glass")
    A[1:3, 7, 2:10] = B("glass")
    A[1:3, 2:6, 0] = B("glass")
    A[4, :, :] = B("blue_terracotta")
    A[1:3, 1:7, 1:11] = 0
    return A


def flagpole(rng, H=330, flag_w=96, flag_h=64):
    W = flag_w + 4
    A = np.zeros((H + 4, 24, W + 24), np.uint16)
    cx = 12
    # three-step platform
    for k, r in enumerate((11, 8, 5)):
        A[k, cx - r:cx + r + 1, cx - r:cx + r + 1] = B("smooth_quartz") if k < 2 else B("polished_granite")
    A[3:H, cx - 1:cx + 2, cx - 1:cx + 2] = B("quartz_pillar")
    A[H:H + 2, cx - 2:cx + 3, cx - 2:cx + 3] = B("gold_block")
    # waving flag hanging east of the pole, top just under the finial
    top = H - 2
    red = B("red_wool")
    yel = B("yellow_wool")
    emb = font.text("无涯", flag_h // 3, 4, bold=1)[::-1]
    eh, ew = emb.shape
    for i in range(flag_w):
        x = cx + 2 + i
        amp = 1 + 5 * i / flag_w
        dz = int(round(amp * math.sin(i / 11.0)))
        sag = int(round(4 * (i / flag_w) ** 2))
        col = np.full(flag_h, red, np.uint16)
        j = i - 10
        if 0 <= j < ew:
            m = emb[:, j]
            ys = np.arange(eh) + (flag_h - eh) // 2
            col[ys[m]] = yel
        y1 = top - sag
        A[y1 - flag_h:y1, cx + dz, x] = col
    return A


def stairs(rng, width, steps, run=4, block="smooth_stone", edge="smooth_quartz"):
    """Grand stair rising toward -z (top at z=0)."""
    A = np.zeros((steps, steps * run, width), np.uint16)
    for k in range(steps):
        z1 = (steps - k) * run
        A[k, :z1, :] = B(block)
        A[k, z1 - 1, :] = B(edge)
    return A


def clock_face(r=32):
    n = 2 * r + 1
    F = np.zeros((n, n), np.uint16)
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    d = np.sqrt(yy ** 2 + xx ** 2)
    F[d <= r] = B("smooth_quartz")
    F[(d <= r) & (d > r - 3)] = B("black_concrete")
    blk = B("black_concrete")
    for h in range(12):
        a = math.radians(h * 30)
        for rr in np.arange(r - 9, r - 4, 0.5):
            for w in (-1.2, 0, 1.2):
                y = int(round(math.cos(a) * rr - math.sin(a) * w))
                x = int(round(math.sin(a) * rr + math.cos(a) * w))
                F[r - y, r + x] = blk
    def hand(angle_deg, length, width):
        a = math.radians(angle_deg)
        for rr in np.arange(-3, length, 0.4):
            for w in np.arange(-width / 2, width / 2 + 0.01, 0.5):
                y = int(round(math.cos(a) * rr - math.sin(a) * w))
                x = int(round(math.sin(a) * rr + math.cos(a) * w))
                F[r - y, r + x] = blk
    hand(7 * 30 + 25, r * 0.55, 3.5)    # hour hand ~7:50
    hand(50 * 6, r * 0.85, 2.5)         # minute hand
    F[r - 2:r + 3, r - 2:r + 3] = B("gold_block")
    return F                              # rows top->bottom


def main_building(rng, W=1088, D=296, H_front=281, H_wing=221, front_d=64, tower_w=128, tower_h=372,
                  wings=(0, 256, 512, 768, 1024), wing_w=64, scheme="white_red"):
    """主教学楼: a comb of wings behind a 1 km long front block, clock tower in the middle.
    Front faces +z (south).  Local z: 0 = rear."""
    sc = SCHEMES[scheme]
    A = np.zeros((380, D, W), np.uint16)
    # rear wings
    for wx in wings:
        hw = H_wing + int(rng.integers(-4, 5)) * 4
        f = {"E": ("corridor", dict(accent_every=10)), "W": ("corridor", dict(accent_every=10)),
             "N": ("windows", dict(accent_every=10))}
        part = bd.box(rng, wing_w, D - front_d + 8, hw, sc, f, extra=30)
        bd.paste(A, part, 0, 0, wx)
    # front block
    win = ("windows", dict(accent_every=10, ac=0.1, text=[
        dict(s="书山有路勤为径", y_top=44, u_center=W // 4 - 8, px=40, fg=B("red_concrete"), bg=B("white_concrete"), bold=1),
        dict(s="学海无涯苦作舟", y_top=44, u_center=3 * W // 4 + 8, px=40, fg=B("red_concrete"), bg=B("white_concrete"), bold=1),
    ]))
    def podium(F, side):
        if side != "S":
            return
        c = F.shape[1] // 2
        F[1:72, c - 210:c + 210, :] = 0
        cw = fc.curtain(72, 420, sc, rng)
        F[0:72, c - 210:c + 210, :cw.shape[2]] = cw
    f = {"S": win, "N": ("windows", dict(accent_every=10)), "E": ("corridor", dict(accent_every=10)),
         "W": ("corridor", dict(accent_every=10))}
    front = bd.box(rng, W, front_d, H_front, sc, f, extra=40, base=podium,
                   sign=None)
    bd.paste(A, front, 0, D - front_d, 0)
    # clock tower
    tx = (W - tower_w) // 2
    tf = {s: ("blank", dict(grid=12)) for s in "NSEW"}
    th = tower_h
    t = bd.box(rng, tower_w, 90, th, sc, tf, parapet=3, piers=False, furniture=False)
    bd.paste(A, t, 0, D - 90, tx)
    # crown: stepped top + mast
    A[th + 4:th + 6, D - 80:D - 10, tx + 10:tx + tower_w - 10] = sc.trim
    A[th + 4:min(380, th + 8), D - 50, tx + tower_w // 2] = B("red_concrete")
    # clock on the south face, protruding
    cf = clock_face(34)
    n = cf.shape[0]
    y_c = th - 60
    sl = A[y_c - n // 2:y_c - n // 2 + n, D - 1, tx + tower_w // 2 - n // 2: tx + tower_w // 2 - n // 2 + n]
    m = cf[::-1] != 0
    sl[m] = cf[::-1][m]
    # red vertical band with the school name under the clock
    nm = font.text("无涯中学", 28, 6, bold=1, vertical=True)[::-1]
    h, w = nm.shape
    yb = y_c - n // 2 - 16 - h
    zf = D - 1
    cx = tx + tower_w // 2
    A[yb - 6:yb + h + 6, zf - 1, cx - w // 2 - 6:cx + w // 2 + 6] = B("red_terracotta")
    A[yb - 6:yb + h + 6, zf, cx - w // 2 - 6:cx + w // 2 + 6] = 0
    sl = A[yb:yb + h, zf, cx - w // 2:cx - w // 2 + w]
    sl[nm] = B("gold_block")
    return A


def portico(rng, W=420, depth=20, col=8, pitch=42, H=72, podium=10):
    """Colossal colonnade + terrace in front of the main entrance (faces +z)."""
    A = np.zeros((podium + H + 10, depth, W), np.uint16)
    A[:podium, :, :] = B("smooth_stone")
    A[podium - 1, :, :] = B("polished_andesite")
    A[podium - 1, -1, :] = B("smooth_quartz")
    for x in range((W - col) % pitch // 2, W - col + 1, pitch):
        A[podium:podium + H, depth - col - 2:depth - 2, x:x + col] = B("quartz_pillar")
        A[podium:podium + 2, depth - col - 3:depth - 1, x - 1:x + col + 1] = B("smooth_quartz")
        A[podium + H - 2:podium + H, depth - col - 3:depth - 1, x - 1:x + col + 1] = B("smooth_quartz")
    A[podium + H:podium + H + 8, :, :] = B("smooth_quartz")
    A[podium + H + 2:podium + H + 4, depth - 1, :] = B("red_terracotta")
    return A


def grandstand(rng, length, depth, H, roof_h):
    """看台: seats rising toward -z, facing +z (the track), with a roof canopy."""
    L, D = length, depth
    A = np.zeros((roof_h + 3, D, L), np.uint16)
    seats = [B(c) for c in ("red_concrete", "yellow_concrete", "blue_concrete", "white_concrete", "green_concrete")]
    for z in range(D):
        h = int((D - z) * H / D) + 1
        A[:h, z, :] = B("light_gray_concrete")
        row = (z // 2) % len(seats)
        band = (np.arange(L) // 24) % 2
        A[h - 1, z, :] = np.where(band == 0, seats[row], seats[(row + 2) % len(seats)])
        A[h - 1, z, ::24] = B("smooth_stone")         # aisles
    A[:roof_h, 0:2, :] = B("light_gray_concrete")
    A[H:roof_h, 0:2, ::8] = B("glass")
    for x in range(0, L, 32):
        A[:roof_h, 2, x:x + 2] = B("white_concrete")
    A[roof_h:roof_h + 2, :, :] = B("white_concrete")
    A[roof_h, :, ::6] = B("light_gray_concrete")
    return A


def floodlight(rng, H=150):
    A = np.zeros((H + 14, 12, 12), np.uint16)
    for y in range(H):
        w = max(1, int(5 - 4 * y / H))
        c = 6
        for (a, b) in ((c - w, c - w), (c - w, c + w - 1), (c + w - 1, c - w), (c + w - 1, c + w - 1)):
            A[y, a, b] = B("iron_bars")
        if y % 6 == 0:
            A[y, c - w:c + w, c - w] = B("iron_bars")
            A[y, c - w:c + w, c + w - 1] = B("iron_bars")
    A[H:H + 12, 2:10, 0:12] = B("gray_concrete")
    A[H + 1:H + 11, 9, 1:11] = B("sea_lantern")
    return A


def globe(rng, R=30):
    """地球仪 sculpture: noise continents on a sphere, gold meridian ring, plinth."""
    n = 2 * R + 9
    Hh = 2 * R + 26
    A = np.zeros((Hh, n, n), np.uint16)
    c = n // 2
    A[0:6, c - 8:c + 9, c - 8:c + 9] = B("polished_granite")
    A[6:14, c - 2:c + 3, c - 2:c + 3] = B("gold_block")
    cy = 14 + R + 2
    yy, zz, xx = np.mgrid[0:Hh, 0:n, 0:n]
    dy, dz, dx = yy - cy, zz - c, xx - c
    d = np.sqrt(dy ** 2 + dz ** 2 + dx ** 2)
    shell = (d <= R) & (d > R - 2.5)
    # cheap "continents": sum of random spherical harmonics-ish waves
    u = np.stack([dx, dy, dz], -1) / np.maximum(d, 1)[..., None]
    f = np.zeros(d.shape)
    for _ in range(9):
        k = rng.normal(size=3)
        k /= np.linalg.norm(k)
        f += np.cos((u @ k) * rng.uniform(3, 7) + rng.uniform(0, 6.28))
    land = f > 1.2
    A[shell & ~land] = B("blue_terracotta")
    A[shell & land] = B("lime_terracotta")
    A[shell & land & (np.abs(dy) > R * 0.8)] = B("white_concrete")
    ring = (np.abs(np.sqrt(dy ** 2 + dx ** 2) - (R + 3)) < 0.8) & (np.abs(dz) < 1)
    A[ring] = B("gold_block")
    return A


def library(rng, W=176, D=150, H=241, col_h=200, scheme="cream_brick"):
    """图书馆: monumental colonnade with pediment-like attic, block behind."""
    sc = SCHEMES[scheme]
    A = np.zeros((H + 45, D, W), np.uint16)
    body = bd.box(rng, W - 16, D - 40, H, sc, {s: ("ribbon", dict(fins=4)) for s in "NSEW"}, extra=30)
    bd.paste(A, body, 0, 0, 8)
    # podium + colonnade along the south
    A[0:6, D - 40:D, :] = B("smooth_sandstone")
    A[5, D - 40:D, :] = B("cut_sandstone")
    pitch, cw = 22, 8
    for x in range(6, W - cw, pitch):
        A[6:6 + col_h, D - 14:D - 6, x:x + cw] = B("quartz_pillar")
    A[6 + col_h:6 + col_h + 16, D - 40:D - 4, 2:W - 2] = B("smooth_sandstone")
    A[6 + col_h + 16:6 + col_h + 18, D - 40:D - 4, 0:W] = B("cut_sandstone")
    bm = font.text("图书馆", 12, 4, bold=1)[::-1]
    h, w = bm.shape
    sl = A[6 + col_h + 2:6 + col_h + 2 + h, D - 5, (W - w) // 2:(W - w) // 2 + w]
    sl[bm] = B("gold_block")
    # stepped attic
    for k in range(6):
        A[6 + col_h + 18 + k * 2:6 + col_h + 20 + k * 2, D - 36 + k * 3:D - 8 - k * 3, 10 + k * 12:W - 10 - k * 12] = B("smooth_sandstone")
    return A
