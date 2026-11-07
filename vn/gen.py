"""Generate visual-novel backgrounds / CG for "School World" with an image model.

The Minecraft map (megaschool/) decides *where* things are and what they look
like; its screenshots can be passed as composition references.  The image
model paints the detailed picture.

  python3 vn/gen.py list                          # the shot list
  python3 vn/gen.py prompt forecourt dusk         # print the full prompt of one shot
  python3 vn/gen.py run [ID ...] [--variants dusk,day] [--no-ref] [--force] [--jobs 2]
  python3 vn/gen.py sheet                         # contact sheet of everything generated

The API is OpenAI-Images compatible (POST /images/generations, and
/images/edits when a reference image is attached).  Configure with:

  IMAGE_API_BASE   default https://api.openai.com/v1
  IMAGE_MODEL      default gpt-image-2.6-flare (the key also lists gpt-image-2.6-sunburst)
  IMAGE_API_KEY    the key (in a Claude cloud session the network proxy adds it; leave unset)
  IMAGE_SIZE       default 1536x1024 (cropped and resized to 1920x1080 afterwards)
  IMAGE_QUALITY    default high

Output: vn/out/<id>/<variant>.png (as generated), <variant>_1080p.png (16:9,
1920x1080, ready for the VN engine) and <variant>.json (prompt, model, time)."""
from __future__ import annotations

import base64
import concurrent.futures as cf
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "out")

BASE = os.environ.get("IMAGE_API_BASE", "https://api.openai.com/v1").rstrip("/")
MODEL = os.environ.get("IMAGE_MODEL", "gpt-image-2.6-flare")
SIZE = os.environ.get("IMAGE_SIZE", "1536x1024")
QUALITY = os.environ.get("IMAGE_QUALITY", "high")

# The art direction of style.md, in the words the model gets: an art style (swappable, see
# styles.json) and the world's rules (always).
ART = ("Highly detailed anime-style digital painting, clean linework, soft volumetric light, atmospheric "
       "perspective, the quality of a commercial galgame or anime film background.")
ANTI_AI = ("Avoid the generic AI-art look: no oversaturated neon gradients, no glossy plastic surfaces, no lens "
           "flares or bloom, no evenly distributed hyper-detail, no perfect mirror symmetry; prefer a restrained "
           "palette, visible hand-made marks, simplified areas away from the focal point and a slightly "
           "asymmetric, considered composition.")
STYLE = (
    "Background art for a visual novel set in 'School World', a world where everything is a school. "
    "Not pixel art, not blocky, not a 3D render, not a photo. Wide 16:9 composition, eye-level camera unless "
    "stated otherwise, leave room in the lower middle of the frame for character sprites. "
    "Architecture at a colossal, awe-inspiring scale (megalophobia, solemn but not horror): school buildings "
    "tens to hundreds of storeys tall with very tall floors; windows gathered into wide bands or tall strips "
    "separated by large solid walls and giant piers, never a dense grid of tiny windows. Human-scale details "
    "(benches, lamps, bicycles, trees) emphasise the size."
)
NO_PEOPLE = "No people or characters in the image."
NO_TEXT = "Absolutely no text, letters, signs with writing, logos or numbers anywhere in the image."
TIME = {
    "dusk": "Perpetual twilight: a soft dusky violet-grey sky with the first few stars and a faint warm glow low on "
            "the horizon; the scene is still clearly readable in a cool ambient light; some classroom windows lit "
            "warm yellow for evening study.",
    "day": "Clear daytime: bright blue sky with a few soft clouds, gentle sunlight, crisp shadows.",
    "night": "Deep night: starry sky, the scene lit mainly by warm windows, lamps and glowing details.",
}
REF_NOTE = ("The attached image is a blocky, low-detail Minecraft render of this place. Use it only as a rough "
            "reference for layout, camera angle and the shapes of the buildings; repaint everything as a detailed "
            "painting with realistic materials and proportions.")


def scenes():
    return json.load(open(os.path.join(HERE, "scenes.json"), encoding="utf-8"))


def styles():
    return json.load(open(os.path.join(HERE, "styles.json"), encoding="utf-8"))


def prompt_of(sc, variant, with_ref, art=None):
    parts = [art or ART, STYLE, sc["prompt"], TIME[variant], ANTI_AI]
    if sc.get("kind", "bg") == "bg":
        parts.append(NO_PEOPLE)
    if sc.get("extra"):
        parts.append(sc["extra"])
    parts.append(NO_TEXT)
    if with_ref:
        parts.append(REF_NOTE)
    return "\n\n".join(parts)


# ------------------------------------------------------------------ API
def _headers(extra=None):
    h = {"Authorization": "Bearer " + os.environ.get("IMAGE_API_KEY", "sk-placeholder-injected-by-proxy")}
    h.update(extra or {})
    return h


