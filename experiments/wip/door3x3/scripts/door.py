"""3x3 flush door generator. Doorway x 0..2, y 4..6, z 0; floor top y 3."""
import sys
L = []
def S(x, y, z, b): L.append(f"set {x} {y} {z} {b}")
def P(x, y, z, b, *pr): L.append(f"place {x} {y} {z} {b} {' '.join(pr)}".rstrip())
DOOR = "smooth_stone"
CTRL = False

def mechanics():
    # middle column (open state): A, B, C on the floor, M beside it, W pushes M west
    P(1, 1, 0, "sticky_piston", "facing=up"); P(1, 2, 0, "sticky_piston", "facing=up")
    S(1, 3, 0, DOOR); S(2, 3, 0, DOOR); P(3, 3, 0, "sticky_piston", "facing=west")
    # floor strips in front of and behind the doorway
    for x in range(-1, 4):
        for z in (-1, 1):
            S(x, 3, z, "stone")
    # drivers: B home, A, W, B up (BU)
    S(1, 1, 1, "stone"); P(1, 2, 1, "repeater", "out=north")
    if not CTRL:
        P(0, 1, 0, "repeater", "out=east")
    S(3, 1, 1, "stone"); S(3, 2, 0, "stone"); P(3, 2, 1, "repeater", "out=north")
    S(-2, 2, 0, "stone")
    if not CTRL:
        S(-2, 1, 1, "stone"); P(-2, 2, 1, "repeater", "out=north")
    P(-2, 3, 0, "redstone_wire"); S(-1, 2, 0, "stone"); P(-1, 3, 0, "repeater", "out=east")
    S(0, 3, 0, "stone")
    # side columns, open: blocks in the wall pockets
    for y in (4, 5, 6):
        P(-2, y, 0, "sticky_piston", "facing=east"); S(-1, y, 0, DOOR)
        P(4, y, 0, "sticky_piston", "facing=west"); S(3, y, 0, DOOR)
    # top: piston above the top pocket
    S(1, 7, 0, DOOR); P(1, 8, 0, "sticky_piston", "facing=down")
    for x in (-1, 0, 2, 3):
        S(x, 7, 0, "stone_bricks")
    # wire staircases (left feeds the top piston too); m mirrors x -> 2 - x
    for m in (lambda x: x, lambda x: 2 - x):
        for (x, y, b) in ((-7, 2, "stone"), (-6, 3, "stone"), (-5, 4, "stone"), (-4, 5, "stone"),
                          (-3, 6, "glass"), (-3, 4, "stone"), (-2, 7, "stone")):
            S(m(x), y, 0, b)
        for (x, y) in ((-7, 3), (-6, 4), (-5, 5), (-4, 6), (-3, 7), (-3, 5), (-2, 8)):
            P(m(x), y, 0, "redstone_wire")
        S(m(-7), 1, 1, "stone"); P(m(-7), 2, 1, "repeater", "out=north")
    P(-1, 8, 0, "redstone_wire"); P(0, 8, 0, "redstone_wire")
    if CTRL:
        return
    for n, p in (("SL", (-7, 2, 1)), ("SR", (9, 2, 1)), ("BH", (1, 2, 1)), ("W", (3, 2, 1)),
                 ("A", (0, 1, 0)), ("BU", (-2, 2, 1))):
        L.append(f"label {n} {p[0]} {p[1]} {p[2]}")

def cycle_target(name, R, F, drive=True):
    t = lambda s: L.append(f"target {name} {s}")
    L.append(f'target new {name} "close at {R}, open at {F}: door cells solid, then clear"')
    if drive:
        for s in ("SL", "SR"):
            t(f"do pulse @{s} at {R} for {F - R}")
        t(f"do pulse @BH at {R} for 1")
        t(f"do pulse @W at {R + 4} for {F + 4 - R - 4}")
        t(f"do pulse @BH at {R + 8} for {F - R - 8}")
        t(f"do pulse @A at {F + 6} for 12")
        t(f"do pulse @BU at {F + 8} for 4")
        t(f"do pulse @BH at {F + 22} for 4")
    for x in (0, 1, 2):
        for y in (4, 5, 6):
            t(f"expect {x} {y} 0 block={DOOR} at {R + 14}")
            t(f"expect {x} {y} 0 block=air at {F + 32}")
    t(f"expect 1 3 0 block={DOOR} at {F + 32}")
    t(f"expect 2 3 0 block={DOOR} at {F + 32}")

