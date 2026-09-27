"""Camera-overlay textures (worn as a head item with an 'equippable' camera_overlay):
letterbox (2.39:1 bars), rifle scope, binoculars, black."""
import math
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "resourcepack", "assets", "kino", "textures", "misc")
W, H = 512, 512
BAR = int(H * 0.128)          # bar height for a 2.39:1 frame on a 16:9 screen
ASPECT = 16 / 9               # overlays are stretched to the screen


def base():
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = im.load()
    for y in list(range(BAR)) + list(range(H - BAR, H)):
        for x in range(W):
            px[x, y] = (0, 0, 0, 255)
    return im, px


def circles(px, centers, r):
    for y in range(H):
        for x in range(W):
            if px[x, y][3] == 255:
                continue
            inside = False
            edge = 1e9
            for (cx, cy) in centers:
                d = math.hypot((x - cx) * ASPECT, y - cy)
                edge = min(edge, d - r)
                if d <= r:
                    inside = True
            if not inside:
                px[x, y] = (0, 0, 0, 255)
            elif edge > -6:
                a = int(255 * (1 - (-edge) / 6) * 0.85)
                px[x, y] = (0, 0, 0, a)


def main():
    os.makedirs(OUT, exist_ok=True)
    im, px = base()
    im.save(os.path.join(OUT, "letterbox.png"))

    im, px = base()
    circles(px, [(W / 2, H / 2)], H * 0.43)
    for x in range(W):            # cross hairs
        for dy in (0,):
            if px[x, H // 2][3] < 200:
                px[x, H // 2 + dy] = (10, 10, 10, 230)
    for y in range(H):
        if px[W // 2, y][3] < 200:
            px[W // 2, y] = (10, 10, 10, 230)
    for k in range(-3, 4):        # thicker outer posts
        for x in list(range(0, int(W / 2 - 60))) + list(range(int(W / 2 + 60), W)):
            if k in (-1, 0, 1) and px[x, H // 2 + k][3] < 200:
                px[x, H // 2 + k] = (10, 10, 10, 240)
    im.save(os.path.join(OUT, "scope.png"))

    im, px = base()
    circles(px, [(W / 2 - W * 0.1, H / 2), (W / 2 + W * 0.1, H / 2)], H * 0.36)
    im.save(os.path.join(OUT, "binoculars.png"))

    Image.new("RGBA", (16, 16), (0, 0, 0, 255)).save(os.path.join(OUT, "black.png"))
    print("overlays written")


if __name__ == "__main__":
    main()
