"""python measure.py STAGE [opts...]: build, check, and report when the doorway is solid / clear."""
import re, subprocess, sys
CLI = "/home/justin/anaconda3/envs/redsim/bin/redsim-cli"
src = subprocess.run([sys.executable, "door.py"] + sys.argv[1:], capture_output=True, text=True, check=True).stdout
out = subprocess.run([CLI, "m.redsim.json"], input=src, capture_output=True, text=True).stdout
chk = [l for l in out.splitlines() if l.startswith("check:") or "fail expect" in l or l.startswith("error")]
cells = [(x, y) for x in (0, 1, 2) for y in (4, 5, 6)]
cmd = "target cycle load; run 130; " + "; ".join(f"changes {x} {y} 0" for x, y in cells)
tr = subprocess.run([CLI, "m.redsim.json", "--dry-run", "-c", cmd], capture_output=True, text=True).stdout
R, F = 10, 70
solid, clear = 0, 0
for block in tr.split("\n")[0:]:
    pass
cur = None; hist = {}
for line in tr.splitlines():
    m = re.match(r"(\d+) (\d+) 0 \(ticks", line)
    if m:
        cur = (int(m[1]), int(m[2])); hist[cur] = []; continue
    m = re.match(r"\s+tick (\d+)\s+(\S+)", line)
    if m and cur:
        hist[cur].append((int(m[1]), m[2]))
for c, h in hist.items():
    s = max((t for t, b in h if b.startswith("smooth") and t < F), default=None)
    a = max((t for t, b in h if b == "air" and t >= F), default=None)
    solid = max(solid, s or 0); clear = max(clear, a or 0)
print(" ".join(sys.argv[1:]), "|", chk[0] if chk else "?", chk[1:3], f"| closed at R+{solid - R}, clear at F+{clear - F}")
