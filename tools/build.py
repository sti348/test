"""Build everything:  python3 tools/build.py [--preview]

  resourcepack/   skins, item models, camera overlays        -> dist/奇诺之旅_资源包.zip
  datapack/       sets + the film as per-tick functions       -> dist/奇诺之旅_数据包.zip
  build/preview/  data for the web preview renderer (needs npm for vanilla textures)
"""
import json
import os
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
RP_FORMAT = 69   # 1.21.9 / 1.21.10


def run(script, *args):
    subprocess.check_call([sys.executable, os.path.join(TOOLS, script), *args], cwd=ROOT)


def zipdir(src, dst):
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for base, _, files in os.walk(src):
            for fn in sorted(files):
                p = os.path.join(base, fn)
                z.write(p, os.path.relpath(p, src))


def main():
    run("skins.py")
    run("models.py")
    run("overlays.py")
    rp = os.path.join(ROOT, "resourcepack")
    with open(os.path.join(rp, "pack.mcmeta"), "w", encoding="utf-8") as fh:
        json.dump({"pack": {"description": "奇诺之旅 · 皮肤 / 艾鲁梅斯 / 道具模型 / 镜头遮罩",
                            "pack_format": RP_FORMAT, "min_format": RP_FORMAT, "max_format": 999}},
                  fh, ensure_ascii=False, indent=2)
    if "--preview" in sys.argv:
        run("build_preview.py")
        run("compile.py")
    else:
        run("compile.py")
    dist = os.path.join(ROOT, "dist")
    os.makedirs(dist, exist_ok=True)
    zipdir(rp, os.path.join(dist, "奇诺之旅_资源包.zip"))
    zipdir(os.path.join(ROOT, "datapack"), os.path.join(dist, "奇诺之旅_数据包.zip"))
    for f in sorted(os.listdir(dist)):
        print(f"dist/{f}: {os.path.getsize(os.path.join(dist, f)) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
