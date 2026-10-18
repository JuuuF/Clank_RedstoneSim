# ruff: noqa: E501  (embedded CLI script text)
"""Writes examples/circuits/seg7_display.cli.txt: the hex 7-segment decoder lighting a lamp digit.

Usage from the repository root: python -m tools.circuitgen.display7, then
PYTHONPATH=src python -m tools.make_circuits seg7_display

The decoder is seg7's lookup table (tools/circuitgen/rom16.py) with its output columns in
the order f e a g d b c (west to east) instead of a..g: then each segment line can run to
its place in the digit without crossing another one. Each line climbs (or drops) at its
own column to the height of its feed into the digit, gets a repeater, shifts sideways in
its own row (a and d first, then e and b, then f and c: the order in which no line passes
another), and joins the 7-wire cable into the back of the digit, with a second repeater.
A stone sits above every wire except where a wire steps up, so wires of different
segments never join diagonally.

The digit (4 wide, 7 high, two lamps per segment, facing south): a, g, d have a repeater
behind each lamp, fed by a wire behind those; b, c, e, f have a wire behind the upper lamp
standing on a block behind the lower one (the wire powers both). Corners are left dark so
that no two segments touch.
"""

from pathlib import Path

from tools.circuitgen.rom16 import SEG7, SEG7_HEAD, X0, or_plane, turns

PERM = "feagdbc"  #: segment carried by output column k (x = X0 + 3k + 2), west to east
LAMPS = {"a": [(1, 8), (2, 8)], "b": [(3, 6), (3, 7)], "c": [(3, 3), (3, 4)], "d": [(1, 2), (2, 2)],
         "e": [(0, 3), (0, 4)], "f": [(0, 6), (0, 7)], "g": [(1, 5), (2, 5)]}
FEED = {"a": (1, 8), "b": (3, 7), "c": (3, 4), "d": (1, 2), "e": (0, 4), "f": (0, 7), "g": (1, 5)}
DX, DZ = 32, 41  #: the digit's west edge and its lamp plane
SHIFT = {"a": 30, "d": 30, "e": 32, "b": 32, "f": 34, "c": 34}  #: the row where each line shifts
REP1, REP2, CABLE_END = 29, 36, 37


def digit() -> dict:
    """Blocks of the digit (local coordinates shifted to DX, 0, DZ): {pos: command}."""
    cells: dict = {}

    def put(x, y, z, what):
        cells[(x + DX, y, z + DZ)] = what

    lamp = {p for v in LAMPS.values() for p in v}
    for x in range(-1, 5):
        for y in range(1, 10):
            put(x, y, 0, "set redstone_lamp" if (x, y) in lamp else "set black_concrete")
    for seg in "agd":
        for (x, y) in LAMPS[seg]:
            for z, top in ((-1, "place repeater out=south"), (-2, "place redstone_wire")):
                put(x, y - 1, z, "set stone")
                put(x, y, z, top)
    for seg in "bcef":
        (x, y0), (_, y1) = LAMPS[seg]
        for z in (-1, -2):
            put(x, y0, z, "set stone")
            put(x, y1, z, "place redstone_wire")
    for (x, y) in ((0, 8), (3, 8), (0, 5), (3, 5)):
        for z in (-2, -3):
            put(x, y, z, "set stone")
    for (x, y) in FEED.values():
        put(x, y - 1, -3, "set stone")
        put(x, y, -3, "place redstone_wire")
    return cells


def routes() -> tuple[dict, set]:
    """Wire paths from the decoder's output repeaters (X0+3k+2, 3, 21) to the digit's feeds."""
    cells: dict = {}
    air: set = set()                       # cells that must stay empty (above a wire's up-step)
    for k, seg in enumerate(PERM):
        x0 = X0 + 3 * k + 2
        fx, fy = FEED[seg]
        xt, yt = fx + DX, fy
        path = [(x0, 3, 22)]
        y, z = 3, 22
        while y != yt:                     # one step per block south
            ny = y + (1 if yt > y else -1)
            air.add((x0, max(y, ny), z if ny > y else z + 1))
            y, z = ny, z + 1
            path.append((x0, y, z))
        zs = SHIFT.get(seg)
        while z < (zs if zs else CABLE_END):
            z += 1
            path.append((x0, y, z))
        if zs:
            step = 1 if xt > x0 else -1
            for x in range(x0 + step, xt + step, step):
                path.append((x, y, zs))
            while z < CABLE_END:
                z += 1
                path.append((xt, y, z))
        for p in path:
            rep = p[2] in (REP1, REP2) and p[0] == (x0 if p[2] == REP1 else xt)
            cells[p] = "place repeater out=south" if rep else "place redstone_wire"
    for (x, y, z) in list(cells):
        cells.setdefault((x, y - 1, z), "set stone")
    for (x, y, z), what in list(cells.items()):
        above = (x, y + 1, z)
        if what == "place redstone_wire" and above not in cells and above not in air:
            cells[above] = "set stone"
    return cells, air


def display() -> str:
    names = "abcdefg"
    table = [sum((SEG7[n] >> names.index(PERM[k]) & 1) << k for k in range(7)) for n in range(16)]
    head = SEG7_HEAD.split("new size")[1]
    L = [HEAD.rstrip("\n"), "new size" + head.rstrip("\n").replace(
        'note "Hex 7-segment decoder: levers @L0..@L3 (binary), segment lines @Sa..@Sg (south end, x = 24..42), settled 46 ticks after a change"',
        'note "Hex 7-segment display: levers @L0..@L3 (binary); the digit (lamps x 32..35, y 2..8, z 41, seen from the south) shows the value, settled 54 ticks after a change"')]
    L += turns() + or_plane(table, 7)
    r, _ = routes()
    d = digit()
    for (x, y, z), what in sorted({**r, **d}.items(), key=lambda kv: (kv[1].startswith("place"), kv[0][1], kv[0])):
        verb, rest = what.split(" ", 1)
        L.append(f"{verb} {x} {y} {z} {rest}")
    for seg in names:
        for i, (x, y) in enumerate(LAMPS[seg]):
            L.append(f'label {"ST"[i]}{seg} {x + DX} {y} {DZ} "segment {seg}, lamp {i + 1}"')
    L.append("settle")
    for i in range(2):
        outs = " ".join(f"@{'ST'[i]}{c}" for c in names)
        rows_ = " ".join("".join(str(n >> b & 1) for b in range(4)) + ":" + "".join(str(SEG7[n] >> k & 1) for k in range(7)) for n in range(16))
        L += ["", f'target new digits{i + 1} "each of the 16 inputs lights its digit (lamp {i + 1} of every segment)"',
              f"target digits{i + 1} truth @L0 @L1 @L2 @L3 -> {outs} rows {rows_} settle 70"]
    L += ["", "check"]
    return "\n".join(L) + "\n"


HEAD = """# Composition: hex 7-segment display: four levers, a lamp digit. Contract:
# doc/redstone/circuits.md, "7-segment display". Generated by tools/circuitgen/display7.py;
# run from the repository root (it imports decoder16.nbt and dac4.nbt, as seg7 does).
#
#   @L0..@L3   levers on the four bits (dac4's inputs, at x = -2)
#   @Sa..@Sg   the upper (or left) lamp of each segment, @Ta..@Tg the other one
# The decoder is seg7's lookup table with its output columns in the order f e a g d b c, so
# that the seven lines reach the digit without crossing (see the generator's docstring).
"""


def main() -> None:
    root = Path(__file__).resolve().parents[2] / "examples" / "circuits"
    (root / "seg7_display.cli.txt").write_text(display())


if __name__ == "__main__":
    main()
