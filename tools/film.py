"""A tiny film DSL: actors (mannequins), props (item_display models), a camera,
dialogue, block changes and effects on one tick timeline (20 ticks/s).

The timeline is sampled tick by tick and compiled to
  * a Minecraft data pack (per-tick functions)       -> compile_mc.py
  * a JSON file for the three.js preview renderer     -> export_preview()
"""
from __future__ import annotations

import bisect
import json
import math
import os
from contextlib import contextmanager

TPS = 20
_VOICES = None


def voice_dur(who, text):
    """Length (s) of the recorded Japanese line for a subtitle, if any (tools/voices.py)."""
    global _VOICES
    if _VOICES is None:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice_index.json")
        _VOICES = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    v = _VOICES.get(f"{who}|{text}")
    return v["dur"] if v else None


def T(sec):
    return int(round(sec * TPS))


def lerp(a, b, u):
    return a + (b - a) * u


def ease(u, kind):
    u = max(0.0, min(1.0, u))
    if kind == "linear":
        return u
    if kind == "in":
        return u * u
    if kind == "out":
        return 1 - (1 - u) * (1 - u)
    return u * u * (3 - 2 * u)  # inout / smoothstep


def yaw_of(dx, dz):
    return -math.degrees(math.atan2(dx, dz))


def look_angles(src, dst):
    dx, dy, dz = dst[0] - src[0], dst[1] - src[1], dst[2] - src[2]
    h = math.hypot(dx, dz)
    return yaw_of(dx, dz), -math.degrees(math.atan2(dy, max(h, 1e-6)))


def unwrap(prev, a):
    while a - prev > 180:
        a -= 360
    while a - prev < -180:
        a += 360
    return a


# ----------------------------------------------------------------------------
class Track:
    """Piecewise definition of a pose (x, y, z, yaw, pitch) over ticks.  The
    segment with the greatest start tick <= t wins; after its end it holds."""

    def __init__(self):
        self.segs = []   # (t0, order, t1, fn)
        self.n = 0

    def add(self, t0, t1, fn):
        self.n += 1
        self.segs.append((t0, self.n, t1, fn))
        self.segs.sort(key=lambda s: (s[0], s[1]))

    def at(self, t):
        keys = [(s[0], s[1]) for s in self.segs]
        i = bisect.bisect_right(keys, (t, 10 ** 9)) - 1
        if i < 0:
            return None
        t0, _, t1, fn = self.segs[i]
        return fn(min(t, t1))


class Entity:
    def __init__(self, film, eid):
        self.film = film
        self.id = eid
        self.track = Track()
        self.visible = []        # (t, bool)
        self.last_pos = None

    # ---- placement / motion -------------------------------------------
    def place(self, t, pos, yaw=0.0, pitch=0.0):
        p = (float(pos[0]), float(pos[1]), float(pos[2]), float(yaw), float(pitch))
        self.track.add(t, t, lambda _t, p=p: p)
        self.last_pos = p
        return self

    def move(self, t0, t1, pts, ease_kind="linear", face="path", pitch=0.0, yaw=None):
        """Move along a polyline of points between ticks t0..t1 (arc-length
        parametrised).  face='path' turns toward the direction of travel."""
        pts = [tuple(float(v) for v in p) for p in pts]
        seg_len = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
        total = sum(seg_len) or 1e-9
        fixed_yaw = yaw

        def fn(t):
            u = ease((t - t0) / max(1, t1 - t0), ease_kind)
            d = u * total
            for i, L in enumerate(seg_len):
                if d <= L or i == len(seg_len) - 1:
                    k = 0 if L == 0 else min(1.0, d / L)
                    a, b = pts[i], pts[i + 1]
                    x, y, z = (lerp(a[j], b[j], k) for j in range(3))
                    yw = fixed_yaw if fixed_yaw is not None else yaw_of(b[0] - a[0], b[2] - a[2])
                    return (x, y, z, yw, pitch)
                d -= L
            return (*pts[-1], fixed_yaw or 0.0, pitch)
        self.track.add(t0, t1, fn)
        end = fn(t1)
        self.last_pos = end
        return self

    def turn(self, t0, t1, yaw1, pitch1=None):
        """Rotate in place (from the pose held at t0)."""
        start = self.track.at(t0)
        if start is None:
            raise ValueError(f"{self.id}: turn before placement")
        x, y, z, yaw0, p0 = start
        yaw1 = unwrap(yaw0, yaw1)
        p1 = p0 if pitch1 is None else pitch1

        def fn(t):
            u = ease((t - t0) / max(1, t1 - t0), "inout")
            return (x, y, z, lerp(yaw0, yaw1, u), lerp(p0, p1, u))
        self.track.add(t0, t1, fn)
        return self

    def face_to(self, t0, t1, target):
        st = self.track.at(t0)
        tgt = self.film.point(target, t0)
        yw, pt = look_angles((st[0], st[1] + 1.62, st[2]), tgt)
        return self.turn(t0, t1, yw, max(-40, min(40, pt)))

    def show(self, t, on=True):
        self.visible.append((t, on))
        return self

    def pos_at(self, t):
        return self.film.world_pose(self, t)


