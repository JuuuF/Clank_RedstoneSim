"""3x3 flush door generator. Doorway x 0..2, y 4..6, z 0; floor top y 3."""
import sys
L = []
OFF = [0, 0, 0]                 # shift of the whole build (the module uses 7 0 2)
def at(x, y, z): return f"{x + OFF[0]} {y + OFF[1]} {z + OFF[2]}"
def S(x, y, z, b): L.append(f"set {at(x, y, z)} {b}")
def P(x, y, z, b, *pr): L.append(f"place {at(x, y, z)} {b} {' '.join(pr)}".rstrip())
DOOR = "smooth_stone"
CTRL = False
FAST = False
MODULE = False
SAFE = False

def mechanics():
    # middle column (open state): A, B, C on the floor, M beside it, W pushes M west
    P(1, 1, 0, "sticky_piston", "facing=up"); P(1, 2, 0, "sticky_piston", "facing=up")
    S(1, 3, 0, DOOR); S(2, 3, 0, DOOR); P(3, 3, 0, "sticky_piston", "facing=west")
    # floor strips in front of and behind the doorway
    for x in range(-1, 4):
        for z in (-1, 1):
            S(x, 3, z, "stone")
    # drivers: B home, A, W, B up (BU)
    if not FAST:                     # (FAST: the spit observer is placed last, see controller_fast)
        S(1, 1, 1, "stone"); P(1, 2, 1, "repeater", "out=north")
    if not CTRL:
        P(0, 1, 0, "repeater", "out=east")
    S(3, 1, 1, "stone"); S(3, 2, 0, "stone"); P(3, 2, 1, "repeater", "out=north")
    S(-2, 2, 0, "stone")
    if not CTRL:
        S(-2, 1, 1, "stone"); P(-2, 2, 1, "repeater", "out=north")
    P(-2, 3, 0, "redstone_wire"); S(-1, 2, 0, "stone")
    if FAST:
        P(-1, 3, 0, "redstone_wire")
    else:
        P(-1, 3, 0, "repeater", "out=east")
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

def controller_fast(h0=8, bu_wire=False, final_wire=False):
    """Stage 05+. B's hold is the floor block 0 3 0 (quasi-connectivity: B extends when M lands
    under C); the spit observer sits behind B and watches a wire spur; W's lock is a delayed
    copy of the input. Options: h0 = hold delay (8 or 6); bu_wire = the observer on A reaches
    0 3 0 through wire only (one-way by a cut, not a repeater); final_wire = the final pull
    reaches B home through wire (no front repeater)."""
    def chain(cells, total):
        # repeater delays (in steps of 2 ticks) for a chain of len(cells) summing to total ticks
        n = len(cells); steps = total // 2
        ds = [1] * n
        i = 0
        while sum(ds) < steps:
            ds[i % n] = min(4, ds[i % n] + 1); i += 1
        assert sum(ds) == steps, (cells, total)
        return ds
    for x in range(-7, 10):                      # trunk: wire on blocks, fed at @IN
        S(x, 1, 5, "stone"); P(x, 2, 5, "redstone_wire")
    for x in (-7, 9):                            # side spurs into the tower drivers
        for z in (4, 3, 2):
            S(x, 1, z, "stone"); P(x, 2, z, "redstone_wire")
    for z in (4, 3, 2):                          # SPIT: spur watched by the observer behind B
        S(1, 1, z, "stone"); P(1, 2, z, "redstone_wire")
    hd = chain([4, 3, 1], h0)                    # HOLD: 2 repeaters, block, repeater -> 0 3 0
    S(-2, 1, 4, "stone"); rep(-2, 2, 4, "north", hd[0])
    S(-2, 1, 3, "stone"); rep(-2, 2, 3, "north", hd[1])
    S(-2, 1, 2, "stone"); S(-2, 2, 2, "stone")
    S(-2, 1, 1, "stone"); rep(-2, 2, 1, "north", hd[2])
    S(3, 1, 4, "stone"); rep(3, 2, 4, "north", 1)   # W 2+2, driver 2 -> W at +6
    S(3, 1, 3, "stone"); rep(3, 2, 3, "north", 1)
    S(3, 2, 2, "stone")
    H = h0                                          # B lets go at f+H (the falling spit ends at f+4)
    wd = chain([4, 3, 2, 1], H + 2)                 # W lock: unlock at f+H+2 -> W off at f+H+4
    for z, d in zip((4, 3, 2), wd):
        S(5, 1, z, "stone"); rep(5, 2, z, "north", d)
    S(5, 1, 1, "stone"); S(5, 2, 1, "stone"); S(4, 1, 1, "stone"); rep(4, 2, 1, "west", wd[3])
    a_on = H + 6                                    # A: (1 3 0) is clear at f+H+4
    a_len = 8 if bu_wire else 10                    # A holds until B raised has pulled C
    for z, d in zip((4, 3, 2, 1), chain([4, 3, 2, 1], a_on - 2)):
        rep(0, 1, z, "north", d)
    P(0, 1, 0, "comparator", "out=east", "mode=subtract")
    rd = chain(range(7), a_on + a_len - 2)
    for z, d in zip((4, 3, 2, 1), rd[:4]):
        rep(-5, 1, z, "north", d)
    S(-5, 1, 0, "stone")
    for x, d in zip((-4, -3, -2), rd[4:]):
        rep(x, 1, 0, "east", d)
    S(-1, 1, 0, "stone")
    # front: observer on A; its pulse gives the final pull (B home) and B raised's push (0 3 0)
    P(1, 1, -1, "observer", "out=north")
    S(1, 1, -2, "stone")
    if final_wire == "none":
        pass        # B home lands on A's retraction and finds 0 3 0 powered (quasi-connectivity)
    elif final_wire:
        P(1, 2, -2, "redstone_wire"); P(1, 2, -1, "redstone_wire")   # into B home
    else:
        P(1, 2, -2, "redstone_wire"); P(1, 2, -1, "repeater", "out=south")
    if bu_wire:
        # wire at y=1 from the observer's output block west, up two steps to 0 3 0; the
        # block 0 2 -2 cuts it off from the final-pull wire on top of the output block
        if final_wire != "none":
            S(0, 2, -2, "stone")
        for x in (0, -1, -2):
            P(x, 1, -2, "redstone_wire")
        S(-2, 1, -1, "stone"); P(-2, 2, -1, "redstone_wire")
    else:
        for x in (0, -1, -2):
            S(x, 1, -2, "stone"); P(x, 2, -2, "redstone_wire")
        S(-2, 1, -1, "stone"); rep(-2, 2, -1, "south", 1)
    P(1, 2, 1, "observer", "out=north")  # last: placed earlier, it sees its spur being built
    for n, p in (("IN", (1, 2, 5)), ("SPIT", (1, 2, 1)), ("HOLD", (-2, 2, 1)), ("W", (3, 2, 1)),
                 ("A", (0, 1, 0)), ("OBS", (1, 1, -1)), ("LOCK", (4, 2, 1))):
        if MODULE and n == "IN":
            continue
        L.append(f"label {n} {at(*p)}")

