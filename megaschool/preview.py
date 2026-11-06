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
    # yaw like Minecraft: 0 south, 90 west, 180 north, 270 east; negative pitch looks up
    "gate": ((-900, 0, 900, 1100), (0.5, -58.4, 1065.5), 180, -12, 75, {}),
    "avenue": ((-900, 0, 900, 1100), (8, -58.4, 860), 182, -16, 75, {}),
    "canyon": ((-1000, -900, 1000, 600), (113, -58.4, 300), 180, -20, 75, {}),
    "east_rows": ((-300, 0, 1300, 1000), (380, -58.4, 870), 180, -22, 75, {}),
    "endless": ((-1200, -1400, 1200, -300), (40, -52, -850), 230, -16, 80, {}),
    "countdown": ((-700, -2048, 700, -1300), (0.5, -58.4, -1610), 180, -26, 75, {}),
    "playground": ((0, -700, 1400, 700), (672, -36, -16), 0, 6, 80, {}),
    "aerial": ((-1300, -1100, 1300, 1100), (260, 230, 1160), 192, 22, 70, dict(haze=0.0009)),
    "night": ((-900, 0, 900, 1100), (0.5, -58.4, 1065.5), 180, -12, 75, dict(night=True)),
}


def main(out, names, w=1600, h=900, ss=1):
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
        img = render.render(render.Grid(V, x0, z0), cam, yaw, pitch, w=w, h=h, fov=fov, tex=tex, ss=ss, **kw)
        Image.fromarray(img).save(os.path.join(out, n + ".png"))
        print(n, f"compose {t1 - t:.0f}s render {time.time() - t1:.0f}s", flush=True)
        del V


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:] or list(VIEWS))
