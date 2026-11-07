"""Tall-world engine: column terrain + pieces -> region files, for any dimension.

The world no longer stops at y 319: the overworld runs from y -1024 to 2032
(the game's maximum) and the Nether from 0 to 1024, through data-pack
dimension-type overrides (twilight.py).  Columns are described by 2-D maps -
ground height, fluid surface and block, ceiling, top and sub-surface blocks -
and a rock-strata table for everything below; buildings and landforms are
pieces pasted on top.  Regions are composed in 256-row bands and only where
something varies: fully solid, fluid, air or ceiling sections are written from
cached uniform entries, so a 3056-block column costs little."""
from __future__ import annotations

import os
import struct
import time
import zlib

import numpy as np

import anvil
import buildings as bd
import nbt
from anvil import B
from nbt import Byte, Int, List, Long

NONE_Y = -30000          # "no fluid" / "no ceiling" sentinel


class Dim:
    def __init__(self, key, min_y, height, folder, strata, ceiling_block=None, bedrock_top=False):
        self.key, self.min_y, self.height, self.folder = key, min_y, height, folder
        self.max_y = min_y + height
        self.strata = strata                    # function y -> block name (constant within 16-row sections)
        self.ceiling_block = ceiling_block
        self.bedrock_top = bedrock_top
        self._lut = None

    def lut(self):
        if self._lut is None:
            self._lut = np.array([B(self.strata(y)) for y in range(self.min_y, self.max_y)], np.uint16)
        return self._lut


