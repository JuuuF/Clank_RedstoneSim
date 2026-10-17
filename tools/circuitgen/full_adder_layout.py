"""Layout of the full adder (doc/redstone/circuits.md, "Full adder"): CLI build lines.

slice_lines: the logic (XOR, core, feeds); module_lines: plus ports and the carry routes.
Coordinates are the script's: the core's G2 comparator at 0 3 0; module box -3 1 -5 .. 13 5 7.
"""

from __future__ import annotations

import sys


def slice_lines(ox: int = 0, oz: int = 0) -> list[str]:
    out: list[str] = []

    def put(cmd, x, y, z, what):
        out.append(f"{cmd} {x + ox} {y} {z + oz} {what}")

    def place(x, y, z, what):
        put("place", x, y, z, what)

    def block(x, y, z, what="stone"):
        put("set", x, y, z, what)

    def wire(x, y, z):
        put("place", x, y, z, "redstone_wire")

    # ---- supports (set first so placements find them)
    supports = [
        # core comparators and side-wire blocks
        (0, 2, 0),
        (0, 2, 2),
        (2, 2, 0),
        (2, 2, 2),
        (0, 2, 1),
        (2, 2, 1),
        # C_in repeater, wire under the C block, torch attach block, H repeater
        (-2, 2, 0),
        (-1, 1, 0),
        (-1, 2, 1),
        (3, 1, 1),
        # east feed repeaters and their port wires
        (4, 2, 0),
        (4, 2, 2),
        (5, 2, 0),
        (5, 2, 2),
        # H line: wire under the H block (9 2 1) on 9 1 1, level-1 run x=8..5, step up to 4 2 1
        (4, 1, 1),
        (9, 1, 1),
        # XOR comparators and the A side repeater, B side repeater
        (9, 2, 0),
        (9, 2, 2),
        (8, 2, 2),
        (10, 2, 0),
        # A wires: column x=7 z=-1..2, row z=-2 x=8..9 to the rear repeater 9 3 -1, A port
        (7, 2, -1),
        (7, 2, 0),
        (7, 2, 1),
        (7, 2, 2),
        (8, 2, -2),
        (9, 2, -2),
        (9, 2, -1),
        (6, 2, 0),
        # B wires: column x=11 z=-1..4, row z=4 x=9..10 to the rear repeater 9 3 3
        (11, 2, -1),
        (11, 2, 0),
        (11, 2, 1),
        (11, 2, 2),
        (11, 2, 3),
        (11, 2, 4),
        (10, 2, 4),
        (9, 2, 4),
        (9, 2, 3),
        # S: wire under YS at level 2 and its continuation
        (1, 1, 2),
        (1, 1, 3),
    ]
    for p in supports:
        block(*p)
    # ---- core (level 3)
    place(0, 3, 0, "comparator out=east mode=subtract")  # G2 = C - notH -> YC
    place(0, 3, 2, "comparator out=east mode=subtract")  # G4 = notC - notH -> YS
    place(2, 3, 0, "comparator out=west mode=subtract")  # G1 = A - H -> YC
    place(2, 3, 2, "comparator out=west mode=subtract")  # G3 = C - H -> YS
    block(1, 3, 0)  # YC
    block(1, 3, 2)  # YS
    wire(0, 3, 1)  # notH (side of G2 and G4)
    wire(2, 3, 1)  # H (side of G1 and G3)
    # ---- west: C
    block(-1, 3, 0)  # C block (rear of G2)
    place(-2, 3, 0, "repeater out=east")  # C_in repeater (its back -3 3 0 is the C input)
    wire(-1, 2, 0)  # under the C block: carries C at level 2
    place(-1, 2, 2, "redstone_wall_torch facing=south")  # notC, attached to -1 2 1
    block(-1, 3, 2)  # notC block (rear of G4), powered by the torch below
    # ---- H and notH
    place(3, 2, 1, "repeater out=west")  # powers 2 2 1 -> H wire
    block(0, 1, 0)  # X: powered by the level-1 H branch (1 1 0 .. 5 1 0)
    place(0, 1, 1, "redstone_wall_torch facing=south")  # notH: powers 0 2 1 -> notH wire
    # ---- east: A and C feeds
    block(3, 3, 0)  # A block (rear of G1)
    place(4, 3, 0, "repeater out=west delay=3")  # 6 ticks: A reaches G1 with H
    wire(5, 3, 0)  # A port
    block(3, 3, 2)  # C block (rear of G3)
    place(4, 3, 2, "repeater out=west")
    wire(5, 3, 2)  # C-east port (fed from the south)
    # ---- XOR: C1 (9 3 0) south, C2 (9 3 2) north into the H block 9 3 1
    place(9, 3, 0, "comparator out=south mode=subtract")  # A - B
    place(9, 3, 2, "comparator out=north mode=subtract")  # B - A
    block(9, 3, 1)  # H block
    wire(9, 2, 1)  # under the H block
    for x in (8, 7, 6, 5):  # level 1 (step down at 8, up at 4)
        wire(x, 1, 1)
    wire(4, 2, 1)  # into the H repeater 3 2 1
    for x in (5, 4, 3, 2, 1):  # branch at level 1 into X (0 1 0): notH as fast as H
        wire(x, 1, 0)
    # A: column x=7 from the north, branch to C1's rear and to the core's A port
    for z in (-1, 0, 1, 2):
        wire(7, 3, z)
    wire(8, 3, -2)
    wire(9, 3, -2)
    place(9, 3, -1, "repeater out=south")  # A into C1's rear (all four XOR inputs: 2 ticks)
    wire(6, 3, 0)  # to the A port 5 3 0
    place(8, 3, 2, "repeater out=east")  # A into C2's west side
    # B: column x=11, repeater into C1's east side, round to C2's rear
    for z in (-1, 0, 1, 2, 3, 4):
        wire(11, 3, z)
    place(10, 3, 0, "repeater out=west")  # B into C1's east side
    wire(10, 3, 4)
    wire(9, 3, 4)
    place(9, 3, 3, "repeater out=north")  # B into C2's rear
    # ---- S: wire under YS, south, down to level 1
    wire(1, 2, 2)
    wire(1, 2, 3)
    wire(1, 1, 4)
    return out


