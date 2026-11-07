"""Numpy voxel ray tracer for previews (textures from the game, sun shadows,
atmospheric haze).  Slow but dependency-free."""
from __future__ import annotations

import math

import numpy as np

import textures


class Grid:
    """Voxel grid V[y,z,x] whose cell (0,0,0) is world (x0, y0, z0); with
    scale s > 1 every cell stands for an s*s*s block (level of detail)."""

    def __init__(self, V, x0, z0, y0=-64, scale=1):
        self.V, self.x0, self.z0, self.y0, self.scale = V, x0, z0, y0, scale


def _march(G, o, d, maxdist, tex, alpha_test=True, max_steps=4000):
    """Returns (block, t, axis, stepsign) per ray; block 0 = nothing hit."""
    T, top, side, bot, emi, cut, shp = tex
    partial = np.any(shp != np.array([0, 0, 0, 1, 1, 1.0]), axis=1)
    V = G.V
    Y, Z, X = V.shape
    N = len(o)
    # rays that start outside the grid jump to where they enter its bounding box
    lo = np.array([G.x0, G.y0, G.z0], float)
    hi = lo + np.array([X, Y, Z], float)
    with np.errstate(divide="ignore", invalid="ignore"):
        t1 = (lo - o) / d
        t2 = (hi - o) / d
    tn = np.nanmax(np.where(np.isnan(np.minimum(t1, t2)), -np.inf, np.minimum(t1, t2)), axis=1)
    tf = np.nanmin(np.where(np.isnan(np.maximum(t1, t2)), np.inf, np.maximum(t1, t2)), axis=1)
    outside = np.any((o < lo) | (o >= hi), axis=1)
    t_off = np.where(outside & (tn < tf) & (tn > 0), tn + 1e-4, 0.0)
    o = o + d * t_off[:, None]
    with np.errstate(divide="ignore", invalid="ignore"):
        inv = 1.0 / d
    step = np.where(d >= 0, 1, -1).astype(np.int64)
    cell = np.floor(o).astype(np.int64)
    tdelta = np.abs(inv)
    nxt = cell + (step > 0)
    tmax = (nxt - o) * inv
    tmax[~np.isfinite(tmax)] = np.inf
    tdelta[~np.isfinite(tdelta)] = np.inf
    off = np.array([G.x0, G.y0, G.z0])
    hit_b = np.zeros(N, np.int64)
    hit_t = np.full(N, np.inf)
    hit_ax = np.zeros(N, np.int64)
    act = np.arange(N)
    it = 0
    while len(act) and it < max_steps:
        it += 1
        tm = tmax[act]
        ax = np.argmin(tm, axis=1)
        r = np.arange(len(act))
        t = tm[r, ax]
        c = cell[act]
        c[r, ax] += step[act, ax]
        cell[act] = c
        tm[r, ax] += tdelta[act, ax]
        tmax[act] = tm
        lc = c - off
        inb = (lc[:, 0] >= 0) & (lc[:, 0] < X) & (lc[:, 2] >= 0) & (lc[:, 2] < Z) & (lc[:, 1] >= 0) & (lc[:, 1] < Y)
        alive = inb & (t < maxdist)
        b = np.zeros(len(act), np.int64)
        b[alive] = V[lc[alive, 1], lc[alive, 2], lc[alive, 0]]
        h = b != 0
        # partial blocks (slabs, panes, doors...): intersect the ray with the sub-box
        if h.any():
            hi = np.nonzero(h)[0]
            pc = hi[partial[b[hi]]]
            if len(pc):
                box = shp[b[pc]]
                oo = o[act[pc]] - c[pc]
                dd = d[act[pc]]
                with np.errstate(divide="ignore", invalid="ignore"):
                    t1 = (box[:, 0:3] - oo) / dd
                    t2 = (box[:, 3:6] - oo) / dd
                tlo = np.where(np.isnan(np.minimum(t1, t2)), -np.inf, np.minimum(t1, t2))
                thi = np.where(np.isnan(np.maximum(t1, t2)), np.inf, np.maximum(t1, t2))
                tn = tlo.max(axis=1)
                tf = thi.min(axis=1)
                miss = (tn > tf) | (tf < t[pc])
                h[pc[miss]] = False
                ok = pc[~miss]
                tnew = np.maximum(tn[~miss], t[ok])
                axn = np.where(tn[~miss] >= t[ok], tlo[~miss].argmax(axis=1), ax[ok])
                t[ok] = tnew
                ax[ok] = axn
        if alpha_test and h.any():
            hi = np.nonzero(h)[0]
            cand = hi[cut[b[hi]]]
            if len(cand):
                p = o[act[cand]] + d[act[cand]] * t[cand, None]
                a = ax[cand]
                tid = _face_tex(b[cand], a, step[act[cand]], top, side, bot)
                u, v = _uv(p, a, step[act[cand]])
                al = T[tid, v, u, 3]
                h[cand[al < 0.5]] = False
        idx = act[h]
        hit_b[idx] = b[h]
        hit_t[idx] = t[h] + t_off[idx]
        hit_ax[idx] = ax[h]
        keep = (~h) & alive
        act = act[keep]
    return hit_b, hit_t, hit_ax, step


