# piston door by pal1_

World: `piston_doors/3x4 piston door by pal1_.redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(Hand-written 2026-10-19 from the replay, `waves`, `why` and `inspect` on a copy, the
mechanism split and three one-change experiments in
`.sandbox/doors/explain/3x4-piston-door-pal1/` (A, B, D below, with a README);
[[../robustness]], [[../metrics]], [[../symmetry]]. Every tick is from the simulator;
what is only inferred says so. Not run on the game server.)

A 3 wide × 4 high door in the plane z = −3 (cells x 4..6, y 5..8), built open, 15 sticky
pistons, 12 gold door blocks. **The whole build is in that one plane**; only the lever
sticks out behind it (6 1 −4, on the north face of the note block 6 1 −3). Box 10 × 14 × 2
= 280 cells, 92 blocks above the floor, 89 of them needed: the trim removes three, and
118 of the 140 single-block changes break the door ([[../robustness]]). The world has
no `input` section ([[../inventory]]); its timeline uses the lever at 1 and at 38. The
doorway is full 28 ticks after the first flip (**closed at 29**) and empty 44 ticks after
the second (**open at 82**). Direction-independent: all eight orientations replay
identically ([[../symmetry]]).

**Piston layout.** The side columns x = 4 and x = 6 are eight **singles**: four sticky
pistons at x = 2 facing east (y 5..8) push the west blocks from x = 3, inside the wall,
into x = 4, and four at x = 8 facing west push the east blocks from x = 7 into x = 6; one
cell each. The **center column x = 5 is the hard part** (a 3-wide door has no wall beside
it). pal1_ solves it as Mumbo Jumbo's flush 3x3 solves its center and bottom-middle cells
([[3x3-piston-door-mumbo-jumbo]]), **twice**: the lower two cells come from the floor,
the upper two from the ceiling, each with a **double extender** (two sticky pistons in a
column: 5 2 / 5 3 facing up below the doorway, 5 11 / 5 10 facing down above it) and a
sideways **floor piston** (3 4 facing east in the floor, 7 9 facing west in the ceiling).
Open, the four center blocks rest at 5 4 (C, right above the lower stack), 4 4 (B, in the
floor beside it), 5 9 (C', right below the upper stack) and 6 9 (B', in the ceiling beside
it). Power access, from the replay: block←observer 9, wire 6, observer 5, wire (QC) 5,
repeater 4, block←observer (QC) 3, block←observer+wire 2, repeater (QC) 2.

**Controller: one pulse per piston, on both edges.** The lever sits on a note block,
whose `powered` state follows it. Three observers watch the note block (5 1 to the west,
7 1 to the east, 6 2 above) and each gives a 2-tick pulse on *both* edges, so the same
pulses close and open the door: a sticky piston that gets a 2-tick pulse **spits** the
block in front of it one cell further when the block is adjacent, and **pulls it back**
when the block is one cell beyond its head (the T flip-flop of [[4x4-piston-door-kwipla]];
the same principle as Lutal's and Purplers' spiral doors). The pulses are relayed up both
sides by chains of observers, each watching the block, wire, hopper or note block the
previous one powers ("observer chains", [[3x3-piston-door-sacredredstone]]): 22
observers, 5 repeaters, 10 wires, 4 hoppers, 2 note blocks. The hoppers are just
observable blocks (their `enabled` property flips when they are powered): experiment A
replaces 9 4 −3 by a note block and every piston event and frame stays the same. The
paths, with the ticks of the closing edge (`waves`):

- **West column**: note block powered at 1 → observer 5 1 fires 3–4 → observer 4 1
  (watching it) 5–6 → block 3 1 → wire 3 2 on 5–6, which feeds three branches: observer
  3 3 fires 7–8 straight into the floor piston 3 4; repeater 4 2 (delay 4) turns the
  2-tick input into 13–20 for the stack piston 5 2; observer 2 2 fires 7–8 → block 1 2 →
  hopper 1 3 → observer 1 4 fires 9–10 → block 1 5, read by 2 5 directly and by 2 6
  through the wire 1 6 on it → observer 1 7 (watching that wire) fires 11–12 → block 1 8,
  read by 2 8 directly and by 2 7 through quasi-connectivity (the cell above it).
- **East column**: observer 7 1 fires 3–4 → block 8 1 → hopper 9 1 → observer 9 2 5–6 →
  block 9 3 → hopper 9 4 → observer 9 5 7–8 → wire 9 6, read by 8 6 directly and 8 5 by
  QC → observer 9 7 9–10 → wire 9 8 → 8 8 and 8 7 (QC) → observer 9 9 11–12 → block 9 10
  → hopper 9 11 → observer 9 12 13–14 → block 9 13 → the wire line over the top (9 14,
  8 13, 7 14, 6 14) → block 6 13 → repeater 5 13 (delay 1) 15–16 → block 4 13 → **note
  block 4 12 powered 15–16: the top half's own lever, 14 ticks after the real one.**
  Experiment D (that repeater at delay 2): the whole top half runs 2 ticks later (closed
  31, open 84) and the bottom half is unchanged: the two halves are independent.
- **Center, bottom**: observer 6 2 (above the note block) fires 3–4 → block 6 3 → piston
  5 3 at 3.
- **Center, top** (from the note block 4 12): observer 4 11 below it fires 17–18 → block
  4 10 → piston 5 10 at 17; observer 3 12 fires 17–18 → the slider piston 2 12; observer
  5 12 fires 17–18 → observer 6 12 19–20 → block 7 12 → wire 7 11 on 19–20 → observer
  7 10 (watching that wire) fires 21–22 straight into the ceiling piston 7 9, and
  repeater 6 11 (delay 4) makes 27–34 for the stack piston 5 11 (5 10 is quasi-connected
  to the same repeater through 5 11 and queues too, but is moved first: "skipped").

**Closing** (lever on at 1):

| tick | what happens |
|---|---|
| 3 | 5 3 pushes C up one (5 4 → 5 5); its power ends at 5, the drop spits C (it lands at once) and the head comes back: 5 4 is free |
| 7 | the floor piston 3 4 pushes B east under C (4 4 → 5 4), spat at 9; the east lower singles 8 5 / 8 6 push 7 5 / 7 6 → 6 5 / 6 6, spat at 9 |
| 9 | the west lower singles 2 5 / 2 6 push → 4 5 / 4 6 (spat 11); the east upper singles 8 7 / 8 8 → 6 7 / 6 8 (spat 11) |
| 11 | the west upper singles 2 7 / 2 8 → 4 7 / 4 8 (spat 13) |
| 13 | the lower stack: 5 2 extends and pushes 5 3, B and C up one each (C to 5 6, B to 5 5, the piston to 5 4); the bottom two rows are closed at 15 |
| 17 | the upper stack's front piston 5 10 pushes C' down one (5 9 → 5 8), spat at 19; the slider piston 2 12 extends into the empty 1 12 and at 19 pulls the observer from 0 12 to 1 12 (it lands at 21 and pulses at 23 into air: parked) |
| 21 | 5 2 retracts and takes 5 3 back down (lands 23; B and C stay: only the block in front of the head is pulled); the ceiling piston 7 9 pushes B' west under C' (6 9 → 5 9), spat at 23 |
| 27 | the upper stack: 5 11 pushes 5 10, B' and C' down one (C' to 5 7, B' to 5 8, the piston to 5 9): **all twelve cells solid at 29** (the markers say Closed at 37) |
| 35 | 5 11 retracts and takes 5 10 back up (lands 37); the door is at rest |

**Opening** (lever off at 38; the same observers fire on the falling edge):

| tick | what happens |
|---|---|
| 40 | 5 3 extends into the empty 5 4 and at 42 pulls B down (5 5 → 5 4) |
| 44 | 3 4 extends into the empty 4 4 and at 46 pulls B home (5 4 → 4 4); 8 5 / 8 6 extend into the empty 7 5 / 7 6 and at 46 pull their blocks back to x = 7 |
| 46–50 | 2 5 / 2 6 and 8 7 / 8 8 extend at 46 and pull at 48; 2 7 / 2 8 at 48 and 50: the side columns are empty at 50 |
| 50 | 5 2 lifts 5 3 to 5 4 (nothing else moves: 5 5 is empty). The lifted piston lands at 52 beside B's home 4 4, which the observer 4 3 (watching the repeater 4 2, now on) powers at 52–53: a **landing check**: it extends at 53 and at 54 pulls C down one (5 6 → 5 5) |
| 54 | 5 10 extends into the empty 5 9 and at 56 pulls B' up (5 8 → 5 9); the slider 2 12 pushes the observer back from 1 12 to 0 12 (spat at 56) |
| 56 | 7 9 extends (quasi-powered by the wire 7 11). Its wire power ends at 58, but the observer 7 10, watching that wire, fires at 58–59 straight into it (`at 58 inspect 7 9 −3`: "receives up 15"), so the retract event of 58 finds it powered and does nothing; at 60 it retracts and pulls B' home (5 9 → 6 9, lands 62) |
| 58 | 5 2 retracts and takes 5 3 down (lands 60). The observer 4 3 fires again on the repeater's falling edge (60–61) and powers B at 4 4, which **quasi-powers the landed piston** (the cell above it, 5 4, is beside B): it extends at 61, its head lands at 63 and updates it, and at 64 it pulls C home (5 5 → 5 4). The bottom is at rest at 66 |
| 64 | the upper stack: 5 11 pushes 5 10 down to 5 9 (C' at 5 7 is not in the way, 5 8 is empty). The lowered piston lands at 66 beside B' at 6 9, which the observer 6 10 (watching the repeater 6 11, now on) powers at 66–67: it extends at 67 and at 68 pulls C' up one (5 7 → 5 8) |
| 72 | 5 11 retracts and takes 5 10 home (lands 74). Nothing powers it there (below) |
| 80 | the slider observer's delayed pulse: it landed at 0 12 at 56 and pulsed at 58 (R-015) into the wire 0 11 → block 0 10 → repeater 1 10 (delay 4: on 66–73) → repeater 2 10 (delay 2: on 70–77) → observer 3 10, which fires on both edges, at 72–73 (5 10 is still being carried home: lost) and at 80–81 → block 4 10 → 5 10 extends at 80 and at 82 pulls C' home (5 8 → 5 9). **Open at 82** (the markers say Opened at 85) |

**Why the top needs a timer and the bottom does not.** Quasi-connectivity is one-way: a
piston also reads the cell above it, never the one below. The lower stack lifts 5 3 to
5 4, next to B's home cell 4 4, so a pulse on B reaches the lifted piston directly (53)
and the lowered one through the cell above it (61): both pulls of C come from one
observer (4 3) on the two edges of the stack's repeater. Mirrored, the upper piston 5 10
is lowered to 5 9 next to B' at 6 9 (67 works the same way), but at home the cell above
it is the other stack piston, not B': the last pull needs a pulse of its own after 5 11
has brought 5 10 home at 74. That is what the slider observer and the two repeaters are:
a **landing-pulse timer** (an observer slider, [[../patterns]]; R-015: a moved observer
pulses 2 ticks after it is set down) started by the opening edge, 22 ticks from pulse to
pulse, whose first output (72) is wasted on the moving piston and whose second (80) does
the job. On the way in the observer is parked at 1 12, where its landing pulse (23) falls
on air, so the timer runs only when opening. Experiment B (the wire 0 11 removed): the
run is identical up to 82, then the last pull never comes and C' stays at 5 8, in the
doorway.

**Same-tick order and the stripped door** ([[../mechanism]]: 16 mechanism pistons, 32
pulses, a retract before an extension at ticks 9, 11, 21, 46, 48, 56, 64, the stripped
door differs from 10). The order inside a tick does not matter here: the spits and the
extensions of one tick act on different cells (at 9: B's spit at 5 4 and four singles'
pushes). The stripped door fails for the D4 reason: the storage columns x = 2 and x = 8
are columns of four pistons, and an editor pulse on a piston also quasi-powers the piston
below it. In the stripped replay 8 5 and 8 6 do not spit at 9; they stay out one and two
ticks longer and then retract *pulling their blocks back* (10, 11), and the west column
does the same at 12 / 13; the first doorway difference is at 10 (the stripped events are
verified; that the pulses on 8 6 / 8 7 hold them is inferred from the D4 rule).

**Input window** ([[../robustness]]). Safe gap 20 (designed 37, no-overlap 35): every
gap 1–19 leaves the doorway stuck, and only 10–11 recover with one more flip. The binding
event at gap 19 (D11 table): the closing stack lowers 5 3 at flip1+20 (tick 21, lands
23) and its landing extension runs at 24, unpowered, because the opening pulse from the
observer 6 2 is over by then (replayed here: at gap 19 the observer is on at 22–23 and
the extension fails "unpowered"; at gap 20 it is on at 23–24 and the extension runs, then
pulls B at 25: "the pulse must cover landing+1", R-026). At gap 6 both center blocks end up the
column (5 6, 5 5): that cycle missed the stack's push at 13 and the pulls at 54 / 64, and
every later cycle pulls them one cell and pushes them back up; no second-cycle gap 1–40
repairs it (D10): edge-pulse toggles do not self-correct.

**Compared with Mumbo Jumbo's 3x3** ([[3x3-piston-door-mumbo-jumbo]], [[../metrics]]):
the same center solution, doubled. Mumbo Jumbo: 12 pistons, a 3 × 9 × 7 box (189), 87
blocks, closed in 10 and open in 24 ticks, safe gap 10, a controller of wire, torches,
repeaters and a comparator clock. pal1_: 15 pistons for 12 door blocks, 10 × 14 × 2
(280), 92 blocks, 28 / 44 ticks, safe gap 20, a controller of observer chains. The
observers make the build two blocks deep and the same in both directions, but every
relay costs 2 ticks and the top half waits 14 ticks for its signal to climb the east
column.

**Lessons.** (1) The flush-door center solution (spit C up, slide B under it, push both;
to open: lift the piston, pull C down one, lower it, pull again) extends to a 3x4 by
doing it from the floor and from the ceiling ([[../patterns]]: floor storage, extenders,
spits). (2) One pulse serves both directions: observers on the lever's note block give
the same 2-tick pulse on both edges, and a sticky piston does the right thing with it in
either state (spit the adjacent block, pull back the one beyond its head), so the door
has no separate closing and opening logic. (3) Quasi-connectivity is not up-down
symmetric: a mirrored stack needs extra timing where the cell above a piston is the
other stack piston instead of the storage (the observer-slider timer, [[../patterns]]
moving power sources). (4) Observable blocks are interchangeable relays: a hopper does
what a note block does (A). (5) A flat observer build has no slack: 89 of 92 blocks are
needed, and the same-tick order is free.

Not verified: no game-server run; the hopper swap was run for 9 4 −3 only; the stripped
door's quasi-power reading is inferred (D4), its events are not; the gap-19 replay above
is the only part of the input sweep re-run here, the rest is cited.

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 3×4 in the plane z = -3; 0 more output cells outside it.
- Timeline: use lever at 1, use lever at 38; markers Closing 1, Closed 37, Opening 38, Opened 85
- Reference states: closed at tick 37, open at tick 85. Fully closed at ticks 29-41; fully open at 0-2, 82-97.
- Pistons by role: door 16, power mover 1
- How extensions were powered (block giving the signal; QC = through the block above the piston): block←observer 9, wire 6, observer 5, wire (QC) 5, repeater 4, block←observer (QC) 3, block←observer+wire 2, repeater (QC) 2
- Phases (bursts of piston events): 3–13 (31 events, 11 pistons); 17–23 (10 events, 4 pistons); 27–27 (2 events, 2 pistons); 35–35 (1 events, 1 pistons); 40–68 (51 events, 17 pistons); 72–72 (1 events, 1 pistons); 80–82 (3 events, 1 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
  0    3    5    7    9   11   13   15   17   19   27   29   42   46
...  ...  ...  ...  ..~  ~.#  #.#  #.#  #~#  ###  #~#  ###  ###  ###
...  ...  ...  ...  ..~  ~.#  #.#  #.#  #.#  #.#  #~#  ###  ###  ###
...  ...  ...  ..~  ~.#  #.#  #~#  ###  ###  ###  ###  ###  ###  ##.
...  .~.  .#.  .#~  ~##  ###  #~#  ###  ###  ###  ###  ###  #.#  #..

 48   50   53   54   56   64   67   68   70   82
##.  .#.  .#.  .#.  ...  ...  .~.  .~.  .#.  ...
##.  .#.  .#.  .#.  .#.  .#.  .#.  ...  ...  ...
.#.  .#.  .#.  ...  ...  ...  ...  ...  ...  ...
...  ...  .~.  .~.  .#.  ...  ...  ...  ...  ...

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| east | 4 | 4 | 2×4 | east 1 (4) |
| west | 4 | 4 | 2×4 | west 1 (4) |
| below | 2 | 4 | 4×2 | down 2 (1), down 1, west 1 (1) |
| above | 2 | 4 | 4×2 | up 2 (1), up 1, east 1 (1) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| 2 5 -3 S | east | door | 9+2→spat, 46+2→pulled | block←observer+wire 2 |
| 2 6 -3 S | east | door | 9+2→spat, 46+2→pulled | wire 2 |
| 2 7 -3 S | east | door | 11+2→spat, 48+2→pulled | block←observer (QC) 2 |
| 2 8 -3 S | east | door | 11+2→spat, 48+2→pulled | block←observer 2 |
| 3 4 -3 S | east | door | 7+2→spat, 44+2→pulled | observer 2 |
| 5 2 -3 S | up | door | 13+8→pulled, 50+8→pulled | repeater 2 |
| 5 3 -3 S | up | door | 3+2→spat, 40+2→pulled, 61+3→pulled | block←observer 2, block←observer (QC) 1 |
| 5 4 -3 S | up | door | 53+1→pulled | block←observer 1 |
| 5 9 -3 S | down | door | 67+1→pulled | block←observer 1 |
| 5 10 -3 S | down | door | 17+2→spat, 54+2→pulled, 80+2→pulled | block←observer 3, repeater (QC) 2 |
| 5 11 -3 S | down | door | 27+8→pulled, 64+8→pulled | repeater 2 |
| 7 9 -3 S | west | door | 21+2→spat, 56+2→retracted, pulled at 60 | observer 1, wire (QC) 1 |
| 8 5 -3 S | west | door | 7+2→spat, 44+2→pulled | wire (QC) 2 |
| 8 6 -3 S | west | door | 7+2→spat, 44+2→pulled | wire 2 |
| 8 7 -3 S | west | door | 9+2→spat, 46+2→pulled | wire (QC) 2 |
| 8 8 -3 S | west | door | 9+2→spat, 46+2→pulled | wire 2 |
| 2 12 -3 S | west | power mover | 17+2→pulled, 54+2→spat | observer 2 |

<!-- end generated -->
