"""Small helper data pack shipped inside the world: viewpoints, day/night,
and a 'tiny player' mode (1.20.5+) that makes everything feel ten times bigger."""
from __future__ import annotations

import json
import os

import campus

NS = "wuya"

def region_viewpoints():
    """Teleport spots in the new regions (beyond the campus and in the Nether)."""
    import regions as R
    px, pz = R.GATE_OW
    main = R.island_top("main")
    lh = R.island_top("lighthouse")
    big = R.SPHERES[0]
    floor = R.SEABED_DEEP - 20 + int(big[3] * 0.45) + 1
    v = {
        "portal": (px + 70.5, -60, pz + 0.5, 90, -18, "巨型地狱门"),
        "sinkhole": (R.SX + 445.5, -60, R.SZ + 0.5, 90, 35, "天坑边缘"),
        "sinkhole_bridge": (R.SX + 220.5, -60, R.SZ + 0.5, 90, 25, "天坑上的桥"),
        "sinkhole_floor": (R.SX + 70.5, R.LEDGES[0][1] + 1, R.SZ + 60.5, 135, -45, "天坑底"),
        "archipelago": (main[1] + 0.5, main[5] + 1, main[2] + 300.5, 180, -14, "海上学院（主岛）"),
        "sea_dorms": (R.island_top("dorm")[1] + 0.5, R.island_top("dorm")[5] + 1, R.island_top("dorm")[2] + 170.5, 180, -10, "宿舍岛"),
        "sea_library": (R.island_top("library")[1] + 0.5, R.island_top("library")[5] + 1, R.island_top("library")[2] + 110.5, 180, -12, "图书馆岛"),
        "lighthouse": (lh[1] + 0.5, lh[5] + 1 + 482, lh[2] + 25.5, 180, 20, "灯塔顶"),
        "sea_surface": (big[1] + 0.5, R.SEA + 2, big[2] + 8.5, 0, 10, "海面浮台（旁边的升降管里有梯子直通海底玻璃球）"),
        "sphere": (big[1] + 20.5, floor, big[2] + 40.5, 200, -25, "海底玻璃球学校"),
        "sphere_dorm": (R.SPHERES[1][1] + 58.5, floor + 30, R.SPHERES[1][2] + 62.5, 136, 14, "海底宿舍球（悬在半空俯看）"),
        "sphere_library": (R.SPHERES[2][1] + 0.5, floor, R.SPHERES[2][2] + 76.5, 180, -15, "海底图书馆球"),
        "sinkhole_library": (R.SX - 190.5, R.LEDGES[0][1] + 1, R.SZ + 90.5, 180, -20, "天坑底的图书馆"),
        "desert": (R.PYR[0] + 0.5, -60, -2130.5, 180, -16, "沙漠学校（金字塔大道）"),
        "pyramid": (R.PYR[0] + 0.5, -60, R.PYR[1] + 300.5, 180, -55, "金字塔正门"),
        "oasis": (R.OASIS[0] + 0.5, -60, R.OASIS[1] + 110.5, 160, -10, "绿洲"),
        "sky_stair": (R.SKY[0][0] + 0.5, -60, R.SKY[0][1] + R.SKY[0][2] + 30.5, 180, -40, "通往空岛的螺旋阶梯"),
    }
    names = ["sky1", "sky2", "sky3", "sky4", "end"]
    labels = ["第一座空岛（y400）", "第二座空岛（y720）", "第三座空岛（y1040）", "第四座空岛（y1360）", "末地空岛（y1720）"]
    for k, (x, z, Rr, top, _s, _r) in enumerate(R.SKY):
        v[names[k]] = (x + 0.5, top + 1, z + int(Rr * 0.8) + 0.5, 180, -14, labels[k])
    gx, gz = R.GATE_NE
    v["nether"] = (gx + 60.5, R.NETHER_FLOOR, gz + 0.5, 90, -15, "地狱学校（下界门前）", "the_nether")
    ax, az = R.ACADEMY_NE
    v["nether_academy"] = (ax + 222.5, R.NETHER_FLOOR, az + 70.5, 108, -30, "地狱学院（黑石金字塔）", "the_nether")
    import eclipse
    v["eclipse"] = eclipse.viewpoint()
    v["nether_library"] = (R.NE_LIBRARY[0] + 0.5, R.NETHER_FLOOR, R.NE_LIBRARY[1] + 100.5, 180, -15, "地狱图书馆", "the_nether")
    return v


