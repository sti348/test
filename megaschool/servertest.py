"""Load a generated world in real vanilla servers and run console commands.

  python3 servertest.py <world_dir> <version> [command ...]

Server jars/JDKs are expected in ../build/servers (see README)."""
from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SRV = os.path.join(os.path.dirname(HERE), "build", "servers")


def java_for(ver):
    if ver.startswith("26"):
        return glob.glob(os.path.join(SRV, "jdk-25*", "bin", "java"))[0]
    return "java"


def run(world, ver, commands, timeout=900):
    d = os.path.join(SRV, f"run-{ver}")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    shutil.copytree(world, os.path.join(d, "world"))
    open(os.path.join(d, "eula.txt"), "w").write("eula=true\n")
    open(os.path.join(d, "server.properties"), "w").write(
        "online-mode=false\nlevel-name=world\nmax-tick-time=-1\nspawn-protection=0\n"
        "view-distance=4\nsimulation-distance=4\nenable-rcon=false\nlevel-type=flat\n")
    p = subprocess.Popen([java_for(ver), os.environ.get("MC_XMX", "-Xmx6G"), "-jar", os.path.join(SRV, f"server-{ver}.jar"), "nogui"],
                         cwd=d, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    lines = []
    done = threading.Event()

    def reader():
        for ln in p.stdout:
            lines.append(ln.rstrip())
            if "Done (" in ln:
                done.set()
    threading.Thread(target=reader, daemon=True).start()
    if not done.wait(timeout):
        p.kill()
        raise SystemExit("\n".join(lines[-50:]))
    start = len(lines)
    for c in commands:
        if c.startswith("sleep "):
            time.sleep(float(c.split()[1]))
            continue
        p.stdin.write(c + "\n")
        p.stdin.flush()
        time.sleep(0.4)
    time.sleep(2)
    p.stdin.write("stop\n")
    p.stdin.flush()
    p.wait(timeout)
    return lines, start


if __name__ == "__main__":
    lines, start = run(sys.argv[1], sys.argv[2], sys.argv[3:])
    bad = [l for l in lines if any(k in l for k in ("ERROR", "WARN", "Exception", "Couldn't", "Failed"))]
    print("---- warnings/errors ----")
    print("\n".join(bad[:80]))
    print("---- console after start ----")
    print("\n".join(lines[start:]))
