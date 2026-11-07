"""Bridge between the 无涯中学 generator and Horizon (Minecraft 26.3 in Rust).

The generator stays as it is.  This script puts its world into Horizon, drives
the game through Horizon's agent control (`horizon-ctl`, JSON over a local
socket; `horizon-ctl mcp` serves the same commands to Claude over MCP), and
closes the loop:

  install      copy build/world/WuyaHighSchool into Horizon's saves
  launch       start Horizon on that world (headless: Xvfb + software Vulkan)
  tour [N..]   teleport to every viewpoint (or the named ones), wait for the
               chunks, screenshot the real game frame -> build/horizon/shots/
  probe [N..]  in-game checks around each viewpoint:
                 - blocks:  sampled blocks must be what the generator wrote
                 - dark:    walkable cells where the game's own light engine
                            gives block light 0 and sky light < 4
               -> build/horizon/report.json
  sheet        contact sheet of the screenshots -> build/horizon/sheet.png
  improve      turn the dark spots of the last probe into lamp fixes
               (megaschool/horizon_fixes.json), which generate.py reads
  mcp-config   write .mcp.json so a Claude Code session in this repository
               gets Horizon's tools (screenshot, tp, block, light, ...)
  quit         save and quit the game

Paths (override with environment variables):
  HORIZON_REPO   checkout of horizon-rust/horizon (built with --profile fast or release)
  HORIZON_HOME   game home with saves/ (default build/horizon_home)
  HORIZON_RES    prepared resources (default $HORIZON_REPO/.local/horizon-client/26.3)

Horizon needs your own copy of Minecraft: Java Edition 26.3 to prepare its
resources (see README); nothing from Mojang is stored in this repository."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(ROOT, "build")
OUT = os.path.join(BUILD, "horizon")
WORLD = "WuyaHighSchool"
FIXES = os.path.join(HERE, "horizon_fixes.json")


def env_paths():
    repo = os.environ.get("HORIZON_REPO", os.path.join(os.path.dirname(ROOT), "horizon-rust", "horizon"))
    home = os.environ.get("HORIZON_HOME", os.path.join(BUILD, "horizon_home"))
    res = os.environ.get("HORIZON_RES", os.path.join(repo, ".local", "horizon-client", "26.3"))
    target = next((os.path.join(repo, "target", p) for p in ("release", "fast")
                   if os.path.exists(os.path.join(repo, "target", p, "horizon-ctl"))), os.path.join(repo, "target", "fast"))
    return repo, home, res, target


def game_env():
    repo, home, res, target = env_paths()
    e = dict(os.environ)
    e["HORIZON_HOME"] = home
    e.setdefault("HORIZON_CONTROL", os.path.join(home, "control.sock"))
    e.setdefault("HORIZON_NO_AUDIO", "1")
    if "DISPLAY" not in e and "WAYLAND_DISPLAY" not in e:
        e["DISPLAY"] = ":77"                                         # our Xvfb (see launch)
    icd = "/usr/share/vulkan/icd.d/lvp_icd.json"                     # software Vulkan when there is no GPU
    if os.path.exists(icd) and not os.path.exists("/dev/dri"):
        e.setdefault("VK_ICD_FILENAMES", icd)
    return e


def ctl(*args, timeout=600, check=True):
    """Run one horizon-ctl command; returns its JSON reply."""
    _, _, _, target = env_paths()
    exe = os.path.join(target, "horizon-ctl")
    home = env_paths()[1]
    os.makedirs(home, exist_ok=True)
    # the game takes its working directory as the game home (saves/, logs/, options.txt)
    p = subprocess.run([exe, *map(str, args)], capture_output=True, text=True, env=game_env(), timeout=timeout, cwd=home)
    out = p.stdout.strip().splitlines()
    try:
        reply = json.loads(out[-1]) if out else {}
    except json.JSONDecodeError:
        reply = {"raw": p.stdout[-2000:]}
    if check and (p.returncode != 0 or (isinstance(reply, dict) and "error" in reply)):
        raise RuntimeError(f"horizon-ctl {' '.join(map(str, args))}: {reply or p.stderr[-2000:]}")
    return reply


def script(*lines, timeout=60):
    """Several horizon-ctl commands back to back in one process (fast enough for a double tap)."""
    _, home, _, target = env_paths()
    p = subprocess.run([os.path.join(target, "horizon-ctl"), "script"], input="\n".join(lines) + "\n",
                       capture_output=True, text=True, env=game_env(), timeout=timeout, cwd=home)
    return p.stdout


# ------------------------------------------------------------------ setup
def install():
    _, home, _, _ = env_paths()
    src = os.path.join(BUILD, "world", WORLD)
    dst = os.path.join(home, "saves", WORLD)
    if not os.path.exists(os.path.join(src, "level.dat")):
        raise SystemExit("generate the world first: python3 megaschool/generate.py")
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    flatten_overlays(dst)
    print("installed", dst)


def flatten_overlays(world):
    """Horizon reads a data pack's base files and skips its overlays (seen in
    Horizon 0.1.0: the Nether would not open, 'invalid world generation field').
    Our pack keeps 1.20.1 files at the base and newer formats in overlays, so
    for Horizon the overlays meant for the newest versions are copied over
    the base.  The shipped save is left as it is for vanilla clients."""
    for pack in os.listdir(os.path.join(world, "datapacks")):
        root = os.path.join(world, "datapacks", pack)
        meta = os.path.join(root, "pack.mcmeta")
        if not os.path.exists(meta):
            continue
        entries = json.load(open(meta, encoding="utf-8")).get("overlays", {}).get("entries", [])
        newest = [e for e in entries if e.get("max_format", (e.get("formats") or [0, 0])[-1]) >= 1000]
        for e in newest:
            d = os.path.join(root, e["directory"])
            if os.path.isdir(d):
                shutil.copytree(d, root, dirs_exist_ok=True)
        print(f"  {pack}: {len(newest)} overlays for the newest versions applied to the base (for Horizon)")


def xvfb():
    e = game_env()
    disp = e.get("DISPLAY", "")
    if not disp.startswith(":") or "WAYLAND_DISPLAY" in os.environ:
        return
    if os.path.exists(f"/tmp/.X11-unix/X{disp[1:].split('.')[0]}"):
        return                                                     # a display is already running
    subprocess.Popen(["Xvfb", disp, "-screen", "0", "1600x900x24", "-nolisten", "tcp"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    time.sleep(2)


def launch(render_distance=24):
    _, home, res, target = env_paths()
    os.makedirs(home, exist_ok=True)
    xvfb()
    reply = ctl("launch", "--world", WORLD, "--creative", "--wait", "--game", os.path.join(target, "horizon-client"),
                "--resources", res, "--render-distance", render_distance, timeout=900)
    print(json.dumps(reply)[:400])
    ctl("options-set", "fov", "80", check=False)
    ctl("options-set", "tutorialStep", "none", check=False)          # no "Move with WASD" toast
    ctl("options-set", "bobView", "false", check=False)
    ctl("render-distance", render_distance, check=False)
    ctl("lod-distance", 96, check=False)                              # distant terrain: the far towers show

    ctl("key", "f1", "tap", check=False)                              # hide the HUD and hand for clean shots
    return reply


# ------------------------------------------------------------------ viewpoints
def viewpoints():
    sys.path.insert(0, HERE)
    import datapack
    v = {}
    for k, t in {**datapack.viewpoints(), **datapack.region_viewpoints()}.items():
        x, y, z, yaw, pitch, label = t[:6]
        dim = t[6] if len(t) > 6 else "overworld"
        v[k] = dict(x=x, y=y, z=z, yaw=yaw, pitch=pitch, label=label, dim=dim)
    v.update(EXTRA)
    return v


# check points that are not teleports of the data pack
EXTRA = {"gate_passage": dict(x=0.5, y=-60, z=880.5, yaw=180, pitch=-10, label="凯旋门主拱通道", dim="overworld",
                             radius=44, depth=3)}


def goto(vp, settle=25.0):
    tp = f"execute in minecraft:{vp['dim']} run tp @s {vp['x']} {vp['y']} {vp['z']} {vp['yaw']} {vp['pitch']}"
    ctl("command", tp)
    st = ctl("state", check=False)
    if st.get("gamemode") != "spectator":               # no gravity: views in mid-air stay in mid-air
        ctl("command", "gamemode spectator", check=False)
        ctl("command", tp)
    ctl("wait-for", "loaded", "--timeout", 120, check=False)
    time.sleep(settle)                                                 # let distant sections mesh


def settle_world(timeout=240):
    """Wait until the chunks around the player are loaded and lit: stored light
    is only meaningful once the light engine has nothing left to do."""
    t0, last = time.time(), None
    while time.time() - t0 < timeout:
        st = ctl("status", check=False)
        chunks, dirty = st.get("chunks"), st.get("dirty_light", 1)
        if dirty == 0 and chunks == last and chunks:
            return st
        last = chunks
        time.sleep(4)
    return None


def tour(names=None, time_of_day=13000):
    os.makedirs(os.path.join(OUT, "shots"), exist_ok=True)
    ctl("time", time_of_day, check=False)
    vps = viewpoints()
    for k in names or list(vps):
        vp = vps[k]
        goto(vp)
        path = os.path.join(OUT, "shots", f"{k}.png")
        ctl("screenshot", path, timeout=300)
        print(f"{k:18s} {vp['label']}  -> {path}", flush=True)


# ------------------------------------------------------------------ in-game probes
def _light(x0, y0, z0, x1, y1, z1):
    """Sky and block light of a box as arrays [y][z][x] (None where not loaded)."""
    import numpy as np
    r = ctl("light", x0, y0, z0, x1, y1, z1)
    nx, nz, ny = x1 - x0 + 1, z1 - z0 + 1, y1 - y0 + 1
    def dec(s):
        a = np.array([int(c, 16) if c != "." else -1 for c in s.replace("\n", "")], np.int16)
        return a[:nx * nz * ny].reshape(ny, nz, nx)
    return dec(r["sky"]), dec(r["block"])


def dark_spots(vp, radius=24, depth=6):
    """Walkable air cells near a viewpoint that the game lights with block 0 / sky < 4."""
    import numpy as np
    sys.path.insert(0, HERE)
    import generate
    import anvil
    W = _WORLDS.setdefault("w", generate.build_worlds())[vp["dim"]]
    x, y, z = int(vp["x"]), int(vp["y"]), int(vp["z"])
    W._floor = W.region_floor(x // 512, z // 512)                     # same floor rule as the writer
    x0, z0 = x - radius, z - radius
    n = 2 * radius + 1
    y0, y1 = y - depth, y + depth
    m = W.maps(x0, z0, n, n)
    V = W.compose(x0, z0, n, n, y0 - 1, y1 + 2, m)
    air = (V == 0) | (V == anvil.B("cave_air"))
    stand = air[1:-1] & air[2:] & ~air[:-2]                           # air, air above, solid below
    spots = []
    for ya in range(y0, y1 + 1, 8):
        yb = min(y1, ya + 7)
        for za in range(z0, z0 + n, 32):
            zb = min(z0 + n - 1, za + 31)
            sky, blk = _light(x0, ya, za, x0 + n - 1, yb, zb)
            sel = stand[ya - y0:yb - y0 + 1, za - z0:zb - z0 + 1, :]
            bad = sel & (blk == 0) & (sky >= 0) & (sky < 4)
            for (yy, zz, xx) in np.argwhere(bad):
                spots.append((int(x0 + xx), int(ya + yy), int(za + zz)))
    return spots


_WORLDS = {}


def block_check(vp, n=24, seed=0):
    """Random non-air blocks near the viewpoint: does the game read what we wrote?"""
    import numpy as np
    sys.path.insert(0, HERE)
    import generate
    import anvil
    W = _WORLDS.setdefault("w", generate.build_worlds())[vp["dim"]]
    rng = np.random.default_rng(seed)
    x, y, z = int(vp["x"]), int(vp["y"]), int(vp["z"])
    W._floor = W.region_floor(x // 512, z // 512)
    m = W.maps(x - 32, z - 32, 64, 64)
    V = W.compose(x - 32, z - 32, 64, 64, y - 16, y + 48, m)
    nz = np.argwhere((V != 0) & (V != anvil.B("cave_air")))
    bad, skipped = [], 0
    for k in rng.choice(len(nz), min(n, len(nz)), replace=False) if len(nz) else []:
        yy, zz, xx = nz[k]
        want = anvil.name_of(int(V[yy, zz, xx])).split("[")[0]
        got = ctl("block", x - 32 + xx, y - 16 + yy, z - 32 + zz)
        if not got.get("loaded", True):
            skipped += 1
            continue
        name = str(got.get("block", ""))
        if name.split("[")[0] != want:
            bad.append({"at": [int(x - 32 + xx), int(y - 16 + yy), int(z - 32 + zz)], "want": want, "got": name})
    return min(n, len(nz)) - skipped, bad


def probe(names=None):
    os.makedirs(OUT, exist_ok=True)
    vps = viewpoints()
    rep = {}
    for k in names or list(vps):
        vp = vps[k]
        goto(vp, settle=3)
        settle_world()
        checked, bad = block_check(vp)
        spots = dark_spots(vp, vp.get("radius", 24), vp.get("depth", 6))
        rep[k] = {"label": vp["label"], "dim": vp["dim"], "blocks_checked": checked, "block_mismatches": bad,
                  "dark_walkable": len(spots), "dark_samples": spots[:5000]}
        print(f"{k:18s} blocks {checked - len(bad)}/{checked}  dark walkable cells {len(spots)}", flush=True)
    path = os.path.join(OUT, "report.json")
    old = json.load(open(path)) if os.path.exists(path) else {}
    old.update(rep)
    json.dump(old, open(path, "w"), indent=1, ensure_ascii=False)
    print("report:", path)


def sheet(cols=4, w=480):
    from PIL import Image, ImageDraw
    d = os.path.join(OUT, "shots")
    files = sorted(f for f in os.listdir(d) if f.endswith(".png"))
    if not files:
        raise SystemExit("no screenshots: run tour first")
    h = int(w * 9 / 16)
    S = Image.new("RGB", (cols * w, (len(files) + cols - 1) // cols * (h + 18)), (20, 20, 28))
    dr = ImageDraw.Draw(S)
    for i, f in enumerate(files):
        im = Image.open(os.path.join(d, f)).convert("RGB")
        im.thumbnail((w, h))
        x, y = (i % cols) * w, (i // cols) * (h + 18)
        S.paste(im, (x, y + 18))
        dr.text((x + 4, y + 3), f[:-4], fill=(230, 230, 240))
    path = os.path.join(OUT, "sheet.png")
    S.save(path)
    print(path)


def improve(min_cells=12, spacing=10):
    """Lamps for the dark walkable places the last probe found: one lamp per
    spacing x spacing cell of dark spots, recorded in horizon_fixes.json."""
    rep = json.load(open(os.path.join(OUT, "report.json")))
    fixes = json.load(open(FIXES)) if os.path.exists(FIXES) else {"lamps": []}
    have = {(l["dim"], l["x"] // spacing, l["z"] // spacing) for l in fixes["lamps"]}
    added = 0
    for k, r in rep.items():
        if r["dark_walkable"] < min_cells:
            continue
        cells = {}
        for (x, y, z) in r["dark_samples"]:
            cells.setdefault((x // spacing, z // spacing), []).append((x, y, z))
        for (cx, cz), pts in cells.items():
            if len(pts) < 3 or (r["dim"], cx, cz) in have:
                continue
            x, y, z = sorted(pts)[len(pts) // 2]
            fixes["lamps"].append({"dim": r["dim"], "x": x, "y": y, "z": z, "from": k})
            have.add((r["dim"], cx, cz))
            added += 1
    json.dump(fixes, open(FIXES, "w"), indent=1, ensure_ascii=False)
    print(f"{added} lamps added, {len(fixes['lamps'])} in {FIXES}; regenerate with generate.py")


def mcp_config():
    _, home, res, target = env_paths()
    e = game_env()
    cfg = {"mcpServers": {"horizon": {"command": os.path.join(target, "horizon-ctl"), "args": ["mcp"],
                                      "env": {k: e[k] for k in ("HORIZON_HOME", "HORIZON_CONTROL", "HORIZON_NO_AUDIO",
                                                                 "DISPLAY", "VK_ICD_FILENAMES") if k in e}}}}
    path = os.path.join(ROOT, ".mcp.json")
    json.dump(cfg, open(path, "w"), indent=2)
    print(path, "(machine-specific: not committed)")


def main(argv):
    cmd, rest = (argv[0], argv[1:]) if argv else ("help", [])
    if cmd == "install":
        install()
    elif cmd == "launch":
        launch(int(rest[0]) if rest else 24)
    elif cmd == "tour":
        tour(rest or None)
    elif cmd == "probe":
        probe(rest or None)
    elif cmd == "sheet":
        sheet()
    elif cmd == "improve":
        improve()
    elif cmd == "mcp-config":
        mcp_config()
    elif cmd == "quit":
        ctl("quit", check=False)
    elif cmd == "ctl":
        print(json.dumps(ctl(*rest), ensure_ascii=False))
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
