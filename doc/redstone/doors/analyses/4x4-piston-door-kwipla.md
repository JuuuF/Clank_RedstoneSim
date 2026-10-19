# piston door by Kwipla

World: `piston_doors/4x4 piston door by Kwipla.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(Hand-written 2026-10-19 from the replay, `waves` and `why` traces on a copy in
`.sandbox/doors/explain/4x4-piston-door-kwipla/`, and one counterfactual (the furnaces).
Every tick below is from the simulator; what is only inferred from the geometry says so.
Not run on the game server, except the trimmed build of EXP-074, which matched.)

A 4x4 door in the plane x = 0 (cells y 8..11, z −3..0), built open, 28 pistons ([[../metrics]]), 16 iron
door blocks, in a 10 × 9 × 12 box (158 blocks above the floor, 142 of them needed,
[[../robustness]]). Two stone buttons stand on the floor on both sides of the wall
(−4 7 −4 and 5 7 −4) and join one wire ring; the run presses the west one at 1 and 37.
The doorway is full 27 ticks after the first press (tick 28) and empty 39 ticks after the
second (76); the mechanism is at rest at 38 and 78. The build is **mirror-symmetric about
z = −1.5**: every piston event of the south half (z ≥ −1) happens in the same tick in the
north half (z' = −3 − z), so the text follows the south half. All eight orientations
replay identically ([[../symmetry]]).

**Piston layout and grouping.** The bottom row goes *down* and the top row *up*, one
sticky piston per block: four facing up at y = 6 push the bottom blocks from the cell
below the doorway (y = 7) up into y = 8 and hold them there for the whole closed state (one 36-tick
pulse); four facing down at y = 13 spit the top blocks from y = 12 down into y = 11
(2-tick pulses) and pull them back up when opening. The two **middle rows are the hard
part**: their eight blocks must leave sideways, two per row and side, and the inner cells
(z = −2, −1) are two cells from the frame. Kwipla's storage for each side is one
**column at z = 1** (north: z = −4), y 8..11, holding all four blocks of that side when
the door is open: the two inner blocks (8 at 0 9 1, 9 at 0 10 1) and, parked below and
above them, the two outer blocks (16 at 0 8 1, 12 at 0 11 1). Behind the column, at
z = 2, two sticky pistons face north (0 9 2, 0 10 2); behind those, at z = 3, two more
(0 9 3, 0 10 3) that push the z = 2 pistons one cell into the column and pull them back:
a **double extender** of sticky pistons (the "stack" role, [[../patterns]]), which gives
the inner blocks their reach of two. Two vertical pistons serve the parking cells: 0 7 1
(up) under the column and 0 12 1 (down) above it, with a **furnace** at 0 13 1 capping
the column (its role below).

**Closing** (press at 1; the north half mirrors every step):

| tick | what happens |
|---|---|
| 2 | the button's ring powers the block 3 6 −7; sticky piston 3 6 −6 pushes the observer 3 6 −5 one cell south to 3 6 −4 (a moving power source: the observer lands at 4 and pulses at 6, R-015) |
| 6 | the pulse makes sticky piston 3 6 −3 spit the **redstone block** from 3 6 −2 to 3 6 −1 (it lands at 8): the door's memory, now "closed" |
| 10 | the redstone block feeds repeater 2 6 −1 (delay 1), which powers block 1 6 −1 and through it the wires 1 6 −2 / 1 6 0: the four bottom pistons 0 6 z lift the bottom row (0 7 z → 0 8 z) and stay out; piston 1 6 1 extends (it moves nothing: its head at 1 7 1 is a signal, below); helper 0 5 0 pushes a stone from 0 5 1 to 0 5 2, under observer 0 6 2 |
| 12 | observer 0 6 2 (the stone arrived) powers wire 0 7 2 → block 0 7 3 → plain piston 0 8 3 extends east: its head at 1 8 3 is another signal. The wire also powers 0 7 1, whose push fails: the column above it holds six blocks ending in the furnace |
| 14 | observers 1 7 2 → 1 8 2 (they saw the head of 1 6 1 at 10) power block 1 9 2 and the wire 1 10 2 on it: 0 9 2 and 0 10 2 **spit** blocks 8 and 9 from z = 1 to z = 0. Observer 0 8 2, watching the piston 0 8 3, pulses and quasi-powers 0 7 1 (it powers the cell 0 8 1 above it); the push is stopped by block 8, still moving through 0 9 1 (R-026, [[../records/R-026-moving-block-blocks-piston]]) |
| 16 | observers 1 9 3 → 1 10 3 (the head of 0 8 3) power block 1 11 3 and the wire 1 12 3 on it for 2 ticks: this starts repeater 0 12 3 (delay 4) and observer 1 12 2 |
| 18 | 1 12 2 powers block 1 12 1 and the wire 1 13 1 on it, which powers the **furnace 0 13 1**: pistons 0 12 1 (below it) and 0 13 0 (beside it) spit the outer top blocks down (12: 0 11 1 → 0 10 1 into the parking cell; 13: 0 12 0 → 0 11 0). Observer 0 8 2's second pulse (0 8 3 finished retracting at 16) quasi-powers 0 7 1 again: now it lifts 16 from 0 8 1 to 0 9 1 |
| 20 | observer 1 13 0 (watching the wire 1 13 1) powers block 1 13 −1: 0 13 −1 spits the inner top block down (and 1 13 −3 → 0 13 −2 on the north side); the top row is complete |
| 21 | the stone button releases (20 ticks); 3 6 −6 pulls the slider observer back to 3 6 −5 |
| 24–26 | repeater 0 12 3 turns on 8 ticks after its input; observer 0 11 3 below it pulses at 26 and powers the stack pistons 0 10 3 (directly) and 0 9 3 (by quasi-connectivity, the cell above it is 0 10 3): each pushes three blocks north, the z = 2 piston to z = 1, the outer block from z = 1 to z = 0 and the inner block from z = 0 to z = −1. The doorway is full at **28**; the stacks drop (spit) at 28 |
| 32–36 | the repeater turns off at 32 (a 2-tick input is stretched to the repeater's 8-tick delay); 0 11 3 pulses again at 34: the stacks extend into the empty z = 2 cell and at 36 pull the door pistons back to z = 2 (they land at 38). The bottom row stays up: its pistons are held by the memory's level |

**Opening** (press at 37): the slider observer is pushed again (38, lands 40, pulses 42);
this time 3 6 −3 extends into the empty 3 6 −2 and at 44 **pulls the redstone block
back** (it lands at 46). A sticky piston and one block are a T flip-flop: a 2-tick pulse
spits the block away when it is in front of the piston, and brings it back when it is
one cell further (the piston's own front cell does not power a piston, so the block
resting there is harmless). With the memory "open":

| tick | what happens |
|---|---|
| 46 | repeater 2 6 −1 off: the bottom pistons pull the bottom row down into y = 7; 1 6 1 retracts (its head leaves 1 7 1: a signal again); the helper pulls its stone back from 0 5 2 |
| 48 | observer 0 6 2 → wire 0 7 2: 0 8 3 extends for 2 ticks (its head at 1 8 3 is the signal); 0 7 1 extends into the empty 0 8 1 and is back at 50 (harmless) |
| 50–52 | 1 7 2 → 1 8 2 (the head of 1 6 1 left at 46): 0 9 2 and 0 10 2 extend into the empty z = 1 cells and at 52 **pull the outer blocks** 16 (0 9 0 → 0 9 1) and 12 (0 10 0 → 0 10 1) out of the doorway |
| 52–58 | 1 9 3 → 1 10 3 → wire 1 12 3 (52–53) → 1 12 2 at 54 → the furnace: 0 12 1 and 0 13 0 extend at 54 and at 56 pull 12 up into its parking cell (0 10 1 → 0 11 1) and 13 up (0 11 0 → 0 12 0). 0 8 2's second pulse at 54 quasi-powers 0 7 1 at 55 for one tick: at 56 it pulls 16 down into 0 8 1. 1 13 0 at 56 → 0 13 −1 pulls the inner top block up at 58 |
| 56–62 | the same wire pulse of 48 also fed repeater 1 7 3 (delay 4, through block 0 7 3). Its output goes into air: only its **state** is used. It is on 56–63; observer 1 6 3 watches it and pulses at 58 and 66, 1 5 3 at 60 and 68, 1 5 2 at 62 and 70, powering block 1 5 1 under piston 1 6 1, which fires at 62 and 70 for 2 ticks each |
| 60–64 | repeater 0 12 3 is on 60–67; 0 11 3 pulses at 62: the stacks push the door pistons 0 9 2 / 0 10 2 into z = 1 and spit them (64) |
| 66–68 | 1 7 2 → 1 8 2 (the head of 1 6 1 at 62): the wire 1 10 2 powers block 1 10 1 beside the moved piston 0 10 1 (direct) and above 0 9 1 (quasi-connectivity): both extend into z = 0 and at 68 **pull the inner blocks** 9 (0 10 −1 → 0 10 0) and 8 (0 9 −1 → 0 9 0) |
| 70–72 | 0 11 3 again (the repeater turned off at 68): the stacks extend into z = 2 and pull the door pistons back there at 72; they land at 74 |
| 74–76 | 1 8 2's second pulse (from 1 6 1's pulse at 70) powers block 1 9 2 at 74–75; the pistons landing at 74 beside it extend at 75 (the landing check) for one tick and at 76 pull 8 and 9 from z = 0 into z = 1. Open at **76**; everything at rest at 78 |

**How the pistons are powered** (the facts table): the bottom row, the helper and the
trigger piston 1 6 1 get a *level* from the memory (redstone block → repeater → block →
wire). Everything else gets 2-tick *pulses* from observers, directly (0 10 3, 0 10 −6) or
through a solid block or a wire on one. Quasi-connectivity is used three times on the
south side and saves a conductor each time: 0 9 3 under the stack piston 0 10 3 (one
observer drives both), 0 7 1 under the cell the observer 0 8 2 faces, and 0 9 1 under
the moved piston 0 10 1; the north side has a fourth, its helper 0 5 −3 (the south helper
0 5 0 has a powered block beside it, 1 5 0; the north one has air there and reads the
block 1 6 −3 above its neighbor). The two furnaces are the power blocks of the outer
top pistons.

**Mechanics as logic.** Three times the wiring powers a piston at the wrong moment and
the mechanics veto it. (1) At 12 the wire 0 7 2 powers 0 7 1 (it is beside it), but
the column above holds four door blocks, the retracted piston 0 12 1 and the furnace,
which cannot move: the push fails, nothing is queued. Replacing both furnaces by smooth
stone (`furnace_to_stone.redsim.json` in the sandbox folder) lifts the whole column at
12 (the piston ends at 0 13 1, the stone at 0 14 1), the top corners never close and
15 blocks are wrong at the end: the furnace is an **immovable cap**, not decoration.
(2) At 14 the observer 0 8 2 quasi-powers 0 7 1 while block 8 is moving through 0 9 1:
a moving block stops the piston (R-026). (3) At 48 0 7 1 extends into air and comes back.
The design works because the third attempt (18) and the one-tick pull (55) are the only
ones that move anything. Whether Kwipla planned the furnace for this or found it, the
evidence does not say; that it is needed is verified.

**Controller.** The only state is the redstone block's cell. The rest is a tree of
observer chains hanging off two edges (the memory's level turning on and off), with the
repeaters giving the long waits: both have delay 4 and do two things each, delaying a
chain by 8 ticks and stretching the 2-tick pulse they get to 8 ticks, so that the
observer watching them fires twice, 8 ticks apart. That is where the "push the pistons
in, pull them back 8 ticks later" pairs of the stacks (26 / 34, 62 / 70) and the two
pulses of 1 6 1 (62 / 70) come from. The pistons 1 6 1, 1 6 −4, 0 8 3 and 0 8 −6 move
nothing: their heads are what observers watch ("fires, moves nothing" in the facts). The
closing's chain through repeater 1 7 3 fires 1 6 1's block at 26 and 34 too, but the
piston is already held out by the level then, so nothing happens: a chain whose result
is used only in one direction. The contract ([[../mechanism]]): 24 mechanism pistons, 54
pulses, and the stripped door moves its doorway identically. Its same-tick
"retract, then extend" ticks 20, 50 and 56 pair pistons that do not touch (20: the
outer top spits end while the inner ones start; 50: 0 7 1 leaves an empty cell while
0 9 2 enters another; 56: the top pulls while 0 13 −1 extends above a different block).

**Input.** Safe gap 25 ticks, no-overlap gap 37, the designed 36 ([[../robustness]]).
Presses within the button's 20 ticks are no input; gaps 20–24 jam it (at the last bad
gap a push hits a sticky piston that is still extended, [[../robustness]]; which push is
not traced here). The memory makes every registered press alternate, so after an
ignored press the door is simply one press behind.

**Compared with Sydney600mc's 4x4** ([[4x4-piston-door-sydney600mc]]): the same grouping
(4 up, 4 down, 2 × 4 sideways in two moves, with the outer side blocks parked above and
below), but Sydney's is three blocks deep (3 × 9 × 10, volume 270 against 1080), closes in
16 ticks and opens in 26 (27 / 39 here), with 8 wires and 20 observers where Kwipla uses 26
and 25. Sydney moves the sides first (spits at 5), the vertical rows at 9 and the
extender stage at 15 as one 7-tick pulse; Kwipla lifts the bottom row first (10), spits
the inner side blocks at 14, parks at 18–20 and runs the extender as a push-and-pull pair
(26, 34). Which of the two orders is forced and which is a choice is not analyzed.

**Lessons.** (1) **A sticky piston and one block are a one-bit memory**: one 2-tick pulse
per press toggles the block between two cells, and the cell decides which circuits see
a redstone block; this is how one button gives "close" and then "open" (block swapper,
[[../patterns]]). (2) **Observers chains are the clock**: each observer adds 2 ticks and
turns any block change into a 2-tick pulse; a piston's head appearing, a stone pushed
into view and a repeater's state are all valid triggers, so pistons that move nothing and
a repeater that outputs into air are timing parts. (3) **A repeater watched by an observer
gives two pulses its delay apart** (on and off), the cheapest "do, then undo later". (4)
**Immovable blocks are logic too**: a furnace capping a column vetoes a push the wiring
would make at the wrong time, and a moving block does the same for a tick (R-026);
the layout's constraints are part of the sequence, not only the wiring. (5) The 4x4's
inner middle cells need a reach of two: a double extender of sticky pistons, with the
outer blocks parked vertically so the storage column is free for the first move.

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 4×4 in the plane x = 0; 0 more output cells outside it.
- Timeline: use stone_button at 1, use stone_button at 37; markers Closing 1, Closed 36, Opening 37, Opened 78
- Reference states: closed at tick 36, open at tick 78. Fully closed at ticks 28-45; fully open at 0-9, 76-115.
- Pistons by role: door 24, fires, moves nothing 4, helper 2, power mover 2
- How extensions were powered (block giving the signal; QC = through the block above the piston): block←wire 19, observer (QC) 12, wire 11, observer 10, block←observer 8, block←observer+wire 6, block←wire (QC) 3, block←repeater+wire 1
- Phases (bursts of piston events): 2–2 (1 events, 1 pistons); 6–22 (54 events, 24 pistons); 26–28 (12 events, 4 pistons); 34–38 (13 events, 5 pistons); 42–58 (60 events, 24 pistons); 62–76 (60 events, 14 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
   0    10    12    14    16    18    20    22    26    28    46    52
....  ....  ....  ....  ....  ~..~  #~~#  ####  ####  ####  ####  ####
....  ....  ....  ~..~  #..#  #..#  #..#  #..#  ~~~~  ####  ####  .##.
....  ....  ....  ~..~  #..#  #..#  #..#  #..#  ~~~~  ####  ####  .##.
....  ~~~~  ####  ####  ####  ####  ####  ####  ####  ####  ....  ....

  56    58    66    68    70    76
.##.  ....  ....  ....  ....  ....
.##.  .##.  ~##~  ~..~  #..#  ....
.##.  .##.  ~##~  ~..~  #..#  ....
....  ....  ....  ....  ....  ....

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| below | 4 | 4 | 2×4 | down 1 (4) |
| south | 4 | 8 | 4×4 | south 2 (2), up 1, south 1 (1), down 1, south 1 (1) |
| north | 4 | 8 | 4×4 | north 2 (2), up 1, north 1 (1), down 1, north 1 (1) |
| above | 4 | 4 | 2×4 | up 1 (4) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| 0 6 -3 S | up | door | 10+36→pulled | block←wire 1 |
| 0 6 -2 S | up | door | 10+36→pulled | wire 1 |
| 0 6 -1 S | up | door | 10+36→pulled | block←repeater+wire 1 |
| 0 6 0 S | up | door | 10+36→pulled | wire 1 |
| 0 7 -4 S | up | door | 18+2→spat, 48+2→retracted, retracted at 52, 55+1→pulled | observer (QC) 2, wire 1 |
| 0 7 1 S | up | door | 18+2→spat, 48+2→retracted, retracted at 52, 55+1→pulled | observer (QC) 2, wire 1 |
| 0 9 -6 S | south | door | 26+2→spat, 34+2→pulled, 62+2→spat, 70+2→pulled | observer (QC) 4 |
| 0 9 -5 S | south | door | 14+2→spat, 50+2→pulled, 75+1→pulled | block←observer+wire 3 |
| 0 9 -4 S | south | door | 66+2→pulled | block←wire (QC) 1 |
| 0 9 1 S | north | door | 66+2→pulled | block←wire (QC) 1 |
| 0 9 2 S | north | door | 14+2→spat, 50+2→pulled, 75+1→pulled | block←observer+wire 3 |
| 0 9 3 S | north | door | 26+2→spat, 34+2→pulled, 62+2→spat, 70+2→pulled | observer (QC) 4 |
| 0 10 -6 S | south | door | 26+2→spat, 34+2→pulled, 62+2→spat, 70+2→pulled | observer 4 |
| 0 10 -5 S | south | door | 14+2→spat, 50+2→pulled, 75+1→pulled | wire 3 |
| 0 10 -4 S | south | door | 66+2→pulled | block←wire 1 |
| 0 10 1 S | north | door | 66+2→pulled | block←wire 1 |
| 0 10 2 S | north | door | 14+2→spat, 50+2→pulled, 75+1→pulled | wire 3 |
| 0 10 3 S | north | door | 26+2→spat, 34+2→pulled, 62+2→spat, 70+2→pulled | observer 4 |
| 0 12 -4 S | down | door | 18+2→spat, 54+2→pulled | block←wire 2 |
| 0 12 1 S | down | door | 18+2→spat, 54+2→pulled | block←wire 2 |
| 0 13 -3 S | down | door | 18+2→spat, 54+2→pulled | block←wire 2 |
| 0 13 -2 S | down | door | 20+2→spat, 56+2→pulled | block←observer 2 |
| 0 13 -1 S | down | door | 20+2→spat, 56+2→pulled | block←observer 2 |
| 0 13 0 S | down | door | 18+2→spat, 54+2→pulled | block←wire 2 |
| 0 8 -6 | east | fires, moves nothing | 12+2→spat, 48+2→spat | block←wire 2 |
| 0 8 3 | east | fires, moves nothing | 12+2→spat, 48+2→spat | block←wire 2 |
| 1 6 -4 | up | fires, moves nothing | 10+36→retracted, 62+2→spat, 70+2→spat | block←wire 1, block←observer 2 |
| 1 6 1 | up | fires, moves nothing | 10+36→retracted, 62+2→spat, 70+2→spat | wire 1, block←observer 2 |
| 0 5 -3 S | north | helper | 10+36→pulled | block←wire (QC) 1 |
| 0 5 0 S | south | helper | 10+36→pulled | block←wire 1 |
| 3 6 -6 S | south | power mover | 2+19→pulled, 38+19→pulled | block←wire 2 |
| 3 6 -3 S | south | power mover | 6+2→spat, 42+2→pulled | observer 2 |

<!-- end generated -->
