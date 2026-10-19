# piston door by Rubik

World: `piston_doors/3x3 piston door by Rubik.redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(Hand-written 2026-10-19 from the replay's piston events, `waves`, `why` traces and the
saved ablation, input sweep and mechanism results; two one-change experiments on copies
in `.sandbox/doors/explain/3x3-piston-door-rubik/` (A, B below; README there). Every
tick is the simulator's; what is only inferred from the geometry says so. Not run on the
game server. The build sits on an imported superflat: the ground is grass at y −61, the
door floats above it.)

**The whole door is one vertical plane, like SacredRedstone's.** Every block is at
z = −4; only the lever sticks out (−10 −58 −3, on the south face of a note block). Box
9×10×2 = 180, 61 blocks above the ground, 10 sticky pistons (the generated table lists
11 because the upper stack piston also fires from the cell it is lifted to), 7
observers, 2 repeaters, 2 note blocks, 12 wire, 27 conducting blocks. The doorway is
x −10..−8, y −54..−52; the frame around it holds every door block one cell out, and the
controller runs around the outside of that: a closed loop of observers and wire that
starts at the lever's note block (bottom left) and goes along the bottom, up the right,
over the top and down the left. Direction-independent: all eight orientations replay
identically ([[../symmetry]]). Lever on at 1 → closed at 15 (14 ticks); lever off at 26
→ open at 52 (26 ticks).

**Piston layout (geometry).** Seven of the nine door blocks are **singles**, each
pushed in and pulled out by one sticky piston two cells from the doorway: the west
column (top, middle, bottom left) by the three east-facing pistons stacked at x −12 (the
blocks rest at x −11); the top middle and top right by two down-facing pistons at y −50
(blocks at y −51); the middle and bottom right by two west-facing pistons at x −6
(blocks at x −7). The **center and the bottom middle** are the hard cells of a flush
3x3 and get Mumbo Jumbo's solution ([[3x3-piston-door-mumbo-jumbo]]): a **double
extender** under the center column (−9 −57 and −9 −56, both facing up) with the center
block, a diamond block, resting on it at −9 −55, and a **slider** (−7 −55, facing west)
that pushes the bottom-middle block, a quartz block stored at −8 −55, under the center
block. Groups: west 3, above 2, east 2, below 2 (generated table).

**Controller: one pulse train for both directions.** The lever stands on a note block
(−10 −58). An observer cannot see power, but it sees a note block's `powered` state
change, and it fires on *both* edges, so every lever flip, on or off, starts the same
2-tick pulses (`waves`: observer −10 −57 on 3–4 and 28–29). Two chains leave the note
block:

- **West chain.** The observer above it (−10 −57, output up) powers the quartz −10 −56
  for 2 ticks. That block feeds the upper stack piston (−9 −56) directly and the delay-1
  repeater −11 −56, which 2 ticks later powers −12 −56; the wire on it climbs to
  −13 −54 and powers the bottom-left piston (−12 −54) at 5. The observer −13 −53
  watching that wire fires at 7: its block −13 −52 carries a wire over the top of the
  door (−13 −51 → −12 −50 → −11 −49 → −10 −49). On the way it powers −12 −51, which
  drives the top-left piston directly and the middle-left one by quasi-connectivity
  (the cell above −12 −53 is the top-left piston; −12 −51 is next to it), and −10 −50,
  which drives the top-middle piston.
- **East chain.** The observer beside the note block (−9 −58, output east) feeds a
  second observer (−8 −58), which powers −7 −58 at 5; the wire −7 −57 on it is the
  branch point. Westward it is the input of the delay-4 repeater −8 −57, whose output
  is the lower stack piston (−9 −57). Upward, the observer −7 −56 watching the wire
  fires at 7 straight into the slider above it (−7 −55). Eastward the wire climbs
  (−6 −56 → −5 −55) to the observer −5 −54, which fires at 7 into the second note block
  (−5 −53); the wire on that note block (−5 −52 → −6 −51) powers −6 −52, which drives
  the middle-right piston directly and the bottom-right one by quasi-connectivity, and
  −7 −50, which drives the top-right piston. (A note block was chosen where any
  conductor would do, so the door sounds; inferred from the block, the simulator does
  not record sounds.)
- **The one timer.** The delay-4 repeater gets a 2-tick input (5–6) and outputs **8
  ticks** (13–20): a repeater stretches any pulse shorter than its delay to its delay
  (it turns on at 13 and, finding its input already off, schedules its own off 8 ticks
  later). The observer −8 −56 watches that repeater and pulses 2 ticks after each of
  its edges (15–16, 23–24, 40–41, 48–49) into the cell −8 −55 above it: the storage
  cell of the bottom-middle block.

**Closing** (lever on at 1):

| tick | what happens |
|---|---|
| 3 | the upper stack piston (−9 −56) pushes the diamond block up one (−9 −55 → −9 −54: the bottom-middle cell); the pulse ends at 5 and the piston **spits** it (drop event, the head comes back) |
| 5 | the bottom-left piston pushes its block in (−11 −54 → −10 −54), spat at 7 |
| 7 | the six other singles push their blocks in (top left, middle left, top middle, top right, middle right, bottom right), and the slider pushes the quartz under the diamond (−8 −55 → −9 −55); all seven are spat at 9. From 9 every cell but the center is solid |
| 13 | the repeater turns on: the lower stack piston (−9 −57) pushes the column up one: the upper piston to −9 −55, the quartz into the bottom-middle cell, the diamond into the center. **Closed at 15** |
| 21 | the repeater turns off: the stack retracts and pulls the upper piston back down to −9 −56 (landed 23); the door blocks stay (a retracted sticky piston carries nothing when it is pulled). The observer −8 −56's pulses at 15 and 23 go into the empty cell −8 −55 and do nothing |

**Opening** (lever off at 26): the same pulses, read by a mechanism in the other state:

| tick | what happens |
|---|---|
| 28 | the upper stack piston extends into the empty cell −9 −55; the pulse ends and at **30** it retracts, pulling the quartz from the bottom-middle cell down to −9 −55 |
| 30 | the bottom-left piston extends into its empty storage cell and at 32 pulls its block out |
| 32 | the six other singles do the same (pulled at 34); the slider extends and at 34 pulls the quartz east, back to −8 −55 (landed 36). Only the center is left |
| 38 | the repeater turns on (38–45): the stack lifts the upper piston to −9 −55 (landed 40) |
| 41 | the observer −8 −56 fires (40–41) into the quartz −8 −55, now back in its cell: the quartz conducts the pulse to the lifted piston beside it, which extends into the empty bottom-middle cell and at **42**, when the pulse ends, pulls the diamond down one (landed 44) |
| 46 | the repeater turns off: the stack lowers the upper piston to −9 −56 (landed 48); the diamond stays at −9 −54 |
| 49 | the observer fires again (48–49) into −8 −55; this time the piston at −9 −56 reads it by **quasi-connectivity** (the cell above it is −9 −55, empty, next to the powered quartz), extends into −9 −55 and at **52** pulls the diamond home to −9 −55. **Open at 52** |

The retraction at 52 is worth a look (`why`): the quasi-connected piston gets no update
when the observer turns off at 50; the update that makes it notice is its **own head
landing** at 51, and the retract is queued then. Had the head taken longer, the diamond
would have stayed up.

**What the counterfactuals say.** All 10 pistons, all 7 observers, both repeaters, both
note blocks, the lever and all 12 wire matter (removal breaks the door); every piston
turn breaks it; 5 quartz blocks are slack (trim 61 → 56: two under the west part of the
doorway, two above the top-left storage, one beside the top right). Glass instead of a
conductor breaks the door in 5 places: the four blocks that carry an observer's or
repeater's output into wire or a piston (−7 −58, −12 −56, −10 −56, −13 −52) and **the
bottom-middle door block itself** (−8 −55): in its storage cell it is the conductor
through which the observer −8 −56 reaches the lifted piston (41) and the home piston
(49). A door block is part of the controller. Both repeater delays are exact (every other
delay breaks the door, ablation); the experiments say why:

- **A** (stack repeater at delay 3, 6 ticks): closing still works (the push comes at 11
  instead of 13), but on opening the stack's pull at 42 meets the lifted piston still
  retracting from its own pull at 40, takes nothing (R-026), and at 44 the stranded
  piston pushes the diamond back into the center and spits it. The 8 ticks are the time
  the lifted piston needs for its 1-tick pull plus its landing before the stack may take
  it down (41 extend, 42 pull, 44 landed, 46 pulled down).
- **B** (west repeater at delay 2, 4 ticks): a 2-tick observer pulse through a delay-2
  repeater comes out 4 ticks long, so the bottom-left piston finishes its push and
  pulls the block back at 11 instead of spitting it, and the observer watching that wire
  now fires on both edges (9 and 13) and pushes the west column twice. Delay 1 (2
  ticks) is the one setting that passes the observer's pulse unchanged.

**The stripped door and the same-tick order** ([[../mechanism]], D4). Driven by its
contract as editor pulses, the mechanism alone differs from tick 9: the three
west pistons stand in a column, and an editor pulse on the middle-left one (7–9) powers
the position its lower neighbor's quasi-connectivity asks from, so the bottom-left
piston, whose own pulse ends at 7, stays powered until 9, completes its push instead of
spitting and then retracts, pulling its block out (verified by replaying the stripped
world: a pull at 9). In the real door the bottom-left piston's power is the wire
−13 −54 and nothing powers the cell above it; stacked singles must be driven from the
side, not from a pulse at the piston above. The two "retract, then extend" ticks (7
and 32) are the bottom-left piston's spit (respectively its pull) running before the six
other singles' events: its power ends in the repeater's scheduled tick, which runs with
very high priority before the observers' ticks that start the others. The two sets touch
different cells, so the order is not what the stripped door trips over (inferred from
the cells; not tested separately).

**Input contract** ([[../robustness]]): the second flip must come at least 20 ticks after
the first (safe gap 20, no-overlap gap 21). At gap 19 the stack's pull at 21 lands the
upper piston at 23, the opening pulse (flip + 2 and + 3) is still on when it lands, the
landed piston queues its extension, and at 24 both it and the stack (quasi-powered by
the same block) find the pulse gone and move nothing: two lost extensions, the quartz
never comes down. At gap 20 the pulse lasts one tick longer: the upper piston extends
at 24 first and the stack's extension, queued behind it, fails harmlessly on the
extended piston (R-027).

**Lessons.** (1) **One pulse train for both directions**: observers on a note block
turn each lever edge into the same 2-tick pulses, and every single answers a 2-tick
pulse by spitting its block in when the cell is empty and pulling it out when it is
full ([[../patterns]] "Spits"; Lutal's vault does the same). (2) The flush 3x3's center
and bottom middle: a **double extender** under the center with a sideways slider, as in
Mumbo Jumbo's door; the stack's hold time comes from **pulse stretching** (a delay-4
repeater makes 8 ticks from 2), which is exact because the lifted piston must finish
its own pull and land before the stack lowers it (R-026). (3) **A door block can be a
conductor of the controller**: the bottom-middle block in its storage cell relays the
observer to the lifted piston and, by quasi-connectivity, to the piston at home.
(4) **Quasi-connected power ends silently**: the piston only notices when something
updates it; here its own head landing is that update, two ticks after the pulse.

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 3×3 in the plane z = -4; 0 more output cells outside it.
- Timeline: use lever at 1, use lever at 26; markers Closing 1, Closed 25, Opening 26, Opened 54
- Reference states: closed at tick 25, open at tick 54. Fully closed at ticks 15-29; fully open at 0-2, 52-68.
- Pistons by role: door 11
- How extensions were powered (block giving the signal; QC = through the block above the piston): block←wire 6, wire 4, block←wire (QC) 4, block←observer 3, repeater 2, observer 2, block←observer (QC) 1
- Phases (bursts of piston events): 3–9 (27 events, 9 pistons); 13–13 (1 events, 1 pistons); 21–21 (1 events, 1 pistons); 28–34 (27 events, 9 pistons); 38–42 (4 events, 2 pistons); 46–52 (3 events, 2 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
  0    3    5    7    9   13   15   30   32   34   41   42   44   52
...  ...  ...  ~~~  ###  ###  ###  ###  ###  ...  ...  ...  ...  ...
...  ...  ...  ~.~  #.#  #~#  ###  ###  ###  .#.  .#.  ...  ...  ...
...  .~.  ~#.  ##~  ###  #~#  ###  #.#  ..#  ...  .~.  .~.  .#.  ...

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| west | 3 | 3 | 2×3 | west 1 (3) |
| below | 2 | 4 | 4×2 | down 2 (1), down 1, east 1 (1) |
| above | 2 | 2 | 2×2 | up 1 (2) |
| east | 2 | 2 | 2×2 | east 1 (2) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| -12 -54 -4 S | east | door | 5+2→spat, 30+2→pulled | wire 2 |
| -12 -53 -4 S | east | door | 7+2→spat, 32+2→pulled | block←wire (QC) 2 |
| -12 -52 -4 S | east | door | 7+2→spat, 32+2→pulled | block←wire 2 |
| -9 -57 -4 S | up | door | 13+8→pulled, 38+8→pulled | repeater 2 |
| -9 -56 -4 S | up | door | 3+2→spat, 28+2→pulled, 49+3→pulled | block←observer 2, block←observer (QC) 1 |
| -9 -55 -4 S | up | door | 41+1→pulled | block←observer 1 |
| -9 -50 -4 S | down | door | 7+2→spat, 32+2→pulled | block←wire 2 |
| -8 -50 -4 S | down | door | 7+2→spat, 32+2→pulled | wire 2 |
| -7 -55 -4 S | west | door | 7+2→spat, 32+2→pulled | observer 2 |
| -6 -54 -4 S | west | door | 7+2→spat, 32+2→pulled | block←wire (QC) 2 |
| -6 -53 -4 S | west | door | 7+2→spat, 32+2→pulled | block←wire 2 |

<!-- end generated -->
