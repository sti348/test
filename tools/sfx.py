"""Sound design shared by the data pack (playsound commands) and the preview
mix (tools/audio.py mixes the very same vanilla / resource-pack sound files).

  SFX            script sound key -> layers of real sound events
  auto_events()  footsteps (by surface, wading in the flooded ruins), engine
                 loops, ambience (birds, water, drips, campfire)
  voice_events() the Japanese dub lines, one per subtitle
  write_sounds_json()  resourcepack/assets/kino/sounds.json
"""
from __future__ import annotations

import hashlib
import json
import math
import os

from film import state_at

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP_SOUNDS = os.path.join(ROOT, "resourcepack", "assets", "kino")
M = "minecraft:"

# key -> [(sound event, volume factor, pitch factor[, delay ticks])]
SFX = {
    # ---- weapons
    "kino.gun_rifle": [(M + "entity.firework_rocket.large_blast", 1.0, 0.72), (M + "entity.generic.explode", 0.25, 1.9)],
    "kino.gun_rifle_far": [(M + "entity.firework_rocket.large_blast_far", 1.0, 0.72),
                           (M + "entity.firework_rocket.blast_far", 0.5, 0.6, 3)],
    "kino.gun_pistol": [(M + "entity.firework_rocket.blast", 1.0, 0.8), (M + "entity.generic.explode", 0.12, 2.0)],
    "kino.gun_pistol_far": [(M + "entity.firework_rocket.blast_far", 1.0, 0.8)],
    "kino.gun_suppressed": [(M + "item.crossbow.shoot", 1.0, 0.55), (M + "entity.firework_rocket.blast", 0.1, 1.7)],
    "kino.bolt": [(M + "item.crossbow.loading_end", 0.7, 1.5), (M + "block.iron_trapdoor.close", 0.25, 1.9, 4)],
    "kino.assemble": [(M + "item.crossbow.loading_middle", 0.8, 1.2), (M + "block.tripwire.click_on", 0.6, 1.6, 10)],
    "kino.holster": [(M + "item.armor.equip_leather", 0.8, 1.2)],
    "kino.bullet_hit": [(M + "entity.arrow.hit", 1.0, 0.8), (M + "entity.player.hurt", 0.5, 0.8, 1)],
    "kino.cannon": [(M + "entity.generic.explode", 1.0, 0.6), (M + "entity.firework_rocket.large_blast_far", 1.0, 0.5, 2)],
    "kino.explosion": [(M + "entity.generic.explode", 1.0, 0.5), (M + "entity.generic.explode", 0.6, 0.7, 4),
                       (M + "block.fire.extinguish", 0.5, 0.6, 10)],
    "kino.fuse": [(M + "entity.tnt.primed", 1.0, 0.75)],
    "kino.ignite": [(M + "item.firecharge.use", 1.0, 0.8)],
    "kino.fire": [(M + "block.fire.ambient", 1.0, 1.0)],
    "kino.burn_hurt": [(M + "entity.player.hurt_on_fire", 1.0, 0.8)],
    "kino.metal": [(M + "block.chain.place", 0.8, 0.8), (M + "item.armor.equip_iron", 0.7, 0.9, 5)],
    "kino.drop_metal": [(M + "block.chain.fall", 1.0, 0.8)],
    "kino.cannon_roll": [(M + "block.grindstone.use", 0.5, 0.5), (M + "block.wood.step", 0.8, 0.6, 6)],
    # ---- bodies
    "kino.kick": [(M + "entity.player.attack.knockback", 1.0, 1.0)],
    "kino.punch": [(M + "entity.player.attack.strong", 1.0, 0.9), (M + "entity.player.hurt", 0.5, 0.9, 1)],
    "kino.hit": [(M + "entity.player.attack.crit", 1.0, 0.7), (M + "entity.player.hurt", 0.7, 0.8, 1)],
    "kino.stab": [(M + "item.trident.hit", 1.0, 0.8), (M + "entity.player.hurt", 0.7, 0.8, 2)],
    "kino.axe": [(M + "item.axe.strip", 0.9, 0.7), (M + "entity.player.attack.crit", 1.0, 0.6), (M + "entity.player.hurt", 0.7, 0.7, 2)],
    "kino.snap": [(M + "block.bone_block.break", 1.0, 0.8)],
    "kino.fall": [(M + "entity.player.big_fall", 1.0, 0.9)],
    "kino.fall_water": [(M + "entity.player.splash", 0.8, 1.0), (M + "entity.player.big_fall", 0.5, 0.8)],
    "kino.splash": [(M + "entity.generic.splash", 1.0, 1.0)],
    "kino.small_splash": [(M + "entity.player.swim", 1.0, 1.4)],
    "kino.choke": [(M + "entity.player.hurt_drown", 1.0, 0.8)],
    "kino.hurt": [(M + "entity.player.hurt", 1.0, 0.9)],
    "kino.cloth": [(M + "item.armor.equip_generic", 1.0, 1.0)],
    "kino.bag": [(M + "item.armor.equip_leather", 1.0, 0.9), (M + "item.bundle.remove_one", 0.6, 1.0, 8)],
    # ---- objects
    "kino.door_open": [(M + "block.wooden_door.open", 1.0, 0.9)],
    "kino.door_close": [(M + "block.wooden_door.close", 1.0, 0.9)],
    "kino.tailgate": [(M + "block.iron_trapdoor.open", 1.0, 0.7), (M + "block.chain.place", 0.5, 0.8, 4)],
    "kino.truck_door": [(M + "block.iron_door.close", 1.0, 0.8)],
    "kino.bed": [(M + "block.wool.step", 1.0, 0.8), (M + "block.wood.step", 0.5, 0.7)],
    "kino.radio_on": [(M + "block.lever.click", 0.8, 1.4), (M + "block.note_block.bit", 0.5, 1.5, 3),
                      (M + "block.note_block.bit", 0.5, 1.5, 6)],
    "kino.radio": [("kino:sfx.radio", 1.0, 1.0)],
    "kino.spyglass": [(M + "item.spyglass.use", 1.0, 1.0)],
    "kino.spyglass_off": [(M + "item.spyglass.stop_using", 1.0, 1.0)],
    "kino.stone": [(M + "block.stone.break", 1.0, 0.8), (M + "block.stone.place", 0.8, 0.7, 5), (M + "block.gravel.break", 0.7, 0.8, 9)],
    "kino.logs": [(M + "block.wood.break", 1.0, 0.6), (M + "block.wood.place", 0.8, 0.7, 7)],
    "kino.pour": [(M + "item.bottle.empty", 1.0, 0.9)],
    "kino.cork": [(M + "entity.chicken.egg", 1.0, 1.3)],
    "kino.drink": [(M + "entity.generic.drink", 1.0, 1.0)],
    "kino.clink": [(M + "block.decorated_pot.hit", 1.0, 1.4), (M + "block.decorated_pot.hit", 0.7, 1.6, 2)],
    "kino.mug_drop": [(M + "block.decorated_pot.fall", 1.0, 1.1)],
    "kino.baby_cry": [(M + "entity.cat.stray_ambient", 1.0, 1.0)],
    "kino.kickstand": [(M + "block.iron_trapdoor.close", 0.7, 1.3)],
    "kino.brake": [(M + "block.grindstone.use", 1.0, 0.6)],
    # ---- engines / custom
    "kino.kickstart": [("kino:sfx.engine_start", 1.0, 1.0)],
    "kino.engine_bike": [("kino:sfx.engine_bike", 1.0, 1.0)],
    "kino.engine_truck": [("kino:sfx.engine_truck", 1.0, 1.0)],
    "kino.birds": [("kino:sfx.birds", 1.0, 1.0)],
    "kino.wind": [("kino:sfx.wind", 1.0, 1.0)],
    "kino.water": [(M + "block.water.ambient", 1.0, 1.0)],
    "kino.drip": [(M + "block.pointed_dripstone.drip_water", 1.0, 1.0)],
    "kino.campfire": [(M + "block.campfire.crackle", 1.0, 1.0)],
    "kino.music_theme": [("kino:music.theme", 1.0, 1.0)],
    "kino.music_ending": [("kino:music.ending", 1.0, 1.0)],
    # ---- footsteps
    "step.grass": [(M + "block.grass.step", 1.0, 1.0)],
    "step.gravel": [(M + "block.gravel.step", 1.0, 1.0)],
    "step.stone": [(M + "block.stone.step", 1.0, 1.0)],
    "step.wood": [(M + "block.wood.step", 1.0, 1.0)],
    "step.water": [(M + "entity.player.swim", 0.55, 1.35), (M + "block.stone.step", 0.25, 0.9)],
}

