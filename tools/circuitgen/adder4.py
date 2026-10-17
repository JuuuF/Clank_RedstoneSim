# ruff: noqa: E501  (embedded CLI script text)
"""Writes examples/circuits/adder4.cli.txt (the script is the checked artifact; edit the layout here and re-run).

Usage from the repository root: python -m tools.circuitgen.adder4, then
PYTHONPATH=src python -m tools.make_circuits adder4
"""

import random
from pathlib import Path

W = 17


def row(a, b, c):
    s = a + b + c
    i = (
        "".join(str((a >> k) & 1) for k in range(4))
        + "".join(str((b >> k) & 1) for k in range(4))
        + str(c)
    )
    o = "".join(str((s >> k) & 1) for k in range(4)) + str((s >> 4) & 1)
    return f"{i}:{o}"


cases = set()
for a in range(16):
    cases.add((a, 15 - a, 1))  # longest propagate chains: sum 16
    cases.add((a, 15 - a, 0))  # sum 15, no carry
for a, b, c in [
    (1, 15, 0),
    (15, 1, 0),
    (15, 15, 1),
    (15, 15, 0),
    (0, 0, 0),
    (8, 8, 0),
    (7, 9, 0),
    (5, 10, 1),
    (9, 6, 1),
]:
    cases.add((a, b, c))
random.seed(4)
while len(cases) < 48:
    cases.add((random.randrange(16), random.randrange(16), random.randrange(2)))
rows = " ".join(row(*c) for c in sorted(cases))
L = [
    '''# Composition: 4-bit ripple-carry adder from four pasted full adders. Contract:
# doc/redstone/circuits.md, "4-bit adder". Run from the repository root (it imports
# examples/circuits/full_adder.nbt).
#
# Copy i (bit i, least significant first) is pasted with its corner at -3+17i 1 -5, so its
# carry-out wire (13+17i 4 0) steps down onto the next copy's carry-in wire (14+17i 3 0).
#   @A0..@A3, @B0..@B3  levers on the input wires (7+17i 3 -6, 11+17i 3 -6)
#   @CIN  lever on bit 0's carry in (-4 3 0)
#   @S0..@S3  sum wires (1+17i 1 7), lamps south of them
#   @COUT repeater after bit 3's carry out (65 3 0), lamp behind it
# All 512 input combinations were checked once (rows generated from A + B + CIN; about a
# minute); this script checks 48 of them, including every longest carry chain.
#   redsim-cli adder4.redsim.json < examples/circuits/adder4.cli.txt
new size 160 force
note "4-bit adder: S3..S0 + COUT = A + B + CIN (bit 0 at the west). Outputs valid 24 ticks after the inputs change"'''
]
for i in range(4):
    L.append(f"import examples/circuits/full_adder.nbt at {-3 + W * i} 1 -5")
for i in range(4):
    for x, nm in ((7, "A"), (11, "B")):
        L += [
            f"set {x + W * i} 2 -6 stone",
            f"place {x + W * i} 3 -6 lever face=floor",
            f'label {nm}{i} {x + W * i} 3 -6 "input {nm}{i} (lever)"',
        ]
    L += [f"place {1 + W * i} 1 8 redstone_lamp", f'label S{i} {1 + W * i} 1 7 "sum bit {i}"']
L += [
    "set -4 2 0 stone",
    "place -4 3 0 lever face=floor",
    'label CIN -4 3 0 "carry in (lever)"',
    f"set {14 + 3 * W} 2 0 stone",
    f"place {14 + 3 * W} 3 0 repeater out=east",
    f"set {15 + 3 * W} 2 0 stone",
    f"place {15 + 3 * W} 3 0 redstone_lamp",
    f'label COUT {14 + 3 * W} 3 0 "carry out (repeater)"',
    "settle",
    "",
    'target new add "S3..S0 + COUT = A + B + CIN: 48 cases, all longest carry chains included"',
    f"target add truth @A0 @A1 @A2 @A3 @B0 @B1 @B2 @B3 @CIN -> @S0 @S1 @S2 @S3 @COUT rows {rows} settle 24",
    "",
    'target new ripple "A = 1111, B = 0000, CIN on at 10: the carry ripples 4 ticks per bit: S0 off at 16, S1 20, S2 24, S3 28, COUT on at 28"',
    "target ripple do use @A0",
    "target ripple do use @A1",
    "target ripple do use @A2",
    "target ripple do use @A3",
    "target ripple do at 10 use @CIN",
    "target ripple expect @S0 power>=1 during 8..15",
    "target ripple expect @S0 power=0 during 16..60",
    "target ripple expect @S1 power>=1 during 8..19",
    "target ripple expect @S1 power=0 during 20..60",
    "target ripple expect @S2 power>=1 during 8..23",
    "target ripple expect @S2 power=0 during 24..60",
    "target ripple expect @S3 power>=1 during 8..27",
    "target ripple expect @S3 power=0 during 28..60",
    "target ripple expect @COUT powered=false during 0..27",
    "target ripple expect @COUT powered=true during 28..60",
    "",
    "check",
]
(Path(__file__).resolve().parents[2] / "examples" / "circuits" / "adder4.cli.txt").write_text(
    "\n".join(L) + "\n"
)
