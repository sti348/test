"""Film -> Minecraft Java data pack (1.21.9+; uses the Mannequin entity).

Layout (namespace kino):
  function/setup        build the sets (spread over several ticks)
  function/play         start the film from the beginning
  function/scene/<n>    start from scene n (state is reconstructed)
  function/stop         stop playback
  function/film/t/<t>   per-tick commands (called through a macro)
  structure/tree/*.nbt  tree templates used by the set builder
"""
from __future__ import annotations

import gzip
import io
import json
import math
import os
import shutil
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
import boxes as boxlib  # noqa: E402
import film as filmlib  # noqa: E402
import world as worldlib  # noqa: E402
from film import state_at  # noqa: E402

NS = "kino"
DATA_VERSION = 3955          # 1.21.1 - structures are upgraded by the game on load
PACK_FORMAT = 88             # 1.21.9 / 1.21.10

# Sound ids used in the script -> vanilla sound events (volume factor, pitch factor)
SOUNDS = {
    "kino.gun_rifle": ("minecraft:entity.generic.explode", 0.35, 1.9),
    "kino.gun_pistol": ("minecraft:entity.firework_rocket.blast", 1.0, 0.7),
    "kino.gun_suppressed": ("minecraft:item.crossbow.shoot", 1.0, 0.6),
    "kino.engine": ("minecraft:entity.minecart.riding", 0.6, 0.6),
    "kino.kickstart": ("minecraft:block.piston.extend", 0.8, 0.6),
    "kino.brake": ("minecraft:block.grindstone.use", 1.0, 0.6),
    "kino.stone": ("minecraft:block.stone.break", 1.0, 0.8),
    "kino.kick": ("minecraft:entity.player.attack.knockback", 1.0, 1.0),
    "kino.baby_cry": ("minecraft:entity.cat.stray_ambient", 1.0, 1.35),
    "kino.cannon": ("minecraft:entity.generic.explode", 1.0, 0.6),
    "kino.explosion": ("minecraft:entity.generic.explode", 1.0, 0.5),
    "kino.snap": ("minecraft:entity.skeleton.hurt", 1.0, 0.5),
    "kino.punch": ("minecraft:entity.player.attack.strong", 1.0, 0.9),
    "kino.hit": ("minecraft:entity.player.attack.crit", 1.0, 0.7),
    "kino.splash": ("minecraft:entity.generic.splash", 1.0, 1.0),
}
PARTICLES = {
    "flame": "minecraft:flame", "small_flame": "minecraft:small_flame", "lava": "minecraft:lava",
    "smoke": "minecraft:smoke", "large_smoke": "minecraft:large_smoke", "poof": "minecraft:poof",
    "explosion": "minecraft:explosion", "splash": "minecraft:splash", "crit": "minecraft:crit",
}
OVERLAY_TEX = {"letterbox": "letterbox", "scope": "scope", "binoculars": "binoculars", "black": "black"}


def f(v):
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def jtext(s):
    return json.dumps(s, ensure_ascii=False)


def sel_actor(aid):
    return f"@e[type=minecraft:mannequin,tag={NS}.a.{aid},limit=1]"


def sel_prop(pid):
    return f"@e[type=minecraft:item_display,tag={NS}.p.{pid},limit=1]"


def item_stack(model, aim=False):
    if not model:
        return "minecraft:air"
    if aim:
        return (f'minecraft:crossbow[minecraft:item_model="{NS}:{model}",'
                f'minecraft:charged_projectiles=[{{id:"minecraft:arrow",count:1}}]]')
    return f'minecraft:stick[minecraft:item_model="{NS}:{model}"]'


def item_nbt(model):
    if not model:
        return '{id:"minecraft:stick",count:1,components:{"minecraft:item_model":"minecraft:air"}}'
    return f'{{id:"minecraft:stick",count:1,components:{{"minecraft:item_model":"{NS}:{model}"}}}}'


