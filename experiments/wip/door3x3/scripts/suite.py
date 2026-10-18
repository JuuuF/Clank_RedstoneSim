"""python suite.py STAGE: lever-driven input-timing suite on a module build (door.py STAGE)."""
import subprocess, sys
CLI = "/home/justin/anaconda3/envs/redsim/bin/redsim-cli"
stage = sys.argv[1]
body = subprocess.run([sys.executable, "door.py", stage], capture_output=True, text=True, check=True).stdout
L = [body.rstrip()]
cells = [f"@D{x}{r}" for x in range(3) for r in range(3)]
def t(n, s): L.append(f"target {n} {s}")
for N in list(range(1, 31)):
    n = f"open{N}"
    L.append(f'target new {n} "lever on for {N} ticks, then a full cycle"')
    t(n, "do at 5 use @L"); t(n, f"do at {5 + N} use @L"); t(n, "do at 100 use @L"); t(n, "do at 160 use @L")
    for c in cells:
        t(n, f"expect {c} block=smooth_stone at 99"); t(n, f"expect {c} block=air at 140"); t(n, f"expect {c} block=smooth_stone at 190")
    n = f"close{N}"
    L.append(f'target new {n} "open, lever off for {N} ticks, then on (stays open), then off"')
    t(n, "do at 5 use @L"); t(n, "do at 60 use @L"); t(n, f"do at {60 + N} use @L"); t(n, "do at 160 use @L")
    for c in cells:
        t(n, f"expect {c} block=air at 155"); t(n, f"expect {c} block=smooth_stone at 190")
L.append("check")
out = subprocess.run([CLI, "suite.redsim.json"], input="\n".join(L) + "\n", capture_output=True, text=True).stdout
fails = [l.split()[1] for l in out.splitlines() if l.startswith("FAIL")]
print(stage, [l for l in out.splitlines() if l.startswith("check:")], "fails:", " ".join(fails))
