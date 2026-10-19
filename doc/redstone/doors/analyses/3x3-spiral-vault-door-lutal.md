# Spiral Vault Door by Lutal

World: `piston_doors/3x3 Spiral Vault Door by Lutal.redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(Hand-written 2026-10-19 from the replay, `why` traces, `waves`, `trace`, the ablation
and three one-change experiments on copies in
`.sandbox/doors/explain/3x3-spiral-vault-door-lutal/`; [[../robustness]], [[../symmetry]],
[[../mechanism]], [[../metrics]]. Ticks are the simulator's; the lever is pulled at 1 and
22.)

**A showpiece: a vault wheel with a lit hub.** The door is three blocks deep in the wall
x = 3..5: two rings of eight iron blocks, one in the plane x = 3 (the lever's side) and
one at x = 5, around a hub, a sea lantern at 4 5 −2. The rings' center cells 3 5 −2 and
5 5 −2 are never filled (they are not output cells and nothing moves into them, maps at
0 and 21), so the closed door is a ring with a 1×1 hole through which the lit hub shows.
Three more sea lanterns sit fixed in the plane x = 4 around the hub cell (4 7 −2 in the
lintel, 4 3 −2 in the floor, 4 5 0 in the south wall); open, the hub lantern parks at
4 5 −4, the matching place in the north wall, so the open passage shows four lanterns
in a cross and the closed door three plus the hub (read from the maps; the look itself is
inferred). The box is 11 × 8 × 10 (880 cells, 205 blocks), the largest 3x3 of the
dataset; the trim keeps 145 blocks in 640 cells (game-verified, EXP-074). [[../metrics]]
lists it as a showpiece: a 3x3 that trades volume for the motion. All eight orientations
replay identically ([[../symmetry]]).

**Piston layout.** Every ring block is a **single**: one sticky piston per block, one cell
out in the frame, pushing it in and pulling it out again, the same at x = 3 and x = 5 (16
pistons): three facing down above the lintel (3 8 −3..−1, 5 8 −3..−1), three facing up
under the floor (3 2 −3..−1, 5 2 −3..−1), one facing south behind the north wall
(3 5 −5, 5 5 −5), one facing north behind the south wall (3 5 1, 5 5 1). Open, each
block rests one cell out of its ring cell (the top row at y = 7, the bottom row at y = 3,
the middles at z = −4 and z = 0). The hub lantern travels two cells along x = 4 between
4 5 −4 and 4 5 −2, moved by a **two-piston stack**: the sticky piston 4 5 −6 (facing
south) carries the sticky piston 4 5 −5 (facing south) one cell forward and back, and the
carried piston does the strokes. A non-sticky piston 4 6 −6 (facing up, extends into
air) exists only to be watched by the observer 4 6 −5: it is the stack's clock (below).
19 pistons move door blocks; the clock piston moves nothing.

**One pulse for both directions.** Every ring piston receives the same 2-tick pulse when
the lever goes on and when it goes off, because the pulses come from observers (an
observer fires on any change of what it watches, 2 ticks for 2 ticks). A sticky piston
that gets a 2-tick pulse with its block in front pushes the block and **spits** it: the
retract comes while the block still moves and leaves it in place (R-018, [[../patterns]]
"Spits"). The same pulse with the head cell empty extends into the air and **pulls** the
block back on the retract. So closing and opening use the same wiring and the same
timing; what differs is only where the blocks are. The replay shows every ring piston
"spat" in the closing and "pulled" in the opening at the same offset from its lever
flip (the pulse table below: 3+2 → spat, 24+2 → pulled, and so on).

**The sweep (the "spiral").** The blocks do not move at once: the pulses reach the rings
in a sweep around the ring, 2 ticks per step, and the same sweep empties it. The steps,
with the path of each pulse (every path verified by `why` at the first move; the same
blocks power the x = 5 ring from the other side):

| step | tick close / open | ring cells (x = 3 and x = 5) | pulse path from the lever |
|---|---|---|---|
| 1 | 3 / 24 | south middle (z −1) | the lever 0 4 −2 powers its block 0 3 −2, the wire 0 2 −2 under it is watched by the observer 0 2 −1, whose pulse climbs a wire stair 0 2 0, 0 2 1, 1 2 1, 2 3 1, 3 4 1 to the wire 4 5 1 between the pistons 3 5 1 and 5 5 1 |
| 2 | 5 / 26 | top south corner | the observer 4 6 1 watches the wire 4 5 1 and pulses up: 4 7 1 → 4 8 0; the targets 3 8 0 and 5 8 0 beside that wire power the pistons 3 8 −1 and 5 8 −1 |
| 3 | 7 / 28 | top middle | the repeater 4 8 −1 (1 tick) → the cyan wool 4 8 −2 between the pistons 3 8 −2 and 5 8 −2 |
| 4 | 9 / 30 | top north corner | the repeater 4 8 −3 (1 tick) → the block 4 8 −4 → the wires 3 8 −4 and 5 8 −4 |
| 4 | 9 / 30 | north middle | the repeater 0 2 −5 (2 ticks) delays the lever's wire; the observer 1 2 −5 watches it and pulses into the block 2 2 −5, which powers the wire 2 3 −5 … 5 3 −5 on top of it; the observers 3 4 −5 and 5 4 −5 watch that wire and pulse up into the pistons 3 5 −5 and 5 5 −5 |
| 4 | 9 / 30 | bottom north corner | the repeater 0 2 −4 (3 ticks); the observer 1 2 −4 pulses into the block 2 2 −4 → the wire 3 2 −4 … 6 2 −4 → the target 4 2 −3 between the pistons 3 2 −3 and 5 2 −3 |
| 5 | 11 / 32 | bottom middle | the repeaters 2 2 −3 and 6 2 −3 (1 tick) → the cyan wool 2 2 −2 and 6 2 −2 beside the pistons 3 2 −2 and 5 2 −2 |
| 6 | 13 / 34 | bottom south corner | the repeaters 2 2 −1 and 6 2 −1 (1 tick) → the wires 2 2 0 and 6 2 0 → the targets 3 2 0 and 5 2 0 beside the pistons 3 2 −1 and 5 2 −1 |

So the ring fills from the south over the top to the north and under the bottom back to
the south (counter-clockwise as seen from the lever's side), with three blocks landing
at once at step 4, and empties in the same order, 21 ticks later. Each row step is one
1-tick repeater, which a 2-tick pulse passes unchanged. The five **targets** are used as
conductors a wire connects to: a target is a signal source, so a passing wire points into
it and powers it like a block at a line's end, and the powered target powers the pistons
on both its sides (`inspect 4 2 -3`: the wire 4 2 −4 connects south into it); a plain block
beside a wire line gets nothing. Fully closed at 15 (when the hub lands) and open at 36:
14 ticks after each lever flip, closing and opening alike.

**The hub: two cells with one stack, no wire to the rider.** The lever's wire also climbs
north (1 2 −7, 2 3 −7, 3 4 −7); the observer 3 5 −7 watches 3 4 −7, and its pulse runs
over 3 6 −7, 3 6 −8, 4 6 −8 into the repeater 4 6 −7 (4 ticks), which turns the 2-tick
pulse into an 8-tick one, 8 ticks later: **11–19** in the closing, **32–40** in the
opening (`waves`). That pulse powers the clock piston 4 6 −6 directly and the stack
piston 4 5 −6 by quasi-connectivity (the repeater powers 4 6 −6, the cell above the stack
piston; `why` at 11). The observer 4 6 −5 watches the clock piston and pulses into the
iron block 4 6 −4 two ticks after each of its changes: 13–14 and 21–22, 34–35 and 42–43.
That block is directly above the carried piston when it is forward (4 5 −4) and
quasi-connected to it when it is home (4 5 −5). The carried piston has no wire at all: it
extends by its **landing check** when the stack sets it down beside that block while
the block is powered ([[../patterns]] "Landing checks"), and it learns that the power is
gone from its own head landing (`why` at 46: the retract was queued at 45 by the head's
landing; the observer's turn-off at 44 reaches only its front block and that block's
neighbors, never the piston at 4 5 −5).

Closing: 11 the stack pushes the lantern 4 5 −4 → −3 and the carried piston −5 → −4; 13
the carried piston lands and finds 4 6 −4 powered; 14 it extends, 15 the observer's
pulse ends and it retracts at once: the lantern, still moving, is spat into the hub cell
4 5 −2. 19 the stack pulls the carried piston home (it lands at 21). 21–22 the observer
fires again because the clock piston retracted at 19, so the carried piston, just landed,
strokes once more (22–25) into empty air: harmless. Opening: 32 the stack pushes the
carried piston forward (the lantern is at −2; the push moves only the piston); 34 it
lands, 35 it extends into the empty −3 and at 36 pulls the lantern to −3; 40 the stack
pulls the piston home; 43 the second observer pulse makes it stroke again, and this time
the stroke pulls the lantern from −3 to −4 at 46. The echo stroke that does nothing in
the closing is the opening's last move. The hub is therefore a one-piston extender whose
two strokes per direction come from one observer firing twice (on the clock's extension
and on its retraction), with the stack's 8-tick pulse spacing them.

**Same-tick order.** In 8 ticks (5, 9, 11, 13 and 26, 30, 32, 34) a spit or a pull of one
step runs before the extensions of the next step, on other cells; the order inside the
tick changes nothing, which is why the stripped door driven by editor pulses runs
identically ([[../mechanism]]).

**Which delays and blocks matter** (the ablation, [[../robustness]]; the experiments are
the copies `hub_delay_3`, `hub_delay_2`, `separator_glass` in the folder above):

- The six 1-tick row repeaters must stay 1 tick: delay 2 breaks all six, delay 3 four of
  them. A longer repeater stretches the 2-tick pulse, the retract then comes after the
  block has landed, and the piston pulls it back instead of leaving it.
- The hub repeater 4 6 −7 must stay 4 ticks: delays 1, 2 and 3 all break the door. At
  delay 3 the stack's pulse is 9–15: the carried piston lands at 11, strokes at 12, spits
  at 13, and its own retraction is still in progress at 15 when the stack retracts. The
  stack's pull then finds a moving piston at 4 5 −4 and only drops its head (`trace` at
  15: `4 5 -5 piston_head → air`, nothing moved; R-026 for a pull): the piston stays at
  4 5 −4 for good and the lantern ends at 4 5 −3 (`diff 0 48`; the same at delay 2). With
  8 ticks the stack retracts at 19, two ticks after the spit's retraction has finished.
- The two lever-side repeaters 0 2 −5 (2) and 0 2 −4 (3) can take any delay (all six
  variants change timing only): the branches work on disjoint cells, so where the north
  middle and the bottom row fall in the sweep is presentation, not mechanics.
- Of 125 conducting structure blocks turned to glass, 11 break the door: the lever's
  block 0 3 −2, the six pulse carriers 2 2 −5, 2 2 −4, 2 2 −2, 6 2 −2, 4 8 −2, 4 8 −4, and
  four **separator blocks** that keep two wire runs apart: 3 3 −4, 4 3 −4, 5 3 −4 between
  the north wire (y = 3, z = −5) and the bottom-row wire (y = 2, z = −4), and 2 3 0 between
  the stair wire 2 3 1 and the wire 2 2 0 (that one by the same rule, not tested). As
  glass, the upper wire steps down into the lower one (`inspect 3 3 -5` with glass at
  3 3 −4: the wire gains `south=side`), the branches merge, and the north block of the
  x = 3 ring stays in the ring (`diff 0 48`).
  60 of the 205 blocks are slack (the trim).

**Input timing** ([[../robustness]]): safe gap 17 ticks (the world waits 21). Gaps 5–16
leave the rings working but the hub lantern at 4 5 −2 instead of 4 5 −4 (the hub's 8-tick
stack pulse is the slow part of the sequence); gaps 1–4 jam.

**Lessons.** (1) One observer pulse serves both directions: a 2-tick pulse spits a
single's block in and pulls it out, so a door of singles needs no separate closing and
opening logic, only edge detection and delays ("Singles", "Spits"). (2) Chains of 1-tick
repeaters make a visual sweep for free, and the ablation separates what is mechanics
(each row's 1-tick steps: a longer step un-spits) from what is presentation (the order
between branches on disjoint cells). (3) Targets are wire-connectable conductors: a
passing dust line powers a target beside it, and the target powers pistons on both sides,
a two-for-one tap without a line end. (4) A stack with a landing-checked rider: the rider
never needs wiring; one observer watching a clock piston fires on its extension and on
its retraction and so gives the rider two strokes per direction, and the stack's pulse
must outlast the rider's spit retraction, or the pull meets a moving piston (R-026).
(5) Separator blocks are wiring too: four solid blocks whose only job is to keep wire
runs from joining are as essential as the wires (4 of the 11 breaking glass replacements).

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 3×3 in the plane x = 3; 9 more output cells outside it.
- Timeline: use lever at 1, use lever at 22; markers Closing 1, Closed 21, Opening 22, Opened 48
- Reference states: closed at tick 21, open at tick 48. Fully closed at ticks 15-25; fully open at 0-2, 36-48.
- Pistons by role: door 19, fires, moves nothing 1
- How extensions were powered (block giving the signal; QC = through the block above the piston): target 12, block←repeater 8, wire 8, observer 4, repeater (QC) 2, block←observer (QC) 2, repeater 2, block←observer 2
- Phases (bursts of piston events): 3–15 (53 events, 19 pistons); 19–36 (57 events, 20 pistons); 40–46 (4 events, 3 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
  0    3    5    7    9   11   13   15   26   28   30   32   34   36
...  ...  ..~  .~#  ~##  ###  ###  ###  ###  ##.  #..  ...  ...  ...
. .  . ~  . #  . #  ~ #  # #  # #  # #  # .  # .  # .  . .  . .  . .
...  ...  ...  ...  ~..  #~.  ##~  ###  ###  ###  ###  .##  ..#  ...

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| above | 6 | 6 | 2×6 | up 1 (6) |
| below | 6 | 6 | 2×6 | down 1 (6) |
| north | 3 | 5 | 2×2, 4×1 | north 1 (2), north 2 (1) |
| south | 2 | 2 | 2×2 | south 1 (2) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| 3 2 -3 S | up | door | 9+2→spat, 30+2→pulled | target 2 |
| 3 2 -2 S | up | door | 11+2→spat, 32+2→pulled | block←repeater 2 |
| 3 2 -1 S | up | door | 13+2→spat, 34+2→pulled | target 2 |
| 3 5 -5 S | south | door | 9+2→spat, 30+2→pulled | observer 2 |
| 3 5 1 S | north | door | 3+2→spat, 24+2→pulled | wire 2 |
| 3 8 -3 S | down | door | 9+2→spat, 30+2→pulled | wire 2 |
| 3 8 -2 S | down | door | 7+2→spat, 28+2→pulled | block←repeater 2 |
| 3 8 -1 S | down | door | 5+2→spat, 26+2→pulled | target 2 |
| 4 5 -6 S | south | door | 11+8→pulled, 32+8→pulled | repeater (QC) 2 |
| 4 5 -5 S | south | door | 22+3→retracted, 43+3→pulled | block←observer (QC) 2 |
| 4 5 -4 S | south | door | 14+1→spat, 35+1→pulled | block←observer 2 |
| 5 2 -3 S | up | door | 9+2→spat, 30+2→pulled | target 2 |
| 5 2 -2 S | up | door | 11+2→spat, 32+2→pulled | block←repeater 2 |
| 5 2 -1 S | up | door | 13+2→spat, 34+2→pulled | target 2 |
| 5 5 -5 S | south | door | 9+2→spat, 30+2→pulled | observer 2 |
| 5 5 1 S | north | door | 3+2→spat, 24+2→pulled | wire 2 |
| 5 8 -3 S | down | door | 9+2→spat, 30+2→pulled | wire 2 |
| 5 8 -2 S | down | door | 7+2→spat, 28+2→pulled | block←repeater 2 |
| 5 8 -1 S | down | door | 5+2→spat, 26+2→pulled | target 2 |
| 4 6 -6 | up | fires, moves nothing | 11+8→retracted, 32+8→retracted | repeater 2 |

<!-- end generated -->
