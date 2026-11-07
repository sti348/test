"""School facilities and outdoor scenery as VibeSchem BuildSpecs (1.20.1).

Spec coordinates: x east, z south, y = 0 is the first air block above the
grass (world y = -60); the ground is y = -1 and specs may dig down to y = -3
(world -63, just above bedrock).  Each spec's [0, 0, 0] is placed at the
north-west corner of its plot.  Written to read well at dusk: lamps,
lanterns, underwater lights and lit windows everywhere."""
from __future__ import annotations

VERSION = "1.20.1"


def _spec(name, desc, ops, palette=None, components=None, seed=1):
    s = {"name": name, "minecraftVersion": VERSION, "description": desc, "seed": seed, "operations": ops}
    if palette:
        s["palette"] = palette
    if components:
        s["components"] = components
    return s


LAMP = {"operations": [
    {"id": "foot", "type": "blocks", "block": "polished_andesite", "at": [[0, 0, 0]]},
    {"id": "post", "type": "box", "from": [0, 1, 0], "to": [0, 4, 0], "block": "polished_blackstone_wall"},
    {"id": "head", "type": "blocks", "block": "dark_oak_fence", "at": [[0, 5, 0]]},
    {"id": "light", "type": "blocks", "block": "lantern[hanging=true]", "at": [[0, 4, 1], [0, 4, -1]]},
    {"id": "arms", "type": "blocks", "block": "dark_oak_fence", "at": [[0, 5, 1], [0, 5, -1]]}]}

BENCH = {"operations": [
    {"id": "seat", "type": "box", "from": [0, 0, 0], "to": [2, 0, 0], "block": "spruce_stairs[facing=north]"},
    {"id": "arm_w", "type": "blocks", "block": "spruce_trapdoor[open=true,facing=east]", "at": [[-1, 0, 0]]},
    {"id": "arm_e", "type": "blocks", "block": "spruce_trapdoor[open=true,facing=west]", "at": [[3, 0, 0]]}]}

FLOODLIGHT = {"operations": [
    {"id": "mast", "type": "box", "from": [0, 0, 0], "to": [0, 13, 0], "block": "gray_concrete"},
    {"id": "arm", "type": "box", "from": [-1, 14, 0], "to": [1, 14, 0], "block": "iron_bars"},
    {"id": "lamps", "type": "box", "from": [-1, 15, 0], "to": [1, 15, 0], "block": "sea_lantern"},
    {"id": "hood", "type": "box", "from": [-1, 16, 0], "to": [1, 16, 0], "block": "smooth_stone_slab"}]}


# ------------------------------------------------------------------ small outdoor props
PINGPONG = _spec("pingpong", "乒乓球台", [
    {"id": "legs", "type": "blocks", "block": "polished_blackstone_wall", "at": [[0, 0, 0], [0, 0, 4], [2, 0, 0], [2, 0, 4]]},
    {"id": "top", "type": "box", "from": [0, 1, 0], "to": [2, 1, 4], "block": "warped_slab[type=bottom]"},
    {"id": "net", "type": "box", "from": [0, 1, 2], "to": [2, 1, 2], "block": "white_stained_glass_pane"}])

FITNESS = _spec("fitness", "室外健身器材：单杠、双杠", [
    {"id": "bar_posts", "type": "box", "from": [0, 0, 0], "to": [0, 2, 0], "block": "blue_concrete"},
    {"id": "bar_posts2", "type": "box", "from": [4, 0, 0], "to": [4, 2, 0], "block": "blue_concrete"},
    {"id": "bar", "type": "box", "from": [1, 2, 0], "to": [3, 2, 0], "block": "iron_bars"},
    {"id": "pb", "type": "group", "operations": [
        {"type": "box", "from": [0, 0, 4], "to": [0, 1, 4], "block": "yellow_concrete"},
        {"type": "box", "from": [0, 0, 8], "to": [0, 1, 8], "block": "yellow_concrete"},
        {"type": "box", "from": [2, 0, 4], "to": [2, 1, 4], "block": "yellow_concrete"},
        {"type": "box", "from": [2, 0, 8], "to": [2, 1, 8], "block": "yellow_concrete"},
        {"type": "box", "from": [0, 1, 5], "to": [0, 1, 7], "block": "iron_bars"},
        {"type": "box", "from": [2, 1, 5], "to": [2, 1, 7], "block": "iron_bars"}]}])


