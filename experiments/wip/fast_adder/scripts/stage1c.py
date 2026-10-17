import itertools, sys
sys.path.insert(0, "/home/justin/.claude/jobs/7b97722e/tmp/cca")
from run import run
from design import emit
N = 4
L = ["new size 48 force"]
lines, cells = emit(N)
L += lines
for j in range(-1, N):
    x0 = 3*j
    L += [f"place {x0+3} 6 -1 lever face=floor", f"label nG{j} {x0+3} 6 -1",
          f"place {x0+2} 6 5 lever face=floor", f"label nX{j} {x0+2} 6 5"]
    if j >= 0:
        L += [f"set {x0+2} 4 -5 stone", f"set {x0} 3 -6 stone", f"set {x0+1} 3 -8 stone",
              f"place {x0} 4 -5 redstone_wire", f"place {x0} 4 -6 lever face=floor", f"label nHa{j} {x0} 4 -6",
              f"place {x0+1} 4 -7 redstone_wire", f"place {x0+1} 4 -8 lever face=floor", f"label nHb{j} {x0+1} 4 -8",
              f"label S{j} {x0+1} 4 -4"]
L += [f"label R4 {3*N+1} 3 0", "settle"]
ins = ["nG-1", "nX-1"] + [f"{t}{j}" for j in range(N) for t in ("nG", "nX", "nHa", "nHb")]
rows = []
for cin in (0, 1):
    for bits in itertools.product("PGK", repeat=N):
        inp = [1-cin, cin]
        c = cin; outs = []
        for b in bits:
            g, k, h = b == "G", b == "K", b == "P"
            inp += [int(not g), int(not k), int(not h), int(not h)]
            outs.append(int(h) ^ c)
            c = 1 if g else 0 if k else c
        outs.append(c)
        rows.append("".join(map(str, inp)) + ":" + "".join(map(str, outs)))
L += ['target new sum "S_j = H_j xor C_j, C4"',
      "target sum truth " + " ".join("@"+i for i in ins) + " -> " + " ".join(f"@S{j}" for j in range(N)) + " @R4 rows " + " ".join(rows) + " settle 14",
      "check"]
o = run("\n".join(L) + "\n", "/home/justin/.claude/jobs/7b97722e/tmp/cca/s1c.redsim.json")
n = 0
for line in o.splitlines():
    if line.startswith(("error", "note", "check", "FAIL", "settled")) or "error" in line:
        n += 1
        if n < 12: print(line[:300])