def module(safe=False):
    """Stage 06: the library module. Input block 1 2 7 (power it to open); a wall torch on it
    feeds the trunk, so the door is closed while the input is off. Built open with the test
    lever on, closed by flipping the lever off, then rebased: tick 0 is the closed door.
    safe: a lockout repeater X between the torch and the trunk (input block 1 2 9), locked
    after every edge of its own output: by comparator OFFL (rear the trunk 24 ticks late,
    side the trunk) while an open runs, by ONL (rear the trunk, side the trunk 8 ticks late)
    while a close runs."""
    if not safe:
        S(1, 2, 7, "stone"); P(1, 2, 6, "redstone_wall_torch", "facing=north")
        P(1, 3, 7, "lever", "face=floor", "powered=true")
        L.append(f'label IN {at(1, 2, 7)} "input block: power it to open (the lever @L is the test harness)"')
        L.append(f'label L {at(1, 3, 7)} "test lever on the input block"')
    else:
        S(1, 2, 9, "stone"); P(1, 2, 8, "redstone_wall_torch", "facing=north")
        P(1, 3, 9, "lever", "face=floor", "powered=true")
        # X (4 ticks) can change again only 4 ticks after its last change; each lock engages 2
        # ticks after X's output changes (wire inputs), so a new request always meets the lock
        S(1, 1, 7, "stone"); rep(1, 2, 7, "north", 2)                 # X: the lockout repeater
        S(1, 1, 6, "stone"); P(1, 2, 6, "redstone_wire")             # X -> trunk
        S(0, 1, 6, "stone"); P(0, 2, 6, "redstone_wire")             # OFFL side: trunk wire (14)
        S(0, 1, 7, "stone"); P(0, 2, 7, "comparator", "out=east", "mode=subtract")
        S(-4, 1, 6, "stone"); rep(-4, 2, 6, "south", 4)              # OFFL rear: 8+8+8, then two
        S(-4, 1, 7, "stone"); rep(-4, 2, 7, "south", 4)              # wires (13, weaker than the side)
        S(-4, 2, 8, "stone")
        S(-3, 1, 8, "stone"); rep(-3, 2, 8, "east", 4)
        for (x, z) in ((-2, 8), (-2, 7), (-1, 7)):
            S(x, 1, z, "stone"); P(x, 2, z, "redstone_wire")
        S(2, 1, 6, "stone"); rep(2, 2, 6, "south", 4)                 # ONL side: trunk 8 late
        S(2, 1, 7, "stone"); P(2, 2, 7, "comparator", "out=west", "mode=subtract")
        for z in (6, 7):                                              # ONL rear: trunk wire
            S(3, 1, z, "stone"); P(3, 2, z, "redstone_wire")
        for n, p, d in (("IN", (1, 2, 9), "input block: power it to open (the lever @L is the test harness)"),
                        ("L", (1, 3, 9), "test lever on the input block"), ("X", (1, 2, 7), "lockout repeater"),
                        ("OFFL", (0, 2, 7), "lock while an open runs"), ("ONL", (2, 2, 7), "lock while a close runs")):
            L.append(f'label {n} {at(*p)} "{d}"')
    for x in (0, 1, 2):
        for y in (4, 5, 6):
            L.append(f'label D{x}{y - 4} {at(x, y, 0)} "door cell (x {x}, row {y - 4})"')

