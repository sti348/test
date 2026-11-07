"""升旗广场与弯弓楼 (forecourt) - blockout rebuilt from hero.png.

Measured from the painting (1536 x 1024, vertical fov 60):
  camera at eye level on the axis, looking north, tilted up ~19 degrees
  tower front ~240 m away, ~56 m wide body, spires beyond the frame (>250 m)
  bow-shaped hall ~110 m tall; at 40 degrees off-axis it is only ~120 m away,
  so its plan is a horseshoe (an arc of r ~110 m) with wings running south
  flagpole ~70 m tall on a round dais ~30 m in front of the entrance steps
What the painting does not show is filled in from the School World map: the
plaza continues south into a tree-lined avenue that ends at the triumphal-arch
school gate, with the endless campus all around in the haze.

Coordinates: metres, x east, z south, y up; the hero camera stands at (0, 0)."""
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from stage import Stage  # noqa: E402

CX, CZ, R_IN, DEPTH = 0.0, -130.0, 110.0, 30.0       # the arc of the hall
H_HALL, STOREY = 110.0, 7.5
TOWER = (-38.0, -310.0, 38.0, -240.0)                 # x0, z0, x1, z1
WING_END_Z = -30.0

CAMERAS = {
    # name: (x, y, z, yaw, pitch, vertical fov); yaw 180 = north, negative pitch looks up
    "hero": (0.0, 1.6, 0.0, 180, -19, 60),
    "reverse": (22.0, 9.6, -206.0, 4, -5, 60),         # from the top of the entrance steps, looking back south
    "east_walk": (-70.0, 1.6, -90.0, 201, -16, 60),   # west side of the plaza under the trees, looking north-east
    "aerial": (330.0, 320.0, 280.0, 138, 30, 55),     # high above the south-east, the whole forecourt
}


