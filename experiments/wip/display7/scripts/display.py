"""7-segment lamp digit (4x7, two lamps per segment) facing south; feeds leave north at z=-3."""
import sys
L = []
OFF = [0, 0, 0]
def at(x, y, z): return f"{x + OFF[0]} {y + OFF[1]} {z + OFF[2]}"
def S(x, y, z, b): L.append(f"set {at(x, y, z)} {b}")
def P(x, y, z, b, *pr): L.append(f"place {at(x, y, z)} {b} {' '.join(pr)}".rstrip())
LAMPS = {"a": [(1, 8), (2, 8)], "b": [(3, 6), (3, 7)], "c": [(3, 3), (3, 4)], "d": [(1, 2), (2, 2)],
         "e": [(0, 3), (0, 4)], "f": [(0, 6), (0, 7)], "g": [(1, 5), (2, 5)]}
FEED = {"a": (1, 8), "b": (3, 7), "c": (3, 4), "d": (1, 2), "e": (0, 4), "f": (0, 7), "g": (1, 5)}
def digit():
    lamp = {p for v in LAMPS.values() for p in v}
    for x in range(-1, 5):                      # face: lamps, background, frame
        for y in range(1, 10):
            S(x, y, 0, "redstone_lamp" if (x, y) in lamp else "black_concrete")
    for seg in "agd":                           # repeaters behind the lamps, wire behind them
        for (x, y) in LAMPS[seg]:
            S(x, y - 1, -1, "stone"); P(x, y, -1, "repeater", "out=south")
            S(x, y - 1, -2, "stone"); P(x, y, -2, "redstone_wire")
    for seg in "bcef":                          # wire behind the upper lamp on a block behind the lower
        (x, y0), (_, y1) = LAMPS[seg]
        S(x, y0, -1, "stone"); P(x, y1, -1, "redstone_wire")
        S(x, y0, -2, "stone"); P(x, y1, -2, "redstone_wire")
    for (x, y) in ((0, 8), (3, 8), (0, 5), (3, 5)):   # cuts between diagonal feeds
        S(x, y, -2, "stone"); S(x, y, -3, "stone")
    for seg, (x, y) in FEED.items():            # feed track one cell further north
        S(x, y - 1, -3, "stone"); P(x, y, -3, "redstone_wire")
if __name__ == "__main__":
    L.append("new size 32 force")
    OFF[:] = [10, 0, 10]
    digit()
    for seg, (x, y) in FEED.items():
        L.append(f"label F{seg} {at(x, y, -3)}")
    L.append("settle")
    for seg in "abcdefg":
        L.append(f'target new seg_{seg} "segment {seg} alone"')
        L.append(f"target seg_{seg} do pulse @F{seg} at 2 for 10")
        for s2, ps in LAMPS.items():
            for (x, y) in ps:
                L.append(f"target seg_{seg} expect {at(x, y, 0)} lit={'true' if s2 == seg else 'false'} at 8")
    L.append("check")
    print("\n".join(L))
