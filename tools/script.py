"""The film: Kino's Journey, chapter 7 "The Tale of Fighters —Reasonable—",
staged in Minecraft.  Builds a Film object (see film.py)."""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import world  # noqa: E402
from film import Cam, Film, T, look_angles, yaw_of  # noqa: E402

G = world.GROUND + 1          # standing height on grass/earth
W = world.GROUND + 0.5        # standing height on the flooded slabs
BIKE = 0.63                   # item_display height above the ground (rider seat)
EYE = 1.62

SPEAKERS = {
    "奇诺": "#f2d27a", "艾鲁梅斯": "#9fd8ff", "胡须男": "#e0b080", "医生": "#bfe3c0", "女子": "#ffb8c8",
    "男子": "#d8d8d8", "年轻男子": "#d8d8d8", "狙击兵": "#d8c090", "部下": "#d8c090", "屋顶的男子": "#d8d8d8",
    "旁白": "#e8e0c8", "男子们": "#d8d8d8", "伤兵": "#d8c090", "山贼": "#c8a070",
}


def dist(a, b):
    return math.dist(a, b)


def arc(cx, cz, r, a0, a1, n=8, y=G):
    """Points on a circle (angles in degrees, 0 = +z, 90 = -x like Minecraft yaw)."""
    out = []
    for k in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * k / n)
        out.append((cx - math.sin(a) * r, y, cz + math.cos(a) * r))
    return out


def build():
    F = Film("奇诺之旅")
    F.speakers = SPEAKERS

    # ------------------------------------------------------------------ cast
    K = F.actor("kino", "kino", slim=True, label="奇诺")
    H = F.prop("hermes", "hermes", translation=(0, -0.13, 0))
    TRUCK = F.prop("truck", "truck", translation=(0, 1.0, 0), scale=2.0, view_range=6.0)
    CAP = F.actor("captain", "captain", label="胡须男")
    guards = {}
    gskins = ["guard_a", "guard_b", "guard_c"]
    for i in range(1, 11):
        guards[i] = F.actor(f"g{i}", gskins[(i - 1) % 3], label="部下")
    SNIPER = F.actor("sniper", "sniper", label="狙击兵")
    DOC = F.actor("doctor", "doctor", label="医生")
    WOMAN = F.actor("woman", "woman", slim=True, label="女子")
    rskins = {1: "retainer_a", 2: "retainer_b", 3: "retainer_c", 4: "retainer_b", 5: "retainer_c", 6: "retainer_b", 7: "retainer_c"}
    R = {i: F.actor(f"r{i}", rskins[i], label="男子") for i in range(1, 8)}
    seats = {}

    def seat(name):
        if name not in seats:
            seats[name] = F.prop("seat_" + name, None)
        return seats[name]

    # ---------------------------------------------------------- utilities
    def ride_to(prop, t0, pts, speed, kind="linear", y=None):
        L = sum(dist(pts[i][::2], pts[i + 1][::2]) for i in range(len(pts) - 1))
        t1 = t0 + max(1, T(L / speed))
        prop.move(t0, t1, pts, ease_kind=kind)
        return t1

    def walk(a, t0, pts, speed=2.6, kind="linear", yaw=None):
        L = sum(dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
        t1 = t0 + max(1, T(L / speed))
        a.move(t0, t1, pts, ease_kind=kind, yaw=yaw)
        return t1

    def side_of(prop, t, right=0.0, back=0.0, up=0.0):
        p = prop.track.at(t)
        r = math.radians(p[3])
        fx, fz = -math.sin(r), math.cos(r)
        rx, rz = -fz, fx
        return (p[0] + rx * right - fx * back, p[1] + up, p[2] + rz * right - fz * back)

    def attach(a, prop, t0, t1, right, back, up, dyaw=0.0):
        """Keep an entity at a local offset of a moving prop (for seats on the truck)."""
        def fn(t):
            p = prop.track.at(t)
            r = math.radians(p[3])
            fx, fz = -math.sin(r), math.cos(r)
            rx, rz = -fz, fx
            return (p[0] + rx * right - fx * back, p[1] + up, p[2] + rz * right - fz * back, p[3] + dyaw, 0.0)
        a.track.add(t0, t1, fn)

    arc_ = arc

    def mount(t):
        K.ride(t, H)
        sfx(t, "kino.cloth", follow="hermes", vol=0.5)

    def dismount(t, right=-0.9, back=0.3):
        """Kino steps off to the left side of Hermes (and puts the stand down)."""
        K.ride(t, None)
        sfx(t + T(0.35), "kino.kickstand", follow="hermes", vol=0.8)
        p = side_of(H, t, right=right, back=back)
        K.place(t, (p[0], p[1] - BIKE, p[2]), H.track.at(t)[3])

    def head(eid, t, dy=1.55):
        return F.point(eid, t)

    # ---------------- occlusion-aware camera placement ----------------
    wb = world.build()
    SOLID = {k for k, v in wb.b.items() if v and not any(n in v for n in ("short_grass", "fern", "light", "dandelion", "poppy",
                                                                          "daisy", "bluet", "cornflower", "carpet"))}
    SLABS = {k for k, v in wb.b.items() if v and "slab" in v and "type=bottom" in v}
    PROP_BOX = {"truck": (1.25, 3.0, 2.9), "hermes": (0.55, 1.35, 1.5), "cannon": (1.3, 1.4, 1.1)}

    def blocked(q, t, ignore):
        return hit(q, t, ignore) is not None

    def hit(q, t, ignore):
        bx, by, bz = math.floor(q[0]), math.floor(q[1]), math.floor(q[2])
        if (bx, by, bz) in SOLID:
            if (bx, by, bz) not in SLABS or q[1] - by < 0.55:
                return "block"
        for a in F.actors.values():
            if a.id in ignore:
                continue
            from film import state_at
            if not state_at(a.visible, t, False):
                continue
            ap = F.world_pose(a, t)
            if ap is None:
                continue
            if abs(q[0] - ap[0]) < 0.42 and abs(q[2] - ap[2]) < 0.42 and ap[1] - 0.1 < q[1] < ap[1] + 1.95:
                return "actor"
        for pid, (hw, hl, hh) in PROP_BOX.items():
            pr = F.props.get(pid)
            if not pr or pid in ignore:
                continue
            from film import state_at
            if not state_at(pr.visible, t, False):
                continue
            pp = pr.track.at(t)
            if pp is None:
                continue
            r = math.radians(pp[3])
            fx, fz = -math.sin(r), math.cos(r)
            dx, dz = q[0] - pp[0], q[2] - pp[2]
            along = dx * fx + dz * fz
            across = dx * fz - dz * fx
            base = pp[1] - (BIKE if pid == "hermes" else 0)
            if abs(along) < hl and abs(across) < hw and base - 0.1 < q[1] < base + hh:
                return "prop"
        return None

    def clear_view(cpos, tgt, t, ignore):
        if blocked(cpos, t, ignore):
            return False
        L = math.dist(cpos, tgt)
        n = max(2, int(L / 0.15))
        for k in range(1, n):
            u = k / n
            if L * (1 - u) < 0.35:
                break
            q = tuple(cpos[i] + (tgt[i] - cpos[i]) * u for i in range(3))
            if blocked(q, t, ignore):
                return False
        return True

    W8 = {"block": 10, "prop": 10, "actor": 2}

    def vscore(c, tgt, t, ignore):
        if blocked(c, t, ignore):
            return 1000
        L = math.dist(c, tgt)
        n = max(2, int(L / 0.15))
        bad = 0
        for k in range(1, n):
            u = k / n
            if L * (1 - u) < 0.35:
                break
            h_ = hit(tuple(c[i] + (tgt[i] - c[i]) * u for i in range(3)), t, ignore)
            if h_:
                bad += W8[h_]
        # clutter: somebody's head right in front of the lens
        vx, vz = tgt[0] - c[0], tgt[2] - c[2]
        vl = math.hypot(vx, vz) or 1
        from film import state_at
        for a in F.actors.values():
            if a.id in ignore or not state_at(a.visible, t, False):
                continue
            ap = F.world_pose(a, t)
            if ap is None:
                continue
            dx, dz = ap[0] - c[0], ap[2] - c[2]
            d = math.hypot(dx, dz)
            if d < 2.0 and (dx * vx + dz * vz) / (vl * max(d, 1e-6)) > 0.5:
                bad += 2
        return bad

    def pick(cands, tgt, t, ignore):
        best, bs = cands[0], 10 ** 9
        for c in cands:
            sc = vscore(c, tgt, t, ignore)
            if sc == 0:
                return c
            if sc < bs:
                best, bs = c, sc
        if os.environ.get("CAMDEBUG") and bs >= 10:
            print("camera compromise", t, [round(v, 1) for v in tgt], ignore, bs, [round(v, 1) for v in best])
        return best

    def S(pos_, look, t=None, ignore=()):
        """Static camera, nudged if something blocks the view of the look target."""
        t = F.cursor if t is None else t
        tgt = F.point(look, t) if not (isinstance(look, tuple) and len(look) == 2 and not isinstance(look[0], str)) else None
        if tgt is None:
            return Cam.static(pos_, look)
        ign = set(ignore) | ({look} if isinstance(look, str) else ({look[0]} if isinstance(look[0], str) else set()))
        cands = [tuple(pos_)]
        for r in (0.4, 0.8, 1.2):
            for (dx, dy, dz) in ((0, r * 0.5, 0), (r, 0, 0), (-r, 0, 0), (0, 0, r), (0, 0, -r), (r, 0, r), (-r, 0, -r), (r, 0, -r), (-r, 0, r)):
                cands.append((pos_[0] + dx, pos_[1] + dy, pos_[2] + dz))
        return Cam.static(pick(cands, tgt, t, ign), look)

    def close(eid, t, dist_=2.2, ang=25, dy=0.05, height=None, look_dy=0.0):
        """Close shot from in front of an actor (ang: degrees to the actor's left), avoiding occluders."""
        e = F.ent(eid)
        p = F.world_pose(e, t)
        h = F.point(eid, t)
        tgt = (h[0], h[1] + look_dy, h[2])
        cands = []
        for d in (dist_, dist_ * 0.8, dist_ * 1.25, dist_ * 0.65):
            for da in (0, -2 * ang, 30, -30, 55, -55, 80, -80, 105, -105):
                a = math.radians(p[3] - ang - da)
                cands.append((h[0] - math.sin(a) * d, h[1] + dy, h[2] + math.cos(a) * d))
        c = pick(cands, tgt, t, {eid})
        return Cam.static(c, tgt)

    def over(a_id, b_id, t, back=2.4, side=1.0, up=0.35):
        """Over-the-shoulder of a, looking at b."""
        pa = F.point(a_id, t)
        pb = F.point(b_id, t)
        yw, _ = look_angles(pa, pb)
        r = math.radians(yw)
        fx, fz = -math.sin(r), math.cos(r)
        rx, rz = -fz, fx
        cands = []
        for (bk, sd) in ((back, side), (back, -side), (back * 0.7, side * 1.3), (back * 0.7, -side * 1.3), (back * 1.3, side * 0.6),
                         (back * 0.5, side * 1.6), (back * 0.5, -side * 1.6), (0.3, 1.9), (0.3, -1.9), (-0.6, 1.8), (-0.6, -1.8)):
            cands.append((pa[0] - fx * bk + rx * sd, pa[1] + up, pa[2] - fz * bk + rz * sd))
        c = pick(cands, pb, t, {a_id, b_id})
        return Cam.static(c, pb)

    def two(a_id, b_id, t, dist_=4.5, side=1, up=0.3):
        pa, pb = F.point(a_id, t), F.point(b_id, t)
        mx, my, mz = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2, (pa[2] + pb[2]) / 2)
        dx, dz = pb[0] - pa[0], pb[2] - pa[2]
        Lh = math.hypot(dx, dz) or 1
        nx, nz = -dz / Lh, dx / Lh
        cands = []
        for sd in (side, -side):
            for d in (max(dist_, Lh * 1.1), dist_ * 0.75, dist_ * 1.3):
                for sk in (0, 0.35, -0.35):
                    ux, uz = nx * sd + dx / Lh * sk, nz * sd + dz / Lh * sk
                    cands.append((mx + ux * d, my + up, mz + uz * d))
        mid = (mx, my - 0.1, mz)
        best, bs = cands[0], 10 ** 9
        for cand in cands:
            sc = vscore(cand, pa, t, {a_id, b_id}) + vscore(cand, pb, t, {a_id, b_id})
            if sc < bs:
                best, bs = cand, sc
            if sc == 0:
                break
        return Cam.static(best, mid)

    def sfx(t, key, pos=None, follow=None, vol=1.0, pitch=1.0, glob=False):
        """A sound effect (see sfx.SFX): at a point, following an entity, or at the listener (glob)."""
        d = {"sound": key, "vol": vol, "pitch": pitch}
        if glob:
            d["global"] = True
        elif follow:
            d["follow"] = follow
        else:
            d["pos"] = [round(v, 2) for v in pos]
        F.event(int(t), "sound", **d)

    def gunshot(t, pos, loud=True, suppressed=False, glob=False):
        key = "kino.gun_suppressed" if suppressed else ("kino.gun_rifle" if loud else "kino.gun_pistol")
        sfx(t, key, pos=pos, vol=(0.9 if glob else (3.0 if not suppressed else 1.5)), glob=glob)
        F.event(t, "particle", type="smoke", pos=pos, delta=(0.05, 0.05, 0.05), speed=0.01, count=6)
        if not suppressed:
            F.event(t, "particle", type="small_flame", pos=pos, delta=(0.02, 0.02, 0.02), speed=0.0, count=3)

    def blood(t, pos, n=14):
        F.event(t, "particle", type="blood", pos=pos, delta=(0.12, 0.15, 0.12), speed=0.05, count=n,
                color=(0.55, 0.03, 0.03))

    def engine(t0, t1, prop, vol=None, pitch=1.0, **_old):
        """The engine runs (a looping sample, pitch follows the speed; see sfx.engines)."""
        F.engines.append((t0, t1, prop.id, vol if vol is not None else (0.75 if prop.id == "truck" else 0.5), pitch))

    def title_card(sec, title, sub=""):
        F.overlay(F.cursor, "black")
        F.title(F.cursor + 5, title, sub, fade_in=10, stay=T(sec) - 30, fade_out=15)
        cam = Cam.static((0, 120, 0), (10, -30))
        with F.shot(cam, dur=sec, name="card"):
            pass
        F.overlay(F.cursor, "letterbox")

    # ======================================================================
    # 1  森林之路 — morning, Kino and Hermes ride west
    # ======================================================================
    F.scene("森林之路", daytime=1000)
    F.event(T(0.4), "sound", sound="kino.music_theme", vol=0.9, pitch=1.0, **{"global": True})
    title_card(6.0, "奇诺之旅", "第七话　战斗者的故事 —Reasonable—")
    t_s1 = F.cursor
    K.show(t_s1)
    H.show(t_s1)
    mount(t_s1)
    RZ = -1.3                         # riding lane (north half of the road)
    x0 = 215.0
    # shot 1: aerial, descending toward the road as they approach
    with F.shot(Cam.move((192, 88, 12), (181, 78, 4), "hermes", "hermes"), dur=7.5, name="aerial") as s:
        pass
    # shot 2: tracking alongside (left side = south)
    with F.shot(Cam.follow("hermes", (-3.3, 1.35, -0.8), look=("kino", 1.2)), name="side") as s:
        s.wait(0.8)
        s.say("艾鲁梅斯", "好悠闲哦，奇诺。")
        s.say("奇诺", "好悠闲呢，艾鲁梅斯。", pause=0.5)
        s.wait(1.5)
    # shot 3: from the front, looking back at Kino
    with F.shot(Cam.follow("hermes", (0.6, 1.55, -4.6), look=("kino", 1.45)), name="front") as s:
        s.say("艾鲁梅斯", "在这空荡荡的森林里……", pause=0.6)
        s.say("艾鲁梅斯", "要是突然冒出什么人，无论是对方或我们都铁定会大吃一惊呢。")
        s.say("奇诺", "…………", dur=1.6)
    # shot 4: close on Kino
    with F.shot(Cam.follow("hermes", (-1.4, 1.75, -1.9), look=("kino", 1.55)), name="kino close") as s:
        s.say("奇诺", "几个人？大概有多少？", pause=0.3)
        s.say("艾鲁梅斯", "距离还蛮远的，人数可能相当多，大概有十个人左右吧。")
        s.say("奇诺", "知道了——等见到面再说吧。")
    t_fast = F.cursor
    H.move(t_s1, t_fast, [(x0, G + BIKE, RZ), (89, G + BIKE, RZ)], face="path")
    # shot 5: roadside low angle, Hermes speeds past toward the waiting men
    t_stop = t_fast + T(5.0)
    H.move(t_fast, t_stop, [(89, G + BIKE, RZ), (46.5, G + BIKE, RZ)], ease_kind="out")
    engine(t_s1, t_stop, H)
    sfx(t_stop - T(1.1), "kino.brake", follow="hermes", vol=0.35, pitch=1.6)
    with F.shot(Cam.static((66, G + 0.6, 4.2), (40, G + 1.3, 0)), dur=5.0, name="speed past"):
        pass

    # ======================================================================
    # 2  拦路的男人们
    # ======================================================================
    F.scene("拦路的男人们")
    t2 = t_fast      # men are placed from the start of shot 5
    men_spots = {
        1: ((38.0, G, 4.6), 180), 2: ((36.5, G, 5.4), 150), 3: ((34.0, G, 4.8), 200), 4: ((40.5, G, -4.8), 10),
        5: ((37.0, G, -5.6), 30), 6: ((33.5, G, -5.0), -20), 7: ((42.5, G, 5.2), 210), 8: ((31.5, G, 4.2), 120),
        9: ((43.5, G, -5.4), -40),
    }
    for i, (p, yw) in men_spots.items():
        guards[i].show(t2).place(t2, p, yw)
        guards[i].hold(t2, "rifle_carry")
    for i in (2, 5, 8):           # a few sit at the roadside
        st = seat(f"g{i}")
        st.show(t2).place(t2, (men_spots[i][0][0], G + 0.12, men_spots[i][0][2]), men_spots[i][1])
        guards[i].ride(t2, st)
    CAP.show(t2).place(t2, (40.0, G, 2.6), 270)
    CAP.hold(t2, "rifle_carry")
    tb = F.cursor
    CAP.move(tb, tb + T(1.5), [(40.0, G, 2.6), (43.2, G, 0.9)], ease_kind="out")
    CAP.turn(tb + T(1.5), tb + T(2.0), 270)
    with F.shot(Cam.static((51.5, G + 1.7, 3.2), (41.0, G + 1.2, 0.5)), name="wide stop") as s:
        s.wait(1.0)
        s.say("胡须男", "嗨，你是旅行者吧？抱歉中途把你拦了下来，我们有点事情想请教。")
        s.say("胡须男", "不会花费你太多时间的，可以吗？")
    with F.shot(close("kino", F.cursor, 2.1, 35), name="kino") as s:
        s.say("奇诺", "什么事呢？如果是我知道的事情，尽管问没关系。")
    with F.shot(over("kino", "captain", F.cursor, back=2.2, side=-1.1), name="cap") as s:
        s.say("胡须男", "谢谢你。我们正在旅行，希望你能告诉我们目前距离最近的国家有多远，")
        s.say("胡须男", "我们进入森林之后就搞不清楚了。", pause=0.1)
    with F.shot(two("kino", "captain", F.cursor, 4.2, side=-1), name="two") as s:
        s.say("奇诺", "从我们过来的方向会比较近，因为我们是昨天傍晚出境的。")
        s.say("奇诺", "况且车子的传动装置也有点问题，我们是慢慢骑过来的。")
        s.say("艾鲁梅斯", "对不起啦。")
        s.say("奇诺", "然后我们要去的目的地，也就是位于西方的国家，大概还要再花三天的时间。")
    with F.shot(close("captain", F.cursor, 2.3, -30), name="cap close") as s:
        s.say("胡须男", "谢谢你这么详细的回答，那我们就往东去好了。")
        s.say("胡须男", "谢谢你，你帮了我们好大的忙呢。")
    with F.shot(close("kino", F.cursor, 2.0, 30), name="kino bye") as s:
        s.say("奇诺", "不客气，那我们告辞了。")
    # Kino rides on through the men, who wave and then stand up and walk east
    t_go = F.cursor
    CAP.move(t_go, t_go + T(1.2), [(43.2, G, 0.9), (43.0, G, 3.0)], ease_kind="out", yaw=270)
    t_pass = ride_to(H, t_go, [(46.5, G + BIKE, RZ), (30, G + BIKE, RZ), (8.0, G + BIKE, RZ)], 7.5, kind="in")
    sfx(t_go - T(0.5), "kino.kickstart", follow="hermes", vol=0.9)
    engine(t_go + T(1.4), t_pass, H)
    with F.shot(Cam.static((24.0, G + 1.2, -2.8), (40, G + 1.3, 0)), dur=3.2, name="ride through") as s:
        s.say("男子们", "再见！", pause=0.8, dur=1.4)
    # men get up and head east toward the truck
    t_up = F.cursor - T(0.5)
    for i in (2, 5, 8):
        guards[i].ride(t_up, None)
        sfx(t_up, "kino.cloth", pos=men_spots[i][0], vol=0.5)
    for i, (p, yw) in men_spots.items():
        q = (p[0] + 0.0, G, p[2])
        guards[i].place(t_up, q, 270)
        amb = ((118.0 + (i % 5) * 1.4), G, (4.8 if p[2] > 0 else -4.8) + (i % 3) * 0.6)
        walk(guards[i], t_up + T(0.2 * i), [q, (q[0] + 6, G, q[2]), amb], speed=2.8)
    CAP.place(t_up, (43.0, G, 3.0), 270)
    walk(CAP, t_up, [(43.0, G, 3.0), (60, G, 2.5), (121.0, G, 3.4)], speed=2.9)
    with F.shot(Cam.follow("hermes", (0.9, 1.9, 2.4), look=(36.0, G + 1.0, 0.0)), dur=3.0, name="look back") as s:
        pass

    # ======================================================================
    # 3  无线电
    # ======================================================================
    F.scene("无线电")
    t3 = F.cursor
    t_in = ride_to(H, t3, [(8.0, G + BIKE, RZ), (4.5, G + BIKE, -2.8), (2.2, G + BIKE, -6.4)], 2.5, kind="out")
    engine(t3, t_in - T(0.6), H, vol=0.4)
    with F.shot(Cam.static((-4.0, G + 1.4, 2.4), (3.0, G + 1.0, -4.5)), name="pull in") as s:
        s.wait(max(0.0, (t_in - t3) / 20 - 0.2))
        dismount(s.cursor, right=-0.9)
        s.say("奇诺", "伤脑筋……", pause=0.4)
    t_bag = F.cursor
    kp = side_of(H, t_bag, right=0.0, back=1.9)
    K.move(t_bag, t_bag + T(1.2), [K.track.at(t_bag)[:3], (kp[0], G, kp[2])], ease_kind="inout")
    K.turn(t_bag + T(1.2), t_bag + T(1.6), H.track.at(t_bag)[3] + 180)
    RADIO = F.prop("radio", "radio")
    rp = side_of(H, t_bag, right=0.0, back=1.3, up=0.3)
    RADIO.show(t_bag + T(2.0)).place(t_bag + T(2.0), rp, H.track.at(t_bag)[3] + 180)
    K.pose(t_bag + T(2.2), "crouching")
    sfx(t_bag + T(1.5), "kino.bag", pos=rp, vol=0.9)
    sfx(t_bag + T(2.0), "kino.cloth", pos=rp, vol=0.6, pitch=1.3)
    with F.shot(Cam.static((kp[0] + 2.4, G + 1.3, kp[2] + 1.6), (kp[0], G + 0.9, kp[2] - 0.6)), name="radio") as s:
        sfx(s.cursor + T(1.4), "kino.radio_on", pos=rp, vol=0.9)
        sfx(s.cursor + T(2.0), "kino.radio", pos=rp, vol=0.7)
        s.wait(2.6)
        s.say("奇诺", "『帽子』呼叫『车篷』——听得见我说话吗？")
        sfx(s.cursor + T(0.1), "kino.radio", pos=rp, vol=0.8, pitch=0.9)
        s.wait(0.6)

    build2(F, locals())
    return F


