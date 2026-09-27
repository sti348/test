"""All character skins for the film.  Run:  python3 tools/skins.py"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from skinlib import Skin, hexc, mirror_rows, rows, sheet  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "resourcepack", "assets", "kino", "textures", "entity", "skins")


# --------------------------------------------------------------------------
# Kino  (from the illustration: tan long coat, brown cap with fur back and
# goggles, black hair, white collar, dark sweater, gun belt, brown boots)
# --------------------------------------------------------------------------
def kino():
    P = {
        # hair
        "H": hexc("26232b"), "h": hexc("3e3a46"), "j": hexc("17151b"),
        # skin / face
        "S": hexc("f3d8c0"), "s": hexc("e2bea2"), "m": hexc("e2b2a2"),
        "E": hexc("5a463a"), "e": hexc("8e7462"), "L": hexc("1c1618"),
        # cap
        "c": hexc("62483a"), "C": hexc("7a5c4a"), "k": hexc("4a362c"), "v": hexc("3e2c24"),
        "w": hexc("ece8de"), "f": hexc("d0cabc"),
        "G": hexc("343c42"), "g": hexc("9aaeb8"), "M": hexc("a8a8a4"),
        "r": hexc("54392a"), "y": hexc("c4a456"),
        # coat
        "T": hexc("cfb068"), "t": hexc("b69852"), "u": hexc("977a3c"), "l": hexc("dfc684"),
        # collar / sweater
        "O": hexc("eeeeea"), "o": hexc("d0d0cc"),
        "D": hexc("3c3e3a"), "d": hexc("30322f"),
        # belts / holster / gun
        "B": hexc("70482c"), "x": hexc("563622"), "A": hexc("825634"), "a": hexc("664228"),
        "I": hexc("9a9a9c"), "i": hexc("646466"),
        # trousers / boots / gloves
        "P": hexc("40413e"), "p": hexc("555652"),
        "Q": hexc("604432"), "q": hexc("463024"), "z": hexc("2c221c"),
        "N": hexc("4a3a30"), "n": hexc("3a2c24"),
    }
    s = Skin("kino", slim=True, noise={
        "H": 4, "T": 3, "t": 3, "l": 2, "u": 2, "D": 4, "d": 3, "P": 4, "p": 3,
        "c": 5, "w": 5, "f": 4, "Q": 5, "q": 4, "B": 4, "N": 4, "A": 4, "S": 1.5, "s": 1.5,
    })

    # ---------------- head (base) ----------------
    s.paint("head", "front", """
        HHHHHHHH
        HHHHHHHH
        HHHhHHHH
        HHsHHsHH
        HLLSSLLH
        HEeSSeEH
        HSSSSSSH
        HsSmmSsH
    """, P)
    right = rows("""
        HHHHHHHH
        HHHHhHHH
        HHhHHHHH
        HHHHHhHH
        HhHHHHHH
        HHHHhHHH
        HHHHHssH
        jHHHHsSH
    """)
    s.paint("head", "right", right, P)
    s.paint("head", "left", mirror_rows(right), P)
    s.paint("head", "back", """
        HHHHHHHH
        HHhHHHHH
        HHHHHhHH
        HhHHHHHH
        HHHHHHhH
        HHHhHHHH
        HhHHHHjH
        jHjHHjHj
    """, P)
    s.paint("head", "top", """
        HHHHHHHH
        HHhHHHHH
        HHHHHhHH
        HHHHHHHH
        HhHHHHHH
        HHHHhHHH
        HHHHHHHH
        HHHHHHHH
    """, P)
    s.paint("head", "bottom", """
        HsSSSSsH
        HSSSSSSH
        HSSSSSSH
        HsSSSSsH
        HssssssH
        HHssssHH
        HHHHHHHH
        HHHHHHHH
    """, P)

    # ---------------- head (hat layer: cap + goggles) ----------------
    s.paint("head", "front", """
        rGgMMGgr
        rGGMMGGr
        vvvvvvvv
        ........
        ........
        ........
        ........
        ........
    """, P, layer=1)
    cap_r = rows("""
        wwwwccCc
        rrrrrryr
        wfwwkkkk
        fwwf....
        ........
        ........
        ........
        ........
    """)
    s.paint("head", "right", cap_r, P, layer=1)
    s.paint("head", "left", mirror_rows(cap_r), P, layer=1)
    s.paint("head", "back", """
        wwwwwwww
        rrrrrrrr
        wfwwwfww
        fwwfwwfw
        .f....f.
        ........
        ........
        ........
    """, P, layer=1)
    s.paint("head", "top", """
        wwwwwwww
        wfwwfwww
        wwwwwwfw
        cccccccc
        cCcccCcc
        ccccCccc
        cccccccc
        kcccccck
    """, P, layer=1)

    # ---------------- body (base) ----------------
    s.paint("body", "front", """
        DDOOOODD
        DDOddODD
        DDDDDDDD
        DDDdDDDD
        DDDdDDDD
        DDDdDDDD
        DDDdDDDD
        DDDdDDDD
        BBByBBBB
        PPPPPxxP
        PIxxxPPP
        AAPpPPPP
    """, P)
    side = ["DDDD"] * 8 + ["BBBB"] + ["PPPP"] * 3
    s.paint("body", "right", side, P)
    s.paint("body", "left", side, P)
    s.paint("body", "back", ["DDDDDDDD"] * 8 + ["BBBBBBBB"] + ["PPPPPPPP"] * 3, P)
    s.paint("body", "top", ["DDDDDDDD"] * 4, P)
    s.paint("body", "bottom", ["PPPPPPPP"] * 4, P)

    # ---------------- body (jacket layer: the long coat) ----------------
    s.paint("body", "front", """
        tll..llt
        tlu..ult
        Tl....lT
        Tu....uT
        TT....uT
        Tu....TT
        tu....ut
        Tu....uT
        Tu....uT
        TT....uT
        tu....ut
        Tu....TT
    """, P, layer=1)
    coat_side = rows("""
        lTTT
        TTTl
        TtTT
        TTTT
        TtTT
        TTTT
        TtTT
        TTTt
        TtTT
        TTTT
        ttTT
        TtTT
    """)
    s.paint("body", "right", coat_side, P, layer=1)
    s.paint("body", "left", mirror_rows(coat_side), P, layer=1)
    s.paint("body", "back", """
        llllllll
        tTTTTTTt
        TTTTTTTT
        TTtTTTTT
        TTTTTtTT
        TTTTTTTT
        TTTuTTTT
        TtTuTTTT
        TTTuTTtT
        TTTuTTTT
        TtTuTTTT
        tTTuTTTt
    """, P, layer=1)
    s.paint("body", "top", """
        llllllll
        TTTTTTTT
        TTTTTTTT
        TTTTTTTT
    """, P, layer=1)

    # ---------------- arms (slim) ----------------
    arm_front = rows("""
        TTT
        TlT
        TTT
        TTt
        TTT
        tTT
        TTT
        TtT
        lll
        ttt
        NNN
        nNn
    """)
    arm_out = rows("""
        TTTT
        TlTT
        TTTT
        TTtT
        TTTT
        tTTT
        TTTT
        TTtT
        llll
        tttt
        NNNN
        nNnN
    """)
    arm_in = rows("""
        tttt
        tTtt
        tttt
        ttut
        tttt
        uttt
        tttt
        ttut
        llll
        uuuu
        NNNN
        nnnn
    """)
    arm_back = rows("""
        TtT
        TTT
        tTT
        TTT
        TTt
        TTT
        tTT
        TTT
        lll
        ttt
        NnN
        nnn
    """)
    s.paint("rarm", "front", arm_front, P)
    s.paint("rarm", "right", arm_out, P)
    s.paint("rarm", "left", arm_in, P)
    s.paint("rarm", "back", arm_back, P)
    s.paint("rarm", "top", ["TTT"] * 4, P)
    s.paint("rarm", "bottom", ["nnn"] * 4, P)
    # sleeve overlay: loose coat sleeve + wide turned-back cuff
    def sleeve(art):
        r = art[:]
        return [row if k < 10 else "." * len(row) for k, row in enumerate(r)]
    s.paint("rarm", "front", sleeve(arm_front), P, layer=1)
    s.paint("rarm", "right", sleeve(arm_out), P, layer=1)
    s.paint("rarm", "left", sleeve(arm_in), P, layer=1)
    s.paint("rarm", "back", sleeve(arm_back), P, layer=1)
    s.paint("rarm", "top", ["TTT"] * 4, P, layer=1)
    s.mirror_to("rarm", "larm", 0)
    s.mirror_to("rarm", "larm", 1)

    # ---------------- legs ----------------
    rleg_front = rows("""
        PAAP
        PAaP
        PaAP
        PAAP
        PiPP
        PPPP
        PPpP
        PPPP
        pppp
        QQQQ
        QqQQ
        zzzz
    """)
    rleg_out = rows("""
        PPPA
        PPPa
        PpPA
        PPPA
        PPPP
        PPPP
        PpPP
        PPPP
        pppp
        QQQQ
        QQqQ
        zzzz
    """)
    leg_in = rows("""
        PPPP
        PPPP
        PPpP
        PPPP
        PPPP
        PpPP
        PPPP
        PPPP
        pppp
        QQQQ
        QqQQ
        zzzz
    """)
    leg_back = rows("""
        PPPP
        PPPP
        PpPP
        PPPP
        PPPP
        PPpP
        PPPP
        PPPP
        pppp
        QQQQ
        qQQq
        zqqz
    """)
    s.paint("rleg", "front", rleg_front, P)
    s.paint("rleg", "right", rleg_out, P)
    s.paint("rleg", "left", leg_in, P)
    s.paint("rleg", "back", leg_back, P)
    s.paint("rleg", "top", ["PPPP"] * 4, P)
    s.paint("rleg", "bottom", ["zzzz"] * 4, P)
    lleg_front = rows("""
        PPPP
        PPPP
        PpPP
        PPPP
        PPPP
        PPPP
        PPpP
        PPPP
        pppp
        QQQQ
        QQqQ
        zzzz
    """)
    s.paint("lleg", "front", lleg_front, P)
    s.paint("lleg", "left", mirror_rows(leg_in), P)
    s.paint("lleg", "right", mirror_rows(leg_in), P)
    s.paint("lleg", "back", mirror_rows(leg_back), P)
    s.paint("lleg", "top", ["PPPP"] * 4, P)
    s.paint("lleg", "bottom", ["zzzz"] * 4, P)
    # coat skirt on the leg overlay (open at the front)
    skirt_out = ["TTTT", "TtTT", "TTTT", "TTtT", "tTTT", "TTTT", "TTtT", "TTTT", "uuuu", "....", "....", "...."]
    skirt_back = ["TTTT", "TTtT", "TTTT", "tTTT", "TTTT", "TtTT", "TTTT", "TTTt", "uuuu", "....", "....", "...."]
    s.paint("rleg", "front", ["T...", "T...", "t...", "T...", "T...", "t...", "T...", "T...", "u...", "....", "....", "...."], P, layer=1)
    s.paint("rleg", "right", skirt_out, P, layer=1)
    s.paint("rleg", "back", skirt_back, P, layer=1)
    s.paint("lleg", "front", ["...T", "...T", "...t", "...T", "...T", "...t", "...T", "...T", "...u", "....", "....", "...."], P, layer=1)
    s.paint("lleg", "left", mirror_rows(skirt_out), P, layer=1)
    s.paint("lleg", "back", mirror_rows(skirt_back), P, layer=1)
    return s



# --------------------------------------------------------------------------
# Supporting cast.  Heads are explicit pixel art; bodies are built from row
# "columns" (one symbol per row) plus hand-placed details.
# --------------------------------------------------------------------------
def column(s, part, seq, pal, layer=0, faces=("front", "back", "right", "left"), top=None, bottom=None):
    for f in faces:
        x0, y0, w, h = s.rect(part, f, layer)
        s.paint(part, f, [ch * w for ch in seq], pal, layer)
    x0, y0, w, h = s.rect(part, "top", layer)
    if top is not False:
        s.paint(part, "top", [(top or seq[0]) * w] * h, pal, layer)
    if bottom is not False:
        s.paint(part, "bottom", [(bottom or seq[-1]) * w] * h, pal, layer)


def put(s, part, face, pts, ch, pal, layer=0):
    """Place single pixels: pts = [(col,row), ...] inside a face."""
    x0, y0, w, h = s.rect(part, face, layer)
    col = pal[ch]
    if len(col) == 3:
        col = (*col, 255)
    for (i, j) in pts:
        s.px[x0 + i, y0 + j] = col


BASE_NOISE = {"H": 4, "h": 3, "A": 4, "a": 3, "P": 4, "p": 3, "F": 3, "V": 4, "D": 4, "d": 3,
              "B": 4, "U": 3, "G": 6, "g": 5, "S": 1.5, "s": 1.5, "C": 4, "X": 3, "w": 3}

HEADS = {
    "short": dict(
        front="""
            HHHHHHHH
            HHHhHHHH
            HhSSSSHH
            SLLSSLLS
            SWESSEWS
            SSSnnSSS
            SSSmmSSS
            sSSSSSSs""",
        right="""
            HHHHHHHH
            HHhHHHHH
            HHHHHHHH
            HHHHHHSS
            HHHHsHSS
            HHHHssSS
            HHHSSSSS
            HHSSSSSs""",
        back="""
            HHHHHHHH
            HHhHHHHH
            HHHHHHhH
            HhHHHHHH
            HHHHhHHH
            HHHHHHHH
            HHhHHHHH
            HHssssHH""",
        top="""
            HHHHHHHH
            HHhHHHHH
            HHHHHhHH
            HHHHHHHH
            HhHHHHHH
            HHHHhHHH
            HHHHHHHH
            HHHHHHHH""",
    ),
    "swept": dict(
        front="""
            HHHHHHHH
            HhHHHHhH
            hSSSSSSh
            SLLSSLLS
            SWESSEWS
            SsSnnSsS
            SSsmmsSS
            sSSSSSSs""",
        right="""
            HHHHHHHH
            HhHHHHHH
            HHHHhHHH
            HHhHHHSS
            HHHHsHSS
            HhHHssSS
            HHHSSSSS
            HHSSSSSs""",
        back="""
            HHHHHHHH
            HhHHhHHH
            HHHHHHhH
            HhHHHHHH
            HHHhHHHH
            HHHHHhHH
            HhHHHHHH
            HHssssHH""",
        top="""
            HhHHhHHH
            HhHHhHHh
            HhHHhHHh
            HhHHhHHh
            HhHHhHHh
            hHHhHHhH
            HHHHHHHH
            HHHHHHHH""",
    ),
    "messy": dict(
        front="""
            HHHHHHHH
            HHhHHHhH
            HHHHHHHH
            SHSSHSHS
            SWESSEWS
            SSSnnSSS
            SSSmmSSS
            sSSSSSSs""",
        right="""
            HHHHHHHH
            HHhHHHHH
            HHHHHhHH
            HHHHHHHS
            HHHHsHSS
            HHHHssSS
            HHHSSSSS
            HHHSSSSs""",
        back="""
            HHHHHHHH
            HhHHHhHH
            HHHHHHHH
            HHhHHHHH
            HHHHHhHH
            HHHHHHHH
            HhHHhHHH
            HHHsHHsH""",
        top="""
            HHHHHHHH
            HhHHHhHH
            HHHHHHHH
            HHhHHHhH
            HHHHHHHH
            HhHHhHHH
            HHHHHHHH
            HHHHHHHH""",
    ),
    "buzz": dict(
        front="""
            HHHHHHHH
            HhHHhHHH
            HSSSSSSH
            SLLSSLLS
            SWESSEWS
            SSSnnSSS
            SSSmmSSS
            sSSSSSSs""",
        right="""
            HHHHHHHH
            HHHhHHHH
            HHHHHHHS
            HHHHHHSS
            HHHHsSSS
            HHHHssSS
            HHHSSSSS
            SSSSSSSs""",
        back="""
            HHHHHHHH
            HHHhHHHH
            HhHHHHHH
            HHHHHhHH
            HHHHHHHH
            HHhHHHHH
            HHHHHHHH
            SSSSSSSS""",
        top="""
            HHHHHHHH
            HHhHHHHH
            HHHHHhHH
            HHHHHHHH
            HhHHHHHH
            HHHHhHHH
            HHHHHHHH
            HHHHHHHH""",
    ),
    "bun": dict(
        front="""
            HHHHHHHH
            HHHHHhHH
            HhHHSSHH
            HHSSSSSH
            HLLSSLLH
            HWESSEWH
            HSSSSSSH
            HsSmmSsH""",
        right="""
            HHHHHHHH
            HHHHHHHH
            HHhHHHHH
            HHHHHHHH
            HHHHHHHH
            HHHHHHSH
            HHHHHSSH
            HHHHSSSH""",
        back="""
            HHHHHHHH
            HhHHHHHH
            HHHHHhHH
            HHHHHHHH
            HHhHHHHH
            HHHHHHHH
            HHHHHHhH
            HHHHHHHH""",
        top="""
            HHHHHHHH
            HHhHHHHH
            HHHHHhHH
            HHHHHHHH
            HhHHHHHH
            HHHHhHHH
            HHHHHHHH
            HHHHHHHH""",
    ),
}


def paint_head(s, style, pal, beard=False, mustache=False, stubble=False):
    h = HEADS[style]
    front = rows(h["front"])
    right = rows(h["right"])
    if beard:
        front[5] = "B" + front[5][1:7] + "B"
        front[6] = "BBSmmSBB"
        front[7] = "BBBBBBBB"
        right[5] = right[5][:4] + "BBSS"
        right[6] = right[6][:3] + "BBBBB"
        right[7] = right[7][:2] + "BBBBBB"
    elif mustache:
        front[6] = "SSBBBBSS"
    elif stubble:
        front[6] = "SbSmmSbS"
        front[7] = "sbbbbbbs"
    s.paint("head", "front", front, pal)
    s.paint("head", "right", right, pal)
    s.paint("head", "left", mirror_rows(right), pal)
    s.paint("head", "back", h["back"], pal)
    s.paint("head", "top", h["top"], pal)
    s.fill("head", "bottom", "S", pal)


def pal_person(skin="e8c4a4", skin_shade="d0a684", hair="3a2a22", hair_hi="54402f", eye="4a3a2c", brow=None, **kw):
    P = {
        "S": hexc(skin), "s": hexc(skin_shade), "n": hexc(skin_shade), "m": hexc("b08470"),
        "o": tuple((a + b) // 2 for a, b in zip(hexc(skin), hexc(skin_shade))),
        "W": hexc("f0f0ec"), "E": hexc(eye), "L": hexc(brow or hair),
        "H": hexc(hair), "h": hexc(hair_hi), "B": hexc(hair), "b": hexc(skin_shade),
        "R": hexc("8a1a1a"), "r": hexc("5e1010"),
    }
    for k, v in kw.items():
        P[k] = hexc(v)
    return P


def body_suit(s, P):
    # grey three-button suit, white shirt, dark tie, black shoes
    s.paint("body", "front", """
        AlWWWWlA
        AAlKKlAA
        AAlKKlAA
        AAAKKAAA
        AAAAkAAA
        AAAAAAAA
        aAAAkAAa
        AAAAAAAA
        AAAAkAAA
        AAAAAAAA
        aAAaAAAa
        aaaaaaaa
    """, P)
    column(s, "body", ["l"] + ["A"] * 10 + ["a"], P, faces=("back", "right", "left"))
    put(s, "body", "back", [(3, 8), (3, 9), (3, 10), (3, 11)], "a", P)
    column(s, "rarm", ["A"] * 10 + ["W", "S"], P)
    column(s, "larm", ["A"] * 10 + ["W", "S"], P)
    column(s, "rleg", ["P"] * 10 + ["F", "f"], P)
    column(s, "lleg", ["P"] * 10 + ["F", "f"], P)
    put(s, "rleg", "front", [(0, 3), (0, 6)], "p", P)
    put(s, "lleg", "front", [(3, 3), (3, 6)], "p", P)


def body_retainer(s, P):
    # black stand-collar shirt with buttons, belt, loose dark trousers, boots
    s.paint("body", "front", """
        AAccccAA
        AAAAkAAA
        AaAAAAaA
        AAAAkAAA
        AAAAAAAA
        AaAAkAaA
        AAAAAAAA
        AAAAkAAA
        XXXXYXXX
        PPPPPPPP
        PpPPPPpP
        PPPPPPPP
    """, P)
    column(s, "body", ["c"] + ["A"] * 7 + ["X", "P", "P", "P"], P, faces=("back", "right", "left"))
    column(s, "rarm", ["A"] * 9 + ["a", "S", "S"], P)
    column(s, "larm", ["A"] * 9 + ["a", "S", "S"], P)
    column(s, "rleg", ["P", "P", "p", "P", "P", "P", "p", "P", "P", "F", "F", "f"], P)
    column(s, "lleg", ["P", "P", "P", "p", "P", "P", "P", "p", "P", "F", "F", "f"], P)
    # loose trouser overlay (a little wider at the calf)
    for leg in ("rleg", "lleg"):
        column(s, leg, ["."] * 5 + ["P", "P", "p", "P"] + ["."] * 3, P, layer=1, top=False, bottom=False)


def body_bare(s, P, boxers="U"):
    s.paint("body", "front", """
        SSSSSSSS
        SSSSSSSS
        SSSSSSSS
        SooSSooS
        SSSSSSSS
        SSSSSSSS
        SSSSSSSS
        SSSSSSSS
        SSSSSSSS
        VVVVVVVV
        UUUUUUUU
        UuUUUUuU
    """, P)
    column(s, "body", ["S"] * 9 + ["V", "U", "U"], P, faces=("back", "right", "left"))
    put(s, "body", "back", [(3, 3), (4, 4), (3, 6)], "o", P)
    column(s, "rarm", ["S"] * 12, P)
    column(s, "larm", ["S"] * 12, P)
    column(s, "rleg", ["U", "U", "u", "U"] + ["S"] * 7 + ["s"], P)
    column(s, "lleg", ["U", "U", "u", "U"] + ["S"] * 7 + ["s"], P)
    if boxers == "stripe":
        for leg, cols in (("rleg", (0, 2)), ("lleg", (1, 3))):
            for f in ("front", "back", "right", "left"):
                put(s, leg, f, [(c, r) for c in cols for r in range(4)], "u", P)


def body_traveler(s, P):
    # outdoor jacket over a vest, belt, field trousers, boots
    s.paint("body", "front", """
        AAcVVcAA
        AaVVVVaA
        AAVkVVAA
        AaVVVVaA
        AAVVkVAA
        AaVVVVaA
        AAVkVVAA
        AaVVVVaA
        AAXYXXAA
        AaPPPPaA
        AAPPPPAA
        aaPPPPaa
    """, P)
    column(s, "body", ["A"] * 11 + ["a"], P, faces=("back", "right", "left"))
    put(s, "body", "back", [(1, 3), (6, 3), (2, 7), (5, 7)], "a", P)
    column(s, "rarm", ["A"] * 8 + ["a", "A", "S", "S"], P)
    column(s, "larm", ["A"] * 8 + ["a", "A", "S", "S"], P)
    column(s, "rleg", ["P", "P", "p", "P", "P", "P", "P", "p", "F", "F", "F", "f"], P)
    column(s, "lleg", ["P", "P", "P", "p", "P", "P", "P", "p", "F", "F", "F", "f"], P)
    # pocket flaps on the thighs
    put(s, "rleg", "right", [(1, 3), (2, 3), (1, 4), (2, 4)], "p", P)
    put(s, "lleg", "left", [(1, 3), (2, 3), (1, 4), (2, 4)], "p", P)
    # jacket overlay (collar + hem)
    column(s, "body", ["A"] + ["."] * 10 + ["a"], P, layer=1, faces=("back", "right", "left"), top=False, bottom=False)
    s.paint("body", "front", ["AA....AA", "A......A"] + ["........"] * 9 + ["aa....aa"], P, layer=1)


def body_bandit(s, P):
    # patched brown/green field clothes, rope belt, grime
    s.paint("body", "front", """
        AAcccAAA
        AAAGAAAA
        AGGAAAaA
        AAGAAGGA
        AAAAAGAA
        aAAAAAAA
        AAGGAAAa
        AAAGAAAA
        XxXXxXXX
        PPPPgPPP
        PgPPPPPP
        PPPPPPgP
    """, P)
    column(s, "body", ["A", "A", "G", "A", "A", "a", "A", "G", "X", "P", "P", "P"], P, faces=("back", "right", "left"))
    put(s, "body", "back", [(2, 2), (3, 3), (5, 5), (6, 6)], "G", P)
    column(s, "rarm", ["A", "A", "G", "A", "A", "A", "a", "A", "A", "a", "S", "S"], P)
    column(s, "larm", ["A", "G", "A", "A", "a", "A", "A", "G", "A", "a", "S", "S"], P)
    column(s, "rleg", ["P", "P", "g", "P", "P", "P", "g", "P", "P", "F", "F", "f"], P)
    column(s, "lleg", ["P", "g", "P", "P", "P", "g", "P", "P", "P", "F", "F", "f"], P)


def body_dress(s, P):
    s.paint("body", "front", """
        DDSSSSDD
        DDDSSDDD
        DDDDDDDD
        DdDDDDdD
        DDDDDDDD
        DDDDDDDD
        DdDDDDdD
        xxxxxxxx
        DDDDDDDD
        DdDDDDdD
        DDDDDDDD
        DDdDDdDD
    """, P)
    column(s, "body", ["D"] * 7 + ["x"] + ["D"] * 4, P, faces=("back", "right", "left"))
    column(s, "rarm", ["D"] * 9 + ["d", "S", "S"], P)
    column(s, "larm", ["D"] * 9 + ["d", "S", "S"], P)
    column(s, "rleg", ["D", "D", "d", "D", "D", "D", "d", "D", "D", "D", "d", "F"], P)
    column(s, "lleg", ["D", "D", "D", "d", "D", "D", "D", "d", "D", "D", "d", "F"], P)
    for leg in ("rleg", "lleg"):  # flared skirt
        column(s, leg, ["."] * 3 + ["D", "D", "d", "D", "D", "D", "d", "D", "."], P, layer=1, top=False, bottom=False)
    # cream shawl over the shoulders
    s.paint("body", "front", ["ww....ww", "wwS..Sww", "w......w", "w......w"] + ["........"] * 8, P, layer=1)
    s.paint("body", "back", ["wwwwwwww", "wwwwwwww", "wwwwwwww", ".wwwwww."] + ["........"] * 8, P, layer=1)
    s.paint("body", "right", ["wwww", "wwww", "wwww", "ww.."] + ["...."] * 8, P, layer=1)
    s.paint("body", "left", ["wwww", "wwww", "wwww", "..ww"] + ["...."] * 8, P, layer=1)
    s.fill("body", "top", "w", P, layer=1)
    for arm in ("rarm", "larm"):
        column(s, arm, ["w", "w"] + ["."] * 10, P, layer=1, bottom=False)


def blood_face(s, P):
    put(s, "head", "front", [(1, 3), (2, 5), (5, 3), (6, 5), (3, 6), (4, 7), (6, 2), (1, 7)], "R", P)
    put(s, "head", "front", [(2, 3), (4, 5), (0, 6)], "r", P)


def leaf_wreath(s, P):
    s.paint("head", "front", ["GgG.GgGg", "g......G", "........", "........", "........", "........", "........", "........"], P, layer=1)
    s.paint("head", "back", ["gGgGGgGg", "G.gG.G.g"] + ["........"] * 6, P, layer=1)
    for f in ("right", "left"):
        s.paint("head", f, ["GgGGgGgG", ".G.g.G.."] + ["........"] * 6, P, layer=1)
    s.paint("head", "top", ["gG....Gg", "G......G", "g......g", "........", "........", "G......g", "g......G", "GgG..gGg"], P, layer=1)


def grime(s, P):
    put(s, "body", "front", [(2, 2), (5, 4), (1, 7), (6, 9)], "r", P)
    put(s, "rarm", "front", [(1, 5), (2, 8)], "R", P)
    put(s, "head", "front", [(0, 4), (7, 6)], "b", P)


def doctor(variant="suit"):
    P = pal_person(skin="e6c2a2", skin_shade="c9a080", hair="e4e2dc", hair_hi="c8c6c0", brow="d8d6d0", eye="52606a",
                   A="6e7074", a="5a5c60", l="84868a", W="efefeb", K="3a2a3a", k="2a2a2c",
                   P="646669", p="545659", F="242426", f="161618", U="d6d6d0", u="9a9aa0", V="c4c4be")
    name = {"suit": "doctor", "bare": "doctor_bare"}[variant]
    s = Skin(name, noise=BASE_NOISE)
    paint_head(s, "swept", P)
    if variant == "suit":
        body_suit(s, P)
    else:
        body_bare(s, P, boxers="stripe")
    return s


def woman():
    P = pal_person(skin="f2d6be", skin_shade="dcb89c", hair="6a4430", hair_hi="86583e", eye="5a3e2a",
                   brow="4a2e20", m="d6887a", D="56647a", d="46526a", x="3a4456", w="e8e0cc", F="4a3428")
    s = Skin("woman", slim=True, noise=BASE_NOISE)
    paint_head(s, "bun", P)
    body_dress(s, P)
    # bun + ribbon on the hat layer
    s.paint("head", "back", ["........", "..HhHH..", "..rrrr..", "..HHhH..", "...HH...", "........", "........", "........"],
            {**P, "r": hexc("8a3a3a")}, layer=1)
    return s


RETAINER_HEADS = {
    "a": dict(style="messy", hair="6a4a30", hair_hi="80603e", skin="efcfb0", skin_shade="d6b090", eye="3e5a6a"),
    "b": dict(style="short", hair="2a2624", hair_hi="3e3834", skin="deb896", skin_shade="c09a78", eye="3a2e24", mustache=True),
    "c": dict(style="short", hair="a08850", hair_hi="b89c60", skin="ecc6a6", skin_shade="d0a888", eye="4a6a4a", stubble=True),
}


def retainer(key, variant="black"):
    hd = RETAINER_HEADS[key]
    P = pal_person(skin=hd["skin"], skin_shade=hd["skin_shade"], hair=hd["hair"], hair_hi=hd["hair_hi"], eye=hd["eye"],
                   A="26262a", a="1c1c20", c="34343a", k="505056", X="4a3222", Y="a08a50",
                   P="2e2e32", p="242428", F="4e3626", f="2a1e16",
                   U="3a3a44", u="2c2c34", V="54545e", G="4e6a2e", g="3a5222")
    name = {"black": f"retainer_{key}", "bare": f"retainer_{key}_bare", "bandit": f"retainer_{key}_bandit"}[variant]
    s = Skin(name, noise=BASE_NOISE)
    paint_head(s, hd["style"], P, mustache=hd.get("mustache"), stubble=hd.get("stubble"))
    if variant == "black":
        body_retainer(s, P)
    elif variant == "bare":
        body_bare(s, P)
    else:
        P2 = dict(P, A=hexc("6a5438"), a=hexc("5a4630"), c=hexc("7a6446"), G=hexc("5a6a36"),
                  P=hexc("5e5040"), p=hexc("4a3e30"), g=hexc("4e5a30"), X=hexc("8a7a58"), x=hexc("6a5a40"),
                  F=hexc("3e2e22"), f=hexc("241a14"))
        body_bandit(s, P2)
        blood_face(s, P2)
        grime(s, P2)
        leaf_wreath(s, dict(P2, G=hexc("4e7a2e"), g=hexc("3a6224")))
    return s


def captain():
    P = pal_person(skin="dcb28e", skin_shade="c0946e", hair="4a3222", hair_hi="5e4230", eye="3a2e22",
                   A="6a5a3e", a="584a32", c="c8bc9c", V="8a7a52", k="5a4a2e", X="4a3222", Y="b0a060",
                   P="5c5446", p="4a4438", F="3e2c20", f="241a12")
    s = Skin("captain", noise=BASE_NOISE)
    paint_head(s, "short", P, beard=True)
    body_traveler(s, P)
    return s


GUARDS = {
    "a": dict(style="buzz", hair="8a6a44", hair_hi="9c7c52", skin="e8c4a2", skin_shade="cca482", eye="4a5a6a",
              A="4e5a3a", a="404a30", V="7a6e4c", P="5a5446", p="4a4438"),
    "b": dict(style="short", hair="222024", hair_hi="36323a", skin="d8ae8a", skin_shade="bc9270", eye="2e2620",
              A="5e4a34", a="4c3c2a", V="6e6a4a", P="4e4a40", p="403c34", stubble=True),
    "c": dict(style="messy", hair="5a3a22", hair_hi="6e4a2e", skin="eccaa8", skin_shade="d0aa88", eye="3e4a3a",
              A="6a6a4e", a="56563e", V="5a4a34", P="56524a", p="46423a"),
}


def guard(key):
    g = GUARDS[key]
    P = pal_person(skin=g["skin"], skin_shade=g["skin_shade"], hair=g["hair"], hair_hi=g["hair_hi"], eye=g["eye"],
                   A=g["A"], a=g["a"], c="c8c0a4", V=g["V"], k="4a3e2a", X="3e2a1c", Y="a09050",
                   P=g["P"], p=g["p"], F="3a2a1e", f="22180f")
    s = Skin(f"guard_{key}", noise=BASE_NOISE)
    paint_head(s, g["style"], P, stubble=g.get("stubble"))
    body_traveler(s, P)
    return s


def sniper():
    s = guard("a")
    s.name = "sniper"
    P = pal_person(C="4a5236", c="3a4228")
    # field cap on the hat layer
    s.paint("head", "front", ["CCCCCCCC", "cccccccc", "........", "........", "........", "........", "........", "........"], P, layer=1)
    for f in ("back", "right", "left"):
        s.paint("head", f, ["CCCCCCCC", "CCCCCCCC", "........", "........", "........", "........", "........", "........"], P, layer=1)
    s.fill("head", "top", "C", P, layer=1)
    return s


def bandit(key="a"):
    P = pal_person(skin="d2a680", skin_shade="b48a66", hair="3a2c20", hair_hi="4c3a2a", eye="2e241a",
                   A="5e4c32", a="4c3c28", c="6e5a3c", G="4a5a30", X="7a6a4a", x="5a4a34",
                   P="52483a", p="42382c", g="465230", F="3a2a1e", f="221810")
    s = Skin(f"bandit_{key}", noise=BASE_NOISE)
    paint_head(s, "messy" if key == "a" else "short", P, beard=True)
    body_bandit(s, P)
    grime(s, P)
    return s


def decoy(kind):
    """Bandit corpses dressed in the retainers' clothes (and the doctor's suit)."""
    if kind == "suit":
        s = doctor("suit")
        s.name = "decoy_suit"
        P = pal_person(skin="d2a680", skin_shade="b48a66", hair="3a2c20", hair_hi="4c3a2a")
        paint_head(s, "messy", P, beard=True)
    else:
        s = retainer("b", "black")
        s.name = "decoy_black"
        P = pal_person(skin="d2a680", skin_shade="b48a66", hair="3a2c20", hair_hi="4c3a2a")
        paint_head(s, "messy", P, beard=True)
    # face fully smeared with blood so nobody can tell who it is
    s.paint("head", "front", ["........", "........", "..R..R..", ".RRrRRR.", "RRRRRrRR", "RrRRRRRR", "RRRRrRRR", "sRRRRRrs"],
            P)
    return s


ALL = [kino, lambda: doctor("suit"), lambda: doctor("bare"), woman,
       lambda: retainer("a"), lambda: retainer("b"), lambda: retainer("c"),
       lambda: retainer("a", "bare"), lambda: retainer("b", "bare"), lambda: retainer("c", "bare"),
       lambda: retainer("a", "bandit"), lambda: retainer("b", "bandit"), lambda: retainer("c", "bandit"),
       captain, lambda: guard("a"), lambda: guard("b"), lambda: guard("c"), sniper,
       lambda: bandit("a"), lambda: bandit("b"), lambda: decoy("black"), lambda: decoy("suit")]



def main():
    os.makedirs(OUT, exist_ok=True)
    made = []
    for fn in ALL:
        sk = fn()
        sk.save(os.path.join(OUT, sk.name + ".png"))
        made.append(sk)
    if len(sys.argv) > 1:
        sheet(made, sys.argv[1])
    print("skins:", ", ".join(s.name for s in made))


if __name__ == "__main__":
    main()
