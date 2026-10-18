"""Fast adder round 2, stage 1: the lever core (nG, nX levers) with nH derived on top of the core:
a wire line over the G torch's and the X torch's above-blocks (G or K), a delay repeater, and
two descents into the H torch blocks."""
import itertools, subprocess, sys
from design import emit
N = 4
L = ["new size 48 force"]
lines, cells = emit(N)
L += lines
for j in range(-1, N):
    x0 = 3 * j
    L += [f"place {x0+3} 6 -1 lever face=floor", f"label nG{j} {x0+3} 6 -1",
          f"place {x0+2} 6 5 lever face=floor", f"label nX{j} {x0+2} 6 5"]
    if j < 0:
        continue
    X = x0 + 2
    for z in range(-8, 5):                      # the nH line on blocks (x0+2, 6, z), z -8..4
        if z == -4:
            L += [f"set {X} 6 {z} stone", f"place {X} 7 {z} repeater out=north"]
        else:
            L += [f"set {X} 6 {z} stone", f"place {X} 7 {z} redstone_wire"]
    # nHa: (X,7,-6) -> (x0+1,6,-6) -> (x0,5,-6) -> (x0,4,-5) on HB2
    L += [f"set {x0+1} 5 -6 stone", f"place {x0+1} 6 -6 redstone_wire",
          f"set {x0} 4 -6 stone", f"place {x0} 5 -6 redstone_wire",
          f"place {x0} 4 -5 redstone_wire"]
    # nHb: (X,7,-8) -> (X,6,-9) -> (x0+1,6,-9) -> (x0+1,5,-8) -> (x0+1,4,-7) on HB1
    L += [f"set {X} 5 -9 stone", f"place {X} 6 -9 redstone_wire",
          f"set {x0+1} 5 -9 stone", f"place {x0+1} 6 -9 redstone_wire",
          f"set {x0+1} 4 -8 stone", f"place {x0+1} 5 -8 redstone_wire",
          f"place {x0+1} 4 -7 redstone_wire"]
    L += [f"set {x0+2} 4 -5 stone", f"label S{j} {x0+1} 4 -4"]
L += [f"label R4 {3*N+1} 3 0", "settle"]
ins = ["nG-1", "nX-1"] + [f"{t}{j}" for j in range(N) for t in ("nG", "nX")]
rows = []
for cin in (0, 1):
    for bits in itertools.product("PGK", repeat=N):
        inp = [1 - cin, cin]; c = cin; outs = []
        for b in bits:
            g, k, h = b == "G", b == "K", b == "P"
            inp += [int(not g), int(not k)]
            outs.append(int(h) ^ c)
            c = 1 if g else 0 if k else c
        outs.append(c)
        rows.append("".join(map(str, inp)) + ":" + "".join(map(str, outs)))
L += ['target new sum "S_j = H_j xor C_j, C4 (nH derived)"',
      "target sum truth " + " ".join("@" + i for i in ins) + " -> " + " ".join(f"@S{j}" for j in range(N)) + " @R4 rows " + " ".join(rows) + " settle 16",
      "check"]
open("s1.cli.txt", "w").write("\n".join(L) + "\n")
