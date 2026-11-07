"""Facade generators.

A facade is a uint16 array F[y, u, d]: y up, u along the wall, d = depth into
the building (d=0 is the outermost layer, reserved for things that stick out:
lettering, AC units, fins).  0 = leave empty.  Every style is a single
floor x bay module tiled over the whole wall, plus overlays."""
from __future__ import annotations

import numpy as np

from anvil import B
import font

AC = B("iron_block")              # 空调外机
LAUNDRY = [B(c + "_wool") for c in ("white", "light_blue", "pink", "yellow", "red", "blue", "lime", "orange")]


def _tile(module, H, W, yoff=0, uoff=0):
    fh, bw, _ = module.shape
    ny = -(-(H + yoff) // fh)
    nu = -(-(W + uoff) // bw)
    return np.tile(module, (ny, nu, 1))[yoff:yoff + H, uoff:uoff + W].copy()


def _light(F, sc, rng, d_glass, d_back, frac):
    """Some windows lit (froglight behind the glass) for night views."""
    if frac <= 0:
        return
    m = F[:, :, d_glass] == sc.glass
    r = rng.random(m.shape) < frac
    # light whole windows: spread along u by smoothing with neighbours
    r = r | np.roll(r, 1, 1) | np.roll(r, -1, 1)
    sel = m & r & (F[:, :, d_back] == sc.back)
    F[:, :, d_back][sel] = sc.lit


def corridor(H, W, sc, rng, fh=4, bay=10, lit=0.02, accent_every=0):
    """外廊式: open corridor with parapet + columns, classroom doors & high windows."""
    D = 6
    M = np.zeros((fh, bay, D), np.uint16)
    M[0, :, 1] = sc.band
    M[1, :, 1] = sc.rail
    M[1:, 0, 1] = sc.column
    M[0, :, 2:4] = sc.floor
    M[:, :, 4] = sc.wall
    M[1:3, 2:4, 4] = sc.door
    M[2:fh, 5:bay - 1, 4] = sc.glass
    M[:, :, 5] = sc.wall
    M[:, :, 5][M[:, :, 4] == sc.glass] = sc.back
    M[:, :, 5][M[:, :, 4] == sc.door] = sc.door
    F = _tile(M, H, W, 0, bay // 2)
    if accent_every:
        for y in range(0, H, fh * accent_every):
            F[y + 1:y + 2, :, 1] = sc.accent
    _light(F, sc, rng, 4, 5, lit)
    return F


def windows(H, W, sc, rng, fh=4, bay=8, lit=0.02, pilaster=True, ac=0.15, accent_every=0,
            win=(1, None), sill=True):
    """外窗式: punched windows recessed one block, optional pilasters + AC units."""
    D = 4
    M = np.zeros((fh, bay, D), np.uint16)
    M[:, :, 1] = sc.wall
    M[0, :, 1] = sc.band
    a, b = win
    b = bay - 1 if b is None else b
    M[2:fh, a:b, 1] = 0
    M[2:fh, a:b, 2] = sc.glass
    M[:, :, 2][M[:, :, 2] == 0] = sc.wall
    M[:, :, 3] = sc.wall
    M[:, :, 3][M[:, :, 2] == sc.glass] = sc.back
    if pilaster:
        M[:, 0, 0] = sc.column
    if sill:
        M[1, a:b, 0] = 0
    F = _tile(M, H, W, 0, bay // 2)
    if accent_every:
        for y in range(0, H, fh * accent_every):
            F[y:y + 2, :, 1] = sc.accent
            F[y:y + 2, :, 0][F[y:y + 2, :, 0] == sc.column] = sc.accent
    if ac:
        # one AC unit under some windows, sitting on the outer layer
        ys = np.arange(fh + 1, H - 1, fh)
        us = np.arange(bay // 2 + a + 1, W - 1, bay) - 0
        us = us[us < W]
        for y in ys:
            pick = us[rng.random(len(us)) < ac]
            F[y, pick, 0] = AC
    _light(F, sc, rng, 2, 3, lit)
    return F


def ribbon(H, W, sc, rng, fh=4, mull=4, lit=0.02, spandrel=None, fins=0):
    """Continuous ribbon windows between solid spandrel bands; optional fins."""
    D = 4
    M = np.zeros((fh, mull, D), np.uint16)
    sp = sc.band if spandrel is None else spandrel
    M[0:2, :, 1] = sp
    M[2:, :, 1] = sc.glass
    M[2:, 0, 1] = sc.column
    M[:, :, 2] = sc.wall
    M[2:, 1:, 2] = sc.back
    M[:, :, 3] = sc.wall
    F = _tile(M, H, W)
    if fins:
        F[:, ::fins, 0] = sc.accent
    _light(F, sc, rng, 1, 2, lit)
    return F


def curtain(H, W, sc, rng, fh=4, mull=3, lit=0.01):
    """玻璃幕墙: full glass grid."""
    D = 3
    M = np.zeros((fh, mull, D), np.uint16)
    M[:, :, 1] = sc.glass
    M[0, :, 1] = sc.column
    M[:, 0, 1] = sc.column
    M[:, :, 2] = sc.back
    F = _tile(M, H, W)
    _light(F, sc, rng, 1, 2, lit)
    return F


def balcony(H, W, sc, rng, fh=4, bay=6, lit=0.03, laundry=0.25, ac=0.4):
    """宿舍阳台: balcony per room, divider walls, clothes hanging out to dry."""
    D = 5
    M = np.zeros((fh, bay, D), np.uint16)
    M[0, :, 0] = sc.band
    M[1, :, 0] = sc.rail
    M[0, :, 1] = sc.floor
    M[:, 0, 0:2] = sc.wall
    M[:, :, 2] = sc.wall
    M[1:fh, 2:4, 2] = sc.glass                 # balcony door
    M[2:fh, 4:bay, 2] = sc.glass               # window
    M[:, :, 3] = sc.wall
    M[:, :, 3][M[:, :, 2] == sc.glass] = sc.back
    M[:, :, 4] = sc.wall
    F = _tile(M, H, W, 0, 0)
    ys = np.arange(fh + 2, H - 1, fh)
    for y in ys:
        for u0 in range(1, W - bay, bay):
            r = rng.random()
            if r < laundry:
                k = rng.integers(1, 4)
                cols = u0 + 1 + rng.permutation(bay - 2)[:k]
                F[y, cols, 1] = LAUNDRY[rng.integers(len(LAUNDRY))]
            elif r < laundry + ac * 0.5:
                F[y - 1, u0 + 1, 1] = AC
    _light(F, sc, rng, 2, 3, lit)
    return F


def stair(H, W, sc, rng, fh=4, lit=0.0):
    """楼梯间: solid accent wall with a vertical line of small landing windows."""
    D = 3
    F = np.zeros((H, W, D), np.uint16)
    F[:, :, 1] = sc.accent
    F[:, :, 2] = sc.accent
    c = W // 2
    for y in range(fh // 2 + 1, H - 2, fh):
        F[y:y + 2, c - 1:c + 1, 1] = sc.glass
        F[y:y + 2, c - 1:c + 1, 2] = sc.back
    F[:, 0, 0] = sc.wall
    F[:, W - 1, 0] = sc.wall
    return F


def blank(H, W, sc, rng, mat=None, grid=0):
    D = 2
    F = np.zeros((H, W, D), np.uint16)
    F[:, :, 1] = sc.wall if mat is None else mat
    if grid:
        F[::grid, :, 1] = sc.band
        F[:, ::grid, 1] = sc.band
    return F


STYLES = {"corridor": corridor, "windows": windows, "ribbon": ribbon, "curtain": curtain,
          "balcony": balcony, "stair": stair, "blank": blank}


# ---------------------------------------------------------------- overlays
def letters(F, s, y_top, u_center, px, fg, bg=None, gap=None, mirror=False, vertical=False,
            pad=None, bold=0, d_fg=0, d_bg=1):
    """Paint text onto a facade.  y_top counts from the top of F."""
    gap = max(1, px // 6) if gap is None else gap
    bm = font.text(s, px, gap, bold=bold, vertical=vertical)
    if mirror:
        bm = bm[:, ::-1]
    h, w = bm.shape
    pad = max(2, px // 4) if pad is None else pad
    H, W, _ = F.shape
    y1 = H - y_top            # F row index of the top edge (F is bottom-up)
    y0 = y1 - h
    u0 = u_center - w // 2
    if bg is not None:
        ya, yb = max(0, y0 - pad), min(H, y1 + pad)
        ua, ub = max(0, u0 - pad), min(W, u0 + w + pad)
        F[ya:yb, ua:ub, d_bg] = bg
        F[ya:yb, ua:ub, d_fg] = 0
        for d in range(d_bg + 1, F.shape[2]):
            sl = F[ya:yb, ua:ub, d]
            sl[sl == 0] = bg
    bmu = bm[::-1]            # rows bottom-up
    ya, yb = max(0, y0), min(H, y1)
    ua, ub = max(0, u0), min(W, u0 + w)
    sub = bmu[ya - y0:yb - y0, ua - u0:ub - u0]
    tgt = F[ya:yb, ua:ub, d_fg]
    tgt[sub] = fg
    return F


# ---------------------------------------------------------------- VibeSchem modules
USE_VIBESCHEM = True
_PANE_CACHE = {}


def _is_pane(F):
    import anvil
    n = len(anvil.all_names())
    lut = _PANE_CACHE.get(n)
    if lut is None:
        lut = np.array(["_pane" in s for s in anvil.all_names()], bool)
        _PANE_CACHE.clear()
        _PANE_CACHE[n] = lut
    return lut[F]


def _light_vs(F, sc, rng, frac, d_back):
    """Some classrooms lit: the dark 'interior' behind a pane becomes a froglight."""
    if frac <= 0:
        return
    cand = (F[:, :, d_back] == sc.back) & _is_pane(F[:, :, d_back - 1])
    r = rng.random(cand.shape) < frac
    r = r | np.roll(r, 1, 1) | np.roll(r, -1, 1) | np.roll(r, 2, 1)
    F[:, :, d_back][cand & r] = sc.lit


def vibeschem_face(style, H, W, sc, rng, side, lit=0.02, accent_every=0, ac=0.15, pilaster=True,
                   laundry=0.25, spandrel=None, fins=0, **_ignored):
    """Facade tiled from the VibeSchem-compiled module for this style/scheme/side."""
    import vibeschem
    M = vibeschem.module(style, sc.name, side)
    fh, bay, D = M.shape
    uoff = bay // 2 if style in ("corridor", "windows") else 0
    F = _tile(M, H, W, 0, uoff)
    u = (np.arange(W) + uoff) % bay
    if style == "corridor":
        if accent_every:
            for y in range(1, H, fh * accent_every):
                row = F[y, :, 1]
                row[row == sc.rail] = sc.accent
        _light_vs(F, sc, rng, lit, 5)
    elif style == "windows":
        if not pilaster:
            F[:, u == 0, 0] = 0
        if accent_every:
            for y in range(0, H, fh * accent_every):
                F[y:y + 2, :, 1] = sc.accent
                F[y, :, 0][F[y, :, 0] != 0] = sc.accent
        if ac:
            for y in range(fh + 1, H - 1, fh):
                pick = (u == 2) & (rng.random(W) < ac)
                F[y, pick, 0] = AC
        _light_vs(F, sc, rng, lit, 3)
    elif style == "balcony":
        for y in range(fh + 2, H - 1, fh):
            for u0 in np.nonzero(u == 1)[0]:
                r = rng.random()
                if r < laundry:
                    cols = u0 + rng.permutation(bay - 2)[:int(rng.integers(1, 4))]
                    cols = cols[cols < W]
                    F[y, cols, 1] = LAUNDRY[rng.integers(len(LAUNDRY))]
                elif r < laundry + ac * 0.5 and u0 + 3 < W:
                    F[y - 1, u0 + 3, 1] = AC
        _light_vs(F, sc, rng, lit + 0.01, 3)
    elif style == "ribbon":
        if spandrel is not None:
            F[:, :, 1][F[:, :, 1] == sc.band] = spandrel
        if fins:
            F[:, ::fins, 0] = sc.accent
        _light_vs(F, sc, rng, lit, 2)
    elif style == "curtain":
        _light_vs(F, sc, rng, lit, 2)
    return F


def face(style, H, W, sc, rng, side, **kw):
    if USE_VIBESCHEM and style in ("corridor", "windows", "balcony", "ribbon", "curtain"):
        import vibeschem
        if vibeschem.has_cache():
            return vibeschem_face(style, H, W, sc, rng, side, **kw)
    return STYLES[style](H, W, sc, rng, **kw)