# ------------------------------------------------------------------ campus lake
def lake_garden(W=200, D=220):
    """校园湖: an organic lake with an island pavilion, a hump-backed stone
    bridge, a lily-padded shore, willows and a lamp-lit promenade."""
    cx, cz = W // 2, D // 2 + 5
    pal = {
        "grass": "grass_block",
        "walk": {"mix": {"polished_andesite": 5, "andesite": 2, "stone_bricks": 1}, "scale": 2},
        "bank": {"mix": {"sand": 3, "gravel": 2, "mud": 1, "moss_block": 1}, "scale": 2},
        "lakebed": {"mix": {"clay": 3, "sand": 2, "gravel": 1}, "scale": 3},
        "column": "stripped_mangrove_log",
        "deck": "smooth_stone",
        "roof": {"mix": {"deepslate_tile_stairs": 5, "cobbled_deepslate_stairs": 1}, "scale": 2},
        "stone": {"mix": {"stone_bricks": 4, "mossy_stone_bricks": 1, "cracked_stone_bricks": 1}, "scale": 2},
    }
    shore = (
        "const W=args.W, D=args.D, cx=args.cx, cz=args.cz;"
        "for (let x=0;x<W;x++) for (let z=0;z<D;z++) {"
        " const dx=(x-cx)/74, dz=(z-cz)/72; const r=Math.hypot(dx,dz) + 0.16*fbm(x/38, z/38, 0.5, 3);"
        " if (r<1.0) { set(x,-1,z,'water'); set(x,-2,z,'water'); set(x,-3,z,'lakebed');"
        "   if (r<0.98 && r>0.86 && chance(0.06)) set(x,0,z,'lily_pad'); }"
        " else if (r<1.07) { set(x,-1,z,'bank'); if (chance(0.25)) set(x,0,z, pick(['tall_grass','short_grass','fern'])); }"
        " else if (r>1.13 && r<1.20) { set(x,-1,z,'walk'); }"
        "}")
    island = (
        "const ix=args.ix, iz=args.iz;"
        "for (let x=ix-16;x<=ix+16;x++) for (let z=iz-16;z<=iz+16;z++) {"
        " const d=Math.hypot(x-ix,z-iz)+1.5*noise(x/5,z/5);"
        " if (d<13) { set(x,-3,z,'dirt'); set(x,-2,z,'dirt'); set(x,-1,z, d<11?'grass_block':'bank'); } }")
    ops = [
        {"id": "ground", "type": "box", "from": [0, -1, 0], "to": [W - 1, -1, D - 1], "block": "grass"},
        {"id": "lake", "type": "script", "code": shore, "args": {"W": W, "D": D, "cx": cx, "cz": cz}},
        {"id": "island", "type": "script", "code": island, "args": {"ix": cx + 26, "iz": cz - 22}},
        {"id": "west_island", "type": "script", "code": island, "args": {"ix": cx - 36, "iz": cz + 16}},
        {"id": "west_island_tree", "type": "tree", "at": [cx - 36, 0, cz + 16], "kind": "willow", "seed": 9},
        # pavilion on the island (亭): stone platform, red columns, curved hip roof
        {"id": "pavilion", "type": "place", "component": "pavilion", "at": [cx + 22, 0, cz - 26]},
        # zig-zag boardwalk from the east shore to the island
        {"id": "boardwalk", "type": "script", "args": {"x0": cx + 37, "z0": cz - 22},
         "code": "let x=args.x0, z=args.z0; const legs=[[1,0,10],[0,1,6],[1,0,10],[0,-1,6],[1,0,10],[0,1,4],[1,0,8]];"
                 "for (const [dx,dz,n] of legs) for (let i=0;i<n;i++) { x+=dx; z+=dz;"
                 " for (let a=-1;a<=1;a++) set(x+(dz?a:0),0,z+(dx?a:0),'spruce_slab[type=bottom]');"
                 " if (i%3==0) { set(x+(dz?2:0),0,z+(dx?2:0),'spruce_fence'); set(x-(dz?2:0),0,z-(dx?2:0),'spruce_fence'); } }"},
        # hump-backed stone bridge across the narrow south-west arm
        {"id": "bridge", "type": "script", "args": {"x0": cx - 80, "z": cz + 16, "len": 34},
         "code": "const L=args.len; for (let i=0;i<=L;i++) { const t=i/L; const y=Math.round(5*Math.sin(Math.PI*t)) - 1;"
                 " const x=args.x0+i; for (let w=-2; w<=2; w++) { set(x,y,args.z+w,'stone'); if (y>0) set(x,y-1,args.z+w,'stone'); }"
                 " set(x,y+1,args.z-3,'stone_brick_wall'); set(x,y+1,args.z+3,'stone_brick_wall'); set(x,y,args.z-3,'stone'); set(x,y,args.z+3,'stone');"
                 " if (i%13==0) { set(x,y+2,args.z-3,'lantern'); set(x,y+2,args.z+3,'lantern'); } }"},
        # willows and cherries along the shore, a few big oaks behind
        {"id": "willows", "type": "script", "args": {"cx": cx, "cz": cz},
         "code": "for (let k=0;k<22;k++) { const a=k/22*2*Math.PI + 0.13*Math.sin(k*7); const r=1.12 + 0.05*Math.sin(k*3);"
                 " const x=Math.round(args.cx+74*r*Math.cos(a)), z=Math.round(args.cz+72*r*Math.sin(a));"
                 " tree({at:[x,0,z], kind: k%4==1 ? 'cherry' : 'willow', seed: k}); }"},
        {"id": "oaks", "type": "group", "operations": [
            {"type": "tree", "at": [12, 0, 14], "kind": "big_oak", "seed": 1},
            {"type": "tree", "at": [W - 14, 0, 16], "kind": "big_oak", "seed": 2},
            {"type": "tree", "at": [14, 0, D - 14], "kind": "big_oak", "seed": 3},
            {"type": "tree", "at": [W - 14, 0, D - 16], "kind": "big_oak", "seed": 4}]},
        # lamps and benches around the promenade
        {"id": "lamps", "type": "script", "args": {"cx": cx, "cz": cz},
         "code": "for (let k=0;k<30;k++) { const a=k/30*2*Math.PI; const x=Math.round(args.cx+74*1.24*Math.cos(a)), z=Math.round(args.cz+72*1.24*Math.sin(a));"
                 " place('lamp',[x,0,z]); if (k%3==1) place('bench',[x+1,0,z+2]); }"},
        {"id": "entry_path", "type": "box", "from": [cx - 2, -1, D - 30], "to": [cx + 2, -1, D - 1], "block": "walk"},
    ]
    pavilion = {"operations": [
        {"id": "platform", "type": "box", "from": [0, 0, 0], "to": [8, 0, 8], "block": "smooth_stone"},
        {"id": "edge", "type": "box", "from": [0, 0, 0], "to": [8, 0, 8], "block": "stone", "walls": True},
        {"id": "columns", "type": "group", "symmetry": {"x": 4, "z": 4}, "operations": [
            {"type": "box", "from": [1, 1, 1], "to": [1, 4, 1], "block": "column[axis=y]"}]},
        {"id": "beam", "type": "box", "from": [1, 5, 1], "to": [7, 5, 7], "block": "column[axis=x]", "walls": True},
        {"id": "roof", "type": "roof", "shape": "hip", "from": [1, 6, 1], "to": [7, 6, 7], "block": "roof",
         "profile": [0.5, 0.5, 1, 1, 1.5], "overhang": 2, "eaves": "dark_oak_stairs", "ridge": "gold_block"},
        {"id": "lantern", "type": "blocks", "block": "lantern[hanging=true]", "at": [[4, 4, 4]]},
        {"id": "seats", "type": "box", "from": [2, 1, 2], "to": [6, 1, 2], "block": "spruce_slab[type=bottom]"},
    ]}
    return _spec("lake_garden", "校园湖：岛上的亭子、九曲栈桥、拱桥、垂柳、荷叶和环湖步道", ops, pal,
                 {"pavilion": pavilion, "lamp": LAMP, "bench": BENCH})


