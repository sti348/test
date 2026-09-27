"""Render the preview video: splits the film at scene boundaries, renders the
segments with N parallel headless browsers, concatenates, adds the audio.
  python3 tools/render.py [workers] [width] [height] [fps]"""
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "build", "render")


def main():
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    w, h = (sys.argv[2], sys.argv[3]) if len(sys.argv) > 3 else ("1280", "720")
    fps = sys.argv[4] if len(sys.argv) > 4 else "20"
    film = json.load(open(os.path.join(ROOT, "build", "preview", "film.json")))
    cuts = [t for t, _ in film["scenes"]] + [film["length"]]
    segs = [(i, cuts[i], cuts[i + 1]) for i in range(len(cuts) - 1) if cuts[i + 1] > cuts[i]]
    os.makedirs(OUT, exist_ok=True)
    todo = [s for s in segs if not os.path.exists(os.path.join(OUT, f"seg_{s[0]:02d}.mp4"))]
    todo.sort(key=lambda s: -(s[2] - s[1]))
    running = []
    t0 = time.time()
    while todo or running:
        while todo and len(running) < workers:
            i, a, b = todo.pop(0)
            tmp = os.path.join(OUT, f"seg_{i:02d}.part.mp4")
            log = open(os.path.join(OUT, f"seg_{i:02d}.log"), "w")
            p = subprocess.Popen(["node", os.path.join(ROOT, "web", "capture.mjs"), str(a), str(b), fps, w, h, tmp],
                                 stdout=log, stderr=subprocess.STDOUT, cwd=ROOT)
            running.append((p, i, tmp))
            print(f"[{time.time() - t0:6.0f}s] start seg {i} ({(b - a) / 20:.0f}s of film)", flush=True)
        for r in list(running):
            p, i, tmp = r
            if p.poll() is not None:
                running.remove(r)
                if p.returncode == 0:
                    os.rename(tmp, os.path.join(OUT, f"seg_{i:02d}.mp4"))
                    print(f"[{time.time() - t0:6.0f}s] done seg {i}", flush=True)
                else:
                    print(f"[{time.time() - t0:6.0f}s] FAILED seg {i}", flush=True)
        time.sleep(2)
    lst = os.path.join(OUT, "list.txt")
    with open(lst, "w") as fh:
        for (i, a, b) in segs:
            fh.write(f"file 'seg_{i:02d}.mp4'\n")
    video = os.path.join(OUT, "video.mp4")
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", video])
    final = os.path.join(ROOT, "build", "奇诺之旅_第七话_Minecraft.mp4")
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i",
                           os.path.join(ROOT, "build", "preview", "audio.wav"), "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                           "-shortest", "-movflags", "+faststart", final])
    print("final:", final, f"{os.path.getsize(final) / 1e6:.1f} MB", f"[{time.time() - t0:.0f}s]")


if __name__ == "__main__":
    main()
