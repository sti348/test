"""Blockout stages: a rough 3D stand-in for a place that only exists as paintings.

A generated picture shows one view of a place and nothing behind it.  A stage
rebuilds that place roughly - masses, heights, positions, what lies behind
the camera - out of a few primitives on a voxel grid (metres; one voxel is
`res` metres).  Rendered from any camera it gives a flat-coloured layout
image; that image goes to the image model together with the earlier
paintings, so a new view keeps the place's structure.

Every primitive carries a label; a label has one flat colour (a Minecraft
concrete/terracotta block, so the stage can also be pasted into the
Minecraft world and walked in Horizon) and a line for the prompt's legend.

  python3 vn/stage.py LOCATION [CAMERA ...]     # render cameras -> vn/locations/LOC/layout_<cam>.png
  python3 vn/stage.py LOCATION --compare hero   # layout next to the painting, to match the camera"""
from __future__ import annotations

import importlib.util
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "megaschool"))

from anvil import B          # noqa: E402  (block ids shared with the voxel renderer)

# label -> (block, legend text for the prompt)
LABELS = {
    "building":  ("light_gray_concrete", "light grey = the main school buildings (walls)"),
    "floorline": ("gray_concrete", "darker grey stripes = floor lines / storeys of those buildings"),
    "tower":     ("white_concrete", "white = the tall tower / landmark building"),
    "roof":      ("cyan_terracotta", "dark teal = roofs"),
    "glass":     ("light_blue_concrete", "light blue = large glazed openings, windows and doors"),
    "plaza":     ("white_terracotta", "beige = paved plaza and walkways"),
    "road":      ("black_concrete", "black = road"),
    "lawn":      ("lime_concrete", "bright green = lawn and planted beds"),
    "tree":      ("green_concrete", "dark green blobs = trees"),
    "stairs":    ("yellow_concrete", "yellow = steps and terraces"),
    "pole":      ("red_concrete", "red = flagpole"),
    "lamp":      ("orange_concrete", "orange = street lamps"),
    "gate":      ("orange_terracotta", "terracotta orange = the school gate (a triumphal arch)"),
    "water":     ("blue_concrete", "blue = water"),
    "far":       ("purple_terracotta", "muted purple = distant buildings in the haze"),
    "rock":      ("stone", "grey stone = rock, cliffs"),
}


