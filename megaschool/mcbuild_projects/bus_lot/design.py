"""校车停车场 - see ../../mcbuild_designs.py (bus_lot).  Run with `mcb design -p .`"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from mcbuild import Build, get_project
import mcbuild_designs as D

P = get_project()
B = Build(P.site(), P.name)
F = B.frame(tuple(P.cfg["design"]["origin"]), turns=P.cfg["design"].get("turns", 0))
INFO = D.bus_lot(F)
B.notes.append("无涯中学 校车停车场：由 megaschool/mcbuild_designs.py 生成，放进地图时按地块左上角对齐。")