def _face_tex(b, ax, step, top, side, bot):
    tid = side[b].copy()
    isy = ax == 1
    down = step[np.arange(len(b)), 1] < 0
    tid[isy & down] = top[b[isy & down]]
    tid[isy & ~down] = bot[b[isy & ~down]]
    return tid


def _uv(p, ax, step):
    f = p - np.floor(p)
    u = np.where(ax == 0, f[:, 2], f[:, 0])
    v = np.where(ax == 1, f[:, 2], 1 - f[:, 1])
    flip = ((ax == 0) & (step[np.arange(len(p)), 0] > 0)) | ((ax == 2) & (step[np.arange(len(p)), 2] < 0))
    u = np.where(flip, 1 - u, u)
    ui = np.clip((u * 16).astype(np.int64), 0, 15)
    vi = np.clip((v * 16).astype(np.int64), 0, 15)
    return ui, vi


DUSK_SUN = np.array([-0.97, 0.13, 0.20])
DUSK_SUN = DUSK_SUN / np.linalg.norm(DUSK_SUN)


def sky_dusk(d):
    """Sunset sky: hot orange near the sun on the western horizon, violet away
    from it, deep blue overhead."""
    up = np.clip(d[:, 1], -0.1, 1)[:, None]
    toward = np.clip(d @ DUSK_SUN, -1, 1)[:, None]
    warm = np.array([1.00, 0.52, 0.24])
    rose = np.array([0.78, 0.46, 0.52])
    violet = np.array([0.36, 0.30, 0.48])
    zen = np.array([0.10, 0.13, 0.30])
    w = np.clip((toward + 0.2) / 1.2, 0, 1) ** 2.2
    hor = violet * (1 - w) + (rose * 0.4 + warm * 0.6) * w
    hor = hor * (1 - 0.35 * np.clip(-toward, 0, 1)) + rose * 0.15 * (1 - w)
    k = np.clip(up / 0.45, 0, 1) ** 0.7
    col = hor * (1 - k) + zen * k
    glow = np.clip(toward, 0, 1) ** 40
    return np.clip(col + glow * np.array([1.0, 0.85, 0.5]) * 1.2, 0, 1.4)


def sky_twilight(d):
    """Twilight-Forest-like sky: violet dome, lavender afterglow low in the west, stars."""
    up = np.clip(d[:, 1], -0.1, 1)[:, None]
    west = np.clip(d @ DUSK_SUN, -1, 1)[:, None]
    hor = np.array([0.66, 0.58, 0.86])
    glow = np.array([0.92, 0.66, 0.80])
    mid = np.array([0.40, 0.34, 0.72])
    zen = np.array([0.15, 0.13, 0.36])
    w = np.clip((west + 0.3) / 1.3, 0, 1) ** 3
    h = hor * (1 - w) + glow * w
    k1 = np.clip(up / 0.25, 0, 1)
    k2 = np.clip((up - 0.25) / 0.6, 0, 1)
    col = h * (1 - k1) + mid * k1
    col = col * (1 - k2) + zen * k2
    # stars: hash the direction on a fine grid
    g = np.floor(d * 700).astype(np.int64)
    hsh = (g[:, 0] * 73856093) ^ (g[:, 1] * 19349663) ^ (g[:, 2] * 83492791)
    star = ((hsh % 997) == 0) & (d[:, 1] > 0.12)
    col = np.where(star[:, None], np.array([0.95, 0.93, 1.0]), col)
    return col