# ------------------------------------------------------------------ pool + tennis
def sports_park(W=200, D=220):
    """室外游泳池 (50 x 25, lane lines, underwater lights, diving tower,
    bleachers) and four fenced tennis courts with floodlights."""
    px0, pz0, PW, PL = 30, 40, 25, 50
    pal = {"deck": {"mix": {"smooth_stone": 5, "polished_diorite": 1}, "scale": 3},
           "tile": "light_blue_concrete", "lane": "blue_concrete",
           "court": "blue_terracotta", "runoff": "green_terracotta", "line": "white_concrete"}
    lanes = "".join(f"box([{px0 + 2 + 3 * i},-3,{pz0 + 2}],[{px0 + 2 + 3 * i},-3,{pz0 + PL - 3}],'lane');" for i in range(8))
    ops = [
        {"id": "ground", "type": "box", "from": [0, -1, 0], "to": [W - 1, -1, D - 1], "block": "grass_block"},
        {"id": "pool_deck", "type": "box", "from": [px0 - 14, -1, pz0 - 14], "to": [px0 + PW + 14, -1, pz0 + PL + 22], "block": "deck"},
        {"id": "pool_shell", "type": "box", "from": [px0 - 1, -3, pz0 - 1], "to": [px0 + PW, -2, pz0 + PL], "block": "tile"},
        {"id": "pool_water", "type": "box", "from": [px0, -2, pz0], "to": [px0 + PW - 1, -1, pz0 + PL - 1], "block": "water"},
        {"id": "lanes", "type": "script", "code": lanes},
        {"id": "coping", "type": "box", "from": [px0 - 1, -1, pz0 - 1], "to": [px0 + PW, -1, pz0 + PL], "block": "smooth_quartz", "walls": True},
        {"id": "pool_water_top", "type": "box", "from": [px0, -1, pz0], "to": [px0 + PW - 1, -1, pz0 + PL - 1], "block": "water"},
        {"id": "underwater_lights", "type": "script", "args": {"x0": px0, "z0": pz0, "w": PW, "l": PL},
         "code": "for (let z=args.z0+4; z<args.z0+args.l-2; z+=6) { set(args.x0-1,-2,z,'sea_lantern'); set(args.x0+args.w,-2,z,'sea_lantern'); }"},
        {"id": "blocks", "type": "script", "args": {"x0": px0, "z0": pz0},
         "code": "for (let i=0;i<8;i++) set(args.x0+2+3*i, 0, args.z0-1, 'smooth_quartz_stairs[facing=north]');"},
        # diving tower at the south end
        {"id": "dive_posts", "type": "group", "symmetry": {"x": px0 + PW // 2}, "operations": [
            {"type": "box", "from": [px0 + 8, 0, pz0 + PL + 4], "to": [px0 + 8, 9, pz0 + PL + 4], "block": "white_concrete"}]},
        {"id": "dive_3", "type": "box", "from": [px0 + 8, 3, pz0 + PL - 2], "to": [px0 + PW - 9, 3, pz0 + PL + 4], "block": "smooth_quartz_slab[type=top]"},
        {"id": "dive_10", "type": "box", "from": [px0 + 8, 9, pz0 + PL - 4], "to": [px0 + PW - 9, 9, pz0 + PL + 4], "block": "smooth_quartz_slab[type=top]"},
        {"id": "dive_rail", "type": "box", "from": [px0 + 8, 10, pz0 + PL - 4], "to": [px0 + PW - 9, 10, pz0 + PL + 4], "block": "iron_bars", "walls": True},
        {"id": "dive_stairs", "type": "script", "args": {"x": px0 + PW - 8, "z": pz0 + PL + 4},
         "code": "for (let y=0;y<9;y++) { set(args.x+1, y, args.z-y+8, 'quartz_stairs[facing=north]'); }"},
        # bleachers on the west side, facing east
        {"id": "bleachers", "type": "script", "args": {"x0": px0 - 13, "z0": pz0, "l": PL},
         "code": "for (let r=0;r<6;r++) for (let z=args.z0; z<args.z0+args.l; z++) { for (let y=0;y<r;y++) set(args.x0+5-r, y, z, 'light_gray_concrete');"
                 " set(args.x0+5-r, r, z, ((z>>2)&1) ? 'blue_concrete' : 'white_concrete'); }"},
        {"id": "pool_fence", "type": "box", "from": [px0 - 15, 0, pz0 - 15], "to": [px0 + PW + 15, 1, pz0 + PL + 23], "block": "iron_bars", "walls": True},
        {"id": "pool_gate", "type": "box", "from": [px0 + 10, 0, pz0 + PL + 23], "to": [px0 + 14, 1, pz0 + PL + 23], "block": "air"},
        {"id": "pool_lights", "type": "group", "operations": [
            {"type": "place", "component": "floodlight", "at": [px0 - 14, 0, pz0 - 14]},
            {"type": "place", "component": "floodlight", "at": [px0 + PW + 14, 0, pz0 - 14]},
            {"type": "place", "component": "floodlight", "at": [px0 - 14, 0, pz0 + PL + 22]},
            {"type": "place", "component": "floodlight", "at": [px0 + PW + 14, 0, pz0 + PL + 22]}]},
        {"id": "lifeguard", "type": "group", "operations": [
            {"type": "box", "from": [px0 + PW + 3, 0, pz0 + 24], "to": [px0 + PW + 3, 2, pz0 + 24], "block": "white_concrete"},
            {"type": "blocks", "block": "red_concrete", "at": [[px0 + PW + 3, 3, pz0 + 24]]},
            {"type": "blocks", "block": "white_wool", "at": [[px0 + PW + 3, 4, pz0 + 24]]}]},
        # tennis courts: 4 courts of 36 x 18 (court 24 x 11 inside a green run-off)
        {"id": "courts", "type": "group", "repeat": {"count": 4, "offset": [0, 0, 48]}, "operations": [
            {"type": "place", "component": "tennis", "at": [118, 0, 8]}]},
        {"id": "trees", "type": "script", "args": {"W": W, "D": D},
         "code": "for (let z=6; z<args.D-6; z+=14) { tree({at:[4,0,z], kind:'birch', seed:z}); tree({at:[args.W-4,0,z], kind:'birch', seed:z+1}); }"},
        {"id": "path", "type": "box", "from": [100, -1, 0], "to": [105, -1, D - 1], "block": "deck"},
        {"id": "pingpong_court", "type": "box", "from": [10, -1, 140], "to": [92, -1, 208], "block": "deck"},
        {"id": "pingpong_tables", "type": "group", "repeat": {"count": 4, "offset": [0, 0, 16]}, "operations": [
            {"type": "place", "component": "pingpong", "at": [16, 0, 146], "repeat": {"count": 6, "offset": [12, 0, 0]}}]},
        {"id": "fitness", "type": "group", "repeat": {"count": 5, "offset": [14, 0, 0]}, "operations": [
            {"type": "place", "component": "fitness", "at": [18, 0, 128]}]},
        {"id": "court_lamps", "type": "group", "operations": [
            {"type": "place", "component": "floodlight", "at": [10, 0, 140]},
            {"type": "place", "component": "floodlight", "at": [92, 0, 208]}]},
        {"id": "pool_house", "type": "group", "operations": [
            {"type": "box", "from": [36, 0, 112], "to": [70, 5, 122], "block": "white_concrete"},
            {"type": "box", "from": [37, 1, 112], "to": [69, 3, 112], "block": "glass_pane"},
            {"type": "box", "from": [37, 4, 113], "to": [69, 4, 121], "block": "ochre_froglight"},
            {"type": "box", "from": [37, 1, 113], "to": [69, 3, 121], "block": "air"},
            {"type": "roof", "shape": "flat", "from": [36, 6, 112], "to": [70, 6, 122], "block": "smooth_stone_slab", "overhang": 2, "eaves": "smooth_quartz_stairs"}]},
        {"id": "path_lamps", "type": "group", "repeat": {"count": 9, "offset": [0, 0, 24]}, "operations": [
            {"type": "place", "component": "lamp", "at": [102, 0, 10]}]},
    ]
    tennis = {"operations": [
        {"id": "runoff", "type": "box", "from": [0, -1, 0], "to": [71, -1, 39], "block": "runoff"},
        {"id": "court", "type": "box", "from": [11, -1, 7], "to": [60, -1, 32], "block": "court"},
        {"id": "lines", "type": "box", "from": [11, -1, 7], "to": [60, -1, 32], "block": "line", "walls": True},
        {"id": "singles", "type": "box", "from": [11, -1, 10], "to": [60, -1, 29], "block": "line", "walls": True},
        {"id": "service", "type": "box", "from": [22, -1, 10], "to": [49, -1, 29], "block": "line", "walls": True},
        {"id": "center", "type": "box", "from": [22, -1, 19], "to": [49, -1, 20], "block": "line"},
        {"id": "net", "type": "box", "from": [35, 0, 6], "to": [36, 0, 33], "block": "white_stained_glass_pane"},
        {"id": "net_posts", "type": "blocks", "block": "polished_blackstone_wall", "at": [[35, 0, 5], [35, 0, 34]]},
        {"id": "fence", "type": "box", "from": [0, 0, 0], "to": [71, 3, 39], "block": "iron_bars", "walls": True},
        {"id": "gate", "type": "box", "from": [34, 0, 39], "to": [37, 2, 39], "block": "air"},
        {"id": "lights", "type": "group", "operations": [
            {"type": "place", "component": "floodlight", "at": [1, 0, 1]},
            {"type": "place", "component": "floodlight", "at": [70, 0, 38]}]},
    ]}
    return _spec("sports_park", "室外游泳池（50 米、水下灯、跳台、看台、更衣室）、四片网球场、乒乓球场和健身器材", ops, pal,
                 {"tennis": tennis, "floodlight": FLOODLIGHT, "lamp": LAMP,
                  "pingpong": {"operations": PINGPONG["operations"]}, "fitness": {"operations": FITNESS["operations"]}})


