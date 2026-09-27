"""Greedy merge of a sparse block dict into axis-aligned boxes."""
from __future__ import annotations

from collections import defaultdict

MAX_VOL = 32768  # vanilla /fill limit


def greedy_boxes(blocks):
    layers = defaultdict(dict)
    for (x, y, z), s in blocks.items():
        if s is not None:
            layers[y][(x, z)] = s
    rects_by_y = {}
    for y, cells in layers.items():
        seen = set()
        rects = []
        for (x, z) in sorted(cells, key=lambda p: (p[1], p[0])):
            if (x, z) in seen:
                continue
            s = cells[(x, z)]
            x2 = x
            while (x2 + 1, z) in cells and (x2 + 1, z) not in seen and cells[(x2 + 1, z)] == s:
                x2 += 1
            z2 = z
            while True:
                nz = z2 + 1
                ok = all((xx, nz) in cells and (xx, nz) not in seen and cells[(xx, nz)] == s for xx in range(x, x2 + 1))
                if not ok:
                    break
                z2 = nz
            for xx in range(x, x2 + 1):
                for zz in range(z, z2 + 1):
                    seen.add((xx, zz))
            rects.append((x, z, x2, z2, s))
        rects_by_y[y] = rects
    # merge identical rectangles vertically
    out = []
    open_ = {}
    for y in sorted(rects_by_y):
        cur = {}
        for r in rects_by_y[y]:
            if r in open_ and open_[r][1] == y - 1:
                y1, _ = open_[r]
                cur[r] = (y1, y)
            else:
                cur[r] = (y, y)
        for r, (y1, y2) in open_.items():
            if r not in cur or cur[r][0] != y1:
                out.append((r[0], y1, r[1], r[2], y2, r[3], r[4]))
        open_ = cur
    for r, (y1, y2) in open_.items():
        out.append((r[0], y1, r[1], r[2], y2, r[3], r[4]))
    # respect the fill volume limit
    final = []
    for (x1, y1, z1, x2, y2, z2, s) in out:
        vol = (x2 - x1 + 1) * (y2 - y1 + 1) * (z2 - z1 + 1)
        if vol <= MAX_VOL:
            final.append((x1, y1, z1, x2, y2, z2, s))
            continue
        per = max(1, MAX_VOL // ((y2 - y1 + 1) * (z2 - z1 + 1)))
        for xs in range(x1, x2 + 1, per):
            final.append((xs, y1, z1, min(x2, xs + per - 1), y2, z2, s))
    return final