def _render_medium(G, o, d, maxdist, tex, mode, haze, H, W, h, w, ss):
    """Nether (no sky, red haze, lava and fire glowing) or underwater (water is
    rendered as blue-green fog, not as cubes)."""
    T, top, side, bot, emi, cut, shp = tex
    b, t, ax, step = _march(G, o, d, maxdist, tex)
    hit = b != 0
    if mode == "nether":
        bg, amb, fogc, gain = np.array([0.22, 0.04, 0.03]), np.array([0.62, 0.36, 0.30]), np.array([0.34, 0.07, 0.05]), 0.9
    else:
        bg, amb, fogc, gain = np.array([0.02, 0.09, 0.16]), np.array([0.30, 0.42, 0.58]), np.array([0.03, 0.16, 0.26]), 0.9
    col = np.tile(bg, (len(d), 1))
    hi = np.nonzero(hit)[0]
    p = o[hi] + d[hi] * t[hi, None]
    tid = _face_tex(b[hi], ax[hi], step[hi], top, side, bot)
    u, v = _uv(p, ax[hi], step[hi])
    c = T[tid, v, u, :3].astype(np.float64)
    a = ax[hi]
    sgn = step[hi, a]
    nrm = np.zeros((len(hi), 3))
    nrm[np.arange(len(hi)), a] = -sgn
    shade = np.where(a == 1, np.where(sgn < 0, 1.0, 0.5), np.where(a == 0, 0.6, 0.8))
    light3 = amb[None] * shade[:, None]
    if not hasattr(G, "glow"):
        G.glow = glow_field(G.V, emi)
    F, cell = G.glow
    q = ((p + nrm * 0.6) - np.array([G.x0, G.y0, G.z0])) / cell
    qi = np.clip(q.astype(np.int64), 0, np.array(F.shape)[[2, 0, 1]] - 1)
    gl = F[qi[:, 1], qi[:, 2], qi[:, 0]]
    light3 = light3 + np.array([1.0, 0.62, 0.32])[None] * np.clip(gl * gain, 0, 1.4)[:, None]
    e = emi[b[hi]]
    light3 = np.where(e[:, None], np.array([1.3, 1.1, 0.9])[None], light3)
    c = c * light3
    f = 1 - np.exp(-haze * t[hi])
    f = np.where(e, f * 0.5, f)
    c = c * (1 - f[:, None]) + fogc * f[:, None]
    col[hi] = c
    img = (np.clip(col, 0, 1) * 255).astype(np.uint8).reshape(H, W, 3)
    if ss > 1:
        img = img.reshape(h, ss, w, ss, 3).mean(axis=(1, 3)).astype(np.uint8)
    return img


def glow_field(V, emi, cell=4, radius=3):
    """Cheap stand-in for block light: emissive blocks counted per 4^3 cell and
    box-blurred.  Returns (field, cell)."""
    Y, Z, X = V.shape
    pz, px, py = (-Z) % cell, (-X) % cell, (-Y) % cell
    E = emi[V]
    if py or pz or px:
        E = np.pad(E, ((0, py), (0, pz), (0, px)))
    Yc, Zc, Xc = E.shape[0] // cell, E.shape[1] // cell, E.shape[2] // cell
    G = E.reshape(Yc, cell, Zc, cell, Xc, cell).sum(axis=(1, 3, 5)).astype(np.float32)
    for ax in range(3):
        for _ in range(2):
            c = np.cumsum(np.pad(G, [(radius + 1, radius) if a == ax else (0, 0) for a in range(3)]), axis=ax)
            hi = np.take(c, np.arange(2 * radius + 1, c.shape[ax]), axis=ax)
            lo = np.take(c, np.arange(0, c.shape[ax] - 2 * radius - 1), axis=ax)
            G = (hi - lo) / (2 * radius + 1)
    return G, cell


