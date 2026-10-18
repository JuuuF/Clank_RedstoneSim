"""Export the 3x3 door work in progress as worlds the owner can open (experiments/wip/door3x3/).

Run from the repository root: python experiments/wip/door3x3/scripts/export_wip.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
CLI = os.path.join(os.path.dirname(sys.executable), "redsim-cli")


def save(name, text, note):
    lines = text.rstrip("\n").split("\n")
    lines = [ln for ln in lines if not ln.startswith("note ")]
    lines.insert(1, f'note "{note}"')
    out = subprocess.run([CLI, os.path.join(OUT, name)], input="\n".join(lines) + "\n",
                         capture_output=True, text=True).stdout
    print(name, [ln for ln in out.splitlines() if ln.startswith(("check:", "error", "FAIL"))])


def gen(*args):
    return subprocess.run([sys.executable, os.path.join(HERE, "door.py"), *args],
                          capture_output=True, text=True, check=True).stdout


def read(name):
    return open(os.path.join(HERE, name)).read()


save("01-middle-column-ideal.redsim.json",
     read("mid.cli.txt").replace("\ncheck\n", "\n") + read("cycle2.txt"),
     "WIP 01 (works): the middle column alone, driven by ideal pulses. A (1 1 0) and B (1 2 0) "
     "sticky pistons facing up, W (3 3 0) sticky facing west; C = stone (the center block), "
     "M = smooth stone (the bottom-middle block). Target cycle2: B spits C up 1, W pushes M under "
     "it, B pushes both up (closed); then B pulls M down, W pulls M aside, A lifts B, B pulls C "
     "down 1, A lowers B, B pulls C down again (open). Target close: an older, longer close.")
save("02-middle-column-repeaters.redsim.json", read("mid2.cli.txt"),
     "WIP 02 (works): the middle column with real repeaters: @A into A from the north, @BH into "
     "B at home from the south, @BU into B's raised position (1 3 0) from the north. Target "
     "cycle: the same sequence as 01. Quasi-connectivity does not move A: the repeater updates "
     "B first, B extends, and A's push then fails (an extended piston cannot be pushed).")
save("03-mechanics-ideal-pulses.redsim.json", gen("mech"),
     "WIP 03 (works): the whole 3x3 door, driven by ideal pulses at the driver repeaters "
     "(@SL @SR towers, @BH, @W, @A, @BU). Doorway x 0..2, y 4..6, z 0 (smooth stone). Wire "
     "staircases in the wall plane power the side pistons and the top one. Target cycle: closed "
     "12 ticks after the close input, clear 28 ticks after the open input.")
save("04-controller-first.redsim.json", gen("ctrl"),
     "WIP 04 (works): the door with its controller; power @IN (the trunk wire, 1 2 5) to close, "
     "unpower it to open. Back: a wire trunk (z=5) feeds short repeater branches: SPIT "
     "(observer on a repeater), W (its driver locked by @LOCK while B holds), HOLD, and A's "
     "pulse (subtracting comparator @A). Front: observer @OBS watches A; its pulse gives B's "
     "raised push (via the floor block 0 3 0) and the final pull. Closed 16 ticks after @IN "
     "rises, clear 37 ticks after it falls.")
save("05-fast-controller.redsim.json", gen("fast", "h0=6", "bu=wire", "final=none"),
     "WIP 05 (works): the faster controller; power @IN to close. B's hold is the floor block 0 3 0 "
     "(quasi-connectivity: B extends when M lands under C, and B home extends for the final pull when "
     "A sets it down); the spit observer sits behind B; W's driver is locked by a delayed copy. "
     "Closed 11 ticks after @IN rises, clear 26 ticks after it falls (stage 04: 16 and 37).")
save("05b-input-timing-fails.redsim.json", gen("fast", "h0=6", "bu=wire", "final=none", "fails"),
     "WIP 05b (FAILS on purpose, 26 of 45 targets pass): the 05 door with too-short inputs. short1..short6: "
     "a close pulse under 7 ticks (the side pistons spit their blocks, or the middle column stops "
     "half-way); gap2, gap9..13, gap18..24: the input off for too short a time while closed "
     "(B's quasi-connected hold returns without an update, or the open stops with a piston head in "
     "the doorway). Load a failing target and seek to tick 78 or 129 to see the stuck state.")
_cells = [f"D{x}{r}" for x in range(3) for r in range(3)]
_t06 = "\n".join(
    ['target new lever "lever on at 5: clear by 33; off at 60: solid by 73"',
     "target lever do at 5 use @L", "target lever do at 60 use @L"]
    + [f"target lever expect @{c} block=air during 33..63" for c in _cells]
    + [f"target lever expect @{c} block=smooth_stone during 73..90" for c in _cells]
    + ['target new short "FAILS on purpose: the lever on for only 20 ticks (like a stone button); expected: open, then closed by 80"',
       "target short do at 5 use @L", "target short do at 25 use @L"]
    + [f"target short expect @{c} block=smooth_stone at 80" for c in _cells]
    + ["check"])
save("06-module-without-lockout.redsim.json", gen("module").rstrip("\n") + "\n" + _t06,
     "WIP 06 (target lever works; target short FAILS on purpose): the module before the lockout. Power the "
     "input block @IN (lever @L) to open: clear 28 ticks after, solid 13 after the lever goes off. An open "
     "request of 20 ticks (target short) re-closes during the open sequence and the door sticks with the "
     "center cell empty. The library door (examples/circuits/door_3x3) adds a lockout repeater that fixes it.")
