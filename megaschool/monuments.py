"""Monuments: the triumphal-arch school gate and the desert pyramid school.

Generators return A[y, z, x] (uint16, 0 = leave as is) like everything else."""
from __future__ import annotations

import math

import numpy as np

from anvil import B


def _arch_mask(h, w, spring, radius, cx):
    """(y, x) mask of an arch opening: a rectangle up to `spring`, a half circle above."""
    ys, xs = np.mgrid[0:h, 0:w]
    dx = xs + 0.5 - cx
    rect = (np.abs(dx) < radius) & (ys < spring)
    circ = (dx ** 2 + (ys + 0.5 - spring) ** 2 < radius ** 2) & (ys >= spring)
    return rect | circ


# ================================================================ triumphal arch (校门)
def triumphal_arch(rng, W=280, D=100, H=260, Wa=80, spring=104, Tw=40, t_spring=56):
    """A triumphal arch in pale stone: one great barrel vault (Wa wide) along z
    for the avenue, a smaller cross vault through each pier along x, relief
    panels and archivolts on both fronts, a deep cornice, an attic ringed
    with round shields and a crowning cornice.  No lettering anywhere.
    Coffers in the vaults glow at dusk."""
    body, rust, trim = B("smooth_quartz"), B("quartz_bricks"), B("chiseled_quartz_block")
    relief, shadow, glow = B("chiseled_sandstone"), B("polished_deepslate"), B("pearlescent_froglight")
    panel_bg = B("smooth_sandstone")
    A = np.zeros((H, D, W), np.uint16)
    A[:] = body
    # rusticated base: grooves every 4 rows on the lowest 40
    for y in range(3, 40, 4):
        A[y, :, :] = rust
    # hollow the core (keep a 6-block shell); interior is never seen
    A[8:H - 8, 6:D - 6, 6:W - 6] = 0
    cx = W / 2
    # --- central barrel vault along z
    m = _arch_mask(H, W, spring, Wa / 2, cx)
    A[:, :, :][np.broadcast_to(m[:, None, :], A.shape)] = 0
    # vault surface: coffers on the intrados (ring of cells just outside the opening)
    ys, xs = np.mgrid[0:H, 0:W]
    dx = xs + 0.5 - cx
    r = np.hypot(dx, np.maximum(0, ys + 0.5 - spring))
    shell = (~m) & (r < Wa / 2 + 3) & ((ys >= spring) | (np.abs(dx) < Wa / 2 + 3))
    ang = np.degrees(np.arctan2(np.maximum(0, ys + 0.5 - spring), dx))
    for z in range(D):
        sl = A[:, z, :]
        sl[shell & (sl == 0)] = body                 # close the vault where the core was hollowed
        cof = shell & (ys >= spring) & (r < Wa / 2 + 1)
        sl[cof & ((np.round(ang / 9).astype(int) + z // 8) % 2 == 0)] = trim
        sl[cof & (np.round(ang / 9).astype(int) % 2 == 0) & (z % 8 == 4)] = glow
    # --- cross vaults along x through both piers
    zc = D / 2
    zs2, ys2 = np.mgrid[0:D, 0:H]
    mt = (np.abs(zs2 + 0.5 - zc) < Tw / 2) & (ys2 < t_spring)
    mt |= ((zs2 + 0.5 - zc) ** 2 + (ys2 + 0.5 - t_spring) ** 2 < (Tw / 2) ** 2) & (ys2 >= t_spring)
    mtT = mt.T                                         # (y, z)
    rt = np.hypot(zs2 + 0.5 - zc, np.maximum(0, ys2 + 0.5 - t_spring)).T
    for x in list(range(0, int(cx - Wa / 2))) + list(range(int(cx + Wa / 2), W)):
        sl = A[:, :, x]
        sl[mtT] = 0
        sh = (~mtT) & (rt < Tw / 2 + 3)
        sl[sh & (sl == 0)] = body
        if x % 10 == 5:
            sl[sh & (rt < Tw / 2 + 1) & (np.arange(H)[:, None] >= t_spring)] = glow
    # --- low light in the passages: the coffers are 100+ blocks up, so the
    # walkway under the vault was pitch dark in Horizon's light engine
    for z in range(3, D - 3, 6):
        for side in (-1, 1):
            x = int(cx - Wa / 2) - 1 if side < 0 else int(cx + Wa / 2)      # the wall face next to the opening
            A[6:9, z, x] = glow                                  # lamp niches along both passage walls
            A[24:26, z, x] = glow
    for x in list(range(4, int(cx - Wa / 2) - 2, 6)) + list(range(int(cx + Wa / 2) + 3, W - 4, 6)):
        for zz in (int(zc - Tw / 2) - 1, int(zc + Tw / 2)):
            A[6:9, zz, x] = glow
    # --- archivolts: a moulded band around the openings on the fronts and sides
    arv = (~m) & (r >= Wa / 2) & (r < Wa / 2 + 5) & (ys >= spring)
    for z in (0, 1, D - 2, D - 1):
        A[:, z, :][arv] = trim
    imp = (np.abs(np.abs(dx) - Wa / 2 - 2) < 3) & (np.abs(ys - spring) < 2)
    for z in (0, D - 1):
        A[:, z, :][imp] = trim
    arv_t = (~mtT) & (rt >= Tw / 2) & (rt < Tw / 2 + 4) & (np.arange(H)[:, None] >= t_spring)
    for x in (0, 1, W - 2, W - 1):
        A[:, :, x][arv_t] = trim
    # --- relief panels on each pier front (both faces) and above the cross vaults
    pier_w = int(cx - Wa / 2)

    def panel(y0, y1, u0, u1, face):
        """A relief panel: a moulded frame flush with the wall, the relief sunk
        2 blocks into it so it reads by its shadow (found flat and invisible at
        dusk when the map was inspected in Horizon)."""
        def at(y, u, depth):
            if face == "N":
                return (y, depth, u)
            if face == "S":
                return (y, D - 1 - depth, u)
            if face == "W":
                return (y, u, depth)
            return (y, u, W - 1 - depth)
        for y in range(y0, y1):
            for u in range(u0, u1):
                if y in (y0, y1 - 1) or u in (u0, u1 - 1):
                    A[at(y, u, 0)] = trim
                    continue
                A[at(y, u, 0)] = 0
                A[at(y, u, 1)] = 0
                inner = ((u - u0) // 3 + (y - y0) // 3) % 4 == 0 or ((u - u0) * 7 + (y - y0) * 3) % 11 == 0
                A[at(y, u, 2)] = relief if inner else panel_bg
                if inner and (u + y) % 3 == 0:
                    A[at(y, u, 1)] = relief            # figures stand out of the sunk ground
    for face in ("N", "S"):
        for (u0, u1) in ((12, pier_w - 12), (W - pier_w + 12, W - 12)):
            panel(t_spring + 34, spring + 30, u0, u1, face)
            panel(48, t_spring + 24, u0, u0 + 14, face)
            panel(48, t_spring + 24, u1 - 14, u1, face)
    for face in ("W", "E"):
        panel(t_spring + Tw // 2 + 12, spring + 30, 14, D - 14, face)
    # spandrel figures: a winged-victory-like abstract relief over the main arch
    for z in (0, D - 1):
        for side in (-1, 1):
            for k in range(26):
                y = spring + Wa // 2 + 6 + k // 2
                xx = int(cx + side * (Wa / 2 + 8 + k))
                A[y:y + 3, z, xx:xx + 2] = relief
    # --- entablature: frieze, deep cornice with a shadow line, attic with shields, top cornice
    ce = H - 62
    A[ce - 14:ce, :, :][A[ce - 14:ce, :, :] != 0] = rust          # frieze
    for y in range(ce - 13, ce - 1, 4):
        A[y, 0, ::6] = relief
        A[y, D - 1, ::6] = relief
    A[ce:ce + 5, :, :] = trim                                       # cornice (projecting via the shadow row)
    A[ce, 0, :] = A[ce, D - 1, :] = shadow
    A[ce, :, 0] = A[ce, :, W - 1] = shadow
    # attic: shields every 22 blocks on the long fronts
    for z in (0, D - 1):
        for xc in range(18, W - 10, 22):
            for yy in range(ce + 14, ce + 40):
                for xx in range(xc - 8, xc + 9):
                    d = math.hypot(xx - xc, (yy - (ce + 27)) * 1.0)
                    if d < 8:
                        A[yy, z, xx] = trim if d > 6.2 else (relief if (xx + yy) % 3 else body)
    A[H - 7:H - 2, :, :] = trim                                     # top cornice
    A[H - 7, 0, :] = A[H - 7, D - 1, :] = shadow
    A[H - 7, :, 0] = A[H - 7, :, W - 1] = shadow
    A[H - 2:H, 3:D - 3, 3:W - 3] = body                             # roof
    A[H - 2:H, 6:D - 6, 6:W - 6][A[H - 2:H, 6:D - 6, 6:W - 6] == body] = rust
    # floor of the passages = the road; leave row 0 open for the ground painter
    return A


def triumphal_size(W=280, D=100, H=260, **_):
    return (H, D, W)


# ================================================================ desert pyramid school (金字塔教学楼)
PYR_B, PYR_H = 560, 360


def pyramid(rng, tx0, tz0, tx1, tz1, Bw=PYR_B, H=PYR_H):
    """One tile [tx0, tx1) x [tz0, tz1) of a giant stepped pyramid that is a
    school: smooth sandstone casing with ridge lines, a continuous glazed
    classroom band every 40 blocks of height (lit at dusk), a gold capstone and
    a tall recessed portal in the middle of the south face."""
    casing, ridge, back = B("smooth_sandstone"), B("cut_sandstone"), B("brown_terracotta")
    glass, lit, gold = B("orange_stained_glass"), B("ochre_froglight"), B("gold_block")
    dark, frame = B("red_sandstone"), B("chiseled_sandstone")
    m = 1
    x0, z0, x1, z1 = tx0 - m, tz0 - m, tx1 + m, tz1 + m
    zs, xs = np.mgrid[z0:z1, x0:x1]
    c = Bw / 2
    dx, dz = np.abs(xs + 0.5 - c), np.abs(zs + 0.5 - c)
    d = np.maximum(dx, dz)
    hy = H + 2
    Y = np.arange(hy)[:, None, None]
    half = c * (1 - Y / H)
    M = (d[None] < half) & (Y < H)
    E1 = M.copy()
    E1[:, 1:, :] &= M[:, :-1, :]
    E1[:, :-1, :] &= M[:, 1:, :]
    E1[:, :, 1:] &= M[:, :, :-1]
    E1[:, :, :-1] &= M[:, :, 1:]
    top_open = np.zeros_like(M)
    top_open[:-1] = M[:-1] & ~M[1:]
    outer = (M & ~E1) | top_open
    E2 = E1 & ~top_open
    inner = E2.copy()
    for k in range(1, 8):                                     # an 8-thick shell, hollow inside
        inner[:, 1:, :] &= E2[:, :-1, :]
        inner[:, :-1, :] &= E2[:, 1:, :]
        inner[:, :, 1:] &= E2[:, :, :-1]
        inner[:, :, :-1] &= E2[:, :, 1:]
        E2 = inner.copy()
    A = np.zeros(M.shape, np.uint16)
    A[M & ~inner] = back
    A[outer] = casing
    # ridge lines along the four arrises
    ar = outer & (np.abs(dx - dz)[None] < 2.0)
    A[ar] = ridge
    # glazed classroom bands: 6 rows every 40, solid sandstone mullions every 24
    band = ((Y % 40) >= 30) & ((Y % 40) < 36) & (Y < H - 50) & (Y > 20)
    u = np.where(dx >= dz, zs, xs)[None]
    gl = outer & band & (np.mod(u, 24) >= 4) & ~ar
    A[gl] = glass
    behind = (M & ~outer) & band & ~inner
    on = (np.mod(u // 24 + Y // 40, 3) == 0)
    A[behind & on] = lit
    A[outer & ((Y % 40) == 29) & (Y < H - 50) & (Y > 20)] = frame          # sill line under each band
    # capstone
    A[(Y >= H - 26) & M] = gold
    # the portal: south face centre, 70 wide at the bottom narrowing to 46 at 96 high, 16 deep
    pw = np.clip(35 - (Y / 96) * 12, 0, None)
    por = (np.abs(xs + 0.5 - c)[None] < pw) & (Y < 96) & ((zs + 0.5)[None] > Bw - 30 - (Y * 0.0)) & M
    A[por] = 0
    rim = (np.abs(np.abs(xs + 0.5 - c)[None] - pw) < 2) & (Y < 98) & M & ((zs + 0.5)[None] > Bw - 30)
    A[rim & (A != 0)] = frame
    back_wall = (np.abs(xs + 0.5 - c)[None] < pw) & (Y < 96) & (np.abs(zs + 0.5 - (Bw - 30))[None] < 1)
    A[back_wall] = np.where((Y % 8 < 6) & (np.mod(xs, 6)[None] != 0), glass, dark)[back_wall]
    A[(np.abs(xs + 0.5 - c)[None] < pw) & (Y == 0) & ((zs + 0.5)[None] > Bw - 30)] = casing
    return A[:, m:-m, m:-m]


def pyramid_tile_size(tx0, tz0, tx1, tz1, H=PYR_H):
    return (H + 2, tz1 - tz0, tx1 - tx0)


def obelisk(rng, w=8, h=120):
    """A tapering obelisk with a gold pyramidion, on a stepped base."""
    n = w + 8
    A = np.zeros((h + 10, n, n), np.uint16)
    A[0:2, :, :] = B("cut_sandstone")
    A[2:4, 2:n - 2, 2:n - 2] = B("chiseled_sandstone")
    c = n / 2
    for y in range(4, h + 4):
        hw = (w / 2) * (1 - 0.35 * (y - 4) / h)
        lo, hi = int(round(c - hw)), int(round(c + hw))
        A[y, lo:hi, lo:hi] = B("smooth_sandstone") if (y // 12) % 4 else B("cut_red_sandstone")
    for k in range(6):
        hw = max(0.6, (w / 2) * 0.65 * (1 - k / 6))
        lo, hi = int(round(c - hw)), int(round(c + hw))
        A[h + 4 + k, lo:max(lo + 1, hi), lo:max(lo + 1, hi)] = B("gold_block")
    return A


def palm(rng, h=None):
    """A date palm: a leaning trunk and drooping fronds (persistent leaves)."""
    h = int(h or rng.integers(12, 20))
    n = 21
    A = np.zeros((h + 6, n, n), np.uint16)
    c = n // 2
    lean = rng.uniform(-0.25, 0.25, 2)
    log = B("jungle_log[axis=y]")
    leaf = B("jungle_leaves[distance=1,persistent=true,waterlogged=false]")
    x, z = float(c), float(c)
    for y in range(h):
        x += lean[0] * (y / h)
        z += lean[1] * (y / h)
        A[y, int(round(z)), int(round(x))] = log
    tx, tz = int(round(x)), int(round(z))
    A[h, tz, tx] = leaf
    for a in range(8):
        ang = a * math.pi / 4
        for k in range(1, 8):
            yy = h + 1 - (k * k) // 12
            zz, xx = int(round(tz + k * math.sin(ang))), int(round(tx + k * math.cos(ang)))
            if 0 <= zz < n and 0 <= xx < n and 0 <= yy < A.shape[0]:
                A[yy, zz, xx] = leaf
    return A