def _ow_strata(y):
    """Rock layers you see in the sinkhole walls; constant per 16-row section."""
    s = (y // 16) * 16
    if s >= -16:
        return "stone"
    bands = {-48: "andesite", -112: "tuff", -176: "diorite", -224: "granite", -320: "calcite",
             -416: "tuff", -512: "dripstone_block", -608: "andesite", -720: "smooth_basalt", -832: "tuff"}
    if s in bands:
        return bands[s]
    return "stone" if s > -256 else "deepslate"


def _nether_strata(y):
    s = (y // 16) * 16
    return {64: "blackstone", 160: "basalt", 320: "blackstone", 480: "magma_block"}.get(s, "netherrack")


OVERWORLD = Dim("overworld", -1024, 3056, "region", _ow_strata)
NETHER = Dim("the_nether", 0, 1024, os.path.join("DIM-1", "region"), _nether_strata, ceiling_block="netherrack")


class World:
    """One dimension: pieces (with an Index), a ground painter for top blocks,
    landform features that edit the column maps, and a biome function."""

    def __init__(self, dim, pieces, base_ground, painter=None, landforms=(), biome=None, top="grass_block", sub="dirt"):
        import campus
        self.dim = dim
        self.pieces = pieces
        self.index = campus.Index(pieces)
        self.base_ground = base_ground
        self.painter = painter                  # (x0, z0, dx, dz) -> top-block ids or None
        self.landforms = list(landforms)        # objects with .bbox (x0, z0, x1, z1) and .apply(maps, x0, z0)
        self.biome = biome or (lambda cx, cz, sy: "minecraft:plains")
        self.top, self.sub = B(top), B(sub)

    # ------------------------------------------------------------ column maps
    def maps(self, x0, z0, dx, dz):
        m = {
            "ground": np.full((dz, dx), self.base_ground, np.int32),
            "fluid": np.full((dz, dx), NONE_Y, np.int32),
            "fluid_id": np.full((dz, dx), B("water"), np.uint16),
            "ceil": np.full((dz, dx), -NONE_Y, np.int32),
            "top": np.full((dz, dx), self.top, np.uint16) if self.painter is None else self.painter(x0, z0, dx, dz),
            "sub": np.full((dz, dx), self.sub, np.uint16),
        }
        for lf in self.landforms:
            a0, b0, a1, b1 = lf.bbox
            if a0 < x0 + dx and a1 > x0 and b0 < z0 + dz and b1 > z0:
                lf.apply(m, x0, z0)
        return m

    def pieces_in(self, x0, z0, dx, dz):
        return self.index.query(x0, z0, dx, dz)

    def touched(self, x0, z0, dx, dz):
        """Does this rectangle differ from what the dimension's generator makes?"""
        if self.pieces_in(x0, z0, dx, dz):
            return True
        return any(lf.bbox[0] < x0 + dx and lf.bbox[2] > x0 and lf.bbox[1] < z0 + dz and lf.bbox[3] > z0
                   for lf in self.landforms)

    # ------------------------------------------------------------ voxels
    def fill(self, m, y0, y1):
        """Terrain voxels for rows y0..y1-1 from the column maps."""
        d = self.dim
        ys = np.arange(y0, y1, dtype=np.int32)[:, None, None]
        g = m["ground"][None]
        strata = d.lut()[np.clip(np.arange(y0, y1) - d.min_y, 0, d.height - 1)][:, None, None]
        V = np.where(ys <= g - 3, strata, 0).astype(np.uint16)
        V = np.where((ys >= g - 2) & (ys < g), m["sub"][None], V)
        V = np.where(ys == g, m["top"][None], V)
        V = np.where((ys > g) & (ys <= m["fluid"][None]), m["fluid_id"][None], V)
        if d.ceiling_block:
            c = m["ceil"][None]
            V = np.where(ys >= c, strata, V)
        if y0 == d.min_y:
            V[0] = B("bedrock")
        fl = getattr(self, "_floor", None)               # shallow regions: bedrock floor, nothing below
        if fl is not None and y0 <= fl < y1:
            V[fl - y0] = B("bedrock")
            V[:fl - y0] = 0
        return V

    def compose(self, x0, z0, dx, dz, y0, y1, m=None, cache=None):
        m = self.maps(x0, z0, dx, dz) if m is None else m
        V = self.fill(m, y0, y1)
        for p in self.pieces_in(x0, z0, dx, dz):
            if p.y >= y1 or p.top <= y0:
                continue
            key = id(p)
            A = cache.get(key) if cache is not None else None
            if A is None:
                A = p.build()
                if cache is not None:
                    cache[key] = A
            bd.paste(V, A, p.y - y0, p.z - z0, p.x - x0)
        return V

    # ------------------------------------------------------------ regions
    def detail_intervals(self, m, pieces):
        """Merged row intervals that need voxels: the terrain band and every piece's
        band, aligned to sections.  Everything between them is plain air."""
        d = self.dim
        lo = int(m["ground"].min()) - 3
        hi = max(int(m["ground"].max()), int(m["fluid"].max())) + 1
        if d.ceiling_block:
            lo = min(lo, int(m["ceil"].min()))
            hi = max(hi, int(m["ceil"].max()) + 1)
        iv = [(lo, hi)] + [(p.y, p.top) for p in pieces]
        iv = sorted((max(d.min_y, (a // 16) * 16), min(d.max_y, -(-b // 16) * 16)) for a, b in iv)
        out = []
        for a, b in iv:
            if out and a <= out[-1][1]:
                out[-1] = (out[-1][0], max(out[-1][1], b))
            else:
                out.append((a, b))
        return out

    def floor_rule(self, m):
        """Where bedrock closes a region's floor (nothing is written below it), or
        None for rock all the way down.  Shallow ground: y -64 like the original
        map; ground a little lower (seas): the section boundary just below it;
        really deep terrain (sinkhole, trench): None."""
        if self.dim.key != "overworld":
            return None
        gmin = int(m["ground"].min())
        if gmin >= -64:
            return -64
        if gmin >= -200:
            return ((gmin - 3) // 16) * 16
        return None

    def region_floor(self, rx, rz):
        """The floor rule write_region applies to a region (for samplers)."""
        return self.floor_rule(self.maps(rx * 512, rz * 512, 512, 512))

    def write_region(self, path, rx, rz, level=9):
        d = self.dim
        x0, z0 = rx * 512, rz * 512
        m = self.maps(x0, z0, 512, 512)
        pieces = self.pieces_in(x0, z0, 512, 512)
        ivs = self.detail_intervals(m, pieces)
        lo = ivs[0][0]
        n_sec = d.height // 16
        # Only regions whose terrain really goes deep (sinkhole, sea, trench) get
        # rock all the way down; elsewhere bedrock closes the floor at y -64 like
        # the original map and the empty depth below is simply left out.
        floor = self.floor_rule(m)
        shallow = floor is not None
        self._floor = floor
        roof_top = (int(m["ceil"].max()) // 16) * 16 + 48 if d.ceiling_block else None
        s_min = d.min_y // 16
        secs = [[None] * n_sec for _ in range(1024)]       # [chunk][section] -> dict
        cache = {}
        ceil_max = int(m["ceil"].max()) if d.ceiling_block else None
        fluid_min = int(m["fluid"].min())
        nonair = 0
        # uniform sections outside the detail range
        for s in range(n_sec):
            ys0 = d.min_y + 16 * s
            if any(a <= ys0 < b for a, b in ivs):
                continue
            if ys0 < lo:
                if shallow:
                    continue                         # below the bedrock floor: left out (air)
                bid = int(d.lut()[ys0 - d.min_y])
                if ys0 == d.min_y:
                    bid = None                       # bedrock row: composed below
            elif d.ceiling_block and ys0 >= ceil_max:
                if ys0 >= roof_top:
                    continue                         # far above the cavern roof: left out
                bid = int(d.lut()[ys0 - d.min_y])
            elif fluid_min >= ys0 + 15 and ys0 > int(m["ground"].max()):
                bid = int(m["fluid_id"].flat[0])
            else:
                bid = 0
            if bid is None:
                continue
            for c in range(1024):
                cx, cz = c % 32, c // 32
                secs[c][s] = _uniform(bid, s + s_min, self.biome(rx * 32 + cx, rz * 32 + cz, s + s_min))
        # the bottom section (bedrock) when it is outside the detail range
        if lo > d.min_y and not shallow:
            V = self.fill(m, d.min_y, d.min_y + 16)
            self._encode_band(V, d.min_y, secs, rx, rz)
        for (a, b) in ivs:
            for y0 in range(a, b, 256):
                y1 = min(b, y0 + 256)
                V = self.compose(x0, z0, 512, 512, y0, y1, m, cache)
                nonair += int(np.count_nonzero(V))
                self._encode_band(V, y0, secs, rx, rz)
        _write_mca(path, rx, rz, secs, s_min, level)
        return nonair

    def _encode_band(self, V, y0, secs, rx, rz):
        s_min = self.dim.min_y // 16
        for k in range(V.shape[0] // 16):
            sy = (y0 // 16) + k
            si = sy - s_min
            band = V[k * 16:(k + 1) * 16]
            for c in range(1024):
                cx, cz = c % 32, c // 32
                sec = band[:, cz * 16:(cz + 1) * 16, cx * 16:(cx + 1) * 16]
                bio = self.biome(rx * 32 + cx, rz * 32 + cz, sy)
                if bio == "minecraft:plains" and not sec.any():
                    secs[c][si] = None                   # plain air: leave the section out
                    continue
                e = anvil.encode_section(sec, sy, bio)
                if bio == "minecraft:plains":
                    del e["biomes"]
                secs[c][si] = e


_UNI = {}


def _uniform(bid, sy, biome):
    """A single-block section; None for plain air (sections that are left out
    of a chunk are air - this keeps 3056-block columns small)."""
    if bid == 0 and biome == "minecraft:plains":
        return None
    k = (bid, sy, biome)
    e = _UNI.get(k)
    if e is None:
        e = {"Y": Byte(sy), "block_states": {"palette": List([anvil._palette_entry(bid)])}}
        if biome != "minecraft:plains":                  # plains is the game's default when "biomes" is absent
            e["biomes"] = {"palette": List([biome])}
        _UNI[k] = e
    return e


def _write_mca(path, rx, rz, secs, s_min, level):
    locs = bytearray(4096)
    stamps = bytearray(4096)
    body = bytearray()
    now = int(time.time())
    for c in range(1024):
        lx, lz = c % 32, c // 32
        root = {
            "DataVersion": Int(anvil.DATA_VERSION),
            "xPos": Int(rx * 32 + lx), "yPos": Int(s_min), "zPos": Int(rz * 32 + lz),
            "Status": "minecraft:full", "LastUpdate": Long(0), "InhabitedTime": Long(0), "isLightOn": Byte(0),
            "sections": List([s for s in secs[c] if s is not None], elem_tag=10),
            "block_entities": List([], elem_tag=10), "fluid_ticks": List([], elem_tag=10),
            "block_ticks": List([], elem_tag=10), "PostProcessing": List([], elem_tag=9),
            "structures": {"References": {}, "starts": {}}, "Heightmaps": {},
        }
        data = zlib.compress(nbt.dumps(root), level)
        blob = struct.pack(">IB", len(data) + 1, 2) + data
        blob += b"\0" * (-len(blob) % 4096)
        off = 2 + len(body) // 4096
        n = len(blob) // 4096
        if n >= 256:
            raise SystemExit(f"chunk {rx * 32 + lx},{rz * 32 + lz} too large ({len(blob)} bytes)")
        locs[4 * c:4 * c + 4] = struct.pack(">I", (off << 8) | n)
        stamps[4 * c:4 * c + 4] = struct.pack(">I", now)
        body += blob
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(locs)
        f.write(stamps)
        f.write(body)
    os.replace(tmp, path)


def regions_of(world, x0, z0, x1, z1):
    """Regions in a rectangle that differ from the generator."""
    out = []
    for rz in range(z0 // 512, -(-z1 // 512)):
        for rx in range(x0 // 512, -(-x1 // 512)):
            if world.touched(rx * 512, rz * 512, 512, 512):
                out.append((rx, rz))
    return out
