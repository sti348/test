"""Generator for Minecraft item models (block-model JSON 'elements') with an
automatically packed texture atlas.  Each face of each box gets its own atlas
region and is painted by a small painter function, so UVs never need to be
written by hand.

Coordinates are model units (16 = one block).  Front of vehicles is -Z
(north); an item_display with yaw Y then faces the direction yaw Y.
"""
from __future__ import annotations

import hashlib
import json
import math
import os

from PIL import Image

FACES = ("north", "south", "east", "west", "up", "down")


def hexc(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def clamp(v):
    return max(0, min(255, int(round(v))))


def shade(c, k):
    return tuple(clamp(x * k) for x in c[:3]) + ((c[3],) if len(c) == 4 else ())


def mix(a, b, t):
    return tuple(clamp(a[i] * (1 - t) + b[i] * t) for i in range(3))


def noise(x, y, salt):
    h = hashlib.md5(f"{x},{y},{salt}".encode()).digest()
    return h[0] / 255.0 * 2 - 1


# ----------------------------------------------------------------------------
# painters:  fn(img, x0, y0, w, h, face, ctx) -> paints the region
# ----------------------------------------------------------------------------
def solid(color, n=6, edge=0.82, grad=0.10, alpha=255):
    color = hexc(color) if isinstance(color, str) else color

    def p(img, x0, y0, w, h, face, ctx):
        px = img.load()
        for j in range(h):
            for i in range(w):
                k = 1.0
                if face not in ("up", "down") and h > 2:
                    k *= 1 + grad * (0.5 - j / max(1, h - 1))
                if edge and (i == 0 or j == 0 or i == w - 1 or j == h - 1) and w > 2 and h > 2:
                    k *= edge
                c = tuple(clamp(v * k + noise(x0 + i, y0 + j, ctx) * n) for v in color)
                px[x0 + i, y0 + j] = c + (alpha,)
    return p


def metal(color, n=4):
    """Polished metal: bright band near the top, darker bottom."""
    color = hexc(color) if isinstance(color, str) else color

    def p(img, x0, y0, w, h, face, ctx):
        px = img.load()
        for j in range(h):
            for i in range(w):
                t = j / max(1, h - 1)
                if face == "up":
                    k = 1.18
                elif face == "down":
                    k = 0.7
                else:
                    k = 1.25 - 0.5 * t if h > 2 else 1.0
                    if h > 3 and j == 1:
                        k = 1.45
                if (i == 0 or i == w - 1) and w > 3:
                    k *= 0.85
                c = tuple(clamp(v * k + noise(x0 + i, y0 + j, ctx) * n) for v in color)
                px[x0 + i, y0 + j] = c + (255,)
    return p


def fins(color, dark):
    color, dark = hexc(color), hexc(dark)

    def p(img, x0, y0, w, h, face, ctx):
        px = img.load()
        for j in range(h):
            for i in range(w):
                if face in ("up", "down"):
                    c = shade(color, 1.1)
                else:
                    c = color if j % 2 == 0 else dark
                    if i == 0 or i == w - 1:
                        c = shade(c, 0.85)
                px[x0 + i, y0 + j] = c + (255,)
    return p


def tire(color="3e3833"):
    color = hexc(color)

    def p(img, x0, y0, w, h, face, ctx):
        px = img.load()
        for j in range(h):
            for i in range(w):
                k = 1.0
                if face in ("up", "down", "north", "south"):  # tread
                    k = 0.8 if (i + j) % 3 == 0 else 1.0
                c = tuple(clamp(v * k + noise(x0 + i, y0 + j, ctx) * 3) for v in color)
                px[x0 + i, y0 + j] = c + (255,)
    return p


def spoked_wheel(rim="b8b8b4", spoke="d8d8d4", hub="9a9a98", spokes=18, tire_col=None):
    """Cut-out disc: rim ring, thin spokes, hub.  Transparent elsewhere."""
    rim, spoke, hub = hexc(rim), hexc(spoke), hexc(hub)
    tc = hexc(tire_col) if tire_col else None

    def p(img, x0, y0, w, h, face, ctx):
        px = img.load()
        cx, cy = (w - 1) / 2, (h - 1) / 2
        R = min(w, h) / 2
        for j in range(h):
            for i in range(w):
                dx, dy = i - cx, j - cy
                r = math.hypot(dx, dy)
                c = None
                if tc and R - 1.0 <= r < R + 0.2:
                    c = tc
                elif R - 1.6 <= r < R - 0.6:
                    c = rim
                elif r < R * 0.16 + 0.6:
                    c = hub
                elif r < R - 1.2:
                    ang = math.atan2(dy, dx)
                    step = 2 * math.pi / spokes
                    d = abs(((ang + step / 2) % step) - step / 2) * r
                    if d < 0.42:
                        c = spoke
                px[x0 + i, y0 + j] = (c + (255,)) if c else (0, 0, 0, 0)
    return p


def cartwheel(wood="8a6440", dark="5e4028", iron="4a4a4c", spokes=12):
    wood, dark, iron = hexc(wood), hexc(dark), hexc(iron)

    def p(img, x0, y0, w, h, face, ctx):
        px = img.load()
        cx, cy = (w - 1) / 2, (h - 1) / 2
        R = min(w, h) / 2
        for j in range(h):
            for i in range(w):
                dx, dy = i - cx, j - cy
                r = math.hypot(dx, dy)
                c = None
                if R - 1.1 <= r < R + 0.1:
                    c = iron
                elif R - 2.6 <= r < R - 1.1:
                    c = wood if (int(math.atan2(dy, dx) * 6) % 2) else dark
                elif r < R * 0.2 + 0.8:
                    c = dark if r > R * 0.2 else iron
                elif r < R - 2.4:
                    ang = math.atan2(dy, dx)
                    step = 2 * math.pi / spokes
                    d = abs(((ang + step / 2) % step) - step / 2) * r
                    if d < 0.75:
                        c = wood
                px[x0 + i, y0 + j] = (c + (255,)) if c else (0, 0, 0, 0)
    return p


def lens(glass="f4ecc8", rim="c8c8c4"):
    glass, rim = hexc(glass), hexc(rim)

    def p(img, x0, y0, w, h, face, ctx):
        px = img.load()
        cx, cy = (w - 1) / 2, (h - 1) / 2
        R = min(w, h) / 2
        for j in range(h):
            for i in range(w):
                r = math.hypot(i - cx, j - cy)
                if r >= R - 0.6:
                    c = rim
                else:
                    c = mix(glass, (255, 255, 255), 0.5) if (i - cx) < -0.5 and (j - cy) < -0.5 else glass
                px[x0 + i, y0 + j] = c + (255,)
    return p


def emblem(base="bcc0c4", ring="c6a458"):
    base, ring = hexc(base), hexc(ring)
    m = metal(base)

    def p(img, x0, y0, w, h, face, ctx):
        m(img, x0, y0, w, h, face, ctx)
        px = img.load()
        cx, cy = w * 0.42, h * 0.45
        R = min(w, h) * 0.32
        for j in range(h):
            for i in range(w):
                r = math.hypot(i - cx, j - cy)
                if R - 0.9 <= r <= R + 0.2 or (r < R * 0.5 and abs(j - cy) < 0.6 and i > cx - 1):
                    px[x0 + i, y0 + j] = ring + (255,)
    return p


def glass(color="c8d8e0", alpha=90, frame=None):
    color = hexc(color)
    fr = hexc(frame) if frame else None

    def p(img, x0, y0, w, h, face, ctx):
        px = img.load()
        for j in range(h):
            for i in range(w):
                if fr and (i == 0 or j == 0 or i == w - 1 or j == h - 1):
                    px[x0 + i, y0 + j] = fr + (255,)
                else:
                    a = alpha + (40 if (i + j) % 7 == 0 else 0)
                    px[x0 + i, y0 + j] = color + (a,)
    return p


def crate(color="dcd6c4", corner="6a6a6a", latch="8a8a88"):
    color, corner, latch = hexc(color), hexc(corner), hexc(latch)

    def p(img, x0, y0, w, h, face, ctx):
        px = img.load()
        for j in range(h):
            for i in range(w):
                k = 1 + 0.08 * (0.5 - j / max(1, h - 1)) if face not in ("up", "down") else 1.05
                c = tuple(clamp(v * k + noise(x0 + i, y0 + j, ctx) * 5) for v in color)
                e = (i in (0, w - 1)) or (j in (0, h - 1))
                if e:
                    c = shade(c, 0.8)
                ci = i == 0 or i == w - 1
                cj = j == 0 or j == h - 1
                if w > 5 and h > 4 and ((ci and (j < 2 or j >= h - 2)) or (cj and (i < 2 or i >= w - 2))):
                    c = corner
                px[x0 + i, y0 + j] = c + (255,)
        if face not in ("up", "down") and w > 6 and h > 4:
            mx = x0 + w // 2
            px[mx, y0 + 1] = latch + (255,)
            px[mx - 1, y0 + 1] = latch + (255,)
            px[mx, y0 + 2] = shade(latch, 0.7) + (255,)
    return p


def canvas(color, n=6, fold=0.88):
    color = hexc(color)

    def p(img, x0, y0, w, h, face, ctx):
        px = img.load()
        for j in range(h):
            for i in range(w):
                k = fold if (i % 5 == 0) else 1.0
                if face == "up":
                    k = (fold if (j % 5 == 0) else 1.0) * 1.05
                c = tuple(clamp(v * k + noise(x0 + i, y0 + j, ctx) * n) for v in color)
                px[x0 + i, y0 + j] = c + (255,)
    return p


def roll_end(color="6e6a44", dark="4a4630"):
    color, dark = hexc(color), hexc(dark)

    def p(img, x0, y0, w, h, face, ctx):
        px = img.load()
        cx, cy = (w - 1) / 2, (h - 1) / 2
        for j in range(h):
            for i in range(w):
                r = math.hypot(i - cx, j - cy)
                ang = math.atan2(j - cy, i - cx)
                spiral = (r - ang / math.pi * 0.9) % 1.8 < 0.6
                c = dark if spiral else color
                px[x0 + i, y0 + j] = c + (255,)
    return p


def log_end(bark="5a4430", ring="a8844e", ring2="8a6a3c"):
    bark, ring, ring2 = hexc(bark), hexc(ring), hexc(ring2)

    def p(img, x0, y0, w, h, face, ctx):
        px = img.load()
        cx, cy = (w - 1) / 2, (h - 1) / 2
        R = min(w, h) / 2
        for j in range(h):
            for i in range(w):
                r = math.hypot(i - cx, j - cy)
                c = bark if r > R - 0.9 else (ring2 if int(r) % 2 else ring)
                px[x0 + i, y0 + j] = c + (255,)
    return p


def bark(color="5e4632"):
    color = hexc(color)

    def p(img, x0, y0, w, h, face, ctx):
        px = img.load()
        for j in range(h):
            for i in range(w):
                k = 0.8 if (j * 3 + (i // 3)) % 4 == 0 else 1.0
                c = tuple(clamp(v * k + noise(x0 + i, y0 + j, ctx) * 8) for v in color)
                px[x0 + i, y0 + j] = c + (255,)
    return p


def planks(color="8a6a44"):
    color = hexc(color)

    def p(img, x0, y0, w, h, face, ctx):
        px = img.load()
        for j in range(h):
            for i in range(w):
                k = 0.78 if j % 3 == 2 else 1.0
                c = tuple(clamp(v * k + noise(x0 + i, y0 + j, ctx) * 7) for v in color)
                px[x0 + i, y0 + j] = c + (255,)
    return p


def pattern(rows, pal):
    """Explicit pixel art for a face; stretched/cropped to the region."""
    def p(img, x0, y0, w, h, face, ctx):
        px = img.load()
        for j in range(h):
            r = rows[min(len(rows) - 1, int(j * len(rows) / h))]
            for i in range(w):
                ch = r[min(len(r) - 1, int(i * len(r) / w))]
                if ch == ".":
                    px[x0 + i, y0 + j] = (0, 0, 0, 0)
                else:
                    c = pal[ch]
                    px[x0 + i, y0 + j] = (hexc(c) if isinstance(c, str) else c) + (255,)
    return p


# ----------------------------------------------------------------------------
class Model:
    def __init__(self, name, tex_w=128, tex_h=128, density=1.0):
        self.name = name
        self.W, self.H = tex_w, tex_h
        self.density = density
        self.img = Image.new("RGBA", (tex_w, tex_h), (0, 0, 0, 0))
        self.elements = []
        self.display = {}
        # shelf packer
        self.cx, self.cy, self.shelf = 0, 0, 0
        self.cache = {}

    def alloc(self, w, h):
        if self.cx + w > self.W:
            self.cx = 0
            self.cy += self.shelf
            self.shelf = 0
        if self.cy + h > self.H:
            raise RuntimeError(f"atlas full for {self.name}: need {w}x{h}")
        x, y = self.cx, self.cy
        self.cx += w
        self.shelf = max(self.shelf, h)
        return x, y

    def box(self, frm, to, faces, rot=None, density=None, skip=()):
        """faces: painter for all faces, or dict face->painter (missing -> no face)."""
        d = density or self.density
        frm = [float(v) for v in frm]
        to = [float(v) for v in to]
        dims = [to[i] - frm[i] for i in range(3)]
        el = {"from": [round(v, 4) for v in frm], "to": [round(v, 4) for v in to], "faces": {}}
        if rot:
            origin, axis, angle = rot
            assert angle in (-45, -22.5, 0, 22.5, 45), angle
            el["rotation"] = {"origin": [round(v, 4) for v in origin], "axis": axis, "angle": angle}
        if not isinstance(faces, dict):
            faces = {f: faces for f in FACES}
        for f in FACES:
            if f in skip or f not in faces or faces[f] is None:
                continue
            if f in ("north", "south"):
                fw, fh = dims[0], dims[1]
            elif f in ("east", "west"):
                fw, fh = dims[2], dims[1]
            else:
                fw, fh = dims[0], dims[2]
            if fw <= 0 and fh <= 0:
                continue
            pw = max(1, int(math.ceil(fw * d - 1e-6)))
            ph = max(1, int(math.ceil(fh * d - 1e-6)))
            key = (id(faces[f]), pw, ph, f if f in ("up", "down") else "side")
            if key in self.cache and getattr(faces[f], "shared", False):
                x, y = self.cache[key]
            else:
                x, y = self.alloc(pw, ph)
                faces[f](self.img, x, y, pw, ph, f, f"{self.name}{len(self.elements)}{f}")
                self.cache[key] = (x, y)
            uv = [x * 16 / self.W, y * 16 / self.H, (x + pw) * 16 / self.W, (y + ph) * 16 / self.H]
            el["faces"][f] = {"uv": [round(v, 4) for v in uv], "texture": "#0"}
        if el["faces"]:
            self.elements.append(el)
        return el

    def plane_x(self, x, y0, z0, y1, z1, painter, rot=None):
        """Zero-thickness plane facing east/west (e.g. a spoked wheel)."""
        return self.box([x, y0, z0], [x, y1, z1], {"east": painter, "west": painter}, rot=rot)

    def ring_x(self, cx, cy, cz, r_out, thick, x0, x1, painter, segs=16):
        """16-gon ring in the Y/Z plane around an axle along X, from rotated boxes."""
        L = 2 * r_out * math.tan(math.pi / 16) + 0.35
        ang = (0, 22.5, -22.5, 45, -45)
        for a in ang:  # top and bottom
            self.box([x0, cy + r_out - thick, cz - L / 2], [x1, cy + r_out, cz + L / 2], painter,
                     rot=([(x0 + x1) / 2, cy, cz], "x", a) if a else None)
            self.box([x0, cy - r_out, cz - L / 2], [x1, cy - r_out + thick, cz + L / 2], painter,
                     rot=([(x0 + x1) / 2, cy, cz], "x", a) if a else None)
        for a in (0, 22.5, -22.5):  # front and back
            self.box([x0, cy - L / 2, cz + r_out - thick], [x1, cy + L / 2, cz + r_out], painter,
                     rot=([(x0 + x1) / 2, cy, cz], "x", a) if a else None)
            self.box([x0, cy - L / 2, cz - r_out], [x1, cy + L / 2, cz - r_out + thick], painter,
                     rot=([(x0 + x1) / 2, cy, cz], "x", a) if a else None)

    def cyl_x(self, cx, cy, cz, r, x0, x1, painter, ends=None):
        """Octagonal cylinder along X (two boxes, one rotated 45 degrees)."""
        s = r * 0.83
        f = dict.fromkeys(("north", "south", "up", "down"), painter)
        if ends:
            f["east"] = ends
            f["west"] = ends
        self.box([x0, cy - s, cz - s], [x1, cy + s, cz + s], f)
        f2 = dict.fromkeys(("north", "south", "up", "down"), painter)
        self.box([x0 + 0.01, cy - s, cz - s], [x1 - 0.01, cy + s, cz + s], f2, rot=([cx, cy, cz], "x", 45))

    def cyl_z(self, cx, cy, cz, r, z0, z1, painter, ends=None):
        s = r * 0.83
        f = dict.fromkeys(("east", "west", "up", "down"), painter)
        if ends:
            f["north"] = ends
            f["south"] = ends
        self.box([cx - s, cy - s, z0], [cx + s, cy + s, z1], f)
        f2 = dict.fromkeys(("east", "west", "up", "down"), painter)
        self.box([cx - s, cy - s, z0 + 0.01], [cx + s, cy + s, z1 - 0.01], f2, rot=([cx, cy, cz], "z", 45))

    def check_bounds(self):
        for el in self.elements:
            for v in el["from"] + el["to"]:
                if v < -16 or v > 32:
                    raise ValueError(f"{self.name}: element out of range {el['from']} {el['to']}")

    def write(self, rp_root):
        self.check_bounds()
        tex_dir = os.path.join(rp_root, "assets", "kino", "textures", "item")
        mdl_dir = os.path.join(rp_root, "assets", "kino", "models", "item")
        itm_dir = os.path.join(rp_root, "assets", "kino", "items")
        for d in (tex_dir, mdl_dir, itm_dir):
            os.makedirs(d, exist_ok=True)
        # trim atlas height to what was used (keep power of two)
        used = self.cy + self.shelf
        h = 16
        while h < used:
            h *= 2
        if h < self.H:
            # rescale v coordinates
            k = self.H / h
            for el in self.elements:
                for f in el["faces"].values():
                    f["uv"][1] = round(f["uv"][1] * k, 4)
                    f["uv"][3] = round(f["uv"][3] * k, 4)
            self.img = self.img.crop((0, 0, self.W, h))
            self.H = h
        self.img.save(os.path.join(tex_dir, self.name + ".png"))
        model = {
            "textures": {"0": f"kino:item/{self.name}", "particle": f"kino:item/{self.name}"},
            "elements": self.elements,
        }
        if self.display:
            model["display"] = self.display
        with open(os.path.join(mdl_dir, self.name + ".json"), "w") as fh:
            json.dump(model, fh, separators=(",", ":"))
        with open(os.path.join(itm_dir, self.name + ".json"), "w") as fh:
            json.dump({"model": {"type": "minecraft:model", "model": f"kino:item/{self.name}"}}, fh, indent=2)
        return model