def viewpoints():
    """Teleport spots, derived from the generated layout."""
    L = campus.build()
    # an open-air corridor of the first teaching block east of the avenue
    slabs = [p for p in L.pieces if p.name == "slab" and p.x > 0 and p.z > campus.SOUTH_ZONE]
    p = min(slabs, key=lambda q: (q.x, q.z))
    side = p.kw["corridor_side"]
    zc = p.z + 3 + (p.kw["Dp"] - 3 if side == "S" else 2)       # corridor walkway (d = 2)
    floor = (p.kw["H"] // 8) // 2                     # facades are drawn at 2x: 8-block storeys
    cy = campus.GROUND_Y + 8 * floor + 2
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
        "plaza": (0.5, -60, campus.FLAG_Z + 45.5, 180, -20, "升旗广场"),
        "tower": (0.5, -60, 566.5, 180, -42, "学习塔脚下（弯弓楼正中）"),
        "bow_corridor": (300.5, -19, 498.5, 90, 0, "弯弓楼外廊（第 6 层）"),
        "canyon": (366.5, -60, campus.GATE_Z - 20.5, 180, -25, "东侧教学楼峡谷"),
        "corridor": (p.x + 14 + ((p.kw["L"] - 28) % 40) // 2 + 20.5, cy, zc + 0.5, 270, 0, "教学楼外廊（%s）" % p.kw["name"]),
        "tower_air": (0.5, 380, 760.5, 180, 0, "学习塔正前方半空"),
        "roof": (260.5, 174, 470.5, 200, 6, "弯弓楼屋顶"),
        "playground": (tc.x + 165.5, -38, tc.z + 14.5, 0, 5, "操场看台"),
        "library": (0.5, -60, lib.z1 + 32.5, 180, -30, "图书馆柱廊"),
        "endless": (40.5, -60, ez + 120.5, 230, -16, "无尽长廊楼"),
        "watertower": (wt.x + 36.5, -36, wt.z1 + 170.5, 180, -24, "巨型水塔"),
        "lake": (fac["lake_garden"].x + 196.5, -59, fac["lake_garden"].z + 40.5, 125, -6, "校园湖（湖心亭、拱桥）"),
        "pool": (fac["sports_park"].x + 42.5, -50, fac["sports_park"].z + 90.5, 180, 14, "游泳池跳台"),
        "auditorium": (fac["auditorium"].x + 100.5, -60, fac["auditorium"].z + 6.5, 0, -18, "大礼堂"),
        "greenhouse": (fac["greenhouse"].x + 99.5, -60, fac["greenhouse"].z + 160.5, 180, -8, "植物园温室"),
        "buses": (fac["bus_lot"].x + 150.5, -58, fac["bus_lot"].z + 40.5, 90, 4, "校车停车场"),
        "grove": (grove.x + 2.5, -60, grove.z + 96.5, 328, -5, "暮色树林"),
        "sky": (300.5, 330, 1260.5, 192, 12, "高空俯瞰"),
        **region_viewpoints(),
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
    for k, vp in VIEWPOINTS.items():
        x, y, z, yaw, pitch = vp[:5]
        dim = vp[6] if len(vp) > 6 else "overworld"
        funcs[f"tp/{k}"] = f"execute in minecraft:{dim} run tp @s {x} {y} {z} {yaw} {pitch}"
        if k == "eclipse":                     # the key art is lit by the sun just behind the top island
            import eclipse
            funcs[f"tp/{k}"] += f"\ntime set {eclipse.SUN_TIME}"
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