def fail_targets():
    """Input-timing limits: close pulses of 1..14 ticks, open gaps of 1..30 ticks."""
    t = lambda n, s: L.append(f"target {n} {s}")
    cells = [(x, y) for x in (0, 1, 2) for y in (4, 5, 6)]
    for D in range(1, 15):
        n = f"short{D}"
        L.append(f'target new {n} "@IN on for {D} ticks, then a full cycle (fails for D < 7)"')
        t(n, f"do pulse @IN at 10 for {D}"); t(n, "do pulse @IN at 80 for 40")
        for x, y in cells:
            t(n, f"expect {x} {y} 0 block=air at 78")
            t(n, f"expect {x} {y} 0 block={DOOR} at 95")
            t(n, f"expect {x} {y} 0 block=air at 150")
    for G in range(1, 31):
        n = f"gap{G}"
        L.append(f'target new {n} "closed, @IN off for {G} ticks, closed again, then open (fails for 2, 9-13, 18-24)"')
        t(n, "do pulse @IN at 10 for 50"); t(n, f"do pulse @IN at {61 + G} for {130 - 61 - G}")
        for x, y in cells:
            t(n, f"expect {x} {y} 0 block={DOOR} at 129")
            t(n, f"expect {x} {y} 0 block=air at 170")

def ctrl_target(name, R, F, closed=18, opened=40):
    t = lambda s: L.append(f"target {name} {s}")
    L.append(f'target new {name} "@IN on {R}..{F}: closed by {R + closed}, open by {F + opened}"')
    t(f"do pulse @IN at {R} for {F - R}")
    for x in (0, 1, 2):
        for y in (4, 5, 6):
            t(f"expect {x} {y} 0 block={DOOR} at {R + closed}")
            t(f"expect {x} {y} 0 block=air at {F + opened}")
    t(f"expect 1 3 0 block={DOOR} at {F + opened}")
    t(f"expect 2 3 0 block={DOOR} at {F + opened}")

if __name__ == "__main__":
    stage = sys.argv[1]
    L.append("new size 40 force")
    CTRL = stage != "mech"
    MODULE = stage in ("module", "safe")
    SAFE = stage == "safe"
    FAST = stage in ("fast", "module", "safe")
    if MODULE:
        OFF[:] = [7, 0, 2]
        sys.argv[2:] = ["h0=6", "bu=wire", "final=none"]
    mechanics()
    if FAST:
        opts = dict(a.split("=") for a in sys.argv[2:] if "=" in a)
        controller_fast(int(opts.get("h0", 8)), opts.get("bu") == "wire",
                        {"wire": True, "none": "none"}.get(opts.get("final"), False))
    elif CTRL:
        controller()
    if MODULE:
        module(SAFE)
    L.append("settle")
    if MODULE:
        L.insert(1, 'note "3x3 flush piston door: power the input block @IN to open (the test lever @L on it); off = closed"')
        L.append(f"at 2 use {at(1, 3, 9 if SAFE else 7)}")
        L.append("seek 40")
        L.append("rebase")
    if stage == "ctrl":
        L.insert(1, 'note "3x3 flush door, stage 3: controller; @IN on = closed (test input)"')
        ctrl_target("cycle", 10, 70)
        L.append("check")
    if stage == "fast":
        L.insert(1, 'note "3x3 flush door, stage 5: faster controller; @IN on = closed (test input)"')
        ctrl_target("cycle", 10, 70, 14, 36)
        if "fails" in sys.argv:
            fail_targets()
        L.append("check")
    if stage == "mech":
        L.insert(1, 'note "3x3 flush door, stage 2: all mechanics, driven by ideal pulses at the driver repeaters"')
        cycle_target("cycle", 10, 50)
        L.append("check")
    print("\n".join(L))
