"""Colour schemes for building exteriors (all blocks exist in 1.20.1+, no gravity
blocks, nothing that connects to neighbours)."""
from __future__ import annotations

from dataclasses import dataclass

from anvil import B


@dataclass
class Scheme:
    name: str
    wall: int        # main facade material
    accent: int      # stripes, stair towers, banners
    band: int        # floor-slab edges
    rail: int        # corridor parapets
    column: int      # columns / pilasters
    floor: int       # corridor floors / balcony slabs
    glass: int       # window plane
    back: int        # what is seen behind the glass
    lit: int         # lit window backing
    door: int
    roof: int
    trim: int        # cornice / parapet cap
    names: dict = None   # role -> block id string (for VibeSchem palettes)


def _s(name, wall, accent, band, rail, column, floor, glass, back, lit="ochre_froglight",
       door="dark_oak_planks", roof="light_gray_concrete", trim="smooth_quartz"):
    names = dict(wall=wall, accent=accent, band=band, rail=rail, column=column, floor=floor, glass=glass,
                 back=back, lit=lit, door=door, roof=roof, trim=trim)
    return Scheme(name, B(wall), B(accent), B(band), B(rail), B(column), B(floor), B(glass), B(back),
                  B(lit), B(door), B(roof), B(trim), names)


SCHEMES = {
    # 白墙红带：最典型的中国中学教学楼
    "white_red": _s("white_red", "white_concrete", "red_terracotta", "light_gray_concrete", "white_concrete",
                    "white_concrete", "smooth_stone", "glass", "cyan_terracotta"),
    # 米黄 + 砖红
    "cream_brick": _s("cream_brick", "smooth_sandstone", "bricks", "white_terracotta", "smooth_sandstone",
                      "bricks", "smooth_stone", "glass", "light_blue_terracotta", trim="cut_sandstone"),
    # 蓝白
    "blue_white": _s("blue_white", "white_concrete", "light_blue_terracotta", "light_blue_concrete",
                     "white_concrete", "white_concrete", "smooth_stone", "glass", "blue_terracotta"),
    # 灰色现代
    "gray_modern": _s("gray_modern", "light_gray_concrete", "gray_concrete", "white_concrete",
                      "light_gray_concrete", "gray_concrete", "smooth_stone", "glass", "black_concrete",
                      lit="pearlescent_froglight", roof="gray_concrete", trim="white_concrete"),
    # 红砖老楼
    "red_brick": _s("red_brick", "bricks", "smooth_quartz", "smooth_quartz", "smooth_quartz", "smooth_quartz",
                    "smooth_stone", "glass", "gray_concrete", lit="shroomlight", trim="smooth_quartz"),
    # 清水混凝土（远处的巨构）
    "brutal": _s("brutal", "polished_andesite", "stone_bricks", "smooth_stone", "polished_andesite",
                 "stone_bricks", "smooth_stone", "glass", "black_concrete", lit="sea_lantern",
                 roof="andesite", trim="smooth_stone"),
    # 土黄
    "ochre": _s("ochre", "yellow_terracotta", "white_concrete", "white_concrete", "white_concrete",
                "white_concrete", "smooth_stone", "glass", "brown_terracotta", trim="white_concrete"),
    # 白瓷砖 + 灰
    "tile_gray": _s("tile_gray", "white_terracotta", "light_gray_terracotta", "light_gray_concrete",
                    "white_concrete", "light_gray_terracotta", "smooth_stone", "glass", "cyan_terracotta"),
}

AIR = 0
