"""Block registry, chunk-section encoding and .mca region writing.

Chunks are written in the 1.20.1 format (DataVersion 3465); every newer game
version upgrades them on load."""
from __future__ import annotations

import os
import struct
import time
import zlib

import numpy as np

import nbt
from nbt import Byte, Int, List, Long, LongArray

DATA_VERSION = 3465          # 1.20.1
MIN_Y = -64
HEIGHT = 384
N_SECTIONS = HEIGHT // 16    # 24, Y = -4 .. 19

# ------------------------------------------------------------------ registry
_NAMES: list[str] = ["minecraft:air"]
_IDS: dict[str, int] = {"minecraft:air": 0}


def B(name: str) -> int:
    """Block-state string ('white_concrete', 'oak_leaves[persistent=true]') -> id."""
    if ":" not in name.split("[")[0]:
        name = "minecraft:" + name
    i = _IDS.get(name)
    if i is None:
        i = len(_NAMES)
        _NAMES.append(name)
        _IDS[name] = i
    return i


def name_of(i: int) -> str:
    return _NAMES[i]


def all_names():
    return list(_NAMES)


_PAL_CACHE: dict[int, dict] = {}


def _palette_entry(i: int) -> dict:
    e = _PAL_CACHE.get(i)
    if e is None:
        s = _NAMES[i]
        if "[" in s:
            base, props = s[:-1].split("[", 1)
            p = {}
            for kv in props.split(","):
                k, v = kv.split("=")
                p[k] = v
            e = {"Name": base, "Properties": p}
        else:
            e = {"Name": s}
        _PAL_CACHE[i] = e
    return e


# ------------------------------------------------------------------ encoding
def _pack(indices: np.ndarray, bits: int) -> np.ndarray:
    vpl = 64 // bits
    n = len(indices)
    nlongs = (n + vpl - 1) // vpl
    pad = nlongs * vpl - n
    idx = indices.astype(np.uint64)
    if pad:
        idx = np.concatenate([idx, np.zeros(pad, np.uint64)])
    idx = idx.reshape(nlongs, vpl)
    shifts = (np.arange(vpl, dtype=np.uint64) * np.uint64(bits))
    packed = np.bitwise_or.reduce(idx << shifts, axis=1)
    return packed.view(np.int64)


def encode_section(sec: np.ndarray, y: int, biome: str = "minecraft:plains") -> dict:
    """sec: (16,16,16) uint16 indexed [y,z,x]."""
    flat = sec.reshape(-1)
    lo = flat.min()
    if lo == flat.max():
        bs = {"palette": List([_palette_entry(int(lo))])}
    else:
        pal, inv = np.unique(flat, return_inverse=True)
        bits = max(4, int(len(pal) - 1).bit_length())
        bs = {"palette": List([_palette_entry(int(p)) for p in pal]),
              "data": LongArray(_pack(inv, bits))}
    return {"Y": Byte(y), "block_states": bs,
            "biomes": {"palette": List([biome])}}


def encode_chunk(col: np.ndarray, cx: int, cz: int) -> bytes:
    """col: (384,16,16) uint16 [y,z,x] for chunk (cx, cz) in world chunk coords."""
    sections = List([encode_section(col[s * 16:(s + 1) * 16], s + MIN_Y // 16)
                     for s in range(N_SECTIONS)], elem_tag=10)
    root = {
        "DataVersion": Int(DATA_VERSION),
        "xPos": Int(cx), "yPos": Int(MIN_Y // 16), "zPos": Int(cz),
        "Status": "minecraft:full",
        "LastUpdate": Long(0),
        "InhabitedTime": Long(0),
        "isLightOn": Byte(0),
        "sections": sections,
        "block_entities": List([], elem_tag=10),
        "fluid_ticks": List([], elem_tag=10),
        "block_ticks": List([], elem_tag=10),
        "PostProcessing": List([], elem_tag=9),
        "structures": {"References": {}, "starts": {}},
        "Heightmaps": {},
    }
    return nbt.dumps(root)


def write_region(path: str, rx: int, rz: int, R: np.ndarray, level: int = 6):
    """R: (384, 512, 512) uint16 [y,z,x] covering region (rx, rz)."""
    assert R.shape == (HEIGHT, 512, 512)
    locs = bytearray(4096)
    stamps = bytearray(4096)
    body = bytearray()
    now = int(time.time())
    for lz in range(32):
        for lx in range(32):
            col = R[:, lz * 16:(lz + 1) * 16, lx * 16:(lx + 1) * 16]
            data = zlib.compress(encode_chunk(col, rx * 32 + lx, rz * 32 + lz), level)
            blob = struct.pack(">IB", len(data) + 1, 2) + data
            blob += b"\0" * (-len(blob) % 4096)
            off = 2 + len(body) // 4096
            n = len(blob) // 4096
            assert n < 256
            i = 4 * (lx + lz * 32)
            locs[i:i + 4] = struct.pack(">I", (off << 8) | n)
            stamps[i:i + 4] = struct.pack(">I", now)
            body += blob
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(locs)
        f.write(stamps)
        f.write(body)
    os.replace(tmp, path)


# ------------------------------------------------------------------ reading (tests)
def read_chunk(path: str, lx: int, lz: int) -> dict | None:
    with open(path, "rb") as f:
        b = f.read()
    (loc,) = struct.unpack_from(">I", b, 4 * (lx + lz * 32))
    off = loc >> 8
    if not off:
        return None
    ln, comp = struct.unpack_from(">IB", b, off * 4096)
    assert comp == 2
    return nbt.loads(zlib.decompress(b[off * 4096 + 5: off * 4096 + 4 + ln]))


def decode_section(sec: dict) -> list[str]:
    bs = sec["block_states"]
    pal = [p["Name"] + ("[" + ",".join(f"{k}={v}" for k, v in sorted(p.get("Properties", {}).items())) + "]"
                        if p.get("Properties") else "") for p in bs["palette"]]
    if "data" not in bs:
        return [pal[0]] * 4096
    bits = max(4, (len(pal) - 1).bit_length())
    vpl = 64 // bits
    out = []
    mask = (1 << bits) - 1
    for v in bs["data"]:
        v = int(v) & (2 ** 64 - 1)
        for k in range(vpl):
            out.append(pal[(v >> (k * bits)) & mask])
    return out[:4096]
