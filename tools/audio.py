"""Sound track of the preview video / web player -> build/preview/audio.wav
(44.1 kHz stereo).  It plays back exactly what the data pack plays in game:

  * every sound event of the film, resolved through Minecraft's sounds.json
    (vanilla files are downloaded from a mirror of the game assets into
    build/cache/sounds/, custom ones come from the resource pack), with the
    game's volume / pitch rules and linear distance attenuation relative to the
    camera, panned by direction;
  * the Japanese voice lines (tools/voices.py) at each subtitle;
  * the piano music of the resource pack.
Ambience and engines are ducked a little under dialogue, then a peak limiter.
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import math
import os
import random
import subprocess
import sys

import numpy as np
import soundfile as sf
from scipy.ndimage import maximum_filter1d
from scipy.signal import lfilter

sys.path.insert(0, os.path.dirname(__file__))
import film as filmlib  # noqa: E402
import script  # noqa: E402
import sfx  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 44100
CACHE = os.path.join(ROOT, "build", "cache", "sounds")
MC_VER = "1.21.10"
MIRROR = f"https://raw.githubusercontent.com/InventivetalentDev/minecraft-assets/{MC_VER}/assets/minecraft/"
RP = os.path.join(ROOT, "resourcepack", "assets", "kino")
VOICE_WAV = os.path.join(ROOT, "build", "voices")

BUS = {"voice": 1.0, "music": 0.42, "sfx": 0.62, "amb": 0.62}


def fetch(url, path):
    if os.path.exists(path):
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for _ in range(4):
        r = subprocess.run(["curl", "-sSfL", "-o", path + ".part", url])
        if r.returncode == 0:
            os.replace(path + ".part", path)
            return path
    raise RuntimeError("download failed: " + url)


class Sounds:
    """Minecraft sound events -> decoded clips (mono float32 @ 44.1 kHz)."""

    def __init__(self):
        self.vanilla = json.load(open(fetch(MIRROR + "sounds.json", os.path.join(CACHE, f"sounds_{MC_VER}.json"))))
        self.custom = json.load(open(os.path.join(RP, "sounds.json")))
        self.clips = {}

    def entries(self, event, depth=0):
        """[(file key, volume, pitch, weight, attenuation)] for a sound event id."""
        ns, name = event.split(":", 1)
        table = self.vanilla if ns == "minecraft" else self.custom
        out = []
        for s in table[name]["sounds"]:
            if isinstance(s, str):
                s = {"name": s}
            if s.get("type") == "event" and depth < 4:
                for (f, v, p, w, a) in self.entries(s["name"] if ":" in s["name"] else "minecraft:" + s["name"], depth + 1):
                    out.append((f, v * s.get("volume", 1.0), p * s.get("pitch", 1.0), w * s.get("weight", 1), a))
                continue
            nm = s["name"] if ":" in s["name"] else "minecraft:" + s["name"]
            out.append((nm, s.get("volume", 1.0), s.get("pitch", 1.0), s.get("weight", 1), s.get("attenuation_distance", 16)))
        return out

    def path(self, key):
        ns, name = key.split(":", 1)
        if ns == "minecraft":
            return fetch(MIRROR + "sounds/" + name + ".ogg", os.path.join(CACHE, name + ".ogg"))
        return os.path.join(RP, "sounds", name + ".ogg")

    def prefetch(self, events):
        keys = set()
        for ev in events:
            for e in self.entries(ev):
                keys.add(e[0])
        with cf.ThreadPoolExecutor(12) as ex:
            list(ex.map(self.path, sorted(keys)))
        return len(keys)

    def clip(self, key):
        if key not in self.clips:
            a, sr = sf.read(self.path(key), dtype="float32", always_2d=True)
            a = a.mean(axis=1)
            if sr != SR:
                a = resample(a, sr / SR)
            self.clips[key] = a
        return self.clips[key]

    def pick(self, event, seed):
        es = self.entries(event)
        tot = sum(e[3] for e in es)
        r = random.Random(repr(seed)).random() * tot
        for e in es:
            r -= e[3]
            if r <= 0:
                return e
        return es[-1]


def resample(a, rate):
    """Play `a` `rate` times faster (Minecraft pitch = playback speed)."""
    if abs(rate - 1) < 1e-4:
        return a
    n = int(len(a) / rate)
    return np.interp(np.arange(n) * rate, np.arange(len(a)), a).astype(np.float32)


class Mixer:
    def __init__(self, F, S, total):
        self.F, self.S = F, S
        self.total = total
        self.bus = {k: np.zeros((total, 2), np.float32) for k in BUS}
        self.ncam = len(S["cam"])

    def cam(self, t):
        return self.S["cam"][max(0, min(self.ncam - 1, t))]

    def source_pos(self, d, t):
        if "pos" in d:
            return tuple(d["pos"])
        f = d["follow"]
        e = self.F.ent(f)
        p = self.F.world_pose(e, max(0, min(self.F.length, t)))
        if p is None:
            return None
        return (p[0], p[1] + (1.0 if f in self.F.actors else 0.3), p[2])

    def add(self, busname, t, clip, vol, att, d=None, global_=False):
        """Place a clip at tick t; positional gain/pan evaluated every tick of its length."""
        s0 = int(t / 20 * SR)
        if s0 >= self.total:
            return
        n = min(len(clip), self.total - s0)
        clip = clip[:n]
        if global_:
            g = np.full(n, vol, np.float32)
            self.bus[busname][s0:s0 + n, 0] += clip * g * 0.85
            self.bus[busname][s0:s0 + n, 1] += clip * g * 0.85
            return
        rng_ = max(vol, 1.0) * att
        base = min(1.0, vol)
        ticks = int(math.ceil(n / SR * 20)) + 2
        gl, gr = np.zeros(ticks), np.zeros(ticks)
        for k in range(ticks):
            src = self.source_pos(d, t + k if "follow" in d else t)
            if src is None:
                continue
            c = self.cam(t + k)
            dist = math.dist(src, c[:3])
            g = base * max(0.0, 1.0 - dist / rng_)
            if g <= 0:
                continue
            yaw = math.radians(c[3])
            rx, rz = -math.cos(yaw), -math.sin(yaw)
            h = math.hypot(src[0] - c[0], src[2] - c[2])
            pan = ((src[0] - c[0]) * rx + (src[2] - c[2]) * rz) / h if h > 0.3 else 0.0
            pan *= min(1.0, h / 2.0) * 0.75
            a = (pan + 1) * math.pi / 4
            gl[k], gr[k] = g * math.cos(a) * 1.41, g * math.sin(a) * 1.41
        if gl.max() <= 0.003 and gr.max() <= 0.003:
            return
        xs = np.arange(n) / SR * 20
        L = np.interp(xs, np.arange(ticks), gl).astype(np.float32)
        R = np.interp(xs, np.arange(ticks), gr).astype(np.float32)
        self.bus[busname][s0:s0 + n, 0] += clip * L
        self.bus[busname][s0:s0 + n, 1] += clip * R


def limiter(x, ceiling=0.93):
    env = maximum_filter1d(np.abs(x).max(axis=1), size=int(0.006 * SR))
    a = math.exp(-1 / (0.18 * SR))
    # peak hold with exponential release: y[n] = max(env[n], a*y[n-1]) ~ approximated by a smoothed max
    rel = lfilter([1 - a], [1, -a], env)
    env = np.maximum(env, rel)
    gain = np.minimum(1.0, ceiling / np.maximum(env, 1e-9))
    gain = maximum_filter1d(gain[::-1], size=int(0.004 * SR))[::-1] if False else gain
    return x * gain[:, None]


def main():
    F = script.build()
    S = filmlib.sample(F)
    auto = sfx.auto_events(F, S)
    events = sorted([e for e in F.events if e[1] == "sound"] + auto, key=lambda e: e[0])
    voices = sfx.voice_events(F)
    n = F.length
    total = int(n / 20 * SR) + 4 * SR
    snd = Sounds()
    used = {l[0] for e in events for l in sfx.SFX[e[2]["sound"]]}
    print(f"audio: {len(events)} sound events ({len(auto)} automatic), {len(voices)} voice lines, "
          f"{snd.prefetch(used)} sound files")
    mix = Mixer(F, S, total)
    for k, (t, _, d) in enumerate(events):
        key = d["sound"]
        for layer in sfx.SFX[key]:
            ev, lv, lp = layer[:3]
            delay = layer[3] if len(layer) > 3 else 0
            f, ev_vol, ev_pitch, _w, att = snd.pick(ev, (t, k, ev))
            vol = d.get("vol", 1.0) * lv * ev_vol
            pitch = max(0.5, min(2.0, d.get("pitch", 1.0) * lp * ev_pitch))
            clip = resample(snd.clip(f), pitch)
            bus = "music" if key.startswith("kino.music") else ("amb" if sfx.is_ambient(key) else "sfx")
            mix.add(bus, t + delay, clip, vol, att, d, global_=d.get("global", False))
    for (t, vid, _dur, _who) in voices:
        a, sr = sf.read(os.path.join(VOICE_WAV, vid + ".wav"), dtype="float32")
        mix.add("voice", t, resample(a, sr / SR), 1.0, 16, global_=True)
    # duck ambience / engines under dialogue
    act = np.zeros(total, np.float32)
    for (t, _vid, dur, _who) in voices:
        s = int(t / 20 * SR)
        act[s:s + int(dur * SR)] = 1.0
    a = math.exp(-1 / (0.25 * SR))
    duck = lfilter([1 - a], [1, -a], act).astype(np.float32)
    out = (mix.bus["voice"] * BUS["voice"] + mix.bus["music"][:] * BUS["music"] * (1 - 0.35 * duck[:, None])
           + mix.bus["sfx"] * BUS["sfx"] + mix.bus["amb"] * BUS["amb"] * (1 - 0.45 * duck[:, None]))
    out = limiter(out)
    path = os.path.join(ROOT, "build", "preview", "audio.wav")
    sf.write(path, out, SR, subtype="PCM_16")
    rms = float(np.sqrt((out ** 2).mean()))
    print(f"audio: {total / SR:.1f}s stereo, rms {20 * math.log10(rms + 1e-9):.1f} dBFS, peak {np.abs(out).max():.2f} -> {path}")


if __name__ == "__main__":
    main()
