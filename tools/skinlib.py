"""Tiny pixel-art painter for Minecraft 64x64 player skins.

Faces are painted from ASCII art.  Every character maps to a colour in a
palette; '.' leaves the pixel untouched (transparent on overlay layers).

Face orientation (as seen from outside the model):
  front/back/right/left : row 0 = top of the part
  right (character's right side): column 0 = back, last column = front
  left  (character's left side) : column 0 = front, last column = back
  top   : last row = front edge,  column 0 = character's right
"""
from __future__ import annotations

import hashlib
from PIL import Image

# (base uv, overlay uv, (w, h, d)) ; arm width is patched for slim skins
PARTS = {
    "head": ((0, 0), (32, 0), (8, 8, 8)),
    "body": ((16, 16), (16, 32), (8, 12, 4)),
    "rarm": ((40, 16), (40, 32), (4, 12, 4)),
    "larm": ((32, 48), (48, 48), (4, 12, 4)),
    "rleg": ((0, 16), (0, 32), (4, 12, 4)),
    "lleg": ((16, 48), (0, 48), (4, 12, 4)),
}


def face_rect(u, v, w, h, d, face):
    return {
        "top": (u + d, v, w, d),
        "bottom": (u + d + w, v, w, d),
        "right": (u, v + d, d, h),
        "front": (u + d, v + d, w, h),
        "left": (u + d + w, v + d, d, h),
        "back": (u + 2 * d + w, v + d, w, h),
    }[face]


def _noise(x, y, salt):
    hsh = hashlib.md5(f"{x},{y},{salt}".encode()).digest()
    return hsh[0] / 255.0 * 2 - 1


def hexc(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


class Skin:
    def __init__(self, name, slim=False, noise=None):
        self.name = name
        self.slim = slim
        self.img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        self.px = self.img.load()
        # palette char -> noise amplitude
        self.noise = noise or {}

    def dims(self, part):
        (bu, ou, (w, h, d)) = PARTS[part]
        if part in ("rarm", "larm") and self.slim:
            w = 3
        return bu, ou, (w, h, d)

    def rect(self, part, face, layer=0):
        bu, ou, (w, h, d) = self.dims(part)
        u, v = ou if layer else bu
        return face_rect(u, v, w, h, d, face)

    def paint(self, part, face, art, pal, layer=0, salt=""):
        x0, y0, w, h = self.rect(part, face, layer)
        if isinstance(art, str):
            art = [r.strip() for r in art.strip().split("\n")]
        assert len(art) == h, f"{self.name} {part}.{face} L{layer}: {len(art)} rows != {h}"
        for j, row in enumerate(art):
            row = row.strip()
            assert len(row) == w, f"{self.name} {part}.{face} L{layer} row{j}: '{row}' != {w}"
            for i, ch in enumerate(row):
                if ch == "." or ch == " ":
                    continue
                col = pal[ch]
                if len(col) == 3:
                    col = (*col, 255)
                amp = self.noise.get(ch, 0)
                if amp:
                    n = _noise(x0 + i, y0 + j, self.name + salt) * amp
                    col = tuple(max(0, min(255, int(c + n))) for c in col[:3]) + (col[3],)
                self.px[x0 + i, y0 + j] = col

    def fill(self, part, face, ch, pal, layer=0):
        x0, y0, w, h = self.rect(part, face, layer)
        self.paint(part, face, [ch * w] * h, pal, layer)

    def mirror_to(self, src, dst, layer=0):
        """Copy a limb to the other side, mirrored (right<->left faces swap)."""
        for face in ("top", "bottom", "front", "back", "right", "left"):
            tgt = {"right": "left", "left": "right"}.get(face, face)
            sx, sy, w, h = self.rect(src, face, layer)
            dx, dy, _, _ = self.rect(dst, tgt, layer)
            for j in range(h):
                for i in range(w):
                    self.px[dx + (w - 1 - i), dy + j] = self.px[sx + i, sy + j]

    def save(self, path):
        self.img.save(path)


def mirror_rows(art):
    rows = [r.strip() for r in art.strip().split("\n")] if isinstance(art, str) else art
    return [r[::-1] for r in rows]


def rows(art):
    return [r.strip() for r in art.strip().split("\n")]


def sheet(skins, path, scale=6):
    """Unfolded texture contact sheet for quick review."""
    n = len(skins)
    out = Image.new("RGBA", (n * 64 * scale + (n - 1) * 8, 64 * scale), (60, 60, 70, 255))
    for k, s in enumerate(skins):
        bg = Image.new("RGBA", (64, 64), (200, 200, 205, 255))
        for y in range(64):
            for x in range(64):
                if ((x // 4) + (y // 4)) % 2:
                    bg.putpixel((x, y), (180, 180, 186, 255))
        bg.alpha_composite(s.img)
        out.paste(bg.resize((64 * scale, 64 * scale), Image.NEAREST), (k * (64 * scale + 8), 0))
    out.save(path)
