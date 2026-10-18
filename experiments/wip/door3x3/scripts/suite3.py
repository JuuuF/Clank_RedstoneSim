"""python suite3.py STAGE [N] [SEED]: random lever sequences; afterwards the door must match the lever and still work."""
import random, subprocess, sys
CLI = "/home/justin/anaconda3/envs/redsim/bin/redsim-cli"
stage = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 40; rnd = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 1)
body = subprocess.run([sys.executable, "door.py", stage], capture_output=True, text=True, check=True).stdout
L = [body.rstrip()]
cells = [f"@D{x}{r}" for x in range(3) for r in range(3)]
for i in range(n):
    t, ts = 5, []
    for _ in range(rnd.randint(2, 9)):
        ts.append(t); t += rnd.randint(1, 40)
    on = len(ts) % 2 == 1                       # lever state after the sequence (starts off)
    end = ts[-1] + 100
    name = f"rand{i}"
    L.append(f'target new {name} "random flips {ts}, then the door must match the lever and cycle"')
    for x in ts:
        L.append(f"target {name} do at {x} use @L")
    L.append(f"target {name} do at {end} use @L")
    L.append(f"target {name} do at {end + 70} use @L")
    a, b = ("air", "smooth_stone") if on else ("smooth_stone", "air")
    for c in cells:
        L.append(f"target {name} expect {c} block={a} at {end - 1}")
        L.append(f"target {name} expect {c} block={b} at {end + 60}")
        L.append(f"target {name} expect {c} block={a} at {end + 130}")
L.append("check")
out = subprocess.run([CLI, f"suite3_{stage}.redsim.json"], input="\n".join(L) + "\n", capture_output=True, text=True).stdout
print(stage, [l for l in out.splitlines() if l.startswith("check:")], "fails:", " ".join(l.split()[1] for l in out.splitlines() if l.startswith("FAIL")))