# ------------------------------------------------------------------ auditorium
def auditorium(W=200, D=220):
    """大礼堂: a severe monumental hall on a dark podium, a giant colonnade,
    tall slit windows between pilasters and a heavy hipped roof."""
    x0, x1, z0, z1 = 30, 170, 60, 170
    pal = {
        "base": {"mix": {"polished_deepslate": 5, "deepslate_bricks": 2, "cobbled_deepslate": 1}, "scale": 2},
        "wall": {"mix": {"smooth_quartz": 6, "calcite": 3, "polished_diorite": 1}, "scale": 3},
        "pilaster": "quartz_pillar",
        "frame": "polished_deepslate",
        "roof": {"mix": {"deepslate_tile_stairs": 5, "deepslate_brick_stairs": 1}, "scale": 3},
        "pave": {"mix": {"polished_andesite": 5, "smooth_stone": 2, "andesite": 1}, "scale": 2},
    }
    H = 46
    ops = [
        {"id": "ground", "type": "box", "from": [0, -1, 0], "to": [W - 1, -1, D - 1], "block": "grass_block"},
        {"id": "forecourt", "type": "box", "from": [x0 - 10, -1, 8], "to": [x1 + 10, -1, z0], "block": "pave"},
        {"id": "podium", "type": "box", "from": [x0 - 4, 0, z0 - 22], "to": [x1 + 4, 4, z1 + 4], "block": "base"},
        {"id": "steps", "type": "script", "args": {"xa": x0 + 30, "xb": x1 - 30, "zf": z0 - 22},
         "code": "for (let k=0;k<5;k++) { const z=args.zf-2*(5-k); box([args.xa,0,z],[args.xb,k,z+1],'base'); box([args.xa,k,z],[args.xb,k,z],'polished_deepslate_stairs[facing=north]'); }"},
        {"id": "hall", "type": "box", "from": [x0, 5, z0], "to": [x1, 5 + H, z1], "block": "wall"},
        {"id": "pilasters", "type": "group", "repeat": {"count": 15, "offset": [10, 0, 0]}, "operations": [
            {"type": "box", "from": [x0, 5, z0 - 1], "to": [x0 + 1, 4 + H, z0 - 1], "block": "pilaster"},
            {"type": "box", "from": [x0, 5, z1 + 1], "to": [x0 + 1, 4 + H, z1 + 1], "block": "pilaster"}]},
        {"id": "side_pilasters", "type": "group", "repeat": {"count": 12, "offset": [0, 0, 10]}, "operations": [
            {"type": "box", "from": [x0 - 1, 5, z0], "to": [x0 - 1, 4 + H, z0 + 1], "block": "pilaster"},
            {"type": "box", "from": [x1 + 1, 5, z0], "to": [x1 + 1, 4 + H, z0 + 1], "block": "pilaster"}]},
        {"id": "slit_windows", "type": "script", "args": {"x0": x0, "x1": x1, "z0": z0, "z1": z1, "h": H},
         "code": "for (let x=args.x0+5; x<args.x1-3; x+=10) for (const z of [args.z0, args.z1]) { box([x,10,z],[x+1,args.h-4,z],'gray_stained_glass_pane'); box([x,9,z],[x+1,9,z],'frame'); box([x,args.h-3,z],[x+1,args.h-3,z],'frame');"
                 " if (chance(0.5)) box([x,11,z+(z==args.z0?1:-1)],[x+1,args.h-5,z+(z==args.z0?1:-1)],'shroomlight'); else box([x,11,z+(z==args.z0?1:-1)],[x+1,args.h-5,z+(z==args.z0?1:-1)],'black_concrete'); }"
                 "for (let z=args.z0+5; z<args.z1-3; z+=10) for (const x of [args.x0, args.x1]) { box([x,10,z],[x,args.h-4,z+1],'gray_stained_glass_pane'); box([x+(x==args.x0?1:-1),11,z],[x+(x==args.x0?1:-1),args.h-5,z+1],'black_concrete'); }"},
        {"id": "entablature", "type": "box", "from": [x0 - 3, 5 + H, z0 - 18], "to": [x1 + 3, 12 + H, z1 + 3], "block": "wall"},
        {"id": "cornice_shadow", "type": "box", "from": [x0 - 4, 4 + H, z0 - 19], "to": [x1 + 4, 4 + H, z1 + 4], "block": "polished_deepslate_slab[type=top]"},
        {"id": "colonnade", "type": "group", "repeat": {"count": 12, "offset": [12, 0, 0]}, "operations": [
            {"type": "box", "from": [x0 + 4, 5, z0 - 16], "to": [x0 + 7, 4 + H, z0 - 13], "block": "pilaster"},
            {"type": "box", "from": [x0 + 3, 5, z0 - 17], "to": [x0 + 8, 5, z0 - 12], "block": "frame"}]},
        {"id": "portal", "type": "box", "from": [x0 + 50, 5, z0], "to": [x1 - 50, 20, z0], "block": "frame"},
        {"id": "doors", "type": "script", "args": {"xa": x0 + 54, "xb": x1 - 54, "z": z0},
         "code": "for (let x=args.xa; x<=args.xb; x+=6) { box([x,5,args.z],[x+2,16,args.z],'black_stained_glass_pane'); set(x,5,args.z-1,'dark_oak_door[facing=north,hinge=left]'); set(x+1,5,args.z-1,'dark_oak_door[facing=north,hinge=right]'); set(x,17,args.z-1,'lantern[hanging=true]'); }"},
        {"id": "name", "type": "layers", "origin": [0, 0, 0], "plane": "xy", "legend": {}, "layers": [[""]]},
        {"id": "roof", "type": "roof", "shape": "hip", "from": [x0 - 3, 13 + H, z0 - 18], "to": [x1 + 3, 13 + H, z1 + 3],
         "block": "roof", "pitch": 0.5, "overhang": 2, "eaves": "deepslate_tile_stairs", "fill": "polished_deepslate"},
        {"id": "plaza_trees", "type": "script", "args": {"x0": x0, "x1": x1},
         "code": "for (let x=args.x0-6; x<=args.x1+6; x+=16) { tree({at:[x,0,4], kind:'oak', seed:x}); place('lamp',[x+8,0,4]); }"},
        {"id": "side_trees", "type": "script", "args": {"x0": x0, "x1": x1, "z0": z0, "z1": z1, "D": D},
         "code": "for (let z=args.z0-10; z<args.D-6; z+=13) { tree({at:[args.x0-16,0,z], kind:'big_oak', seed:z}); tree({at:[args.x1+16,0,z], kind:'big_oak', seed:z+7}); place('lamp',[args.x0-9,0,z+6]); place('lamp',[args.x1+9,0,z+6]); }"
                 "for (let x=args.x0; x<=args.x1; x+=14) tree({at:[x,0,args.D-8], kind:'oak', seed:x});"},
        {"id": "torches", "type": "script", "args": {"x0": x0, "x1": x1, "z": z0 - 21},
         "code": "for (let x=args.x0; x<=args.x1; x+=12) { set(x,5,args.z,'polished_blackstone_wall'); set(x,6,args.z,'lantern'); }"},
    ]
    ops = [o for o in ops if o["id"] != "name"]
    return _spec("auditorium", "大礼堂：深色基座、巨柱门廊、壁柱间的狭长高窗和厚重的四坡屋顶", ops, pal, {"lamp": LAMP})


