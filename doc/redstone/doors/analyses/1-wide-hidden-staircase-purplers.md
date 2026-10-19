# 1 Wide Hidden Staircase by Purplers

World: `other_piston_contraptions/1 Wide Hidden Staircase by Purplers.redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(Hand-written 2026-10-19 from the replay's piston events and block changes, the power
reads of `tools.doorlab.power`, the gap replays of `tools.doorlab.inputs` and the stripped
build of [[../mechanism]], on a copy in `.sandbox/doors/explain/1-wide-hidden-staircase-purplers/`;
[[../robustness]], [[../metrics]], [[../symmetry]]. Every tick below is from the
simulator; what is only read from the geometry says so. The trimmed build (71 blocks)
matched the 26.3 server, EXP-071.)

Not a door: a **staircase hidden in a floor**. The build is a 6×4×7 box (x −2..3,
y 1..4, z −5..1; 168 cells, 107 blocks, 13 pistons, 9 repeaters, 3 torches, 12 wires)
whose top layer, y = 4, is a flat sandstone plate: the floor the player walks on
(inferred: it is the only finished face; the trim removes all of it but the shaft's
cells, so it is decoration to the mechanism). Below the plate, in the 1-wide shaft
x = 0, four oak stairs run down to the south: 0 4 −3 (flush with the plate), 0 3 −2,
0 2 −1, 0 1 0 (ground level). The seven output cells are those four and the three plate
cells over the stairs, 0 4 −2..0. **Open** (the build state) the three plate cells are
air and the stairs stand: a 1×3 hole in the floor with steps leading down and out to
the south. **Closed** the hole is filled with sandstone and the three upper stairs are
gone from the shaft; from above the floor is seamless. The lever −1 2 −5 is on the
north face of the mechanism at ground level. Direction-independent: all eight
orientations replay identically. The lever closes it at 1 (every cell filled at 26, 25
ticks) and opens it at 28 (stairs back at 55, 27 ticks).

**The mechanical problem: a stair must leave the shaft and a filler take its cell,
then a filler must rise into the floor.** Each of the four lanes z = −3..0 solves it
with a row of cells across the shaft and a lifter under the shaft cell:

| lane | row (recess · shaft · store) | what is exchanged | lifter |
|---|---|---|---|
| z = −3 | −1 3 −3 · 0 3 −3 · 1 3 −3 | the top stair (parked at 0 3 −3 after a first pull-down) ↔ a sandstone | 0 2 −3, sticky up, fixed; built extended, holding the top stair up at floor level |
| z = −2 | −1 3 −2 · 0 3 −2 · 1 3 −2 | the stair 0 3 −2 ↔ a sandstone | 0 2 −2, sticky up, fixed |
| z = −1 | −1 2 −1 · 0 2 −1 · 1 2 −1 | the stair 0 2 −1 ↔ **a sticky piston** (1 2 −1, facing up) | that piston itself, once it stands in the shaft; the sandstone it lifts is pushed in above it (1 3 −1 → 0 3 −1) by 2 3 −1 |
| z = 0 | · 0 2 0 · 1 2 0 | nothing to remove (the bottom stair 0 1 0 stays) | a second **mobile** sticky piston 1 2 0, pushed to 0 2 0; its sandstone pushed in above it (1 3 0 → 0 3 0) by 2 3 0 |

Each row is worked by two opposed pistons: a plain **west** piston at x = 2 (2 3 −3,
2 3 −2, 2 2 −1) pushes the pair [stair, filler] one cell west, so the stair lands in the
recess at x = −1 and the filler in the shaft; a plain **east** piston at x = −2 (−2 3 −3,
−2 3 −2, −2 2 −1) pushes the pair back. The east pistons are built extended: their heads
fill the recess cells while the stairs are out, and retract first (tick 3) to make
room. The z = −1 and z = 0 fillers above the mobile pistons, and the mobile pistons
themselves, are moved by three **sticky** west pistons (2 3 −1, 2 3 0, 2 2 0), which pull
them home again. 13 pistons: 4 lifters (7 sticky in all), 6 plain movers. The roles of
[[../representation]] call the mobile pistons' mover 2 2 0 a "stack" (it moves a
piston) and the mobile pistons "door" at the cell they fire in.

**Closing** (lever on at 1; the ticks are the piston events, the controller's changes
are in the next section):

| tick | what moves | powered by |
|---|---|---|
| 3 | the three east pistons retract: the recess cells −1 3 −3, −1 3 −2, −1 2 −1 are free | the floor torch −2 2 −4 goes out (its block −2 1 −4 is at the west end of the wire under the lever's block) |
| 5 | the fixed lifter 0 2 −3 retracts and pulls the top stair down, 0 4 −3 → 0 3 −3: the floor cell opens, the stair is in its row | the repeater −1 1 −3 (delay 1) loses the wire −2 2 −3 behind it |
| 9 | 2 3 −3 pushes stair + filler west: the stair into the recess, the sandstone into the shaft | the wall torch 2 3 −4 lights (lever → torch −1 3 −4 off at 3 → repeater 0 3 −4 off at 7 → torch on at 9) and sits next to the piston |
| 12 | 0 2 −3 lifts the sandstone into the floor (0 3 −3 → 0 4 −3) | the repeater 1 1 −3 (delay 1) from the wire 2 1 −3, on at 11; the filler landed at 11, so the push comes one tick after the landing (R-026) |
| 13 | 2 3 −2 pushes its stair + filler west; 2 3 −1 pushes the z = −1 filler 1 3 −1 → 0 3 −1; 2 2 −1 pushes its stair into the recess and the mobile piston 1 2 −1 into the shaft, 0 2 −1 | the repeater 3 2 −3 (delay 2) powers the wool 3 2 −2; the wire 3 3 −2 on top of it powers 2 3 −2 directly, 2 3 −1 through the wool 3 3 −1, and 2 2 −1 by quasi-connectivity through the same wool |
| 16 | 0 2 −2 lifts its filler, 0 3 −2 → 0 4 −2; the mobile piston, landed at 15, lifts its filler 0 3 −1 → 0 4 −1 | the repeater 1 1 −2 (delay 3) on at 15 powers the wool 0 1 −2 (R-026 again); the mobile piston lands on the wool 0 1 −1, powered since 9 by the wire 1 1 −1: a landing check |
| 21 | 2 3 0 pushes the z = 0 filler 1 3 0 → 0 3 0; 2 2 0 pushes the second mobile piston 1 2 0 → 0 2 0 | the repeater 3 2 −1 (delay 4) powers the wool 3 2 0 and, through it, the wire 3 3 0 |
| 24 | the mobile piston at 0 2 0, landed at 23, lifts 0 3 0 → 0 4 0; the block lands at 26: **closed** | a landing check again: the sandstone −1 2 0 beside it is powered by the wire −2 2 0, on since 17 (repeater −2 1 −1, delay 1) |

Closed, the shaft holds (bottom to top) the stair 0 1 0, the two mobile pistons with
their heads, sandstone at 0 3 −2 / 0 3 −3, and the four floor blocks; the three upper
stairs wait in the recess at x = −1.

**Opening** (lever off at 28):

| tick | what moves | why |
|---|---|---|
| 36 | the mobile piston 0 2 −1 retracts and pulls its floor block down, 0 4 −1 → 0 3 −1 | the wall torch 2 3 −4 goes out at 36 (lever → torch −1 3 −4 on at 30 → repeater 0 3 −4 on at 34), and with it every wire it fed: 2 2 −4, 3 2 −4, 2 1 −3, 2 1 −2, 2 1 −1, 1 1 −1 |
| 38 | 0 2 −3 pulls its floor block down | repeater 1 1 −3 off (delay 1 after the wire) |
| 40 | the plain pistons 2 3 −2 and 2 3 −3 retract: their heads leave the store cells 1 3 −2, 1 3 −3 | repeaters 3 2 −3 and 1 1 −4 off (delay 2); 2 3 −3 had stayed on after the torch through the wool 3 3 −3 beside the wire 3 3 −2 (the ablation: that wool is "internal", a second path) |
| 42 | 0 2 −2 pulls its floor block down | repeater 1 1 −2 off (delay 3) |
| 44 | the mobile piston 0 2 0 pulls its floor block down | repeater −2 1 −1 off, the wire −2 2 0 goes out |
| 48 | 2 3 0 and 2 3 −1 pull their fillers back east; 2 2 0 pulls the mobile piston back to 1 2 0; 2 2 −1 retracts | repeater 3 2 −1 off (delay 4) takes the wool 3 2 0 and the wire 3 3 0 with it. 2 2 −1 lost its quasi-power at 40 but nothing updated it: it notices at 48, when its neighbours move (the update problem, harmless here: its head only has to be out of 1 2 −1 before 50) |
| 50 | the three east pistons push the stairs back into the shaft and, with them, the z = −3 / −2 fillers back to x = 1 and the mobile piston back to 1 2 −1 | the floor torch −2 2 −4 relights at 50 (below) |
| 53 | 0 2 −3 lifts the top stair back to floor level, 0 3 −3 → 0 4 −3 (landed 52, lift at 53, R-026); lands 55: **open** | the wire −2 2 −3 is back at 50, the repeater −1 1 −3 on at 52 |

**The controller: one rising edge, fanned out by repeater delays.** The lever's block
−1 2 −4 does three things at once: the wire −1 1 −4 under it turns the floor torch
−2 2 −4 off (the east pistons and, through the wire −2 2 −3 and the repeater −1 1 −3,
the top lifter), the torch −1 3 −4 on top of it goes out and, through the repeater
0 3 −4 (delay 2) and the block 1 3 −4, lights the **wall torch 2 3 −4** at 9. That
torch is the clock edge of the closing: it powers the piston beside it (lane z = −3 at
9), the wire 2 2 −4 under it, and from that wire two lines: east, 3 2 −4 → repeater
3 2 −3 (delay 2, the z −2 / −1 pushes at 13) → repeater 3 2 −1 (delay 4, the z = 0
pushes at 21); and down the step to the y = 1 wires 2 1 −3 → 2 1 −2 → 2 1 −1 → 1 1 −1,
which feed the lifters: repeater 1 1 −3 (delay 1, lane −3), repeater 1 1 −2 (delay 3,
lane −2, and through the wire −1 1 −2 the repeater −2 1 −1 for lane 0), and the wool
0 1 −1 for the mobile piston of lane −1. The opening is the same edge falling at 36 and
the same delays running out: lifts at 36, 38, 42, 44, the sticky pulls at 48.

The **hold chain** is what makes the stairs come back last. The wire 2 2 −4 also powers
the wool 2 1 −4 it lies on, and from there repeater 1 1 −4 (delay 2) → repeater 0 1 −4
(delay 4) → the wire −1 1 −4 under the lever: the same wire the lever itself powers. So
the floor torch stays out after the lever is released (the wire stays on through the
chain) and relights only 14 ticks after the wall torch went out (36 → 40 → 48 → torch 50),
two ticks after the fillers were pulled east at 48 — the torch's own delay orders the
two. Without that chain the east pistons would push the stairs back at 30, into fillers
and heads still in the rows (inferred from the torch's delay; not run).

Exact delays (the ablation, [[../robustness]]): the two delay-2 repeaters of the edge
(0 3 −4, 3 2 −3) and the hold chain's delay-2 (1 1 −4) break the build at 3 or 4 ticks
(the swap pushes come after the lifts, or the stairs come back too early); 1 1 −2 at
delay 1 breaks it (the lane −2 lift before its filler has landed), and the top lifter's
delay-1 (−1 1 −3) at 3 or 4; every other delay change (the delay-4s 0 1 −4 and 3 2 −1
at any setting, the other delay-1s at 2–4) only shifts the timing. 78 of the 191
single changes break the build, 31 change its timing, 76 are inert.

**What the split of [[../mechanism]] misses (backlog D4).** The stripped build differs
from tick 13: the two mobile pistons stand at 1 2 −1 and 1 2 0 in the build and never
fire there (role "idle"), and fire at 0 2 −1 and 0 2 0 (role "door"); the split keeps
pistons by the cell they fire in, so the stripped world has air at 1 2 −1 and 1 2 0.
At 13 the plain piston 2 2 −1 then extends into air instead of pushing stair and
piston, and the lifts of lanes −1 and 0 (16, 24) never happen. A piston that is moved
before it fires must be kept at its build cell.

**The input window** (gaps between the two flips, [[../robustness]]: clean at 1–7,
stuck at 8–9, clean from 10; traced by replaying gaps 7–10):

- At gap 10 (second flip at 11) the closing's push of lane −2 at 13 and the opening's
  east piston −2 3 −2 meet in the same tick: the stair is already moving into the recess
  when the east piston's event runs, so that extension fails on the moving block
  (R-026), lane −1 the other way round (the east piston's head is moving in, the west
  push fails). Both lanes simply keep their stair, nothing is lifted there, and the run
  ends clean.
- At gap 9 (flip at 10) the first event that differs is harmless: the east pistons
  −2 3 −2 and −2 2 −1 extend at 12 (flip2+2), one tick **before** the west pushes of 13,
  which then cannot resolve (a piston head in the row; their wire 3 3 −2 is on 13–22).
  Lane −2 lifts its own stair into the floor at 15 and pulls it back at 24. What jams is
  lane 0: the mobile lifter 0 2 0 pushes its floor block at 24 as designed, and the
  opening's cut (the wire −2 2 0 going out, flip2+16) reaches it at 26, while the block is
  still landing: the retract becomes a **drop**, the sandstone is spat into 0 4 0 and
  the piston comes back without it. 2 3 0 then pulls nothing at 30 and the block stays in
  the floor (final frame `#..####`). Gap 8 is the same one tick earlier (drop at 25).
