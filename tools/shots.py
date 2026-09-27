"""List shots with their start ticks (for picking preview frames)."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import script
F = script.build()
lo = int(sys.argv[1]) if len(sys.argv) > 1 else 0
hi = int(sys.argv[2]) if len(sys.argv) > 2 else 10**9
for (t0, t1, cam, name, scene) in sorted(F.shots):
    if lo <= t0 <= hi:
        print(f"{t0:6d} {t1:6d} {(t1-t0)/20:5.1f}s  {scene} / {name}")
