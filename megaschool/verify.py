"""Check a generated world in real vanilla servers: random sample of non-air
blocks must match, the data pack must load without errors.

  python3 verify.py <world_dir> <version> [n_samples]"""
from __future__ import annotations

import re
import sys

import numpy as np

import generate
import servertest
import anvil


def samples(n, seed=1, extra_partial=60):
    """Random non-air voxels from one chunk of every written region (both
    dimensions, every height), plus voxels with block states near the gate."""
    W = generate.build_worlds()
    rng = np.random.default_rng(seed)
    out = []
    regs = generate.regions()
    per = max(1, n // len(regs))
    for dim, rx, rz in regs:
        w = W[dim]
        w._floor = w.region_floor(rx, rz)                 # same floor rule as the writer
        cx = rx * 512 + int(rng.integers(0, 32)) * 16
        cz = rz * 512 + int(rng.integers(0, 32)) * 16
        m = w.maps(cx, cz, 16, 16)
        ivs = w.detail_intervals(m, w.pieces_in(cx, cz, 16, 16))
        cells = []
        for (a, b) in ivs:
            V = w.compose(cx, cz, 16, 16, a, b, m)
            nz = np.argwhere(V != 0)
            if len(nz):
                for k in rng.choice(len(nz), min(per, len(nz)), replace=False):
                    y, z, x = nz[k]
                    cells.append((cx + x, a + y, cz + z, anvil.name_of(int(V[y, z, x]))))
        rng.shuffle(cells)
        out += [(dim,) + c for c in cells[:per]]
    w = W["overworld"]
    w._floor = w.region_floor(0, 1)
    m = w.maps(100, 640, 256, 256)
    V = w.compose(100, 640, 256, 256, -64, 320, m)
    lut = np.array(["[" in anvil.name_of(i) for i in range(len(anvil.all_names()))])
    nz = np.argwhere(lut[V])
    for k in rng.choice(len(nz), min(extra_partial, len(nz)), replace=False):
        y, z, x = nz[k]
        out.append(("overworld", 100 + x, y - 64, 640 + z, anvil.name_of(int(V[y, z, x]))))
    return out


def main():
    world, ver = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 120
    pts = samples(n)
    cmds = []
    # forceload in batches: tall chunks (3056 blocks) are heavy, 1.20.1 runs out of heap otherwise
    for i in range(0, len(pts), 32):
        batch = pts[i:i + 32]
        for (d, x, y, z, b) in batch:
            cmds.append(f"execute in minecraft:{d} run forceload add {x} {z}")
        cmds.append("sleep 25")
        for (d, x, y, z, b) in batch:
            cmds.append(f"execute in minecraft:{d} if block {x} {y} {z} {b}")
        cmds += ["execute in minecraft:overworld run forceload remove all",
                 "execute in minecraft:the_nether run forceload remove all", "sleep 5"]
    cmds += ["datapack list", "function wuya:help", "function wuya:day", "function wuya:tiny",
             "function wuya:tp/gate", "function wuya:tp/nether", "forceload remove all"]
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
