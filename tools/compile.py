"""Compile the film script.
  python3 tools/compile.py            -> build/preview/film.json  +  datapack/
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import film as filmlib  # noqa: E402
import script  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def export_preview(F, S, path):
    actors = {}
    for a in F.actors.values():
        actors[a.id] = {
            "skin": a.skin, "slim": a.slim,
            "track": filmlib.compress(S["actors"][a.id]),
            "poses": sorted([list(p) for p in a.poses]),
            "rides": sorted([list(r) for r in a.rides], key=lambda r: r[0]),
            "items": sorted([list(i) for i in a.items], key=lambda r: r[0]),
            "fires": [list(f) for f in a.fires],
        }
    props = {}
    for p in F.props.values():
        props[p.id] = {
            "model": p.model, "translation": list(p.translation), "scale": p.scale,
            "track": filmlib.compress(S["props"][p.id]),
        }
    events = []
    for k, (t, kind, data) in enumerate(sorted(F.events, key=lambda e: e[0])):
        if kind == "sound":
            continue
        d = dict(data)
        if kind == "particle":
            d.setdefault("seed", (t * 7919 + k * 104729) & 0x7fffffff)
        events.append([t, kind, d])
    out = {
        "length": F.length, "tps": filmlib.TPS,
        "actors": actors, "props": props,
        "cam": filmlib.compress(S["cam"], jump=3.5),
        "subs": sorted([list(s) for s in F.subs]),
        "titles": sorted([list(t) for t in F.titles]),
        "overlays": sorted([list(o) for o in F.overlays], key=lambda o: o[0]),
        "times": sorted([list(t) for t in F.times], key=lambda o: o[0]),
        "scenes": [list(s) for s in F.scenes],
        "speakers": F.speakers,
        "events": events,
    }
    with open(path, "w") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
    return out


def main():
    t0 = time.time()
    F = script.build()
    S = filmlib.sample(F)
    import sfx
    auto = sfx.auto_events(F, S)
    F.events += auto
    sfx.write_sounds_json()
    os.makedirs(os.path.join(ROOT, "build", "preview"), exist_ok=True)
    export_preview(F, S, os.path.join(ROOT, "build", "preview", "film.json"))
    if "--no-mc" not in sys.argv:
        import compile_mc
        compile_mc.write_datapack(F, S, os.path.join(ROOT, "datapack"))
    L = F.length / filmlib.TPS
    nsnd = sum(1 for e in F.events if e[1] == "sound")
    print(f"sound: {nsnd} sound events ({len(auto)} automatic: footsteps, engines, ambience), "
          f"{len(sfx.voice_events(F))} voice lines")
    print(f"film: {F.length} ticks ({int(L // 60)}:{int(L % 60):02d}), {len(F.shots)} shots, {len(F.subs)} lines, "
          f"{len(F.actors)} actors, {len(F.props)} props  [{time.time() - t0:.1f}s]")


if __name__ == "__main__":
    main()
