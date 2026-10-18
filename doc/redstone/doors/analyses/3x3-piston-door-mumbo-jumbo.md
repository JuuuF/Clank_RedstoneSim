# piston door by Mumbo Jumbo

World: `piston_doors/3x3 piston door by Mumbo Jumbo.redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

A flush 3x3 door in the plane x = 5 (cells y 5..7, z −3..−1), 3 blocks deep (x 3..5),
12 sticky pistons, built open; the lever (3 2 −1) closes it (closed 10 ticks after the
lever) and opens it again (open 24 ticks after the lever). Direction-independent: all
eight orientations replay identically ([[../symmetry]]).

**Piston layout (geometry).** Eight of the nine door blocks are **singles**: one sticky
piston each pulls it one cell out of the doorway into the frame: three per side column
(z = −5 facing south, z = 1 facing north), the top middle up into the lintel (5 9 −2,
facing down). The **center** and the **bottom middle** are the hard cells (like every
flush 3x3): they go *down*. When open, the bottom-middle block (B) rests in the floor
beside the center column at 5 4 −1, the center block (C) in the floor at 5 4 −2. Under
the center column stand two sticky pistons facing up: P1 at 5 3 −2 and P2 at 5 2 −2 (a
double extender); a sticky piston at 5 4 0 (facing north) slides B between 5 4 −1 and
5 4 −2.

**Closing** (lever at 1):

1. tick 2: P1 extends and pushes C up one (5 4 −2 → 5 5 −2). P1 is powered through the
   iron block 5 3 −1 beside it (wire 4 3 −1 powers that block).
2. tick 3: the lever's signal turns the torch 4 3 1 off; sticky piston 5 3 1 retracts and
   **pulls that iron block away** (5 3 −1 → 5 3 0). P1 loses its power while C is still
   moving: P1 **spits** C (C lands at 5 5 −2 at once, P1's head comes back). A one-tick
   pulse made by moving the conductor, not by a pulse circuit (role "power switch").
3. tick 5: the side singles and the top extend; the floor piston 5 4 0 pushes B under C
   (5 4 −1 → 5 4 −2).
4. tick 6: 5 3 1 pushes the iron block back; P1 is powered again and at tick 9 pushes B
   and C up together (B to 5 5 −2, C to 5 6 −2). Closed at 11.

**Opening** (lever at 13):

1. tick 14: P1 retracts and pulls B down (5 5 −2 → 5 4 −2).
2. tick 17: singles and top retract; 5 4 0 pulls B back to 5 4 −1 (into the floor).
3. tick 21: P2 lifts P1 one cell (5 3 −2 → 5 4 −2); P1, set down next to power, extends at
   24 (the landing check, [[../../components]]) into the empty cell below C, and at 25
   pulls C down to 5 5 −2.
4. tick 28: P2 retracts and takes P1 back down; P1 extends again at 31 and at 37 pulls C
   down into the floor (5 4 −2). Open at 37.

The helper piston 4 3 −3 pushes a wool block in and out three times (9, 24, 30) next to
the wire 5 3 −5: each move reshapes that wire (a solid block beside it changes where it
connects). The causal links show that line (5 3 −5, 5 4 −4) is what retracts the raised
P1 at 25 (through the floor block beside it), so the helper is part of the timing of the
opening's middle step; its exact logic is not worked out yet (backlog).

**Lessons.** (1) The center-and-bottom problem of a flush 3x3 is solved with a double
extender under the center and one sideways floor piston: C is placed by a spit and B is
slid under it, then both go up together. (2) Short pulses can be made mechanically: a
piston moving the **block that powers** another piston gives an exact one-tick pulse.
(3) A raised piston that lands next to power extends by itself (landing check), which
saves a wire to it.

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 3×3 in the plane x = 5; 0 more output cells outside it.
- Timeline: use lever at 1, use lever at 13; markers Closing 1, Closed 12, Opening 13, Opened 40
- Reference states: closed at tick 12, open at tick 40. Fully closed at ticks 11-13; fully open at 0-1, 37-40.
- Pistons by role: door 10, helper 1, power switch 1, stack 1
- How extensions were powered (block giving the signal; QC = through the block above the piston): block←wire 6, torch 3, block←wire (QC) 2, wire 2, block←repeater 1, block←comparator 1, block←repeater+wire 1, block←torch+wire 1, target 1
- Phases (bursts of piston events): 2–9 (15 events, 11 pistons); 14–17 (9 events, 9 pistons); 21–31 (11 events, 4 pistons); 37–37 (2 events, 2 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
  0    2    3    5    7    9   11   14   17   24   25   27   37
...  ...  ...  ~~~  ###  ###  ###  ###  ...  ...  ...  ...  ...
...  ...  ...  ~.~  #.#  #~#  ###  ###  .#.  .#.  ...  ...  ...
...  .~.  .#.  ~#~  ###  #~#  ###  #.#  ...  .~.  .~.  .#.  ...

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| south | 3 | 3 | 2×3 | south 1 (3) |
| north | 3 | 3 | 2×3 | north 1 (3) |
| below | 2 | 3 | 4×2 | down 2 (1), down 1, south 1 (1) |
| above | 1 | 1 | 2×1 | up 1 (1) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| 5 3 -2 S | up | door | 2+1→spat, 9+5→pulled, 31+6→pulled | block←wire 2, wire 1 |
| 5 4 -2 S | up | door | 24+1→pulled | block←wire 1 |
| 5 4 0 S | north | door | 5+12→pulled | torch 1 |
| 5 5 -5 S | south | door | 5+12→pulled | block←wire (QC) 1 |
| 5 5 1 S | north | door | 5+12→pulled | torch 1 |
| 5 6 -5 S | south | door | 5+12→pulled | block←wire 1 |
| 5 6 1 S | north | door | 5+12→pulled | block←torch+wire 1 |
| 5 7 -5 S | south | door | 5+12→pulled | block←wire 1 |
| 5 7 1 S | north | door | 5+12→pulled | block←wire 1 |
| 5 9 -2 S | down | door | 5+12→pulled | target 1 |
| 4 3 -3 S | north | helper | 9+12→pulled, 24+3→pulled, 30+7→pulled | block←repeater 1, block←wire (QC) 1, wire 1 |
| 5 3 1 S | north | power switch | pulled at 3, 6+None→held | torch 1 |
| 5 2 -2 S | up | stack | 21+7→pulled, 31+None→held | block←comparator 1, block←repeater+wire 1 |

<!-- end generated -->
