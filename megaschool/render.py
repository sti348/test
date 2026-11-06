"""Numpy voxel ray tracer for previews (textures from the game, sun shadows,
atmospheric haze).  Slow but dependency-free."""
from __future__ import annotations

import math

import numpy as np

import textures


class Grid:
    def __init__(self, V, x0, z0, y0=-64):
        self.V, self.x0, self.z0, self.y0 = V, x0, z0, y0


def _march(G, o, d, maxdist, tex, alpha_test=True, max_steps=4000):
    """Returns (block, t, axis, stepsign) per ray; block 0 = nothing hit."""
    T, top, side, bot, emi, cut = tex
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
           shadows=True, night=False, tex=None, ss=1):
    """yaw like Minecraft: 0 = +Z (south), 180 = -Z (north); pitch>0 looks down."""
    tex = tex or textures.atlas()
    T, top, side, bot, emi, cut = tex
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
    o = np.broadcast_to(np.array(cam, float), d.shape).copy()
    b, t, ax, step = _march(G, o, d, maxdist, tex)
    hit = b != 0
    col = sky_color(d, night)
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
