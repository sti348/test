"""Custom sounds of the resource pack (Minecraft has no engines, songbirds or
radios), synthesised here and written as Ogg Vorbis:

  sounds/sfx/engine_bike.ogg    2.0 s seamless loop, two-cylinder "putt" (Hermes)
  sounds/sfx/engine_truck.ogg   2.0 s seamless loop, deeper four-cylinder rumble
  sounds/sfx/engine_start.ogg   kick-start, catch, a blip of throttle
  sounds/sfx/birds1..5.ogg      short songbird phrases
  sounds/sfx/wind.ogg           soft leaf rustle
  sounds/sfx/radio.ogg          squelch + static burst
  sounds/music/theme.ogg        opening piano theme
  sounds/music/ending.ogg       epilogue piano

  python3 tools/sfx_synth.py
"""
from __future__ import annotations

import os
import subprocess

import numpy as np
from scipy.signal import butter, fftconvolve, lfilter, sosfilt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "resourcepack", "assets", "kino", "sounds")
SR = 44100


def bp(x, lo, hi, order=2):
    sos = butter(order, [lo / (SR / 2), hi / (SR / 2)], btype="band", output="sos")
    return sosfilt(sos, x)


def lp(x, f, order=2):
    return sosfilt(butter(order, f / (SR / 2), output="sos"), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f / (SR / 2), btype="high", output="sos"), x)


def t_(n):
    return np.arange(n) / SR


def fade(x, a=0.005, b=0.005):
    x = x.copy()
    na, nb = int(a * SR), int(b * SR)
    sh = (-1, 1) if x.ndim == 2 else (-1,)
    if na:
        x[:na] *= np.linspace(0, 1, na).reshape(sh)
    if nb:
        x[-nb:] *= np.linspace(1, 0, nb).reshape(sh)
    return x


def norm(x, peak=0.8):
    return x / (np.abs(x).max() + 1e-9) * peak


def write(name, x, q=4):
    path = os.path.join(OUT, name + ".ogg")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    x = np.clip(x, -1, 1)
    ch = 1 if x.ndim == 1 else x.shape[1]
    raw = (x * 32767).astype("<i2").tobytes()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", str(ch), "-i", "-",
                    "-c:a", "libvorbis", "-q:a", str(q), path], input=raw, check=True)
    print(f"  {name}.ogg  {len(x) / SR:.2f}s")


# ----------------------------------------------------------------------------
def engine_loop(rng, dur, fire_hz, res, decay, noise_band, pattern, rumble=0.0, tick=0.0, noise=0.25, cut=1800):
    """Exhaust pulses (damped resonances + a short noise burst) at the firing rate.
    Pulses are laid out circularly (period = dur) and the noise layers are
    crossfaded over the wrap point, so the file loops seamlessly."""
    n = int(dur * SR)
    m = int(0.08 * SR)
    assert abs(fire_hz * dur - round(fire_hz * dur)) < 1e-6
    L = n + 2 * m
    pl = int(0.12 * SR)
    tt = t_(pl)
    circ = np.zeros(n + pl)
    for k in range(int(round(fire_hz * dur))):
        amp = pattern[k % len(pattern)] * (1 + 0.1 * rng.standard_normal())
        s = int((k / fire_hz + 0.0015 * rng.standard_normal()) * SR) % n
        pulse = np.zeros(pl)
        for (f, a, tau) in res:
            f2 = f * (1 + 0.03 * rng.standard_normal())
            pulse += a * np.exp(-tt / tau) * np.sin(2 * np.pi * f2 * tt + rng.uniform(0, 0.4))
        nb = bp(rng.standard_normal(pl), *noise_band) * np.exp(-tt / decay)
        pulse += noise * nb / (np.abs(nb).max() + 1e-9)
        pulse *= np.minimum(1, tt / 0.003)
        circ[s:s + pl] += amp * pulse
    circ[:pl] += circ[n:n + pl]
    circ = circ[:n]
    pulses = np.tile(circ, 3)[n - m: n - m + L]           # pre-roll m, then n + m
    pulses /= np.abs(pulses).max() + 1e-9
    tl = (np.arange(L) - m) / SR
    mech = hp(rng.standard_normal(L), 2500) * (0.5 + 0.5 * np.cos(2 * np.pi * fire_hz * 2 * tl) ** 8)
    hiss = bp(rng.standard_normal(L), 500, 1600)
    y = pulses + tick * mech / np.abs(mech).max() + 0.006 * hiss / np.abs(hiss).max()
    if rumble:
        r = lp(rng.standard_normal(L), 180)
        y += rumble * r / np.abs(r).max()
    y = lp(y, cut, order=4)[m:]                             # soft, no fizz; drop filter start-up
    w = np.linspace(0, 1, m)
    loop = y[:n].copy()
    loop[:m] = y[:m] * w + y[n:n + m] * (1 - w)
    loop = np.tanh(1.2 * loop / (np.abs(loop).max() + 1e-9)) / np.tanh(1.2)
    return fade(norm(loop, 0.7), 0.003, 0.003)


