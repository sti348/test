"""巨型地狱门（下界） - see ../../mcbuild_regions.py (nether_gate).  Run with `mcb design -p .`"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from mcbuild import Build, get_project
P = get_project()
B = Build(P.site(), P.name)
F = B.frame(tuple(P.cfg["design"]["origin"]), turns=P.cfg["design"].get("turns", 0))
import mcbuild_regions as M
INFO = M.nether_gate(F, **{'nether': True})
B.notes.append("无涯中学 巨型地狱门（下界）：由 megaschool/mcbuild_designs.py 生成，放进地图时按地块左上角对齐。")
