"""Stage 1: lines + reads + C path + XOR per bit; G/K/H driven by (inverted) levers."""
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
# ---- supports and structure first
for j in range(-1, N+1):
    x0 = 3*j
    if j >= 0:
        block(x0, 3, 0)                       # Gr support
        block(x0+1, 3, 2)                     # Kr support
        block(x0+1, 2, 0); block(x0+1, 2, 1)  # R and spur supports
    if 0 <= j < N:
        block(x0+1, 4, 0, "glass"); block(x0+2, 4, 0)   # G glass, G stone
        block(x0+2, 4, 2, "glass"); block(x0+3, 4, 2)   # K glass, K stone
    if j == -1:
        block(-1, 4, 0)                        # G start stone
        block(-1, 4, 2, "glass"); block(0, 4, 2)  # K start glass + stone
    if j < N:
        block(x0+2, 5, -2)   # GB'
        block(x0+2, 6, 1)    # KB
    if 0 <= j < N:
        for p in [(x0+2,2,0),(x0+2,2,-1),(x0+1,3,-1),(x0+1,5,-1),(x0+2,2,-2),(x0+2,3,-3),
                  (x0+1,2,-2),(x0+1,2,-3),(x0,2,-3),(x0,2,-4),(x0+1,3,-4),(x0+2,2,-4),
                  (x0+1,2,-5),(x0+2,2,-5),(x0+1,2,-6)]:
            block(*p)
# ---- wires and components
for j in range(-1, N+1):
    x0 = 3*j
    if j >= 0:
        wire(x0, 4, 0)            # Gr
        wire(x0+1, 4, 2)          # Kr
        place(x0+1, 3, 0, "comparator out=east mode=subtract")   # R
        wire(x0+1, 3, 1)          # spur
        put(f"label R{j} {x0+1} 3 0")
    if 0 <= j < N:
        wire(x0+1, 5, 0); wire(x0+2, 5, 0)     # Gi, Gs
        wire(x0+2, 5, 2); wire(x0+3, 5, 2)     # Ki, Ks
    if j == -1:
        wire(-1, 5, 0); wire(-1, 5, 2); wire(0, 5, 2)
    if j < N:
        place(x0+2, 5, -1, "redstone_wall_torch facing=south")   # G torch on GB'
        place(x0+2, 6, 2, "redstone_wall_torch facing=south")   # K torch on KB
        place(x0+2, 6, -2, "lever face=floor"); put(f"label nG{j} {x0+2} 6 -2")
        place(x0+2, 7, 1, "lever face=floor"); put(f"label nK{j} {x0+2} 7 1")
    if 0 <= j < N:
        wire(x0+2, 3, 0)          # YC (C dust under the G stone)
        wire(x0+2, 3, -1)         # c2
        wire(x0+1, 4, -1)         # c3 on B1
        wire(x0+2, 3, -2)         # c2'
        place(x0+1, 3, -2, "repeater out=north")   # C-rep-a
        place(x0+1, 3, -3, "comparator out=north mode=subtract")  # C1 = C - H
        wire(x0, 3, -3)           # H dust (C1 side)
        place(x0, 3, -4, "redstone_torch")          # H torch 2
        wire(x0+1, 4, -4); put(f"label S{j} {x0+1} 4 -4")
        place(x0+2, 3, -4, "repeater out=north")   # C-rep-d
        place(x0+1, 3, -5, "comparator out=south mode=subtract")  # C2 = H - C
        wire(x0+2, 3, -5)         # C2 side dust
        place(x0+1, 3, -6, "redstone_torch")        # H torch 1 (C2 rear)
        place(x0, 2, -5, "lever face=wall facing=north"); put(f"label nHa{j} {x0} 2 -5")
        place(x0+1, 2, -7, "lever face=wall facing=north"); put(f"label nHb{j} {x0+1} 2 -7")
put("settle")
ins = ["nG-1", "nK-1"] + [f"{t}{j}" for j in range(N) for t in ("nG", "nK", "nHa", "nHb")]
rows = []
for cin in (0, 1):
    for bits in itertools.product("PGK", repeat=N):
        inp = [1-cin, cin]           # nG, nK for CIN
        c = cin; outs = []
        for b in bits:
            g, k = b == "G", b == "K"
            h = b == "P"
            inp += [int(not g), int(not k), int(not h), int(not h)]
            outs.append(int(h) ^ c)
            c = 1 if g else 0 if k else c
        outs.append(c)
        rows.append("".join(map(str, inp)) + ":" + "".join(map(str, outs)))
put('target new sum "S_j = H_j xor C_j, C4"')
put("target sum truth " + " ".join("@"+i for i in ins) + " -> " + " ".join(f"@S{j}" for j in range(N)) + " @R4 rows " + " ".join(rows))
put("check")
text = "\n".join(L) + "\n"
open("/home/justin/.claude/jobs/7b97722e/tmp/cca/stage1b.cli.txt", "w").write(text)
o = run(text, "/home/justin/.claude/jobs/7b97722e/tmp/cca/s1b.redsim.json")
fails = 0
for line in o.splitlines():
    if line.startswith(("placed", "set ", "> place", "> set", "> label", "@", "> target", "labeled", "> new", "new ", "PASS")):
        continue
    if line.startswith("FAIL"):
        fails += 1
        if fails > 6: continue
    print(line[:400])
