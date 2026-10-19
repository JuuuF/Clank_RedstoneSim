# piston door by Sydney600mc

World: `piston_doors/4x4 piston door by Sydney600mc.redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(Hand-written 2026-10-19 from the replay, `waves`, `why` and `inspect` on a copy in
`.sandbox/doors/explain/4x4-piston-door-sydney600mc/`, the saved ablation, input sweep
and symmetry results, and two gap replays (18 and 3, below). Every tick is from the
simulator; what is only inferred from the geometry says so. Not run on the game server.)

A 4x4 door in the plane x = 2 (cells y 4..7, z −3..0), built open, 16 iron door blocks,
24 pistons, in a 3 × 9 × 10 box (x 0..2, y 1..9, z −6..3; volume 270, 125 blocks above
the floor, 113 of them needed, [[../robustness]]): **three blocks deep**, the whole
mechanism and controller in the two layers behind the doorway plus the lever. The lever
(0 1 −2, on the back of the block 1 1 −2) is flipped at 1 and 31. The doorway is full
at **17** (16 ticks after the first flip; the last stack lands at 24) and empty at **57**
(26 after the second; at rest 59). The build is **mirror-symmetric about z = −1.5**:
every one of the 52 piston events of the north half (z ≤ −2) has a twin at z' = −3 − z in
the same tick (checked on the replay), so the text follows the north half. All eight
orientations replay identically ([[../symmetry]]).

**Piston layout and grouping: the same as Kwipla's.** The top row goes up (four sticky
pistons facing down at y = 9 spit the blocks from y 8 into y 7 and pull them back), the
bottom row down (four facing up at y = 2, from y 3), both with 2-tick pulses. The two
**middle rows leave sideways**, four blocks per side, and when the door is open all
four of a side rest in **one column at z = −4** (one cell out of the doorway): the two
inner blocks at their own level (2 5 −4, 2 6 −4) and the two outer blocks parked above
and below them (2 7 −4 and 2 4 −4, the corners' level). Behind the column, at z = −5,
two sticky **side pistons** face south (2 5 −5, 2 6 −5); behind those, at z = −6, two
more (2 5 −6, 2 6 −6) that push the side pistons one cell into the column and pull them
back: a double extender of sticky pistons (the "stack" role, [[../patterns]]), which gives
the inner cells (z −2) their reach of two. Two **parking pistons** serve the corner
cells of the column: 2 3 −4 (facing up) under it and 2 8 −4 (facing down) above it,
with the timer's hopper 2 9 −4 on top of the column (its second job below).

**Closing** (lever on at 1; the south half mirrors every step):

| tick | what happens |
|---|---|
| 1 | the lever powers its block 1 1 −2; the wires 1 2 −2 / 1 2 −1 on it and on 1 1 −1 feed two delay-1 repeaters, 1 2 −3 (north) and 1 2 0 (south). The powered blocks **lock the hoppers** 1 1 −3 and 1 1 0 beside them |
| 3 | repeater 1 2 −3 powers the block 1 2 −4: the plain piston 1 3 −4 on it extends north (it moves nothing: its head at 1 3 −5 is a signal), and the delay-2 repeater 1 2 −5 starts. Observer 1 1 −4, watching the locked hopper, fires (3–4) and its output locks the next hopper, 1 1 −5 |
| 5 | observer 1 4 −5 (watching the head's cell) fires up into the wool 1 5 −5 and the wire 1 6 −5 on it: the two side pistons **spit** the inner blocks from z −4 to −3 (extend 5, dropped at 7). Observer 2 1 −5 (watching hopper 1 1 −5) fires |
| 7 | repeater 1 2 −5 powers the block 1 2 −6: the **power mover** 2 2 −6 lifts the observer 2 3 −6 to 2 4 −6 (it lands at 9 and pulses at 11 into 2 4 −5, which is an observer: the pulse changes nothing, `effects`). Observer 1 7 −5 (watching the wire 1 6 −5) fires up into the block 1 8 −5, the input of repeater 1 8 −4 (delay 1). Observer 2 1 −4 fires |
| 9 | three 2-tick pulses in one tick: (a) the repeater powers 1 8 −3 and the **wire 1 9 −3** on it spits the top row down (2 9 z), triggers the dropper 1 9 −4 and quasi-powers the parking piston 2 8 −4 through that dropper (a conductor: the piston's cell above is the hopper, whose neighbor the dropper is), which spits the upper outer block from 2 7 −4 down into 2 6 −4; (b) observer 2 2 −5, which saw the power mover extend at 7, powers the **obsidian 2 2 −4**: parking piston 2 3 −4 spits the lower outer block from 2 4 −4 up into 2 5 −4 and the corner piston 2 2 −3 spits its bottom block up; (c) observer 2 1 −3, the last of the hopper chain, powers the block 2 1 −2 under the bottom piston 2 2 −2 (2 2 −1 from 2 1 −1 and the south chain). The top and bottom rows are closed from 11; the outer side blocks now sit in the column's middle cells |
| 13 | the dropper 1 9 −4 drops its one wool item into the hopper 2 9 −4 (4 ticks after the trigger) |
| 15 | comparator 2 9 −5 reads the item (signal 1) into the block 2 9 −6; the wire 2 8 −6 on the dropper 2 7 −6 carries it down: the **stack pistons** 2 6 −6 (directly, through the dropper) and 2 5 −6 (quasi-connectivity, the dropper is a neighbor of its cell above) each push three blocks: the side piston from z −5 to −4, the outer block from −4 to −3 and the inner block from −3 to −2. **Closed at 17** |
| 20–22 | the hopper hands the item back to the dropper (20); the comparator goes off at 22 and the stacks retract, pulling the side pistons back to z −5 (they land at 24, the mechanism at rest). The dropper 2 7 −6's `triggered` flag went on at 15 and off at 22; observer 2 7 −5 watching it pulses at 17 and 24 into the parking cell 2 7 −4, which is empty now: nothing |

**Opening** (lever off at 31):

| tick | what happens |
|---|---|
| 33 | repeater 1 2 −3 off: the plain piston retracts (head removed at 33 → observer 1 4 −5 at 35); the hopper 1 1 −3 unlocks → observer 1 1 −4 at 33 → 2 1 −5 at 35 → 2 1 −4 at 37 → 2 1 −3 at 39 |
| 35 | the side pistons extend into the empty z −4 cells and at 37 **pull the outer blocks** from −3 back to −4 |
| 37 | repeater 1 2 −5 off: the power mover retracts and lowers the observer back to 2 3 −6 (lands 39, pulses 41 into the delay-3 repeater 2 3 −5, which is on 47–52: a 2-tick input stretched to the repeater's own delay). Observer 1 7 −5 (the wire 1 6 −5 off) → repeater 1 8 −4 → 39 |
| 39–41 | the wire 1 9 −3 again: the top row pistons extend into y 8 and pull their blocks up at 41; the dropper is triggered (item at 43); 2 8 −4 extends into 2 7 −4 and pulls the upper outer block up into its parking cell at 41. Observer 2 2 −5 (the power mover retracted at 37) → obsidian: 2 3 −4 extends into 2 4 −4 and pulls the lower outer block down at 41, 2 2 −3 pulls the corner block down; the hopper chain's 2 1 −3 → bottom pistons pull at 41. Top row, bottom row and the outer side blocks are home at 43 |
| 45 | the comparator is on again (45–51): the stacks push the side pistons to z −4 (they land at 47) |
| 47–49 | observer 2 7 −5 (the dropper 2 7 −6 triggered at 45) pulses 47–48 into the **parked outer block 2 7 −4**, which powers the moved side piston 2 6 −4 under it directly and 2 5 −4 by quasi-connectivity (2 7 −4 is a neighbor of 2 6 −4, the cell above 2 5 −4): both extend at 48, the tick after landing, and at 49 **pull the inner blocks** from −2 to −3 |
| 52 | the hopper returns the item (50), the comparator goes off (52): the stacks retract and pull the side pistons back to z −5 (they land at 54); the dropper untriggers, so observer 2 7 −5 pulses again at 54–55 |
| 55 | 2 6 −5 extends: quasi-connectivity through the parked block 2 7 −4 (its cell above is the observer 2 7 −5, whose neighbor the block is). 2 5 −5 extends too, from a different path: observer 2 4 −5 under it saw the repeater 2 3 −5 turn off at 53. Two chains, one tick. At 57 both **pull the inner blocks** from −3 into −4. **Open at 57**; everything at rest at 59 |

**How the pistons are powered** (the facts table): nothing but the lever is a level,
and it holds only four pistons that move no door block: the two plain pistons (heads as
signals, 3–33) and the two power movers (7–37). Every mechanism piston gets 2-tick
pulses from observers (through a wool, a wire on a wool, an obsidian, a dropper or the
parked iron block) or the 7-tick pulse of the item timer. Quasi-connectivity is used four
times per side and saves a conductor each time: 2 8 −4 through the dropper 1 9 −4, the
lower stack 2 5 −6 through the dropper 2 7 −6, 2 5 −4 and (at 55) 2 6 −5 through the
parked block. Three blocks do two jobs: the dropper 1 9 −4 is the timer's launcher and
the conductor above 2 8 −4; the dropper 2 7 −6 conducts the comparator's signal to the
stacks *and* its `triggered` flag, which follows that signal, is what observer 2 7 −5
watches (a dispenser as a block-update relay); and the parked outer block 2 7 −4 is a
conductor only while it is parked, i.e. only during the opening ("carried power",
[[../patterns]]): the same observer pulses go into air at 17 and 24.

**The hopper chain.** A hopper locks (`enabled` false) the moment a neighbor powers it,
with no delay, and unlocks the same way; an observer watching it turns either edge into
a 2-tick pulse. Sydney chains four of them per side at y = 1 (hopper 1 1 −3 locked by
the lever's block → observer 1 1 −4 → hopper 1 1 −5 → observer 2 1 −5 → observer 2 1 −4
→ observer 2 1 −3 → the bottom pistons' block): 8 ticks from the lever to the bottom
row, on both edges, with hoppers where a solid block could not be watched. The hoppers
hold no items (`inspect`).

**The item timer.** The dropper 1 9 −4 holds one wool item and faces the hopper 2 9 −4,
which faces back into the dropper. A 2-tick pulse on the wire beside the dropper (9 and
39) makes it drop the item into the hopper 4 ticks later (13, 43); the comparator
2 9 −5 reads the hopper (one item: signal 1) 2 ticks after that (15, 45); the hopper
pushes the item back into the dropper 7 ticks after receiving it (20, 50) and the
comparator goes off 2 ticks later (22, 52). So a 2-tick trigger becomes a **7-tick
pulse, 6 ticks later**, from one item that shuttles and is in place for the next cycle
(the two-cycle test runs this door identically twice, [[../robustness]]); it is the
stacks' pulse in both directions. The signal is 1: the wire 2 8 −6 carries exactly one
step to the dropper below it and powers nothing else.

**Mechanics as logic.** The repeater 2 3 −5 exists for the observer 2 4 −5 that watches
it (its off edge at 53 fires 2 5 −5 at 55), but its output also goes straight into the
parking piston 2 3 −4 beside it, for all of 47–52. A push is impossible there: the
column above holds the parked block, the two moved side pistons, the other parked block
and the parking piston 2 8 −4, and ends in the **hopper 2 9 −4**, a block entity that
cannot be moved (`power.piston_decision` at 47–51: powered, blocked). At 52 the stacks
pull the side pistons out of the column and a push would resolve (the decision is
"extend"), but nothing updates the piston in that tick; the repeater goes off at 53 and
the update it then sends finds it unpowered. The replay has no event of 2 3 −4 between
41 and the end. So the hopper caps the column like Kwipla's furnace, and the update
order covers the last tick; that the column would be lifted without the cap is inferred
from the resolver, not run (the hopper is also the timer, so there is no clean
counterfactual).

**Controller.** No memory, no clock: a lever door that uses **both edges of one level**.
Per half, the level drives one plain piston and one power mover; ten observers turn
the edges into pulses, two hoppers make a solid-block chain watchable, the item timer
makes the one long pulse, and four repeaters set the delays: delay 1 at the lever
(1 2 −3) and before the top row (1 8 −4), delay 2 for the power mover (1 2 −5), delay 3
for the opening's last pull (2 3 −5). The power mover is an **off-edge detector**: the
observer it carries pulses after both landings, but only the landing at 39 has a
listener (the repeater), so one lifted observer gives the opening a pulse 10 ticks
after the flip and the closing nothing. Every delay is exact: 20 of the 24 repeater
delay changes break the door and the other 4 only shift its timing (the two lead
repeaters at delay 2, the two power-mover repeaters at delay 3); every one of the 120
piston turns breaks it, and so does removing any observer, repeater, wire, hopper,
dropper or comparator. The only slack is 12 iron blocks of the wall at x = 1 beside the
storage cells (removal inert; the trim keeps 113 of 125 blocks in the same box).

**Contract** ([[../mechanism]]): 48 pulses on the 20 mechanism pistons (the four side
pistons work from two cells each, 24 entries), and the stripped door moves its doorway
identically. There is no tick with a retract before an extend: every stage is all
pushes (5, 9, 15, 35, 39, 45, 48, 55) or all pulls (22, 37, 41, 49, 52, 57), and pistons
that act in the same tick never share a block, so the contract is a plain pulse schedule
and any controller that keeps these pulse times, in any component order, runs this door.

**Input** ([[../robustness]]): safe gap 19 ticks, no-overlap gap 22, the designed 30;
gaps 1–18 leave the doorway wrong, and one more flip repairs only gaps 6 and 8–11.
The binding constraint, read from the gap-18 replay (second flip at 19): the opening's
first move is the side pistons' 2-tick pulse 4 ticks after the flip (observer 1 4 −5),
and the side pistons are still being pulled back by the stacks (retract 22, land 24).
With the flip at 19 the pulse is on 23–24; the pistons land at 24, are updated and
queue, and their event at 25 finds the pulse over: all four extensions are lost
("unpowered"), the outer blocks are never pulled out and 12 blocks end wrong. With the
flip at 20 the pulse (24–25) still holds at 25. **The second flip must not come before
the stacks' return is one tick from landing** (gap ≥ 19); the no-overlap gap waits for
the landing itself. At the other end (gap 3, 12 iron blocks left in the doorway, D10)
no extension fails at all: the opening edge is **swallowed by observers that are still
in their closing pulse**. An observer ignores a change while it is powered or has its
tick pending (`ObserverBlock.updateShape`), so each one passes at most one edge per
4 ticks: 1 4 −5 fires at 5 and misses the head removed at 6, 1 1 −4 fires at 3 and
misses the hopper unlocked at 4, and 1 7 −5 sees only the closing pulse of its wire.
No opening pulse ever reaches the side pistons, the top row, the upper parking pistons
or the inner bottom pistons. The stacks still run at 15 (the dropper was triggered at
9): the y 6 stack pushes its row in; the y 5 stack moves only its piston, because the
lower parking piston 2 3 −4 (observer 2 2 −5 does fire twice, at 9 and 13: the power
mover retracts at 11, after that observer has gone off) is pulling the outer block away
in the same tick, and the inner block stays at −3. The blocks left behind are the two
inner bottom blocks (2 4 −2, 2 4 −1), the whole
top row, the whole y 6 row and the outer cells of y 5 (2 5 −3, 2 5 0): exactly the
groups whose edge was lost. Later flips do not bring them back ([[../robustness]];
why the next edges do not is not traced here).

**Compared with Kwipla's 4x4** ([[4x4-piston-door-kwipla]], numbers from [[../metrics]]).
The same mechanism: same grouping, the same column storage with the outer blocks parked
above and below the inner ones, the same double extender giving the inner cells their
reach, the same vertical parking pistons, and the same trick of an immovable block
capping the column (a hopper here, a furnace there). The differences are the controller
and the depth. Kwipla's door is a button door with a one-bit memory (a redstone block
toggled by a sticky piston) whose level and edges drive observer chains with two delay-4
repeaters as the long waits; Sydney's is a lever door with no memory, whose two edges
drive observer chains, a hopper chain and an item timer. Kwipla's sequence lifts the
bottom row first (10), spits the inner side blocks at 14, parks the outer ones at 18–20
and runs the extender as a push at 26 and a pull-back at 34; Sydney's spits the sides
first (5), rows and parking together at 9, and the stack push at 15 lands everything at
once, so it closes in 16 ticks against 27 and opens in 26 against 39 (the opening is
the longer direction in both, because the inner blocks need two pulls with the stack
between them). Sydney's build is three blocks deep (box 270 against 1080, 125 blocks
against 158, 24 pistons against 28, 38 logic blocks against 57) and dominates Kwipla's on
every measured goal, the input window included (safe gap 19 against 25 ticks; both need
a user who waits). What Kwipla's gives in return is a button on both sides of the wall,
where a lever has to be reached from one side; the price is the memory, which is one
press behind after an ignored press, while a lever door can never be out of step with
its input ([[4x4-piston-door-kwipla]]). Which of the two orders of the same moves is
forced by the mechanism is not analyzed.

**Lessons.** (1) **One level, both edges**: a lever door needs no memory if every
action is an observer pulse off the on edge or the off edge; the direction is in which
observers listen, and a lifted observer that only has a listener after its second
landing is an off-edge detector. (2) **Blocks whose state follows power are relays**: a
hopper (locked), a dropper (triggered) and a piston head change on the tick and can be
watched, so an observer chain can pass through them where a solid block would be
invisible; the dropper even conducts the signal it relays. (3) **An item can be a
timer**: one item shuttling between a dropper and a hopper turns a 2-tick trigger into a
7-tick pulse 6 ticks later, reset by itself; the comparator's signal of 1 is enough for
one wire step. (4) **A parked door block can carry power**: the outer block's parking
cell is also the conductor that fires the moved side pistons, so the same observer pulse
is a command in one direction and nothing in the other. (5) **Mechanics as logic**, as in
Kwipla's door: the hopper that caps the column vetoes a push the wiring makes at the
wrong time, and the update order covers the one tick it could not. (6) **Observers swallow
edges that come within 4 ticks**: that is why a quick second flip loses whole groups of
moves without any extension failing, and why the safe gap is a property of the controller,
not only of the mechanism.

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 4×4 in the plane x = 2; 0 more output cells outside it.
- Timeline: use lever at 1, use lever at 31; markers Closing 1, Closed 30, Opening 31, Opened 60
- Reference states: closed at tick 30, open at tick 60. Fully closed at ticks 17-36; fully open at 0-4, 57-71.
- Pistons by role: door 24, fires, moves nothing 2, power mover 2
- How extensions were powered (block giving the signal; QC = through the block above the piston): block←observer 14, dropper (QC) 8, wire 8, block←repeater 4, block←observer+wire 4, dropper 4, block←observer (QC) 4, block←wire 4, observer 2
- Phases (bursts of piston events): 3–11 (52 events, 20 pistons); 15–15 (4 events, 4 pistons); 22–22 (4 events, 4 pistons); 33–41 (52 events, 20 pistons); 45–57 (32 events, 12 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
   0     5     7     9    11    15    17    37    41    48    49    51
....  ....  ....  ~~~~  ####  ####  ####  ####  ....  ....  ....  ....
....  ~..~  #..#  #..#  #..#  ~~~~  ####  .##.  .##.  ~##~  ~..~  #..#
....  ~..~  #..#  #..#  #..#  ~~~~  ####  .##.  .##.  ~##~  ~..~  #..#
....  ....  ....  ~~~~  ####  ####  ####  ####  ....  ....  ....  ....

  57
....
....
....
....

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| north | 4 | 8 | 4×4 | north 2 (2), down 1, north 1 (1), up 1, north 1 (1) |
| south | 4 | 8 | 4×4 | south 2 (2), down 1, south 1 (1), up 1, south 1 (1) |
| above | 4 | 4 | 2×4 | up 1 (4) |
| below | 4 | 4 | 2×4 | down 1 (4) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| 2 2 -3 S | up | door | 9+2→spat, 39+2→pulled | block←observer 2 |
| 2 2 -2 S | up | door | 9+2→spat, 39+2→pulled | block←observer 2 |
| 2 2 -1 S | up | door | 9+2→spat, 39+2→pulled | block←observer 2 |
| 2 2 0 S | up | door | 9+2→spat, 39+2→pulled | block←observer 2 |
| 2 3 -4 S | up | door | 9+2→spat, 39+2→pulled | block←observer 2 |
| 2 3 1 S | up | door | 9+2→spat, 39+2→pulled | block←observer 2 |
| 2 5 -6 S | south | door | 15+7→pulled, 45+7→pulled | dropper (QC) 2 |
| 2 5 -5 S | south | door | 5+2→spat, 35+2→pulled, 55+2→pulled | block←observer+wire 2, observer 1 |
| 2 5 -4 S | south | door | 48+1→pulled | block←observer (QC) 1 |
| 2 5 1 S | north | door | 48+1→pulled | block←observer (QC) 1 |
| 2 5 2 S | north | door | 5+2→spat, 35+2→pulled, 55+2→pulled | block←observer+wire 2, observer 1 |
| 2 5 3 S | north | door | 15+7→pulled, 45+7→pulled | dropper (QC) 2 |
| 2 6 -6 S | south | door | 15+7→pulled, 45+7→pulled | dropper 2 |
| 2 6 -5 S | south | door | 5+2→spat, 35+2→pulled, 55+2→pulled | wire 2, block←observer (QC) 1 |
| 2 6 -4 S | south | door | 48+1→pulled | block←observer 1 |
| 2 6 1 S | north | door | 48+1→pulled | block←observer 1 |
| 2 6 2 S | north | door | 5+2→spat, 35+2→pulled, 55+2→pulled | wire 2, block←observer (QC) 1 |
| 2 6 3 S | north | door | 15+7→pulled, 45+7→pulled | dropper 2 |
| 2 8 -4 S | down | door | 9+2→spat, 39+2→pulled | dropper (QC) 2 |
| 2 8 1 S | down | door | 9+2→spat, 39+2→pulled | dropper (QC) 2 |
| 2 9 -3 S | down | door | 9+2→spat, 39+2→pulled | wire 2 |
| 2 9 -2 S | down | door | 9+2→spat, 39+2→pulled | block←wire 2 |
| 2 9 -1 S | down | door | 9+2→spat, 39+2→pulled | block←wire 2 |
| 2 9 0 S | down | door | 9+2→spat, 39+2→pulled | wire 2 |
| 1 3 -4 | north | fires, moves nothing | 3+30→retracted | block←repeater 1 |
| 1 3 1 | south | fires, moves nothing | 3+30→retracted | block←repeater 1 |
| 2 2 -6 S | up | power mover | 7+30→pulled | block←repeater 1 |
| 2 2 3 S | up | power mover | 7+30→pulled | block←repeater 1 |

<!-- end generated -->