# ------------------------------------------------------------------ greenhouse
def greenhouse(W=200, D=220):
    """植物园温室: three glass barrel vaults on brick plinths, palms and
    flowers inside, warm lights, a formal garden with hedges and a pond."""
    pal = {"plinth": {"mix": {"bricks": 5, "mud_bricks": 1}, "scale": 2},
           "rib": "white_concrete",
           "hedge": {"mix": {"azalea_leaves": 4, "flowering_azalea_leaves": 1}, "scale": 2},
           "walk": {"mix": {"gravel": 3, "coarse_dirt": 1, "packed_mud": 1}, "scale": 2}}
    vault = (
        "const x0=args.x0, z0=args.z0, w=args.w, l=args.l, h=args.h; const c=(w-1)/2;"
        "box([x0,-1,z0],[x0+w-1,0,z0+l-1],'plinth'); box([x0+1,-1,z0+1],[x0+w-2,-1,z0+l-2],'grass_block');"
        "for (let z=z0; z<z0+l; z++) for (let x=x0; x<x0+w; x++) {"
        " const t=(x-x0-c)/c; const y=Math.round(h*Math.sqrt(Math.max(0,1-t*t)));"
        " const yn=Math.round(h*Math.sqrt(Math.max(0,1-Math.pow((Math.abs(x-x0-c)+1)/c,2))));"
        " for (let yy=Math.min(y,yn+1); yy<=y; yy++) set(x, yy+1, z, ((z-z0)%6==0) ? 'rib' : 'glass'); }"
        "for (const z of [z0, z0+l-1]) for (let x=x0; x<x0+w; x++) { const t=(x-x0-c)/c; const y=Math.round(h*Math.sqrt(Math.max(0,1-t*t)));"
        " for (let yy=1; yy<=y; yy++) set(x, yy, z, (Math.abs(x-x0-c)<2 && yy<5) ? 'air' : ((x-x0)%5==0 ? 'rib' : 'glass')); }"
        "for (let k=0;k<6;k++) tree({at:[x0+4+randInt(0,w-9),0,z0+6+k*Math.floor((l-12)/6)], kind: pick(['palm','jungle','cherry','oak']), seed:k+x0});"
        "scatter({from:[x0+1,-1,z0+1],to:[x0+w-2,1,z0+l-2], block:'flowers', density:0.12, on:['grass_block']});"
        "for (let z=z0+5; z<z0+l-3; z+=10) set(x0+Math.round(c), h-1, z, 'lantern[hanging=true]');")
    pal["flowers"] = {"mix": {"poppy": 2, "dandelion": 2, "cornflower": 1, "allium": 1, "azure_bluet": 1,
                              "oxeye_daisy": 1, "fern": 2, "short_grass": 2}}
    ops = [
        {"id": "ground", "type": "box", "from": [0, -1, 0], "to": [W - 1, -1, D - 1], "block": "grass_block"},
        {"id": "walks", "type": "group", "operations": [
            {"type": "box", "from": [0, -1, 20], "to": [W - 1, -1, 23], "block": "walk"},
            {"type": "box", "from": [97, -1, 0], "to": [102, -1, D - 1], "block": "walk"}]},
    ]
    for k, (x0, w, l, h) in enumerate(((16, 31, 96, 15), (84, 33, 120, 19), (153, 31, 96, 15))):
        ops.append({"id": f"vault_{k}", "type": "script", "code": vault,
                    "args": {"x0": x0, "z0": 32, "w": w, "l": l, "h": h}})
    ops += [
        {"id": "hedges", "type": "script", "args": {"W": W},
         "code": "for (let x=8; x<args.W-8; x+=1) { if (x>94 && x<106) continue; set(x,0,160,'hedge'); set(x,0,206,'hedge'); }"
                 "for (let z=160; z<=206; z++) { set(8,0,z,'hedge'); set(args.W-9,0,z,'hedge'); }"},
        {"id": "pond", "type": "cylinder", "center": [52, -2, 183], "radius": 12, "height": 2, "block": "water"},
        {"id": "pond_rim", "type": "cylinder", "center": [52, -1, 183], "radius": 13, "height": 1, "block": "smooth_stone", "hollow": True},
        {"id": "beds", "type": "scatter", "from": [110, -1, 166], "to": [188, 1, 200], "block": "flowers", "density": 0.35, "on": ["grass_block"]},
        {"id": "garden_lamps", "type": "group", "repeat": {"count": 8, "offset": [0, 0, 26]}, "operations": [
            {"type": "place", "component": "lamp", "at": [95, 0, 8]}, {"type": "place", "component": "lamp", "at": [104, 0, 8]}]},
    ]
    return _spec("greenhouse", "植物园：三座玻璃筒拱温室（里面有棕榈和花）、绿篱花园和水池", ops, pal, {"lamp": LAMP})


