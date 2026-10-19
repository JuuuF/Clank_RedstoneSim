# Flush Enchanting Table Door by Purplers

World: `other_piston_contraptions/3x3 Flush Enchanting Table Door by Purplers.redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(Hand-written 2026-10-19 from the replay's piston events, `why` traces, the turn-on ticks
of every component and three one-change experiments on copies in
`.sandbox/doors/explain/3x3-flush-enchanting-table-door-purplers/` (A–C below, README
there); [[../robustness]], [[../metrics]], [[../mechanism]]. Every tick is from the
simulator; what is only inferred from geometry or from the game's rules says so. Not
run on the game server: `run_world` has no exact stand-in for a button on a dropper
(EXP-074), and the item loop needs the game (below).)

A flush 3x3 door of **bookshelves** in the plane z = −4 (cells x −3..−1, y 5..7), built
open, in front of a two-deep enchanting room (z −3..−2, floor y 4, back wall z = −1)
with an **enchanting table at −2 5 −3**, right behind the bottom-center cell. An oak
button on the dropper 1 2 −3 is the input: pressed at 1 the doorway is full at 37, pressed
at 63 it is empty at 119 (36 / 56 ticks; at rest 59 / 121). 27 sticky pistons, 220
blocks above the floor in a 6 × 10 × 6 box (172 of them needed, [[../metrics]]); all
eight orientations replay identically ([[../symmetry]]). The three columns x = −3, −2,
−1 are built alike and move alike (the center column leads by two ticks at the start,
below), so the text follows one column, `x`.

**The table and the storage (geometry).** An enchanting table is a block entity: no
piston can move it, and nothing may pass through its cell. Purplers never moves it:
**the door hides as floor and wall around it.**

- The **bottom row** (y 5) rests at x 4 −3: one cell down and one cell south, in the
  room's floor, *under the table* for the center column. It gets there by a sideways
  push at floor level and comes back the same way, so the table only ever sees a block
  arriving under it or leaving (while the door is closed the table stands over air:
  −2 4 −3 is empty at tick 62).
- The **middle row** (y 6) rests at x 4 −4, two cells down, in the floor under the
  doorway itself.
- The **top row** (y 7) rests at x 7 −1: three cells south, where it is the top row of
  the room's back wall (bookshelves at x 5..7 −1 when open; while the door is closed
  that row of the wall is missing).

Experiment C (the table removed): inert, every block as in the original at every tick.
The table is what the door is built around, not a part it reads. The ablation says the
same: 37 of the 56 bookshelves are slack (their removal changes nothing); the 19 whose
removal breaks the door are the 9 of the door and the 10 that carry power
([[../robustness]]).

**Piston layout.** Per column, seven sticky pistons in three groups; the other six (the
"power mover", "power switch" and idle ones of the facts table) are the controller's:

- **Under the doorway**: a vertical double extender, the stack x 2 −4 (up) under the
  door piston x 3 −4 (up), both below the middle block's rest cell x 4 −4. The door
  piston pushes from y 3 (one cell: x 4 → 5) and, lifted to y 4 by the stack, from
  there (x 5 → 6): the two-cell lift of the middle block, done as two one-cell spits.
- **Behind the table**: a second vertical double extender, the stack x 2 −2 under the
  piston x 3 −2 (facing north). Lifted to y 4 it stands behind the bottom block's rest
  cell x 4 −3 and pushes it north under the doorway (x 4 −3 → x 4 −4) or pulls it
  back. Its cell at y 4 is the room's floor: the switch piston x 4 0 (north, extended
  at rest, head at x 4 −1) holds a floor bookshelf at x 4 −2 and pulls it out of the way
  to x 4 −1 before the lift; the pulled bookshelf is also the lifted piston's power block
  (that is why the facts call x 4 0 a "power switch"). Three obsidian blocks x 3 −3
  separate the two extenders (their job in "Mechanics as logic").
- **Above the back wall**: the pusher x 7 0 (north, at the end of the top row's rest
  cell), a **carried piston** parked at x 8 −1 (north, above the rest cell) and the
  stack x 9 −1 (down) that lowers it into the row and lifts it out again. The pusher
  reaches one cell; the top block must travel three (x 7 −1 → −4). So the parked
  piston is lowered into the row behind the block, pushed along with it, fires once
  from the middle of the row, and is pulled back and lifted away: the same idea as the
  carried pistons of Purplers' sliding door ([[4x4-sliding-piston-door-purplers]]).

**Closing** (press at 1; an oak button stays pressed 30 ticks and releases at 31):

| tick | what happens |
|---|---|
| 1 | the button powers the upper dropper 1 2 −3 (both droppers are *triggered*: the lower one, 1 1 −3, by quasi-connectivity through the upper's cell); the wires 0 2 −3 / −1 2 −3 on the dropper's west side light and power the note block −2 1 −3 (through the block −1 1 −3) |
| 3 | observer −2 2 −3 (watching the note block) → obsidian −2 3 −3: piston −2 3 −4 pushes its middle block up into the doorway (−2 4 −4 → −2 5 −4). Observer 1 2 −4 (watching the dropper's *triggered*) → repeater 0 2 −5 (delay 4). The wall torch 0 1 −4 under the wire goes out |
| 5 | the lower dropper pushes the dust up into the upper dropper (its 4-tick dispense delay). Observers −3 2 −3 (via −3 1 −3, watching the note block) and 0 2 −4 (watching the torch 0 1 −4) fire: −3 3 −4 and −1 3 −4 push their middle blocks up; −2 3 −4 drops its block (spit). 7: the other two spits; the bottom cells hold the middle blocks |
| 7 | comparator 1 2 −2 reads the upper dropper: one dust in nine slots is signal 1. Its output block 1 2 −1 turns the torch tower off step by step: wall torch 1 2 0 and torch 1 3 −1 out at 9, torch 1 4 0 lit at 11, torch 1 6 0 and wall torch 1 5 −1 out at 13 |
| 9 | torch 1 3 −1 out → wire 1 4 −2 off → the slider 0 3 −2 (down) retracts and pulls observer 0 1 −2 up to 0 2 −2 (lands 11, pulses 13): at y 2 it watches the button's wire 0 2 −3 |
| 11 | repeater 0 2 −5 on for 8 ticks (a 2-tick pulse stretched to the repeater's delay) → note blocks −3 2 −5, −1 2 −5 and wire −2 2 −5: the stacks x 2 −4 lift the door pistons to y 4 (land 13) |
| 13 | observers x 3 −5 (watching the note blocks and the wire) → bookshelves x 4 −5: 14: the lifted pistons x 4 −4 push the middle blocks from y 5 to y 6 (spat 15). Closed middle row at 15 |
| 15 | observers 0 7 0 (watching wire 0 6 0, off since 13) and 1 7 0 (watching torch 1 6 0) → wire 0 8 0 → wires x 9 0: the pushers x 7 0 (quasi-connected to the wire two above them) push the top blocks one cell north (x 7 −1 → −2), spat at 17 |
| 17–23 | 1 8 0 → activator rails 1 10 0 / 1 10 −1 (17) → observer 1 10 −2 (19) → repeater 0 10 −3, delay 1 (21) → rails x 10 −3 (21) → observers x 10 −2 (23), which quasi-power the stacks x 9 −1: they push the parked pistons down into the row (x 8 −1 → x 7 −1), spat 25 |
| 19 | the stacks x 2 −4 retract and take the door pistons back to y 3 |
| 21 | repeater −1 6 0 off (8 after torch 1 6 0) → wire −2 6 0 → wool −2 5 0 unpowered: the switch pistons x 4 0 retract and pull the floor bookshelves x 4 −2 → x 4 −1. Repeater 0 2 −1 on (the slider observer's landing pulse of 13 + 8) → wires x 2 0 → repeaters x 2 −1 (delay 4). The note blocks' turn-off (19) fires x 3 −5 again: 22–25 the door pistons extend into air and retract (a pulse that moves nothing) |
| 25–27 | observer −3 10 −1 → hopper −3 10 0 disabled (25) → observer −2 10 0, watching the hopper's *enabled* (27) → wool −1 10 0: the wires x 9 0 light again and the pushers x 7 0 push piston and block one cell (piston to x 7 −2, block to x 7 −3), spat 29; the piston 0 10 0 pushes observer 0 10 −1 to 0 10 −2 (lands 29, pulses 31) |
| 29 | repeaters x 2 −1 on (8 ticks): the stacks x 2 −2 lift the pistons x 3 −2 to y 4 (land 31). Observers x 3 −1 (watching those repeaters) → bookshelves x 4 −1 |
| 31 | the moved observer 0 10 −2 → wire 0 9 −2 → wires x 9 −2 → bookshelves x 8 −2: the carried pistons x 7 −2 push the top blocks into the doorway (x 7 −3 → −4), spat 33. **The button releases**: the note block and the wire 0 2 −3 go off. Repeater 1 6 −3 went off at 29 (torch 1 5 −1 → 1 6 −2 → 1 6 −3, 8 + 8): its observers 1 7 −3 and 1 5 −3 fire; 1 5 −3 updates the piston 1 4 −4, which has lost its quasi-power and retracts, pulling the dropper-observer 1 2 −4 up to 1 3 −4, out of the dropper's view. In the same tick the release un-triggers the dropper, a change the observer would report at 33: its scheduled tick finds the cell empty (the observer fires at 3 and 97 only; its landing pulse at 35 goes into air) |
| 32 | the lifted pistons x 4 −2 push the floor blocks north under the doorway (x 4 −3 → x 4 −4), spat 33 |
| 33–37 | the release fires the note-block observers again (−2 2 −3 at 33; −3 1 −3 / −3 2 −3 and 0 1 −4 / 0 2 −4 at 35): the door pistons x 3 −4 push the floor blocks up into the bottom row (−2 at 33, −3 and −1 at 35; spat 35 / 37). At 33 the spit of −2 4 −2 and the lift of −2 3 −4 are in the same tick, spit first: the block must have landed in x 4 −4 before it is pushed up (R-026). 1 7 −3 → rail 0 8 −3 (31) → 0 8 −2 (33) → repeater 0 8 −1, delay 1 (35) → wire 0 8 0 → x 9 0: the pushers x 7 0 extend at 35 and at 37 **pull the carried pistons back** to x 7 −1. **Doorway full at 37** |
| 37–47 | stacks x 2 −2 down (37). 1 7 −2 (33) → repeater 1 7 −1, delay 2 (37) → 1 8 −1 (39) → rails → 1 10 −2 (41) → 0 10 −3 (43) → rails x 10 −3 → x 10 −2 (45): the stacks x 9 −1 extend into the empty x 8 −1 and at 47 **lift the carried pistons out**, parked again. 39–43: x 7 −1 extends and retracts in the row (quasi-power from x 8 −2, moves nothing) |
| 49–57 | the release pulse of the slider observer (33) comes round again: repeater 0 2 −1 (41) → x 2 −1 (49): the stacks x 2 −2 lift once more; the lifted pistons extend at 52 into the empty x 4 −3 and retract at 53; down at 57. The same chain does the work when opening. 0 10 0 pulls its observer back at 51 (its landing pulse at 55 goes nowhere). At rest from 59 |

**Opening** (press at 63, release at 93):

| tick | what happens |
|---|---|
| 63 | the button, the wires and the note block as at 1; the slider observer, now at 0 2 −2, sees the wire 0 2 −3 light (pulse 65) |
| 65–69 | the note-block observers: −2 3 −4 extends into the empty x 4 −4 (65) and at 67 **pulls the bottom-center block down** (−2 5 −4 → −2 4 −4); −3 and −1 at 67 / 69. The bottom row is open at 69 |
| 67 | the upper dropper throws the dust out (4 ticks after the press), south, into the comparator's cell. The comparator reads 0 at 69: the memory flips back |
| 71 | wall torch 1 2 0 and torch 1 3 −1 lit → wire 1 4 −2: the slider 0 3 −2 pushes its observer back down to 0 1 −2 (its landing pulse at 75 ends in the wall) |
| 73–85 | repeater 0 2 −1 (73, from the observer's pulse at 65) → repeaters x 2 −1 (81): the stacks x 2 −2 lift the pistons x 3 −2 (land 83); 84 they extend into x 4 −3 and at 85 **pull the bottom blocks back under the table** (x 4 −4 → x 4 −3); stacks down at 89 |
| 75–91 | torch 1 4 0 out (73) → torch 1 6 0 and wall torch 1 5 −1 lit (75) → wire 0 6 0 → repeater −1 6 0 (83) → wool −2 5 0: the switch pistons are powered at 83, but their push line ends in the lifted piston still landing at x 4 −2 (R-026: nothing is queued). The observers x 3 −1 fire at 91 (the repeaters x 2 −1 turned off at 89) and update them: they **push the floor bookshelves back** (x 4 −1 → x 4 −2) |
| 77–95 | 0 7 0 / 1 7 0 (77) → x 9 0: the pushers extend into the empty x 7 −1 and spit (nothing to push). 1 8 0 (79) → rails → 1 10 −2 (81) → 0 10 −3 (83) → x 10 −2 (85): the stacks x 9 −1 lower the parked pistons into the row (spat 87). Hopper (87) → −2 10 0 (89): the pushers push the lowered pistons one cell north (x 7 −1 → −2, spat 91) and 0 10 0 pushes its observer north again (pulse 93) → x 9 −2: the carried pistons extend at 93 and at 95 **pull the top blocks out of the doorway** (x 7 −4 → −3) |
| 93–105 | wall torch 1 5 −1 (75) → repeaters 1 6 −2 (83), 1 6 −3 (91) → bookshelf 1 6 −4 → observers 1 5 −3 / 1 7 −3 (93): the piston 1 4 −4 pushes the dropper-observer back down to 1 2 −4 (lands 95, **pulses 97**) → repeater 0 2 −5 (105): the stacks x 2 −4 lift the door pistons (land 107). 1 7 −3 → rail 0 8 −3 (93) → 0 8 −2 (95) → 0 8 −1 (97) → x 9 0: the pushers extend at 97 and at 99 pull the carried pistons back to x 7 −1; those extend at 102 (x 9 −2 lit at 101 by 1 8 −1) and at 105 pull the top blocks on (x 7 −3 → −2) |
| 107–113 | 1 7 −2 (95) → 1 7 −1 (99) → 1 8 −1 (101) → rails → 1 10 −2 (103) → 0 10 −3 (105) → x 10 −2 (107): the stacks x 9 −1 extend and at 109 lift the carried pistons out. 108: the lifted door pistons x 4 −4 extend into x 5 −4 and at 109 **pull the middle blocks down** (x 6 −4 → x 5 −4). 111: the pushers x 7 0 (hopper 109 → −2 10 0 at 111) extend and at 113 pull the top blocks home (x 7 −2 → −1): the back wall is whole. Stacks x 2 −4 down at 113 |
| 116–119 | the door pistons x 3 −4 extend into x 4 −4 and at 119 pull the middle blocks into the floor. **Open at 119**, the last block lands at 121; the release's note-block pulses (95–99) moved nothing |

**The item is the memory.** The door has one bit of state: *where the dust is*. Built
open, the dust lies in the lower dropper 1 1 −3 (facing up) and the upper dropper 1 2 −3
(facing south) is empty. A press triggers both (the upper directly from the button, the
lower by quasi-connectivity): the lower one, holding the dust, pushes it up into the
upper one (a dropper facing a container inserts); the upper one, holding it, throws it
out as an item. The comparator 1 2 −2 reads the upper dropper (one dust in nine slots:
signal 1; empty: 0), so **closed = dust up = comparator on**. Press 1: dust up at 5,
comparator on at 7. Press 2: dust out at 67, comparator off at 69. In the game the thrown
dust falls in the comparator's cell onto the hopper 1 1 −2's reach (it sucks items from
the cell above it) and the hopper, facing north, moves it into the lower dropper some
ticks later: the loop is closed and press 3 pushes it up again (inferred from the
game's dropper and hopper rules, not run: the simulator has no item entities,
[[../../differences]]). **In the simulator the dust is gone from 67.** The first cycle is
complete evidence (the dust goes up without becoming an entity, and the second press
only needs it to leave); from the third press on everything that hangs off the
comparator is **simulator-only**: the two-cycle test's second closing runs its
press-driven parts (middle blocks up at 3–15) and differs from tick 30 of the cycle,
where the top row should enter and does not (`inputs --repeat`: differs from 213,
press 3 at 183; backlog D9). A one-item memory is Purplers' answer to the same
question Kwipla answers with a redstone block that a piston toggles
([[4x4-piston-door-kwipla]]): one button, two meanings.

**How the pistons are powered** (the facts table). Only four kinds of signal reach the
mechanism, and the memory decides which parts the press reaches:

- The **press itself** (the note block −2 1 −3 and the dropper's *triggered* state, both
  watched by observers; a wall torch under the wire for the third column) spits the
  middle blocks up (3–7), starts the stacks x 2 −4 through the dropper-observer 1 2 −4 (11)
  and, on the release, lifts the bottom row (33–37). On the second press the same
  pulses pull the bottom row down (65–69); the dropper-observer is parked away then, so
  the stacks do not fire.
- The **memory's edge** (the comparator through a tower of five torches at x = 1, each
  stage two ticks later: 9, 11, 13) drives everything with a direction: the floor
  switch, the top row's whole choreography, the slider, the dropper-observer's return.
- **Two moved observers reroute the press.** The slider observer 0 1 −2 / 0 2 −2 (the
  piston 0 3 −2, held by the torch 1 3 −1) watches the button's wire only while the
  door is closed: its pulses on the release (33) and on the next press (65) are what
  drive the floor stacks x 2 −2 (through 0 2 −1 and x 2 −1, 8 + 8 ticks), so the floor
  blocks are slid in at 32 and pulled back at 85. The dropper-observer 1 2 −4 is lifted
  out of the dropper's view at 31 and set back at 93: it fires the stacks x 2 −4 on the
  press when closing and on its own landing (97) when opening. Moving an observer is
  both an enable switch and, on landing, a pulse (R-015).
- Quasi-connectivity, 54 of the 107 extensions: the pushers x 7 0 under the wires x 9 0,
  the stacks x 9 −1 beside the observers x 10 −2, the carried pistons under the
  bookshelves x 8 −2, the piston 1 4 −4 under 1 6 −4; and an **update relay**: the
  observer 1 5 −3 fires into the cell beside 1 4 −4 exactly when its quasi-power
  changes, so the piston notices (31, 93).

**Controller.** Observers watching cheap state blocks are the wiring: note blocks
(*powered*), activator rails (*powered*; the three at x 10 −3 are also a bus from one
repeater to three observers), a hopper (*enabled*: a 2-tick pulse into it comes out as
one observer pulse two ticks later at −2 10 0), the droppers (*triggered*), and
observers watching observers. The waits are repeaters: 0 2 −5, 0 2 −1, x 2 −1 and −1 6 0
(delay 4: each also stretches a 2-tick pulse to 8, the stack pulses), 1 6 −2 / 1 6 −3
(delay 4 each: the 16 ticks before the dropper-observer is moved), 1 7 −1 (delay 2),
0 10 −3 and 0 8 −1 (delay 1). The ablation agrees on which delays are exact: 18 of the
33 delay changes break the door; the stack repeaters 0 2 −1 and x 2 −1 accept delays
1–3 and 1 7 −1 delay 1 (internal only). 32 of the 49 conductors matter when glass
([[../robustness]]); the bookshelves x 4 −5, x 8 −2, x 4 −1, 1 6 −4 and the wools
0 3 −4, −1 10 0, −2 5 0 are power blocks, the obsidian x 3 −3 is something else:

**Mechanics as logic.** (1) **Obsidian as a cap.** When the stacks x 2 −2 set the pistons
x 3 −2 back down (57 closing, 89 opening), the observers x 3 −1 above the repeaters fire
on the repeater turning off and quasi-power the landing piston for one tick through the
bookshelf x 4 −1. Its push line is the obsidian: immovable, nothing is queued.
Experiment A (−1 3 −3 glass): at 60 the piston pushes the glass, the door piston −1 3 −4
and the observer −1 3 −5 one cell north and the door is wrong from 69. The same
"immovable cap" as Kwipla's furnaces ([[4x4-piston-door-kwipla]]). (2) **The button is a
timer.** The bottom row's lift is triggered by the button's *release* (31 → 33 / 35),
after the floor blocks were slid in at 32. Experiment B (a stone button, 20 ticks): the
release comes at 21, while the door pistons are up on the air pulse of 22–25 and the
floor blocks are still under the table, and while the dropper-observer is still in the
dropper's view: it fires at 23 and restarts the stacks x 2 −4 at 31, into the floor
slide. The doorway is wrong from 33 and the bottom row ends open. So the 30 ticks are
timed twice: the lift must follow the slide (32), and the release must not come before
the dropper-observer is pulled away (31). An oak button is a 30-tick delay line here. (3)
**A moving block as a wait.** The floor switch is powered at 83 while the lifted
piston is still landing in its push line (R-026); the update that lets it push comes at
91 from an observer, after the piston went down at 89. (4) **Same-tick order.** At 33
the floor block is spat (lands) before the door piston under it fires: one of the six
"retract, then extend" ticks the mechanism page counts (the other five were not
traced). The mechanism
page's stripped door differs from tick 3 for a reason of the split itself: the lab
classes bookshelves as analog sources, so the stripped build has no door blocks (x 4 −4,
x 4 −3, x 7 −1 are air there) and the first spits push nothing (noted for D4).

**Input window** ([[../robustness]]): a second press within the 30 ticks the button is
down is no press (gaps 1–29 ignored); from gap 30 the door is stuck at 30–33, 35 and
44–45, "door ok" at 54, clean from 55 (the design's 62 waits 7 more). The no-overlap gap
is 57: the last bad gap pushes into a sticky piston that is still extended. None of
the eight real bad gaps recovers with one or two more presses, but every gap from 55 is
clean: a user who waits for the door to settle is safe. Simulator-only beyond the
first cycle (above).

**Lessons.** (1) A block entity in the way is a constraint on the *storage*, not on the
mechanism: store the door as floor and wall around it (here the bottom row is the
table's floor, the top row the back wall's top). (2) One item can be a one-bit memory:
dropper up / dropper down, read by a comparator; the button that toggles it also pulses
the controller, and the memory's edge, not the press, carries the direction. (3) A
piston carried into a row extends its reach: lower it behind the block, push both,
fire it once, pull it back, lift it out. (4) Moved observers are switches: an observer
set in or out of a block's view decides which pulses a press produces, and its landing
is a pulse of its own. (5) Immovable caps and a button's press time are part of the
timing: an obsidian absorbs a wrongly timed landing pulse, an oak button's 30 ticks set
when the bottom row rises.

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 3×3 in the plane z = -4; 0 more output cells outside it.
- Timeline: use oak_button at 1, use oak_button at 63; markers Closing 1, Closed 62, Opening 63, Opened 123
- Reference states: closed at tick 62, open at tick 123. Fully closed at ticks 37-66; fully open at 0-2, 119-137.
- Pistons by role: door 18, idle 6, power mover 3, power switch 3, stack 9
- How extensions were powered (block giving the signal; QC = through the block above the piston): block←observer 31, wire (QC) 25, observer (QC) 12, repeater 9, block←observer (QC) 8, block←wire (QC) 8, block←wire 7, bud 4, wire 2, block←repeater (QC) 1
- Phases (bursts of piston events): 3–53 (149 events, 33 pistons); 57–57 (3 events, 3 pistons); 65–71 (10 events, 4 pistons); 77–119 (127 events, 32 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
  0    3    5    7   14   15   31   33   35   37   67   69   95  108
...  ...  ...  ...  ...  ...  ~~~  ###  ###  ###  ###  ###  ...  ...
...  ...  ...  ...  ~~~  ###  ###  ###  ###  ###  ###  ###  ###  ###
...  .~.  ~#~  ###  ~~~  ...  ...  .~.  ~#~  ###  #.#  ...  ...  ~~~

109  111  119
...  ...  ...
...  ...  ...
~~~  ###  ...

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| below | 6 | 9 | 4×6 | down 2 (3), down 1, south 1 (3) |
| recess | 3 | 9 | 6×3 | south 3 (3) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| -3 3 -4 S | up | door | 5+2→spat, 22+3→retracted, 35+2→spat, 67+2→pulled, 97+2→spat, 116+3→pulled | block←observer 4, block←observer (QC) 2 |
| -3 4 -4 S | up | door | 14+1→spat, 108+1→pulled | block←observer 2 |
| -3 4 -2 S | north | door | 32+1→spat, 52+1→spat, 84+1→pulled | block←observer 3 |
| -3 7 -2 S | north | door | 31+2→spat, 93+2→pulled | block←wire 2 |
| -3 7 -1 S | north | door | 40+3→retracted, 102+3→pulled | block←wire (QC) 2 |
| -3 7 0 S | north | door | 15+2→spat, 27+2→spat, 35+2→pulled, 49+2→spat, 77+2→spat, 89+2→spat, 97+2→pulled, 111+2→pulled | wire (QC) 8 |
| -2 3 -4 S | up | door | 3+2→spat, 22+3→retracted, 33+2→spat, 65+2→pulled, 95+2→spat, 116+3→pulled | block←observer 4, block←observer (QC) 2 |
| -2 4 -4 S | up | door | 14+1→spat, 108+1→pulled | block←observer 2 |
| -2 4 -2 S | north | door | 32+1→spat, 52+1→spat, 84+1→pulled | block←observer 3 |
| -2 7 -2 S | north | door | 31+2→spat, 93+2→pulled | block←wire 2 |
| -2 7 -1 S | north | door | 40+3→retracted, 102+3→pulled | block←wire (QC) 2 |
| -2 7 0 S | north | door | 15+2→spat, 27+2→spat, 35+2→pulled, 49+2→spat, 77+2→spat, 89+2→spat, 97+2→pulled, 111+2→pulled | wire (QC) 8 |
| -1 3 -4 S | up | door | 5+2→spat, 22+3→retracted, 35+2→spat, 67+2→pulled, 97+2→spat, 116+3→pulled | block←observer 4, block←observer (QC) 2 |
| -1 4 -4 S | up | door | 14+1→spat, 108+1→pulled | block←observer 2 |
| -1 4 -2 S | north | door | 32+1→spat, 52+1→spat, 84+1→pulled | block←observer 3 |
| -1 7 -2 S | north | door | 31+2→spat, 93+2→pulled | block←wire 2 |
| -1 7 -1 S | north | door | 40+3→retracted, 102+3→pulled | block←wire (QC) 2 |
| -1 7 0 S | north | door | 15+2→spat, 27+2→spat, 35+2→pulled, 49+2→spat, 77+2→spat, 89+2→spat, 97+2→pulled, 111+2→pulled | wire (QC) 8 |
| 0 3 -2 S | down | power mover | pulled at 9, 71+None→held | wire (QC) 1 |
| 0 10 0 S | north | power mover | 27+2→spat, 49+2→pulled, 89+2→spat, 111+2→pulled | block←observer 4 |
| 1 4 -4 S | down | power mover | pulled at 31, 93+None→held | block←repeater (QC) 1 |
| -3 4 0 S | north | power switch | pulled at 21, 91+None→held | block←wire (QC) 1 |
| -2 4 0 S | north | power switch | pulled at 21, 91+None→held | block←wire 1 |
| -1 4 0 S | north | power switch | pulled at 21, 91+None→held | block←wire (QC) 1 |
| -3 2 -4 S | up | stack | 11+8→pulled, 105+8→pulled | bud 2 |
| -3 2 -2 S | up | stack | 29+8→pulled, 49+8→pulled, 81+8→pulled | repeater 3 |
| -3 9 -1 S | down | stack | 23+2→spat, 45+2→pulled, 85+2→spat, 107+2→pulled | observer (QC) 4 |
| -2 2 -4 S | up | stack | 11+8→pulled, 105+8→pulled | wire 2 |
| -2 2 -2 S | up | stack | 29+8→pulled, 49+8→pulled, 81+8→pulled | repeater 3 |
| -2 9 -1 S | down | stack | 23+2→spat, 45+2→pulled, 85+2→spat, 107+2→pulled | observer (QC) 4 |
| -1 2 -4 S | up | stack | 11+8→pulled, 105+8→pulled | bud 2 |
| -1 2 -2 S | up | stack | 29+8→pulled, 49+8→pulled, 81+8→pulled | repeater 3 |
| -1 9 -1 S | down | stack | 23+2→spat, 28+1→spat, 45+2→pulled, 85+2→spat, 90+1→spat, 107+2→pulled | observer (QC) 4, block←observer (QC) 2 |

<!-- end generated -->
