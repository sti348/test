"""Render preview images of the campus (needs build/tex from a client jar).

  python3 preview.py <out_dir> [view ...]"""
from __future__ import annotations

import os
import sys
import time

from PIL import Image

import anvil
import campus
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


def main(out, names, w=1600, h=900, ss=1):
    import os as _o
    w, h = int(_o.environ.get("PW", w)), int(_o.environ.get("PH", h))
    os.makedirs(out, exist_ok=True)
    L = campus.build()
    idx = campus.Index(L.pieces)
    tex = None
    for n in names:
        rect, cam, yaw, pitch, fov, kw = VIEWS[n]
        x0, z0, x1, z1 = rect
        t = time.time()
        V = campus.compose(L, idx, x0, z0, x1 - x0, z1 - z0)
        t1 = time.time()
        if tex is None or len(tex[1]) != len(anvil.all_names()):
            tex = textures.atlas()
        kw = dict(kw)
        if not kw.get("night") and not kw.get("dusk"):
            kw.setdefault("twilight", True)
        img = render.render(render.Grid(V, x0, z0), cam, yaw, pitch, w=w, h=h, fov=fov, tex=tex, ss=ss, **kw)
        Image.fromarray(img).save(os.path.join(out, n + ".png"))
        print(n, f"compose {t1 - t:.0f}s render {time.time() - t1:.0f}s", flush=True)
        del V


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:] or list(VIEWS))