- At gap 7 the cut arrives in the push's own tick: the event at 24 runs unpowered,
  nothing is lifted, nothing is left behind (shorter gaps cut earlier still; the sweep
  finds 1–7 clean, not traced one by one).

So the staircase's binding constraint is the kind Mumbo Jumbo's door has: **the cut
must come at landing + 1 or later** (push at flip1+23, landing +25, cut at flip2+16:
gap ≥ 10). The row for the staircase in [[../robustness]] "What the second flip waits
for" names the first differing event (the step piston −2 3 −2 at flip2+2) and a step
placed at flip1+8..10 as what it waits for; the events say otherwise: that extension is
harmless, the stair push it pre-empts is at flip1+12 (the same tick as the veto at gap
10), and the gap is set by the lane-0 drop. One more flip after gap 8 or 9 repairs it
(the sweep's `11`): the next closing finds the sandstone already in the floor, 2 3 0 and
0 2 0 extend into empty cells (90, 93), all seven cells are filled from 87, and the
build ends exactly in the designed closed rest state (replayed: gap 9, third flip at
70, every block compared), so the opening after that is the designed one.

**The trim** (107 → 71 blocks, box 168 → 144; game-verified, EXP-071): the whole
y = 4 plate except the shaft's own cells (32 blocks) and four fillers (−1 1 0, 1 1 0,
−1 3 −1, −1 3 0) are slack; nothing of the three layers y 1..3 can go. Glass instead of
the store sandstones 1 3 −3..0 is "internal" (any solid filler will do); 14 conductors
of the power paths break as glass and the wool 3 3 −3 is redundant (internal). Two glass
changes read as "timing" although the staircase is broken: with the lime wool −2 2 −2
as glass the two east pistons it powers never fire, the stairs of lanes −2 and −1 stay in
the recess, and a sandstone and the mobile piston stand in their cells at the end
(replayed); the doorway frames count any solid block as filled, so the markers cannot
tell a stair from a filler (the blue wool −2 3 −4, lane −3's east piston, is the same
kind; not replayed).