def engine_bike(rng):
    return engine_loop(rng, 2.0, 22.0, [(92, 1.0, 0.016), (205, 0.45, 0.009), (430, 0.1, 0.005)], 0.007, (200, 900),
                       [1.0, 0.82], cut=1800)


def engine_truck(rng):
    return engine_loop(rng, 2.0, 30.0, [(68, 1.0, 0.022), (150, 0.5, 0.012), (320, 0.12, 0.006)], 0.01, (150, 700),
                       [1.0, 0.9, 0.95, 0.85], rumble=0.1, cut=1400)


def engine_start(rng):
    """Kick lever clunk, a few uneven catches, a blip of throttle, settle to idle."""
    dur = 2.6
    n = int(dur * SR)
    y = np.zeros(n + SR)
    # kick lever: a dull mechanical clunk
    k = int(0.12 * SR)
    tt = t_(k)
    clunk = (np.sin(2 * np.pi * 140 * tt) * np.exp(-tt / 0.02) + 0.6 * bp(rng.standard_normal(k), 800, 4000) * np.exp(-tt / 0.01))
    y[:k] += 0.7 * clunk
    res = [(92, 1.0, 0.016), (205, 0.55, 0.009), (430, 0.18, 0.005)]
    pl = int(0.12 * SR)
    tp = t_(pl)
    times = [0.30, 0.52, 0.66, 0.76]
    t = 0.84
    while t < dur - 0.05:
        u = (t - 0.84) / (dur - 0.84)
        rate = 22 + 26 * np.exp(-((u - 0.25) / 0.12) ** 2)   # throttle blip
        times.append(t)
        t += 1 / rate
    for j, ts in enumerate(times):
        pulse = sum(a * np.exp(-tp / tau) * np.sin(2 * np.pi * f * tp) for (f, a, tau) in res)
        nb = bp(rng.standard_normal(pl), 200, 900) * np.exp(-tp / 0.007)
        pulse = pulse + 0.25 * nb / np.abs(nb).max()
        amp = (1.25 if j < 4 else 1.0) * (1 + 0.1 * rng.standard_normal())
        s = int(ts * SR)
        y[s:s + pl] += amp * pulse
    y = y[:n]
    y = lp(y, 2000, order=4)
    y = np.tanh(1.2 * y / np.abs(y).max()) / np.tanh(1.2)
    return fade(norm(y, 0.75), 0.001, 0.25)


# ----------------------------------------------------------------------------
def chirp(f0, f1, dur, shape="lin", harm=0.15, vib=0.0):
    n = int(dur * SR)
    tt = t_(n)
    u = tt / dur
    if shape == "lin":
        f = f0 + (f1 - f0) * u
    elif shape == "exp":
        f = f0 * (f1 / f0) ** u
    else:  # arch
        f = f0 + (f1 - f0) * np.sin(np.pi * u)
    if vib:
        f = f * (1 + 0.04 * np.sin(2 * np.pi * vib * tt))
    ph = 2 * np.pi * np.cumsum(f) / SR
    env = np.sin(np.pi * u) ** 1.5
    return (np.sin(ph) + harm * np.sin(2 * ph)) * env


def place(buf, x, t):
    s = int(t * SR)
    e = min(len(buf), s + len(x))
    buf[s:e] += x[:e - s]


def forest_reverb(x, rng, rt=0.9, wet=0.25):
    n = int(rt * SR)
    ir = rng.standard_normal(n) * np.exp(-t_(n) / (rt / 6.9))
    ir = lp(ir, 5000)
    ir[0] = 0
    w = fftconvolve(x, ir)
    out = np.zeros(len(w))
    out[:len(x)] += x
    out += wet * w / (np.abs(w).max() + 1e-9) * np.abs(x).max()
    return out