# sound category per key prefix (data pack), and which keys are ambience (ducked under dialogue in the mix)
CATEGORY = {"step.": "neutral", "kino.birds": "ambient", "kino.wind": "ambient", "kino.water": "ambient", "kino.drip": "ambient",
            "kino.campfire": "ambient", "kino.music": "music", "kino.engine": "neutral"}
AMBIENT = ("kino.birds", "kino.wind", "kino.water", "kino.drip", "kino.campfire", "kino.engine_bike", "kino.engine_truck",
           "step.")

# custom sound events of the resource pack (files are made by tools/sfx_synth.py)
CUSTOM = {
    "sfx.engine_bike": ["sfx/engine_bike"],
    "sfx.engine_truck": ["sfx/engine_truck"],
    "sfx.engine_start": ["sfx/engine_start"],
    "sfx.birds": ["sfx/birds1", "sfx/birds2", "sfx/birds3", "sfx/birds4", "sfx/birds5"],
    "sfx.wind": ["sfx/wind"],
    "sfx.radio": ["sfx/radio"],
    "music.theme": ["music/theme"],
    "music.ending": ["music/ending"],
}
ENGINE_LOOP = 2.0     # seconds (length of engine_*.ogg at pitch 1)


def category(key):
    for p, c in CATEGORY.items():
        if key.startswith(p):
            return c
    return "master"