**Lessons.** (1) A hidden staircase is four one-cell doors in a column; each is a
**row swap** (recess · shaft · store, two opposed pistons) plus a **lifter** under the
shaft cell: the stair goes sideways, a filler takes its place, the filler goes up.
(2) **A piston can be the filler**: lanes −1 and 0 push a sticky piston into the shaft
cell, where it is at once the solid cell and the lifter of the cell above, powered by a
**landing check** (it lands next to a powered block and fires one tick later, R-026;
[[../patterns]] "landing checks"). (3) One clock edge and a **ladder of repeater
delays** (1, 2, 3, 4 and 2+4) sequences four lanes both ways; the same delays run out
in the opposite order on the falling edge, which is what the opening needs (lifts down,
then fillers east, then stairs east). (4) A **hold chain** (the clock's own wire fed back
through 2+4 ticks of repeaters into the input's wire) keeps the last movers off until
everything else is home: the stairs return 2 ticks after the fillers, ordered by a
torch's delay. (5) Input safety: the only bad gaps (8–9) drop the last lift; a lockout
of 10 ticks, or waiting for the no-overlap gap (18), makes it safe
([[../robustness]], [[../patterns]] "Input safety").

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 4×4 in the plane x = 0; 0 more output cells outside it.
- Timeline: use lever at 1, use lever at 28; markers Closing 1, Closed 27, Opening 28, Opened 56
- Reference states: closed at tick 27, open at tick 56. Fully closed at ticks 26-35; fully open at never.
- Pistons by role: door 12, idle 2, stack 1
- How extensions were powered (block giving the signal; QC = through the block above the piston): block←wire 5, block←repeater 2, block←repeater+wire 2, wire 2, block←torch 1, block←wire (QC) 1, torch 1
- Phases (bursts of piston events): 3–5 (4 events, 4 pistons); 9–16 (7 events, 7 pistons); 21–24 (3 events, 3 pistons); 36–44 (6 events, 6 pistons); 48–53 (8 events, 8 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
   0     5    12    13    14    15    16    18    24    26    36    38
#...  ....  ~...  ~...  #...  #...  #~~.  ###.  ###~  ####  ##.#  .#.#
 #     #     #     ~     ~     #     ~     #     #     #     #     #
  #     #     #     ~     ~     #     #     #     #     #     ~     #
   #     #     #     #     #     #     #     #     #     #     #     #

  42    44    50    52    53    55
...#  ....  ....  ....  ~...  #...
 ~     #     ~     #     #     #
  #     #     ~     #     #     #
   #     #     #     #     #     #

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| recess | 5 | 12 | 2×1, 4×4 | down 1, east 1 (4), east 1 (1) |
| stays in the doorway | 3 | 7 | 2×2, 4×1 | up 1, east 1 (1), east 1 (2) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| -2 2 -1 | east | door | retracted at 3, 50+None→held | block←wire 1 |
| -2 3 -3 | east | door | retracted at 3, 50+None→held | block←torch 1 |
| -2 3 -2 | east | door | retracted at 3, 50+None→held | block←wire 1 |
| 0 2 -3 S | up | door | pulled at 5, 12+26→pulled, 53+None→held | block←repeater 2 |
| 0 2 -2 S | up | door | 16+26→pulled | block←repeater+wire 1 |
| 0 2 -1 S | up | door | 16+20→pulled | block←wire 1 |
| 0 2 0 S | up | door | 24+20→pulled | block←wire 1 |
| 2 2 -1 | west | door | 13+35→retracted | block←wire (QC) 1 |
| 2 3 -3 | west | door | 9+31→retracted | torch 1 |
| 2 3 -2 | west | door | 13+27→retracted | wire 1 |
| 2 3 -1 S | west | door | 13+35→pulled | block←wire 1 |
| 2 3 0 S | west | door | 21+27→pulled | wire 1 |
| 2 2 0 S | west | stack | 21+27→pulled | block←repeater+wire 1 |

<!-- end generated -->