# ------------------------------------------------------------------ walkway, fountain, bus stop
def walkway(L=180):
    """风雨廊: a covered walk along the avenue, lanterns under every bay."""
    ops = [
        {"id": "pave", "type": "box", "from": [0, -1, 0], "to": [4, -1, L - 1], "block": "smooth_stone"},
        {"id": "posts", "type": "group", "repeat": {"count": L // 6 + 1, "offset": [0, 0, 6]}, "operations": [
            {"type": "box", "from": [0, 0, 0], "to": [0, 3, 0], "block": "white_concrete"},
            {"type": "box", "from": [4, 0, 0], "to": [4, 3, 0], "block": "white_concrete"},
            {"type": "blocks", "block": "lantern[hanging=true]", "at": [[2, 3, 3]]}]},
        {"id": "roof", "type": "roof", "shape": "flat", "from": [0, 4, 0], "to": [4, 4, L - 1], "block": "smooth_stone_slab",
         "overhang": 1, "eaves": "smooth_quartz_stairs"},
        {"id": "beam", "type": "box", "from": [0, 4, 0], "to": [4, 4, L - 1], "block": "smooth_quartz", "walls": True},
        {"id": "benches", "type": "group", "repeat": {"count": L // 24, "offset": [0, 0, 24]}, "operations": [
            {"type": "box", "from": [1, 0, 8], "to": [1, 0, 10], "block": "spruce_stairs[facing=west]"}]},
    ]
    return _spec("walkway", "风雨连廊：每一跨挂一盏灯笼", ops)