def is_ambient(key):
    return any(key.startswith(p) for p in AMBIENT)


def rnd(*xs):
    """Deterministic 0..1 from arbitrary values."""
    h = hashlib.md5(repr(xs).encode()).digest()
    return int.from_bytes(h[:4], "little") / 2 ** 32


# ----------------------------------------------------------------------------
def voice_index():
    p = os.path.join(ROOT, "tools", "voice_index.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def voice_events(F):
    """[(tick, id, duration_s, speaker)] for every subtitle that has a recorded line."""
    idx = voice_index()
    out = []
    for (t0, _t1, who, text) in F.subs:
        v = idx.get(f"{who}|{text}")
        if v and t0 < F.length:
            out.append((t0, v["id"], v["dur"], who))
    return sorted(out)


def write_sounds_json():
    js = {}
    for ev, files in CUSTOM.items():
        stream = ev.startswith("music.")
        js[ev] = {"sounds": [{"name": "kino:" + f, "stream": True} if stream else "kino:" + f for f in files]}
        if ev == "sfx.birds":
            js[ev]["sounds"] = [{"name": "kino:" + f, "attenuation_distance": 24} for f in files]
    for v in sorted(voice_index().values(), key=lambda v: v["id"]):
        js["voice." + v["id"]] = {"sounds": [{"name": "kino:voice/" + v["id"], "stream": True}]}
    with open(os.path.join(RP_SOUNDS, "sounds.json"), "w", encoding="utf-8") as fh:
        json.dump(js, fh, indent=1)
    return js


# ----------------------------------------------------------------------------
def surface(block):
    if not block:
        return None
    if "water" in block and "waterlogged=false" not in block:
        return "step.water"
    for key, names in (("step.grass", ("grass_block", "dirt_path", "moss", "leaves", "short_grass", "fern")),
                       ("step.gravel", ("dirt", "gravel", "podzol", "mud", "farmland")),
                       ("step.wood", ("planks", "_log", "_wood", "carpet", "wool", "barrel", "crafting"))):
        if any(n in block for n in names):
            return key
    return "step.stone"


def footsteps(F, S, blocks):
    ev = []
    for a in F.actors.values():
        rows = S["actors"][a.id]
        prev = None
        last_step = None
        for t, r in enumerate(rows):
            if r is None:
                prev, last_step = None, None
                continue
            if prev is None or state_at(a.rides, t) or state_at(a.poses, t, "standing") in ("swimming", "sleeping"):
                prev = r
                last_step = math.floor(r[5] / 4.716)
                continue
            d = math.hypot(r[0] - prev[0], r[2] - prev[2])
            k = math.floor(r[5] / 4.716)
            if k != last_step and d > 0.02 and d < 1.2:
                x, y, z = r[0], r[1], r[2]
                blk = None
                for dy in (0.05, 0.55):
                    b = blocks.get((math.floor(x), math.floor(y - dy), math.floor(z)))
                    if b and not any(n in b for n in ("short_grass", "fern", "light", "flower", "poppy", "dandelion")):
                        blk = b
                        break
                key = surface(blk) or "step.grass"
                if key == "step.grass" and blocks.get((math.floor(x), math.floor(y), math.floor(z)), "").startswith(("short_grass", "fern")):
                    key = "step.grass"
                run = d * 20 > 4.0
                crouch = state_at(a.poses, t, "standing") == "crouching"
                vol = (0.55 if run else 0.38) * (0.5 if crouch else 1.0)
                if a.id == "kino":
                    vol *= 1.1
                pitch = 0.92 + 0.16 * rnd(a.id, t)
                ev.append((t, "sound", {"sound": key, "pos": [round(x, 2), round(y, 2), round(z, 2)], "vol": round(vol, 2),
                                        "pitch": round(pitch, 3), "auto": True}))
            last_step = k
            prev = r
    return ev


def engines(F, S):
    ev = []
    for (t0, t1, pid, vol, pitch) in getattr(F, "engines", []):
        rows = S["props"][pid]
        key = "kino.engine_truck" if pid == "truck" else "kino.engine_bike"
        t = t0
        while t < t1:
            r0, r1 = rows[max(0, t - 2)], rows[min(len(rows) - 1, t + 2)]
            v = math.hypot(r1[0] - r0[0], r1[2] - r0[2]) * 5 if (r0 and r1) else 0.0
            p = pitch * (0.9 + 0.45 * min(1.0, v / 9.0))
            # quantise the pitch so the (pitch-scaled) loop lasts a whole number of ticks:
            # retriggered every N ticks it then joins seamlessly
            N = max(20, min(80, round(ENGINE_LOOP * 20 / p)))
            p = ENGINE_LOOP * 20 / N
            ev.append((t, "sound", {"sound": key, "follow": pid, "vol": vol, "pitch": round(p, 4), "auto": True}))
            t += N
    return ev


def in_plaza(c):
    return -121 <= c[0] <= -39 and -153 <= c[2] <= -71


def in_keep(c):
    return -88 <= c[0] <= -72 and -147 <= c[2] <= -131 and c[1] < 72


def in_forest(c):
    return (-160 <= c[0] <= 245 and -40 <= c[2] <= 40) or (-100 <= c[0] <= -55 and -75 <= c[2] <= -30)


def ambience(F, S, blocks):
    """Birds in the forest (by day), water and drips in the ruins, the enemy campfire."""
    ev = []
    n = S["n"]
    times = sorted(F.times)
    water_cells = [k for k, v in blocks.items() if v and "waterlogged=true" in v]
    camp = (-84.0, 65.5, -62.0)
    next_bird, next_water, next_drip, next_fire = 0, 0, 0, 0
    for t in range(0, n):
        c = S["cam"][t]
        day = state_at(times, t, 1000)
        inn = c[0] > 280 and abs(c[2]) < 12
        if (in_forest(c) or inn) and not in_plaza(c) and t >= next_bird:
            a = rnd("bird", t) * 2 * math.pi
            r = 7 + 9 * rnd("birdr", t)
            pos = [round(c[0] + math.sin(a) * r, 1), 72.0 + 4 * rnd("birdy", t), round(c[2] + math.cos(a) * r, 1)]
            dusk = day >= 11500 or inn          # (inside the inn: only now and then, through the window)
            ev.append((t, "sound", {"sound": "kino.birds", "pos": pos, "vol": 0.9 if not dusk else 0.6,
                                    "pitch": round(0.9 + 0.25 * rnd("birdp", t), 3), "auto": True}))
            next_bird = t + int(20 * ((3.0 if not dusk else 7.0) + 4.0 * rnd("birdn", t)))
        if in_plaza(c) and t >= next_water:
            # a waterlogged cell 3-10 blocks from the camera
            for k in range(12):
                a = rnd("wa", t, k) * 2 * math.pi
                r = 3 + 7 * rnd("wr", t, k)
                q = (math.floor(c[0] + math.sin(a) * r), 64, math.floor(c[2] + math.cos(a) * r))
                if q in blocks and "waterlogged=true" in (blocks[q] or ""):
                    ev.append((t, "sound", {"sound": "kino.water", "pos": [q[0] + 0.5, 64.6, q[2] + 0.5], "vol": 0.45,
                                            "pitch": round(0.8 + 0.4 * rnd("wp", t), 3), "auto": True}))
                    break
            next_water = t + int(20 * (1.6 + 2.0 * rnd("wn", t)))
        if in_keep(c) and t >= next_drip:
            ev.append((t, "sound", {"sound": "kino.drip", "pos": [round(c[0] + 4 * rnd("dx", t) - 2, 1), 67.5,
                                                                  round(c[2] + 4 * rnd("dz", t) - 2, 1)],
                                    "vol": 0.7, "pitch": round(0.8 + 0.5 * rnd("dp", t), 3), "auto": True}))
            next_drip = t + int(20 * (1.2 + 2.5 * rnd("dn", t)))
        if math.dist(c[:3], camp) < 22 and t >= next_fire:
            ev.append((t, "sound", {"sound": "kino.campfire", "pos": list(camp), "vol": 1.2,
                                    "pitch": round(0.9 + 0.2 * rnd("fp", t), 3), "auto": True}))
            next_fire = t + int(20 * (0.8 + 1.2 * rnd("fn", t)))
    return ev


def auto_events(F, S):
    import world
    blocks = world.build().b
    ev = footsteps(F, S, blocks) + engines(F, S) + ambience(F, S, blocks)
    return ev