def birds(rng, kind):
    buf = np.zeros(int(4.5 * SR))
    if kind == 1:      # descending "tsee" whistles
        t = 0.1
        for k in range(4):
            place(buf, 0.6 * chirp(7200 - 200 * k, 5200 - 150 * k, 0.16, "exp"), t)
            t += 0.24
        t += 0.5
        for k in range(3):
            place(buf, 0.5 * chirp(6800, 5000, 0.14, "exp"), t)
            t += 0.22
    elif kind == 2:    # a fast trill
        t = 0.15
        for k in range(16):
            place(buf, 0.45 * chirp(4200, 5600, 0.035, "arch"), t)
            t += 0.055
        place(buf, 0.6 * chirp(5200, 3600, 0.22, "exp"), t + 0.05)
    elif kind == 3:    # two-note call, repeated
        t = 0.1
        for k in range(5):
            place(buf, 0.55 * chirp(3900, 4300, 0.11, "arch"), t)
            place(buf, 0.5 * chirp(3100, 3000, 0.13, "lin"), t + 0.16)
            t += 0.55
    elif kind == 4:    # warble
        t = 0.1
        notes = [(3400, 4800), (4800, 3900), (4100, 5300), (5300, 4200), (3600, 4400), (4700, 3500), (3900, 5100)]
        for (a, b) in notes:
            d = 0.08 + 0.05 * rng.random()
            place(buf, 0.45 * chirp(a, b, d, "lin", vib=40), t)
            t += d + 0.03
        t += 0.6
        for (a, b) in notes[:4]:
            d = 0.08 + 0.05 * rng.random()
            place(buf, 0.4 * chirp(a * 1.05, b * 1.05, d, "lin", vib=40), t)
            t += d + 0.03
    else:              # distant cuckoo-ish dove: two soft low notes
        t = 0.2
        for k in range(3):
            place(buf, 0.5 * chirp(760, 720, 0.28, "lin", harm=0.05), t)
            place(buf, 0.45 * chirp(640, 600, 0.36, "lin", harm=0.05), t + 0.34)
            t += 1.2
    y = forest_reverb(buf, rng, 0.8, 0.3)
    nz = np.nonzero(np.abs(y) > 1e-4)[0]
    y = y[: nz[-1] + 1] if len(nz) else y
    return fade(norm(y, 0.6), 0.005, 0.2)


def wind(rng):
    dur = 8.0
    n = int(dur * SR)
    x = bp(rng.standard_normal(n), 350, 2600) + 0.5 * bp(rng.standard_normal(n), 2500, 6000)
    tt = t_(n)
    gust = 0.55 + 0.25 * np.sin(2 * np.pi * tt / dur) + 0.2 * np.sin(2 * np.pi * 3 * tt / dur + 1.3)
    x = x * gust
    m = int(0.5 * SR)
    w = np.linspace(0, 1, m)
    x[:m] = x[:m] * w + x[-m:] * (1 - w)
    x = x[:-m]
    return norm(x, 0.35)


def radio(rng):
    dur = 0.9
    n = int(dur * SR)
    tt = t_(n)
    st = bp(rng.standard_normal(n), 700, 3400)
    crack = np.zeros(n)
    for _ in range(40):
        s = rng.integers(0, n - 200)
        crack[s:s + 60] += rng.standard_normal(60) * rng.uniform(0.5, 1.5)
    x = st / np.abs(st).max() * 0.35 + bp(crack, 600, 5000) * 0.5
    env = np.minimum(1, tt / 0.01) * np.minimum(1, (dur - tt) / 0.04)
    beep = np.sin(2 * np.pi * 1250 * tt) * (tt < 0.08) * 0.35
    return fade(norm(x * env + beep, 0.6), 0.002, 0.01)


# ----------------------------------------------------------------------------
NOTE_I = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8,
          "A": 9, "A#": 10, "Bb": 10, "B": 11}


def freq(name):
    return 440.0 * 2 ** ((NOTE_I[name[:-1]] + 12 * (int(name[-1]) + 1) - 69) / 12)


def piano(f, dur, vel=0.7):
    """Additive piano-ish tone: slightly inharmonic partials, faster decay for
    higher partials, soft hammer, damper release."""
    ring = min(6.0, dur + 1.2)
    n = int(ring * SR)
    tt = t_(n)
    B = 0.00035
    tau0 = 2.6 * (261.6 / f) ** 0.45
    x = np.zeros(n)
    for k in range(1, 11):
        fk = k * f * np.sqrt(1 + B * k * k)
        if fk > 9000:
            break
        a = (1 / k ** 1.25) * (0.6 + 0.4 * vel) ** (k * 0.3)
        tau = tau0 / (1 + 0.55 * (k - 1))
        # two slightly detuned strings -> gentle beating
        x += a * np.exp(-tt / tau) * (np.sin(2 * np.pi * fk * tt) + 0.6 * np.sin(2 * np.pi * fk * 1.0007 * tt + 0.3))
    x *= np.minimum(1, tt / 0.004)
    rel = np.ones(n)
    r0 = int(dur * SR)
    if r0 < n:
        rel[r0:] = np.exp(-(tt[r0:] - dur) / 0.25)
    hammer = lp(np.random.default_rng(int(f)).standard_normal(n), 2500) * np.exp(-tt / 0.006) * 0.08
    return (x * rel + hammer) * vel