class Actor(Entity):
    def __init__(self, film, eid, skin, slim=False, label=None):
        super().__init__(film, eid)
        self.skin = skin
        self.slim = slim
        self.label = label
        self.poses = []          # (t, pose)
        self.rides = []          # (t, prop_id | None)
        self.items = []          # (t, hand, model | None, aim)
        self.fires = []          # (t0, t1)

    def pose(self, t, p):
        self.poses.append((t, p))
        return self

    def ride(self, t, prop):
        self.rides.append((t, prop.id if prop else None))
        return self

    def hold(self, t, model, aim=False, hand="main"):
        self.items.append((t, hand, model, aim))
        return self

    def burn(self, t0, t1):
        self.fires.append((t0, t1))
        return self


class Prop(Entity):
    def __init__(self, film, eid, model, translation=(0, 0, 0), scale=1.0, seat=None, view_range=4.0):
        super().__init__(film, eid)
        self.model = model
        self.translation = translation
        self.scale = scale
        self.view_range = view_range


# ----------------------------------------------------------------------------
def state_at(changes, t, default=None):
    """changes: list of (t, value...) -> the value of the last change at or before t."""
    best = default
    bt = -10 ** 9
    for ch in changes:
        if ch[0] <= t and ch[0] >= bt:
            bt = ch[0]
            best = ch[1] if len(ch) == 2 else ch[1:]
    return best


class Shot:
    def __init__(self, film, t0, dur, cam, name):
        self.film = film
        self.t0 = t0
        self.min_dur = T(dur) if dur else 0
        self.cursor = t0
        self.cam = cam
        self.name = name

    def at(self, sec):
        return self.t0 + T(sec)

    def wait(self, sec):
        self.cursor += T(sec)
        return self.cursor

    def say(self, who, text, pause=0.15, dur=None, extra=0.0):
        """A subtitle line; its length follows the recorded voice when there is one
        (voice + a short breath, but never shorter than a comfortable reading time)."""
        start = self.cursor + T(pause)
        vd = voice_dur(who, text) if who else None
        if vd is not None:
            d = max(dur or 0.0, vd + 0.4, len(text) / 10.0 + 0.5, 1.2)
        else:
            d = dur if dur is not None else max(1.5, len(text) / 8.5 + 0.7)
        end = start + T(d + extra)
        self.film.subs.append((start, end, who, text))
        self.cursor = end
        return start, end

    @property
    def end(self):
        return max(self.cursor + T(0.4), self.t0 + self.min_dur)


