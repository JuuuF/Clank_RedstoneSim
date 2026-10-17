"""Export the fast-adder work in progress as worlds the owner can open (experiments/wip/fast_adder/)."""
import sys, pickle, shutil
sys.path.insert(0, "/home/justin/.claude/jobs/7b97722e/tmp/cca")
from run import run
OUT = "/home/justin/Documents/Programming/redstone-sim/experiments/wip/fast_adder/"
def save(name, text):
    o = run(text, OUT + name)
    bad = [l for l in o.splitlines() if l.startswith("error") or "FAIL" in l]
    summ = [l for l in o.splitlines() if l.startswith("check:")]
    print(name, summ, bad[:3])
# 01: R-024 carry lines
src = open("/home/justin/Documents/Programming/redstone-sim/experiments/redstone/R-024-analog-carry-lines.cli.txt").read()
save("01-carry-lines.redsim.json", src)
# 02: stage 1 core (levers drive G, K, H)
t = open("stage1.cli.txt").read()
t = t.replace("new size 48 force\n", 'new size 48 force\nnote "WIP 02 (works): carry lines + per-bit read, C path and XOR. Levers: nG/nK = NOT generate/kill per bit, nHa/nHb = NOT propagate (both), S0..S3 sum wires, R4 carry out. Target sum: 162/162."\n')
save("02-core-with-levers.redsim.json", t)
# 03: stage 1c (G torch fed from the next slice, K injected by a repeater from the south)
exec(open("stage1c.py").read().split("o = run(")[0])
L.insert(1, 'note "WIP 03 (works): as 02, but the G torch hangs on the next slice\'s corner block (lever nG on it), K is injected by a repeater from the south whose rear is the X torch (lever nX on its block), and both H torches are wall torches whose blocks are powered weakly by a wire on top (levers nHa/nHb feed those wires). Target sum: 162/162."')
save("03-relocated-injections.redsim.json", "\\n".join(L).replace("\\\\n", "\\n") if False else "\n".join(L) + "\n")

# 03b: the same with levers placed directly on the H-torch blocks: FAILS (52/162)
L3b = [l for l in L]
txt = "\n".join(L3b)
import re
for j in range(4):
    x0 = 3*j
    txt = txt.replace(f"place {x0} 4 -5 redstone_wire\nplace {x0} 4 -6 lever face=floor\nlabel nHa{j} {x0} 4 -6",
                      f"place {x0} 4 -5 lever face=floor\nlabel nHa{j} {x0} 4 -5")
    txt = txt.replace(f"place {x0+1} 4 -7 redstone_wire\nplace {x0+1} 4 -8 lever face=floor\nlabel nHb{j} {x0+1} 4 -8",
                      f"place {x0+1} 4 -7 lever face=floor\nlabel nHb{j} {x0+1} 4 -7")
txt = txt.replace("WIP 03 (works)", "WIP 03b (FAILS 52/162, kept on purpose): levers stand directly on the H-torch blocks; a lever powers its block STRONGLY, and that block also feeds the previous bit's C wire beside it (x0-1 3 -5), so the previous bit's sum breaks. Compare with 03, where a wire on top powers the block weakly")
save("03b-strong-levers-fail.redsim.json", txt + "\n")
# 04: the router's partial slice (periodic slice replicated over 4 bits)
c = pickle.load(open("g1.pkl", "rb"))
lines = ["new size 48 force", 'note "WIP 04 (unfinished, does not work): one bit slice laid out by the wire router (NAB, the notH feed into the H torches, the south input logic), copied 4 times; the A, B, S and part of the notH wires could not be routed yet. Wire colours are not shown; use inspect/effects to follow a net. See README.md."']
blocks, comps = [], []
for j in range(5):
    for (x,y,z),(t,n,f) in c.items():
        if y == 0 or (j == 4 and x != 0): continue
        X = x + 3*j
        if t in ("stone","glass"): blocks.append(f"set {X} {y} {z} {t}")
        elif t == "dust": comps.append((y, f"place {X} {y} {z} redstone_wire"))
        elif t == "rep": comps.append((y, f"place {X} {y} {z} repeater out={f}"))
        elif t == "cmp": comps.append((y, f"place {X} {y} {z} comparator out={f} mode=subtract"))
        elif t == "torch": comps.append((y, f"place {X} {y} {z} redstone_torch"))
        elif t == "wtorch": comps.append((y, f"place {X} {y} {z} redstone_wall_torch facing={f}"))
lines += blocks + [cmd for _, cmd in sorted(comps)]
save("04-routed-slice-unfinished.redsim.json", "\n".join(lines) + "\n")
