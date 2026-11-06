"""Minimal NBT writer/reader (Java Edition, big-endian)."""
from __future__ import annotations

import gzip
import io
import struct

import numpy as np


class _Num:
    __slots__ = ("v",)

    def __init__(self, v):
        self.v = v

    def __repr__(self):
        return f"{type(self).__name__}({self.v!r})"

    def __eq__(self, other):
        return type(self) is type(other) and self.v == other.v


class Byte(_Num): tag = 1; fmt = ">b"
class Short(_Num): tag = 2; fmt = ">h"
class Int(_Num): tag = 3; fmt = ">i"
class Long(_Num): tag = 4; fmt = ">q"
class Float(_Num): tag = 5; fmt = ">f"
class Double(_Num): tag = 6; fmt = ">d"


class ByteArray:
    tag = 7
    def __init__(self, a): self.a = np.asarray(a, dtype=">i1")


class IntArray:
    tag = 11
    def __init__(self, a): self.a = np.asarray(a, dtype=">i4")


class LongArray:
    tag = 12
    def __init__(self, a): self.a = np.asarray(a, dtype=">i8")


class List:
    tag = 9
    def __init__(self, items=(), elem_tag=None):
        self.items = list(items)
        self.elem_tag = elem_tag

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        return self.items[i]


def _tag_of(v):
    if isinstance(v, bool):
        return 1
    if isinstance(v, str):
        return 8
    if isinstance(v, dict):
        return 10
    if isinstance(v, int):
        return 3
    if isinstance(v, float):
        return 6
    return v.tag


def _w_str(out, s):
    b = s.encode("utf-8")  # (modified UTF-8 only differs for NUL / astral chars)
    out.write(struct.pack(">H", len(b)))
    out.write(b)


def _w_payload(out, v):
    t = _tag_of(v)
    if t == 8:
        _w_str(out, v)
    elif t == 10:
        for k, x in v.items():
            out.write(bytes([_tag_of(x)]))
            _w_str(out, k)
            _w_payload(out, x)
        out.write(b"\x00")
    elif isinstance(v, bool):
        out.write(struct.pack(">b", int(v)))
    elif isinstance(v, int):
        out.write(struct.pack(">i", v))
    elif isinstance(v, float):
        out.write(struct.pack(">d", v))
    elif isinstance(v, _Num):
        out.write(struct.pack(v.fmt, v.v))
    elif t == 9:
        et = v.elem_tag
        if et is None:
            et = _tag_of(v.items[0]) if v.items else 0
        out.write(bytes([et]))
        out.write(struct.pack(">i", len(v.items)))
        for x in v.items:
            _w_payload(out, x)
    elif t in (7, 11, 12):
        out.write(struct.pack(">i", len(v.a)))
        out.write(v.a.tobytes())
    else:
        raise TypeError(v)


def dumps(root: dict, name: str = "") -> bytes:
    out = io.BytesIO()
    out.write(b"\x0a")
    _w_str(out, name)
    _w_payload(out, root)
    return out.getvalue()


def write_gzip(path, root: dict):
    with open(path, "wb") as f:
        f.write(gzip.compress(dumps(root), 6))


# ---------------------------------------------------------------- reader (tests)
def _r_str(b, i):
    (n,) = struct.unpack_from(">H", b, i)
    return b[i + 2:i + 2 + n].decode("utf-8", "replace"), i + 2 + n


_FMT = {1: ">b", 2: ">h", 3: ">i", 4: ">q", 5: ">f", 6: ">d"}
_ARR = {7: ">i1", 11: ">i4", 12: ">i8"}


def _r_payload(b, i, t):
    if t in _FMT:
        f = _FMT[t]
        return struct.unpack_from(f, b, i)[0], i + struct.calcsize(f)
    if t == 8:
        return _r_str(b, i)
    if t in _ARR:
        (n,) = struct.unpack_from(">i", b, i)
        dt = np.dtype(_ARR[t])
        a = np.frombuffer(b, dt, n, i + 4)
        return a, i + 4 + n * dt.itemsize
    if t == 9:
        et = b[i]
        (n,) = struct.unpack_from(">i", b, i + 1)
        i += 5
        items = []
        for _ in range(n):
            x, i = _r_payload(b, i, et)
            items.append(x)
        return items, i
    if t == 10:
        d = {}
        while True:
            tt = b[i]
            i += 1
            if tt == 0:
                return d, i
            k, i = _r_str(b, i)
            d[k], i = _r_payload(b, i, tt)
    raise ValueError(t)


def loads(b: bytes):
    assert b[0] == 10
    _, i = _r_str(b, 1)
    return _r_payload(b, i, 10)[0]