class Film:
    def __init__(self, name="film"):
        self.name = name
        self.actors = {}
        self.props = {}
        self.cursor = 0
        self.shots = []          # (t0, t1, cam_spec, name, scene)
        self.subs = []           # (t0, t1, who, text)
        self.events = []         # (t, kind, data)
        self.times = []          # (t, daytime)
        self.overlays = []       # (t, overlay | None)
        self.titles = []         # (t, title, subtitle, fade_in, stay, fade_out)
        self.scenes = []         # (t, name)
        self.labels = {}         # speaker -> colour
        self.engines = []        # (t0, t1, prop id, volume, base pitch) engine running
        self.scene_name = ""

    # ---- cast --------------------------------------------------------------
    def actor(self, eid, skin, slim=False, label=None):
        a = Actor(self, eid, skin, slim, label)
        self.actors[eid] = a
        return a

    def prop(self, eid, model, **kw):
        p = Prop(self, eid, model, **kw)
        self.props[eid] = p
        return p

    def ent(self, eid):
        return self.actors.get(eid) or self.props.get(eid)

    # ---- structure --------------------------------------------------------
    def scene(self, name, daytime=None):
        self.scenes.append((self.cursor, name))
        self.scene_name = name
        if daytime is not None:
            self.times.append((self.cursor, daytime))

    @contextmanager
    def shot(self, cam, dur=None, name=""):
        s = Shot(self, self.cursor, dur, cam, name)
        yield s
        t1 = s.end
        self.shots.append((s.t0, t1, cam, name, self.scene_name))
        self.cursor = t1

    def gap(self, sec, cam):
        with self.shot(cam, dur=sec):
            pass

    def event(self, t, kind, **data):
        self.events.append((t, kind, data))

    def overlay(self, t, name):
        self.overlays.append((t, name))

    def daytime(self, t, value):
        self.times.append((t, value))

    def title(self, t, title, subtitle="", fade_in=10, stay=70, fade_out=20):
        self.titles.append((t, title, subtitle, fade_in, stay, fade_out))

    # ---- evaluation helpers -----------------------------------------------
    def world_pose(self, e, t):
        """World pose of an entity at tick t, resolving riding."""
        if isinstance(e, Actor):
            veh = state_at(e.rides, t)
            if veh:
                v = self.props[veh]
                vp = v.track.at(t)
                if vp is None:
                    return None
                own = e.track.at(t)
                pitch = own[4] if own else 0.0
                return (vp[0], vp[1] - 0.6, vp[2], vp[3], pitch)
        return e.track.at(t)

    def point(self, target, t, head=True):
        """Resolve a look/aim target: a point, an entity id, or (id, dy)."""
        if isinstance(target, str):
            e = self.ent(target)
            p = self.world_pose(e, t)
            dy = 1.55 if (head and isinstance(e, Actor)) else 0.5
            if isinstance(e, Actor):
                pose = state_at(e.poses, t, "standing")
                if pose in ("swimming", "sleeping"):
                    dy = 0.3
                if state_at(e.rides, t):
                    dy = 1.55
            return (p[0], p[1] + dy, p[2])
        if isinstance(target, tuple) and len(target) == 2 and isinstance(target[0], str):
            e = self.ent(target[0])
            p = self.world_pose(e, t)
            return (p[0], p[1] + target[1], p[2])
        return tuple(float(v) for v in target)

    @property
    def length(self):
        return max([s[1] for s in self.shots] + [0])