class Stage:
    def __init__(self, x0, z0, x1, z1, y0=-2, y1=400, res=2.0):
        self.x0, self.z0, self.y0, self.res = x0, z0, y0, res
        self.nx, self.nz, self.ny = int((x1 - x0) / res), int((z1 - z0) / res), int((y1 - y0) / res)
        self.V = np.zeros((self.ny, self.nz, self.nx), np.uint16)
        self.used = set()
        # world-space centres of every voxel, built lazily
        self._xs = (np.arange(self.nx) + 0.5) * res + x0
        self._zs = (np.arange(self.nz) + 0.5) * res + z0
        self._ys = (np.arange(self.ny) + 0.5) * res + y0

    def _id(self, label):
        self.used.add(label)
        return B(LABELS[label][0])

    def _yr(self, y0, y1):
        a = max(0, int(round((y0 - self.y0) / self.res)))
        b = min(self.ny, int(round((y1 - self.y0) / self.res)))
        return a, b

    def _put2d(self, mask2d, y0, y1, label):
        a, b = self._yr(y0, y1)
        if a < b:
            self.V[a:b][:, mask2d] = self._id(label)

    # ---------------------------------------------------------------- primitives (metres)
    def box(self, x0, y0, z0, x1, y1, z1, label):
        X = (self._xs >= min(x0, x1)) & (self._xs < max(x0, x1))
        Z = (self._zs >= min(z0, z1)) & (self._zs < max(z0, z1))
        self._put2d(Z[:, None] & X[None, :], y0, y1, label)

    def ground(self, label, y=0.0):
        """Fill the whole floor up to height y."""
        self._put2d(np.ones((self.nz, self.nx), bool), self.y0, y, label)

    def disc(self, cx, cz, r, y0, y1, label, r_in=0.0):
        d = np.hypot(self._xs[None, :] - cx, self._zs[:, None] - cz)
        self._put2d((d < r) & (d >= r_in), y0, y1, label)

    def sector(self, cx, cz, r0, r1, a0, a1, y0, y1, label):
        """Part of a ring around (cx, cz); angles in degrees, 0 = toward -z (north), + toward +x."""
        dx, dz = self._xs[None, :] - cx, self._zs[:, None] - cz
        d = np.hypot(dx, dz)
        a = np.degrees(np.arctan2(dx, -dz))
        self._put2d((d >= r0) & (d < r1) & (a >= a0) & (a < a1), y0, y1, label)

    def spire(self, cx, cz, half, y0, y1, label, square=True):
        """A pyramid / cone tapering from `half` at y0 to a point at y1."""
        a, b = self._yr(y0, y1)
        for k in range(a, b):
            t = (self._ys[k] - y0) / max(1e-6, y1 - y0)
            h = half * (1 - t)
            if square:
                m = (np.abs(self._xs[None, :] - cx) < h) & (np.abs(self._zs[:, None] - cz) < h)
            else:
                m = np.hypot(self._xs[None, :] - cx, self._zs[:, None] - cz) < h
            self.V[k][m] = self._id(label)

    def blob(self, cx, cy, cz, r, label, squash=0.8):
        d = np.sqrt((self._xs[None, None, :] - cx) ** 2 + ((self._ys[:, None, None] - cy) / squash) ** 2
                    + (self._zs[None, :, None] - cz) ** 2)
        self.V[d < r] = self._id(label)

    def tree(self, x, z, h=12, r=5, y=0.0):
        self.box(x - 0.6, y, z - 0.6, x + 0.6, y + h * 0.5, z + 0.6, "tree")
        self.blob(x, y + h - r * 0.8, z, r, "tree")

    def stairs(self, x0, x1, z_front, z_back, y_base, y_top, label="stairs"):
        """Steps rising from z_front up to z_back (either direction)."""
        n = max(1, int(abs(y_top - y_base) / self.res))
        for k in range(n):
            t0 = k / n
            z = z_front + (z_back - z_front) * t0
            self.box(x0, y_base, z, x1, y_base + (k + 1) * (y_top - y_base) / n, z_back, label)

    def floorlines(self, every, y0, y1, label="floorline"):
        """Paint storey lines on every 'building' voxel at these heights."""
        bid, fid = B(LABELS["building"][0]), self._id(label)
        y = y0 + every
        while y < y1:
            a, _ = self._yr(y, y + self.res)
            if 0 <= a < self.ny:
                sl = self.V[a]
                sl[sl == bid] = fid
            y += every

    # ---------------------------------------------------------------- output
    def legend(self):
        return "; ".join(LABELS[k][1] for k in LABELS if k in self.used)

    def render(self, cam, w=1536, h=1024):
        import render
        import textures
        x, y, z, yaw, pitch, fov = cam
        G = render.Grid(self.V, self.x0, self.z0, self.y0, self.res)
        img = render.render(G, (x, y, z), yaw, pitch, w=w, h=h, fov=fov, tex=textures.atlas(), maxdist=3000,
                            haze=0.00035)
        from PIL import Image
        return Image.fromarray(img)


def load(loc):
    path = os.path.join(HERE, "locations", loc, "scene.py")
    spec = importlib.util.spec_from_file_location(f"scene_{loc}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build(loc):
    mod = load(loc)
    st = mod.make_stage()
    return mod, st


def main(argv):
    if not argv:
        print(__doc__)
        return
    loc, rest = argv[0], argv[1:]
    mod, st = build(loc)
    d = os.path.join(HERE, "locations", loc)
    if rest[:1] == ["--compare"]:
        from PIL import Image
        cam = rest[1] if len(rest) > 1 else "hero"
        lay = st.render(mod.CAMERAS[cam]).convert("RGB")
        pic = Image.open(os.path.join(d, f"{cam}.png")).convert("RGB").resize(lay.size)
        both = Image.blend(pic, lay, 0.5)
        S = Image.new("RGB", (lay.width * 3 // 2, lay.height // 2))
        S.paste(pic.resize((lay.width // 2, lay.height // 2)), (0, 0))
        S.paste(lay.resize((lay.width // 2, lay.height // 2)), (lay.width // 2, 0))
        S.paste(both.resize((lay.width // 2, lay.height // 2)), (lay.width, 0))
        out = os.path.join(d, f"compare_{cam}.jpg")
        S.save(out, quality=85)
        print(out)
        return
    for cam in rest or list(mod.CAMERAS):
        out = os.path.join(d, f"layout_{cam}.png")
        st.render(mod.CAMERAS[cam]).save(out)
        print(out)


if __name__ == "__main__":
    main(sys.argv[1:])