# ----------------------------------------------------------------------------
# NBT writer (for structure templates)
def _nbt_str(s):
    b = s.encode("utf-8")
    return struct.pack(">H", len(b)) + b


def _tag(tagtype, name, payload):
    return bytes([tagtype]) + _nbt_str(name) + payload


def nbt_payload(v):
    if isinstance(v, bool):
        return 1, bytes([1 if v else 0])
    if isinstance(v, int):
        return 3, struct.pack(">i", v)
    if isinstance(v, str):
        return 8, _nbt_str(v)
    if isinstance(v, dict):
        out = b""
        for k, x in v.items():
            t, p = nbt_payload(x)
            out += _tag(t, k, p)
        return 10, out + b"\x00"
    if isinstance(v, list):
        if not v:
            return 9, bytes([0]) + struct.pack(">i", 0)
        t0, _ = nbt_payload(v[0])
        out = bytes([t0]) + struct.pack(">i", len(v))
        for x in v:
            out += nbt_payload(x)[1]
        return 9, out
    raise TypeError(v)


def write_nbt(path, root):
    t, p = nbt_payload(root)
    data = _tag(10, "", p[:])
    with gzip.open(path, "wb") as fh:
        fh.write(data)


def state_to_palette(state):
    name, props = (state.split("[", 1) + [""])[:2]
    entry = {"Name": "minecraft:" + name}
    if props:
        entry["Properties"] = dict(kv.split("=") for kv in props.rstrip("]").split(","))
    return entry


def write_tree_templates(dp):
    d = os.path.join(dp, "data", NS, "structure", "tree")
    os.makedirs(d, exist_ok=True)
    for name, blocks in worldlib.TREE_VARIANTS.items():
        mx, _, mz = worldlib.TREE_MIN[name]
        xs = [b[0] - mx for b in blocks]
        ys = [b[1] for b in blocks]
        zs = [b[2] - mz for b in blocks]
        pal, idx = [], {}
        out = []
        for (x, y, z, st) in blocks:
            if st not in idx:
                idx[st] = len(pal)
                pal.append(state_to_palette(st))
            out.append({"pos": [x - mx, y, z - mz], "state": idx[st]})
        write_nbt(os.path.join(d, name + ".nbt"), {
            "DataVersion": DATA_VERSION, "size": [max(xs) + 1, max(ys) + 1, max(zs) + 1],
            "palette": pal, "blocks": out, "entities": []})


# ----------------------------------------------------------------------------
class DP:
    def __init__(self, root):
        self.root = root
        self.fdir = os.path.join(root, "data", NS, "function")

    def fn(self, name, lines):
        p = os.path.join(self.fdir, name + ".mcfunction")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")


def block_cmd(x, y, z, st):
    return f"setblock {x} {y} {z} minecraft:{st if st else 'air'}"


def summon_actor(a, p, pose, t):
    tags = f'["{NS}","{NS}.actor","{NS}.a.{a.id}"]'
    model = "slim" if a.slim else "wide"
    return (f"summon minecraft:mannequin {f(p[0])} {f(p[1])} {f(p[2])} "
            f'{{Tags:{tags},profile:{{texture:"{NS}:entity/skins/{a.skin}",model:"{model}"}},'
            f'hide_description:1b,immovable:1b,Invulnerable:1b,NoGravity:1b,Silent:1b,PersistenceRequired:1b,'
            f'pose:"{pose}",Rotation:[{f(p[3])}f,{f(p[4])}f]}}')


def summon_prop(pr, p):
    tags = f'["{NS}","{NS}.prop","{NS}.p.{pr.id}"]'
    t = pr.translation
    sc = pr.scale
    item = f"item:{item_nbt(pr.model)}," if pr.model else ""
    return (f"summon minecraft:item_display {f(p[0])} {f(p[1])} {f(p[2])} "
            f"{{Tags:{tags},{item}item_display:\"none\","
            f"transformation:{{left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f],"
            f"translation:[{f(t[0])}f,{f(t[1])}f,{f(t[2])}f],scale:[{f(sc)}f,{f(sc)}f,{f(sc)}f]}},"
            f"teleport_duration:3,view_range:{f(pr.view_range)}f,Rotation:[{f(p[3])}f,{f(p[4])}f]}}")


