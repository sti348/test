"""Static check of the generated data pack against the real command trees and
registries of Minecraft versions (from misode/mcmeta "summary" data).

  python3 tools/validate_mc.py 1.21.10 26.3

Checks every command's literals/argument structure, block ids + block state
properties, item ids, entity types, particle ids, sound events, game rules and
the camera-overlay / model ids against the resource pack."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "build", "cache", "mcmeta")
DP = os.path.join(ROOT, "datapack", "data")
RP = os.path.join(ROOT, "resourcepack", "assets")
_sj = os.path.join(RP, "kino", "sounds.json")
RP_SOUNDS = json.load(open(_sj)) if os.path.exists(_sj) else {}


def load(ver, what):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, f"{ver}_{what}.json")
    if not os.path.exists(p):
        subprocess.check_call(["curl", "-sSf", "-o", p, f"https://raw.githubusercontent.com/misode/mcmeta/{ver}-summary/{what}/data.json"])
    return json.load(open(p))


def tokenize(s):
    out, cur, depth, q = [], "", 0, None
    i = 0
    while i < len(s):
        ch = s[i]
        if q:
            cur += ch
            if ch == "\\" and i + 1 < len(s):
                cur += s[i + 1]
                i += 2
                continue
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
            cur += ch
        elif ch in "[{(":
            depth += 1
            cur += ch
        elif ch in "]})":
            depth -= 1
            cur += ch
        elif ch == " " and depth == 0:
            if cur:
                out.append(cur)
            cur = ""
        else:
            cur += ch
        i += 1
    if cur:
        out.append(cur)
    return out


def ns(x):
    return x if ":" in x else "minecraft:" + x


class Checker:
    def __init__(self, ver):
        self.ver = ver
        self.tree = load(ver, "commands")
        reg = load(ver, "registries")
        self.reg = {k: set(ns(v) for v in vals) for k, vals in reg.items()}
        self.blocks = {ns(k): v for k, v in load(ver, "blocks").items()}
        self.errors = Counter()
        self.examples = {}

    def err(self, kind, line):
        self.errors[kind] += 1
        self.examples.setdefault(kind, line)

    # ---- argument semantics ------------------------------------------
    def check_block(self, tok, line):
        m = re.match(r"^([a-z0-9_:./-]+)(\[(.*)\])?(\{.*\})?$", tok)
        if not m:
            self.err("bad block syntax", line)
            return
        bid = ns(m.group(1))
        if bid not in self.blocks:
            self.err(f"unknown block {bid}", line)
            return
        props, _defaults = self.blocks[bid]
        if m.group(3):
            for kv in m.group(3).split(","):
                if "=" not in kv:
                    self.err("bad block state", line)
                    continue
                k, v = kv.split("=", 1)
                if k not in props:
                    self.err(f"{bid} has no property {k}", line)
                elif v not in props[k]:
                    self.err(f"{bid}[{k}={v}] invalid value", line)

    def check_item(self, tok, line):
        m = re.match(r"^([a-z0-9_:./-]+)", tok)
        iid = ns(m.group(1)) if m else None
        if iid not in self.reg["item"]:
            self.err(f"unknown item {iid}", line)
        for comp in re.findall(r"[\[,]((?:minecraft:)?[a-z_]+)=", tok.split("{")[0] if False else tok):
            cid = ns(comp)
            if "data_component_type" in self.reg and cid not in self.reg["data_component_type"]:
                self.err(f"unknown item component {cid}", line)

    def arg(self, node, toks, i, line):
        """Consume tokens for an argument node; return new index or None."""
        parser = node.get("parser")
        props = node.get("properties", {})
        n = {"minecraft:vec3": 3, "minecraft:block_pos": 3, "minecraft:vec2": 2, "minecraft:rotation": 2,
             "minecraft:column_pos": 2}.get(parser, 1)
        if parser in ("minecraft:message",) or (parser == "brigadier:string" and props.get("type") == "greedy"):
            return len(toks)
        if i + n > len(toks):
            return None
        vals = toks[i:i + n]
        t = vals[0]
        if parser in ("minecraft:vec3", "minecraft:block_pos", "minecraft:vec2", "minecraft:rotation", "minecraft:column_pos"):
            for v in vals:
                if not re.match(r"^[~^]?-?(\d+(\.\d*)?|\.\d+)?$", v):
                    return None
        elif parser in ("brigadier:integer",):
            if not re.match(r"^-?\d+$", t):
                return None
        elif parser in ("brigadier:float", "brigadier:double"):
            if not re.match(r"^-?(\d+(\.\d*)?|\.\d+)$", t):
                return None
            if "min" in props and float(t) < props["min"] or "max" in props and float(t) > props["max"]:
                self.err(f"number out of range for {parser}", line)
        elif parser in ("minecraft:block_state", "minecraft:block_predicate"):
            self.check_block(t, line)
        elif parser in ("minecraft:item_stack", "minecraft:item_predicate"):
            self.check_item(t, line)
        elif parser == "minecraft:particle":
            pid = ns(re.match(r"^[a-z0-9_:]+", t).group(0))
            if pid not in self.reg["particle_type"]:
                self.err(f"unknown particle {pid}", line)
        elif parser == "minecraft:resource" or parser == "minecraft:resource_key":
            regname = props.get("registry", "").replace("minecraft:", "")
            if regname in self.reg and ns(t) not in self.reg[regname]:
                self.err(f"unknown {regname} {t}", line)
        elif parser == "minecraft:entity":
            if not (t.startswith("@") or re.match(r"^[A-Za-z0-9_-]+$", t)):
                return None
        elif parser in ("minecraft:nbt_compound_tag", "minecraft:component", "minecraft:style"):
            if parser == "minecraft:nbt_compound_tag" and not t.startswith("{"):
                return None
        return i + n

    def walk(self, node, toks, i, line):
        """Return True if toks[i:] matches the subtree (node already consumed)."""
        if i == len(toks):
            return node.get("executable", False) or ("redirect" in node and False)
        if "redirect" in node:
            target = self.tree
            for p in node["redirect"]:
                target = target["children"][p]
            node = target
        kids = node.get("children", {})
        tok = toks[i]
        if tok in kids and kids[tok]["type"] == "literal":
            if tok == "run" and not kids[tok].get("children"):
                return self.command(toks[i + 1:], line)
            return self.walk(kids[tok], toks, i + 1, line)
        for name, child in kids.items():
            if child["type"] != "argument":
                continue
            j = self.arg(child, toks, i, line)
            if j is not None and self.walk(child, toks, j, line):
                return True
        return False

    def command(self, toks, line):
        if not toks:
            return False
        head = toks[0]
        if head not in self.tree["children"]:
            self.err(f"unknown command {head}", line)
            return True
        return self.walk(self.tree["children"][head], toks, 1, line)

    def check_line(self, line):
        line = line.strip()
        if not line or line.startswith("#"):
            return
        if line.startswith("$"):
            line = re.sub(r"\$\(\w+\)", "1", line[1:])
        toks = tokenize(line)
        if toks[0] == "gamerule" and len(toks) > 1 and toks[1] not in self.tree["children"]["gamerule"]["children"]:
            self.err(f"unknown gamerule {toks[1]}", line)
            return
        if not self.command(toks, line):
            self.err(f"syntax: {toks[0]} {toks[1] if len(toks) > 1 else ''}", line)
        for k, t in enumerate(toks[:-1]):
            if t == "playsound":
                sid = ns(toks[k + 1])
                if sid.startswith("kino:"):
                    if sid[5:] not in RP_SOUNDS:
                        self.err(f"sound {sid} missing from the resource pack", line)
                elif sid not in self.reg["sound_event"]:
                    self.err(f"unknown sound {toks[k + 1]}", line)


def resource_checks(lines):
    """Model / texture ids referenced by commands must exist in the resource pack."""
    missing = Counter()
    for line in lines:
        for m in re.findall(r'item_model"?[=:]"kino:([a-z_]+)"', line):
            if not os.path.exists(os.path.join(RP, "kino", "items", m + ".json")):
                missing[f"item model kino:{m}"] += 1
        for m in re.findall(r'texture:"kino:([a-z_/]+)"', line):
            if not os.path.exists(os.path.join(RP, "kino", "textures", m + ".png")):
                missing[f"texture kino:{m}"] += 1
        for m in re.findall(r'camera_overlay:"kino:([a-z_/]+)"', line):
            if not os.path.exists(os.path.join(RP, "kino", "textures", m + ".png")):
                missing[f"overlay kino:{m}"] += 1
    for ev, entry in RP_SOUNDS.items():
        for snd in entry["sounds"]:
            name = snd if isinstance(snd, str) else snd["name"]
            if not os.path.exists(os.path.join(RP, "kino", "sounds", name.split(":", 1)[1] + ".ogg")):
                missing[f"sound file {name} (event kino:{ev})"] += 1
    return missing


def main():
    versions = sys.argv[1:] or ["1.21.10", "26.3"]
    files = []
    for base, _, fs in os.walk(DP):
        for f in fs:
            if f.endswith(".mcfunction"):
                files.append(os.path.join(base, f))
    lines_by_file = {f: open(f, encoding="utf-8").read().splitlines() for f in files}
    uniq = {}
    for f, ls in lines_by_file.items():
        for l in ls:
            uniq.setdefault(l, f)
    print(f"{len(files)} functions, {sum(len(v) for v in lines_by_file.values())} lines, {len(uniq)} distinct lines")
    miss = resource_checks(uniq.keys())
    for k, v in miss.items():
        print(f"  MISSING {k} ({v}x)")
    ok = True
    for ver in versions:
        c = Checker(ver)
        per_file_bad = defaultdict(int)
        for l, f in uniq.items():
            before = sum(c.errors.values())
            c.check_line(l)
            if sum(c.errors.values()) > before:
                per_file_bad[os.path.relpath(f, DP)] += 1
        print(f"== {ver}: {sum(c.errors.values())} problems")
        for kind, n in c.errors.most_common():
            print(f"  {n:5d}  {kind}\n         e.g. {c.examples[kind][:220]}")
        rules_only = all("rules/" in f for f in per_file_bad)
        if c.errors and not rules_only:
            ok = False
        elif c.errors:
            print("  (only inside rules/* functions, which are version-specific on purpose)")
    sys.exit(0 if ok and not miss else 1)


if __name__ == "__main__":
    main()