def build2(F, L):
    """Scenes 4 - 8 (flashback, the snipe, the chase, the enemy, the water ruins)."""
    K, H, TRUCK, CAP, guards, SNIPER, DOC, WOMAN, R = (L[k] for k in ("K", "H", "TRUCK", "CAP", "guards", "SNIPER", "DOC", "WOMAN", "R"))
    seat, ride_to, walk, side_of, attach, mount, dismount, close, over, two, gunshot, blood, engine, title_card = (
        L[k] for k in ("seat", "ride_to", "walk", "side_of", "attach", "mount", "dismount", "close", "over", "two",
                       "gunshot", "blood", "engine", "title_card"))
    RADIO = F.props["radio"]
    S = L["S"]
    sfx = L["sfx"]
    RZ = -1.3
    L2 = {}

    # ======================================================================
    # 4  两天前 — the cheap inn (flashback)
    # ======================================================================
    F.scene("两天前", daytime=6500)
    title_card(2.6, "", "两天前")
    t4 = F.cursor
    ix, iz = world.SPOTS["inn"]
    IY = world.GROUND + 1
    # everyone in the room
    bed = seat("bed")
    bed.show(t4).place(t4, (ix - 3.4, IY + 0.42, iz - 2.4), -90)
    K.pose(t4, "standing")
    K.ride(t4, bed)
    H.place(t4, (ix + 2.6, IY + BIKE, iz + 1.8), 180)
    RADIO.show(t4, False)
    DOC.show(t4).place(t4, (ix - 0.4, IY, iz - 1.0), 90)
    WOMAN.show(t4).place(t4, (ix + 0.3, IY, iz - 2.6), 110)
    WOMAN.hold(t4, "baby")
    for i, (px, pz, yw) in {2: (ix + 0.9, iz + 0.6, 110), 3: (ix - 0.9, iz + 1.9, 150), 4: (ix + 1.4, iz - 1.2, 95)}.items():
        R[i].show(t4).place(t4, (px, IY, pz), yw)
    with F.shot(S((ix + 3.8, IY + 2.3, iz - 3.0), (ix - 1.5, IY + 0.9, iz - 0.6)), name="inn wide") as s:
        s.wait(0.6)
        s.say("医生", "旅行者，我们有件事想拜托你——请你保护我们到下一个国家。")
    with F.shot(close("r2", F.cursor, 2.0, -20), name="r2") as s:
        s.say("男子", "听说两国之间的森林里有山贼出没，会埋伏在唯一的道路上，")
        s.say("男子", "要把一半的行李当作『收获』带走，如果拒绝就毫不留情把所有人杀掉。", pause=0.1)
    with F.shot(S((ix - 1.2, IY + 1.75, iz - 2.9), (ix - 0.4, IY + 1.45, iz - 1.0)), name="doc") as s:
        s.say("医生", "这个国家拒绝了我们的移民，停留的期限也到了。")
        s.say("医生", "我们虽然有说服者，但还没习惯与人争斗……只能把最后的希望寄托在你身上。")
    with F.shot(S((ix + 0.8, IY + 1.5, iz + 2.6), (ix + 2.6, IY + 0.8, iz + 1.6)), name="hermes") as s:
        s.say("艾鲁梅斯", "请恕我无礼，奇诺她很强哟。")
    with F.shot(close("doctor", F.cursor, 2.2, 20), name="doc close") as s:
        s.say("医生", "这是目前我们所能支付的最大金额了。")
    with F.shot(S((ix + 0.2, IY + 1.4, iz + 3.1), ("hermes", 0.7)), name="hermes2") as s:
        s.say("艾鲁梅斯", "不过决定权还是在奇诺啦！")
    with F.shot(close("kino", F.cursor, 1.7, 15, dy=0.0), name="kino think") as s:
        s.wait(1.2)
        s.say("奇诺", "…………", dur=1.8)
        s.say("奇诺", "……我明白了，我接受这个委托。")
    # they leave
    tl = F.cursor
    door = (ix + 3.0, IY, iz + 3.4)
    exits = []
    for a, d in ((DOC, 0.0), (WOMAN, 0.6), (R[2], 1.0), (R[3], 1.4), (R[4], 1.8)):
        p = a.track.at(tl)
        te = walk(a, tl + T(d), [p[:3], (ix + 1.0, IY, iz + 1.6), door], speed=2.4)
        a.show(te, False)
        exits.append(te)
    sfx(min(exits) - T(0.5), "kino.door_open", pos=(door[0], IY + 1, door[2]), vol=0.9)
    sfx(max(exits) + T(0.4), "kino.door_close", pos=(door[0], IY + 1, door[2]), vol=0.9)
    WOMAN.hold(tl, "baby")
    with F.shot(S((ix - 3.0, IY + 1.9, iz + 2.6), (ix + 2.0, IY + 1.0, iz + 1.0)), dur=4.5, name="leave") as s:
        pass
    with F.shot(S((ix + 0.6, IY + 1.4, iz - 0.4), (ix - 3.2, IY + 1.1, iz - 2.3)), name="why") as s:
        s.say("艾鲁梅斯", "为什么要接受呢？报酬又不高，还可能要豁出性命耶。")
        s.say("奇诺", "或许是因为，", pause=0.6, dur=1.6)
        s.say("奇诺", "婴儿很可爱吧？", pause=0.2)
        s.wait(0.8)
    K.ride(F.cursor, None)

    # ======================================================================
    # 5  「长笛」 — back in the forest, the snipe
    # ======================================================================
    F.scene("长笛", daytime=1500)
    t5 = F.cursor
    for bx, by, bz, st in world.barricade_blocks():
        pass
    F.event(t5, "blocks", list=[list(b) for b in world.barricade_blocks()])
    hp = (2.2, G + BIKE, -6.4)
    H.place(t5, hp, 205)
    RADIO.show(t5).place(t5, side_of(H, t5, right=0.0, back=1.3, up=0.3), 25)
    kp = side_of(H, t5, right=-1.0, back=0.6)
    K.place(t5, (kp[0], G, kp[2]), 205 - 90)
    K.pose(t5, "standing")
    K.hold(t5, "flute_carry")
    RADIO.show(t5 + T(3.0), False)
    sfx(t5 + T(0.5), "kino.assemble", pos=(kp[0], G + 1.0, kp[2]), vol=0.9)
    sfx(t5 + T(1.3), "kino.bolt", pos=(kp[0], G + 1.0, kp[2]), vol=0.9)
    sfx(t5 + T(2.6), "kino.radio_on", pos=RADIO.track.at(t5)[:3], vol=0.5, pitch=0.8)
    with F.shot(S((kp[0] - 2.6, G + 1.5, kp[2] + 1.6), (kp[0] + 0.3, G + 1.1, kp[2] - 0.6)), name="assemble") as s:
        s.wait(1.2)
        s.say("艾鲁梅斯", "果真是他们吗？")
        s.say("奇诺", "恐怕就是呢。")
        s.say("奇诺", "我马上回来。", pause=0.6)
        s.say("艾鲁梅斯", "了解！")
    # run east through the trees on the north side, then crawl to the road edge
    tr = F.cursor
    run_pts = [(kp[0], G, kp[2]), (8, G, -8.0), (30, G, -7.5), (50, G, -7.0), (54.5, G, -3.2)]
    t_arr = walk(K, tr, run_pts, speed=5.4)
    with F.shot(Cam.move((14.0, G + 1.6, -1.6), (30.0, G + 1.6, -1.8), "kino", "kino", kind="linear"), dur=4.0, name="run") as s:
        pass
    with F.shot(S((57.0, G + 0.8, 0.8), (50.0, G + 1.0, -6.5)), dur=max(2.5, (t_arr - F.cursor) / 20 + 1.0), name="arrive") as s:
        pass
    tp = F.cursor
    K.place(tp, (55.4, G, -2.3), -90)
    K.pose(tp, "swimming")
    K.hold(tp, "flute", aim=True)
    sfx(tp + T(0.1), "kino.cloth", pos=(55.4, G + 0.3, -2.3), vol=0.8)
    sfx(tp + T(1.2), "kino.bolt", pos=(55.4, G + 0.3, -2.3), vol=0.6)
    # the ambush group (12 men) waiting for the truck
    amb = {}
    for i in range(1, 11):
        g = guards[i]
        zside = 4.6 if i % 2 else -4.6
        amb[i] = (116.0 + i * 1.3, G, zside + (0.4 if i % 3 == 0 else 0.0))
        g.place(tp, amb[i], -90)
        g.show(tp)
        g.hold(tp, "rifle_carry")
    guards[8].hold(tp, "grenade")
    CAP.place(tp, (121.0, G, 3.4), -90)
    SNIPER.show(tp).place(tp, (128.0, G, -5.0), -90)
    SNIPER.hold(tp, "rifle_carry")
    # the truck comes along the road from the east
    TRUCK.show(tp)
    t_truck0 = tp
    with F.shot(S((52.8, G + 0.7, -3.3), (70, G + 0.9, -1.2)), name="prone") as s:
        s.wait(2.4)
    F.overlay(F.cursor, "scope")
    sfx(F.cursor, "kino.spyglass", glob=True, vol=0.8)
    with F.shot(S((108.5, G + 1.45, -1.4), (122.0, G + 1.3, 0.4)), name="scope") as s:
        s.wait(1.6)
        s.say("奇诺", "请不要怨我哟……", pause=0.2)
        s.wait(0.4)
        t_hit1 = s.cursor
        s.wait(2.6)
    g8 = guards[8]
    gunshot(t_hit1, (55.9, G + 0.4, -2.3), suppressed=True, glob=True)
    blood(t_hit1 + 2, (amb[8][0], G + 1.35, amb[8][2]))
    sfx(t_hit1 + 2, "kino.bullet_hit", pos=(amb[8][0], G + 1.3, amb[8][2]), vol=1.2)
    sfx(t_hit1 + T(0.7), "kino.drop_metal", pos=(amb[8][0], G + 0.2, amb[8][2]), vol=0.8)
    sfx(t_hit1 + T(0.9), "kino.fall", pos=(amb[8][0], G + 0.2, amb[8][2]), vol=0.9)
    g8.hold(t_hit1 + 2, None)
    F.event(t_hit1 + 2, "drop", model="grenade", pos=[amb[8][0], G + 1.0, amb[8][2]], vel=[0.05, 0.1, 0.08], floor=G)
    F.subs.append((t_hit1 + 3, t_hit1 + T(1.5), "部下", "哇！"))
    # second: the first man to turn around, hit in the thigh
    g1 = guards[1]
    t_turn = t_hit1 + T(0.8)
    g1.turn(t_turn, t_turn + 6, 90)
    t_hit2 = t_hit1 + T(1.9)
    sfx(t_hit1 + T(0.9), "kino.bolt", glob=True, vol=0.5)
    gunshot(t_hit2, (55.9, G + 0.4, -2.3), suppressed=True, glob=True)
    blood(t_hit2 + 2, (amb[1][0], G + 0.7, amb[1][2]))
    sfx(t_hit2 + 2, "kino.bullet_hit", pos=(amb[1][0], G + 0.7, amb[1][2]), vol=1.2)
    sfx(t_hit2 + 3, "kino.fall", pos=(amb[1][0], G + 0.2, amb[1][2]), vol=0.9)
    g1.pose(t_hit2 + 3, "swimming")
    # the rest run for the trees
    for i in (2, 3, 4, 5, 6, 7, 9):
        a = amb[i]
        walk(guards[i], t_hit2 + T(0.3 + 0.1 * i), [a, (a[0] + 1.5, G, a[2] + (7.0 if a[2] > 0 else -7.0))], speed=5.0)
    walk(CAP, t_hit2 + T(0.2), [(121.0, G, 3.4), (123.0, G, 10.5)], speed=5.0)
    walk(SNIPER, t_hit2 + T(0.2), [(128.0, G, -5.0), (129.0, G, -12.0)], speed=5.0)
    g10 = guards[10]
    t_hit3 = t_hit2 + T(1.6)
    walk(g10, t_hit2 + T(0.6), [amb[10], (amb[10][0] + 0.6, G, amb[10][2] - 2.2)], speed=2.0)
    sfx(t_hit2 + T(0.8), "kino.bolt", glob=True, vol=0.5)
    gunshot(t_hit3, (55.9, G + 0.4, -2.3), suppressed=True, glob=True)
    blood(t_hit3 + 2, (amb[10][0] + 0.6, G + 0.6, amb[10][2] - 2.2))
    sfx(t_hit3 + 2, "kino.bullet_hit", pos=(amb[10][0] + 0.6, G + 0.6, amb[10][2] - 2.2), vol=1.2)
    sfx(t_hit3 + 3, "kino.fall", pos=(amb[10][0] + 0.6, G + 0.2, amb[10][2] - 2.2), vol=0.9)
    sfx(t_hit3 + T(0.8), "kino.bolt", glob=True, vol=0.5)
    g10.pose(t_hit3 + 3, "swimming")
    with F.shot(S((108.5, G + 1.45, -1.4), (122.0, G + 1.1, 0.8)), dur=2.8, name="scope2") as s:
        pass
    sfx(F.cursor - T(0.2), "kino.spyglass_off", glob=True, vol=0.7)
    F.overlay(F.cursor, "letterbox")
    # truck: travels west along the road at 7 b/s
    tt = F.cursor
    TRUCK.place(t_truck0, (215.0, G, 0.0), 90)
    t_at_amb = tt + T(1.0)
    TRUCK.move(t_truck0, t_at_amb, [(215.0, G, 0.0), (126.0, G, 0.0)])
    with F.shot(S((110.0, G + 1.2, 5.6), (126.0, G + 1.0, 0.0)), dur=4.0, name="truck passes") as s:
        pass
    # Kino runs back to Hermes
    tk = F.cursor - T(3.0)
    K.pose(tk, "standing")
    K.hold(tk, "flute_carry")
    back_pts = [(55.4, G, -2.3), (50, G, -7.0), (30, G, -7.5), (8, G, -8.0), (kp[0], G, kp[2])]
    t_back = walk(K, tk, back_pts, speed=5.6)
    with F.shot(Cam.move((44.0, G + 1.7, -1.8), (26.0, G + 1.7, -2.0), "kino", "kino", kind="linear"),
                dur=max(3.0, (t_back - T(1.0) - F.cursor) / 20), name="run back") as s:
        pass
    with F.shot(S((kp[0] - 3.2, G + 1.5, kp[2] + 2.6), (kp[0] + 0.6, G + 1.0, kp[2] - 0.6)), name="welcome") as s:
        s.wait(max(0.0, (t_back - s.t0) / 20))
        s.say("艾鲁梅斯", "欢迎你回来。")
        mount(s.cursor)
        K.hold(s.cursor, None)
        s.say("奇诺", "我射中三个人，他们要追踪的话应该会很困难。")
        F.event(s.cursor, "sound", sound="kino.kickstart", follow="hermes", vol=1.0, pitch=1.0)
        s.wait(0.6)
        s.say("艾鲁梅斯", "来了哟，奇诺。")
    # truck reaches Kino's spot as she finishes; keep the truck timeline continuous
    t_meet = F.cursor
    TRUCK.move(t_at_amb, t_meet, [(126.0, G, 0.0), (6.0, G, 0.0)])
    engine(t_truck0, t_meet, TRUCK)
    L2.update(t_meet=t_meet, kp=kp, hp=hp)

    # ======================================================================
    # 6  追逐 — the truck, the barricade, the side track
    # ======================================================================
    F.scene("陷阱")
    t6 = F.cursor
    for i, sd in ((5, 0.55), (6, -0.55)):
        st = seat(f"bed{i}")
        st.show(t6)
        attach(st, TRUCK, t6, t6 + T(120), right=sd, back=2.35, up=0.42, dyaw=180)
        R[i].show(t6)
        R[i].ride(t6, st)
        R[i].hold(t6, "rifle_carry")
    t_stop = t6 + T(13.0)
    TRUCK.move(t6, t_stop, [(6.0, G, 0.0), (-40.0, G, 0.0), (-84.0, G, 0.0)], ease_kind="out")
    engine(t6, t_stop, TRUCK)
    # Hermes follows the truck
    H.move(t6, t6 + T(1.5), [hp, (2.0, G + BIKE, -2.5), (-2.0, G + BIKE, RZ)], ease_kind="in")
    h_stop = t_stop + T(0.4)
    H.move(t6 + T(1.5), h_stop, [(-2.0, G + BIKE, RZ), (-40.0, G + BIKE, RZ), (-75.5, G + BIKE, RZ)], ease_kind="out")
    engine(t6, h_stop, H)
    sfx(h_stop - T(0.9), "kino.brake", follow="hermes", vol=0.35, pitch=1.6)
    with F.shot(Cam.follow("hermes", (1.6, 1.8, 3.4), look=("truck", 1.6)), dur=0.5, name="behind truck") as s:
        s.wait(0.5)
        s.say("男子", "成、成功了！那些家伙并没有追过来！")
        s.say("奇诺", "别管那些，总之快逃吧！")
    with F.shot(Cam.follow("hermes", (-1.5, 1.7, -2.2), look=("kino", 1.45)), name="kino chase") as s:
        s.say("艾鲁梅斯", "嗯——有可能就这样甩掉他们吗？")
        s.say("奇诺", "不……如果是我，就会——")
    F.cursor = max(F.cursor, t_stop - T(1.0))
    with F.shot(S((-72.0, G + 2.2, 5.5), (-86.0, G + 1.0, 0.0)), dur=2.4, name="brake") as s:
        pass
    F.event(t_stop - T(1.2), "sound", sound="kino.brake", follow="truck", vol=1.5, pitch=0.8)
    with F.shot(S((-90.0, G + 1.6, -5.2), (-93.0, G + 0.8, 1.0)), name="barricade") as s:
        s.wait(0.3)
        dismount(s.cursor, right=-0.9)
        s.say("奇诺", "设下障碍物哟！")
    tw = F.cursor
    kp6 = K.track.at(tw)
    walk(K, tw, [kp6[:3], (-79.5, G, -2.4)], speed=3.0)
    with F.shot(S((-77.0, G + 1.7, -4.0), (-86.0, G + 1.4, 0.0)), name="shout") as s:
        s.wait(1.0)
        s.say("奇诺", "没关系，直接把它压断吧。")
    # the truck goes forward a little and swings right into the track
    t_turn = F.cursor
    track = [(-84.0, G, 0.0)] + [(x, G, z) for (x, _, z) in [(p[0], 0, p[2]) for p in L["arc_"](-84.0, -3.0, 3.0, 0, 90, 6)]]
    track += [(x, G, z) for (x, z) in world.TRACK[1:4]]
    t_gone = ride_to(TRUCK, t_turn, track, 4.0, kind="in")
    engine(t_turn, t_gone, TRUCK)
    with F.shot(S((-78.5, G + 1.6, -1.2), (-87.0, G + 1.2, -5.0)), name="turn") as s:
        s.wait(1.4)
        s.say("奇诺", "什么——", dur=1.2)
        s.wait(1.2)
        s.say("奇诺", "不能往那边去啊！", pause=0.1)
        s.wait(1.4)
    with F.shot(close("kino", F.cursor, 2.2, -25), name="kino mad") as s:
        s.say("奇诺", "啊～真是的！那明明是显而易见的陷阱啊！")
    tm = F.cursor
    walk(K, tm, [K.track.at(tm)[:3], side_of(H, tm, right=-0.9, back=0.3)[:1] + (G,) + side_of(H, tm, right=-0.9, back=0.3)[2:]], speed=3.0)
    with F.shot(S((-72.0, G + 1.5, 2.8), (-75.5, G + 1.0, -1.3)), name="mount") as s:
        s.wait(1.2)
        mount(s.cursor)
        s.say("艾鲁梅斯", "请节哀顺变，这群生手实在很让人伤脑筋耶，这下该怎么办？")
    tf = F.cursor
    h_path = [(-75.5, G + BIKE, RZ), (-82.0, G + BIKE, -0.8)] + [(x, G + BIKE, z) for (x, z) in world.TRACK[:4]]
    t_h6 = ride_to(H, tf, h_path, 4.0, kind="in")
    sfx(tf - T(0.8), "kino.kickstart", follow="hermes", vol=0.9)
    engine(tf + T(1.2), t_h6, H)
    with F.shot(Cam.follow("hermes", (0.9, 1.9, 3.4), look=("kino", 1.3)), name="follow") as s:
        s.wait(1.5)
        s.say("奇诺", "伤脑筋……这下子可就麻烦了呢……")
        s.wait(0.6)
    for i in (5, 6):
        R[i].show(F.cursor, False)
    K.show(F.cursor, False)
    H.show(F.cursor, False)
    TRUCK.show(F.cursor, False)

    # ======================================================================
    # 7  障碍物前的男人们
    # ======================================================================
    F.scene("中计")
    t7 = F.cursor
    for i in range(1, 11):
        guards[i].show(t7, False)
    SNIPER.show(t7, False)
    CAP.place(t7, (-89.0, G, -2.6), 0)
    CAP.hold(t7, "rifle_carry")
    g2, g8, g9, g10 = guards[2], guards[8], guards[9], guards[10]
    g2.show(t7).place(t7, (-87.5, G, 1.0), 60).hold(t7, "rifle_carry")
    g8.show(t7).place(t7, (-91.0, G, 2.4), 250).pose(t7, "standing")
    g9.show(t7).place(t7, (-90.2, G, 3.4), 240).pose(t7, "standing")
    g9.hold(t7, "rifle_carry")
    g10.show(t7).place(t7, (-91.4, G, 3.8), 230).pose(t7, "standing")
    CAP.move(t7, t7 + T(2.0), [(-89.0, G, -2.6), (-86.8, G, -3.6)], ease_kind="out", yaw=0)
    with F.shot(S((-82.8, G + 1.9, -7.5), (-88.0, G + 0.9, -1.5)), name="tracks") as s:
        s.wait(1.0)
        s.say("胡须男", "原来他们雇用那名旅行者当护卫啊……")
        s.say("胡须男", "本想说她还很年轻而没放在心上……")
    with F.shot(close("guards_2" if False else "g2", F.cursor, 2.2, 20), name="g2") as s:
        s.say("部下", "不过，他们中计了。")
    with F.shot(close("captain", F.cursor, 2.0, -25), name="cap") as s:
        s.say("胡须男", "是啊，接下来不必太急躁，还是有机会可以把那个旅行者干掉——")
        s.say("胡须男", "好了，把树干移开，不要在路面留下任何痕迹。")
    F.event(F.cursor + T(1.2), "blocks", list=[[x, y, z, None] for (x, y, z, _) in world.barricade_blocks()])
    for k in range(3):
        sfx(F.cursor + T(0.4 + 0.55 * k), "kino.logs", pos=(-93.0, G + 0.5, -1.5 + 1.5 * k), vol=1.2, pitch=0.9 + 0.1 * k)
    with F.shot(S((-99.0, G + 3.5, 6.0), (-91.0, G + 0.5, 0.0)), dur=2.6, name="moved") as s:
        pass
    for a in (CAP, g2, g8, g9, g10):
        a.show(F.cursor, False)

    # ======================================================================
    # 8  水之遗迹 — the flooded fortress
    # ======================================================================
    F.scene("水之遗迹", daytime=4600)
    t8 = F.cursor
    TRUCK.show(t8)
    K.show(t8)
    H.show(t8)
    mount(t8)
    tr8 = [(x, G, z) for (x, z) in world.TRACK[3:]] + [(-79.5, W, -74.0), (-79.5, W, -112.0), (-72.0, W, -121.0),
                                                       (-68.0, W, -126.0), (-68.0, W, -129.5)]
    t_park = ride_to(TRUCK, t8, tr8, 4.5, kind="out")
    engine(t8, t_park, TRUCK)
    for t in range(t8 + T(4.0), t_park, 6):
        p = TRUCK.track.at(t)
        if p[2] < -73:
            F.event(t, "particle", type="splash", pos=[p[0], W + 0.4, p[2]], delta=(1.0, 0.1, 1.6), speed=0.1, count=6)
            if t % 12 == 0:
                sfx(t, "kino.small_splash", pos=(p[0], W + 0.3, p[2]), vol=1.0, pitch=0.7 + 0.1 * ((t // 12) % 3))
    for i, st in ((5, "bed5"), (6, "bed6")):
        attach(seats[st] if False else F.props["seat_" + st], TRUCK, t8, t8 + T(200), right=(0.55 if i == 5 else -0.55),
               back=2.35, up=0.42, dyaw=180)
        F.props["seat_" + st].show(t8)
        R[i].show(t8)
        R[i].ride(t8, F.props["seat_" + st])
    h8 = [(x, G + BIKE, z) for (x, z) in world.TRACK[3:]] + [(-79.8, W + BIKE, -74.0), (-80.2, W + BIKE, -98.0),
                                                            (-80.2, W + BIKE, -103.0)]
    t_h8 = ride_to(H, t8 + T(2.0), h8, 6.5, kind="out")
    engine(t8, t_h8, H)
    for t in range(t8 + T(2.0), t_h8, 8):
        p = H.track.at(t)
        if p[2] < -73:
            sfx(t, "kino.small_splash", pos=(p[0], W + 0.3, p[2]), vol=0.7, pitch=1.0 + 0.1 * ((t // 8) % 3))
    with F.shot(Cam.move((-80.0, G + 3.0, -60.0), (-80.5, G + 14.0, -64.0), (-80.0, 66.0, -110.0), (-79.0, 67.0, -135.0), kind="inout"),
                dur=9.0, name="reveal") as s:
        pass
    with F.shot(S((-83.5, W + 1.2, -106.5), (-80.2, W + 1.3, -99.0)), name="kino stops") as s:
        s.wait(max(0.3, (t_h8 - s.t0) / 20 + 0.3))
        dismount(s.cursor, right=-0.9)
        s.wait(0.8)
        s.say("奇诺", "这是……好棒的地方……", pause=0.2)
    with F.shot(S((-76.0, W + 0.6, -97.0), (-80.5, W + 0.7, -103.5)), name="water low") as s:
        s.say("艾鲁梅斯", "这地方真不错呢，奇诺。建造这处碉堡的人利用石板路建造出几近完美的水平呢。")
    with F.shot(close("kino", F.cursor, 2.3, 30), name="kino water") as s:
        s.say("奇诺", "然后把河水引进这里，形成这么美丽的场所……")
        s.say("奇诺", "真是的，若不是身处于这种紧张的时刻，我一定会大声欢呼发现到这么棒的地方呢。")
    L2.update(t_park=t_park)
    L.update(L2)
    build3(F, L)


def build3(F, L):
    """Scenes 8b - 18."""
    K, H, TRUCK, CAP, guards, SNIPER, DOC, WOMAN, R = (L[k] for k in ("K", "H", "TRUCK", "CAP", "guards", "SNIPER", "DOC", "WOMAN", "R"))
    seat, ride_to, walk, side_of, attach, mount, dismount, close, over, two, gunshot, blood, engine, title_card = (
        L[k] for k in ("seat", "ride_to", "walk", "side_of", "attach", "mount", "dismount", "close", "over", "two",
                       "gunshot", "blood", "engine", "title_card"))
    t_park = L["t_park"]
    S = L["S"]
    sfx = L["sfx"]
    DOORZ = -131.0
    g = guards

    def pos(a, t):
        p = a.track.at(t)
        return (p[0], p[1], p[2])

    def cam_at(pos_, look):
        return S(pos_, look)

    # ---------------- 8b  everyone gets out of the truck -------------------
    t_out = max(F.cursor, t_park)
    tp = TRUCK.track.at(t_out)
    DOC_START = (-66.3, W, -125.6)
    group = {
        "woman": ((-69.4, W, -124.4), 180), "doctor": (DOC_START, 150), 1: ((-70.6, W, -126.4), 150), 2: ((-68.2, W, -124.0), 180),
        3: ((-70.0, W, -123.0), 170), 4: ((-67.2, W, -123.0), 200), 5: ((-71.2, W, -124.5), 140), 6: ((-68.9, W, -122.2), 190),
        7: ((-66.9, W, -121.4), 200),
    }
    for i in (5, 6):
        R[i].ride(t_out, None)
    sfx(t_out, "kino.tailgate", pos=(tp[0] + 0.3, W + 1.2, tp[2] + 3.0), vol=1.0)
    sfx(t_out + T(0.3), "kino.truck_door", pos=(tp[0] + 1.2, W + 1.2, tp[2] - 1.0), vol=0.8)
    for k in range(4):
        sfx(t_out + T(0.8 + 0.6 * k), "kino.fall_water" if k == 0 else "kino.small_splash", pos=(tp[0] + 0.3, W + 0.3, tp[2] + 3.4),
            vol=0.6, pitch=1.0 + 0.1 * k)
    for k, (p, yw) in group.items():
        a = DOC if k == "doctor" else (WOMAN if k == "woman" else R[k])
        src = (tp[0] + 0.3, W, tp[2] + 3.4)
        a.show(t_out + T(0.25 * (k if isinstance(k, int) else 0)))
        walk(a, t_out + T(0.25 * (k if isinstance(k, int) else 0)), [src, p], speed=2.4)
        a.hold(t_out, "rifle_carry" if isinstance(k, int) else None)
    WOMAN.hold(t_out, "baby")
    DOC.show(t_out, False)
    DOC.show(t_out + T(9.0))
    DOC.place(t_out + T(9.0), (-72.3, W, -125.4), 120)
    DOC.face_to(t_out + T(9.2), t_out + T(9.8), "kino")
    kpos = pos(K, t_out)
    walk(K, t_out + T(1.0), [kpos, (-76.5, W, -118.0), (-73.2, W, -120.8)], speed=2.6)
    with F.shot(S((-75.5, W + 2.2, -116.0), (-69.0, W + 1.0, -124.5)), name="get out") as s:
        s.wait(3.8)
        s.say("奇诺", "为什么没有突破那道封锁线呢？这是个陷阱耶，")
        s.say("奇诺", "我们被逼进这里了，已经无法回到森林那条路了。", pause=0.1)
        s.say("男子", "那是因为……")
    K.face_to(F.cursor, F.cursor + 8, "doctor")
    with F.shot(over("kino", "doctor", F.cursor, back=2.0, side=0.9), name="doc arrives") as s:
        s.say("医生", "是我叫他们那么做的，请不要责怪他们。")
        s.say("奇诺", "你是……我记得你是医生吧？")
    with F.shot(close("doctor", F.cursor, 2.4, 20), name="doc talk") as s:
        s.say("医生", "在那种状态下卡车会产生颠簸，很可能危及婴儿的性命，因此我们无法那么做。")
    with F.shot(close("kino", F.cursor, 2.1, -30), name="kino") as s:
        s.say("奇诺", "不，只要把她抱紧，那点冲撞应该——")
    with F.shot(two("doctor", "woman", F.cursor, 4.0, side=-1), name="doc woman") as s:
        s.say("医生", "我好像还没跟你说呢……所以很抱歉会演变成这样的结果。")
        s.say("奇诺", "……什么事情？")
        s.say("医生", "关于这个孩子……她天生心脏就脆弱，能不能活到三岁都还是个问题呢。")
        s.say("医生", "因此无法让她承受太大的冲击。")
    with F.shot(S((-69.0, W + 1.1, -116.8), (-73.6, W + 1.2, -121.2)), name="hermes") as s:
        s.say("艾鲁梅斯", "天哪～")
    with F.shot(close("kino", F.cursor, 2.0, 20), name="kino sigh") as s:
        s.say("奇诺", "…………你应该在一开始就告诉我的……", pause=0.5)
        s.say("医生", "对不起。")
    tl = F.cursor
    K.turn(tl, tl + T(1.0), 0, -3)
    with F.shot(Cam.move((-74.0, W + 1.9, -123.2), (-74.2, W + 2.3, -123.8), (-76.0, W + 1.2, -95.0), (-79.0, W + 1.0, -60.0)), dur=5.0,
                name="the road") as s:
        pass
    # Kino hides Hermes behind a broken wall; everyone goes into the keep
    th = F.cursor
    HIDE = (-73.4, W + BIKE, -108.0)
    kp = pos(K, th)
    walk(K, th, [kp, (-78.8, W, -104.0)], speed=3.0)
    t_m = th + T(2.4)
    H.move(t_m, t_m + T(2.5), [(-80.2, W + BIKE, -103.0), (-75.5, W + BIKE, -106.5), HIDE], ease_kind="inout")
    K.move(t_m, t_m + T(2.5), [(-78.8, W, -104.0), (-74.6, W, -107.0), (-74.6, W, -109.2)], ease_kind="inout")
    for k in range(5):
        hp_ = H.track.at(t_m + T(0.5 * k))
        sfx(t_m + T(0.5 * k), "kino.small_splash", pos=(hp_[0], W + 0.3, hp_[2]), vol=0.6, pitch=1.1 + 0.05 * k)
    sfx(t_m + T(2.6), "kino.kickstand", follow="hermes", vol=0.8)
    with F.shot(S((-77.0, W + 1.6, -113.0), (-74.0, W + 0.9, -107.5)), name="hide") as s:
        s.wait(4.6)
        s.say("艾鲁梅斯", "把我们排挤在外实在很过分呢——等会儿再请你们把事情跟奇诺说清楚。")
        s.say("奇诺", "知道了啦，你在这里稍等一会儿吧。")
    with F.shot(S((-76.2, W + 2.2, -121.5), (-80.0, W + 1.6, -131.0)), name="go in") as s:
        for k in range(3):
            sfx(s.t0 + T(0.5 + 1.1 * k), "kino.bag", pos=(-68.0, W + 1.2, -126.5), vol=0.8, pitch=0.9 + 0.1 * k)
        sfx(s.t0 + T(1.4), "kino.metal", pos=(-68.0, W + 1.2, -126.5), vol=0.6)
        s.say("医生", "动作快！只要搬武器跟粮食就好！")
        s.wait(2.2)
    t_in = F.cursor
    K.hold(t_in - T(2.0), "flute_carry")
    for a in [K, DOC, WOMAN] + [R[i] for i in range(1, 8)]:
        a.show(t_in, False)

    # ======================================================================
    # 9  碉堡之内
    # ======================================================================
    F.scene("碉堡之内", daytime=5000)
    t9 = F.cursor
    for a in [K, DOC, WOMAN] + [R[i] for i in range(1, 8)]:
        a.show(t9)
    K.place(t9, (-80.0, W, -132.6), 180)
    walk(K, t9, [(-80.0, W, -132.6), (-80.0, W, -137.0)], speed=2.0)
    order = [DOC, R[1], WOMAN, R[2], R[3], R[4], R[5], R[6], R[7]]
    for k, a in enumerate(order):
        a.place(t9, (-80.0 + (k % 2) * 0.8 - 0.4, W, -128.0 + k * 0.9), 180)
        walk(a, t9 + T(0.3 * k), [(-80.0 + (k % 2) * 0.8 - 0.4, W, -128.0 + k * 0.9), (-80.0 + (k % 2) * 0.8 - 0.4, W, -133.0 - k * 0.2)],
             speed=2.2)
    with F.shot(S((-79.2, W + 1.7, -139.6), (-80.0, W + 1.2, -131.0)), name="corridor") as s:
        s.wait(2.6)
        s.say("男子", "这里是……什么地方啊？")
        s.wait(0.6)
    # two men go up to the roof as lookouts
    tr = F.cursor
    for i, (rx) in ((6, -84.0), (7, -76.0)):
        a = R[i]
        walk(a, tr, [pos(a, tr), (-80.0, W, -141.5), (-77.8, W, -144.0)], speed=2.8)
        a.show(tr + T(3.4), False)
        a.show(tr + T(6.0))
        a.place(tr + T(6.0), (rx, 73.0, -132.3), 0)
    with F.shot(close("kino", F.cursor, 2.0, 20), name="orders") as s:
        s.say("奇诺", "你们两个，到屋顶上监视道路。")
        s.say("奇诺", "我想他们应该还没到，不过只要发现他们的踪迹，就立刻开枪通知大家。")
    # the gathering room (south-east)
    tg = F.cursor
    room = {"kino": ((-73.8, W, -133.6), 90), "doctor": ((-76.4, W, -135.4), -60), "woman": ((-76.9, W, -132.3), -110),
            1: ((-80.2, W, -135.2), -90), 2: ((-74.6, W, -136.1), 10), 3: ((-77.2, W, -134.0), -85), 4: ((-75.4, W, -131.9), 175),
            5: ((-80.4, W, -133.0), -90)}
    for k, (p, yw) in room.items():
        a = K if k == "kino" else (DOC if k == "doctor" else (WOMAN if k == "woman" else R[k]))
        a.place(tg, p, yw)
    with F.shot(S((-73.5, W + 1.9, -132.0), (-76.4, W + 1.1, -135.0)), name="room") as s:
        s.wait(0.8)
        s.say("奇诺", "虽然我觉得不太可能，不过——")
        s.say("医生", "怎么了？")
        s.say("奇诺", "这里好像有人在使用。")
    with F.shot(close("doctor", F.cursor, 1.9, 15), name="doc q") as s:
        s.say("医生", "你所谓的『有人』是……？")
    with F.shot(close("kino", F.cursor, 1.8, -20), name="kino a") as s:
        s.say("奇诺", "十之八九是那群山贼吧，")
        s.say("奇诺", "这儿有地方可睡，有水可喝，眺望的视野也不错，是当据点的最佳场所哟。", pause=0.1)
    with F.shot(S((-76.8, W + 1.8, -136.0), (-74.0, W + 1.3, -133.0)), name="men") as s:
        s.say("男子", "那么，那些家伙目前就躲在这里埋伏——")
        s.say("奇诺", "他们不在这里哟，要是在的话我们早就被袭击了。")
        s.say("医生", "这么说，我们等于直接被逼进他们的据点啊……")
    with F.shot(close("kino", F.cursor, 1.9, 25), name="kino plan") as s:
        s.say("奇诺", "问题是我们能在这样的包围下撑多久，毕竟我们没有太多食物。")
        s.say("奇诺", "要是不尽快把对方全部歼灭，最后吃败仗的会是我们。")
    tq = F.cursor
    K.turn(tq + T(1.0), tq + T(1.8), 90, 35)
    with F.shot(close("kino", F.cursor, 1.8, -15, dy=0.1), name="strange") as s:
        s.wait(1.4)
        s.say("奇诺", "奇怪？", dur=1.4)
        s.say("奇诺", "咦？『全部歼灭』……奇怪了……")
        s.say("男子", "怎、怎么了吗？")
    K.turn(F.cursor, F.cursor + 8, 90, 0)
    with F.shot(S((-76.9, W + 1.6, -135.8), (-74.0, W + 1.5, -133.4)), name="explain") as s:
        s.say("奇诺", "奇怪了……我越想越觉得奇怪，那个时候怎么没发现到呢？")
        s.say("医生", "什么事啊？")
        s.say("奇诺", "就是那群山贼的行动。当他们挡住去路，把我们逼到旁边的小路时，怎么没在那里设下陷阱呢？")
        s.say("奇诺", "我只能猜测那是他们『不想那么做』，所以『没有那么做』。那些人——")
    with F.shot(close("kino", F.cursor, 1.9, 20), name="hurt?") as s:
        s.say("奇诺", "有谁——有人受伤吗？包括上面那两个人。")
        s.say("医生", "没有……？没有人受伤耶……")
        s.say("奇诺", "那么——")
    # the line of blood in the water
    tb = F.cursor
    line = [(-82.4 + k * 0.45, W + 0.42, -133.5 + (0.08 if k % 2 else -0.05)) for k in range(0, 20)]
    for t in range(tb - T(20), tb + T(40), 5):
        for k, p in enumerate(line):
            if (t // 5 + k) % 2 == 0:
                F.event(t, "particle", type="dust", pos=list(p), delta=(0.08, 0.0, 0.06), speed=0.0, count=2,
                        color=(0.32, 0.04, 0.12))
    K.turn(tb, tb + T(0.8), 115, 30)
    with F.shot(S((-81.0, W + 1.3, -133.3), (-76.3, W + 0.3, -133.7)), name="blood") as s:
        s.say("奇诺", "那地上流的血是谁的？", pause=0.3)
        s.wait(2.2)
    # follow the line to the walled-up doorway
    tf = F.cursor
    walk(K, tf, [pos(K, tf), (-77.0, W, -134.2), (-80.3, W, -134.2)], speed=1.2)
    K.turn(tf + T(3.2), tf + T(3.8), 90, 20)
    for i in (2, 3, 4):
        walk(R[i], tf + T(1.0), [pos(R[i], tf), (-78.0, W, -134.0), (-80.6 - (i - 2) * 0.1, W, -133.0 - (i - 3) * 1.1)], speed=1.6)
    walk(DOC, tf + T(0.6), [pos(DOC, tf), (-77.6, W, -134.8), (-79.4, W, -135.6)], speed=1.5)
    with F.shot(S((-79.6, W + 1.8, -137.8), (-81.6, W + 0.8, -134.2)), dur=5.5, name="follow line") as s:
        pass
    with F.shot(S((-78.8, W + 2.2, -135.8), (-82.0, W + 1.1, -134.0)), name="stones") as s:
        s.say("奇诺", "把这些石头搬开。", pause=0.3)
        s.wait(2.4)
        for k in range(3):
            sfx(s.cursor - T(2.0 - 0.8 * k), "kino.stone", pos=(-82.5, 65.5, -134.0 + 0.4 * k), vol=1.0, pitch=0.8 + 0.08 * k)
    F.event(F.cursor, "blocks", list=[list(b) for b in world.rubble_cleared()])
    # the real bandits, dead since last night
    BD = []
    for k, (bx, bz, yw, sk) in enumerate([(-85.0, -134.6, 80, "bandit_a"), (-84.2, -135.4, 110, "bandit_b"),
                                         (-86.0, -133.8, 60, "bandit_b")]):
        b = F.actor(f"bandit{k}", sk, label="山贼")
        b.show(F.cursor).place(F.cursor, (bx, world.GROUND + 1.0, bz), yw).pose(F.cursor, "swimming")
        BD.append(b)
    with F.shot(S((-82.2, W + 2.4, -134.3), (-85.2, W + 0.7, -134.6)), name="bodies") as s:
        s.wait(1.6)
        s.say("奇诺", "原来如此。")
        s.say("年轻男子", "这、这些家伙是怎么回事啊……？")
        s.say("奇诺", "那还用说，是真正的山贼们哟。")
        s.wait(0.5)

    # ======================================================================
    # 10  真相
    # ======================================================================
    F.scene("真相", daytime=5400)
    t10 = F.cursor
    for k, (p, yw) in room.items():
        a = K if k == "kino" else (DOC if k == "doctor" else (WOMAN if k == "woman" else R[k]))
        a.place(t10, p, yw)
    K.face_to(t10, t10 + 1, "doctor")
    with F.shot(close("kino", t10, 2.0, 25), name="not bandits") as s:
        s.say("奇诺", "回到主题，刚刚我话没说完。那些觊觎你们的家伙，目标并不是你们的行李。")
        s.say("奇诺", "那些人并不是山贼。而盘踞在这里的山贼们，已经轻易被昨晚那些人给杀了。")
        s.say("奇诺", "那么，他们究竟是谁呢？")
    with F.shot(S((-73.4, W + 1.8, -135.8), (-76.5, W + 1.2, -133.0)), name="silence") as s:
        s.say("男子们", "…………", dur=1.8)
        s.say("奇诺", "其实你们知道吧，知道追杀自己的集团是谁吧——你们真正害怕的，并不是山贼。")
        s.say("奇诺", "究竟是谁？", pause=0.4)
        s.say("男子们", "…………", dur=1.8)
    with F.shot(close("kino", F.cursor, 1.9, -25), name="leave") as s:
        s.say("奇诺", "我明白了。既然你们不回答就算了，但是现在我已经没必要履行保护你们不受山贼伤害的约定，")
        s.say("奇诺", "所以我要回去艾鲁梅斯那里了，接下来你们自己看着办吧。", pause=0.1)
    r3 = R[3]
    with F.shot(close("r3", F.cursor, 2.0, 25), name="betray") as s:
        s.say("男子", "什么？你想背叛我们吗？")
    with F.shot(close("kino", F.cursor, 2.0, 30), name="contract") as s:
        s.say("奇诺", "最初说谎骗人的是你们，这算是违反契约的行为。")
        s.say("奇诺", "既然你们不把知道的事情告诉我，那我也无可奈何——")
        s.say("奇诺", "我会把事情跟那些人坦白说清楚，请他们放过我跟艾鲁梅斯。")
    tk = F.cursor
    r3.hold(tk + T(0.6), "canon", aim=True)
    with F.shot(two("kino", "r3", tk, 3.6, side=1), name="kick") as s:
        s.say("男子", "你这家伙！", pause=0.3)
        s.say("医生", "住手！", pause=0.0, dur=1.2)
        t_kick = s.cursor - T(0.9)
        s.wait(1.2)
        s.say("奇诺", "再不快点捡回来会湿掉哟。")
    r3.hold(t_kick, None)
    rp3 = pos(r3, t_kick)
    F.event(t_kick, "drop", model="canon", pos=[rp3[0], W + 1.3, rp3[2]], vel=[-0.05, 0.25, -0.12], floor=W + 0.3)
    F.event(t_kick, "sound", sound="kino.kick", pos=list(rp3), vol=1.0, pitch=1.0)
    F.event(t_kick + 12, "particle", type="splash", pos=[rp3[0] - 0.5, W + 0.4, rp3[2] - 1.2], delta=(0.2, 0.05, 0.2), speed=0.1, count=10)
    sfx(t_kick + 12, "kino.small_splash", pos=(rp3[0] - 0.5, W + 0.3, rp3[2] - 1.2), vol=1.0, pitch=1.2)
    sfx(tk + T(0.5), "kino.holster", pos=(rp3[0], W + 1.0, rp3[2]), vol=0.8)
    K.hold(t_kick + T(0.8), "canon")
    sfx(t_kick + T(0.8), "kino.holster", follow="kino", vol=0.7, pitch=0.9)
    with F.shot(S((-73.4, W + 1.9, -135.6), (-76.0, W + 1.1, -133.4)), name="calm down") as s:
        s.say("医生", "大家请住手，跟奇诺战斗也毫无意义。虽然不愿意承认，但奇诺她终究比较强，")
        s.say("医生", "就算我们人数多过她，那接下来呢？我们的目的呢？", pause=0.1)
    K.hold(F.cursor, "flute_carry")
    with F.shot(close("kino", F.cursor, 1.9, 20), name="then") as s:
        s.say("奇诺", "那么，可以请你告诉我目的吗？毕竟我也不认为现在向那些人举白旗投降，他们会毫不计较地放过我们。")
    with F.shot(close("doctor", F.cursor, 2.0, -20), name="truth1") as s:
        s.say("医生", "知道了……我把来龙去脉全说出来，各位应该同意吧？")
        s.wait(0.6)
        s.say("医生", "其实那个女婴是某王室唯一留存的血脉。至于我原本是王室的御医，而在场的这些人都是侍女及随从。")
    with F.shot(close("woman", F.cursor, 1.7, 15), name="woman sad") as s:
        s.wait(1.8)
    with F.shot(close("doctor", F.cursor, 2.0, 25), name="truth2") as s:
        s.say("医生", "大约是半年前，君主制度因为革命被推翻，王室的人全遭到逮捕，还被处决……那孩子则是唯一的幸存者。")
    with F.shot(over("doctor", "kino", F.cursor, back=1.8, side=0.8), name="kino guess") as s:
        s.say("奇诺", "结果，那些人便奉命追杀王室的遗族——啊，不对，应该是说完全相反。")
    with F.shot(close("doctor", F.cursor, 2.0, 25), name="truth3") as s:
        s.say("医生", "是的……那些人是狂热支持者，也是前禁卫军。")
        s.say("医生", "国家一直处于不安定的局势，有不少国民希望能复兴王室。于是那些人打算拱这个孩子出来，企图复辟君主制。")
    with F.shot(close("kino", F.cursor, 1.9, 20), name="alive") as s:
        s.say("奇诺", "原来如此……所以他们说什么都要『活捉』她。")
    with F.shot(close("doctor", F.cursor, 2.0, 25), name="truth4") as s:
        s.say("医生", "……是的，我们为了阻止这件事情发生才逃离祖国，我们根本不想要复辟什么君主制，")
        s.say("医生", "也希望让这孩子在剩下的日子里能过着自由自在的人生……", pause=0.1)
    with F.shot(two("kino", "doctor", F.cursor, 3.4, side=-1), name="offer") as s:
        s.say("医生", "奇诺，只靠没有战斗经验的我们是无法击退那群士兵的。但是，我们也无法保证你能够平安无事地回归旅途，")
        s.say("医生", "因为艾鲁梅斯太醒目了。", pause=0.1)
        s.say("奇诺", "是没错啦。")
        s.say("医生", "我明知道这样的请求非常卑劣……如果这孩子能平安抵达下一个国家，我愿意把卡车送给你当作酬劳。")
    with F.shot(close("doctor", F.cursor, 2.0, 25), name="three years") as s:
        s.say("男子们", "医生！", dur=1.2)
        s.say("医生", "事到如今，能保住性命比较重要。我决定说什么都要让这孩子在下一个国家生活，")
        s.say("医生", "只要再待个三年就好。等过了这段时间，我们的任务就结束了，一切就终告结束。", pause=0.1)
    with F.shot(close("kino", F.cursor, 1.9, -20), name="deal") as s:
        s.say("奇诺", "知道了，撇开酬劳不说，为了保命也只有拼了呢。")
        s.say("奇诺", "我们需要更多武器，请大家现在快去找出来。")
        s.say("奇诺", "就是那些被杀的山贼们的武器啊。那些武器很重，我不认为那些人会带走，应该是藏在房间的某处。")
    for a in [K, DOC, WOMAN] + [R[i] for i in (1, 2, 3, 4, 5)] + BD:
        a.show(F.cursor, False)

    # ======================================================================
    # 11  再见了，奇诺
    # ======================================================================
    F.scene("约定", daytime=6200)
    t11 = F.cursor
    K.show(t11).place(t11, (-74.8, W, -109.6), -30)
    K.hold(t11, "flute_carry")
    AMMO = F.prop("ammo", "radio")
    with F.shot(two("kino", "hermes", t11, 3.6, side=1), name="talk") as s:
        s.wait(0.6)
        s.say("奇诺", "总之，就是这么回事。")
        s.say("艾鲁梅斯", "天哪~想不到连奇诺也被卷入相当危险的情况里呢。")
        s.say("艾鲁梅斯", "何不直接落跑呢？把包包里的无线电拿去卖，应该足以抵那些衣服的钱哟？")
    with F.shot(close("kino", F.cursor, 1.9, 30), name="another way") as s:
        s.say("奇诺", "如果有『别条路』，或许我就会那么做。")
        s.say("艾鲁梅斯", "喔，这话有点意思。然后呢？")
        s.say("奇诺", "如果找到的话，我会那么做的。")
    with F.shot(S((-71.2, W + 1.1, -110.4), (-74.2, W + 1.2, -108.6)), name="goodbye") as s:
        s.say("艾鲁梅斯", "原则上先说一声——再见了，奇诺。")
        s.say("奇诺", "啊啊——再见。")
        s.say("艾鲁梅斯", "这句话，已经说了几遍啊？")
        s.say("奇诺", "不知道——那么待会儿见。")
    tg = F.cursor
    walk(K, tg, [pos(K, tg), (-78.0, W, -112.0), (-80.0, W, -125.0), (-80.0, W, -131.5)], speed=3.8)
    for t in range(tg, tg + T(4.5), 4):
        p = K.track.at(t)
        F.event(t, "particle", type="splash", pos=[p[0], W + 0.4, p[2]], delta=(0.15, 0.02, 0.15), speed=0.05, count=3)
    with F.shot(S((-73.8, W + 1.2, -106.0), (-80.0, W + 1.3, -122.0)), dur=4.0, name="splash away") as s:
        pass
    K.show(F.cursor, False)

    # ======================================================================
    # 12  旧式武器与投降者
    # ======================================================================
    F.scene("投降", daytime=6600)
    t12 = F.cursor
    CANNON = F.prop("cannon", "cannon", translation=(0, 0.5, 0))
    CANNON.show(t12).place(t12, (-80.0, W, -138.2), 180)
    wz = -139.4
    spots12 = {"kino": ((-82.6, W, -140.0), -60), 4: ((-78.6, W, -139.8), 110), 2: ((-83.4, W, -138.4), -110),
               1: ((-81.4, W, -135.6), 170), 3: ((-78.8, W, -136.0), 150), "doctor": ((-84.2, W, -139.8), -80)}
    for k, (p, yw) in spots12.items():
        a = K if k == "kino" else (DOC if k == "doctor" else R[k])
        a.show(t12).place(t12, p, yw)
    for i in (1, 2, 3, 4):
        R[i].hold(t12, "rifle_carry")
    sfx(t12 + T(0.3), "kino.metal", pos=(-80.0, W + 0.8, -139.5), vol=0.9)
    sfx(t12 + T(1.5), "kino.drop_metal", pos=(-80.5, W + 0.5, -139.5), vol=0.6, pitch=1.1)
    with F.shot(S((-77.6, W + 2.4, -141.6), (-81.0, W + 0.8, -138.2)), name="weapons") as s:
        s.wait(0.5)
        s.say("男子", "全部应该就这些了。")
        s.say("男子", "几挺从前端塞火药的旧式步枪，三挺左轮步枪，十瓶左右的液体火药，还有十四把不太利的刀剑。")
        s.say("奇诺", "说服者全都很老旧，根本就派不上用场。液体火药就这么多，如果要使用就用在自己的反冲式说服者上。")
    with F.shot(S((-78.4, W + 1.3, -136.4), (-80.0, W + 0.8, -138.6)), name="cannon") as s:
        s.say("男子", "然后大炮应该是旧款的。大致清洗过后应该还能用，虽然有办法弄到火药，但是完全没有炮弹。")
        s.say("男子", "改塞短刀在里面怎么样？", pause=0.2)
        s.say("男子", "应该几乎飞不去才对。这种款式的大炮只要打出一发就没了，")
        s.say("男子", "要是没有把台车固定好，还会因为发射的后座力往后冲，所以无法轻易改变它瞄准的方向。", pause=0.1)
    CANNON.move(F.cursor, F.cursor + T(1.5), [(-80.0, W, -138.2), (-80.0, W, -137.2), (-80.0, W, -138.2)], yaw=180)
    sfx(F.cursor, "kino.cannon_roll", pos=(-80.0, W + 0.5, -137.8), vol=1.0)
    sfx(F.cursor + T(0.8), "kino.cannon_roll", pos=(-80.0, W + 0.5, -137.8), vol=0.8, pitch=0.9)
    with F.shot(close("kino", F.cursor, 1.8, 25), name="i see") as s:
        s.wait(1.6)
        s.say("奇诺", "原来如此。")
    r1 = R[1]
    with F.shot(close("r1", F.cursor, 1.9, 20), name="doomed") as s:
        s.say("年轻男子", "完了……我们死定了……")
        s.say("男子", "放心，一切都还未定呢，知道吗？")
        s.say("年轻男子", "可是我们不过是普通人！不像那些家伙是经过严格训练的士兵……")
        s.say("年轻男子", "从没杀过人的我们，有可能打赢虐杀山贼的那群人吗？你说！有办法战斗吗？")
        s.say("男子", "不是啦……你——", dur=1.4)
    t_run = F.cursor
    r1.hold(t_run, None)
    F.event(t_run, "drop", model="rifle", pos=[-81.4, W + 1.0, -135.6], vel=[0.02, 0.1, 0.04], floor=W + 0.3)
    sfx(t_run + T(0.4), "kino.drop_metal", pos=(-81.4, W + 0.3, -135.6), vol=0.8)
    sfx(t_run + T(0.45), "kino.small_splash", pos=(-81.4, W + 0.3, -135.6), vol=0.8)
    run_end = walk(r1, t_run + T(0.3), [(-81.4, W, -135.6), (-80.0, W, -132.0), (-80.0, W, -120.0), (-80.2, W, -83.2)], speed=5.2)
    for t in range(t_run, run_end, 3):
        p = r1.track.at(t)
        F.event(t, "particle", type="splash", pos=[p[0], W + 0.4, p[2]], delta=(0.2, 0.02, 0.2), speed=0.08, count=4)
    with F.shot(S((-80.8, W + 1.7, -130.4), (-80.0, W + 1.1, -118.0)), name="run out") as s:
        s.say("年轻男子", "我受够了！", pause=0.2)
        s.say("年轻男子", "投降！我投降！")
    with F.shot(Cam.move((-82.2, W + 1.5, -104.0), (-82.2, W + 1.5, -92.0), "r1", "r1", kind="linear"), name="surrender") as s:
        s.say("年轻男子", "我投降！放过我一马！我投降！我投降！")
        s.wait(max(0.0, (run_end - s.cursor) / 20 - 0.2))
    t_shot = max(F.cursor, run_end)
    F.event(t_shot, "sound", sound="kino.gun_rifle_far", pos=[-66.5, 75, -66], vol=6.0, pitch=1.0)
    blood(t_shot + 2, (-80.2, W + 1.2, -83.2), 18)
    sfx(t_shot + 2, "kino.bullet_hit", pos=(-80.2, W + 1.2, -83.2), vol=1.0)
    sfx(t_shot + 4, "kino.fall_water", pos=(-80.2, W + 0.3, -83.2), vol=1.3)
    r1.pose(t_shot + 3, "swimming")
    F.event(t_shot + 6, "particle", type="splash", pos=[-80.2, W + 0.4, -83.2], delta=(0.5, 0.05, 0.5), speed=0.15, count=24)
    with F.shot(S((-77.6, W + 1.4, -86.8), (-80.2, W + 0.5, -83.0)), dur=3.2, name="shot") as s:
        s.say("", "砰！", pause=0.0, dur=1.2)
    r6 = R[6]
    r6.hold(F.cursor, "rifle", aim=True)
    with F.shot(S((-82.5, 74.6, -128.0), (-84.0, 74.4, -132.3)), name="roof fires") as s:
        s.say("屋顶的男子", "可恶！", pause=0.1)
        gunshot(s.cursor, (-84.0, 74.6, -131.4))
        sfx(s.cursor + T(0.6), "kino.bolt", pos=(-84.0, 74.6, -131.4), vol=0.8, pitch=0.8)
        s.wait(0.8)
    K.show(F.cursor).place(F.cursor, (-80.0, W, -131.6), 0, -35)
    with F.shot(S((-78.6, W + 0.9, -127.0), ("kino", 1.3)), name="don't waste") as s:
        s.say("奇诺", "如果看不到对方就不要开枪！那只是浪费子弹而已哟！")
        s.say("屋顶的男子", "……知道了，对不起……")
    r6.hold(F.cursor, "rifle_carry")
    WOMAN.show(F.cursor).place(F.cursor, (-78.6, W, -140.4), 180)
    WOMAN.hold(F.cursor, "baby")
    cry0 = F.cursor
    with F.shot(S((-79.6, W + 1.8, -137.4), (-78.6, W + 1.1, -140.4)), name="cry") as s:
        s.wait(0.6)
        s.say("", "（婴儿哇哇大哭起来）", dur=2.6)
    for t in range(cry0, cry0 + T(40), 26):
        F.event(t, "sound", sound="kino.baby_cry", pos=[-78.6, 66.0, -140.4], vol=2.5, pitch=1.3)
    K.hold(F.cursor, "canon")
    sfx(F.cursor + T(0.3), "kino.holster", pos=(-79.6, W + 1.0, -137.6), vol=0.8)
    K.place(F.cursor, (-79.6, W, -137.6), 160)
    with F.shot(close("kino", F.cursor, 1.6, -15, dy=-0.1), name="draw") as s:
        s.wait(2.2)
    for a in [K, DOC, WOMAN] + [R[i] for i in (2, 3, 4)]:
        a.show(F.cursor, False)
    L.update(t_shot=t_shot, cry0=cry0, CANNON=CANNON)
    build4(F, L)


def build4(F, L):
    """Scenes 13 - 18."""
    K, H, TRUCK, CAP, guards, SNIPER, DOC, WOMAN, R = (L[k] for k in ("K", "H", "TRUCK", "CAP", "guards", "SNIPER", "DOC", "WOMAN", "R"))
    seat, ride_to, walk, side_of, attach, mount, dismount, close, over, two, gunshot, blood, engine, title_card, S = (
        L[k] for k in ("seat", "ride_to", "walk", "side_of", "attach", "mount", "dismount", "close", "over", "two",
                       "gunshot", "blood", "engine", "title_card", "S"))
    CANNON = L["CANNON"]
    sfx = L["sfx"]
    g = guards

    def pos(a, t):
        p = a.track.at(t)
        return (p[0], p[1], p[2])

    def cry(t0, sec, far=False):
        """The princess crying in the keep; heard faintly all the way to the forest edge."""
        for t in range(t0, t0 + T(sec), 26):
            if far:
                sfx(t, "kino.baby_cry", glob=True, vol=0.45, pitch=1.3)
            else:
                F.event(t, "sound", sound="kino.baby_cry", pos=[-79.0, 66.0, -134.0], vol=3.0, pitch=1.3)

    def spyglass(t0, t1):
        sfx(t0, "kino.spyglass", glob=True, vol=0.7)
        sfx(t1 - T(0.15), "kino.spyglass_off", glob=True, vol=0.6)

    # ======================================================================
    # 13  森林边缘的男人们
    # ======================================================================
    F.scene("森林边缘", daytime=7300)
    t13 = F.cursor
    FIRE = (-84.0, G, -62.0)
    SEAT_SN = (-66.5, 70.95, -67.5)
    ss = seat("sniper")
    ss.show(t13).place(t13, SEAT_SN, 180)
    SNIPER.show(t13).ride(t13, ss)
    SNIPER.hold(t13, "srifle", aim=True)
    CAP.show(t13).place(t13, (-82.6, G, -64.6), 180)
    CAP.hold(t13, "binoculars")
    camp = {1: ((-86.6, G, -64.2), 170), 2: ((-85.6, G, -59.8), 200), 3: ((-81.8, G, -59.9), 150), 4: ((-88.2, G, -61.6), 120),
            7: ((-80.4, G, -63.2), 200), 8: ((-85.0, G, -57.8), 190), 10: ((-79.4, G, -58.6), 160)}
    for i, (p, yw) in camp.items():
        g[i].show(t13).place(t13, p, yw)
        g[i].pose(t13, "standing")
        g[i].hold(t13, "rifle_carry" if i < 8 else None)
    for i, (x, yw) in ((5, (-86.0, -90)), (6, (-82.0, 90))):
        st = seat(f"log{i}")
        st.show(t13).place(t13, (x, G + 0.9, -62.0), yw)
        g[i].show(t13).ride(t13, st)
        g[i].hold(t13, "rifle_carry")
    g[10].pose(t13, "sleeping")
    g9 = g[9]
    g9.show(t13).place(t13, (-89.0, G, -58.6), 110)
    g9.pose(t13, "standing")
    g9.hold(t13, "mug")
    with F.shot(S((-64.6, 72.4, -64.8), (-80.0, 66.0, -110.0)), name="sniper") as s:
        s.wait(0.6)
        s.say("狙击兵", "现在是还有办法狙击，要开枪吗？")
    with F.shot(close("captain", F.cursor, 2.3, 25), name="cap wait") as s:
        s.say("胡须男", "不，不用开枪。")
        s.say("胡须男", "还不用急，时间对我们有利。")
        s.say("狙击兵", "了解。")
    tt = F.cursor
    walk(g9, tt, [pos(g9, tt), (-85.5, G, -62.5), (-83.2, G, -63.4)], speed=1.2)
    CAP.turn(tt + T(2.0), tt + T(3.0), 90)
    with F.shot(two("captain", "g9", tt + T(4.0), 3.8), name="tea") as s:
        sfx(s.t0 + T(1.6), "kino.pour", pos=(-83.6, G + 1.0, -63.2), vol=0.8)
        s.wait(3.0)
        s.say("部下", "队长，请喝茶。")
        s.say("胡须男", "谢谢你，脚伤得怎么样？")
        s.say("部下", "很痛呢，我会把这股痛楚用来狠狠击垮那个旅行者的。")
        s.say("胡须男", "啊啊，就看你的了。说什么都要带公主殿下一起回国，大家都在等着呢。")
        s.say("部下", "是！")
    g9.hold(F.cursor - T(1.0), None)
    CAP.hold(F.cursor - T(1.0), "mug")
    sfx(F.cursor - T(0.2), "kino.drink", follow="captain", vol=0.8)
    cry(F.cursor, 6, far=True)
    with F.shot(S((-78.6, G + 1.6, -60.2), (-84.0, G + 1.2, -62.0)), name="laugh") as s:
        s.say("", "（远方清楚传来婴儿的哭泣声）", pause=0.4, dur=2.4)
        s.say("部下", "是公主殿下，看样子她精神不错呢！")
        s.say("", "（男人们都笑了起来）", dur=1.8)
    # gunfire inside the keep
    tg = F.cursor
    for k in range(18):
        t = tg + T(0.4) + int(k * 32 * (0.6 + 0.4 * ((k * 7) % 5) / 5))
        loud = k % 3 != 1
        F.event(t, "sound", sound="kino.gun_pistol_far" if loud else "kino.gun_rifle_far", pos=[-80.0, 66.0, -136.0], vol=8.0,
                pitch=1.0)
        wx, wz = ((-80.0, -131.2), (-85.0, -131.2), (-75.0, -131.2))[k % 3]
        F.event(t, "particle", type="small_flame", pos=[wx, 67.6 if k % 3 else 65.8, wz], delta=(0.2, 0.2, 0.05), speed=0.0, count=6)
        F.event(t, "particle", type="smoke", pos=[wx, 67.6 if k % 3 else 65.8, wz - 0.2], delta=(0.2, 0.2, 0.1), speed=0.01, count=5)
    t_end_fire = tg + T(18.0)
    CAP.hold(tg + T(2.0), "binoculars")
    with F.shot(close("captain", F.cursor, 2.1, -20), name="what") as s:
        s.wait(0.6)
        s.say("胡须男", "什么？对方往这边开枪吗？")
        s.say("部下", "不是的！")
        s.say("狙击兵", "是那里面发生枪战！")
        s.say("胡须男", "什么？")
    CAP.turn(F.cursor - T(1.5), F.cursor - T(1.0), 180, -2)
    F.overlay(F.cursor, "binoculars")
    with F.shot(S((-80.4, 67.0, -118.0), (-80.0, 67.0, -131.0)), name="bino1") as s:
        s.wait(1.6)
        s.say("胡须男", "他们……开始起内讧了吗？")
        spyglass(s.t0, s.cursor + T(0.4))
    F.overlay(F.cursor, "letterbox")
    with F.shot(S((-88.6, G + 1.7, -57.0), (-83.5, G + 1.2, -62.0)), name="angry") as s:
        s.say("部下", "王八蛋！怎么当着公主殿下的面干这种事！")
        s.say("部下", "那群白痴！")
        s.say("部下", "该死会是那个旅行者干的吧！")
    with F.shot(S((-64.8, 71.6, -69.4), ("sniper", 1.3)), name="sniper2") as s:
        s.say("狙击兵", "监视者下楼了！要闯进去吗？")
    with F.shot(close("captain", F.cursor, 2.0, 25), name="wait more") as s:
        s.say("胡须男", "现在突击太危险了，再等一会儿。", pause=0.1)
    for i in (6, 7):
        R[i].show(F.cursor - T(3.0), False)
    H.show(F.cursor)
    with F.shot(S((-71.8, W + 1.0, -111.2), ("hermes", 0.8)), name="hermes") as s:
        s.say("艾鲁梅斯", "喔，打起来了打起来了。『卡农』及『森之人』卯起来射击了呢。")
        s.wait(max(0.5, (t_end_fire - s.cursor) / 20))
    with F.shot(S((-83.2, G + 1.6, -66.4), (-82.6, G + 1.4, -64.6)), name="quiet") as s:
        s.wait(1.4)
        s.say("部下", "难不成那个旅行者把那些随从杀了……？")
        s.say("胡须男", "不知道，但是——有那个可能。")
        s.say("狙击兵", "队、队长！请你快看入口！")

    # ---- the bodies -------------------------------------------------------
    F.scene("尸体", daytime=7600)
    spots = [(-82.3, -127.8), (-77.7, -127.8), (-82.3, -126.0), (-77.7, -126.0), (-82.3, -124.2), (-77.7, -124.2),
             (-82.3, -129.6), (-77.7, -129.6)]
    decoys = []
    for k in range(8):
        d = F.actor(f"decoy{k}", "decoy_suit" if k == 6 else "decoy_black", label="尸体")
        decoys.append(d)
    t_b = F.cursor
    bino_cam = S((-80.3, 66.4, -116.0), (-80.0, 65.6, -128.0))
    throw_times = []

    def throw(k, t):
        d = decoys[k]
        x, z = spots[k]
        d.show(t).place(t, (-80.0, W, -131.8), 0)
        d.pose(t, "swimming")
        d.move(t + T(0.3), t + T(1.3), [(-80.0, W, -131.8), (x, W, z + 0.2), (x, W, z)], ease_kind="out", yaw=(-25 if x < -80 else 25))
        K.show(t).place(t, (-80.0, W, -132.6), 0)
        K.move(t, t + T(1.2), [(-80.0, W, -132.6), (-80.0 + (x + 80) * 0.25, W, -131.4)], ease_kind="out")
        K.show(t + T(2.0), False)
        F.event(t + T(1.2), "particle", type="splash", pos=[x, W + 0.4, z], delta=(0.5, 0.05, 0.5), speed=0.15, count=24)
        F.event(t + T(1.2), "sound", sound="kino.fall_water", pos=[x, W, z], vol=1.5, pitch=0.9)
        sfx(t + T(0.2), "kino.cloth", pos=(-80.0, W + 1.0, -131.8), vol=0.8, pitch=0.8)
        throw_times.append(t)

    F.overlay(t_b, "binoculars")
    with F.shot(bino_cam, name="body1") as s:
        s.wait(0.6)
        throw(0, s.cursor)
        s.say("胡须男", "什么！", pause=0.4)
        s.wait(1.4)
        spyglass(s.t0, s.cursor + T(0.4))
    F.overlay(F.cursor, "letterbox")
    with F.shot(S((-64.8, 71.6, -69.4), ("sniper", 1.3)), name="again") as s:
        throw(1, s.t0 + T(0.4))
        s.say("狙击兵", "又开始了。", pause=0.8)
        s.say("狙击兵", "等那旅行者再次出现时，就射击她的手臂怎么样？")
    cry(F.cursor, 5, far=True)
    with F.shot(close("captain", F.cursor, 2.0, 20), name="stop") as s:
        s.say("", "（婴儿的哭声）", dur=1.4)
        s.say("胡须男", "住手！公主殿下没事！")
        s.say("狙击兵", "了解，那我等队长的指示。")
    F.overlay(F.cursor, "binoculars")
    with F.shot(bino_cam, name="body3") as s:
        s.wait(0.3)
        throw(2, s.cursor)
        s.say("", "（尸体的脸被染得一片鲜红，根本就看不出是谁）", pause=0.8, dur=3.0)
        spyglass(s.t0, s.cursor + T(0.4))
    F.overlay(F.cursor, "letterbox")
    with F.shot(S((-88.6, G + 1.7, -57.0), (-83.5, G + 1.2, -62.0)), name="guess") as s:
        s.say("部下", "那家伙在干什么啊……？")
        s.say("部下", "该不会那名旅行者已经知道事情的来龙去脉，想拿公主殿下当作跟我们交涉的筹码？")
    with F.shot(close("captain", F.cursor, 2.1, -25), name="plan") as s:
        s.say("胡须男", "这家伙有一套，她是刻意让我们看到尸体的。只要她主动提出，就答应跟她交涉吧。")
        s.say("部下", "队、队长！可是——")
        s.say("胡须男", "我们的目的是什么？")
        s.say("部下", "……是！是把公主殿下平安带回祖国！")
        s.say("胡须男", "没错，只要能完成那个任务，就算跟耍小聪明又有点肮脏的旅行者谈谈也无所谓。")
        s.say("胡须男", "只不过，是赏她一颗全金属包覆弹头的铅弹。我们有优秀的狙击兵，可以从背后赏她一发。")
    t_mont = F.cursor
    F.overlay(t_mont, "binoculars")
    with F.shot(bino_cam, name="bodies 4-6") as s:
        throw(3, s.t0 + T(0.4))
        throw(4, s.t0 + T(3.2))
        throw(5, s.t0 + T(6.0))
        s.wait(8.0)
        s.say("狙击兵", "是第六个。建筑物里面还有两个男人，其他就只剩下公主殿下跟那个女人而已。")
        s.say("胡须男", "好了，你是否能顺利把所有人都杀了呢，旅行者呀！")
        sfx(s.t0, "kino.spyglass", glob=True, vol=0.7)
    # the seventh: the grey suit, three shots at point-blank range
    with F.shot(bino_cam, name="suit") as s:
        throw(6, s.t0 + T(0.4))
        t7 = s.t0 + T(2.0)
        K.show(t7).place(t7, (-80.6, W, -131.4), 30, 25)
        K.hold(t7, "canon", aim=True)
        for j in range(3):
            tj = t7 + T(1.0 + 0.45 * j)
            gunshot(tj, (-81.1, W + 1.3, -130.6), loud=False)
            blood(tj + 1, (spots[6][0] + 0.3, W + 0.4, spots[6][1] + 0.8), 16)
            sfx(tj + 1, "kino.bullet_hit", pos=(spots[6][0] + 0.3, W + 0.4, spots[6][1] + 0.8), vol=0.9, pitch=1.0 + 0.1 * j)
        K.show(t7 + T(3.2), False)
        K.hold(t7 + T(3.2), None)
        s.wait(4.2)
        sfx(s.cursor + T(0.2), "kino.spyglass_off", glob=True, vol=0.6)
    F.overlay(F.cursor, "letterbox")
    with F.shot(S((-88.6, G + 1.7, -57.0), (-83.5, G + 1.2, -62.0)), name="cruel") as s:
        s.say("部下", "致命的一击啊……")
        s.say("部下", "怎么会有这种家伙。")
        s.say("胡须男", "振作点！事情还没结束呢！")
    F.overlay(F.cursor, "binoculars")
    with F.shot(bino_cam, name="last") as s:
        throw(7, s.t0 + T(0.4))
        s.say("狙击兵", "最后一个了。", pause=1.2)
        s.wait(0.8)
        spyglass(s.t0, s.cursor + T(0.4))
    F.overlay(F.cursor, "letterbox")
    with F.shot(close("captain", F.cursor, 2.1, 25), name="admire") as s:
        s.say("胡须男", "没想到她把他们全干掉了……真让我感到佩服，了不起。")
        s.say("胡须男", "好了，接下要丢什么出来呢，优秀的旅行者。")
    # Kino calls out from the doorway
    tk = F.cursor
    K.show(tk).place(tk, (-80.0, W, -132.2), 0)
    K.pose(tk, "crouching")
    with F.shot(S((-80.0, 66.4, -120.0), (-80.0, 66.2, -131.0)), name="call") as s:
        s.wait(1.0)
        s.say("奇诺", "我有话要说！听——得——见——我——说——话——吗——！", dur=4.2)
    with F.shot(close("captain", F.cursor, 2.0, -20), name="reply") as s:
        s.say("胡须男", "啊啊！听得见！你那边情况如何？")
    with F.shot(S((-78.6, W + 0.9, -133.6), ("kino", 1.0)), name="wash") as s:
        for k in range(3):
            sfx(s.t0 + T(0.2 + 0.45 * k), "kino.small_splash", follow="kino", vol=0.7, pitch=1.3 + 0.1 * k)
        s.say("奇诺", "喔——这个可帮了不少忙呢？", pause=0.6)
        K.pose(s.cursor, "standing")
        s.say("奇诺", "我听见你说话了——！我有话想跟你说，可以吗？")
    with F.shot(close("captain", F.cursor, 2.0, 20), name="say it") as s:
        s.say("胡须男", "你说说看！")
    with F.shot(S((-81.8, W + 1.3, -127.2), ("kino", 1.3)), name="speech") as s:
        s.say("奇诺", "委托我当护卫的那些人欺骗了我，所以我把他们全杀了！")
        s.say("奇诺", "我拷问那个女人之后，得知婴儿是一位公主！")
        s.say("奇诺", "我对你们的继承人之战没有兴趣！对我来说，自己跟摩托车的安全才是第一位！")
        s.say("奇诺", "请你们确认尸体的身份，然后过来这边接婴儿！")
        s.say("奇诺", "呼……喉咙累死了。", pause=0.6)
    with F.shot(close("captain", F.cursor, 2.1, -25), name="agree") as s:
        s.say("胡须男", "我答应你。")
        s.say("胡须男", "受伤的三个人待在森林里，狙击兵继续留在树上，其余的七个人跟我过去。")
        s.say("胡须男", "我们现在有八个人要过去！要是你敢开任何一枪，我们的交涉就决裂了！")
    with F.shot(S((-81.8, W + 1.3, -127.2), ("kino", 1.3)), name="ok") as s:
        s.say("奇诺", "知道了！最起码请你们过来能够正常说话的位置哟！咳咳！")

    # ======================================================================
    # 14  用「枪」决胜负
    # ======================================================================
    F.scene("决胜负", daytime=7900)
    t14 = F.cursor
    for i in (5, 6):
        g[i].ride(t14, None)
    CAP.hold(t14, "rifle_carry")
    cols = {"captain": (-77.4, -111.0), 1: (-82.6, -111.0), 2: (-77.4, -113.0), 3: (-82.6, -113.0),
            4: (-77.4, -115.0), 5: (-82.6, -115.0), 6: (-77.4, -117.0), 7: (-82.6, -117.0)}
    arrive = {}
    for k, (x, z) in cols.items():
        a = CAP if k == "captain" else g[k]
        start = pos(a, t14) if a.track.at(t14) else (x, G, -62.0)
        a.place(t14, start, 180)
        a.hold(t14, "rifle_carry")
        lag = 0 if k == "captain" else (k * 0.35)
        path = [start, (x * 0.5 + -80 * 0.5, G, -68.0), (x, W, -74.0), (x, W, z)]
        arrive[k] = walk(a, t14 + T(lag), path, speed=3.4)
        a.face_to(arrive[k], arrive[k] + 6, (-80.0, 66.5, -131.0))
    t_halt = max(arrive.values())
    for t in range(t14 + T(6.0), t_halt, 5):
        for k in cols:
            a = CAP if k == "captain" else g[k]
            p = a.track.at(t)
            if p and p[2] < -73 and (t + (k if isinstance(k, int) else 0)) % 10 == 0:
                F.event(t, "particle", type="splash", pos=[p[0], W + 0.4, p[2]], delta=(0.15, 0.02, 0.15), speed=0.05, count=3)
    K.pose(t14, "standing")
    K.place(t14, (-80.0, W, -131.9), 0)
    with F.shot(S((-79.0, W + 2.8, -103.0), (-80.0, W + 1.0, -80.0)), name="advance") as s:
        s.wait(2.0)
        s.say("胡须男", "好！大家千万不要大意！", pause=0.1)
        s.wait(1.0)
    with F.shot(close("kino", F.cursor, 1.9, 15), name="coming") as s:
        s.say("奇诺", "过来了吗……", pause=0.6)
        s.say("奇诺", "好了……就照你说的，用『枪』决胜负吧。", pause=0.6)
        s.say("男子", "真、真的没问题吗？")
        s.say("奇诺", "这个嘛，得试试看才知道呢。")
        s.say("奇诺", "不过这种事情我在学校里学过，应该会很顺利才对。")
        s.say("奇诺", "也请你们照计划去做，导火线的长度可是很重要的呢。")
    CANNON.place(F.cursor, (-80.0, W, -133.9), 180)
    sfx(F.cursor, "kino.cannon_roll", pos=(-80.0, W + 0.5, -134.5), vol=0.9, pitch=0.9)
    with F.shot(Cam.move((-86.0, W + 2.2, -118.0), (-86.0, W + 2.6, -110.0), "captain", "captain", kind="linear"),
                dur=max(3.0, (t_halt - F.cursor) / 20 + 0.5), name="walk in") as s:
        pass
    # Kino appears on the roof with the baby
    K.show(F.cursor, False)
    tr = F.cursor
    K.show(tr + T(3.0)).place(tr + T(3.0), (-80.0, 74.0, -131.05), 0)
    K.hold(tr + T(3.0), "baby")
    K.hold(tr + T(3.0), None, hand="off")
    with F.shot(close("captain", F.cursor, 2.2, 25), name="traveller!") as s:
        s.say("胡须男", "旅行者！")
        s.say("胡须男", "来到这里你就听得见了吧？这样一来我们双方就不用喊到喉咙痛得要命了。")
        s.say("奇诺", "我也有同感。")
    CAP.face_to(F.cursor, F.cursor + 8, "kino")
    with F.shot(S((-79.0, W + 1.3, -108.2), ("kino", 1.2)), name="on the roof") as s:
        s.wait(1.0)
        s.say("胡须男", "公主殿下……", pause=0.2)
    with F.shot(S((-65.0, 72.2, -68.9), ("sniper", 1.3)), name="sniper aim") as s:
        s.say("狙击兵", "王八蛋……")
        s.say("", "（瞄准镜的十字线对准了旅行者的喉咙——但婴儿可能会摔下来）", dur=3.2)
        s.say("狙击兵", "可恶！")
    roof_cam = S((-79.2, 75.6, -126.0), ("kino", 1.2))
    with F.shot(roof_cam, name="hello") as s:
        s.say("胡须男", "嗨，旅行者！")
        s.say("奇诺", "你好，你就是队长吧？这距离大概有二十公尺吧？很高兴能像早上那样跟你正常交谈呢。")
    with F.shot(close("captain", F.cursor, 2.2, -20), name="princess") as s:
        s.say("胡须男", "旅行者你抱在怀里的，应该是我国非常重要的公主殿下吧？")
    with F.shot(roof_cam, name="yes") as s:
        s.say("奇诺", "是的，我从躺在那儿的人们口中得知所有来龙去脉了。听说你们打算立这孩子为王，复兴王室是吧？")
        s.say("胡须男", "一点也没错。")
        s.say("奇诺", "老实说那些事情跟我一点关系也没有。对我来说，最重要的就是我跟我的摩托车艾鲁梅斯是否能跟过去一样继续旅行。")
        s.say("奇诺", "因此我才把欺骗我，还害我卷入这场风波的那些人干掉。")
    with F.shot(close("captain", F.cursor, 2.1, 25), name="humour") as s:
        s.say("胡须男", "真了不起，也很感谢你减轻我们的工作。虽然你伤了我三名可爱的部下，不过他们并没有生命危险。")
        s.say("胡须男", "那件事情就在如此美妙的场所付诸流水，当作没发生过怎么样？")
    with F.shot(S((-71.8, W + 1.0, -111.2), ("hermes", 0.8)), name="hermes joke") as s:
        s.say("艾鲁梅斯", "喔，挺幽默的嘛——")
    with F.shot(roof_cam, name="proposal") as s:
        s.say("奇诺", "这主意不错，那么接下来就是我的提议。")
        s.say("胡须男", "好，请说。")
        s.say("奇诺", "我会抱着这个孩子跨上艾鲁梅斯回到那条道路，你们则驾驶那辆卡车在后面跟着。")
        s.say("奇诺", "接着你们就带着婴儿，开着卡车回国去吧。以上就是我的提议。")
    with F.shot(close("captain", F.cursor, 2.1, -25), name="or else") as s:
        s.say("胡须男", "这提议很赞，对我们来说没有拒绝的理由呢。只不过，如果我们拒绝或是在半路对你出手，会有什么样的后果呢？")
    K.hold(F.cursor + T(1.5), "bottle", hand="off")
    with F.shot(close("kino", F.cursor + T(1.0), 1.8, 20), name="bottle") as s:
        s.say("奇诺", "我不太愿意臆测那个后果耶。")
        s.wait(1.2)
        s.say("奇诺", "如果我倒下而在上面加诸力道，我跟艾鲁梅斯就会连同这孩子一起『砰』！")
    with F.shot(S((-84.8, W + 1.6, -116.4), ("captain", 1.2)), name="bastard") as s:
        s.say("部下", "你这家伙！")
        s.say("胡须男", "我也不愿意臆测那样的后果呢，不过目前我们会尽最大的努力，不让事情演变成那么可怕的后果的。")
    with F.shot(roof_cam, name="deal") as s:
        s.say("奇诺", "那么交涉成立啰！")
        s.say("胡须男", "是的，成立了。我们会默默目送你离开的。")
        s.say("奇诺", "不过，会默许狙击兵开枪是吗？")
    with F.shot(close("captain", F.cursor, 2.0, 20), name="silence") as s:
        s.say("胡须男", "…………", pause=0.3, dur=1.6)
    t_jump = F.cursor + T(2.4)
    with F.shot(roof_cam, name="if it were me") as s:
        s.say("奇诺", "如果是我，真的会那么做哟！")
        K.move(s.cursor, s.cursor + T(0.5), [(-80.0, 74.0, -131.05), (-80.0, 73.3, -132.0), (-80.0, 73.0, -132.6)], ease_kind="out")
        K.pose(s.cursor + T(0.4), "crouching")
        s.say("奇诺", "开车！", pause=0.4, dur=1.0)
    t_fire = F.cursor
    sfx(t_fire - T(2.6), "kino.fuse", pos=(-80.0, W + 0.8, -134.4), vol=1.6)
    sfx(t_fire - T(2.7), "kino.ignite", pos=(-80.0, W + 0.8, -134.4), vol=0.9)
    # ---------------- the cannon ------------------------------------------
    F.event(t_fire, "sound", sound="kino.cannon", pos=[-80.0, 66.0, -135.5], vol=8.0, pitch=0.7)
    F.event(t_fire, "particle", type="explosion", pos=[-80.0, 66.0, -135.6], delta=(0.6, 0.4, 0.6), speed=0.0, count=10)
    F.event(t_fire, "particle", type="large_smoke", pos=[-80.0, 66.0, -131.0], delta=(0.6, 0.6, 0.4), speed=0.08, count=40,
            dir=[0, 0.02, 0.25])
    t_ex = t_fire + T(1.7)
    CANNON.move(t_fire, t_ex, [(-80.0, W, -133.9), (-80.0, W, -112.3)], ease_kind="out", yaw=180)
    for t in range(t_fire, t_ex, 2):
        p = CANNON.track.at(t)
        F.event(t, "particle", type="splash", pos=[p[0], W + 0.4, p[2]], delta=(0.9, 0.1, 0.4), speed=0.2, count=6)
    CANNON.show(t_ex, False)
    with F.shot(S((-80.6, W + 3.6, -99.0), (-80.0, 67.0, -126.0)), dur=1.1, name="burst out") as s:
        pass
    with F.shot(S((-74.8, W + 1.5, -110.2), ("captain", 1.3)), name="haha") as s:
        s.say("胡须男", "什么！", pause=0.0, dur=0.7)
        s.say("胡须男", "哈哈！", pause=0.0, dur=0.6)
        s.say("胡须男", "咦？", pause=0.0, dur=0.6)
    F.cursor = max(F.cursor, t_ex - T(0.1))
    EX = (-80.0, W + 0.8, -112.3)
    F.event(t_ex, "sound", sound="kino.explosion", pos=list(EX), vol=10.0, pitch=0.8)
    F.event(t_ex, "particle", type="explosion", pos=list(EX), delta=(1.6, 1.0, 1.6), speed=0.0, count=40, spread=8)
    F.event(t_ex, "particle", type="flame", pos=list(EX), delta=(2.2, 0.8, 2.2), speed=0.12, count=160)
    F.event(t_ex, "particle", type="lava", pos=list(EX), delta=(0.5, 0.3, 0.5), speed=0.3, count=40)
    F.event(t_ex + 4, "particle", type="large_smoke", pos=list(EX), delta=(2.0, 1.4, 2.0), speed=0.05, count=90)
    for tt_ in range(t_ex, t_ex + T(6), 10):
        F.event(tt_, "particle", type="flame", pos=[EX[0], W + 0.6, EX[2]], delta=(1.4, 0.2, 1.4), speed=0.02, count=12)
    for k, tt_ in enumerate(range(t_ex + 4, t_ex + T(6), 16)):
        sfx(tt_, "kino.fire", pos=(EX[0] + (k % 3 - 1) * 1.2, W + 0.8, EX[2]), vol=1.4, pitch=0.8 + 0.1 * (k % 3))
    for k in range(6):
        a_ = k * 1.1
        sfx(t_ex + T(0.5 + 0.2 * k), "kino.small_splash", pos=(EX[0] + math.sin(a_) * 3, W + 0.3, EX[2] + math.cos(a_) * 3),
            vol=0.9, pitch=0.8 + 0.1 * (k % 4))
    # burning front four, the rest blown into the walls
    burning = [CAP, g[1], g[2], g[3]]
    for j, a in enumerate(burning):
        a.burn(t_ex, t_ex + T(3.0 + 0.7 * j))
        a.hold(t_ex, None)
        for tt_ in range(t_ex + T(0.3 + 0.2 * j), t_ex + T(2.6), T(0.8)):
            sfx(tt_, "kino.burn_hurt", follow=a.id, vol=0.9, pitch=0.9 + 0.05 * j)
        p = pos(a, t_ex)
        wob = [p]
        for k in range(1, 6):
            wob.append((p[0] + math.sin(k * 1.7 + j) * 0.9, W, p[2] + math.cos(k * 2.3 + j) * 0.9))
        a.move(t_ex, t_ex + T(3.0 + 0.7 * j), wob)
    blown = {4: (-70.9, -116.8), 5: (-89.2, -116.2), 6: (-71.2, -118.9), 7: (-89.0, -118.4)}
    for i, (x, z) in blown.items():
        a = g[i]
        p = pos(a, t_ex)
        a.hold(t_ex, None)
        a.move(t_ex, t_ex + 6, [p, (x, W + 0.6, z)], ease_kind="out", yaw=(90 if x < -80 else -90))
        a.place(t_ex + 7, (x + (0.6 if x < -80 else -0.6), W, z), 90 if x < -80 else -90)
        a.pose(t_ex + 7, "swimming")
        blood(t_ex + 6, (x, W + 1.2, z), 20)
        sfx(t_ex + 6, "kino.hit", pos=(x, W + 1.2, z), vol=1.2, pitch=0.8)
        sfx(t_ex + 8, "kino.fall_water", pos=(x, W + 0.3, z), vol=1.0)
    # the barrel flies and smashes a wall
    BARREL = F.prop("barrel", "cannon_barrel", translation=(0, 0.5, 0))
    BARREL.show(t_ex)
    t_hit = t_ex + T(1.2)
    BARREL.move(t_ex, t_hit, [(-80.0, W + 0.8, -112.3), (-83.0, W + 5.0, -109.0), (-86.0, W + 4.2, -106.0), (-88.3, W + 1.2, -103.6)],
                yaw=135)
    BARREL.place(t_hit + 1, (-89.8, W + 0.1, -103.2), 150)
    F.event(t_hit, "blocks", list=[list(b) for b in world.smashed_wall()])
    F.event(t_hit, "sound", sound="kino.stone", pos=[-88.0, 66.0, -103.5], vol=4.0, pitch=0.6)
    F.event(t_hit, "particle", type="poof", pos=[-88.0, W + 1.5, -103.5], delta=(0.6, 0.8, 0.8), speed=0.1, count=40)
    with F.shot(S((-96.0, W + 5.5, -121.0), (-80.0, W + 1.0, -111.0)), dur=3.2, name="boom") as s:
        pass
    with F.shot(S((-70.0, W + 0.9, -104.8), ("hermes", 0.8)), name="close call") as s:
        s.say("艾鲁梅斯", "危险险险险险险险险险险险险险哪！", pause=0.1, dur=2.4)
    # ======================================================================
    # 15  狙击兵
    # ======================================================================
    F.scene("狙击兵")
    F.overlay(F.cursor, "scope")
    with F.shot(S((-78.5, 67.6, -99.5), (-80.0, 65.8, -113.5)), name="mercy") as s:
        s.wait(0.3)
        for j, a in enumerate(burning):
            tj = s.cursor + T(0.9 * j)
            sfx(tj, "kino.gun_rifle", glob=True, vol=0.9, pitch=0.95)
            if j < 3:
                sfx(tj + T(0.45), "kino.bolt", glob=True, vol=0.5)
            a.burn(t_ex, tj)
            a.pose(tj + 2, "swimming")
            blood(tj + 2, pos(a, tj), 10)
            sfx(tj + 3, "kino.fall_water", pos=pos(a, tj), vol=0.8)
            a.move(tj + 2, tj + 3, [pos(a, tj + 2), pos(a, tj + 2)])
        s.wait(3.6)
        s.say("", "（首先是敬爱的队长。过去在军校的同期战友。有时候让人感到讨厌的二年级学弟。当成弟弟看待的年轻男子。）",
              dur=4.5)
    F.overlay(F.cursor, "letterbox")
    SNIPER.hold(F.cursor, "srifle_carry")
    with F.shot(S((-64.8, 71.6, -69.4), ("sniper", 1.3)), name="sniper numb") as s:
        s.say("狙击兵", "…………", dur=1.6)
    # retreat along the track
    tret = F.cursor
    SNIPER.ride(tret, None)
    SNIPER.place(tret, (-67.0, G, -68.4), 0)
    g10 = g[10]
    g10.pose(tret, "sleeping")
    blood(tret, (-79.4, G + 0.3, -58.6), 12)
    g8, g9 = g[8], g[9]
    g8.place(tret, (-83.0, G, -61.0), 0)
    g9.place(tret, (-83.8, G, -61.2), 0)
    g8.hold(tret, None)
    g9.hold(tret, None)
    with F.shot(S((-80.0, G + 1.7, -55.0), ("sniper", 1.2)), name="retreat") as s:
        s.say("狙击兵", "暂时撤退！", pause=0.3)
        s.say("", "（一个人的脸部被粗大的木片刺中，已经不动了）", dur=2.6)
    tr2 = F.cursor
    run_pts = [(-80.4, G, -52.0), (-80.0, G, -46.0), (-81.6, G, -38.0)]
    walk(SNIPER, tr2, [(-67.0, G, -68.4), (-78.0, G, -60.0)] + run_pts, speed=3.2)
    walk(g8, tr2, [(-83.0, G, -61.0)] + [(x + 0.8, y, z - 1.2) for (x, y, z) in run_pts], speed=3.0)
    t_fall = walk(g9, tr2, [(-83.8, G, -61.2)] + [(x - 0.6, y, z + 0.4) for (x, y, z) in run_pts[:2]], speed=2.6)
    g9.pose(t_fall, "crouching")
    sfx(t_fall, "kino.hurt", follow="g9", vol=0.8, pitch=0.8)
    with F.shot(Cam.move((-77.0, G + 1.8, -44.0), (-77.4, G + 1.8, -40.0), "g9", "g9"), name="run") as s:
        s.wait(max(1.0, (t_fall - s.t0) / 20))
        s.say("狙击兵", "撑着点！没事的！对方不会马上追过来的！只要到达道路，跑到我们系马的地方就没问题了！知道吗？")
        s.say("部下", "好……")
    g9.pose(F.cursor, "standing")
    tr3 = F.cursor
    walk(g9, tr3, [pos(g9, tr3), (-81.5, G, -36.8)], speed=2.2)
    walk(SNIPER, tr3, [pos(SNIPER, tr3), (-82.2, G, -35.4)], speed=2.0)
    walk(g8, tr3, [pos(g8, tr3), (-81.0, G, -33.6)], speed=2.2)
    g8.turn(tr3 + T(1.6), tr3 + T(2.0), 180)
    with F.shot(two("g8", "g9", tr3 + T(2.0), 3.6), name="angel") as s:
        s.wait(1.4)
        s.say("部下", "加油！走不动的话我来背你！")
        s.say("伤兵", "哼！想不到会有这么一天，我竟然会把你的声音听成是天使的声音呢！")
        s.say("部下", "混帐东西！我什么时候变成天使的——", dur=2.0)
    # the "bandits" strike
    ta = F.cursor - T(0.6)
    x3 = F.actor("x3", "retainer_c_bandit", label="山贼")
    x4 = F.actor("x4", "retainer_b_bandit", label="山贼")
    x7 = F.actor("x7", "retainer_a_bandit", label="山贼")
    p8 = pos(g8, ta)
    x3.show(ta).place(ta, (p8[0] + 2.2, G, p8[2] - 0.6), 90)
    x3.hold(ta, "knife")
    x3.move(ta, ta + T(0.4), [(p8[0] + 2.2, G, p8[2] - 0.6), (p8[0] + 0.6, G, p8[2])], yaw=90)
    blood(ta + T(0.4), (p8[0], G + 1.0, p8[2]), 20)
    F.event(ta + T(0.4), "sound", sound="kino.stab", pos=list(p8), vol=2.0, pitch=1.0)
    g8.pose(ta + T(0.9), "swimming")
    sfx(ta + T(0.9), "kino.fall", pos=p8, vol=1.0)
    x3.pose(ta + T(1.0), "crouching")
    with F.shot(S((p8[0] - 3.0, G + 1.6, p8[2] - 2.6), ("g8", 1.0)), dur=1.8, name="stab") as s:
        pass
    tb = F.cursor
    p9 = pos(g9, tb)
    x4.show(tb - T(0.4)).place(tb - T(0.4), (p9[0] - 2.0, G, p9[2] + 1.2), -60)
    x4.hold(tb - T(0.4), "axe", aim=True)
    x4.move(tb, tb + T(0.4), [(p9[0] - 2.0, G, p9[2] + 1.2), (p9[0] - 0.7, G, p9[2] + 0.4)], yaw=-60)
    blood(tb + T(0.5), (p9[0], G + 1.6, p9[2]), 24)
    F.event(tb + T(0.5), "sound", sound="kino.axe", pos=list(p9), vol=2.0, pitch=1.0)
    g9.pose(tb + T(0.9), "swimming")
    sfx(tb + T(0.9), "kino.fall", pos=p9, vol=1.0)
    with F.shot(close("sniper", tb, 2.4, 30), name="axe") as s:
        s.say("山贼", "哇啊啊啊！", pause=0.0, dur=1.4)
    SNIPER.hold(F.cursor - T(0.6), "srifle", aim=True)
    tc = F.cursor
    ps = pos(SNIPER, tc)
    x7.show(tc).place(tc, (ps[0], G, ps[2] + 0.7), 180)
    F.event(tc + T(0.4), "sound", sound="kino.gun_rifle", pos=list(ps), vol=4.0, pitch=1.0)
    SNIPER.turn(tc + T(0.3), tc + T(0.5), 180, -30)
    with F.shot(close("sniper", tc, 2.4, -35), name="grab") as s:
        s.say("山贼", "去死吧！", pause=0.3, dur=1.2)
        F.event(s.cursor, "sound", sound="kino.punch", pos=list(ps), vol=2.0, pitch=1.0)
        s.say("狙击兵", "喝呀！", pause=0.2, dur=1.0)
    tj = F.cursor
    x7.move(tj, tj + T(0.5), [(ps[0], G + 0.1, ps[2] + 0.7), (ps[0], G + 1.6, ps[2]), (ps[0], G, ps[2] - 1.4)], yaw=0)
    x7.pose(tj + T(0.4), "sleeping")
    F.event(tj + T(0.5), "sound", sound="kino.punch", pos=list(ps), vol=2.0, pitch=0.7)
    sfx(tj + T(0.55), "kino.fall", pos=(ps[0], G, ps[2] - 1.4), vol=1.2)
    SNIPER.hold(tj, None)
    SNIPER.turn(tj + T(0.8), tj + T(1.2), 90, 0)
    p4 = pos(x4, tj)
    x4.move(tj + T(1.0), tj + T(1.6), [p4, (ps[0] - 1.1, G, ps[2] + 0.2)], yaw=-90)
    blood(tj + T(1.7), (ps[0], G + 1.6, ps[2]), 30)
    F.event(tj + T(1.7), "sound", sound="kino.axe", pos=list(ps), vol=2.5, pitch=0.8)
    SNIPER.pose(tj + T(1.9), "swimming")
    sfx(tj + T(1.9), "kino.fall", pos=ps, vol=1.0)
    with F.shot(S((ps[0] + 3.2, G + 1.7, ps[2] + 1.8), ("sniper", 1.0)), dur=3.0, name="throw") as s:
        pass
    F.overlay(F.cursor, "black")
    for k in range(5):
        sfx(F.cursor + T(0.3 + 0.35 * k), "kino.stab" if k % 2 else "kino.axe", glob=True, vol=0.55, pitch=0.8 + 0.05 * k)
    with F.shot(Cam.static((0, 120, 0), (10, -30)), dur=2.6, name="black"):
        pass
    F.overlay(F.cursor, "letterbox")
    everyone = [CAP, SNIPER, x3, x4, x7] + [g[i] for i in range(1, 11)] + decoys + [K, H, TRUCK, CANNON, BARREL]
    L.update(decoys=decoys, x3=x3, x4=x4, x7=x7, BARREL=BARREL, everyone=everyone)
    build5(F, L)


def build5(F, L):
    """Scenes 16 - 18: the toast, dusk, epilogue."""
    K, H, TRUCK, DOC, WOMAN, R = (L[k] for k in ("K", "H", "TRUCK", "DOC", "WOMAN", "R"))
    seat, walk, side_of, mount, close, over, two, blood, engine, title_card, S = (
        L[k] for k in ("seat", "walk", "side_of", "mount", "close", "over", "two", "blood", "engine", "title_card", "S"))
    sfx = L["sfx"]

    def pos(a, t):
        p = a.track.at(t)
        return (p[0], p[1], p[2])

    # hide the battle: bodies moved into the forest
    t16 = F.cursor
    for a in L["everyone"]:
        a.show(t16, False)
    F.event(t16, "blocks", list=[list(b) for b in world.smashed_wall()])
    # ======================================================================
    # 16  干杯
    # ======================================================================
    F.scene("干杯", daytime=9500)
    HX, HZ = -80.0, -121.2
    H.show(t16).place(t16, (HX, W + BIKE, HZ), 90)
    BOARD = F.prop("board", "board", translation=(0, 0, 0))
    BOARD.show(t16).place(t16, side_of(H, t16, right=0.0, back=0.62, up=0.62 + 0.5), 90)
    TRUCK.show(t16).place(t16, (-68.0, W, -129.5), 180)
    K.show(t16).place(t16, (-78.3, W, -120.2), 120)
    K.hold(t16, "mug")
    DB = F.actor("doctor_b", "doctor_bare", label="医生")
    ring = {}
    circle = [("doctor", -79.6, -119.1, 170), ("woman", -82.0, -121.9, -70), (2, -81.4, -119.0, -140), (3, -82.3, -120.4, -100),
              (4, -78.4, -122.6, 60), (5, -79.8, -123.4, 10), (6, -81.6, -123.3, -40), (7, -77.9, -121.4, 90)]
    bare = {2: "retainer_b_bare", 3: "retainer_c_bare", 4: "retainer_b_bare", 5: "retainer_c_bare", 6: "retainer_b_bare",
            7: "retainer_c_bare"}
    men = {}
    for (k, x, z, yw) in circle:
        if k == "doctor":
            a = DB
        elif k == "woman":
            a = WOMAN
        else:
            a = F.actor(f"b{k}", bare[k], label="男子")
            men[k] = a
        a.show(t16).place(t16, (x, W, z), yw)
        a.pose(t16, "standing")
        a.hold(t16, "mug" if k != "woman" else "wine")
        ring[k] = a
    WOMAN.hold(t16, "baby", hand="off")
    with F.shot(S((-74.6, W + 2.8, -116.0), (-80.2, W + 0.9, -121.0)), name="toast wide") as s:
        s.wait(1.0)
        s.say("", "（下午三、四点。当作替身的尸体已被挪开，士兵们的尸体运进了森林。）", dur=3.4)
        s.say("艾鲁梅斯", "想不到我会遭到这种对待！", pause=0.3)
    with F.shot(close("doctor_b", F.cursor, 2.4, 20), name="speech") as s:
        s.say("医生", "各位——你们表现得太好了，这是一场漂亮的战斗。")
        s.say("医生", "虽然过程很辛苦，也很让人害怕。不仅让我们失去了一名无可取代的伙伴，")
        s.say("医生", "尽管如此，为了让这孩子得到幸福，我们还是愿意挺身而战！")
        s.say("医生", "这瓶酒原本是为了等到那天找到安身之处再享用的，因为它代表了最后的故乡味道，")
        s.say("医生", "然而我认为现在正是品尝它的时候！大家应该没有异议吧？就算有也已经来不及了。", pause=0.1)
    with F.shot(S((-84.4, W + 1.6, -118.4), (-79.8, W + 1.1, -121.2)), name="laugh") as s:
        sfx(s.t0 + T(0.1), "kino.cork", pos=(-82.0, W + 1.3, -121.9), vol=0.9)
        for k in range(4):
            sfx(s.t0 + T(0.9 + 0.7 * k), "kino.pour", pos=(-81.0 + 0.6 * k, W + 1.1, -121.5), vol=0.6, pitch=1.0 + 0.08 * k)
        s.say("男子们", "没有异议！我们早就等不及了！")
    t_toast = F.cursor + T(2.2)
    for k, a in ring.items():
        if k != "woman":
            a.hold(t_toast, "mug", aim=True)
    K.hold(t_toast, "mug", aim=True)
    with F.shot(S((-80.4, W + 3.6, -125.8), (-80.0, W + 1.2, -121.0)), name="cheers") as s:
        s.say("医生", "为祖国的安定、这孩子的未来、我们生存的意义，以及死去的伙伴们——", pause=0.2)
        s.say("男子们", "干杯！", dur=1.4)
        for k, (x_, z_) in enumerate(((-80.2, -120.6), (-79.4, -121.6), (-80.9, -121.9), (-79.9, -122.4), (-80.6, -120.9))):
            sfx(s.cursor - T(0.9 - 0.07 * k), "kino.clink", pos=(x_, W + 1.6, z_), vol=0.8, pitch=0.95 + 0.06 * k)
        s.wait(0.8)
    t_drink = F.cursor
    for k, a in ring.items():
        if k != "woman":
            a.hold(t_drink + T(1.0), "mug")
    K.hold(t_drink + T(1.0), "mug")
    t_poison = t_drink + T(2.4)
    for k, (x_, z_) in enumerate(((-81.4, -119.0), (-79.8, -123.4), (-78.4, -122.6), (-81.6, -123.3))):
        sfx(t_drink + T(0.1 + 0.2 * k), "kino.drink", pos=(x_, W + 1.5, z_), vol=0.7, pitch=0.9 + 0.08 * k)
    with F.shot(S((-76.6, W + 1.7, -118.6), (-80.6, W + 1.2, -121.2)), dur=2.0, name="drink") as s:
        pass
    with F.shot(S((-76.6, W + 1.7, -118.6), (-80.6, W + 1.2, -121.2)), name="don't") as s:
        s.say("男子", "——不要喝啊！", pause=0.1, dur=1.4)
        s.wait(3.4)
    for j, (k, a) in enumerate(sorted(men.items())):
        tj = t_poison + T(0.25 * j)
        p = pos(a, tj)
        yw = math.radians(a.track.at(tj)[3])
        mouth = (p[0] - math.sin(yw) * 0.35, W + 1.45, p[2] + math.cos(yw) * 0.35)
        F.event(tj, "particle", type="blood", pos=list(mouth), delta=(0.05, 0.05, 0.05), speed=0.12, count=30,
                dir=[-math.sin(yw) * 0.12, 0.05, math.cos(yw) * 0.12])
        a.hold(tj, None)
        F.event(tj + 4, "drop", model="mug", pos=[p[0], W + 1.0, p[2]], vel=[0.02, 0.05, 0.02], floor=W + 0.3, life=1200)
        a.pose(tj + T(0.9), "crouching")
        a.pose(tj + T(1.8), "swimming")
        sfx(tj + T(0.1), "kino.choke", pos=mouth, vol=0.9, pitch=0.8 + 0.07 * j)
        sfx(tj + 10, "kino.mug_drop", pos=(p[0], W + 0.3, p[2]), vol=0.6, pitch=1.0 + 0.05 * j)
        sfx(tj + T(1.8), "kino.fall_water", pos=(p[0], W + 0.3, p[2]), vol=0.9, pitch=0.9 + 0.05 * j)
        F.event(tj + T(1.8), "particle", type="splash", pos=[p[0], W + 0.4, p[2]], delta=(0.5, 0.05, 0.5), speed=0.1, count=16)
    F.subs.append((t_poison, t_poison + T(1.8), "男子们", "喔嘎！……嘎！　耶嘎啊！　咕！　喔啊啊啊！"))
    with F.shot(S((-79.0, W + 1.4, -117.4), ("doctor_b", 1.2)), name="why") as s:
        s.wait(0.6)
        s.say("艾鲁梅斯", "天哪～", pause=0.4)
        s.say("医生", "为什、么……", dur=1.8)
    t_doc = F.cursor
    DB.hold(t_doc, None)
    walk(DB, t_doc, [pos(DB, t_doc), (-80.6, W, -120.1)], speed=0.9)
    DB.pose(t_doc + T(1.2), "crouching")
    DB.pose(t_doc + T(2.4), "swimming")
    sfx(t_doc + T(0.2), "kino.choke", follow="doctor_b", vol=0.8, pitch=0.7)
    sfx(t_doc + T(2.4), "kino.fall_water", pos=(-80.6, W + 0.3, -120.1), vol=1.0, pitch=0.85)
    with F.shot(close("doctor_b", t_doc, 2.3, -30), dur=3.6, name="doc falls") as s:
        pass
    with F.shot(close("kino", F.cursor, 2.0, 20), name="kino tea") as s:
        sfx(s.t0 + T(0.5), "kino.drink", follow="kino", vol=0.5, pitch=1.3)
        sfx(s.t0 + T(1.4), "kino.drink", follow="kino", vol=0.5, pitch=1.25)
        s.say("", "（奇诺「滋滋滋」地细细啜饮她的茶，然后大大叹了口气）", pause=0.4, dur=3.0)
    WOMAN.hold(F.cursor, None)
    WOMAN.hold(F.cursor, "baby", hand="main")
    WOMAN.hold(F.cursor, None, hand="off")
    WOMAN.turn(F.cursor, F.cursor + T(0.8), -60)
    with F.shot(close("woman", F.cursor, 2.0, 15), name="success") as s:
        s.wait(0.8)
        s.say("女子", "顺利成功了！")
    with F.shot(S((-77.4, W + 1.0, -118.0), ("hermes", 0.8)), name="hermes why") as s:
        s.say("艾鲁梅斯", "嗯——为什么？")
    wcam = close("woman", F.cursor, 2.2, 30)
    with F.shot(wcam, name="want to know") as s:
        s.say("女子", "想知道吗？摩托车你说什么都想知道吗？")
        s.say("女子", "那我就告诉你吧！不过在那之前，有件事我想先跟奇诺声明一下，可以吗？")
        s.say("艾鲁梅斯", "可以哟——")
    with F.shot(two("woman", "kino", F.cursor, 3.4, side=-1), name="thanks") as s:
        s.say("女子", "真的非常谢谢你，奇诺。托你的福才能击退那些禁卫军，真的很感谢你。")
        s.say("女子", "我以母亲的身份，替这孩子再次向你道谢。")
        s.say("奇诺", "…………不客气。", pause=0.6)
    with F.shot(wcam, name="mother") as s:
        s.say("女子", "其实我，是这孩子的亲生母亲。而她的父亲的的确确是在革命中遭到杀害的国王陛下。")
        s.say("艾鲁梅斯", "这真让人大吃一惊呢。")
        s.say("女子", "很吃惊吧！我本来只是王宫的洗衣妇哟，而且还是所有侍女之中地位最最最卑微的。")
        s.say("女子", "两年前，我偶然遇到国王陛下——他说我很可爱，因此深深爱上了我！我真的好开心！")
    with F.shot(close("woman", F.cursor, 1.8, -20), name="snake pit") as s:
        s.say("艾鲁梅斯", "结果，你就有了那个孩子。")
        s.say("女子", "没错！不过王宫真的是可怕的蛇窝呢。那些后宫嫔妃派出禁卫军对我做出各种威胁。")
        s.say("女子", "但是我说什么都想把她生下来，所以我请亲切的御医写下『我流产了』的假诊断书，然后离开了王宫。")
    with F.shot(wcam, name="revolution") as s:
        s.say("女子", "后来就开始了名为『革命』的杀戮。温柔的国王陛下、那些可恨的后宫嫔妃、那些王子公主，全都被杀了。")
        s.say("女子", "那位御医来到我居住的村子，跟我说：『你女儿被人追杀，你也有性命危险。』")
        s.say("女子", "没错！逼不得已，我只好跟那群人一起逃跑……这样的情况一直周而复始地重复。我真的是受够了！")
        s.say("艾鲁梅斯", "不过也已经结束了啦。那么，你打算接下来怎么做呢？")
    with F.shot(close("woman", F.cursor, 1.9, 25), name="queen") as s:
        s.say("女子", "我已经做好练习了！就是驾驶卡车的方法！我还被夸奖过技术很好呢！")
        s.say("女子", "当然是回我的祖国！")
        s.say("艾鲁梅斯", "什么？", dur=1.2)
        s.say("女子", "现在祖国不是正在吵要不要再立国王这件事吗？没错！我女儿就会变成女王哟！")
    K.hold(F.cursor, None)
    with F.shot(close("kino", F.cursor, 1.9, 25), name="true aim") as s:
        s.say("奇诺", "那就是你真正的目的吗？")
    with F.shot(wcam, name="three years lie") as s:
        s.say("女子", "当然啰！一旦这孩子变成女王陛下，我就能以她母亲的身份过着优雅又幸福的生活。")
        s.say("奇诺", "可是医生说她『寿命只剩三年』……")
        s.say("女子", "那当然不是真的啰！是医生为了鼓动那些随从跟着行动而说的谎哟。")
        s.say("女子", "只要他们全不在了，那我就没必要苦等下去！所以我才要了他们的命，用的是医生带出来的药哦。")
    with F.shot(S((-77.4, W + 1.0, -118.0), ("hermes", 0.8)), name="hermes warn") as s:
        s.say("艾鲁梅斯", "你讲那种话妥当吗？搞不好奇诺会把大姐姐你杀死，并把所有东西带走哟？")
    with F.shot(wcam, name="good person") as s:
        s.say("女子", "哎呀？奇诺才不会做那种事呢！")
        s.say("女子", "因为会做那种事情的人，是不可能豁出性命『为婴儿』战斗的！")
        s.say("女子", "奇诺她虽然敢用非常残酷的方法战斗，但她其实是个好人哟！")
        s.say("艾鲁梅斯", "人家都那么说了，你要怎么办呢，奇诺？")
    with F.shot(close("kino", F.cursor, 1.8, 20), name="no more") as s:
        s.say("奇诺", "这个嘛……我……今天……已经不想再杀任何人了……", dur=4.0)
        s.say("女子", "我就知道！奇诺你的确很温柔呢！")
        s.say("奇诺", "你错了。", pause=0.5)
    # the doctor rises behind her
    t_rise = F.cursor - T(3.0)
    wp = pos(WOMAN, t_rise)
    DB.pose(t_rise, "standing")
    DB.place(t_rise, (wp[0] - 0.9, W, wp[2] - 0.5), -60)
    with F.shot(two("woman", "kino", F.cursor, 3.2, side=1), name="snap") as s:
        s.say("女子", "咦？", pause=0.6, dur=1.0)
        t_snap = s.cursor
        s.wait(1.0)
        s.say("医生", "……拜、托了……", dur=2.2)
    F.event(t_snap, "sound", sound="kino.snap", pos=list(wp), vol=2.0, pitch=0.8)
    WOMAN.pose(t_snap + T(0.6), "swimming")
    sfx(t_snap + T(0.6), "kino.fall_water", pos=(wp[0], W + 0.3, wp[2]), vol=1.0)
    WOMAN.hold(t_snap + T(0.3), None)
    walk(K, t_snap, [pos(K, t_snap), (wp[0] + 0.7, W, wp[2] + 0.3)], speed=5.0)
    K.hold(t_snap + T(0.4), "baby")
    DB.pose(F.cursor - T(0.4), "swimming")
    sfx(F.cursor - T(0.4), "kino.fall_water", pos=(wp[0] - 0.9, W + 0.3, wp[2] - 0.5), vol=0.8, pitch=0.8)
    F.event(t_snap + T(0.6), "particle", type="splash", pos=[wp[0], W + 0.4, wp[2]], delta=(0.5, 0.05, 0.5), speed=0.1, count=20)
    tbaby = F.cursor
    walk(K, tbaby, [pos(K, tbaby), side_of(H, tbaby, right=-0.8, back=0.9)[:1] + (W,) + side_of(H, tbaby, right=-0.8, back=0.9)[2:]],
         speed=2.0)
    BABY = F.prop("baby", "baby", translation=(0, 0, 0))
    K.hold(tbaby + T(2.0), None)
    BABY.show(tbaby + T(2.0)).place(tbaby + T(2.0), side_of(H, tbaby, right=0.0, back=0.75, up=0.62 + 0.62), 0)
    sfx(tbaby + T(2.0), "kino.cloth", follow="hermes", vol=0.6, pitch=1.2)
    with F.shot(S((-77.2, W + 1.8, -120.0), ("hermes", 0.9)), name="rack") as s:
        s.wait(2.4)
        s.say("艾鲁梅斯", "这不是婴儿床耶。")
        s.say("奇诺", "她都没有哭耶，可能觉得躺在艾鲁梅斯身上很舒服吧。")
        s.say("艾鲁梅斯", "这个嘛，我是无所谓啦。")
    DB.pose(F.cursor, "crouching")
    with F.shot(close("doctor_b", F.cursor, 2.6, 35, dy=-0.3), name="wail") as s:
        s.say("医生", "哇啊啊啊啊啊啊！", pause=0.3, dur=2.0)
        s.say("医生", "哇啊啊！哇啊啊啊啊啊啊啊啊！", dur=2.4)
        s.say("", "（一个年过五十岁的男人像个孩子般哭泣）", dur=2.6)

    # ======================================================================
    # 17  暮色
    # ======================================================================
    F.scene("暮色", daytime=12250)
    t17 = F.cursor
    sfx(t17 + T(0.2), "kino.wind", glob=True, vol=0.35)
    sfx(t17 + T(7.4), "kino.wind", glob=True, vol=0.3)
    K.place(t17, (-78.4, W, -118.9), 150)
    with F.shot(Cam.move((-70.0, W + 2.6, -104.0), (-72.0, W + 3.4, -108.0), (-79.6, W + 0.8, -121.0), (-79.6, W + 0.8, -121.0)),
                dur=6.0, name="dusk") as s:
        s.say("", "（白云在淡桔色的天空里飘着。脚下的水面映照着相同的景色，唯一不同的是，水面映照着许多尸体。）", pause=1.0,
              dur=4.6)
    with F.shot(close("doctor_b", F.cursor, 2.4, -30, dy=-0.2), name="kill me") as s:
        s.say("医生", "奇诺……我有一事相求……", pause=0.6)
        s.say("医生", "请你杀了我……请你杀了我……")
    with F.shot(close("kino", F.cursor, 2.0, 25), name="drive") as s:
        s.say("奇诺", "你没听到我刚才说的话吗？", pause=0.8)
        s.wait(0.6)
        s.say("奇诺", "你会开卡车吧？", pause=0.4)
        s.wait(1.2)

    # ======================================================================
    # 18  尾声 —— 奇诺
    # ======================================================================
    F.scene("尾声", daytime=12500)
    t18 = F.cursor
    F.overlay(t18, "black")
    with F.shot(Cam.static((0, 120, 0), (10, -30)), name="black") as s:
        s.say("旁白", "爷爷他临死前曾跟我说：", pause=1.0, dur=2.6)
        s.say("旁白", "『人生就像一场战争。』『千万不要害怕战斗。』", dur=3.6)
    F.overlay(F.cursor, "letterbox")
    tt = F.cursor
    for a in list(F.actors.values()):
        if a.id not in ("kino",):
            a.show(tt, False)
    for p_ in list(F.props.values()):
        p_.show(tt, False)
    TRUCK.show(tt)
    t_tr = tt + T(14.0)
    TRUCK.move(tt, t_tr, [(-62.0, G, 0.4), (-40.0, G, 0.4), (-10.0, G, 0.4)], yaw=-90)
    engine(tt, t_tr, TRUCK, vol=0.6)
    with F.shot(Cam.move((-66.0, G + 2.0, 3.4), (-54.0, G + 2.8, 3.4), "truck", "truck", kind="linear"), dur=6.5, name="truck away") as s:
        s.say("旁白", "可是有关我们出生的国家，还有我母亲的事情——他到最后都没有告诉我。", pause=0.4)
        s.say("旁白", "说那并不重要，知道了也没有用。")
    H.show(F.cursor)
    K.show(F.cursor)
    mount(F.cursor)
    tk = F.cursor
    t_k = tk + T(30.0)
    H.move(tk, t_k, [(-96.0, G + BIKE, -1.3), (-150.0, G + BIKE, -1.3)], yaw=90)
    engine(tk, t_k, H)
    with F.shot(Cam.follow("hermes", (-3.2, 1.4, 1.5), look=("kino", 1.3)), name="kino rides") as s:
        s.say("旁白", "不过，当我问他为什么我会取名叫做『奇诺』，他倒是跟我说了呢。", pause=0.4)
        s.say("旁白", "这个『奇诺』是一位旅行者的名字。")
    with F.shot(Cam.follow("hermes", (0.4, 1.6, -4.4), look=("kino", 1.45)), name="face") as s:
        s.say("旁白", "是爷爷抱着襁褓中的我四处流浪的时候，保护我们俩并勇敢战斗的旅行者的名字。")
        s.say("旁白", "我只知道她是『骑着摩托车，而且非常温柔非常厉害的旅行者』。")
    with F.shot(Cam.follow("hermes", (1.5, 1.2, 4.5), look=(-200.0, 70.0, -1.3)), name="sunset") as s:
        s.say("旁白", "『我们两个现在能像这样平安无事地活着，全都是托奇诺的福哟。』")
        s.say("旁白", "爷爷在临死前是这么跟我说的。")
    with F.shot(Cam.move((-118.0, G + 3.0, 6.0), (-112.0, G + 30.0, 18.0), "hermes", (-170.0, 70.0, -1.0)), dur=9.0, name="crane") as s:
        s.say("旁白", "不知道那位旅行者如今在什么地方做些什么？", pause=0.6)
        s.say("旁白", "还继续旅行吗？还在为某人战斗吗？")
        s.say("旁白", "或者——", dur=2.4)
    for k in range(3):
        sfx(F.cursor - T(9.0) + T(7.4 * k), "kino.wind", glob=True, vol=0.3)
    L["title_card"](8.0, "奇诺之旅", "第七话「战斗者的故事」完")
    L["title_card"](7.0, "原作　时雨泽惠一", "Minecraft 同人改编 · 非商业")
    # the piano comes back under the narration and ends with the credits
    F.event(max(t18 + T(1.0), F.cursor - T(56.0)), "sound", sound="kino.music_ending", vol=0.9, pitch=1.0, **{"global": True})
