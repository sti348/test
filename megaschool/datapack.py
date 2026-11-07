"""Small helper data pack shipped inside the world: viewpoints, day/night,
and a 'tiny player' mode (1.20.5+) that makes everything feel ten times bigger."""
from __future__ import annotations

import json
import os

import campus

NS = "wuya"

def viewpoints():
    """Teleport spots, derived from the generated layout."""
    L = campus.build()
    # an open-air corridor of the first teaching block east of the avenue
    slabs = [p for p in L.pieces if p.name == "slab" and p.x > 0 and p.z > campus.SOUTH_ZONE]
    p = min(slabs, key=lambda q: (q.x, q.z))
    side = p.kw["corridor_side"]
    zc = p.z + 3 + (p.kw["Dp"] - 3 if side == "S" else 2)       # corridor walkway (d = 2)
    floor = (p.kw["H"] // 4) // 2
    cy = campus.GROUND_Y + 4 * floor + 1
    tc = [q for q in L.pieces if q.name == "stand"][0]
    lib = [q for q in L.pieces if q.name == "library"][0]
    wt = [q for q in L.pieces if q.name == "water_tower"][0]
    fac = {q.name: q for q in L.pieces if q.name in ("lake_garden", "sports_park", "auditorium", "greenhouse", "bus_lot")}
    grove = sorted((q for q in L.pieces if q.name == "twilight_grove"), key=lambda q: abs(q.x) + abs(q.z))[0]
    ez = campus.ENDLESS_ROW * campus.PITCH + campus.ZOFF
    sx, sy, sz = campus.SPAWN
    return {
        # name: (x, y, z, yaw, pitch, label)
        "gate": (sx + 0.5, sy, sz + 0.5, 180, -12, "校门外（出生点）"),
        "plaza": (0.5, -60, campus.FLAG_Z + 70.5, 180, -20, "升旗广场"),
        "steps": (0.5, -54, 641.5, 180, -35, "主楼台阶与巨柱"),
        "canyon": (366.5, -60, campus.GATE_Z - 20.5, 180, -25, "东侧教学楼峡谷"),
        "corridor": (p.x + 20.5, cy, zc + 0.5, 270, 0, "教学楼外廊（%s）" % p.kw["name"]),
        "clock": (0.5, 250, 690.5, 180, 0, "钟楼正前方半空"),
        "roof": (200.5, 223, 570.5, 180, 10, "主楼屋顶"),
        "playground": (tc.x + 165.5, -38, tc.z + 14.5, 0, 5, "操场看台"),
        "library": (0.5, -60, lib.z1 + 32.5, 180, -30, "图书馆柱廊"),
        "endless": (40.5, -60, ez + 120.5, 230, -16, "无尽长廊楼"),
        "watertower": (wt.x + 36.5, -60, wt.z1 + 150.5, 180, -32, "巨型水塔"),
        "lake": (fac["lake_garden"].x + 196.5, -59, fac["lake_garden"].z + 40.5, 125, -6, "校园湖（湖心亭、拱桥）"),
        "pool": (fac["sports_park"].x + 42.5, -50, fac["sports_park"].z + 90.5, 180, 14, "游泳池跳台"),
        "auditorium": (fac["auditorium"].x + 100.5, -60, fac["auditorium"].z + 6.5, 0, -18, "大礼堂"),
        "greenhouse": (fac["greenhouse"].x + 99.5, -60, fac["greenhouse"].z + 160.5, 180, -8, "植物园温室"),
        "buses": (fac["bus_lot"].x + 150.5, -58, fac["bus_lot"].z + 40.5, 90, 4, "校车停车场"),
        "grove": (grove.x + 2.5, -60, grove.z + 96.5, 328, -5, "暮色树林"),
        "sky": (300.5, 230, 1160.5, 192, 22, "高空俯瞰"),
    }




def _w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def write(dst):
    VIEWPOINTS = viewpoints()
    funcs = {}
    funcs["welcome"] = "\n".join([
        'tellraw @s ["",{"text":"—— 无涯中学 ——","color":"gold","bold":true}]',
        'tellraw @s {"text":"暮色版：像暮色森林一样的永恒暮色，教室和路灯都亮着。建议渲染距离 16~32 区块。","color":"gray"}',
        'tellraw @s {"text":"/function wuya:help  查看传送点与玩法","color":"yellow"}',
        "tag @s add wuya_seen",
    ])
    lines = ['tellraw @s {"text":"—— 无涯中学 · 指令 ——","color":"gold"}']
    for k, v in VIEWPOINTS.items():
        lines.append('tellraw @s {"text":"/function wuya:tp/%s   %s","color":"aqua"}' % (k, v[5]))
    lines += [
        'tellraw @s {"text":"/function wuya:tiny     缩小成十分之一（1.20.5+），巨物感拉满","color":"light_purple"}',
        'tellraw @s {"text":"/function wuya:normal   恢复正常大小","color":"light_purple"}',
        'tellraw @s {"text":"/function wuya:day | wuya:dusk | wuya:night   切换时间","color":"green"}',
    ]
    funcs["help"] = "\n".join(lines)
    for k, (x, y, z, yaw, pitch, _) in VIEWPOINTS.items():
        funcs[f"tp/{k}"] = f"tp @s {x} {y} {z} {yaw} {pitch}"
    funcs["day"] = "time set 1000"
    funcs["dusk"] = "time set 13000"
    funcs["night"] = "time set 18000"
    funcs["tick"] = "execute as @a[tag=!wuya_seen] at @s run function wuya:welcome"
    # attribute was renamed in 1.21.2; only the variant that parses in the running
    # version loads, the function tags below call whichever exists.
    # the scale attribute exists since 1.20.5 and was renamed in 1.21.2: each
    # variant lives in a pack overlay that only the matching versions load.
    overlay_funcs = {
        "ov_generic_scale": {"scale/tiny": "attribute @s minecraft:generic.scale base set 0.1",
                             "scale/normal": "attribute @s minecraft:generic.scale base set 1"},
        "ov_scale": {"scale/tiny": "attribute @s minecraft:scale base set 0.1",
                     "scale/normal": "attribute @s minecraft:scale base set 1"},
    }
    funcs["tiny"] = "function #wuya:tiny\ntellraw @s {\"text\":\"你变小了。（需要 1.20.5 或更新版本）\",\"color\":\"light_purple\"}"
    funcs["normal"] = "function #wuya:normal"
    tags = {
        (NS, "tiny"): [f"{NS}:scale/tiny"],
        (NS, "normal"): [f"{NS}:scale/normal"],
        ("minecraft", "tick"): [f"{NS}:tick"],
    }
    for folder in ("function", "functions"):          # 1.21+ / 1.20.x
        for name, body in funcs.items():
            _w(os.path.join(dst, "data", NS, folder, name + ".mcfunction"), body + "\n")
        for (ns, name), vals in tags.items():
            _w(os.path.join(dst, "data", ns, "tags", folder, name + ".json"),
               json.dumps({"values": [{"id": v, "required": False} for v in vals]}, indent=1))
        for ov, fs in overlay_funcs.items():
            for name, body in fs.items():
                _w(os.path.join(dst, ov, "data", NS, folder, name + ".mcfunction"), body + "\n")
    import twilight
    tw_entries = twilight.write(dst)
    meta = {"pack": {"pack_format": 15, "supported_formats": [15, 1000], "min_format": 15, "max_format": 1000,
                     "description": "无涯中学 · 传送点与小人模式"},
            "overlays": {"entries": [
                {"formats": [41, 56], "min_format": 41, "max_format": 56, "directory": "ov_generic_scale"},
                {"formats": [57, 1000], "min_format": 57, "max_format": 1000, "directory": "ov_scale"},
            ] + tw_entries}}
    _w(os.path.join(dst, "pack.mcmeta"), json.dumps(meta, ensure_ascii=False, indent=1))
