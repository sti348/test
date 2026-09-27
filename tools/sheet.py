"""Contact sheet: python3 tools/sheet.py outdir cols out.png"""
import os, sys
from PIL import Image, ImageDraw
d, cols, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
files = sorted([f for f in os.listdir(d) if f.startswith("f_")], key=lambda f: float(f[2:-4]))
ims = [Image.open(os.path.join(d, f)).convert("RGB") for f in files]
w, h = ims[0].size
sc = 0.5 if w > 700 else 1.0
tw, th = int(w * sc), int(h * sc)
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (cols * tw, rows * th), (0, 0, 0))
for i, (im, f) in enumerate(zip(ims, files)):
    im = im.resize((tw, th))
    ImageDraw.Draw(im).text((6, 4), f[2:-4], fill=(255, 255, 0))
    sheet.paste(im, ((i % cols) * tw, (i // cols) * th))
sheet.save(out)
