"""python rtest.py WORLD MIN SEED: 60 random lever sequences on a lockout world (lever @L, output @OUT); every
output level must last >= MIN ticks and the output must end equal to the lever."""
import random, re, subprocess, sys
R = "/home/justin/anaconda3/envs/redsim/bin/redsim-cli"
world = sys.argv[1]; MIN = int(sys.argv[2]); rnd = random.Random(int(sys.argv[3]))
bad = 0
for i in range(60):
    t, ts = 5, []
    for _ in range(rnd.randint(1, 12)):
        ts.append(t); t += rnd.choice([rnd.randint(1, 6), rnd.randint(1, 45)])
    end = ts[-1] + MIN + 20
    cmds = [f"at {x} use @L" for x in ts] + [f"run {end}", "changes @OUT"]
    out = subprocess.run([R, world, "--dry-run", "-c", "; ".join(cmds)], capture_output=True, text=True).stdout
    ev = [(int(m[1]), m[2] == "true") for m in re.finditer(r"tick (\d+)\s+repeater\[.*?powered=(\w+)\]", out)][1:]
    final = ev[-1][1] if ev else False
    want = len(ts) % 2 == 1
    durs = [b[0] - a[0] for a, b in zip(ev, ev[1:])]
    ok = final == want and all(d >= MIN for d in durs)
    if not ok:
        bad += 1
        print("FAIL", ts, ev)
print(world, "60 sequences,", bad, "bad")