def sky_color(d, night=False):
    t = np.clip(d[:, 1], -0.2, 1)[:, None]
    if night:
        hor = np.array([0.08, 0.10, 0.16])
        zen = np.array([0.01, 0.015, 0.04])
    else:
        hor = np.array([0.80, 0.86, 0.93])
        zen = np.array([0.42, 0.60, 0.88])
    k = np.clip(t, 0, 1) ** 0.6
    return hor * (1 - k) + zen * k


def render(G, cam, yaw, pitch, w=960, h=540, fov=70, maxdist=1100, haze=0.0012, sun=(0.45, 0.8, 0.35),
           shadows=True, night=False, tex=None, ss=1, dusk=False, twilight=False, mode=None):
    """yaw like Minecraft: 0 = +Z (south), 180 = -Z (north); pitch>0 looks down."""
    tex = tex or textures.atlas()
    T, top, side, bot, emi, cut, shp = tex
    W, H = w * ss, h * ss
    yr, pr = math.radians(yaw), math.radians(pitch)
    fwd = np.array([-math.sin(yr) * math.cos(pr), -math.sin(pr), math.cos(yr) * math.cos(pr)])
    right = np.array([-math.cos(yr), 0.0, -math.sin(yr)])
    up = np.cross(right, fwd)
    up /= np.linalg.norm(up)
    right = np.cross(fwd, up)
    th = math.tan(math.radians(fov) / 2)          # vertical fov like Minecraft
    ys, xs = np.mgrid[0:H, 0:W]
    px = (2 * (xs + 0.5) / W - 1) * th * W / H
    py = (1 - 2 * (ys + 0.5) / H) * th
    d = fwd[None] + px.reshape(-1, 1) * right[None] + py.reshape(-1, 1) * up[None]
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    s_ = getattr(G, "scale", 1)
    org = np.array([G.x0, G.y0, G.z0], float)
    cam_g = (np.array(cam, float) - org) / s_ + org             # camera in grid units
    o = np.broadcast_to(cam_g, d.shape).copy()
    haze = haze * s_
    maxdist = maxdist / s_
    if mode in ("nether", "underwater"):
        return _render_medium(G, o, d, maxdist, tex, mode, haze, H, W, h, w, ss)
    b, t, ax, step = _march(G, o, d, maxdist, tex)
    hit = b != 0
    col = sky_twilight(d) if twilight else (sky_dusk(d) if dusk else sky_color(d, night))
    hi = np.nonzero(hit)[0]
    p = o[hi] + d[hi] * t[hi, None]
    tid = _face_tex(b[hi], ax[hi], step[hi], top, side, bot)
    u, v = _uv(p, ax[hi], step[hi])
    c = T[tid, v, u, :3].astype(np.float64)
    a = ax[hi]
    sgn = step[hi, a]
    nrm = np.zeros((len(hi), 3))
    nrm[np.arange(len(hi)), a] = -sgn
    shade = np.where(a == 1, np.where(sgn < 0, 1.0, 0.5), np.where(a == 0, 0.6, 0.8))
    if twilight:
        amb = np.array([0.72, 0.68, 0.92])
        light3 = amb[None] * shade[:, None]
        # soft sky occlusion: one ray toward the bright western sky
        so_dir = np.array([-0.62, 0.70, 0.35])
        so_dir = so_dir / np.linalg.norm(so_dir)
        so = p + nrm * 1e-3 + so_dir * 1e-3
        sb, _, _, _ = _march(G, so, np.broadcast_to(so_dir, so.shape).copy(), 700, tex)
        occl = np.where(sb == 0, 1.0, 0.72)
        lam = np.clip(nrm @ DUSK_SUN, 0, 1)
        light3 = light3 * occl[:, None] + np.array([0.30, 0.16, 0.22])[None] * lam[:, None]
        if not hasattr(G, "glow"):
            G.glow = glow_field(G.V, emi)
        F, cell = G.glow
        q = ((p + nrm * 0.6) - np.array([G.x0, G.y0, G.z0])) / cell
        qi = np.clip(q.astype(np.int64), 0, np.array(F.shape)[[2, 0, 1]] - 1)
        gl = F[qi[:, 1], qi[:, 2], qi[:, 0]]
        light3 = light3 + np.array([1.0, 0.74, 0.45])[None] * np.clip(gl * 0.7, 0, 1.2)[:, None]
        e = emi[b[hi]]
        light3 = np.where(e[:, None], np.array([1.3, 1.15, 0.95])[None], light3)
        c = c * light3
        dist = t[hi]
        f = 1 - np.exp(-haze * dist)
        hd = np.c_[d[hi, 0], np.full(len(hi), 0.04), d[hi, 2]]
        fogc = sky_twilight(hd / np.linalg.norm(hd, axis=1, keepdims=True)) * 0.95
        f = np.where(e, f * 0.4, f)
        c = c * (1 - f[:, None]) + fogc * f[:, None]
        col[hi] = c
        img = (np.clip(col, 0, 1) * 255).astype(np.uint8).reshape(H, W, 3)
        if ss > 1:
            img = img.reshape(h, ss, w, ss, 3).mean(axis=(1, 3)).astype(np.uint8)
        return img
    if dusk:
        sd = DUSK_SUN
        lam = np.clip(nrm @ sd, 0, 1)
        amb = np.array([0.62, 0.56, 0.76])
        sunc = np.array([1.15, 0.62, 0.32])
        lit = np.ones(len(hi), bool)
        if shadows:
            so = p + nrm * 1e-3 + sd * 1e-3
            sb, _, _, _ = _march(G, so, np.broadcast_to(sd, so.shape).copy(), 900, tex)
            lit = sb == 0
        light3 = amb[None] * (0.55 * shade)[:, None] + sunc[None] * (lam * lit)[:, None] * 0.9
        if not hasattr(G, "glow"):
            G.glow = glow_field(G.V, emi)
        F, cell = G.glow
        q = ((p + nrm * 0.6) - np.array([G.x0, G.y0, G.z0])) / cell
        qi = np.clip(q.astype(np.int64), 0, np.array(F.shape)[[2, 0, 1]] - 1)
        gl = F[qi[:, 1], qi[:, 2], qi[:, 0]]
        light3 = light3 + np.array([1.0, 0.72, 0.42])[None] * np.clip(gl * 0.55, 0, 1.1)[:, None]
        e = emi[b[hi]]
        light3 = np.where(e[:, None], np.array([1.25, 1.1, 0.9])[None], light3)
        c = c * light3
        dist = t[hi]
        f = 1 - np.exp(-haze * dist)
        fogc = sky_dusk(np.c_[d[hi, 0], np.full(len(hi), 0.02), d[hi, 2]] /
                        np.linalg.norm(np.c_[d[hi, 0], np.full(len(hi), 0.02), d[hi, 2]], axis=1, keepdims=True)) * 0.85
        f = np.where(e, f * 0.45, f)
        c = c * (1 - f[:, None]) + fogc * f[:, None]
        col[hi] = c
        img = (np.clip(col, 0, 1) * 255).astype(np.uint8).reshape(H, W, 3)
        if ss > 1:
            img = img.reshape(h, ss, w, ss, 3).mean(axis=(1, 3)).astype(np.uint8)
        return img
    if night:
        light = 0.18 * shade
    else:
        sd = np.array(sun, float)
        sd /= np.linalg.norm(sd)
        lam = np.clip(nrm @ sd, 0, 1)
        light = 0.55 * shade + 0.55 * lam
        if shadows:
            so = p + nrm * 1e-3 + sd * 1e-3
            sb, _, _, _ = _march(G, so, np.broadcast_to(sd, so.shape).copy(), 700, tex)
            lit = sb == 0
            light = np.where(lit, light, 0.55 * shade * 0.75)
    e = emi[b[hi]]
    light = np.where(e, 1.0, light)
    c = c * light[:, None]
    # haze toward horizon colour
    dist = t[hi]
    f = 1 - np.exp(-haze * dist)
    fogc = sky_color(np.tile([[0, 0.02, 0]], (len(hi), 1)), night)
    if night:
        f = np.where(e, f * 0.4, f)
    c = c * (1 - f[:, None]) + fogc * f[:, None]
    col[hi] = c
    img = (np.clip(col, 0, 1) ** (1 / 1.0) * 255).astype(np.uint8).reshape(H, W, 3)
    if ss > 1:
        img = img.reshape(h, ss, w, ss, 3).mean(axis=(1, 3)).astype(np.uint8)
    return img