def fountain(R=12):
    c = R + 2
    ops = [
        {"id": "plaza", "type": "cylinder", "center": [c, -1, c], "radius": R + 2, "height": 1, "block": "smooth_quartz"},
        {"id": "basin", "type": "cylinder", "center": [c, -1, c], "radius": R, "height": 1, "block": "water"},
        {"id": "bottom", "type": "cylinder", "center": [c, -2, c], "radius": R, "height": 1, "block": "light_blue_terracotta"},
        {"id": "rim", "type": "cylinder", "center": [c, 0, c], "radius": R, "height": 1, "block": "smooth_quartz_slab", "hollow": True},
        {"id": "plinth", "type": "cylinder", "center": [c, -1, c], "radius": 3, "height": 2, "block": "polished_deepslate"},
        {"id": "column", "type": "cylinder", "center": [c, 1, c], "radius": 1, "height": 7, "block": "quartz_pillar"},
        {"id": "lights", "type": "script", "args": {"c": c, "R": R},
         "code": "for (let k=0;k<12;k++) { const a=k/12*2*Math.PI; set(Math.round(args.c+(args.R-1)*Math.cos(a)), -2, Math.round(args.c+(args.R-1)*Math.sin(a)), 'sea_lantern'); }"},
        {"id": "crown", "type": "blocks", "block": "sea_lantern", "at": [[c, 8, c]]},
    ]
    return _spec("fountain", "校门外广场上的喷泉水池（水下灯）", ops)


def bus_stop():
    ops = [
        {"id": "pad", "type": "box", "from": [-1, -1, -1], "to": [9, -1, 3], "block": "smooth_stone"},
        {"id": "back", "type": "box", "from": [0, 0, 2], "to": [8, 2, 2], "block": "glass_pane"},
        {"id": "posts", "type": "blocks", "block": "polished_blackstone_wall", "at": [[0, 0, 2], [0, 1, 2], [0, 2, 2], [8, 0, 2], [8, 1, 2], [8, 2, 2]]},
        {"id": "roof", "type": "box", "from": [-1, 3, 0], "to": [9, 3, 2], "block": "smooth_stone_slab"},
        {"id": "ad", "type": "box", "from": [9, 0, 1], "to": [9, 2, 2], "block": "sea_lantern"},
        {"id": "bench", "type": "box", "from": [2, 0, 1], "to": [6, 0, 1], "block": "spruce_slab[type=bottom]"},
        {"id": "sign", "type": "group", "operations": [
            {"type": "box", "from": [-3, 0, 0], "to": [-3, 3, 0], "block": "iron_bars"},
            {"type": "blocks", "block": "blue_concrete", "at": [[-3, 4, 0]]}]},
    ]
    return _spec("bus_stop", "公交站：玻璃候车亭、长椅、灯箱", ops)


# ------------------------------------------------------------------ buses, cars, parking
BUS = {"operations": [
    {"id": "body", "type": "box", "from": [0, 1, 0], "to": [2, 3, 11], "block": "yellow_concrete"},
    {"id": "windows", "type": "box", "from": [0, 2, 1], "to": [2, 2, 10], "block": "black_stained_glass_pane"},
    {"id": "body_mid", "type": "box", "from": [1, 1, 0], "to": [1, 3, 11], "block": "yellow_concrete"},
    {"id": "roof", "type": "box", "from": [0, 4, 1], "to": [2, 4, 10], "block": "smooth_quartz_slab[type=bottom]"},
    {"id": "skirt", "type": "box", "from": [0, 0, 1], "to": [2, 0, 10], "block": "black_concrete"},
    {"id": "wheels", "type": "blocks", "block": "coal_block", "at": [[0, 0, 2], [2, 0, 2], [0, 0, 9], [2, 0, 9]]},
    {"id": "headlights", "type": "blocks", "block": "ochre_froglight", "at": [[0, 1, 0], [2, 1, 0]]},
    {"id": "tail", "type": "blocks", "block": "red_concrete", "at": [[0, 1, 11], [2, 1, 11]]},
    {"id": "stripe", "type": "box", "from": [0, 1, 1], "to": [0, 1, 10], "block": "black_concrete"},
    {"id": "stripe2", "type": "box", "from": [2, 1, 1], "to": [2, 1, 10], "block": "black_concrete"}]}


def bus_lot(W=300, D=80):
    """校车停车场: two rows of yellow school buses, headlights on."""
    ops = [
        {"id": "asphalt", "type": "box", "from": [0, -1, 0], "to": [W - 1, -1, D - 1], "block": "gray_concrete"},
        {"id": "kerb", "type": "box", "from": [0, -1, 0], "to": [W - 1, -1, D - 1], "block": "smooth_stone", "walls": True},
        {"id": "bays", "type": "script", "args": {"W": W},
         "code": "for (let x=6; x<args.W-6; x+=6) { box([x,-1,4],[x,-1,18],'yellow_concrete'); box([x,-1,D-19],[x,-1,D-5],'yellow_concrete'); }"
                 .replace("D-19", str(D - 19)).replace("D-5", str(D - 5))},
        {"id": "buses", "type": "script", "args": {"W": W, "D": D},
         "code": "for (let x=8; x<args.W-8; x+=6) { if (chance(0.8)) place('bus',[x+1,0,5]); if (chance(0.7)) place('bus',[x+1,0,args.D-17]); }"},
        {"id": "lamps", "type": "script", "args": {"W": W, "D": D},
         "code": "for (let x=10; x<args.W; x+=30) place('lamp',[x,0,Math.floor(args.D/2)]);"},
    ]
    return _spec("bus_lot", "校车停车场：两排黄色校车，车灯亮着", ops, components={"bus": BUS, "lamp": LAMP})


