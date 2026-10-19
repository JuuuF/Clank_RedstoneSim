# Sliding Piston Door by Purplers

World: `piston_doors_with_slime/4x4 Sliding Piston Door by Purplers.redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(Hand-written 2026-10-19 from the replay's piston events, `why` traces and four
one-change experiments on copies in `.sandbox/doors/explain/4x4-sliding-piston-door-purplers/`
(A–D below); [[../robustness]], [[../metrics]], [[../symmetry]].)

A 4x4 door in the plane z = −2 (cells x −2..1, y 4..7) whose two halves **slide in from
the sides, two cells each**. The lever (0 3 0, on the frame block 0 3 −1) closes it 9 ticks
after the flip (closed at 10) and opens it 4 ticks after the flip (open at 17): the
fastest 4x4 of the dataset and the shortest safe gap (9), paid for with the largest 4x4
build: box 20×11×4 (880), 401 blocks above the floor, 70 pistons (66 fire), 20 redstone
blocks ([[../metrics]]). Direction-independent: all eight orientations replay identically.
The east side is the west side mirrored at x = −0.5: all 81 piston events of each side
mirror the other's (checked on the replay), so everything below is said for the west.

**The halves (geometry).** Each half is a 2×4×3 slab of 24 blocks: a core of four slime
and four honey blocks in the door plane, and 16 chiseled quartz blocks on its front
(z = −1) and back (z = −3) faces. The quartz is what the player sees; the sticky core is
hidden inside the wall. Open, the west half rests at x −4..−3, the east at 2..3. The core
is two 2×2 assemblies: in the west half slime above (y 6..7) and honey below (y 4..5), in
the east half honey above and slime below. Slime and honey do not stick to each other, so
(1) each 2×2 core with its 8 quartz is a separate 12-block assembly, exactly the piston
limit, and (2) at the closed seam (x −1 | 0) slime always meets honey and the halves never
merge. Experiment B (the east core built like the west one, slime above): the door closes
normally at 10 and never opens: at 14 the pulls find the two slime assemblies joined
across the seam (24 blocks) and move nothing.

**Floor and ceiling are taken out of contact first.** Under and over the halves run two
rows of 8 quartz (y 3 and y 8, x −4..3) on 16 sticky pistons (y 1 facing up, y 10 facing
down), extended at rest. Honey and slime would drag them along, so at tick 2 all 16
retract and pull the rows away (floor to y 2, ceiling to y 9; landed at 4) before anything
slides, and push them back at 17 (landed 19) when the halves are home. The frame the
player sees (z = −1, y 3 and 8) is fixed, so the gap behind it is invisible (read from
the maps). Ablation: every one of the 16 pistons is needed (removal breaks the door); the
quartz blocks themselves are not (internal: no block, no contact).

**Each half moves in two one-cell strokes** (from the move lists: every core move is 11
or 12 blocks, the limit). Four sticky pistons face the doorway at x = −5, y 4..7:

1. **Tick 5, first cell.** The y 5 piston pushes the honey assembly, the y 6 piston the
   slime assembly (landed at 7; the doorway's outer columns fill). Each push is 11
   blocks: the 2×2 core, six quartz, and the retracted piston at y 4 (or y 7), which
   the core **carries along** (honey sticks to a retracted piston; slime to anything
   movable): the two carried pistons ride one cell east to x −4. The two remaining front
   quartz (y 5 and y 6, z −1) would make it 13, so two plain pistons at −5 5 −1 and
   −5 6 −1 push them separately **in the same tick, earlier in the queue** (the front
   pistons' events rank 8–13 of 32 in tick 5, the core pushes 27–31): a block that is still moving is skipped
   as a sticky neighbour, so the cores count 11. Experiment A (−5 5 −1 removed): the
   honey pusher never even queues an event (its structure has 13 blocks) and the lower
   half of the west side stays open. The order inside the tick is made by the power
   sources: the front pistons are powered by a redstone block that lands at 4 (pulled to
   −9 10 −3 at 2, through a wire staircase to −6 6 −1), so they queue at 4 and head tick
   5's queue; the core pushers are powered inside tick 5 by a chain of spits (below) and
   queue behind them. Inferred: had the front quartz been pushed a tick earlier and
   landed, the cores would stick to them again (13).
2. **Tick 8, second cell.** The carried pistons, now at −4 4 −2 and −4 7 −2, extend and
   push 12 blocks each (core and all 8 quartz; the pusher itself is excluded): closed at
   10. The bottom one is powered by a redstone block pushed under it at the same time
   (−6 3 −2 pushes it from −5 3 −2 to −4 3 −2 at 5; piston and block land at 7, the
   piston extends at 8: a landing check). The top one is quasi-connected to a redstone
   block lowered to −4 8 −1 at 2 (by −4 10 −1). Also at 8 the two **stack pistons**
   −6 4 −2 and −6 7 −2 (quasi-powered: a wool block lowered into the output cell of
   the comparator −8 5 −2 at 5, and a redstone block pushed to −6 9 −3 at 5; both land
   at 7 and update them through the note block −6 5 −2 and the wire −6 9 −2) extend
   into the cells the carried pistons left. They matter on the way back.

Opening (lever off at 13):

3. **Tick 14.** The carried pistons retract and pull their assemblies back one cell (12
   blocks each; landed 16). The bottom one loses its redstone block (−6 3 −2 pulls it
   back at 14) and retracts at once. The top one is quasi-connected: its block is pulled
   up at 14 (−4 10 −1), but a quasi-connected piston does not notice until it is
   updated. The update is delivered by the plain piston −5 8 −2, whose head has sat in
   −4 8 −2, the cell above the carried piston, since tick 2 and is withdrawn at 14
   (itself updated by −5 9 −2 retracting when the wire −5 10 −1 goes off). Experiment C
   (−5 8 −2 removed): the carried top piston stays extended through 14–16, retracts
   only at 17 when the stack piston's head beside it disappears, and the west slime
   assembly ends one cell inside the doorway (x −3..−2; the column x −2 stays solid at
   y 6..7 from 19). Two pistons per side exist only to pass one block update down to a
   quasi-connected piston; the upper one, −5 9 −2, is redundant in the simulator:
   without it the head at −4 8 −2 relays the redstone block's departure to −5 8 −2
   itself (experiment E; the ablation calls it internal).
4. **Tick 17.** The stack pistons pull the carried pistons back to x −5 (events 36–37 of
   48 in the tick; the east pair 32–33), then the y 5 / y 6 pushers retract and pull their
   assemblies home (12 blocks each; events 45 and 47). The order matters: the carried piston at −4 4 −2 is
   stuck to the honey, and with it the pull would be 13. Experiment D (stack piston
   −6 4 −2 removed): at 17 the pusher −5 5 −2 moves nothing ("retract retracted") and
   the west honey assembly stays at x −3..−2. In the original the stack pistons' update
   chain is two block events long (the wool −7 5 −2 lifted out of the comparator's
   output, the note block −6 5 −2 off, the piston), the pushers' four (the redstone-block
   chain at z −3 reversed), so the stack pistons queue first. Open at 17 (the cells
   empty when the blocks start moving), floor and ceiling back at 19, the controller's
   last events at 20.

**Power: moving redstone blocks, no timing components.** The lever feeds one wire under
the doorway (y 2, z −1, x −5..4). Everything else is pistons moving redstone blocks (20
"power movers") or moving the conductor next to a source (8 "power switches", including
four wool blocks slid into the output cells of furnace comparators: each furnace holds one
redstone dust, signal 1, enough for the next block). The two repeaters only turn the
constant redstone blocks at −10 11 −2 / 9 11 −2 into strongly powered wool for the
ceiling wire (their delay is inert in the ablation); the six note blocks are update
relays: a note block changes its `powered` state when a signal arrives or leaves, and
that change updates the quasi-connected piston below it. The only delays are piston
travel: a pushed block lands 2 ticks after its event and the piston it powers fires one
tick later, so the stages fall on ticks 2, 5, 8, 11 (closing) and 14, 17, 20 (opening).
Inside a stage, **spits** chain in one tick: a piston pushes a redstone block, the block's
departure unpowers a second piston, which retracts and pulls away the first one's
conductor, so the first drops its block where it is (the block lands at once) and the
dropped block powers the next piston. The west side's closing:

| tick | what the controller does (west; the east mirrors it) |
|---|---|
| 1 | the lever's wire powers the wool −6 2 −1 |
| 2 | −6 3 −1 pushes the redstone block −7 3 −1 west; that block had quasi-powered −8 2 −1, which retracts and pulls the wool away from the wire, cutting −6 3 −1: the block is spat at −8 3 −1. From there: the note block −8 3 −2 switches on and −8 2 −2 pushes the block −7 2 −2 to −6 2 −2, so the floor wire (z −3, y 2) loses its source and the 8 floor pistons retract; a wire staircase up z −1 (−9 3 −1 … −9 11 −1) switches on and −8 11 −1 pushes the wool −8 11 −2 out of the repeater's output, so the ceiling wire (z −3, y 11) loses its source and the 8 ceiling pistons retract; the staircase also fires −10 1 −2 (a slime block lifts a wool block into the output cell −10 4 −2 of the comparator −9 4 −2), −4 10 −1 (lowers the redstone block for the carried top piston to −4 8 −1), −5 9 −2 and −5 8 −2 (the update helpers); −8 10 −3, which the moved wool had quasi-powered, retracts and pulls a redstone block to −9 10 −3 |
| 4 | the blocks land: the wool at −10 4 −2 carries the comparator's 1 through the wire −10 4 −3 to the wool −9 4 −3; the block at −9 10 −3 powers the staircase at z −3 / z −1 that ends at the wire −6 6 −1 (the front pistons queue) |
| 5 | −9 5 −3 pushes the redstone block −8 5 −3 east; its departure unpowers −7 4 −3, which retracts and pulls the wool −9 4 −3 away, cutting −9 5 −3: spit at −7 5 −3. That block powers −7 6 −3, which pushes −6 6 −3 east; that departure unpowers −5 5 −3, which retracts and pulls the block at −7 5 −3 to −6 5 −3, cutting −7 6 −3: spit at −5 6 −3. That block lies beside the slime pusher −5 6 −2 (direct) and beside the cell above the honey pusher −5 5 −2 (quasi-connectivity): both push. Also at 5: −6 3 −2 (powered by the block landed at −6 2 −2) pushes −5 3 −2 under the carried bottom piston; −7 7 −2 lowers a wool block into the comparator output −7 5 −2 and −8 9 −3 pushes a block to −6 9 −3: the stack pistons' sources |
| 8 | the carried pistons and the stack pistons extend (above) |
| 11 | −9 5 −3 and −7 6 −3 extend again into air (their power is back): the last closing events |

Opening runs the same chains in reverse with pulls: at 14 −6 3 −1 (re-extended at 8)
pulls the block −8 3 −1 back to −7 3 −1, the staircase goes off, −8 2 −2 and −8 11 −1
pull the floor block and the ceiling wool back (both wires on again at 16, their 16
pistons extend at 17), the carried pistons lose their blocks and pull; at 17 the
comparator wools are moved out of the output cells, the z −3 chain reverses in one tick
(−9 5 −3 pulls −7 5 −3 to −8 5 −3, −7 6 −3 pulls −5 6 −3 to −6 6 −3, the pushers lose
power and pull home) and the stack pistons pull the carried pistons back; at 20 the last
blocks are pushed back where the build has them.

**Lessons.** (1) **Slime and honey are chosen by what must not stick**: the two cores of
a half are separate assemblies so that each stays within 12 blocks, and the halves meet
slime-to-honey so they part again (experiment B). (2) **The 12-block limit is designed
to the block**: 11 with the carried piston, 12 without; the extra blocks are pre-pushed in
the same tick, ahead in the queue, which a block still moving allows (experiment A), and
the carried piston is pulled off before the 12-block pull home (experiment D). (3)
**Floor and ceiling retract to break adhesion**, not to move door blocks: a slime door's
frame must be out of contact while it moves. (4) **A quasi-connected piston needs an
update to let go**: here a piston head withdrawn from the cell above it (experiment C),
and note blocks as update relays; the carried bottom piston is powered from directly
below instead and needs none. (5) **A controller can be all moving redstone blocks**:
power switches, spits and landing checks give exact 3-tick stages and in-tick chains
without a single repeater delay, and the order inside a tick follows from whether a
piston's power landed last tick or was spat this tick.

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 4×4 in the plane z = -2; 0 more output cells outside it.
- Timeline: use lever at 1, use lever at 13; markers Closing 1, Closed 12, Opening 13, Opened 22
- Reference states: closed at tick 12, open at tick 22. Fully closed at ticks 10-13; fully open at 0-4, 17-53.
- Pistons by role: door 8, fires, moves nothing 4, helper 22, idle 4, power mover 20, power switch 8, stack 4
- How extensions were powered (block giving the signal; QC = through the block above the piston): block←wire 28, redstone_block 14, redstone_block (QC) 12, wire 8, block←wire (QC) 6, block←comparator (QC) 4, wire (QC) 4, block←repeater (QC) 2
- Phases (bursts of piston events): 2–20 (162 events, 66 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
   0     5     7     8    10    14    16    17
....  ~..~  #..#  ~~~~  ####  ~..~  #..#  ....
....  ~..~  #..#  ~~~~  ####  ~..~  #..#  ....
....  ~..~  #..#  ~~~~  ####  ~..~  #..#  ....
....  ~..~  #..#  ~~~~  ####  ~..~  #..#  ....

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| east | 8 | 4 | 4×8 | east 2 (8) |
| west | 8 | 4 | 4×8 | west 2 (8) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| -5 5 -2 S | east | door | 5+12→pulled | redstone_block (QC) 1 |
| -5 6 -2 S | east | door | 5+12→pulled | redstone_block 1 |
| -4 4 -2 S | east | door | 8+6→pulled | redstone_block 1 |
| -4 7 -2 S | east | door | 8+6→pulled | redstone_block (QC) 1 |
| 3 4 -2 S | west | door | 8+6→pulled | redstone_block 1 |
| 3 7 -2 S | west | door | 8+6→pulled | redstone_block (QC) 1 |
| 4 5 -2 S | west | door | 5+12→pulled | redstone_block (QC) 1 |
| 4 6 -2 S | west | door | 5+12→pulled | redstone_block 1 |
| -5 8 -2 | east | fires, moves nothing | 2+12→retracted | block←wire (QC) 1 |
| -5 9 -2 | up | fires, moves nothing | 2+12→retracted | block←wire 1 |
| 4 8 -2 | west | fires, moves nothing | 2+12→retracted | block←wire (QC) 1 |
| 4 9 -2 | up | fires, moves nothing | 2+12→retracted | block←wire 1 |
| -10 1 -2 S | up | helper | 2+15→pulled | block←wire 1 |
| -5 5 -1 | east | helper | 5+12→retracted | wire (QC) 1 |
| -5 6 -1 | east | helper | 5+12→retracted | wire 1 |
| -4 1 -2 S | up | helper | pulled at 2, 17+None→held | block←wire 1 |
| -4 10 -2 S | down | helper | pulled at 2, 17+None→held | block←wire 1 |
| -3 1 -2 S | up | helper | pulled at 2, 17+None→held | block←wire 1 |
| -3 10 -2 S | down | helper | pulled at 2, 17+None→held | block←wire 1 |
| -2 1 -2 S | up | helper | pulled at 2, 17+None→held | block←wire 1 |
| -2 10 -2 S | down | helper | pulled at 2, 17+None→held | block←wire 1 |
| -1 1 -2 S | up | helper | pulled at 2, 17+None→held | block←wire (QC) 1 |
| -1 10 -2 S | down | helper | pulled at 2, 17+None→held | block←wire (QC) 1 |
| 0 1 -2 S | up | helper | pulled at 2, 17+None→held | block←wire (QC) 1 |
| 0 10 -2 S | down | helper | pulled at 2, 17+None→held | block←wire (QC) 1 |
| 1 1 -2 S | up | helper | pulled at 2, 17+None→held | block←wire 1 |
| 1 10 -2 S | down | helper | pulled at 2, 17+None→held | block←wire 1 |
| 2 1 -2 S | up | helper | pulled at 2, 17+None→held | block←wire 1 |
| 2 10 -2 S | down | helper | pulled at 2, 17+None→held | block←wire 1 |
| 3 1 -2 S | up | helper | pulled at 2, 17+None→held | block←wire 1 |
| 3 10 -2 S | down | helper | pulled at 2, 17+None→held | block←wire 1 |
| 4 5 -1 | west | helper | 5+12→retracted | wire (QC) 1 |
| 4 6 -1 | west | helper | 5+12→retracted | wire 1 |
| 9 1 -2 S | up | helper | 2+15→pulled | block←wire 1 |
| -9 1 -3 S | south | power mover | pulled at 2, 17+None→held | block←wire 1 |
| -9 5 -3 S | east | power mover | 5+0→spat, 11+6→pulled | block←wire 2 |
| -8 2 -2 S | east | power mover | 2+12→pulled | redstone_block (QC) 1 |
| -8 9 -3 S | east | power mover | 5+12→pulled | wire 1 |
| -8 10 -3 S | west | power mover | pulled at 2, 17+None→held | block←repeater (QC) 1 |
| -7 6 -3 S | east | power mover | 5+0→spat, 11+6→pulled | redstone_block 2 |
| -6 3 -2 S | east | power mover | 5+9→pulled | redstone_block 1 |
| -6 3 -1 S | west | power mover | 2+0→spat, 8+6→pulled | block←wire 2 |
| -5 5 -3 S | west | power mover | pulled at 5, 8+9→retracted, 20+None→held | redstone_block 1, redstone_block (QC) 1 |
| -4 10 -1 S | down | power mover | 2+12→pulled | wire 1 |
| 3 10 -1 S | down | power mover | 2+12→pulled | wire 1 |
| 4 5 -3 S | east | power mover | pulled at 5, 8+9→retracted, 20+None→held | redstone_block 1, redstone_block (QC) 1 |
| 5 3 -2 S | west | power mover | 5+9→pulled | redstone_block 1 |
| 5 3 -1 S | east | power mover | 2+0→spat, 8+6→pulled | block←wire 2 |
| 6 6 -3 S | west | power mover | 5+0→spat, 11+6→pulled | redstone_block 2 |
| 7 2 -2 S | west | power mover | 2+12→pulled | redstone_block (QC) 1 |
| 7 9 -3 S | west | power mover | 5+12→pulled | wire 1 |
| 7 10 -3 S | east | power mover | pulled at 2, 17+None→held | block←repeater (QC) 1 |
| 8 1 -3 S | south | power mover | pulled at 2, 17+None→held | block←wire 1 |
| 8 5 -3 S | west | power mover | 5+0→spat, 11+6→pulled | block←wire 2 |
| -8 2 -1 S | east | power switch | pulled at 2, 5+9→pulled, 17+None→held | redstone_block 1, redstone_block (QC) 1 |
| -8 11 -1 S | north | power switch | 2+12→pulled | wire 1 |
| -7 4 -3 S | west | power switch | pulled at 5, 8+9→pulled, 20+None→held | block←comparator (QC) 1, redstone_block (QC) 1 |
| -7 7 -2 S | down | power switch | 5+12→pulled | block←wire 1 |
| 6 4 -3 S | east | power switch | pulled at 5, 8+9→pulled, 20+None→held | block←comparator (QC) 1, redstone_block (QC) 1 |
| 6 7 -2 S | down | power switch | 5+12→pulled | block←wire 1 |
| 7 2 -1 S | west | power switch | pulled at 2, 5+9→pulled, 17+None→held | redstone_block 1, redstone_block (QC) 1 |
| 7 11 -1 S | north | power switch | 2+12→pulled | wire 1 |
| -6 4 -2 S | east | stack | 8+9→pulled | block←comparator (QC) 1 |
| -6 7 -2 S | east | stack | 8+9→pulled | wire (QC) 1 |
| 5 4 -2 S | west | stack | 8+9→pulled | block←comparator (QC) 1 |
| 5 7 -2 S | west | stack | 8+9→pulled | wire (QC) 1 |

<!-- end generated -->
