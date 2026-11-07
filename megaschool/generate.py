"""Generate the 无涯中学 world save.

  python3 generate.py [--out DIR] [--jobs N] [--zip]

Writes a complete Java Edition world (1.20.1 format, opens in 1.20.1 ... 26.x)."""
from __future__ import annotations

import argparse
import multiprocessing as mp
import os
import shutil
import time
import zipfile


import campus
import datapack
import level

HERE = os.path.dirname(os.path.abspath(__file__))
DUSK = 13000                     # twilight: the sun has just gone, first stars (with the twilight data pack)
WORLD_NAME = "无涯中学"          # name shown in the world list
FOLDER = "WuyaHighSchool"       # folder name inside the zip (ASCII so every unzip tool is happy)

_W = None        # {"overworld": World, "the_nether": World}


def build_worlds():
    """Campus + new regions (overworld) and the Nether school, as world3d Worlds."""
    import regions
    import world3d
    L = campus.build()
    ow_pieces, ow_lands = regions.overworld()
    ne_pieces, ne_lands = regions.nether()
    ow = world3d.World(world3d.OVERWORLD, L.pieces + ow_pieces, campus.GROUND_Y - 1,
                       painter=lambda x0, z0, dx, dz: campus.paint_ground(L, x0, z0, dx, dz),
                       landforms=ow_lands, biome=regions.overworld_biome)
    ne = world3d.World(world3d.NETHER, ne_pieces, regions.NETHER_FLOOR - 1, landforms=ne_lands,
                       biome=regions.nether_biome, top="netherrack", sub="netherrack")
    return {"overworld": ow, "the_nether": ne}


def _init():
    global _W
    if _W is None:
        _W = build_worlds()
        # register block states before forking so palette ids (and thus the output
        # bytes) do not depend on which worker meets a block first
        seen = set()
        for w in _W.values():
            for p in w.pieces:
                key = (p.name, p.kw.get("scheme"), p.kw.get("rock"), p.kw.get("kind"))
                if key not in seen or p.name == "shop":
                    seen.add(key)
                    p.build()
            w.dim.lut()


def _region(args):
    dim, rx, rz, out = args
    _init()
    t = time.time()
    w = _W[dim]
    folder = os.path.join(out, w.dim.folder)
    n = w.write_region(os.path.join(folder, f"r.{rx}.{rz}.mca"), rx, rz)
    return dim, rx, rz, time.time() - t, n


def regions():
    """(dimension, rx, rz) of every region that differs from the generators."""
    import world3d
    _init()
    out = []
    ow = _W["overworld"]
    for (rx, rz) in world3d.regions_of(ow, -4096, -4096, 5120, 1536):
        out.append(("overworld", rx, rz))
    ne = _W["the_nether"]
    for (rx, rz) in world3d.regions_of(ne, -1024, -1024, 512, 1024):
        out.append(("the_nether", rx, rz))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(HERE), "build", "world", FOLDER))
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    ap.add_argument("--zip", default=None, help="also write a .zip of the world here")
    ap.add_argument("--only", default=None, help="comma list of dim:rx:rz to (re)generate (dim = overworld|the_nether)")
    a = ap.parse_args()
    out = a.out
    if a.only is None and os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(os.path.join(out, "region"), exist_ok=True)
    os.makedirs(os.path.join(out, "DIM-1", "region"), exist_ok=True)
    rs = regions()
    if a.only:
        rs = [(s.split(":")[0], int(s.split(":")[1]), int(s.split(":")[2])) for s in a.only.split(",")]
    _init()          # build the layout before forking so workers share it
    t0 = time.time()
    ctx = mp.get_context("fork")
    total = 0
    with ctx.Pool(a.jobs) as pool:
        for dim, rx, rz, dt, n in pool.imap_unordered(_region, [(d, rx, rz, out) for d, rx, rz in rs]):
            total += n
            print(f"  {dim:10s} region {rx:+d},{rz:+d}  {dt:5.1f}s  {n / 1e6:6.1f}M blocks", flush=True)
    print(f"regions done in {time.time() - t0:.0f}s, {total / 1e6:.0f} million blocks above ground")
    level.write_level_dat(os.path.join(out, "level.dat"), WORLD_NAME, campus.SPAWN, angle=180.0, day_time=DUSK,
                          datapacks=("vanilla", "file/wuya"))
    dp = os.path.join(out, "datapacks", "wuya")
    shutil.rmtree(dp, ignore_errors=True)
    datapack.write(dp)
    icon = os.path.join(HERE, "icon.png")
    if os.path.exists(icon):
        shutil.copy(icon, os.path.join(out, "icon.png"))
    size = sum(os.path.getsize(os.path.join(dp_, f)) for dp_, _, fs in os.walk(out) for f in fs)
    print(f"world: {out}  ({size / 1e6:.0f} MB)")
    if a.zip:
        os.makedirs(os.path.dirname(os.path.abspath(a.zip)), exist_ok=True)
        with zipfile.ZipFile(a.zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for d, _, fs in os.walk(out):
                for f in sorted(fs):
                    p = os.path.join(d, f)
                    arc = os.path.join(FOLDER, os.path.relpath(p, out))
                    z.write(p, arc)
        print(f"zip: {a.zip} ({os.path.getsize(a.zip) / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
