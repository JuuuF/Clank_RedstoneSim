# vault lamp door by Purplers

World: `piston_doors/5x5 vault lamp door by Purplers.redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(Hand-written 2026-10-19 from the replay, `why` traces, the trace of ticks 3 and 28 and
one removal experiment; [[../symmetry]], [[../robustness]], [[../metrics]]. Positions
`x y z`; ticks are the simulator's game ticks; the lever is pulled at 1 and at 14.)

**A 5x5 funnel, not a wall.** The opening is 5 wide (z −3..1), 5 high (y 4..8) and 5
deep (x 0..4); the lever stands on the floor of the opening (4 4 −1, on the quartz
block 4 3 −1), at its outer face. The 25 door cells are not in one plane: the center
(0 6 −1) is five cells deep, the ring around it at x = 1, the next ring at x = 2 (the
8 cells `report` calls the doorway), the next at x = 3 and the four corners at x = 4.
Closed, the door is a stepped funnel seen from the east, with a lit redstone lamp at
its deepest point: the "vault lamp". Open, all 25 cells are air (the whole depth), and
the mechanism is in the walls above (y 9..12), below (y 1..3), north (z −6..−4) and
south (z 2..4). Box 5×12×11 = 660, 373 blocks above the floor, 57 pistons.

**Piston layout.** Every door block is pushed in by a sticky piston from its own wall
and pulled back by the same piston:

- **16 singles** (one cell each): the 12 blocks of the outer rings (8 at x = 3, the 4
  corners at x = 4) come from above (3 10 −2, 3 10 0, 4 10 −3, 4 10 1), from below
  (3 2 −2, 3 2 0) and from the sides (3 5 −5 / 3 5 3, 3 7 −5 / 3 7 3; the bottom corners
  4 4 −5 / 4 4 3 sideways because the floor is under them); at x = 2 the four edge cells
  (2 8 −1 from above, 2 4 −1 from below, 2 6 −3 / 2 6 1 from the sides).
- **8 double extenders** (two cells): the ring at x = 1 (1 7 −1 from above, 1 5 −1 from
  below, 1 6 −2 / 1 6 0 from the sides) and the four x = 2 cells one cell in from the
  edge (2 5 −2 / 2 5 0, 2 7 −2 / 2 7 0, from the sides). Each is a rear sticky piston that pushes a front
  sticky piston and the block one cell (tick 3); the front then pushes the block the
  second cell (tick 6).
- **The center: a triple extender from above.** Three sticky pistons in a column
  (0 10 −1, 0 11 −1, 0 12 −1, facing down) with the lamp at 0 9 −1 under them. The top
  one pushes the two below it and the lamp (3), the middle one pushes the lowest and
  the lamp (6), the lowest pushes the lamp into the center (9, lands 11).
- **Two carriers** at x = 0, y = 6: a double extender on each side that moves a
  redstone block instead of a door block (0 6 4 / 0 6 3 south, 0 6 −6 north).

**Closing** (lever off at 1; all ticks from the replay):

| tick | what happens |
|---|---|
| 1 | the lever's wire line under its block (x = 4, y = 2, z −5..3) drops to 0 |
| 3 | the two torches at its ends (4 3 −6, 4 3 4) turn on; their wires climb both side walls (y 4..9) and run inward at y = 9 (z −4 and z 2); 34 piston events: every single and every rear piston pushes, the lever's bottom torches (2 2 −2, 3 1 0, 1 2 0) push the four bottom pistons; a redstone block is spat into the top line (below) and the top extender's first stage pushes in the same tick |
| 5 | the 16 single-move blocks and the 8 front pistons land; the cauldron is pushed away from its comparator (below); the north redstone block is pulled away (0 6 −4 → 0 6 −5) |
| 6 | the 8 front pistons extend as soon as they land (landing checks): each finds a powered block beside it (a quartz block under a wire of the y = 9, y = 4 or y = 10 lines, the bottom torch's block, the south redstone block) or quasi-connectivity from the y = 9 line; the top stack's middle piston pushes the lowest one and the lamp a second cell |
| 7–8 | the south carrier pushes its redstone block 0 6 2 → 0 6 1; the x = 1 ring lands at 8 |
| 9 | the lowest stack piston (now 0 8 −1) pushes the lamp into the center; the ring at x = 2 is closed from 8 |
| 10–12 | the carrier's front piston pushes the redstone block to 0 6 0, beside the center; the lamp lands at 11, the block at 12 |

All 25 cells are solid from tick 11 (the x = 2 ring from 8); the markers say Closed at 13.

**Opening** (lever on at 14): the line comes back, both torches go out at 16, so every
line that held a piston extended drops in the same tick: at 16 all 16 singles and all 8
fronts retract and pull their blocks one cell, the lowest stack piston pulls the lamp
up one, the carrier pulls its redstone block out of 0 6 0. **All 25 cells are air at 16,
two ticks after the lever.** What follows is the extenders bringing their blocks the
rest of the way home, where the fronts stand one cell too far forward:

| tick | what happens |
|---|---|
| 16 | the top line's redstone block is pulled back (4 11 4); the top stack piston retracts without pulling (the piston below it is still extended) |
| 18 | the north carrier pushes its redstone block back to 0 6 −4; a pink wool is lifted into the shovel furnace's comparator line (below) |
| 20 | the 8 rear pistons retract (repeaters scheduled at 16, delay 2 where traced) and pull their front pistons back; the middle stack piston pulls the lowest one up; a second pink wool is lifted on the north side |
| 22 | the fronts land; the shovel furnace's comparator turns on for 2 ticks: the top stack piston extends |
| 23 | every front piston extends into the gap (landing checks); the lowest stack piston too |
| 24 | all those pulses end: each front pulls its block the last cell (home at 26); the top stack piston pulls the middle one up, the lowest pulls the lamp up one |
| 27–28 | the middle stack piston pulses (1 tick) and pulls the lowest one up |
| 31–32 | the lowest stack piston pulses and pulls the lamp back into the wall (home at 34) |

The doorway is open after 2 ticks, the mechanism at rest after 20 (lever 14 → lamp
home 34). Two rear pistons (1 1 −1 below, 0 6 4 south) try to extend again at 23 and
fail on their extended fronts; harmless, as in Mumbo Jumbo's door.

**The controller.** The lever's line feeds everything through the two torches, so the
door is *closed while the lever is off* and *open while it is on*; the torches invert
once (2 ticks). Three tricks make the rest of the timing:

1. **The top line is switched by a spat redstone block, inside one tick.** The top
   extender and the six "above" pistons are powered by lime wool blocks under a wire
   line at y 11–12, whose source is a redstone block that piston 4 11 4 (facing west)
   pushes from 3 11 4 to 2 11 4. The trace of tick 3 shows three block events in a
   row: 4 11 4 extends (the line's wire 4 10 3 powers the lime wool 4 10 4 under it);
   the redstone block starts moving, so 2 10 4, whose only power was that block (by
   quasi-connectivity: 3 11 4 is beside the cell above the piston), retracts and pulls
   that lime wool from under 4 11 4; 4 11 4 loses its
   power and drops its extension, which finishes the move at once: the redstone block
   stands at 2 11 4 and the wire 2 11 3 reads 15 in the same tick, and the top
   extender's first stage fires with everything else at 3. Afterwards 2 10 4 pushes the
   wool back (6) and 4 11 4 extends again (9) so that its retraction at 16 pulls the
   redstone block home and the top line dies at 16 with the other lines. A
   power-switch spit ([[../patterns]]) used as a line driver.
2. **Lifted wool as a conductor that starts a timer.** Two pink wools are moved into
   the output of a repeater or in front of a comparator when the opening begins: 0 12 3
   lifts 0 10 3 → 0 11 3 (18, lands 20); the comparator 0 11 2 then reads the furnace
   0 11 4 *through* it (a wooden shovel in the fuel slot: signal 5) and turns on at 22,
   which powers the wool 0 12 0 (the top stack piston extends), the wires 0 10 1 /
   0 10 0 (the lowest stack piston extends at 23, through the quartz block 0 9 0) and
   0 12 3 itself, which pushes the wool back down; the comparator turns off at 24 and
   both pulses end. On the north, 1 12 −6 lifts 1 10 −6 → 1 11 −6 (20, lands 22) into
   the output of the repeater 2 11 −6; the wool powers the wire 0 11 −6 and two
   repeater chains along x = 0 (0 11 −4 → 0 11 −2: on 26, off 28; 0 10 −5 → 0 10 −3:
   on 28, off 32), which end the last two stack pulses; the first chain also re-extends
   1 12 −6 (26), which pushes the wool back and spits it (28). Both are self-resetting.
3. **A pulse from a landing check and a repeater that is still on.** The fronts return
   at 20–22 into wires that repeaters of delay 2 fed by the same lines keep alive until
   24 (1 8 4 south, 1 8 −6 north, both scheduled at 20; the y = 5 fronts have their own
   repeaters 1 5 3, 1 5 −5), so each front extends on landing (23) and retracts one tick
   later (24): the
   1-tick "grab" that brings a block the last cell. On the south, 0 9 4 removes the
   orange wool 0 8 4 that carries 1 8 4's output (7–20) and puts it back for the pulse
   (lands 22); the ablation finds the doorway works without this mover and without
   the wool (both internal), so what it protects is not traced.

**The lamp.** The center block is a redstone lamp. In the wall it is kept lit by a
signal of 1: the comparator 2 10 1 reads the water cauldron 2 10 2 (level 3) and its
wire dies at 0 10 0 with power 1, which powers the quartz block 0 9 0 beside the
lamp's rest cell. The cauldron is pushed away from its comparator at 5 (piston 1 10 2)
and pulled back at 24, so the line is off from 5 to 28 (inferred reason: 0 9 0 is
beside the cell above the lowest stack piston in the closed state, and a power of 1
there would hold it; the ablation finds the doorway works without the cauldron,
internal: only the lamp's rest lighting is lost). A second lamp at 0 3 −1, at the
bottom of the shaft under the center column, is lit all the time and changes nothing
when removed (inert): decoration.
In the door the lamp is lit by the carried redstone block at 0 6 0 (verified at 13:
`receives south 15`; the lamp had scheduled its turn-off check for 15 after landing
unpowered at 11 and finds the block, which landed at 12). The lamp stays lit through
the pull-out until 22, is dark from 22 to 34 and lights again when it lands at 0 9 −1
next to the quartz block. The second furnace (1 11 3, one redstone dust: signal 1)
and its comparator 1 11 1 output 1 into 1 11 0, where the helper 3 11 0 pushes a block
during the closed state; the ablation says both comparators matter, what the signal 1
does is not traced. Tick 28 has a near-race: the cauldron's comparator comes back in
the same tick in which the middle stack piston pulls the lowest one up; the lowest
piston queues an extension from the weak line, but the repeater's scheduled tick runs
before the comparator's, so the pull comes first and the extension is skipped.

**Why two orientations jam** ([[../symmetry]], [[../../records/R-027-double-extender-order]],
game EXP-074). The north y = 5 extender (rear 2 5 −6, front 2 5 −5, both facing south)
is powered through the orange wool 2 6 −6 above the rear: directly for the rear, by
quasi-connectivity for the front. Both queue their extension in tick 3; here the rear
is updated first, pushes the front with its block, and the front's own event is
skipped (the four other pairs whose rear and front queue in the same tick end the same
way). Turned 90° or mirrored,
the wire 2 4 −5 *under the front* is reached first, the front extends alone and the
rear's push fails on it: the door jams in the game too.

**The north redstone block** (0 6 −4) powers nothing at rest. Removing the piston that
carries it (0 6 −6, with its head) breaks the door: the north front 1 6 −4 lands beside
the redstone block at 5, is held powered by it and never retracts at 16
(`no_north_carrier.redsim.json` in `.sandbox/doors/explain/…`: 1 6 −4 stays extended
to the end). Removing the redstone block alone is harmless (ablation: internal). So the
carrier exists to take an unwanted power source out of the front's way; what the block
is for in the open state is not visible in the replay (inferred: a leftover, or
symmetry with the south block that lights the lamp, which also powers the south front
1 6 2 when it lands at 5 (`redstone_block` in the power table) before it is carried on).

**Lessons.** (1) A door's depth is free: the funnel costs no extra pistons per cell,
only extender stages for the deeper rings (1, 2 and 3 moves). (2) Opening is fast when
every block's *first* move is a retraction of a powered piston on one line: the
funnel clears in 2 ticks and the extenders tidy up afterwards, out of sight. (3) A
redstone block spat into a wire line switches it within the tick, with no repeater
delay; a block moved into a repeater's or comparator's output starts a timer. (4)
Constant comparator sources (a cauldron level, an item in a furnace) give signal
strengths that a wire turns into a weak, local power (here a 1 that lights the lamp),
and the source can be moved away when that power would be in the way. (5) Two pistons
powered by the same block in one tick are a race; the orientation decides it.

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 5×5 in the plane x = 2; 17 more output cells outside it.
- Timeline: use lever at 1, use lever at 14; markers Closing 1, Closed 13, Opening 14, Opened 40
- Reference states: closed at tick 13, open at tick 40. Fully closed at ticks 8-15; fully open at 0-2, 16-41.
- Pistons by role: door 44, helper 5, power mover 4, power switch 2, stack 2
- How extensions were powered (block giving the signal; QC = through the block above the piston): block←wire 35, block←wire (QC) 8, wire (QC) 5, torch 5, repeater 3, block←torch 2, block←repeater (QC) 2, block←repeater 2, block←repeater+wire 2, redstone_block 2, block←torch+wire 2, repeater (QC) 1, torch (QC) 1
- Phases (bursts of piston events): 3–10 (55 events, 51 pistons); 16–32 (94 events, 56 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
    0      3      5      6      8     16
  .      ~      #      #      #      .
 . .    . .    . .    ~ ~    # #    . .
.   .  ~   ~  #   #  #   #  #   #  .   .
 . .    . .    . .    ~ ~    # #    . .
  .      ~      #      #      #      .

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| south | 7 | 13 | 2×4, 4×3 | south 2 (3), south 1 (4) |
| north | 7 | 13 | 2×4, 4×3 | north 1 (4), north 2 (3) |
| above | 7 | 12 | 2×5, 4×1, 6×1 | up 2 (1), up 1 (5), up 3 (1) |
| below | 4 | 6 | 2×3, 4×1 | down 2 (1), down 1 (3) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| 0 8 -1 S | down | door | 9+7→pulled | block←wire (QC) 1 |
| 0 9 -1 S | down | door | 23+1→pulled | block←wire 2 |
| 0 10 -1 S | down | door | 6+14→pulled, 31+1→pulled | repeater (QC) 1, block←repeater 1 |
| 0 12 -1 S | down | door | 3+13→retracted, 22+2→pulled | block←wire 2 |
| 1 1 -1 S | up | door | 3+17→pulled, 23+None→held | torch (QC) 1, block←repeater (QC) 1 |
| 1 2 -1 S | up | door | 23+1→pulled | torch 1, block←repeater 1 |
| 1 3 -1 S | up | door | 6+10→pulled | block←torch 1 |
| 1 6 -6 S | south | door | 3+17→pulled | block←wire 1 |
| 1 6 -5 S | south | door | 23+1→pulled | wire (QC) 1 |
| 1 6 -4 S | south | door | 6+10→pulled | block←wire (QC) 1 |
| 1 6 2 S | north | door | 6+10→pulled | redstone_block 1 |
| 1 6 3 S | north | door | 23+1→pulled | wire (QC) 1 |
| 1 6 4 S | north | door | 3+17→pulled | block←wire 1 |
| 1 9 -1 S | down | door | 6+10→pulled | block←wire 1 |
| 1 10 -1 S | down | door | 23+1→pulled | block←wire 1 |
| 1 11 -1 S | down | door | 3+17→pulled | block←wire 1 |
| 2 2 -1 S | up | door | 3+13→pulled | torch 1 |
| 2 5 -6 S | south | door | 3+17→pulled | block←wire 1 |
| 2 5 -5 S | south | door | 23+1→pulled | block←wire (QC) 1, repeater 1 |
| 2 5 -4 S | south | door | 6+10→pulled | block←wire 1 |
| 2 5 2 S | north | door | 6+10→pulled | block←wire 1 |
| 2 5 3 S | north | door | 23+1→pulled | block←wire (QC) 1, repeater 1 |
| 2 5 4 S | north | door | 3+17→pulled | block←wire 1 |
| 2 6 -5 S | south | door | 3+13→pulled | block←wire 1 |
| 2 6 3 S | north | door | 3+13→pulled | block←wire 1 |
| 2 7 -6 S | south | door | 3+17→pulled | block←wire 1 |
| 2 7 -5 S | south | door | 23+1→pulled | block←wire (QC) 1, wire (QC) 1 |
| 2 7 -4 S | south | door | 6+10→pulled | block←wire 1 |
| 2 7 2 S | north | door | 6+10→pulled | block←wire 1 |
| 2 7 3 S | north | door | 23+1→pulled | wire (QC) 1 |
| 2 7 4 S | north | door | 3+17→pulled | block←wire 1 |
| 2 10 -1 S | down | door | 3+13→pulled | block←wire 1 |
| 3 2 -2 S | up | door | 3+13→pulled | torch 1 |
| 3 2 0 S | up | door | 3+13→pulled | torch 1 |
| 3 5 -5 S | south | door | 3+13→pulled | block←wire 1 |
| 3 5 3 S | north | door | 3+13→pulled | block←wire 1 |
| 3 7 -5 S | south | door | 3+13→pulled | block←wire 1 |
| 3 7 3 S | north | door | 3+13→pulled | block←wire 1 |
| 3 10 -2 S | down | door | 3+13→pulled | block←wire 1 |
| 3 10 0 S | down | door | 3+13→pulled | block←wire (QC) 1 |
| 4 4 -5 S | south | door | 3+13→pulled | block←torch+wire 1 |
| 4 4 3 S | north | door | 3+13→pulled | block←torch+wire 1 |
| 4 10 -3 S | down | door | 3+13→pulled | block←wire 1 |
| 4 10 1 S | down | door | 3+13→pulled | block←wire 1 |
| 0 12 3 S | down | helper | 5+13→pulled, 22+2→spat | block←wire 2 |
| 1 1 -4 S | up | helper | pulled at 7, 20+None→held | block←wire 1 |
| 1 10 2 S | east | helper | 5+17→retracted, pulled at 24 | block←wire 1 |
| 1 12 -6 S | down | helper | 5+15→pulled, 26+2→spat | block←repeater+wire 2 |
| 3 11 0 S | west | helper | 3+13→pulled | block←wire 1 |
| 0 6 -6 S | south | power mover | pulled at 5, 18+None→held | block←torch 1 |
| 0 6 2 S | north | power mover | 10+6→pulled | block←wire (QC) 1 |
| 0 6 3 S | north | power mover | 23+1→pulled | wire (QC) 1 |
| 4 11 4 S | west | power mover | 3+0→spat, 9+7→pulled | block←wire 2 |
| 0 9 4 S | down | power switch | 7+13→pulled | block←wire 1 |
| 2 10 4 S | east | power switch | pulled at 3, 6+None→held | redstone_block 1 |
| 0 6 4 S | north | stack | 7+13→pulled, 23+None→held | torch 1, block←repeater (QC) 1 |
| 0 11 -1 S | down | stack | 27+1→pulled | block←wire (QC) 1, repeater 1 |

<!-- end generated -->