def reverb_st(x, rng, rt=2.4, wet=0.32):
    n = int(rt * SR)
    out = np.zeros((len(x) + n, 2))
    for ch in range(2):
        ir = rng.standard_normal(n) * np.exp(-t_(n) / (rt / 6.9))
        ir = lfilter([0.25], [1, -0.75], ir)          # darker tail
        ir[: int(0.012 * SR)] = 0
        w = fftconvolve(x, ir)[: len(x) + n]
        w = w / (np.abs(w).max() + 1e-9) * np.abs(x).max()
        out[: len(w), ch] += wet * w
        out[: len(x), ch] += x
    return out


def score(events, bpm, total_beats, rng, vel_scale=1.0):
    beat = 60.0 / bpm
    length = total_beats * beat + 4.0
    buf = np.zeros(int(length * SR))
    for (b, d, names, vel) in events:
        for nm in names.split():
            tone = piano(freq(nm), d * beat, vel * vel_scale)
            place(buf, tone, b * beat)
    y = reverb_st(buf, rng)
    return y


def theme_events(var=0):
    """A small A-minor theme in 3/4 (left hand broken chords, right hand melody)."""
    ev = []
    prog = [("A2", "E3 A3 C4"), ("F2", "C3 F3 A3"), ("C3", "G3 C4 E4"), ("G2", "D3 G3 B3"),
            ("A2", "E3 A3 C4"), ("F2", "C3 F3 A3"), ("D3", "A3 D4 F4"), ("E2", "B2 E3 G#3")]
    mel = [
        [(0, 2, "E5"), (2, 1, "D5")], [(0, 1.5, "C5"), (1.5, 0.5, "A4"), (2, 1, "C5")],
        [(0, 2, "G4"), (2, 1, "E4")], [(0, 3, "D5")],
        [(0, 2, "E5"), (2, 1, "A5")], [(0, 1.5, "G5"), (1.5, 0.5, "F5"), (2, 1, "E5")],
        [(0, 2, "D5"), (2, 1, "F5")], [(0, 3, "E5")],
    ]
    if var == 1:
        mel += [[(0, 2, "C5"), (2, 1, "B4")], [(0, 1.5, "A4"), (1.5, 0.5, "C5"), (2, 1, "E5")],
                [(0, 2, "D5"), (2, 1, "C5")], [(0, 3, "B4")],
                [(0, 2, "C5"), (2, 1, "E5")], [(0, 1.5, "D5"), (1.5, 0.5, "C5"), (2, 1, "B4")],
                [(0, 3, "A4")], [(0, 3, "A4")]]
        prog += [("A2", "E3 A3 C4"), ("F2", "C3 F3 A3"), ("D3", "A3 D4 F4"), ("E2", "B2 E3 G#3"),
                 ("F2", "C3 F3 A3"), ("G2", "D3 G3 B3"), ("A2", "E3 A3 C4"), ("A2", "E3 A3 E4")]
    for bar, ((bass, chord), line) in enumerate(zip(prog, mel)):
        b0 = bar * 3
        cn = chord.split()
        ev.append((b0, 3.0, bass, 0.55))
        ev.append((b0 + 1, 2.0, cn[0], 0.32))
        ev.append((b0 + 1.5, 1.5, cn[1], 0.3))
        ev.append((b0 + 2, 1.0, cn[2], 0.3))
        for (o, d, nm) in line:
            ev.append((b0 + o, d, nm, 0.62))
    return ev, len(prog) * 3


def theme(rng):
    ev, beats = theme_events(0)
    y = score(ev, 66, beats, rng)
    return fade(norm(y, 0.55), 0.01, 3.0)


def ending(rng):
    ev, beats = theme_events(1)
    y = score(ev, 60, beats, rng, 0.9)
    return fade(norm(y, 0.55), 0.01, 4.0)


def main():
    rng = np.random.default_rng(20)
    print("custom sounds:")
    write("sfx/engine_bike", engine_bike(rng))
    write("sfx/engine_truck", engine_truck(rng))
    write("sfx/engine_start", engine_start(rng))
    for k in range(1, 6):
        write(f"sfx/birds{k}", birds(rng, k), q=3)
    write("sfx/wind", wind(rng), q=2)
    write("sfx/radio", radio(rng))
    write("music/theme", theme(rng), q=3)
    write("music/ending", ending(rng), q=3)


if __name__ == "__main__":
    main()