def _post(url, body, headers, timeout=600):
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:800]}") from None


def _multipart(fields, files):
    b = uuid.uuid4().hex
    out = io.BytesIO()
    for k, v in fields.items():
        out.write(f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    for k, (name, data, ctype) in files:
        out.write(f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{name}\"\r\n"
                  f"Content-Type: {ctype}\r\n\r\n".encode())
        out.write(data)
        out.write(b"\r\n")
    out.write(f"--{b}--\r\n".encode())
    return out.getvalue(), f"multipart/form-data; boundary={b}"


def generate(prompt, ref_path=None):
    """One image; returns PNG/JPEG bytes."""
    if ref_path:
        from PIL import Image
        im = Image.open(ref_path).convert("RGB")
        buf = io.BytesIO()
        im.save(buf, "PNG")
        body, ctype = _multipart({"model": MODEL, "prompt": prompt, "size": SIZE, "quality": QUALITY, "n": 1},
                                 [("image[]", (os.path.basename(ref_path).rsplit(".", 1)[0] + ".png",
                                               buf.getvalue(), "image/png"))])
        r = _post(BASE + "/images/edits", body, _headers({"Content-Type": ctype}))
    else:
        body = json.dumps({"model": MODEL, "prompt": prompt, "size": SIZE, "quality": QUALITY, "n": 1}).encode()
        r = _post(BASE + "/images/generations", body, _headers({"Content-Type": "application/json"}))
    d = r["data"][0]
    if d.get("b64_json"):
        return base64.b64decode(d["b64_json"])
    with urllib.request.urlopen(d["url"], timeout=300) as f:
        return f.read()


def to_1080p(data):
    """Centre-crop to 16:9 and resize to 1920x1080."""
    from PIL import Image
    im = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = im.size
    if w / h > 16 / 9:
        nw = int(h * 16 / 9)
        im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w * 9 / 16)
        im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    return im.resize((1920, 1080), Image.LANCZOS)


