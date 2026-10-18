"""Fast adder round 3, step a: G tap north of the G torch, K tap east of the X torch; the nH
net climbs over the core at y=7 and comes down at the front into one y=4 path joining both H
blocks; nG enters the G torch's block through a repeater from the north; K repeater delay 2.
Levers on nX (top of the X torch's block), pulses on the nG repeaters."""
import itertools, re
from design import emit
N = 4
L = ["new size 48 force"]
lines, cells = emit(N)
# the K injection repeaters get delay 2 (4 ticks), matching the nG repeater
lines = [re.sub(r"^place (-?\d+) 5 3 repeater out=north$", r"place \1 5 3 repeater out=north delay=2", l) for l in lines]
L += lines
def S(x, y, z, b="stone"): L.append(f"set {x} {y} {z} {b}")
def W(x, y, z): L.append(f"place {x} {y} {z} redstone_wire")
def nh(x0):
    X = x0 + 2
    W_ = lambda x, y, z: (S(x, y - 1, z), W(x, y, z))
    S(x0 + 1, 5, -4)                               # cut: S (x0+1,4,-4) must not step up into nH
    W_(X, 5, -2)                                   # G tap (north of the G torch)
    W_(x0 + 3, 5, 4)                               # K tap (east of the X torch)
    W_(x0 + 3, 6, 3); W_(x0 + 3, 7, 2); W_(x0 + 3, 7, 1); W_(x0 + 3, 7, 0)
    W_(X, 7, 0); W_(X, 7, -1)                      # over the G torch's above-block (also G)
    W_(x0 + 1, 7, -1); W_(x0 + 1, 6, -2); W_(x0 + 1, 5, -3)
    W_(X, 5, -3); W_(X, 5, -4)                     # joins the G tap's line
    S(X, 4, -5); L.append(f"place {X} 5 -5 repeater out=north")   # delay: H at C's time
    W_(X, 5, -6); W_(X, 5, -7)
    L.append(f"place {x0 + 1} 4 -7 redstone_wire")                # on HB1, step from X 5 -7
    W_(x0, 4, -7); W_(x0, 4, -6)
    L.append(f"place {x0} 4 -5 redstone_wire")                    # on HB2
for j in range(-1, N):
    x0 = 3 * j
    L += [f"set {x0+3} 4 -2 stone", f"place {x0+3} 5 -2 repeater out=south", f"label nG{j} {x0+3} 5 -2",
          f"place {x0+2} 6 5 lever face=floor", f"label nX{j} {x0+2} 6 5"]
    if j >= 0:
        nh(x0)
        L.append(f"label S{j} {x0+1} 4 -4")
L += [f"label R4 {3*N+1} 3 0", "settle"]
ins = ["nG-1", "nX-1"] + [f"{t}{j}" for j in range(N) for t in ("nG", "nX")]
rows = []
for cin in (0, 1):
    for bits in itertools.product("PGK", repeat=N):
        inp = [1 - cin, cin]; c = cin; outs = []
        for b in bits:
            g, k, h = b == "G", b == "K", b == "P"
            inp += [int(not g), int(not k)]
            outs.append(int(h) ^ c); c = 1 if g else 0 if k else c
        outs.append(c)
        rows.append("".join(map(str, inp)) + ":" + "".join(map(str, outs)))
L += ['target new sum "S_j = H_j xor C_j, C4 (round 3 taps)"',
      "target sum truth " + " ".join("@" + i for i in ins) + " -> " + " ".join(f"@S{j}" for j in range(N)) + " @R4 rows " + " ".join(rows) + " settle 20",
      "check"]
open("r3a.cli.txt", "w").write("\n".join(L) + "\n")
