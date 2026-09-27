"""Builds data for the web preview renderer into build/preview/:
  world.json   block palette + merged boxes of the whole set
  atlas.png    16x16 block textures (vanilla, taken from the npm package
               'minecraft-assets' - not committed to this repository)
  tex/         particle / sky textures
Run:  python3 tools/build_preview.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile

from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
import blockdefs  # noqa: E402
import boxes  # noqa: E402
import world  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "build", "preview")
CACHE = os.path.join(ROOT, "build", "cache")
MC_VER = "1.21.11"


def vanilla_dir():
    d = os.path.join(CACHE, "minecraft-assets", MC_VER)
    if os.path.isdir(d):
        return d
    os.makedirs(CACHE, exist_ok=True)
    tgz = os.path.join(CACHE, "minecraft-assets-1.19.0.tgz")
    if not os.path.exists(tgz):
        subprocess.check_call(["npm", "pack", "minecraft-assets@1.19.0", "--pack-destination", CACHE],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    prefix = f"package/minecraft-assets/data/{MC_VER}/"
    with tarfile.open(tgz) as tf:
        for m in tf.getmembers():
            if m.name.startswith(prefix) and m.isfile():
                rel = m.name[len(prefix):]
                if rel.split("/")[0] not in ("blocks", "particle", "environment", "colormap", "misc"):
                    continue
                dst = os.path.join(d, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with tf.extractfile(m) as src, open(dst, "wb") as fh:
                    fh.write(src.read())
    return d


def colormap(van, name, temp=0.6, downfall=0.6):
    im = Image.open(os.path.join(van, "colormap", name + ".png")).convert("RGB")
    downfall *= temp
    i = int((1.0 - temp) * 255.0)
    j = int((1.0 - downfall) * 255.0)
    return list(im.getpixel((i, j)))


def first_frame(path):
    im = Image.open(path).convert("RGBA")
    return im.crop((0, 0, 16, 16)) if im.size[1] > 16 else im.resize((16, 16), Image.NEAREST)


def main():
    van = vanilla_dir()
    os.makedirs(OUT, exist_ok=True)
    w = world.build()
    extra_states = {s for *_, s in world.barricade_blocks()}
    blocks = dict(w.b)
    bx = boxes.greedy_boxes(blocks)
    states = sorted({b[6] for b in bx} | extra_states)
    defs = [blockdefs.define(s) for s in states]
    tex_names = set()
    for d in defs:
        tex_names.update(d["tex"].values())
    tex_names.update(["water_still"])
    tex_names = sorted(tex_names)
    grass = colormap(van, "grass")
    foliage = colormap(van, "foliage")
    # atlas
    n = len(tex_names)
    cols = 16
    rows = (n + cols - 1) // cols
    atlas = Image.new("RGBA", (cols * 16, max(1, rows) * 16), (0, 0, 0, 0))
    index = {}
    for k, t in enumerate(tex_names):
        if t == "grass_block_side#tinted":
            base = first_frame(os.path.join(van, "blocks", "grass_block_side.png"))
            ov = first_frame(os.path.join(van, "blocks", "grass_block_side_overlay.png"))
            px = ov.load()
            for y in range(16):
                for x in range(16):
                    r, g, b, a = px[x, y]
                    px[x, y] = (r * grass[0] // 255, g * grass[1] // 255, b * grass[2] // 255, a)
            base.alpha_composite(ov)
            img = base
        else:
            img = first_frame(os.path.join(van, "blocks", t + ".png"))
        atlas.paste(img, ((k % cols) * 16, (k // cols) * 16))
        index[t] = k
    atlas.save(os.path.join(OUT, "atlas.png"))
    pal_index = {s: i for i, s in enumerate(states)}
    flat = []
    for (x1, y1, z1, x2, y2, z2, s) in bx:
        flat += [x1, y1, z1, x2, y2, z2, pal_index[s]]
    data = {
        "states": states, "defs": defs, "atlas": {"cols": cols, "rows": rows, "index": index},
        "tints": {"grass": grass, "foliage": foliage, "birch": [0x80, 0xA7, 0x55], "spruce": [0x61, 0x99, 0x61],
                  "water": [0x3F, 0x76, 0xE4]},
        "boxes": flat,
    }
    with open(os.path.join(OUT, "world.json"), "w") as fh:
        json.dump(data, fh, separators=(",", ":"))
    # particle + sky textures
    tex = os.path.join(OUT, "tex")
    os.makedirs(tex, exist_ok=True)
    for sub in ("particle",):
        for f in os.listdir(os.path.join(van, sub)):
            if f.endswith(".png"):
                shutil.copy(os.path.join(van, sub, f), os.path.join(tex, f))
    for f in ("environment/celestial/sun.png", "environment/celestial/moon/full_moon.png", "environment/clouds.png"):
        p = os.path.join(van, f)
        if os.path.exists(p):
            shutil.copy(p, os.path.join(tex, os.path.basename(f)))
    print(f"preview: {len(bx)} boxes, {len(states)} states, {n} textures, grass {grass} foliage {foliage}")


if __name__ == "__main__":
    main()