def car_park(W=300, D=80):
    car = {"operations": [
        {"id": "body", "type": "box", "from": [0, 0, 0], "to": [1, 0, 4], "block": "paint"},
        {"id": "cabin", "type": "box", "from": [0, 1, 1], "to": [1, 1, 3], "block": "gray_stained_glass_pane"},
        {"id": "top", "type": "box", "from": [0, 2, 1], "to": [1, 2, 3], "block": "paint_slab"},
        {"id": "lights", "type": "blocks", "block": "ochre_froglight", "at": [[0, 0, 0], [1, 0, 0]]}]}
    colors = ["white", "black", "gray", "light_gray", "red", "blue"]
    comps = {"lamp": LAMP}
    for c in colors:
        comps[f"car_{c}"] = {"operations": [dict(o, block=o["block"].replace("paint_slab", "smooth_quartz_slab[type=bottom]" if c in ("white", "light_gray") else "smooth_stone_slab[type=bottom]").replace("paint", f"{c}_concrete")) for o in car["operations"]]}
    ops = [
        {"id": "asphalt", "type": "box", "from": [0, -1, 0], "to": [W - 1, -1, D - 1], "block": "gray_concrete"},
        {"id": "kerb", "type": "box", "from": [0, -1, 0], "to": [W - 1, -1, D - 1], "block": "smooth_stone", "walls": True},
        {"id": "bays", "type": "script", "args": {"W": W, "D": D},
         "code": "for (let x=4; x<args.W-4; x+=3) { box([x,-1,3],[x,-1,9],'white_concrete'); box([x,-1,args.D-10],[x,-1,args.D-4],'white_concrete'); box([x,-1,args.D/2-8],[x,-1,args.D/2+7],'white_concrete'); }"},
        {"id": "cars", "type": "script", "args": {"W": W, "D": D, "colors": colors},
         "code": "for (let x=5; x<args.W-5; x+=3) for (const z of [4, args.D-9, args.D/2-7, args.D/2+2]) if (chance(0.62)) place('car_'+pick(args.colors),[x,0,z]);"},
        {"id": "lamps", "type": "script", "args": {"W": W, "D": D},
         "code": "for (let x=12; x<args.W; x+=24) { place('lamp',[x,0,14]); place('lamp',[x,0,args.D-15]); }"},
        {"id": "trees", "type": "script", "args": {"W": W, "D": D},
         "code": "for (let x=6; x<args.W; x+=12) tree({at:[x,0,args.D/2], kind:'oak', seed:x});"},
    ]
    return _spec("car_park", "停车场：一排排小汽车", ops, components=comps)


# ------------------------------------------------------------------ water tower
def water_tower():
    """巨型水塔: eight legs with cross bracing, a central shaft with a ladder,
    a 70-wide tank 260 blocks up, red warning lights on top."""
    R, LEG, TOP, TH = 30, 2, 250, 52
    legs = [(round(R * __import__("math").cos(k * 3.14159265 / 4)), round(R * __import__("math").sin(k * 3.14159265 / 4))) for k in range(8)]
    ops = [{"id": "foot", "type": "cylinder", "center": [0, -1, 0], "radius": R + 6, "height": 1, "block": "polished_andesite"}]
    for i, (x, z) in enumerate(legs):
        ops.append({"id": f"leg_{i}", "type": "cylinder", "center": [x, 0, z], "radius": LEG, "height": TOP, "block": "light_gray_concrete"})
        ops.append({"id": f"pier_{i}", "type": "cylinder", "center": [x, 0, z], "radius": LEG + 2, "height": 6, "block": "polished_deepslate"})
    brace = []
    for y in range(36, TOP, 36):
        for i in range(8):
            (xa, za), (xb, zb) = legs[i], legs[(i + 1) % 8]
            brace.append({"type": "line", "from": [xa, y, za], "to": [xb, y, zb], "block": "light_gray_concrete", "radius": 1})
            brace.append({"type": "line", "from": [xa, y, za], "to": [0, y, 0], "block": "gray_concrete"})
            brace.append({"type": "line", "from": [xa, y - 36, za], "to": [xb, y, zb], "block": "iron_bars"})
    ops.append({"id": "bracing", "type": "group", "operations": brace})
    ops += [
        {"id": "shaft", "type": "cylinder", "center": [0, 0, 0], "radius": 4, "height": TOP, "block": "light_gray_concrete", "hollow": True},
        {"id": "ladder", "type": "box", "from": [0, 0, -5], "to": [0, TOP - 1, -5], "block": "ladder[facing=north]"},
        {"id": "ring", "type": "cylinder", "center": [0, TOP, 0], "radius": R + 6, "height": 1, "block": "smooth_stone_slab[type=top]"},
        {"id": "ring_rail", "type": "cylinder", "center": [0, TOP + 1, 0], "radius": R + 6, "height": 1, "block": "iron_bars", "hollow": True},
        {"id": "tank_floor", "type": "sphere", "center": [0, TOP + 1, 0], "radii": [R + 4, 14, R + 4], "half": "bottom", "block": "light_gray_concrete", "hollow": True, "thickness": 2},
        {"id": "tank", "type": "cylinder", "center": [0, TOP + 1, 0], "radius": R + 4, "height": TH, "block": "white_concrete", "hollow": True, "thickness": 2},
        {"id": "bands", "type": "group", "repeat": {"count": 4, "offset": [0, 13, 0]}, "operations": [
            {"type": "cylinder", "center": [0, TOP + 6, 0], "radius": R + 5, "height": 1, "block": "gray_concrete", "hollow": True}]},
        {"id": "roof", "type": "dome", "center": [0, TOP + 1 + TH, 0], "radius": R + 4, "height": 14, "block": "light_gray_concrete", "hollow": True},
        {"id": "beacon", "type": "box", "from": [-1, TOP + TH + 15, -1], "to": [1, TOP + TH + 17, 1], "block": "red_concrete"},
        {"id": "warning", "type": "blocks", "block": "shroomlight", "at": [[0, TOP + TH + 18, 0], [R + 4, TOP + TH, 0], [-R - 4, TOP + TH, 0], [0, TOP + TH, R + 4], [0, TOP + TH, -R - 4]]},
    ]
    return _spec("water_tower", "巨型水塔：八根塔腿、交叉支撑、260 格高的水箱，顶上有红色警示灯", ops)


FACILITIES = {
    "lake_garden": lake_garden, "sports_park": sports_park, "auditorium": auditorium, "greenhouse": greenhouse,
    "walkway": walkway, "fountain": fountain, "bus_stop": bus_stop, "bus_lot": bus_lot, "car_park": car_park,
    "water_tower": water_tower, "pingpong": lambda: PINGPONG, "fitness": lambda: FITNESS,
}
