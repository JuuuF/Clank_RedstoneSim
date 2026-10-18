"""Fast adder round 2, stage 2: input logic. Even bits at the back (A, B -> the X torch's block
from two sides; A and B also end in blocks with the not-A / not-B torches, whose above-blocks
carry nG at y=8; nG runs over the core in column x0+3 and descends at the front into the G
torch's block). Odd bits (and CIN) still with levers, unless ODD_LOGIC."""
import itertools, sys
from design import emit
N = 4
ODD = "odd" in sys.argv
L = ["new size 64 force"]
lines, cells = emit(N)
L += lines
def S(x, y, z, b="stone"): L.append(f"set {x} {y} {z} {b}")
def W(x, y, z): L.append(f"place {x} {y} {z} redstone_wire")
def nh_network(x0):
    X = x0 + 2
    for z in range(-8, 5):
        S(X, 6, z)
        L.append(f"place {X} 7 {z} " + ("repeater out=north" if z == -4 else "redstone_wire"))
    S(x0+1, 5, -6); W(x0+1, 6, -6); S(x0, 4, -6); W(x0, 5, -6); W(x0, 4, -5)
    S(X, 5, -9); W(X, 6, -9); S(x0+1, 5, -9); W(x0+1, 6, -9); S(x0+1, 4, -8); W(x0+1, 5, -8); W(x0+1, 4, -7)
    S(x0+2, 4, -5)
def ng_run(x0, z_from):
    """nG at y=8: north along column x0+1 from z_from to -10, east to x0+3, back south to -6,
    then the descent into GB (x0+3,5,-1) from its north side."""
    M, C = x0 + 1, x0 + 3
    for z in range(z_from, -11, -1):
        S(M, 7, z, "glass" if z in (-6, -9) else "stone"); W(M, 8, z)   # glass: the nH steps below need air over them
    for x in (x0 + 2, C):
        S(x, 7, -10); W(x, 8, -10)
    for z in range(-9, -5):
        S(C, 7, z); W(C, 8, z)
    for z in range(-8, 5):
        S(x0 + 2, 8, z)                       # cut: the nH line below must not join nG
    S(C, 6, -5); W(C, 7, -5); S(C, 5, -4); W(C, 6, -4); S(C, 4, -3); W(C, 5, -3); S(C, 4, -2); W(C, 5, -2)
def even_back(j):
    x0 = 3 * j
    # B: line (x0,6,5..8) on blocks, steps down east into (x0+1,5,5) -> XB; ends in T_B (x0,6,9)
    for z in range(5, 9):
        S(x0, 5, z); W(x0, 6, z)
    S(x0+1, 4, 5); W(x0+1, 5, 5)
    S(x0, 6, 9); L.append(f"place {x0} 6 10 redstone_wall_torch facing=south")
    # A: line (x0+2,6,7..9), steps down north into (x0+2,5,6) -> XB; ends in T_A (x0+2,6,10)
    for z in range(7, 10):
        S(x0+2, 5, z); W(x0+2, 6, z)
    S(x0+2, 4, 6); W(x0+2, 5, 6)
    S(x0+2, 6, 10); L.append(f"place {x0+2} 6 11 redstone_wall_torch facing=south")
    # nG at y=8 on the torches' above-blocks (x0,7,10), (x0+2,7,11)
    for (x, z) in ((x0, 10), (x0+1, 10), (x0+1, 11), (x0+2, 11)):
        S(x, 7, z); W(x, 8, z)
    ng_run(x0, 9)
    L.append(f"label A{j} {x0+2} 6 8"); L.append(f"label B{j} {x0} 6 7")
for j in range(-1, N):
    x0 = 3 * j
    even = j >= 0 and j % 2 == 0
    if not even:
        L += [f"place {x0+3} 6 -1 lever face=floor", f"label nG{j} {x0+3} 6 -1",
              f"place {x0+2} 6 5 lever face=floor", f"label nX{j} {x0+2} 6 5"]
    if j < 0:
        continue
    nh_network(x0)
    if even:
        even_back(j)
    L.append(f"label S{j} {x0+1} 4 -4")
L += [f"label R4 {3*N+1} 3 0", "settle"]
ins, rows = ["nG-1", "nX-1"], []
for j in range(N):
    ins += [f"A{j}", f"B{j}"] if j % 2 == 0 else [f"nG{j}", f"nX{j}"]
for cin in (0, 1):
    for bits in itertools.product(range(4), repeat=N):
        if any(bits[j] == 3 and j % 2 == 1 for j in range(N)):
            continue                              # odd bits: 3 patterns (P G K) only
        inp = [1 - cin, cin]; c = cin; outs = []
        for j, b in enumerate(bits):
            if j % 2 == 0:
                a, bb = b & 1, b >> 1
                inp += [a, bb]
                g, k = a and bb, not a and not bb
            else:
                g, k = b == 1, b == 2
                inp += [int(not g), int(not k)]
            h = not g and not k
            outs.append(int(h) ^ c)
            c = 1 if g else 0 if k else c
        outs.append(c)
        rows.append("".join(map(str, inp)) + ":" + "".join(map(str, outs)))
L += [f'target new sum "{len(rows)} rows: even bits from A, B; odd bits from levers"',
      "target sum truth " + " ".join("@" + i for i in ins) + " -> " + " ".join(f"@S{j}" for j in range(N)) + " @R4 rows " + " ".join(rows) + " settle 16",
      "check"]
open("s2.cli.txt", "w").write("\n".join(L) + "\n")
print(len(rows), "rows")
