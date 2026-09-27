"""Synthesised sound track for the preview video: every 'sound' event of the
film (attenuated by distance to the camera, like in-game), soft wind, and a
small piano motif over the title cards.  -> build/preview/audio.wav"""
from __future__ import annotations

import math
import os
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import film as filmlib  # noqa: E402
import script  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 44100
rng = np.random.default_rng(7)


def env(n, a=0.002, tau=0.1):
    t = np.arange(n) / SR
    e = np.exp(-t / tau)
    k = int(a * SR)
    if k > 0:
        e[:k] *= np.linspace(0, 1, k)
    return e


def lowpass(x, cut):
    a = math.exp(-2 * math.pi * cut / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def lp_fast(x, cut):
    # one-pole low-pass via cumulative filter in blocks (vectorised enough for our sizes)
    from scipy.signal import lfilter  # type: ignore
    a = math.exp(-2 * math.pi * cut / SR)
    return lfilter([1 - a], [1, -a], x)


try:
    import scipy  # noqa: F401
    LP = lp_fast
except Exception:  # pragma: no cover
    LP = lowpass


def noise(sec):
    return rng.standard_normal(int(sec * SR))


def sine(freq, sec, phase=0.0):
    t = np.arange(int(sec * SR)) / SR
    return np.sin(2 * np.pi * freq * t + phase)


def gun(sec=0.5, cut=3000, tau=0.07, thump=90, tw=0.6):
    n = noise(sec)
    x = LP(n, cut) * env(len(n), 0.001, tau)
    x += tw * sine(thump, sec) * env(len(n), 0.001, tau * 1.5)
    return x


def boom(sec=2.8, cut=500, tau=0.7):
    n = noise(sec)
    x = LP(LP(n, cut), cut) * env(len(n), 0.004, tau) * 3.0
    x += 0.9 * sine(45, sec) * env(len(n), 0.002, tau * 0.8)
    return x


def engine(sec=1.3, f0=46):
    t = np.arange(int(sec * SR)) / SR
    saw = 2 * ((t * f0) % 1.0) - 1
    am = 0.55 + 0.45 * np.sin(2 * np.pi * 11.5 * t) ** 8
    x = LP(saw * am, 700) * 0.6 + LP(noise(sec), 400) * 0.08
    fade = np.minimum(1, np.minimum(t / 0.15, (sec - t) / 0.15))
    return x * fade


def cry(sec=0.9):
    t = np.arange(int(sec * SR)) / SR
    f = 420 + 120 * np.sin(np.pi * t / sec) - 60 * t
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sign(np.sin(ph)) * 0.3 + np.sin(ph * 2) * 0.3 + np.sin(ph * 3) * 0.2
    x = LP(x, 2200) * np.sin(np.pi * t / sec) ** 0.6
    return x * 0.8


def splash(sec=0.45):
    n = noise(sec)
    return (LP(n, 5000) - LP(n, 600)) * env(len(n), 0.01, 0.12)


def thud(sec=0.25, f=110):
    n = noise(sec)
    return (sine(f, sec) * 0.8 + LP(n, 1200) * 0.5) * env(len(n), 0.001, 0.05)


def squeal(sec=0.9):
    t = np.arange(int(sec * SR)) / SR
    return np.sin(2 * np.pi * (1700 + 40 * np.sin(2 * np.pi * 9 * t)) * t) * 0.25 * np.minimum(1, (sec - t) / 0.3)


SOUNDS = {
    "kino.gun_rifle": lambda: gun(0.6, 2600, 0.08, 80),
    "kino.gun_pistol": lambda: gun(0.45, 3500, 0.05, 120, 0.4),
    "kino.gun_suppressed": lambda: gun(0.2, 900, 0.03, 70, 0.8) * 0.8,
    "kino.engine": engine,
    "kino.kickstart": lambda: np.concatenate([thud(0.15, 200), engine(0.9, 52)]),
    "kino.brake": squeal,
    "kino.stone": lambda: sum(np.pad(thud(0.2, 160 + 60 * k), (int(k * 0.07 * SR), int(0.6 * SR)))[:int(0.6 * SR)] for k in range(4)),
    "kino.kick": lambda: thud(0.22, 140),
    "kino.baby_cry": cry,
    "kino.cannon": lambda: boom(2.2, 700, 0.5),
    "kino.explosion": lambda: boom(3.2, 450, 0.9),
    "kino.snap": lambda: gun(0.12, 6000, 0.015, 300, 0.2) * 0.8,
    "kino.punch": lambda: thud(0.2, 95),
    "kino.hit": lambda: thud(0.25, 80) + splash(0.25)[: int(0.25 * SR)] * 0.3,
    "kino.splash": splash,
}


def piano(freq, sec=2.2):
    t = np.arange(int(sec * SR)) / SR
    x = sum(np.sin(2 * np.pi * freq * h * t) / (h ** 1.6) for h in (1, 2, 3, 4))
    return x * np.exp(-t / 0.7) * np.minimum(1, t / 0.005)


NOTE = {n: 440 * 2 ** ((i - 9) / 12) for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}


def motif(sec):
    """A slow, sparse A-minor-pentatonic phrase (C418-ish mood)."""
    seq = ["A3", "E4", "C5", "B4", "E4", "A4", "G4", "E4", "D4", "E4", "A3", "C4", "E4", "G4", "A4", "E5"]
    out = np.zeros(int((sec + 3) * SR))
    beat = 0.55
    k = 0
    t = 0.0
    while t < sec:
        name = seq[k % len(seq)]
        f = NOTE[name[:-1]] * 2 ** (int(name[-1]) - 4)
        s = int(t * SR)
        p = piano(f) * (0.22 if k % 4 else 0.3)
        out[s:s + len(p)] += p[: len(out) - s]
        if k % 4 == 0:
            p2 = piano(f / 2, 3.0) * 0.15
            out[s:s + len(p2)] += p2[: len(out) - s]
        t += beat * (2 if k % 8 == 7 else 1)
        k += 1
    return out[: int(sec * SR)]


def main():
    F = script.build()
    S = filmlib.sample(F)
    n = F.length
    total = int(n / 20 * SR) + SR
    mix = np.zeros(total)
    cache = {}
    for (t, kind, d) in F.events:
        if kind != "sound" or t >= n:
            continue
        key = d["sound"]
        if key not in cache:
            cache[key] = [SOUNDS[key]() for _ in range(3)]
        clip = cache[key][t % 3]
        if "follow" in d:
            e = F.props[d["follow"]]
            p = e.track.at(t)
            if p is None:
                continue
            pos = p[:3]
        else:
            pos = d["pos"]
        cam = S["cam"][t]
        dist = math.dist(pos, cam[:3])
        rng_ = 16 * max(1.0, d.get("vol", 1.0))
        gain = max(0.0, 1 - dist / rng_)
        if key == "kino.engine":
            gain *= 0.5
        gain *= min(1.0, d.get("vol", 1.0)) * (d.get("pitch", 1.0) ** 0)
        if gain <= 0.01:
            continue
        s = int(t / 20 * SR)
        e_ = min(total, s + len(clip))
        mix[s:e_] += clip[: e_ - s] * gain * 0.5
    # wind bed
    wind = LP(LP(rng.standard_normal(total), 300), 300)
    wind = wind / (np.abs(wind).max() + 1e-9) * 0.05
    mix += wind
    # music over title cards and the epilogue
    cards = [s for s in F.shots if s[3] == "card"]
    for (t0, t1, *_rest) in cards[:1]:
        m = motif((t1 - t0) / 20 + 6)
        s = int(t0 / 20 * SR)
        mix[s:s + len(m)] += m[: total - s]
    ep = [t for (t, name) in F.scenes if name == "尾声"]
    if ep:
        s = int(ep[0] / 20 * SR)
        m = motif((n - ep[0]) / 20)
        fade = np.minimum(1, np.arange(len(m)) / (3 * SR))
        mix[s:s + len(m)] += (m * fade)[: total - s]
    peak = np.abs(mix).max()
    mix = np.tanh(mix / max(peak, 1e-9) * 1.6) * 0.85
    out = os.path.join(ROOT, "build", "preview", "audio.wav")
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    print(f"audio: {total / SR:.1f}s -> {out}")


if __name__ == "__main__":
    main()
