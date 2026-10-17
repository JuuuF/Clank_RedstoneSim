"""Prototype: two analog carry lines (G z=0, K z=2) with glass diodes, read comparators."""
import itertools, sys
sys.path.insert(0, "/home/justin/.claude/jobs/7b97722e/tmp/cca")
from run import run

N = 4
L = []
def put(c): L.append(c)
def block(x,y,z,b="stone"): put(f"set {x} {y} {z} {b}")
def wire(x,y,z): put(f"place {x} {y} {z} redstone_wire")
def place(x,y,z,w): put(f"place {x} {y} {z} {w}")

put("new size 48 force")
# G line z=0: segment for bit j: Gr (x0,3) on stone, glass x0+1 (dust 4), stone x0+2 (dust 4)
def line(dx, z, n):
    # starting stone-dust at x=dx-1 (CIN inject), then bits 0..n-1, then final read at bit n
    block(dx-1, 3, z); 
    for j in range(n+1):
        x0 = 3*j + dx
        block(x0, 2, z)
        if j < n:
            block(x0+1, 3, z, "glass"); block(x0+2, 3, z)
    wire(dx-1, 4, z)
    for j in range(n+1):
        x0 = 3*j + dx
        wire(x0, 3, z)
        if j < n:
            wire(x0+1, 4, z); wire(x0+2, 4, z)
line(0, 0, N)
line(1, 2, N)
# injections: G at glass-dust x0+1 from z=-1 (repeater south); K at x0+2 from z=3 (repeater north)
def inj(x, z, facing, zr, name):
    block(x, 3, z)                       # repeater support
    place(x, 4, z, f"repeater out={facing}")
    block(x, 4, zr)                      # lever block
    place(x, 5, zr, "lever face=floor")
    put(f"label {name} {x} 5 {zr}")
inj(-1, -1, "south", -2, "CG")
inj(0, 3, "north", 4, "CK")
for j in range(N):
    inj(3*j+1, -1, "south", -2, f"G{j}")
    inj(3*j+2, 3, "north", 4, f"K{j}")
# reads: R_j at (x0+1, 2, 0) facing east, spur (x0+1, 2, 1)
for j in range(N+1):
    x0 = 3*j
    block(x0+1, 1, 0); block(x0+1, 1, 1)
    place(x0+1, 2, 0, "comparator out=east mode=subtract")
    wire(x0+1, 2, 1)
    put(f"label C{j} {x0+1} 2 0")
put("settle")
ins = ["CG", "CK"] + [f"{t}{j}" for j in range(N) for t in "GK"]
rows = []
for cin in (0, 1):
    for bits in itertools.product("PGK", repeat=N):
        inp = [cin, 1-cin]
        for b in bits:
            inp += [1 if b == "G" else 0, 1 if b == "K" else 0]
        c = cin; outs = [c]
        for b in bits:
            c = 1 if b == "G" else 0 if b == "K" else c
            outs.append(c)
        rows.append("".join(map(str, inp)) + ":" + "".join(map(str, outs)))
put("target new carry \"C_j = nearest non-propagate below j is G (CIN as bit -1)\"")
put("target carry truth " + " ".join("@"+i for i in ins) + " -> " + " ".join(f"@C{j}" for j in range(N+1)) + " rows " + " ".join(rows))
put("check")
text = "\n".join(L) + "\n"
open("/home/justin/.claude/jobs/7b97722e/tmp/cca/exp.cli.txt", "w").write(text)
o = run(text)
import re
for line in o.splitlines():
    if line.startswith(("placed", "set ", "> place", "> set", "> label", "@", "> target", "labeled", "> new", "new ")):
        continue
    print(line[:300])
