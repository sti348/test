"""Bridge to minecraft-build-design (github.com/yimeng-YM/minecraft-build-design).

The facilities in mcbuild_designs.py are built as mcbuild projects in
mcbuild_projects/<name>/ (project.toml + design.py), so anyone with the skill
can open, change, verify and preview them with its `mcb` tool.  This script

  sync      writes the projects, runs `mcb design / export / verify` for each
            (target version 1.20.1), reads the exported .litematic back and
            stores the blocks in mcbuild_cache.json.gz for generate.py;
  previews  runs `mcb preview --shots` (textured 3-D previews) for the given ones.

  MCB_SKILL=<path to the skill folder> python3 mcbuild_bridge.py sync [name ...]"""
from __future__ import annotations

import base64
import gzip
import json
import os
import subprocess
import sys
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECTS = os.path.join(HERE, "mcbuild_projects")
CACHE = os.path.join(HERE, "mcbuild_cache.json.gz")
SKILL = os.environ.get("MCB_SKILL", "/home/user/yimeng-ym/minecraft-build-design")
TARGET = "1.20.1"
sys.path.insert(0, os.path.join(SKILL, "scripts"))          # the skill's toolkit package `mcbuild`

TOML = '''# mcbuild project (minecraft-build-design).  python <skill>/scripts/mcb.py <command> -p <this folder>
[project]
name = "无涯中学 · {title}"
id = "Wuya{cid}"
version = "1.21.11"
lang = "zh"
author = "无涯中学"

[site]
source = "flat"                # the campus is superflat: grass at y=-61 on two dirt layers on bedrock
ground_y = -61
layers = [["dirt", 2]]
base = "bedrock"
box = [{bx0}, -64, {bz0}, {bx1}, 320, {bz1}]

[design]
script = "design.py"
origin = [0, -60, 0]           # local (0,0,0) = first air block above the grass at the plot's NW corner
turns = 0

[export]
mode = "portable"
target_version = "{target}"    # the map is written in the 1.20.1 format
schem = true
max_region = 64

[verify]
spawnproof = true
spawnproof_strict = false      # open landscape at twilight: dark grass is reported, not fatal (the map is peaceful)
{walk}

[preview]
title = "无涯中学 · {title}"
front = "south"
context = 20
'''

DESIGN_PY = '''"""{title} - see ../../mcbuild_designs.py ({fn}).  Run with `mcb design -p .`"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from mcbuild import Build, get_project
import mcbuild_designs as D

P = get_project()
B = Build(P.site(), P.name)
F = B.frame(tuple(P.cfg["design"]["origin"]), turns=P.cfg["design"].get("turns", 0))
INFO = D.{fn}(F)
B.notes.append("无涯中学 {title}：由 megaschool/mcbuild_designs.py 生成，放进地图时按地块左上角对齐。")
'''


def mcb(args, project):
    cmd = [sys.executable, os.path.join(SKILL, "scripts", "mcb.py"), "-p", project] + args
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def walk_toml(info):
    if not info.get("walk_start"):
        return ""
    lines = [f"walk_start = [{', '.join(str(v) for v in w(info['walk_start']))}]"]
    tg = ", ".join(f'"{k}" = [{", ".join(str(v) for v in w(p))}]' for k, p in info["walk_targets"].items())
    lines.append(f"walk_targets = {{ {tg} }}")
    return "\n".join(lines)


def w(p):
    """local -> world (origin 0, -60, 0)"""
    return (p[0], p[1] - 60, p[2])


def write_project(name):
    import mcbuild_designs as D
    fn, (W, Dd), title = D.DESIGNS[name]
    d = os.path.join(PROJECTS, name)
    os.makedirs(d, exist_ok=True)
    m = 12
    if name == "water_tower":
        bx0, bz0, bx1, bz1 = -48, -48, 48, 48
    else:
        bx0, bz0, bx1, bz1 = -m, -m, W + m, Dd + m
    info = {}
    # walk targets come from the design itself: run it once on a throwaway frame
    try:
        sys.path.insert(0, os.path.join(SKILL, "scripts"))
        from mcbuild import Build
        from mcbuild.terrain import make_flat
        site = make_flat((bx0, -64, bz0, bx1, 320, bz1), -61, layers=(("dirt", 2),), base="bedrock")
        B = Build(site, name)
        info = fn(B.frame((0, -60, 0))) or {}
    except Exception as e:                                   # noqa: BLE001 - reported by `mcb design` later
        print("  (dry run failed:", e, ")")
    open(os.path.join(d, "project.toml"), "w", encoding="utf-8").write(TOML.format(
        title=title, cid="".join(p.capitalize() for p in name.split("_")), bx0=bx0, bz0=bz0, bx1=bx1, bz1=bz1,
        target=TARGET, walk=walk_toml(info)))
    open(os.path.join(d, "design.py"), "w", encoding="utf-8").write(DESIGN_PY.format(title=title, fn=fn.__name__))
    return d