def make_stage():
    st = Stage(-700, -460, 700, 760, y0=-2, y1=340, res=2.0)
    st.ground("lawn", 0.0)
    # --- plaza: a round paved forecourt inside the horseshoe and its southern extension
    st.disc(CX, CZ, R_IN - 6, -2, 0.2, "plaza")
    st.box(-75, -2, CZ, 75, 0.2, 70, "plaza")
    for r in (30, 55, 80):                               # concentric paving rings (subtle: same label)
        st.disc(0, -175, r + 1, -2, 0.2, "plaza", r_in=r)
    # --- the hall: an arc around the plaza + two straight wings toward the camera
    st.sector(CX, CZ, R_IN, R_IN + DEPTH, -100, 100, 0, H_HALL, "building")
    for sx in (-1, 1):
        x_in = sx * R_IN * math.sin(math.radians(100))
        z_arc = CZ - R_IN * math.cos(math.radians(100))
        x0, x1 = sorted((x_in, x_in + sx * DEPTH))
        st.box(x0, 0, z_arc, x1, H_HALL, WING_END_Z, "building")
    st.floorlines(STOREY, 6, H_HALL)
    # pier towers rising above the roof every 30 degrees, and at the wing ends
    for a in (-90, -60, -30, 30, 60, 90):
        px = CX + (R_IN + DEPTH / 2) * math.sin(math.radians(a))
        pz = CZ - (R_IN + DEPTH / 2) * math.cos(math.radians(a))
        st.box(px - 9, 0, pz - 9, px + 9, H_HALL + 18, pz + 9, "building")
        st.spire(px, pz, 6, H_HALL + 18, H_HALL + 34, "roof")
    for sx in (-1, 1):
        x = sx * (R_IN * math.sin(math.radians(100)) + DEPTH / 2)
        st.box(x - 12, 0, WING_END_Z - 20, x + 12, H_HALL + 20, WING_END_Z, "building")
    st.sector(CX, CZ, R_IN, R_IN + DEPTH, -100, 100, H_HALL, H_HALL + 2, "roof")
    # ground-floor arcade: a glazed band all round the inner face
    st.sector(CX, CZ, R_IN - 0.5, R_IN + 1.5, -100, 100, 1, 9, "glass")
    # --- the tower of learning: a tall body, stepped crown, a cluster of spires
    x0, z0, x1, z1 = TOWER
    st.box(x0 - 10, 0, z0 - 10, x1 + 10, 40, z1, "tower")                 # base block with the portal
    st.box(x0, 0, z0, x1, 190, z1, "tower")
    st.box(x0 + 6, 190, z0 + 6, x1 - 6, 230, z1 - 6, "tower")
    st.box(x0 + 12, 230, z0 + 12, x1 - 12, 255, z1 - 12, "tower")
    st.spire((x0 + x1) / 2, (z0 + z1) / 2, 15, 255, 335, "tower")
    for (sx, sz) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):                  # corner pinnacles
        st.spire((x0 + x1) / 2 + sx * 30, (z0 + z1) / 2 + sz * 28, 6, 190, 250, "tower")
    st.box(-9, 0, z1 - 0.5, 9, 32, z1 + 1.5, "glass")                      # the pointed portal (glazed)
    # entrance steps from the plaza up to the portal
    st.stairs(-45, 45, -205, -240, 0, 8)
    # --- flagpole on a round dais
    st.disc(0, -175, 9, 0, 0.8, "stairs")
    st.box(-1.2, 0, -176.2, 1.2, 72, -173.8, "pole")
    # --- trees in front of the hall, lamps and benches along the plaza edge
    for a in range(-95, 96, 9):
        if abs(a) < 40:
            continue
        r = R_IN - 14
        st.tree(CX + r * math.sin(math.radians(a)), CZ - r * math.cos(math.radians(a)), h=16, r=6)
    for z in range(-110, 60, 14):
        for x in (-70, 70):
            st.box(x - 0.4, 0, z - 0.4, x + 0.4, 6, z + 0.4, "lamp")
    # --- behind the hero camera: the avenue south to the gate
    st.box(-14, -2, 70, 14, 0.3, 600, "road")
    st.box(-40, -2, 70, -14, 0.3, 600, "plaza")
    st.box(14, -2, 70, 40, 0.3, 600, "plaza")
    for z in range(80, 590, 12):
        for x in (-46, 46, -96, 96):
            st.tree(x, z, h=14, r=5)
    gx0, gx1, gz0, gz1, gh = -140, 140, 600, 700, 260                     # triumphal-arch gate
    st.box(gx0, 0, gz0, gx1, gh, gz1, "gate")
    _carve_arch(st, 0, 104, 40, gz0, gz1)
    # --- the endless campus in the haze: tall masses beyond the hall's wings and along the avenue
    import random
    rnd = random.Random(7)
    for k in range(70):
        x = rnd.choice([-1, 1]) * rnd.uniform(200, 680)
        z = rnd.uniform(-440, 740)
        if abs(x) < 220 and z < 0 or abs(x) < 200:            # keep the hall and the avenue clear
            continue
        if any(math.hypot(x - c[0], z - c[2]) < 110 for c in CAMERAS.values()):
            continue
        w, d, h = rnd.uniform(40, 110), rnd.uniform(30, 90), rnd.uniform(90, 300)
        st.box(x - w / 2, 0, z - d / 2, x + w / 2, h, z + d / 2, "far")
    return st


def _carve_arch(st, cx, spring, r, z0, z1):
    """Cut a round-headed passage through the gate along z."""
    import numpy as np
    xs, ys = st._xs, st._ys
    m = (np.abs(xs[None, :] - cx) < r) & (ys[:, None] < spring)
    m |= ((xs[None, :] - cx) ** 2 + (ys[:, None] - spring) ** 2 < r * r) & (ys[:, None] >= spring)
    Z = (st._zs >= z0 - 2) & (st._zs < z1 + 2)
    for k in np.nonzero(Z)[0]:
        sl = st.V[:, k, :]
        sl[m] = 0
