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

import numpy as np

import anvil
import campus
import datapack
import level

HERE = os.path.dirname(os.path.abspath(__file__))
DUSK = 12700                     # this build is the dusk version: the sun is just setting
WORLD_NAME = "无涯中学"          # name shown in the world list
FOLDER = "WuyaHighSchool"       # folder name inside the zip (ASCII so every unzip tool is happy)

_L = None
_IDX = None


def _init():
    global _L, _IDX
    if _L is None:
        _L = campus.build()
        _IDX = campus.Index(_L.pieces)
        # register every block state before forking so palette ids (and thus the
        # output bytes) do not depend on which worker meets a block first
        seen = set()
        for p in _L.pieces:
            key = (p.name, p.kw.get("scheme"))
            if key not in seen or p.name == "shop":
                seen.add(key)
                p.build()


def _region(args):
    rx, rz, out = args
    _init()
    t = time.time()
    V = campus.compose(_L, _IDX, rx * 512, rz * 512, 512, 512)
    anvil.write_region(os.path.join(out, "region", f"r.{rx}.{rz}.mca"), rx, rz, V)
    return rx, rz, time.time() - t, int(np.count_nonzero(V[4:]))


def regions():
    xs = range(-campus.HALF // 512, campus.HALF // 512)
    zs = range(-campus.HALF // 512, -(-campus.SOUTH_EDGE // 512))
    return [(rx, rz) for rz in zs for rx in xs]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(HERE), "build", "world", FOLDER))
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    ap.add_argument("--zip", default=None, help="also write a .zip of the world here")
    ap.add_argument("--only", default=None, help="comma list of rx:rz to (re)generate")
    a = ap.parse_args()
    out = a.out
    if a.only is None and os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(os.path.join(out, "region"), exist_ok=True)
    rs = regions()
    if a.only:
        rs = [tuple(map(int, s.split(":"))) for s in a.only.split(",")]
    _init()          # build the layout before forking so workers share it
    t0 = time.time()
    ctx = mp.get_context("fork")
    total = 0
    with ctx.Pool(a.jobs) as pool:
        for rx, rz, dt, n in pool.imap_unordered(_region, [(rx, rz, out) for rx, rz in rs]):
            total += n
            print(f"  region {rx:+d},{rz:+d}  {dt:5.1f}s  {n / 1e6:6.1f}M blocks", flush=True)
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