def subtitle_json(F, who, text):
    color = F.speakers.get(who, "#FFFFFF") if who else "#FFFFFF"
    if not who:
        return jtext({"text": text, "color": "#E0E0E0", "italic": True})
    if who == "旁白":
        return jtext({"text": text, "color": "#E8E0C8"})
    return jtext({"text": "", "extra": [{"text": who + "：", "color": color}, {"text": text, "color": "#FFFFFF"}]})


def overlay_cmd(name):
    if not name or name == "none":
        return "item replace entity @a armor.head with minecraft:air"
    tex = OVERLAY_TEX[name]
    return ("item replace entity @a armor.head with minecraft:paper["
            f'minecraft:equippable={{slot:"head",camera_overlay:"{NS}:misc/{tex}"}}]')


def changes_between(lst, t):
    return [c for c in lst if c[0] == t]


def write_datapack(F, S, root):
    if os.path.isdir(os.path.join(root, "data")):
        shutil.rmtree(os.path.join(root, "data"))
    dp = DP(root)
    with open(os.path.join(root, "pack.mcmeta"), "w", encoding="utf-8") as fh:
        json.dump({"pack": {
            "description": "奇诺之旅 · 第七话「战斗者的故事」— Minecraft film (/function kino:setup, kino:play)",
            "pack_format": PACK_FORMAT, "min_format": PACK_FORMAT, "max_format": 999}}, fh, ensure_ascii=False, indent=2)
    n = S["n"]

    # ---------------- per tick -------------------------------------------------
    ticks = [[] for _ in range(n)]
    cuts = set(s[0] for s in F.shots)
    cam_prev = None
    for t in range(n):
        c = S["cam"][t]
        if t + 1 in cuts and t + 1 < n:
            ticks[t].append(f"data merge entity @e[tag={NS}.cam,limit=1] {{teleport_duration:0}}")
        if t in cuts:
            ticks[t].append(f"spectate @e[tag={NS}.cam,limit=1] @a")
        if t - 1 in cuts:
            ticks[t].append(f"data merge entity @e[tag={NS}.cam,limit=1] {{teleport_duration:2}}")
        if c != cam_prev:
            ticks[t].append(f"tp @e[tag={NS}.cam,limit=1] {f(c[0])} {f(c[1])} {f(c[2])} {f(c[3])} {f(c[4])}")
        cam_prev = c

    # props
    for pr in F.props.values():
        rows = S["props"][pr.id]
        prev = None
        for t in range(n):
            r = rows[t]
            if r is None:
                if prev is not None:
                    ticks[t].append(f"kill {sel_prop(pr.id)}")
                prev = None
                continue
            if prev is None:
                ticks[t].append(summon_prop(pr, r))
            elif r != prev:
                jump = math.dist(r[:3], prev[:3]) > 3
                if jump:
                    ticks[t].append(f"data merge entity {sel_prop(pr.id)} {{teleport_duration:0}}")
                ticks[t].append(f"tp {sel_prop(pr.id)} {f(r[0])} {f(r[1])} {f(r[2])} {f(r[3])} {f(r[4])}")
                if jump and t + 1 < n:
                    ticks[t + 1].insert(0, f"data merge entity {sel_prop(pr.id)} {{teleport_duration:3}}")
            prev = r

    # actors
    for a in F.actors.values():
        rows = S["actors"][a.id]
        prev = None
        prev_ride = None
        prev_pose = None
        held = {"main": None, "off": None}
        for t in range(n):
            r = rows[t]
            if r is None:
                if prev is not None:
                    s_ = sel_actor(a.id)
                    if prev_ride:
                        ticks[t].append(f"ride {s_} dismount")
                    ticks[t].append(f"tag {s_} add {NS}.gone")
                    ticks[t].append(f"tp {s_} {f(prev[0])} 330 {f(prev[2])}")
                    ticks[t].append(f"tag @e[tag={NS}.gone] remove {NS}.a.{a.id}")
                prev, prev_ride, prev_pose, held = None, None, None, {"main": None, "off": None}
                continue
            ride = state_at(a.rides, t)
            pose = state_at(a.poses, t, "standing")
            s = sel_actor(a.id)
            if prev is None:
                ticks[t].append(summon_actor(a, r, pose, t))
                prev_pose = pose
            if pose != prev_pose:
                ticks[t].append(f'data merge entity {s} {{pose:"{pose}"}}')
                prev_pose = pose
            if ride != prev_ride:
                if ride:
                    ticks[t].append(f"ride {s} mount {sel_prop(ride)}")
                else:
                    ticks[t].append(f"ride {s} dismount")
                prev_ride = ride
            if ride:
                if prev is None or (r[3], r[4]) != (prev[3], prev[4]):
                    ticks[t].append(f"rotate {s} {f(r[3])} {f(r[4])}")
            elif prev is None or r[:5] != prev[:5]:
                ticks[t].append(f"tp {s} {f(r[0])} {f(r[1])} {f(r[2])} {f(r[3])} {f(r[4])}")
            for hand in ("main", "off"):
                cur = None
                for it in sorted(a.items, key=lambda i: i[0]):
                    if it[0] <= t and it[1] == hand:
                        cur = (it[2], it[3])
                if cur != held[hand]:
                    slot = "weapon.mainhand" if hand == "main" else "weapon.offhand"
                    ticks[t].append(f"item replace entity {s} {slot} with {item_stack(*(cur or (None, False)))}")
                    held[hand] = cur
            for (t0, t1) in a.fires:
                if t0 <= t <= t1 and t % 2 == 0:
                    ticks[t].append(f"execute at {s} run particle minecraft:flame ~ ~0.9 ~ 0.25 0.55 0.25 0.02 8 force @a")
            prev = r

    # world events, particles, sounds, drops
    for (t, kind, d) in F.events:
        if t >= n:
            continue
        if kind == "blocks":
            for (x, y, z, st) in d["list"]:
                ticks[t].append(block_cmd(x, y, z, st))
        elif kind == "particle":
            pos = d["pos"]
            dl = d.get("delta", (0, 0, 0))
            cnt = max(1, int(d.get("count", 1)))
            sp = d.get("speed", 0)
            if d["type"] in ("dust", "blood"):
                col = d.get("color", (0.5, 0.05, 0.05))
                pid = f"minecraft:dust{{color:[{f(col[0])},{f(col[1])},{f(col[2])}],scale:1.2}}"
            else:
                pid = PARTICLES.get(d["type"], "minecraft:poof")
            ticks[t].append(f"particle {pid} {f(pos[0])} {f(pos[1])} {f(pos[2])} {f(dl[0])} {f(dl[1])} {f(dl[2])} "
                            f"{f(sp)} {cnt} force @a")
            if d["type"] == "explosion" and cnt >= 20:
                ticks[t].append(f"particle minecraft:explosion_emitter {f(pos[0])} {f(pos[1])} {f(pos[2])} 0 0 0 0 1 force @a")
        elif kind == "sound":
            snd, vk, pk = SOUNDS[d["sound"]]
            vol = d.get("vol", 1.0) * vk
            pit = max(0.5, min(2.0, d.get("pitch", 1.0) * pk))
            if "follow" in d:
                ticks[t].append(f"execute at {sel_prop(d['follow'])} run playsound {snd} master @a ~ ~ ~ {f(vol)} {f(pit)}")
            else:
                p = d["pos"]
                ticks[t].append(f"playsound {snd} master @a {f(p[0])} {f(p[1])} {f(p[2])} {f(vol)} {f(pit)}")
        elif kind == "drop":
            p, v = d["pos"], d["vel"]
            ticks[t].append(f"summon minecraft:item {f(p[0])} {f(p[1])} {f(p[2])} "
                            f"{{Tags:[\"{NS}\"],PickupDelay:32767,Item:{item_nbt(d['model'])},"
                            f"Motion:[{f(v[0])}d,{f(v[1])}d,{f(v[2])}d]}}")

    # subtitles (actionbar, refreshed while the line is up), titles, overlays, time
    for (t0, t1, who, text) in F.subs:
        js = subtitle_json(F, who, text)
        for t in range(t0, min(t1, n), 30):
            ticks[t].append(f"title @a actionbar {js}")
        if t1 < n:
            nxt = [s for s in F.subs if s[0] == t1]
            if not nxt:
                ticks[t1].append('title @a actionbar ""')
    for (t, title, sub, fi, stay, fo) in F.titles:
        ticks[t].append(f"title @a times {fi} {stay} {fo}")
        ticks[t].append(f"title @a subtitle {jtext({'text': sub, 'color': '#E8E0C8'})}")
        ticks[t].append(f"title @a title {jtext({'text': title, 'color': '#FFFFFF'})}")
    for (t, name) in F.overlays:
        if t < n:
            ticks[t].append(overlay_cmd(name))
    times = sorted(F.times)
    for t in range(0, n, 20):
        dt = state_at(times, t, 1000)
        ticks[t].append(f"time set {dt}")

    for t in range(n):
        dp.fn(f"film/t/{t}", ticks[t] or ["# (nothing happens on this tick)"])

    # ---------------- control functions ----------------------------------------
    dp.fn("load", [
        f"scoreboard objectives add {NS}.t dummy",
        f'tellraw @a [{{"text":"[奇诺之旅] ","color":"gold"}},{{"text":"已加载。先运行 ","color":"gray"}},'
        f'{{"text":"/function {NS}:setup","color":"yellow"}},{{"text":" 搭建场景，再运行 ","color":"gray"}},'
        f'{{"text":"/function {NS}:play","color":"yellow"}}]',
    ])
    dp.fn("tick", [f"execute if score #playing {NS}.t matches 1 run function {NS}:film/step"])
    dp.fn("film/step", [
        f"kill @e[tag={NS}.gone]",
        f"scoreboard players add #f {NS}.t 1",
        f"execute store result storage {NS}:film f int 1 run scoreboard players get #f {NS}.t",
        f"function {NS}:film/run with storage {NS}:film",
        f"execute if score #f {NS}.t matches {n - 1}.. run function {NS}:stop",
    ])
    dp.fn("film/run", [f"$function {NS}:film/t/$(f)"])
    dp.fn("stop", [
        f"scoreboard players set #playing {NS}.t 0",
        "item replace entity @a armor.head with minecraft:air",
        'title @a actionbar ""',
        f'tellraw @a {{"text":"[奇诺之旅] 放映结束。/function {NS}:play 重新播放","color":"gold"}}',
    ])
    dp.fn("cleanup", [f"tp @e[tag={NS}.actor] ~ 330 ~", f"kill @e[tag={NS}]", f"scoreboard players set #playing {NS}.t 0"])

    # dynamic blocks: every position touched by an event, with its state at tick t
    base = worldlib.build()
    dyn = {}
    for (t, kind, d) in sorted([e for e in F.events if e[1] == "blocks"], key=lambda e: e[0]):
        for (x, y, z, st) in d["list"]:
            dyn.setdefault((x, y, z), [(-1, base.b.get((x, y, z)))]).append((t, st))

    def blocks_at(t):
        out = []
        for (x, y, z), ch in dyn.items():
            cur = None
            for (tt, st) in ch:
                if tt <= t:
                    cur = st
            out.append(block_cmd(x, y, z, cur))
        return out

    def seek_lines(T0):
        """Commands that reconstruct the complete film state at tick T0."""
        L = [f"tp @e[tag={NS}.actor] ~ 330 ~", f"kill @e[tag={NS}]", "gamemode spectator @a", "difficulty peaceful",
             "weather clear 1000000"]
        L += blocks_at(T0)
        c = S["cam"][T0]
        L.append(f"summon minecraft:item_display {f(c[0])} {f(c[1])} {f(c[2])} "
                 f'{{Tags:["{NS}","{NS}.cam"],teleport_duration:2,Rotation:[{f(c[3])}f,{f(c[4])}f]}}')
        L.append(f"tp @a {f(c[0])} {f(c[1])} {f(c[2])} {f(c[3])} {f(c[4])}")
        for pr in F.props.values():
            r = S["props"][pr.id][T0]
            if r is not None:
                L.append(summon_prop(pr, r))
        for a in F.actors.values():
            r = S["actors"][a.id][T0]
            if r is None:
                continue
            pose = state_at(a.poses, T0, "standing")
            L.append(summon_actor(a, r, pose, T0))
            s = sel_actor(a.id)
            ride = state_at(a.rides, T0)
            if ride:
                L.append(f"ride {s} mount {sel_prop(ride)}")
            for hand in ("main", "off"):
                cur = None
                for it in sorted(a.items, key=lambda i: i[0]):
                    if it[0] <= T0 and it[1] == hand:
                        cur = (it[2], it[3])
                if cur and cur[0]:
                    slot = "weapon.mainhand" if hand == "main" else "weapon.offhand"
                    L.append(f"item replace entity {s} {slot} with {item_stack(*cur)}")
        ov = state_at(sorted(F.overlays), T0, "letterbox")
        L.append(overlay_cmd(ov))
        L.append(f"time set {state_at(times, T0, 1000)}")
        L.append(f"scoreboard players set #f {NS}.t {T0 - 1}")
        L.append(f"schedule function {NS}:film/go 2t")
        return L

    dp.fn("film/go", [f"spectate @e[tag={NS}.cam,limit=1] @a", f"scoreboard players set #playing {NS}.t 1"])
    dp.fn("play", [f"function {NS}:scene/0"])
    index = []
    for k, (t0, name) in enumerate(F.scenes):
        dp.fn(f"scene/{k}", [f"# {name}"] + seek_lines(max(0, t0)))
        index.append(f'tellraw @a [{{"text":" {k:2d}  ","color":"yellow","clickEvent":{{"action":"run_command",'
                     f'"value":"/function {NS}:scene/{k}"}}}},{{"text":{jtext(name)},"color":"white"}},'
                     f'{{"text":"  {int(t0 / 20 // 60)}:{int(t0 / 20 % 60):02d}","color":"gray"}}]')
    dp.fn("scenes", ['tellraw @a {"text":"奇诺之旅 — 场景列表（点击跳转）","color":"gold"}'] + index)

    # ---------------- set builder --------------------------------------------
    write_tree_templates(root)
    static, plants = base.split()
    bx = boxlib.greedy_boxes(static)
    x0 = min(b[0] for b in bx) - 2
    x1 = max(b[3] for b in bx) + 2
    z0 = min(b[2] for b in bx) - 2
    z1 = max(b[5] for b in bx) + 2
    cmds = []
    for (a, b, c, d, e, g, st) in bx:
        if (a, b, c) == (d, e, g):
            cmds.append(f"setblock {a} {b} {c} minecraft:{st}")
        else:
            cmds.append(f"fill {a} {b} {c} {d} {e} {g} minecraft:{st}")
    for (name, x, y, z) in base.trees:
        cmds.append(f"place template {NS}:tree/{name} {x} {y} {z}")
    for (x, y, z), st in sorted(plants.items()):
        cmds.append(f"setblock {x} {y} {z} minecraft:{st} keep")
    per = 1500
    parts = [cmds[i:i + per] for i in range(0, len(cmds), per)]
    for i, part in enumerate(parts):
        nxt = [f"schedule function {NS}:build/part_{i + 1} 2t"] if i + 1 < len(parts) else [
            f"function {NS}:build/done"]
        dp.fn(f"build/part_{i}", [f'title @a actionbar {jtext({"text": f"搭建场景… {i + 1}/{len(parts)}", "color": "yellow"})}']
              + part + nxt)
    # biome (birch forest colours) + clear the air above the set first
    clear = []
    for (cx0, cz0, cx1, cz1) in chunked(x0, z0, x1, z1, 32):
        clear.append(f"fill {cx0} 60 {cz0} {cx1} 90 {cz1} minecraft:air")
    biome = []
    for (cx0, cz0, cx1, cz1) in chunked(x0, z0, x1, z1, 32):
        biome.append(f"fillbiome {cx0} 60 {cz0} {cx1} 91 {cz1} minecraft:birch_forest")
    forceload = []
    for (cx0, cz0, cx1, cz1) in chunked(x0, z0, x1, z1, 160):
        forceload.append(f"forceload add {cx0} {cz0} {cx1} {cz1}")
    dp.fn("setup", [
        'tellraw @a {"text":"[奇诺之旅] 开始搭建场景（约需一分钟，请保持在世界中）…","color":"gold"}',
        "gamemode spectator @a", "difficulty peaceful", "weather clear 1000000",
        f"function {NS}:rules/legacy", f"function {NS}:rules/modern",
    ] + forceload + [f"tp @a -80 90 -100", f"schedule function {NS}:build/clear 100t"])
    dp.fn("build/clear", clear + biome + [f"schedule function {NS}:build/part_0 2t"])
    dp.fn("build/done", [
        'title @a actionbar {"text":"场景搭建完成","color":"green"}',
        f'tellraw @a [{{"text":"[奇诺之旅] 场景已完成！运行 ","color":"gold"}},{{"text":"/function {NS}:play","color":"yellow",'
        f'"clickEvent":{{"action":"run_command","value":"/function {NS}:play"}}}},{{"text":" 开始放映，或 ","color":"gold"}},'
        f'{{"text":"/function {NS}:scenes","color":"yellow","clickEvent":{{"action":"run_command","value":"/function {NS}:scenes"}}}},'
        f'{{"text":" 选择场景。","color":"gold"}}]',
    ])
    # game rules changed names in newer versions; each set lives in its own file so
    # a parse error in one never breaks the rest of the pack
    dp.fn("rules/legacy", ["gamerule doDaylightCycle false", "gamerule doWeatherCycle false", "gamerule doMobSpawning false",
                           "gamerule commandModificationBlockLimit 2000000", "gamerule maxCommandChainLength 10000000"])
    dp.fn("rules/modern", ["gamerule advance_time false", "gamerule advance_weather false", "gamerule spawn_mobs false"])
    tags = os.path.join(root, "data", "minecraft", "tags", "function")
    os.makedirs(tags, exist_ok=True)
    with open(os.path.join(tags, "load.json"), "w") as fh:
        json.dump({"values": [f"{NS}:load"]}, fh)
    with open(os.path.join(tags, "tick.json"), "w") as fh:
        json.dump({"values": [f"{NS}:tick"]}, fh)
    total = sum(len(t) for t in ticks)
    print(f"datapack: {n} tick functions, {total} timeline commands, {len(cmds)} build commands in {len(parts)} parts, "
          f"{len(F.scenes)} scenes")


def chunked(x0, z0, x1, z1, step):
    out = []
    for a in range(x0, x1 + 1, step):
        for b in range(z0, z1 + 1, step):
            out.append((a, b, min(x1, a + step - 1), min(z1, b + step - 1)))
    return out
