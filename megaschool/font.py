"""CJK glyph bitmaps (WenQuanYi Zen Hei) for giant facade lettering."""
from __future__ import annotations

import functools
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "/System/Library/Fonts/PingFang.ttc",
]


@functools.lru_cache(None)
def _font(px):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return ImageFont.truetype(p, px)
    raise SystemExit("no CJK font found; install fonts-wqy-zenhei")


@functools.lru_cache(None)
def glyph(ch: str, px: int, bold: int = 0) -> np.ndarray:
    """Boolean (px, px) bitmap, row 0 = top."""
    s = px * 4
    im = Image.new("L", (s, s), 0)
    d = ImageDraw.Draw(im)
    f = _font(s)
    box = d.textbbox((0, 0), ch, font=f)
    w, h = box[2] - box[0], box[3] - box[1]
    d.text(((s - w) / 2 - box[0], (s - h) / 2 - box[1]), ch, font=f, fill=255,
           stroke_width=bold * 4, stroke_fill=255)
    im = im.resize((px, px), Image.BOX)
    return np.asarray(im) > 110


def text(s: str, px: int, gap: int, bold: int = 0, vertical: bool = False) -> np.ndarray:
    """Bitmap of a whole string, rows top->bottom, cols left->right."""
    gl = [glyph(c, px, bold) if c != " " else np.zeros((px, px), bool) for c in s]
    n = len(gl)
    if vertical:
        out = np.zeros((n * px + (n - 1) * gap, px), bool)
        for i, g in enumerate(gl):
            out[i * (px + gap):i * (px + gap) + px] = g
    else:
        out = np.zeros((px, n * px + (n - 1) * gap), bool)
        for i, g in enumerate(gl):
            out[:, i * (px + gap):i * (px + gap) + px] = g
    return out
