"""Item models for the film: Hermes (motorrad), the truck, the museum cannon,
the baby bundle and small props.  Run:  python3 tools/models.py"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from modellib import (Model, bark, canvas, cartwheel, crate, emblem, fins, glass, hexc, lens,  # noqa: E402
                      log_end, metal, pattern, planks, roll_end, solid, spoked_wheel, tire)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "resourcepack")


def arc(m, cx, cy, cz, r0, r1, x0, x1, painter, angles):
    """Mudguard: arc of boxes above an axle (angles measured from the top, +ve toward -Z/front... see note)."""
    import math
    L = 2 * r1 * math.tan(math.pi / 16) + 0.3
    for a in angles:
        if abs(a) <= 45:
            m.box([x0, cy + r0, cz - L / 2], [x1, cy + r1, cz + L / 2], painter,
                  rot=([(x0 + x1) / 2, cy, cz], "x", a) if a else None)
        else:  # 67.5 etc: start from the side position (front/back) and rotate back
            side = 1 if a > 0 else -1           # +: back (+Z) side, -: front
            b = a - 90 if a > 0 else a + 90
            if side > 0:
                m.box([x0, cy - L / 2, cz + r0], [x1, cy + L / 2, cz + r1], painter,
                      rot=([(x0 + x1) / 2, cy, cz], "x", b) if b else None)
            else:
                m.box([x0, cy - L / 2, cz - r1], [x1, cy + L / 2, cz - r0], painter,
                      rot=([(x0 + x1) / 2, cy, cz], "x", b) if b else None)


# ----------------------------------------------------------------------------
def hermes():
    m = Model("hermes", 128, 256)
    FRAME = "4e5866"
    SILVER = "b4b8bc"
    CHROME = "c8c8c4"
    BRASS = "b8986a"
    LEATHER = "34302e"
    frame = solid(FRAME, n=4)
    chrome = metal(CHROME)
    silver = metal(SILVER)
    dark = solid("2e2e30", n=3)
    fender = metal("a4a8ae")
    rub = solid("262422", n=2)

    # wheels -----------------------------------------------------------------
    for cz in (-8.0, 13.5):
        m.ring_x(8, 5.5, cz, 5.5, 1.3, 7.0, 9.0, tire("3c3632"))
        m.box([8, 1.2, cz - 4.3], [8, 9.8, cz + 4.3], {"east": spoked_wheel(), "west": spoked_wheel()}, density=2)
        m.box([6.6, 4.8, cz - 0.7], [9.4, 6.2, cz + 0.7], chrome)
    m.box([9.0, 3.9, 11.9], [9.8, 7.1, 15.1], silver)          # rear brake drum
    m.box([6.2, 4.2, -9.3], [7.0, 6.8, -6.7], silver)           # front brake drum

    # mudguards --------------------------------------------------------------
    arc(m, 8, 5.5, -8.0, 6.0, 6.7, 6.4, 9.6, fender, (0, -22.5, 22.5, -45, 45, -67.5))
    arc(m, 8, 5.5, 13.5, 6.0, 6.7, 6.4, 9.6, fender, (0, -22.5, 22.5, 45, 67.5))
    m.box([6.6, 4.6, -8.3], [7.0, 11.8, -7.7], fender)          # front guard stays
    m.box([9.0, 4.6, -8.3], [9.4, 11.8, -7.7], fender)

    # front fork, headstock, headlight ---------------------------------------
    for x0 in (5.8, 9.2):
        m.box([x0, 5.3, -7.6], [x0 + 1.0, 15.8, -6.4], chrome, rot=([x0 + 0.5, 10.5, -7.0], "x", 22.5))
    m.box([5.6, 14.2, -5.6], [10.4, 15.6, -4.0], frame, rot=([8, 14.9, -4.8], "x", 22.5))   # fork crown
    m.box([7.2, 12.5, -5.2], [8.8, 17.0, -3.8], frame, rot=([8, 14.7, -4.5], "x", 22.5))    # headstock
    m.box([5.6, 12.6, -10.4], [10.4, 17.4, -7.6],
          {"north": lens("f2eac6", "d0d0cc"), "south": chrome, "east": chrome, "west": chrome, "up": chrome, "down": chrome})
    m.box([6.6, 13.2, -7.6], [9.4, 16.8, -6.4], chrome)         # headlight shell back
    # handlebar, grips, levers, speedometer
    m.box([1.6, 16.8, -3.4], [14.4, 17.6, -2.6], solid("3a3c40", n=2))
    m.box([6.6, 15.4, -4.0], [7.4, 17.0, -3.2], chrome)
    m.box([8.6, 15.4, -4.0], [9.4, 17.0, -3.2], chrome)
    m.box([1.2, 16.6, -3.6], [3.6, 17.8, -2.4], rub)
    m.box([12.4, 16.6, -3.6], [14.8, 17.8, -2.4], rub)
    m.box([3.4, 17.1, -5.2], [5.2, 17.5, -3.4], chrome)
    m.box([10.8, 17.1, -5.2], [12.6, 17.5, -3.4], chrome)
    m.box([7.0, 17.2, -4.6], [9.0, 18.8, -3.0],
          {"up": pattern(["cddc", "dwwd", "dwkd", "cddc"], {"c": CHROME, "d": "2a2a2a", "w": "e8e4d8", "k": "8a2020"}),
           "north": chrome, "south": chrome, "east": chrome, "west": chrome, "down": chrome})
    # windscreen (translucent) with two brackets
    m.box([3.4, 17.0, -5.3], [12.6, 25.6, -5.1],
          {"north": glass("dfe8ec", 70, "e8eef0"), "south": glass("dfe8ec", 70, "e8eef0")},
          rot=([8, 17, -5.2], "x", 22.5))
    m.box([3.0, 16.0, -5.6], [3.6, 19.4, -4.8], chrome, rot=([3.3, 17, -5.2], "x", 22.5))
    m.box([12.4, 16.0, -5.6], [13.0, 19.4, -4.8], chrome, rot=([12.7, 17, -5.2], "x", 22.5))

    # fuel tank with emblem -------------------------------------------------
    m.box([5.3, 11.4, -4.2], [10.7, 15.0, 4.4],
          {"east": emblem(SILVER, "c6a458"), "west": emblem(SILVER, "c6a458"),
           "north": silver, "south": silver, "up": silver, "down": silver})
    m.box([5.8, 15.0, -3.4], [10.2, 15.8, 3.6], silver)
    m.box([5.6, 11.8, -5.4], [10.4, 14.4, -3.6], silver, rot=([8, 13, -4.5], "x", -22.5))
    m.box([7.4, 15.8, -1.6], [8.6, 16.4, -0.4], chrome)          # filler cap
    m.box([6.8, 10.6, -4.6], [9.2, 11.6, 6.6], frame)             # top tube

    # frame ------------------------------------------------------------------
    m.box([7.2, 3.6, -6.0], [8.8, 12.8, -4.6], frame, rot=([8, 8.2, -5.3], "x", -22.5))   # down tube
    m.box([7.3, 3.0, 5.0], [8.7, 11.6, 6.4], frame)                                        # seat tube
    for x0 in (6.2, 9.0):
        m.box([x0, 2.4, -4.2], [x0 + 0.8, 3.2, 6.4], frame)                                # cradle rails
        m.box([x0, 4.2, 5.6], [x0 + 0.8, 5.2, 13.6], frame)                                # chain stays
        m.box([x0, 4.2, 9.6], [x0 + 0.8, 13.4, 10.6], frame, rot=([x0 + 0.4, 8.8, 10.1], "x", -45))  # seat stays

    # engine -----------------------------------------------------------------
    m.box([5.6, 5.4, -3.4], [10.4, 10.2, 0.8], fins("c4c4c0", "7a7a78"))                  # finned barrel
    m.box([5.4, 10.2, -3.6], [10.6, 11.2, 1.0], fins("b8b8b4", "6e6e6c"))                 # head
    m.box([5.8, 2.2, -3.6], [10.2, 6.2, 4.8], silver)                                      # crankcase
    m.box([6.0, 2.8, 4.8], [10.0, 6.8, 8.2], silver)                                       # gearbox
    m.box([4.6, 2.6, -2.2], [5.8, 6.2, 8.4], metal("d0d0cc"))                             # primary cover (left)
    m.box([10.2, 3.0, -2.6], [11.0, 6.0, 1.6], metal("d0d0cc"))                           # timing cover (right)
    m.box([8.6, 6.6, 0.8], [10.2, 8.4, 2.4], chrome)                                       # carburettor
    m.box([5.2, 7.6, 5.4], [10.8, 11.0, 8.8], solid("3c4450", n=3))                       # battery / tool box
    m.box([3.0, 3.8, 2.4], [5.0, 4.4, 3.6], rub)                                           # footrests
    m.box([11.0, 3.8, 2.4], [13.0, 4.4, 3.6], rub)
    m.box([3.6, 1.6, 6.0], [4.6, 4.2, 7.0], chrome, rot=([4.1, 2.9, 6.5], "x", 22.5))      # kick-start lever

    # exhaust (brass-coloured, right side = +X) ------------------------------
    brass = metal(BRASS)
    m.box([10.0, 3.0, -4.8], [11.2, 8.6, -3.6], brass)
    m.box([10.0, 2.2, -4.8], [11.2, 3.4, -1.8], brass)
    m.box([10.2, 2.2, -1.8], [11.4, 3.4, 9.0], brass)
    m.box([10.2, 2.0, 8.6], [12.4, 4.6, 18.0], brass)
    m.box([10.5, 2.3, 18.0], [12.1, 4.3, 18.6], solid("6e5a40", n=2))

    # saddle on springs -----------------------------------------------------
    m.box([5.6, 12.1, 4.8], [10.4, 13.5, 11.0], solid(LEATHER, n=4, grad=0.25))
    m.box([6.6, 12.2, 3.4], [9.4, 13.3, 4.8], solid(LEATHER, n=4, grad=0.25))
    for x0 in (5.9, 9.1):
        m.box([x0, 9.4, 9.0], [x0 + 1.0, 12.1, 10.2], fins("bcbcb8", "6a6a68"))

    # rear rack + luggage ---------------------------------------------------
    m.box([3.0, 13.2, 11.6], [13.0, 14.0, 23.0], dark)
    for x0 in (3.0, 12.2):
        m.box([x0, 8.6, 21.8], [x0 + 0.8, 13.2, 22.6], dark)
    m.box([3.6, 9.2, 16.0], [12.4, 13.2, 22.8], solid("2a2a2c", n=3))                     # black box
    m.box([1.4, 14.0, 11.4], [14.6, 19.6, 23.2], crate("dcd6c4", "8a8a86", "7a7a78"))     # big case
    m.cyl_x(8, 22.1, 17.3, 2.7, 2.0, 14.0, canvas("6e6a42", n=5), ends=roll_end("6e6a42", "4a4630"))
    cord = solid("9a7a48", n=4, edge=0)
    for x0 in (4.6, 10.8):
        m.box([x0, 19.2, 14.6], [x0 + 0.6, 24.9, 20.0], cord)                                # cords round the roll
        m.box([x0, 13.8, 11.2], [x0 + 0.6, 19.8, 23.4], cord)                                # cords round the case
    for (x0, x1) in ((-1.8, 1.6), (14.4, 17.8)):                                           # side cases
        m.box([x0, 6.4, 12.4], [x1, 13.0, 21.2], crate("d8d2c0", "8a8a86", "7a7a78"))
    m.box([7.0, 11.8, 22.8], [9.0, 12.8, 23.4], solid("b83a2a", n=3))                     # tail light

    m.display = {
        "gui": {"rotation": [25, 135, 0], "translation": [0, -1, 0], "scale": [0.36, 0.36, 0.36]},
        "ground": {"scale": [0.3, 0.3, 0.3]},
        "fixed": {"rotation": [0, 90, 0], "scale": [0.45, 0.45, 0.45]},
    }
    return m


# ----------------------------------------------------------------------------
def truck():
    """Half-scale model (display entity scales it x2).  Brown bonnet truck with a
    green canvas canopy, armour plates on the bed and a log lashed to the bumper."""
    m = Model("truck", 256, 256)
    BROWN = "7a5638"
    brown = solid(BROWN, n=5)
    brown_d = solid("5e422c", n=4)
    dark = solid("2c2a28", n=3)
    steel = solid("6a6c6e", n=5)
    green = canvas("58683e", n=6)
    green_d = canvas("48562f", n=5)

    for cz in (-6.5, 20.0):
        for (x0, x1) in ((-0.8, 1.6), (14.4, 16.8)):
            m.ring_x((x0 + x1) / 2, 3.6, cz, 3.6, 1.0, x0, x1, tire("2e2a28"))
        for xp in (-0.8, 16.8):
            m.box([xp, 0.8, cz - 2.8], [xp, 6.4, cz + 2.8],
                  {"east": spoked_wheel("5a5c58", "6e706c", "3a3a3a", spokes=6), "west": spoked_wheel("5a5c58", "6e706c", "3a3a3a", spokes=6)},
                  density=2)
    m.box([-0.6, 3.1, -7.0], [16.6, 4.1, -6.0], dark)            # axles
    m.box([-0.6, 3.1, 19.5], [16.6, 4.1, 20.5], dark)
    for x0 in (3.0, 11.0):
        m.box([x0, 3.0, -12.0], [x0 + 2.0, 4.6, 28.0], dark)     # chassis rails
    m.box([-0.6, 2.4, -13.2], [16.6, 4.0, -12.0], steel)          # bumper
    m.cyl_x(8, 5.2, -14.4, 1.4, -2.6, 18.6, bark("5e4632"), ends=log_end())   # the log

    # bonnet + grille + lamps
    grille = pattern(["cccccccc", "cdcdcdcd", "cdcdcdcd", "cdcdcdcd", "cdcdcdcd", "cccccccc"],
                     {"c": "a8a8a0", "d": "2a2826"})
    louvre = pattern(["bbbbbbbb", "bdbdbdbd", "bbbbbbbb", "bbbbbbbb"], {"b": BROWN, "d": "4a3424"})
    m.box([3.4, 4.8, -12.6], [12.6, 10.4, -4.0],
          {"north": grille, "east": louvre, "west": louvre, "up": brown, "south": brown, "down": dark})
    m.box([4.0, 10.4, -12.4], [12.0, 11.2, -4.0], brown)
    for x0 in (1.4, 12.8):
        m.box([x0, 8.2, -12.2], [x0 + 1.8, 10.0, -10.4],
              {"north": lens("efe6c0", "9a9a96"), "south": metal("9a9a96"), "east": metal("9a9a96"),
               "west": metal("9a9a96"), "up": metal("9a9a96"), "down": metal("9a9a96")})
    # mudguards + running boards
    for (x0, x1) in ((-0.8, 3.2), (12.8, 16.8)):
        m.box([x0, 7.0, -10.6], [x1, 7.8, -2.6], brown_d)
        m.box([x0, 3.6, -12.2], [x1, 7.4, -11.4], brown_d, rot=([(x0 + x1) / 2, 7.0, -10.6], "x", 45))
        m.box([x0, 3.6, -2.6], [x1, 4.2, 4.6], dark)
    # cab
    cab_side = pattern(["bbbbbbbbbb", "bggggggbbb", "bggggggbbb", "bggggggbbb", "bbbbbbbbbb", "bbbbbbbbbb",
                        "bbbbbbbbkb", "bbbbbbbbbb", "bbbbbbbbbb", "bdddddddbb"],
                       {"b": BROWN, "g": "30383c", "k": "b0a070", "d": "5e422c"})
    cab_front = pattern(["bbbbbbbbbbbbbb", "bggggggbgggggb", "bggggggbgggggb", "bggggggbgggggb", "bbbbbbbbbbbbbb",
                         "bbbbbbbbbbbbbb", "bbbbbbbbbbbbbb", "bbbbbbbbbbbbbb", "bbbbbbbbbbbbbb", "bbbbbbbbbbbbbb"],
                        {"b": BROWN, "g": "3a4448"})
    m.box([0.8, 4.2, -4.0], [15.2, 15.4, 4.6],
          {"north": cab_front, "east": cab_side, "west": cab_side, "south": brown, "down": dark})
    m.box([0.6, 15.4, -4.4], [15.4, 16.2, 4.9], brown_d)

    # bed with armour plates
    m.box([-0.4, 4.2, 4.8], [16.4, 5.4, 29.6], planks("8a6a44"))
    plate = pattern(["ssssssssssssssssssss", "sdsssssssdssssssssds", "ssssssssssssssssssss", "ssssssssssssssssssss",
                     "sssssssssssssssssssd"], {"s": "6a6c6e", "d": "4a4c4e"})
    m.box([-0.6, 5.4, 4.8], [0.4, 9.8, 29.6], plate)
    m.box([15.6, 5.4, 4.8], [16.6, 9.8, 29.6], plate)
    m.box([-0.4, 5.4, 28.8], [16.4, 8.4, 29.6], planks("7a5a3a"))
    # canopy
    m.box([-0.4, 9.8, 5.0], [0.4, 18.2, 29.2], green)
    m.box([15.6, 9.8, 5.0], [16.4, 18.2, 29.2], green)
    m.box([0.4, 5.4, 4.9], [15.6, 18.2, 5.6], green_d)                                    # front wall
    m.box([1.6, 19.6, 5.0], [14.4, 20.8, 29.2], green)                                    # roof
    m.box([-0.4, 17.4, 5.0], [3.4, 19.4, 29.2], green, rot=([1.5, 18.4, 17], "z", 22.5))    # shoulders
    m.box([12.6, 17.4, 5.0], [16.4, 19.4, 29.2], green, rot=([14.5, 18.4, 17], "z", -22.5))
    m.box([0.6, 18.0, 29.2], [15.4, 19.6, 30.2], green_d)                                 # rolled rear flap
    for x0 in (-0.2, 14.8):
        m.box([x0, 4.4, 29.6], [x0 + 1.4, 5.2, 30.0], solid("a02a20", n=3))

    m.display = {"gui": {"rotation": [25, 135, 0], "scale": [0.36, 0.36, 0.36]}}
    return m


# ----------------------------------------------------------------------------
def cannon():
    """Old museum field gun on a wooden carriage.  Muzzle toward -Z.  Crates of
    liquid gunpowder are lashed to the trail end (+Z) with a fuse."""
    m = Model("cannon", 256, 256)
    wood = planks("7a5a38")
    wood_d = planks("5e4430")
    bronze = metal("9a7a48")
    iron = solid("3e3e40", n=3)
    for xw in (-3.0, 19.0):
        m.ring_x(xw, 8.0, 8.0, 8.0, 1.0, xw - 1.0, xw + 1.0, solid("3a3a3a", n=3, edge=0))
        m.box([xw, 0.4, 0.4], [xw, 15.6, 15.6], {"east": cartwheel(), "west": cartwheel()}, density=1.5)
    m.box([-4.0, 7.3, 7.3], [20.0, 8.7, 8.7], iron)                              # axle
    for x0 in (4.6, 10.2):                                                         # carriage cheeks
        m.box([x0, 7.0, -1.0], [x0 + 1.2, 12.0, 14.0], wood)
    m.box([6.0, 7.6, 7.0], [10.0, 10.8, 29.0], wood_d, rot=([8, 9.2, 8.0], "x", 22.5))   # trail
    # barrel
    m.cyl_z(8, 12.2, 0, 2.2, -14.0, 12.0, bronze)
    m.cyl_z(8, 12.2, -13.3, 2.7, -14.2, -12.4, bronze)                            # muzzle swell
    m.cyl_z(8, 12.2, 11, 2.6, 10.0, 12.6, bronze)                                  # breech ring
    m.box([7.2, 11.4, 12.6], [8.8, 13.0, 14.0], bronze)                           # cascabel
    m.box([4.2, 11.4, 3.6], [11.8, 12.8, 5.0], bronze)                            # trunnions
    m.box([6.6, 14.2, -14.0], [9.4, 14.6, -13.0], iron)                            # sight
    # crates of liquid gunpowder on the trail end + fuse
    box = crate("8a6a44", "4a3a2a", "3a3a3a")
    m.box([2.8, 2.6, 21.0], [8.2, 7.6, 26.6], box)
    m.box([8.0, 2.4, 20.2], [13.2, 7.2, 25.8], box)
    m.box([5.0, 7.4, 20.8], [11.0, 11.4, 26.0], box)
    m.box([4.8, 7.2, 21.6], [5.4, 11.8, 22.2], solid("6e5a3a", n=2, edge=0))        # rope
    m.box([10.6, 7.2, 21.6], [11.2, 11.8, 22.2], solid("6e5a3a", n=2, edge=0))
    m.box([7.8, 11.4, 23.2], [8.2, 13.8, 23.6], solid("1e1e1e", n=0, edge=0))       # fuse
    m.display = {"gui": {"rotation": [25, 135, 0], "scale": [0.3, 0.3, 0.3]}}
    return m


# ----------------------------------------------------------------------------
def baby():
    m = Model("baby", 64, 64)
    cloth = solid("ece6da", n=4, edge=0.9)
    trim = solid("e4c4c0", n=2)
    face = pattern(["tttttt", "tsssst", "tsesst", "tsssst", "tssmst", "tttttt"],
                   {"t": "ece6da", "s": "f4d4c0", "e": "5a4638", "m": "e0a090"})
    m.box([6.0, 6.0, 4.0], [10.0, 9.6, 12.4], {"north": face, "south": cloth, "east": cloth, "west": cloth, "up": cloth, "down": cloth},
          density=1.5)
    m.box([5.6, 5.6, 3.4], [10.4, 10.2, 5.2], {"south": cloth, "east": cloth, "west": cloth, "up": cloth, "down": cloth})
    m.box([5.8, 7.4, 7.0], [10.2, 8.2, 9.0], trim)
    m.display = {
        "thirdperson_righthand": {"rotation": [0, 90, 0], "translation": [-2.5, 3.5, 3], "scale": [0.9, 0.9, 0.9]},
        "thirdperson_lefthand": {"rotation": [0, 90, 0], "translation": [-2.5, 3.5, 3], "scale": [0.9, 0.9, 0.9]},
        "gui": {"rotation": [30, 45, 0], "scale": [1.0, 1.0, 1.0]},
        "ground": {"scale": [0.6, 0.6, 0.6]},
    }
    return m


def rifle(name, stock="6e4a2c", metal_col="3a3c3e", scope=False, suppressor=False, length=20):
    """Long gun built along Z with the muzzle at -Z."""
    m = Model(name, 64, 64)
    wood = planks(stock)
    steel = solid(metal_col, n=3, edge=0.9)
    z_end = 8 + length / 2
    z_muz = 8 - length / 2
    m.box([7.4, 5.2, z_end - 7.0], [8.6, 8.0, z_end], wood)                        # butt stock
    m.box([7.5, 6.4, z_end - 10.0], [8.5, 7.8, z_end - 7.0], wood)                 # wrist
    m.box([7.3, 7.0, z_end - 14.0], [8.7, 8.6, z_end - 9.5], steel)                # receiver
    m.box([7.5, 6.6, z_muz + 3.0], [8.5, 7.6, z_end - 12.0], wood)                 # fore-end
    m.box([7.7, 7.6, z_muz + 1.0], [8.3, 8.2, z_end - 13.0], steel)                # barrel
    m.box([7.6, 5.8, z_end - 12.0], [8.4, 7.0, z_end - 10.6], steel)               # trigger guard / mag
    if scope:
        m.box([7.4, 8.6, z_end - 16.0], [8.6, 9.8, z_end - 9.0], steel)
        m.box([7.2, 8.4, z_end - 16.6], [8.8, 10.0, z_end - 15.4], steel)
    if suppressor:
        m.box([7.3, 7.1, z_muz - 3.0], [8.7, 8.7, z_muz + 2.0], solid("4a4a48", n=3))
    else:
        m.box([7.6, 7.5, z_muz], [8.4, 8.3, z_muz + 1.0], steel)
    # held like a rifle: stock at the shoulder, muzzle forward
    m.display = {
        "thirdperson_righthand": {"rotation": [0, 0, 0], "translation": [0, 1.0, -2.0], "scale": [1.0, 1.0, 1.0]},
        "thirdperson_lefthand": {"rotation": [0, 0, 0], "translation": [0, 1.0, -2.0], "scale": [1.0, 1.0, 1.0]},
        "gui": {"rotation": [0, 90, -45], "scale": [0.7, 0.7, 0.7]},
        "ground": {"scale": [0.5, 0.5, 0.5]},
    }
    return m


def revolver():
    m = Model("canon", 32, 32)
    steel = solid("5a5c5e", n=3, edge=0.9)
    wood = planks("6a4428")
    m.box([7.5, 7.4, 3.0], [8.5, 8.4, 8.0], steel)          # barrel (muzzle -Z)
    m.box([7.2, 6.8, 8.0], [8.8, 8.8, 10.4], steel)         # cylinder
    m.box([7.4, 7.0, 10.4], [8.6, 8.6, 11.2], steel)
    m.box([7.4, 4.2, 10.6], [8.6, 7.2, 12.2], wood, rot=([8, 7, 11], "x", -22.5))   # grip
    m.display = {
        "thirdperson_righthand": {"rotation": [0, 0, 0], "translation": [0, 0.5, -1.0], "scale": [1, 1, 1]},
        "thirdperson_lefthand": {"rotation": [0, 0, 0], "translation": [0, 0.5, -1.0], "scale": [1, 1, 1]},
        "gui": {"rotation": [0, 90, 0], "scale": [1.4, 1.4, 1.4]},
        "ground": {"scale": [0.8, 0.8, 0.8]},
    }
    return m


def small(name, parts, display=None, size=64):
    m = Model(name, size, size)
    for frm, to, painter in parts:
        m.box(frm, to, painter)
    m.display = display or {}
    return m


def props():
    held = {
        "thirdperson_righthand": {"rotation": [0, 0, 0], "translation": [0, 2.0, -1.0], "scale": [0.8, 0.8, 0.8]},
        "thirdperson_lefthand": {"rotation": [0, 0, 0], "translation": [0, 2.0, -1.0], "scale": [0.8, 0.8, 0.8]},
        "ground": {"scale": [0.6, 0.6, 0.6]},
    }
    out = []
    out.append(small("mug", [([6.5, 5, 6.5], [9.5, 9, 9.5], metal("b0b0ae")),
                             ([9.5, 6, 7.6], [10.4, 8.4, 8.4], metal("a0a09e"))], held))
    out.append(small("bottle", [([7, 4, 7], [9, 9, 9], glass("3a6a3a", 210)),
                                ([7.5, 9, 7.5], [8.5, 11, 8.5], glass("3a6a3a", 220)),
                                ([7.6, 11, 7.6], [8.4, 11.8, 8.4], solid("a08058", 2, edge=0))], held))
    out.append(small("wine", [([7, 4, 7], [9, 10, 9], glass("5a1a24", 230)),
                              ([7.5, 10, 7.5], [8.5, 12.5, 8.5], glass("5a1a24", 230)),
                              ([7.4, 12.5, 7.4], [8.6, 13.2, 8.6], solid("c8b890", 2, edge=0))], held))
    out.append(small("grenade", [([7.5, 3, 7.5], [8.5, 9, 8.5], planks("8a6a44")),
                                 ([6.8, 9, 6.8], [9.2, 12, 9.2], solid("4a5040", 3))], held))
    radio_face = pattern(["kkkkkkkk", "kddkdkdk", "kkkkkkkk", "kwwwwkgk", "kwwwwkkk", "kkkkkkkk"],
                         {"k": "3a3e36", "d": "b0b0a8", "w": "c8c0a0", "g": "6a8a4a"})
    out.append(small("radio", [([3, 0, 5], [13, 7, 11], {"north": radio_face, "south": solid("3a3e36"), "east": solid("3a3e36"),
                                                        "west": solid("3a3e36"), "up": solid("40443c"), "down": solid("2a2c28")}),
                               ([11.6, 7, 9.6], [12, 18, 10], solid("8a8a88", 2, edge=0))]))
    out.append(small("board", [([-4, 0, 0], [20, 1, 12], planks("9a7a52"))]))
    return out


def cannon_barrel():
    m = Model("cannon_barrel", 128, 64)
    bronze = metal("9a7a48")
    m.cyl_z(8, 8, 0, 2.2, -5.0, 21.0, bronze)
    m.cyl_z(8, 8, -4.3, 2.7, -5.2, -3.4, bronze)
    m.cyl_z(8, 8, 20, 2.6, 19.0, 21.6, bronze)
    m.box([4.2, 7.2, 12.6], [11.8, 8.6, 14.0], bronze)
    m.display = {"ground": {"scale": [1, 1, 1]}}
    return m


def binoculars():
    m = Model("binoculars", 32, 32)
    blk = solid("2a2a2a", n=2, edge=0.9)
    for x0 in (5.6, 8.6):
        m.box([x0, 7, 4], [x0 + 1.8, 8.8, 9], blk)
    m.box([7.4, 7.4, 5], [8.6, 8.4, 7], solid("4a4a4a"))
    m.display = {
        "thirdperson_righthand": {"rotation": [0, 0, 0], "translation": [0, 2.0, -1.0], "scale": [0.8, 0.8, 0.8]},
        "thirdperson_lefthand": {"rotation": [0, 0, 0], "translation": [0, 2.0, -1.0], "scale": [0.8, 0.8, 0.8]},
    }
    return m


def blade(name, axe=False):
    m = Model(name, 32, 32)
    handle = planks("6a4a2c")
    steel = metal("c8c8c8")
    if axe:
        m.box([7.4, 7.4, 2], [8.6, 8.6, 14], handle)
        m.box([7.6, 8.6, 1.5], [8.4, 12.0, 5.0], steel)
    else:
        m.box([7.5, 7.4, 9], [8.5, 8.6, 13], handle)
        m.box([7.8, 7.6, 1.5], [8.2, 8.4, 9], steel)
    m.display = {
        "thirdperson_righthand": {"rotation": [0, 0, 0], "translation": [0, 1.0, -1.5], "scale": [1, 1, 1]},
        "thirdperson_lefthand": {"rotation": [0, 0, 0], "translation": [0, 1.0, -1.5], "scale": [1, 1, 1]},
    }
    return m


ALL = [hermes, truck, cannon, baby, cannon_barrel, binoculars, lambda: blade("knife"), lambda: blade("axe", True),
       lambda: rifle("srifle", scope=True, length=22),
       lambda: rifle("flute", scope=True, suppressor=True, length=22),
       lambda: rifle("rifle", stock="7a5030", length=22), revolver]


def variant(name, parent, display):
    """Same geometry, different hand pose (e.g. a rifle carried muzzle-up)."""
    import json
    mdl = os.path.join(RP, "assets", "kino", "models", "item", name + ".json")
    with open(mdl, "w") as fh:
        json.dump({"parent": f"kino:item/{parent}", "display": display}, fh, indent=1)
    with open(os.path.join(RP, "assets", "kino", "items", name + ".json"), "w") as fh:
        json.dump({"model": {"type": "minecraft:model", "model": f"kino:item/{name}"}}, fh, indent=2)


CARRY = {
    "thirdperson_righthand": {"rotation": [180, 0, 0], "translation": [0, 1.5, 1.0], "scale": [1.0, 1.0, 1.0]},
    "thirdperson_lefthand": {"rotation": [180, 0, 0], "translation": [0, 1.5, 1.0], "scale": [1.0, 1.0, 1.0]},
}


def main():
    made = []
    for fn in ALL:
        m = fn()
        m.write(RP)
        made.append(f"{m.name}({len(m.elements)} el, {m.W}x{m.H})")
    for m in props():
        m.write(RP)
        made.append(f"{m.name}({len(m.elements)} el)")
    variant("flute_carry", "flute", CARRY)
    variant("rifle_carry", "rifle", CARRY)
    variant("srifle_carry", "srifle", CARRY)
    print("models:", ", ".join(made))


if __name__ == "__main__":
    main()
