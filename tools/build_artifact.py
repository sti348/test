"""Assemble the browser player (build/artifact/): the same renderer as the
preview video, packaged as a static page with its data files."""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess

import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "build", "artifact")
PRE = os.path.join(ROOT, "build", "preview")
RP = os.path.join(ROOT, "resourcepack", "assets", "kino")

PARTICLES = (["flame", "lava", "critical_hit", "splash_0", "splash_1", "splash_2", "splash_3"]
             + [f"generic_{i}" for i in range(8)] + [f"big_smoke_{i}" for i in range(12)]
             + [f"explosion_{i}" for i in range(16)])


def copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy(src, dst)


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    # renderer modules, with paths made relative to the page
    for fn in ("player.js", "mcmodel.js", "world.js", "stage.js", "filmplayer.js"):
        s = open(os.path.join(ROOT, "web", "lib", fn), encoding="utf-8").read()
        s = s.replace("../build/preview/tex/", "tex/")
        if fn == "stage.js":
            s = s.replace("  render(cam) {", """  setSize(W, H) {
    this.W = W; this.H = H;
    this.renderer.setSize(W, H, false);
    this.camera.aspect = W / H; this.camera.updateProjectionMatrix();
  }

  render(cam) {""", 1)
        with open(os.path.join(OUT, "lib", fn) if os.path.isdir(os.path.join(OUT, "lib")) else _mk(os.path.join(OUT, "lib", fn)), "w",
                  encoding="utf-8") as fh:
            fh.write(s)
    for f in ("world.json", "film.json", "atlas.png"):
        copy(os.path.join(PRE, f), os.path.join(OUT, "data", f))
    for p in PARTICLES + ["sun", "clouds"]:
        copy(os.path.join(PRE, "tex", p + ".png"), os.path.join(OUT, "tex", p + ".png"))
    film = json.load(open(os.path.join(PRE, "film.json"), encoding="utf-8"))
    models = set()
    for a in film["actors"].values():
        copy(os.path.join(RP, "textures", "entity", "skins", a["skin"] + ".png"),
             os.path.join(OUT, "rp", "assets", "kino", "textures", "entity", "skins", a["skin"] + ".png"))
        for it in a["items"]:
            if it[2]:
                models.add(it[2])
    for p in film["props"].values():
        if p["model"]:
            models.add(p["model"])
    for e in film["events"]:
        if e[1] == "drop":
            models.add(e[2]["model"])
    for m in sorted(models):
        src = os.path.join(RP, "models", "item", m + ".json")
        copy(src, os.path.join(OUT, "rp", "assets", "kino", "models", "item", m + ".json"))
        j = json.load(open(src))
        tex = j["parent"].split("/")[-1] if "parent" in j else m
        if "parent" in j:
            copy(os.path.join(RP, "models", "item", tex + ".json"), os.path.join(OUT, "rp", "assets", "kino", "models", "item", tex + ".json"))
        copy(os.path.join(RP, "textures", "item", tex + ".png"), os.path.join(OUT, "rp", "assets", "kino", "textures", "item", tex + ".png"))
    for o in ("letterbox", "scope", "binoculars", "black"):
        copy(os.path.join(RP, "textures", "misc", o + ".png"), os.path.join(OUT, "rp", "assets", "kino", "textures", "misc", o + ".png"))
    wav = os.path.join(PRE, "audio.wav")
    if os.path.exists(wav):
        write_audio(wav, film["length"] / 20)
    poster = os.path.join(ROOT, "build", "poster.jpg")
    if os.path.exists(poster):
        copy(poster, os.path.join(OUT, "poster.jpg"))
    shutil.copy(os.path.join(ROOT, "web", "artifact.html"), os.path.join(OUT, "index.html"))
    n = sum(len(fs) for _, _, fs in os.walk(OUT))
    size = sum(os.path.getsize(os.path.join(b, f)) for b, _, fs in os.walk(OUT) for f in fs)
    print(f"artifact: {n} files, {size / 1e6:.1f} MB -> {OUT}")


CHUNK = 30.0     # seconds per piece
PAD = 0.2        # overlap before / after each piece (covers decoder delay differences)
SYNC_AT = 0.25   # position of the click in sync.mp3


def mp3(samples, sr, path):
    raw = (np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(sr), "-ac", "2", "-i", "-",
                    "-c:a", "libmp3lame", "-b:a", "64k", path], input=raw, check=True)


def write_audio(wav, length_s):
    """The sound track as 30 s MP3 pieces for Web Audio (see Sound in index.html):
    piece k holds [k*30 - 0.2, (k+1)*30 + 0.2) s; sync.mp3 has a click at 0.25 s so
    the page can measure the MP3 decoder delay of the browser it runs in."""
    x, sr = sf.read(wav, dtype="float32", always_2d=True)
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    d = os.path.join(OUT, "audio")
    os.makedirs(d, exist_ok=True)
    n = int(math.ceil(length_s / CHUNK))
    for k in range(n):
        a, b = int(round((k * CHUNK - PAD) * sr)), int(round(((k + 1) * CHUNK + PAD) * sr))
        seg = np.zeros((b - a, 2), np.float32)
        lo, hi = max(a, 0), min(b, len(x))
        if hi > lo:
            seg[lo - a:hi - a] = x[lo:hi]
        mp3(seg, sr, os.path.join(d, f"c{k:03d}.mp3"))
    click = np.zeros((sr, 2), np.float32)
    click[int(SYNC_AT * sr)] = 0.9
    mp3(click, sr, os.path.join(d, "sync.mp3"))
    with open(os.path.join(d, "meta.json"), "w") as fh:
        json.dump({"chunk": CHUNK, "pad": PAD, "n": n, "sync": SYNC_AT, "rate": sr}, fh)
    size = sum(os.path.getsize(os.path.join(d, f)) for f in os.listdir(d))
    print(f"audio: {n} pieces of {CHUNK:.0f} s, {size / 1e6:.1f} MB")


def _mk(p):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


if __name__ == "__main__":
    main()
