# ruff: noqa: E501  (embedded CLI script text)
"""Writes examples/circuits/full_adder.cli.txt (the script is the checked artifact; edit the layout here and re-run).

Usage from the repository root: python -m tools.circuitgen.full_adder, then
PYTHONPATH=src python -m tools.make_circuits full_adder
"""

from pathlib import Path

from tools.circuitgen.full_adder_layout import module_lines

head = """# Circuit: full adder (S = A xor B xor C, COUT = majority). Contract: doc/redstone/circuits.md,
# "Full adder". Built to be pasted side by side: four copies 17 blocks apart are the 4-bit
# adder (adder4.cli.txt), each copy's COUT running into the next copy's CIN.
#
# Module (box -3 1 -5 .. 13 5 7; it needs a solid floor under its bottom layer):
#   @A    7 3 -5   input A: wire, drive it from the north (7 3 -6)
#   @B    11 3 -5  input B: wire, drive it from the north (11 3 -6)
#   @CIN  -3 3 0   carry in: wire, drive it from the west (-4 3 0)
#   @COUT 13 3 0   carry out: wire at the east edge (the next copy's CIN wire touches it)
#   @S    1 1 7    sum: wire on the bottom layer at the south edge, pointing south
# How it works (all comparators subtract; H = A xor B):
#   XOR: comparators 9 3 0 (A - B) and 9 3 2 (B - A) into the stone 9 3 1 = H; all four
#     inputs through delay-1 repeaters (9 3 -1, 10 3 0, 8 3 2, 9 3 3), so it never glitches.
#   H leaves under the H stone (9 2 1), runs west on the bottom layer, climbs to the
#     repeater 3 2 1, which powers the stone 2 2 1 under the H wire 2 3 1; a branch on the
#     bottom layer powers the stone 0 1 0, whose torch 0 1 1 powers 0 2 1 under the NOT-H
#     wire 0 3 1: H and NOT H reach the core in the same tick.
#   Core: YC (1 3 0) gets G1 = A - H (2 3 0, A through a delay-3 repeater so it arrives
#     with H) and G2 = C - NOT H (0 3 0): COUT = H ? C : A. YS (1 3 2) gets G3 = C - H
#     (2 3 2) and G4 = NOT C - NOT H (0 3 2): S = H xor C. G1/G3 share the H wire between
#     them, G2/G4 the NOT-H wire.
#   C: the CIN repeater -2 3 0 powers the C stone -1 3 0 (G2's rear); the wire under it
#     feeds the torch -1 2 2 (NOT C, powers G4's stone -1 3 2); a wire round the south
#     (repeater -3 3 5) brings C to G3's stone 3 3 2.
#   COUT: repeater 1 3 -1 north of YC, up to the top layer (y=5), east over the A and B
#     wires (repeater 12 5 -4), down to 13 3 0.
# Latency: A or B -> S 8 ticks, -> COUT 12; CIN -> S 6, -> COUT 8. Single input changes
# never glitch; several inputs changing together can glitch for 2-4 ticks before settling.
# Test harness outside the box: levers @LA, @LB, @LCIN; lamp under S; repeater + lamp on COUT.
#   redsim-cli full_adder.redsim.json < examples/circuits/full_adder.cli.txt
new size 48 force
note "Full adder: @S = A xor B xor CIN, @COUT = majority(A, B, CIN). Paste copies 17 apart in x to chain the carry (adder4)"
"""
body = module_lines()
tail = """label A 7 3 -5 "input A: wire, driven from the north"
label B 11 3 -5 "input B: wire, driven from the north"
label CIN -3 3 0 "carry in: wire, driven from the west"
label COUT 13 3 0 "carry out: wire at the east edge"
label S 1 1 7 "sum: wire on the bottom layer, pointing south"
label H 9 3 1 "A xor B"
label YC 1 3 0 "carry stone: H ? C : A"
label YS 1 3 2 "sum stone: H xor C"
group full_adder -3 1 -5 13 5 7 in @A A in @B B in @CIN CIN out @S S out @COUT COUT
settle
prefab save full_adder -3 1 -5 13 5 7
# harness
set 7 2 -6 stone
place 7 3 -6 lever face=floor
set 11 2 -6 stone
place 11 3 -6 lever face=floor
set -4 2 0 stone
place -4 3 0 lever face=floor
place 1 1 8 redstone_lamp
set 14 2 0 stone
place 14 3 0 repeater out=east
set 15 2 0 stone
place 15 3 0 redstone_lamp
label LA 7 3 -6 "test lever A"
label LB 11 3 -6 "test lever B"
label LCIN -4 3 0 "test lever CIN"
settle

target new truth "S = A xor B xor CIN, COUT = majority"
target truth truth @LA @LB @LCIN -> @S @COUT rows 000:00 001:10 010:10 011:01 100:10 101:01 110:01 111:11 settle 16

target new latency "A on at 5 (S at 13), CIN on at 30 (S off at 36, COUT on at 38), B on at 55 (S on at 63), CIN off at 80 (S off 86), A off at 105 (COUT off 117, S on 113)"
target latency do at 5 use @LA
target latency do at 30 use @LCIN
target latency do at 55 use @LB
target latency do at 80 use @LCIN
target latency do at 105 use @LA
target latency expect @S power=0 during 0..12
target latency expect @S power>=1 during 13..35
target latency expect @S power=0 during 36..62
target latency expect @COUT power=0 during 0..37
target latency expect @COUT power>=1 during 38..116
target latency expect @S power>=1 during 63..85
target latency expect @S power=0 during 86..112
target latency expect @S power>=1 during 113..130
target latency expect @COUT power=0 during 117..130

target new hazards "the two hazards the design removes: A alone never makes a false carry (G1 waits for H); A turning on while CIN is on switches COUT on once, without a dropout (H and NOT H switch together)"
target hazards do at 5 use @LA
target hazards expect @COUT power=0 during 0..40
target hazards do at 45 use @LA
target hazards do at 60 use @LCIN
target hazards do at 80 use @LA
target hazards expect @COUT power=0 during 41..91
target hazards expect @COUT power>=1 during 92..130

check
"""
(Path(__file__).resolve().parents[2] / "examples" / "circuits" / "full_adder.cli.txt").write_text(
    head + "\n".join(body) + "\n" + tail
)