# ----------------------------------------------------------------------------
# camera specs: callables cam(film, t, shot_t0, shot_t1) -> (x, y, z, yaw, pitch)
class Cam:
    @staticmethod
    def static(pos, look):
        def f(film, t, t0, t1):
            if isinstance(look, tuple) and len(look) == 2 and not isinstance(look[0], str):
                return (*pos, look[0], look[1])
            yw, pt = look_angles(pos, film.point(look, t))
            return (*pos, yw, pt)
        return f

    @staticmethod
    def move(p0, p1, look0, look1=None, kind="inout"):
        look1 = look1 if look1 is not None else look0

        def f(film, t, t0, t1):
            u = ease((t - t0) / max(1, t1 - t0), kind)
            pos = tuple(lerp(p0[i], p1[i], u) for i in range(3))
            a = film.point(look0, t)
            b = film.point(look1, t)
            tgt = tuple(lerp(a[i], b[i], u) for i in range(3))
            yw, pt = look_angles(pos, tgt)
            return (*pos, yw, pt)
        return f

    @staticmethod
    def follow(eid, offset, look=None, look_dy=1.3, fixed_yaw=None, smooth=True):
        """Offset is (right, up, back) in the entity's heading frame (or world yaw fixed_yaw)."""
        def f(film, t, t0, t1):
            e = film.ent(eid)
            p = film.world_pose(e, t)
            yw = fixed_yaw if fixed_yaw is not None else p[3]
            r = math.radians(yw)
            fwd = (-math.sin(r), math.cos(r))
            right = (-fwd[1], fwd[0])   # heading south (+z): right = west (-x)
            ox = right[0] * offset[0] - fwd[0] * offset[2]
            oz = right[1] * offset[0] - fwd[1] * offset[2]
            pos = (p[0] + ox, p[1] + offset[1], p[2] + oz)
            tgt = film.point(look, t) if look is not None else (p[0], p[1] + look_dy, p[2])
            yw2, pt = look_angles(pos, tgt)
            return (*pos, yw2, pt)
        return f

    @staticmethod
    def orbit(center, radius, height, a0, a1, kind="inout", look=None):
        def f(film, t, t0, t1):
            c = film.point(center, t)
            u = ease((t - t0) / max(1, t1 - t0), kind)
            a = math.radians(lerp(a0, a1, u))
            pos = (c[0] + math.sin(a) * radius, c[1] + height, c[2] + math.cos(a) * radius)
            tgt = film.point(look, t) if look is not None else c
            yw, pt = look_angles(pos, tgt)
            return (*pos, yw, pt)
        return f


# ----------------------------------------------------------------------------
def sample(film):
    """Per-tick states for everything.  Returns dict with lists indexed by tick."""
    n = film.length + 1
    cam = []
    shot_i = 0
    shots = sorted(film.shots)
    for t in range(n):
        while shot_i + 1 < len(shots) and shots[shot_i + 1][0] <= t:
            shot_i += 1
        t0, t1, spec, _, _ = shots[shot_i]
        cam.append(spec(film, min(t, t1), t0, t1))
    actors = {}
    for a in film.actors.values():
        rows = []
        speed = 0.0
        wpos = 0.0
        prev = None
        for t in range(n):
            vis = state_at(a.visible, t, False)
            p = film.world_pose(a, t) if vis else None
            if p is None:
                rows.append(None)
                prev = None
                speed = 0.0
                continue
            riding = state_at(a.rides, t)
            if prev is not None and not riding:
                d = math.hypot(p[0] - prev[0], p[2] - prev[2])
                if d > 3:
                    d = 0
                target = min(d * 4.0, 1.0)
            else:
                target = 0.0
            speed += (target - speed) * 0.4
            wpos += speed
            rows.append((p[0], p[1], p[2], p[3], p[4], wpos, speed))
            prev = p
        actors[a.id] = rows
    props = {}
    for pr in film.props.values():
        rows = []
        for t in range(n):
            vis = state_at(pr.visible, t, False)
            p = pr.track.at(t) if vis else None
            rows.append(p)
        props[pr.id] = rows
    return {"n": n, "cam": cam, "actors": actors, "props": props}


def compress(rows, eps=1e-3, jump=2.5, angle_idx=(3,)):
    """Keyframe compression of per-tick rows (None = absent)."""
    out = []
    prev_yaw = {}
    fixed = []
    for t, r in enumerate(rows):
        if r is None:
            fixed.append(None)
            prev_yaw = {}
            continue
        r = list(r)
        for i in angle_idx:
            if i in prev_yaw:
                r[i] = unwrap(prev_yaw[i], r[i])
            prev_yaw[i] = r[i]
        fixed.append(r)
    for t, r in enumerate(fixed):
        if r is None:
            if t > 0 and fixed[t - 1] is not None:
                out.append([t, None])
            continue
        p = fixed[t - 1] if t > 0 else None
        nx = fixed[t + 1] if t + 1 < len(fixed) else None
        keep = p is None or nx is None
        if not keep:
            for i in range(len(r)):
                if abs((p[i] + nx[i]) / 2 - r[i]) > eps:
                    keep = True
                    break
            if math.dist(p[:3], r[:3]) > jump or math.dist(nx[:3], r[:3]) > jump:
                keep = True
        if keep:
            out.append([t] + [round(v, 4) for v in r])
    return out
