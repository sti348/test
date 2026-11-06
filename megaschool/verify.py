"""Check a generated world in real vanilla servers: random sample of non-air
blocks must match, the data pack must load without errors.

  python3 verify.py <world_dir> <version> [n_samples]"""
from __future__ import annotations

import re
import sys

import numpy as np

import campus
import generate
import servertest
import anvil


def samples(n, seed=1):
    L = campus.build()
    idx = campus.Index(L.pieces)
    rng = np.random.default_rng(seed)
    out = []
    regs = generate.regions()
    per = max(1, n // len(regs))
    for rx, rz in regs:
        # one 16x16 chunk per region, a few interesting voxels from it
        cx = rx * 512 + int(rng.integers(0, 32)) * 16
        cz = rz * 512 + int(rng.integers(0, 32)) * 16
        V = campus.compose(L, idx, cx, cz, 16, 16)
        nz = np.argwhere(V[4:] != 0) + [4, 0, 0]
        if len(nz) == 0:
            continue
        for k in rng.choice(len(nz), min(per, len(nz)), replace=False):
            y, z, x = nz[k]
            out.append((cx + x, y - 64, cz + z, anvil.name_of(int(V[y, z, x])).split("[")[0]))
    return out


def main():
    world, ver = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 120
    pts = samples(n)
    cmds = []
    for (x, y, z, b) in pts:
        cmds.append(f"forceload add {x} {z}")
    cmds.append("sleep 25")
    for (x, y, z, b) in pts:
        cmds.append(f"execute if block {x} {y} {z} {b}")
    cmds += ["datapack list", "function wuya:help", "function wuya:day", "function wuya:tiny",
             "function wuya:tp/gate", "forceload remove all"]
    lines, start = servertest.run(world, ver, cmds, timeout=1800)
    body = lines[start:]
    passed = sum("Test passed" in l for l in body)
    failed = [l for l in body if "Test failed" in l]
    errs = [l for l in lines if re.search(r"ERROR|Exception|Failed to load|Couldn't load|Unknown|Incorrect", l)
            and "DragonFight" not in l]
    print(f"{ver}: {passed}/{len(pts)} block checks passed, {len(failed)} failed")
    if failed:
        # map failed lines back to samples (they are in order)
        res = [l for l in body if "Test passed" in l or "Test failed" in l]
        for p, l in zip(pts, res):
            if "failed" in l:
                print("   FAIL", p)
    print("errors/warnings:")
    for l in errs[:40]:
        print("  ", l[:300])
    for l in body:
        if "data pack" in l.lower() or "wuya" in l.lower() or "enabled" in l.lower():
            print("  ", l[:300])


if __name__ == "__main__":
    main()