def run_one(sc, variant, use_ref=True, force=False, retries=3):
    d = os.path.join(OUT, sc["id"])
    os.makedirs(d, exist_ok=True)
    png = os.path.join(d, f"{variant}.png")
    if os.path.exists(png) and not force:
        return f"skip {sc['id']}/{variant} (exists)"
    ref = os.path.join(ROOT, sc["ref"]) if (use_ref and sc.get("ref")) else None
    if ref and not os.path.exists(ref):
        ref = None
    prompt = prompt_of(sc, variant, bool(ref))
    for k in range(retries):
        try:
            t = time.time()
            data = generate(prompt, ref)
            break
        except Exception as e:                                          # noqa: BLE001 - report and retry
            if k == retries - 1:
                return f"FAIL {sc['id']}/{variant}: {e}"
            time.sleep(10 * (k + 1))
    open(png, "wb").write(data)
    to_1080p(data).save(os.path.join(d, f"{variant}_1080p.png"))
    json.dump({"id": sc["id"], "title": sc["title"], "variant": variant, "model": MODEL, "size": SIZE,
               "quality": QUALITY, "reference": sc.get("ref") if ref else None, "prompt": prompt,
               "seconds": round(time.time() - t, 1), "created": time.strftime("%Y-%m-%d %H:%M:%S")},
              open(os.path.join(d, f"{variant}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return f"ok   {sc['id']}/{variant}  {sc['title']}  ({time.time() - t:.0f}s{', ref' if ref else ''})"


def sheet(cols=4, w=480):
    from PIL import Image, ImageDraw
    items = []
    for sc in scenes():
        for v in sc["variants"]:
            p = os.path.join(OUT, sc["id"], f"{v}_1080p.png")
            if os.path.exists(p):
                items.append((f"{sc['id']} / {v}", p))
    if not items:
        raise SystemExit("nothing generated yet")
    h = w * 9 // 16
    S = Image.new("RGB", (cols * w, (len(items) + cols - 1) // cols * (h + 18)), (18, 18, 26))
    dr = ImageDraw.Draw(S)
    for i, (label, p) in enumerate(items):
        im = Image.open(p).convert("RGB").resize((w, h))
        x, y = (i % cols) * w, (i // cols) * (h + 18)
        S.paste(im, (x, y + 18))
        dr.text((x + 4, y + 3), label, fill=(230, 230, 240))
    path = os.path.join(OUT, "sheet.jpg")
    S.save(path, quality=88)
    print(path)


def prompt_style(sc, variant, st):
    """Style-first prompt for comparing art styles: the medium leads and closes, the subject is one line."""
    tod = {"dusk": "at dusk, a soft violet-grey sky with the first stars and some windows lit warm",
           "day": "on a clear day", "night": "at night, lit windows and lamps"}[variant]
    return "\n\n".join([
        f"An image made entirely in this style - {st['name_en']}: {st['art']}",
        f"Subject: {sc.get('short') or sc['prompt']}, {tod}. The buildings are enormous; tiny benches and lamps "
        "show the scale. No people. No text or lettering anywhere.",
        f"Important: every part of the image must be rendered strictly in the style described above "
        f"({st['name_en']}), with its characteristic marks, palette and simplifications. Do not drift toward a "
        "generic polished digital painting, and avoid the usual AI-art look (glossy surfaces, neon gradients, "
        "evenly spread hyper-detail)."])


def style_test(sc, variant, only=(), jobs=4, tag="r2"):
    """The same shot in every art style of styles.json (or the named ones), and a labelled sheet."""
    d = os.path.join(OUT, "_styles", f"{sc['id']}_{variant}_{tag}")
    os.makedirs(d, exist_ok=True)
    todo = [st for st in styles() if not only or st["id"] in only]

    def one(st):
        png = os.path.join(d, f"{st['id']}.png")
        if os.path.exists(png):
            return f"skip {st['id']}"
        prompt = prompt_style(sc, variant, st)
        for k in range(3):
            try:
                t = time.time()
                data = generate(prompt)
                break
            except Exception as e:                                      # noqa: BLE001
                if k == 2:
                    return f"FAIL {st['id']}: {e}"
                time.sleep(8 * (k + 1))
        open(png, "wb").write(data)
        to_1080p(data).save(os.path.join(d, f"{st['id']}_1080p.png"))
        json.dump({"style": st, "scene": sc["id"], "variant": variant, "model": MODEL, "prompt": prompt},
                  open(os.path.join(d, f"{st['id']}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return f"ok   {st['id']:14s} {st['name']}  ({time.time() - t:.0f}s)"
    with cf.ThreadPoolExecutor(jobs) as ex:
        for msg in ex.map(one, todo):
            print(msg, flush=True)
    style_sheet(d, [st for st in styles()])


def style_sheet(d, sts, cols=3, w=640):
    from PIL import Image, ImageDraw, ImageFont
    items = [(f"{i + 1}. {st['name']}", os.path.join(d, f"{st['id']}_1080p.png")) for i, st in enumerate(sts)]
    items = [it for it in items if os.path.exists(it[1])]
    font = None
    for f in ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
              "/usr/share/fonts/opentype/unifont/unifont.otf"):
        if os.path.exists(f):
            font = ImageFont.truetype(f, 22)
            break
    h, lab = w * 9 // 16, 32
    S = Image.new("RGB", (cols * w, (len(items) + cols - 1) // cols * (h + lab)), (24, 24, 28))
    dr = ImageDraw.Draw(S)
    for i, (label, p) in enumerate(items):
        x, y = (i % cols) * w, (i // cols) * (h + lab)
        S.paste(Image.open(p).convert("RGB").resize((w, h)), (x, y + lab))
        dr.text((x + 8, y + 4), label, fill=(235, 235, 240), font=font)
    out = os.path.join(d, "sheet.jpg")
    S.save(out, quality=88)
    print(out)


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return
    cmd, rest = argv[0], argv[1:]
    S = {s["id"]: s for s in scenes()}
    if cmd == "list":
        for s in S.values():
            print(f"{s['id']:22s} {s['title']:16s} {','.join(s['variants']):18s} {'ref' if s.get('ref') else ''}")
    elif cmd == "prompt":
        sc = S[rest[0]]
        v = rest[1] if len(rest) > 1 else sc["variants"][0]
        print(prompt_of(sc, v, bool(sc.get("ref"))))
    elif cmd == "run":
        ids, variants, use_ref, force, jobs = [], None, True, False, 2
        it = iter(rest)
        for a in it:
            if a == "--variants":
                variants = next(it).split(",")
            elif a == "--no-ref":
                use_ref = False
            elif a == "--force":
                force = True
            elif a == "--jobs":
                jobs = int(next(it))
            else:
                ids.append(a)
        todo = [(S[i], v) for i in (ids or list(S)) for v in S[i]["variants"] if not variants or v in variants]
        print(f"{len(todo)} images with {MODEL} at {BASE}", flush=True)
        with cf.ThreadPoolExecutor(jobs) as ex:
            for msg in ex.map(lambda t: run_one(t[0], t[1], use_ref, force), todo):
                print(msg, flush=True)
    elif cmd == "sheet":
        sheet()
    elif cmd == "styles":
        style_test(S[rest[0]], rest[1] if len(rest) > 1 else "dusk", rest[2:])
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