def rep(x, y, z, out, d=1):
    P(x, y, z, "repeater", f"out={out}", f"delay={d}")

def controller():
    """Back: trunk z=5 (y=2) with branches; front: observer on A -> B up / final pull."""
    for x in range(-7, 10):                      # trunk: wire on blocks, fed at @IN
        S(x, 1, 5, "stone"); P(x, 2, 5, "redstone_wire")
    for x in (-7, 9):                            # side spurs into the tower drivers
        for z in (4, 3, 2):
            S(x, 1, z, "stone"); P(x, 2, z, "redstone_wire")
    for z in (4, 3):                             # SPIT: spur, watched repeater, observer
        S(-1, 1, z, "stone"); P(-1, 2, z, "redstone_wire")
    S(-1, 1, 2, "stone"); rep(-1, 2, 2, "north", 1)
    P(0, 2, 2, "observer", "out=east")
    S(1, 1, 4, "stone"); rep(1, 2, 4, "north", 4)   # HOLD 8+4, driver 2 -> B at +14
    S(1, 1, 3, "stone"); rep(1, 2, 3, "north", 2)
    S(1, 2, 2, "stone")
    S(3, 1, 4, "stone"); rep(3, 2, 4, "north", 2)   # W 4+4, driver 2 -> W at +10
    S(3, 1, 3, "stone"); rep(3, 2, 3, "north", 2)
    S(3, 2, 2, "stone")
    for z in (4, 3, 2):                             # W lock 4+4+4, block, 4 -> side at +16
        S(5, 1, z, "stone"); rep(5, 2, z, "north", 2)
    S(5, 1, 1, "stone"); S(5, 2, 1, "stone"); S(4, 1, 1, "stone"); rep(4, 2, 1, "west", 2)
    for z, d in ((4, 2), (3, 2), (2, 2), (1, 3)):   # A side 4+4+4+6 = 18 (from the trunk support)
        rep(0, 1, z, "north", d)
    P(0, 1, 0, "comparator", "out=east", "mode=subtract")
    for z in (4, 3, 2, 1):                          # A rear 7 x 4 = 28 via the west
        rep(-5, 1, z, "north", 2)
    S(-5, 1, 0, "stone")
    for x in (-4, -3, -2):
        rep(x, 1, 0, "east", 2)
    S(-1, 1, 0, "stone")
    # front: observer watching A; its pulse feeds the final pull (B home, from the front)
    # and B-up (the floor block 0 3 0) through a wire to the B-up repeater
    P(1, 1, -1, "observer", "out=north")
    S(1, 1, -2, "stone"); P(1, 2, -1, "repeater", "out=south")
    for (x, z) in ((1, -2), (0, -2), (-1, -2), (-2, -2), (-2, -1)):
        if (x, z) != (1, -2):
            S(x, 1, z, "stone")
        P(x, 2, z, "redstone_wire")
    for n, p in (("IN", (1, 2, 5)), ("BH", (1, 2, 1)), ("W", (3, 2, 1)), ("A", (0, 1, 0)),
                 ("OBS", (1, 1, -1)), ("SPIT", (0, 2, 2)), ("LOCK", (4, 2, 1))):
        L.append(f"label {n} {p[0]} {p[1]} {p[2]}")

def ctrl_target(name, R, F):
    t = lambda s: L.append(f"target {name} {s}")
    L.append(f'target new {name} "@IN on {R}..{F}: closed by {R + 18}, open by {F + 40}"')
    t(f"do pulse @IN at {R} for {F - R}")
    for x in (0, 1, 2):
        for y in (4, 5, 6):
            t(f"expect {x} {y} 0 block={DOOR} at {R + 18}")
            t(f"expect {x} {y} 0 block=air at {F + 40}")
    t(f"expect 1 3 0 block={DOOR} at {F + 40}")
    t(f"expect 2 3 0 block={DOOR} at {F + 40}")

if __name__ == "__main__":
    stage = sys.argv[1]
    L.append("new size 40 force")
    CTRL = stage != "mech"
    mechanics()
    if CTRL:
        controller()
    L.append("settle")
    if stage == "ctrl":
        L.insert(1, 'note "3x3 flush door, stage 3: controller; @IN on = closed (test input)"')
        ctrl_target("cycle", 10, 70)
        L.append("check")
    if stage == "mech":
        L.insert(1, 'note "3x3 flush door, stage 2: all mechanics, driven by ideal pulses at the driver repeaters"')
        cycle_target("cycle", 10, 50)
        L.append("check")
    print("\n".join(L))