def litematic_blocks(path):
    """-> (A[y,z,x] uint16 palette indices, palette [names as stored], origin)."""
    sys.path.insert(0, os.path.join(SKILL, "scripts"))
    from mcbuild.schematic import read_litematic
    from mcbuild import nbt as mnbt
    doc = read_litematic(path)
    root = mnbt.load(path)
    regs = list(root["Regions"].items())
    xs, ys, zs = [], [], []
    for r in doc["regions"]:
        (px, py, pz), sh = r["pos"], r["index"].shape
        xs += [px, px + sh[2]]; ys += [py, py + sh[0]]; zs += [pz, pz + sh[1]]
    x0, y0, z0 = min(xs), min(ys), min(zs)
    A = np.zeros((max(ys) - y0, max(zs) - z0, max(xs) - x0), np.uint16)
    names = ["minecraft:air"]
    lut_names = {"minecraft:air": 0}
    for r, (_, raw) in zip(doc["regions"], regs):
        pal = []
        for e in raw["BlockStatePalette"]:
            n = str(e["Name"])
            props = {k: str(v) for k, v in e.get("Properties", {}).items()}
            if props:
                n += "[" + ",".join(f"{k}={v}" for k, v in sorted(props.items())) + "]"
            if n not in lut_names:
                lut_names[n] = len(names)
                names.append(n)
            pal.append(lut_names[n])
        pal = np.array(pal, np.uint16)
        idx = pal[r["index"]]
        px, py, pz = r["pos"]
        sh = idx.shape
        sub = A[py - y0:py - y0 + sh[0], pz - z0:pz - z0 + sh[1], px - x0:px - x0 + sh[2]]
        m = idx != 0
        sub[m] = idx[m]
    rep = json.load(open(os.path.join(os.path.dirname(os.path.dirname(path)), "artifacts", "litematic-report.json")))
    ox, oy, oz = rep["origin"]                               # world min corner; design origin is (0, -60, 0)
    return A, names, [ox, oy + 60, oz]


def _summary(project):
    p = os.path.join(project, "artifacts", "verification.json")
    if not os.path.exists(p):
        return {}
    v = json.load(open(p))
    sp = v.get("spawnProofing", {})
    return {"status": v.get("status"), "errors": len(v.get("errors", [])), "warnings": len(v.get("warnings", [])),
            "states_validated": v.get("file", {}).get("paletteStatesValidated"), "rule_problems": v.get("rules", {}).get("problems"),
            "floating": v.get("structure", {}).get("floating"), "missing_in_1_20_1": v.get("targetVersion", {}).get("missing"),
            "dark_surfaces": f"{sp.get('darkSurfaces')}/{sp.get('spawnableSurfaces')}", "walk": v.get("walk"),
            "first_errors": [str(e)[:200] for e in v.get("errors", [])[:5]],
            "first_warnings": [str(e)[:160] for e in v.get("warnings", [])[:4]]}


def sync(names=None):
    import mcbuild_designs as D
    sys.path.insert(0, HERE)
    out = {}
    if os.path.exists(CACHE):
        out = json.loads(gzip.decompress(open(CACHE, "rb").read()))
    report = {}
    for name in D.DESIGNS:
        if names and name not in names:
            continue
        d = write_project(name)
        for step in (["design", "--no-drawings"], ["export"], ["verify"]):
            rc, log = mcb(step, d)
            if rc and step[0] != "verify":
                print(log[-3000:])
                raise SystemExit(f"mcb {step[0]} failed for {name}")
        lit = [f for f in os.listdir(os.path.join(d, "release")) if f.endswith(".litematic")][0]
        A, pal, origin = litematic_blocks(os.path.join(d, "release", lit))
        out[name] = {"shape": list(A.shape), "palette": pal, "origin": origin,
                     "data": base64.b64encode(zlib.compress(A.tobytes(), 9)).decode()}
        report[name] = _summary(d)
        report[name]["blocks"] = int((A != 0).sum())
        print(f"  {name:16s} {A.shape}  verify: {report[name]}", flush=True)
    with open(CACHE, "wb") as f:
        f.write(gzip.compress(json.dumps(out, separators=(",", ":")).encode(), 9))
    with open(os.path.join(PROJECTS, "verification-summary.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    print(f"cache: {CACHE} ({os.path.getsize(CACHE) / 1e3:.0f} kB)")


_LOADED = None


def load():
    global _LOADED
    if _LOADED is None:
        from anvil import B
        raw = json.loads(gzip.decompress(open(CACHE, "rb").read()))
        _LOADED = {}
        for k, e in raw.items():
            A = np.frombuffer(zlib.decompress(base64.b64decode(e["data"])), np.uint16).reshape(e["shape"])
            lut = np.array([0 if p == "minecraft:air" else B(p.replace("minecraft:", "", 1)) for p in e["palette"]], np.uint16)
            _LOADED[k] = (lut[A], e["origin"])
    return _LOADED


def has_cache():
    return os.path.exists(CACHE)


def previews(names):
    for name in names:
        d = os.path.join(PROJECTS, name)
        rc, log = mcb(["preview", "--shots"], d)
        print(name, rc, log.strip().splitlines()[-1:] if log else "")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "sync"
    if cmd == "sync":
        sync(sys.argv[2:] or None)
    elif cmd == "previews":
        previews(sys.argv[2:])