if __name__ == "__main__":
    print("\n".join(slice_lines(int(sys.argv[1]) if len(sys.argv) > 1 else 0)))


def module_lines(ox: int = 0, oz: int = 0) -> list[str]:
    """The slice plus its ports: A/B columns from the north edge (z=-5), the C input wire
    at -3 3 0 with the C route round the south to the C-east port, S at level 1 to the
    south edge, and Cout from the wire on YC over the top (level 5) to the east edge (13 4 0)."""
    out = slice_lines(ox, oz)

    def put(cmd, x, y, z, what):
        out.append(f"{cmd} {x + ox} {y} {z + oz} {what}")

    def block(x, y, z):
        put("set", x, y, z, "stone")

    def wire(x, y, z):
        put("place", x, y, z, "redstone_wire")

    def place(x, y, z, what):
        put("place", x, y, z, what)

    # A and B columns from the north edge
    for x in (7, 11):
        for z in (-5, -4, -3, -2):
            block(x, 2, z)
            wire(x, 3, z)
    # C input wire and the C route: repeater -3 3 1 (C may arrive weak), west column x=-3
    # z=2..5, row z=5 (over the S wire), up x=5 to the C-east port: 15 wires, the most one
    # repeater reaches
    block(-3, 2, 0)
    wire(-3, 3, 0)
    block(-3, 2, 1)
    place(-3, 3, 1, "repeater out=south")
    for z in range(2, 6):
        block(-3, 2, z)
        wire(-3, 3, z)
    for x in range(-2, 6):
        block(x, 2, 5)
        wire(x, 3, 5)
    for z in (4, 3):
        block(5, 2, z)
        wire(5, 3, z)
    # S: level 1 from 1 1 4 to the south edge 1 1 7
    for z in (5, 6, 7):
        wire(1, 1, z)
    # Cout: wire on YC (15), up to the top layer, straight east over the core, the A port and
    # the XOR, down onto the stone 13 3 0: 13 4 0 is 3, the next copy's CIN wire 14 3 0 is 2
    wire(1, 4, 0)
    for x in range(2, 13):
        block(x, 4, 0)
    for x in range(2, 13):
        wire(x, 5, 0)
    block(13, 3, 0)
    wire(13, 4, 0)
    return out
