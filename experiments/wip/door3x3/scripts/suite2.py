"""python suite2.py STAGE: close, quick re-open after N1, quick re-close after N2; must end closed and still work."""
import subprocess, sys
CLI = "/home/justin/anaconda3/envs/redsim/bin/redsim-cli"
body = subprocess.run([sys.executable, "door.py", sys.argv[1]], capture_output=True, text=True, check=True).stdout
L = [body.rstrip()]
cells = [f"@D{x}{r}" for x in range(3) for r in range(3)]
for N1 in (10, 12, 14, 16, 18, 20, 22, 24, 26):
    for N2 in (2, 4, 6, 8, 12):
        n = f"r{N1}_{N2}"
        L.append(f'target new {n} "open 5, close 60, re-open +{N1}, re-close +{N2}, then open 200 and close 260"')
        for t in (5, 60, 60 + N1, 60 + N1 + N2, 200, 260):
            L.append(f"target {n} do at {t} use @L")
        for c in cells:
            L.append(f"target {n} expect {c} block=smooth_stone at 199")
            L.append(f"target {n} expect {c} block=air at 245")
            L.append(f"target {n} expect {c} block=smooth_stone at 290")
L.append("check")
out = subprocess.run([CLI, "suite2.redsim.json"], input="\n".join(L) + "\n", capture_output=True, text=True).stdout
print(sys.argv[1], [l for l in out.splitlines() if l.startswith("check:")], "fails:", " ".join(l.split()[1] for l in out.splitlines() if l.startswith("FAIL")))
