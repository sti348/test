"""Render preview images of the campus (needs build/tex from a client jar).

  python3 preview.py <out_dir> [view ...]"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
from PIL import Image

import anvil
import render
import textures

VIEWS = {
    # name: (rect x0, z0, x1, z1), camera (x, y, z), yaw, pitch, fov, kwargs
    # yaw like Minecraft: 0 south, 90 west, 180 north, 270 east; negative pitch looks up.
    # Dusk lighting is the default (see main()).
    "gate": ((-900, 0, 900, 1100), (0.5, -58.4, 1065.5), 180, -12, 75, {}),
    "avenue": ((-900, 0, 900, 1100), (8, -58.4, 860), 182, -16, 75, {}),
    "lake": ((-1300, 100, 300, 1000), (-162, -57.2, 742), 100, -9, 78, {}),
    "pool": ((-300, 0, 1000, 1000), (192.5, -45.0, 735.5), 180, 26, 78, {}),
    "auditorium": ((-1000, 300, 0, 1000), (-482, -54.4, 628), 0, -14, 80, {}),
    "greenhouse": ((0, 300, 1200, 1000), (481.5, -57.4, 838), 180, -6, 78, {}),
    "buses": ((-1200, 300, 400, 1100), (-640, -56.4, 1008), 160, -10, 78, {}),
    "street": ((-400, 700, 400, 1100), (30, -57.4, 1052), 250, -4, 70, {}),
    "canyon": ((-1000, -900, 1000, 600), (113, -58.4, 300), 180, -20, 75, {}),
    "endless": ((-1200, -1400, 1200, -300), (40, -52, -850), 230, -16, 80, {}),
    "watertower": ((-700, -2048, 700, -1300), (0.5, -58.4, -1690), 180, -32, 78, {}),
    "aerial": ((-1300, -1100, 1300, 1100), (260, 230, 1160), 192, 22, 70, dict(haze=0.0009)),
    "grove": ((-1700, -1100, -500, 100), (-1213.5, -57.6, -495.5), 328, -6, 80, {}),
    "night": ((-900, 0, 900, 1100), (0.5, -58.4, 1065.5), 180, -12, 75, dict(night=True)),
    "facade": ((-100, 300, 800, 1100), (236, -52, 884), 200, -18, 70, {}),
    "corridor": ((-100, 300, 800, 1100), (178.5, 14.6, 686.5), 270, 2, 80, {}),
}


def region_views():
    """Views of the regions beyond the campus (tall: they pick their own y range)."""
    import regions as R
    px, pz = R.GATE_OW
    gx, gz = R.GATE_NE
    ax, az = R.ACADEMY_NE
    bx, bz, br = R.SPHERES[0][1:]
    bot = R.SEABED_DEEP - 20                     # bottom of the big sphere
    floor = bot + int(br * 0.45) + 1
    ex, ez, eR, etop = R.END_ISLAND[:4]
    return {
        "r_portal": ((px - 260, pz - 260, px + 260, pz + 260), (px + 150, -50, pz + 40), 95, -18, 78,
                     dict(y=(-64, 192))),
        # odd y0 with lod 2 so the sampled layers include the grass at y -61
        "r_sinkhole": ((R.SX - 700, R.SZ - 700, R.SX + 900, R.SZ + 700), (R.SX + 520, 40, R.SZ + 210), 112, 30, 84,
                       dict(y=(-943, 113), lod=2, haze=0.0007)),
        "r_sinkhole_floor": ((R.SX - 330, R.SZ - 330, R.SX + 330, R.SZ + 330), (R.SX + 160, -880, R.SZ + 160), 135, -38, 82,
                             dict(y=(-944, -48), haze=0.0005)),
        "r_archipelago": ((2300, -800, 3700, 1100), (2500, 45, 720), 226, 7, 82,
                          dict(y=(-160, 544), lod=2, haze=0.0005, maxdist=1500)),
        "r_sphere": ((bx - 260, bz - 260, bx + 260, bz + 260), (bx + 40, bot + br - 10, bz + 200), 190, -6, 84,
                     dict(y=(bot - 32, bot + 2 * br + 32), mode="underwater", no_water=True, haze=0.004)),
        "r_sphere_in": ((bx - 140, bz - 140, bx + 140, bz + 140), (bx + 8, floor + 14, bz + 100), 182, -6, 84,
                        dict(y=(bot - 8, bot + 2 * br + 8), mode="underwater", no_water=True, haze=0.002)),
        "r_sky": ((-900, -3820, 700, -2380), (950, 560, -1850), 142, -24, 78,
                  dict(y=(-63, 1920), lod=3, haze=0.00022, maxdist=2800)),
        "r_end": ((ex - 320, ez - 320, ex + 320, ez + 320), (ex + 230, etop + 40, ez + 250), 137, 10, 80,
                  dict(y=(etop - 400, etop + 336), haze=0.0005)),
        "r_nether_gate": ((gx - 320, gz - 320, gx + 320, gz + 320), (gx + 150, 74, gz + 30), 98, -14, 80,
                          dict(dim="the_nether", y=(0, 640), mode="nether")),
        "r_nether_academy": ((ax - 320, az - 320, ax + 320, az + 320), (ax + 40, 80, az + 230), 188, -16, 80,
                             dict(dim="the_nether", y=(0, 640), mode="nether")),
    }


def compose_lod(world, x0, z0, dx, dz, y0, y1, s=1):
    """Compose a volume band by band; with s > 1 keep every s-th voxel."""
    m = world.maps(x0, z0, dx, dz)
    cache = {}
    parts = []
    step = 256 if s == 1 else s * max(1, 48 // s)          # thin bands at low detail: wide views stay in memory
    for a in range(y0, y1, step):
        b = min(y1, a + step)
        V = world.compose(x0, z0, dx, dz, a, b, m, cache)
        parts.append(V[::s, ::s, ::s] if s > 1 else V)
    return np.concatenate(parts, axis=0)


def main(out, names, w=1600, h=900, ss=1):
    import os as _o
    w, h = int(_o.environ.get("PW", w)), int(_o.environ.get("PH", h))
    os.makedirs(out, exist_ok=True)
    import generate
    worlds = generate.build_worlds()
    tex = None
    views = dict(VIEWS, **region_views())
    for n in names:
        rect, cam, yaw, pitch, fov, kw = views[n]
        kw = dict(kw)
        dim = kw.pop("dim", "overworld")
        y0, y1 = kw.pop("y", (-64, 320))
        lod = kw.pop("lod", 1)
        no_water = kw.pop("no_water", False)
        x0, z0, x1, z1 = rect
        t = time.time()
        V = compose_lod(worlds[dim], x0, z0, x1 - x0, z1 - z0, y0, y1, lod)
        if no_water:
            V[np.isin(V, [anvil.B("water"), anvil.B("water[level=8]")])] = 0
        V[V == anvil.B("cave_air")] = 0
        t1 = time.time()
        if tex is None or len(tex[1]) != len(anvil.all_names()):
            tex = textures.atlas()
        if not kw.get("night") and not kw.get("dusk") and not kw.get("mode"):
            kw.setdefault("twilight", True)
        img = render.render(render.Grid(V, x0, z0, y0, lod), cam, yaw, pitch, w=w, h=h, fov=fov, tex=tex, ss=ss, **kw)
        Image.fromarray(img).save(os.path.join(out, n + ".png"))
        print(n, f"compose {t1 - t:.0f}s render {time.time() - t1:.0f}s", flush=True)
        del V


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:] or list(VIEWS) + list(region_views()))
