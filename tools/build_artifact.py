"""Assemble the browser player (build/artifact/): the same renderer as the
preview video, packaged as a static page with its data files."""
from __future__ import annotations

import json
import os
import shutil
import subprocess

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
        subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-ac", "1", "-c:a", "aac", "-b:a", "40k",
                               os.path.join(OUT, "audio.mp4")])
    poster = os.path.join(ROOT, "build", "poster.jpg")
    if os.path.exists(poster):
        copy(poster, os.path.join(OUT, "poster.jpg"))
    shutil.copy(os.path.join(ROOT, "web", "artifact.html"), os.path.join(OUT, "index.html"))
    n = sum(len(fs) for _, _, fs in os.walk(OUT))
    size = sum(os.path.getsize(os.path.join(b, f)) for b, _, fs in os.walk(OUT) for f in fs)
    print(f"artifact: {n} files, {size / 1e6:.1f} MB -> {OUT}")


def _mk(p):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


if __name__ == "__main__":
    main()
