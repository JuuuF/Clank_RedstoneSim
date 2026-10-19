# Glass Piston Door by ashevoy

World: `piston_doors/5x5 Glass Piston Door By ashevoy.redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(Hand-written 2026-10-20 from the replay's piston events (`events.py` in
`.sandbox/doors/explain/5x5-glass-piston-door-ashevoy/`, a condensed log), `why` traces,
the stripped build of [[../mechanism]], the input sweep of [[../robustness]] and one
one-change experiment (A below); [[../metrics]], [[../patterns]], [[../symmetry]]. Every
tick is the simulator's; what is only inferred from the geometry says so. Not run on the
game server.)

**A flush, all-glass 5x5.** The doorway is the plane x = 0 (cells y 11..15, z −4..0);
closed, all 25 cells are glass. (The 26th output cell, −1 10 −1, is a floor block west of
the doorway that never changes in the run.) Open, the 25 glass blocks are out of sight: 15
under the floor and in the floor row (the centre columns z −3..−1), 10 in the walls one
cell east of the doorway plane (the side columns, at x = 1, z −6 and z 2). The walls
(quartz pillars at z −5 and z 1), the lintel (y 16) and the floor (y 10) are *themselves
moving parts*: the pillars are pulled aside and used as pusher extensions, the lintel's
middle is pushed down into the doorway on the way open, and the floor row slides four
cells. That is what the size buys: a 15×23×25 box (8625 cells), 1954 blocks above the
ground, 760 logic components, 171 pistons (the dataset's most: 98 "door" pistons by
firing position, 33 stacks, 27 helpers, 22 power movers, 8 power switches, 21 that never
fire), a lever on the floor eight cells west (−8 11 −2). Closes in 36 ticks (lever at 1,
all 25 cells solid at 37), opens in 37 (lever at 43, the last glass gone at 62, the last
quartz back in the lintel at 80). Direction-independent: 8 of 8 orientations
([[../symmetry]]).

**Four mechanisms, one timing primitive.** The door blocks are moved by *chains of
carried pushers*: n pistons in a row; the first pushes the whole line (the other pushers
included) one cell; the next pusher, carried onto a cell beside a powered block, extends
one tick after it lands (a landing check, [[../patterns]]), and so on: one cell every 3
ticks (2 of travel, 1 for the landing check), each pusher that fired left behind. The
stages' power blocks are switched on by the controller as the stages arrive (repeater
chains of delay 1 along the lines; wires timed to the tick), so in the designed run the
controller's timing and the landing checks give the same ticks, and which one the builder
relied on cannot be told from the run.

1. *The floor conveyor* (y 10, three columns x 0..2, both directions). Each column is a
   line of exactly 12 movable blocks between a four-pusher chain at z 8, 7, 6, 5 (facing
   north) and one at z −6, −8, −10, −12 (facing south): 3 carried pushers, 1 quartz, 3
   glass (x 0 and x 1) or 3 sticky pistons (x 2), and the 5 floor blocks of the doorway
   (z 0..−4). Closing: pushes at 2, 5, 8, 11 (the first through the target 0 9 8 on the
   lever's line, the next three through the blocks under the carried pushers, fed by the
   repeaters 0 9 7, 0 9 5, 0 9 3; the same at x 1 and x 2); the floor glass arrives under
   the doorway (0 10 −3..−1, 1 10 −3..−1) and the x = 2 sticky pistons beside it at 11;
   the floor quartz is pushed on north, and the four south-facing pushers ahead of it are
   compacted into a block at z −12..−9. Opening: the same southwards at 68, 71, 74, 77
   (target 0 9 −12, repeaters at z −11, −9, −7).
2. *The shuttle and the lift.* Three sticky pistons built at −1 9 −3..−1 (facing up) are
   pushed under the floor cells (0 9) at 4 by the pushers −3 9 (a 6-block line: a quartz,
   the shuttle, the glass of y 9, three quartz; spit at 6) and pushed back at 22 by the
   pushers 5 9 (spit at 24). There they are powered by the quartz beside them (−1 9),
   powered in turn by an observer bank (below): at 16 they push the floor glass up into
   the doorway's bottom row (spit at 18: the first three closed cells). At 20 the x = 2
   sticky pistons push the x = 1 floor glass west into the emptied floor cells (spit 22).
   Then the *lift*: four plain pistons stacked at 0 1..4 in each column z −3..−1, the
   bottom one powered at 26 by the wire line at y 2 (x = −1): it pushes 10 blocks up (the
   3 pistons above it, a glass filler, the floor quartz, and the glass of y 7, 8, 9, 10,
   11) and spits at 28; the piston it carried to 0 3 fires at 29 (9 blocks), the next at
   32 (8), the last at 35 (7). The column rises four cells in 9 ticks, the centre is
   closed at 37, and the floor quartz built at 0 6 is now the floor under the door
   (0 10). The stages' power blocks (−1 1, −1 3, −1 5 under the wires at y 2, 4, 6; the
   target −1 7) come on at 26, (not traced), 32 and 34: in step with the ladder.
3. *The side columns* (z −4 and z 0, five cells each): a double extender per row at x =
   0 (rear sticky pistons at z −8 / 4, fronts at z −7 / 3) that uses the *frame pillar*
   (quartz at z −5 / 1) as a spacer, and a slider (plain pistons at x = 3 and x = −2)
   that moves a three-block line, a target, the glass and a quartz, between x = 2 and
   x = −1. Closing, north side (the south side mirrors it): 11 the fronts extend into
   the empty cell z −6; 13 they retract and pull the pillar out (−5 → −6); 17 the x = 3
   pushers slide the glass from the wall (1 y −6) into 0 y −6 and the pillar out to x =
   −1 (spit 19); 20 the fronts push the glass to −5 (spit 21); 23 the x = −2 pushers put
   the pillar back at 0 y −6 (spit 25); 27 the fronts push glass and pillar together:
   glass at −4, pillar at −5 (spit 29; the columns are closed from 29). Opening: 46/48
   the fronts out and the pillar pulled to −6; 50/52 the x = −2 pistons pull the pillar
   to x = −1; 56 the rears push the fronts to −6 (the double extender; the south rears at
   54, four of them dropping back at 56 with the fronts spat in place); 59/60 the fronts
   pull the glass to −5 (both sides open from 60); 64 the rears pull the fronts back;
   67/68 the fronts pull the glass to −6; 72 the x = −2 pushers slide pillar, glass and
   target back east (spit 74); 76 the fronts push the pillar home (spit 78). Power: the
   fronts from a blue-wool-and-wire column at x = −1 (−1 12 −7: an observer at −1 11 −7
   and two wires; the y 11 front through quasi-connectivity), the x = 3 pushers from
   blue wool and wires at x = 4 (an observer at 4 11 −6), the rears from cyan wool under
   wires at z −9 / 5, the x = −2 pushers from blue wool at x = −3.
4. *The lintel stack* (the opening's centre): four sticky pistons facing down at
   0 17..20 above the lintel quartz 0 16 (z −3..−1). At 44 (one tick after the flip, by a
   wire line along y 22/23 over the door to the wool 0 21 −3) the top one pushes the
   whole centre column down one cell, 11 blocks (3 pistons, the lintel quartz, the 5 door
   glass, the floor quartz, the filler glass) into the cell the lift's top head left at
   40; the stages carried to 0 18, 0 16 and 0 14 fire at 47 (the wire 0 19 −4 through
   quasi-connectivity), 50 (the quartz 0 16 −4 under the wire 0 17 −4, on at 50) and 53
   (the quartz 1 15 beside the cell above it, powered by the pressed observer, below).
   Each push takes the lift's retracted pistons down with it (one at 47, two at 50,
   three at 53): after four pushes the lift is compacted back to 0 1..4, the filler, the
   floor quartz and the glass of y 7..9 are where they were built, and the column reads
   "closed" though it holds, from the top, a head, the lowest stage, its head, the lintel
   quartz and the two floor-row glass blocks (tick 55: `show x=0`). The stack then
   climbs home in extend-and-pull strokes (56, 60, 63/64, 65, 68, 71/72, 75/76, 79/80),
   the lintel quartz rising at 56, 64, 72 and 80, while the two floor-row glass blocks
   leave sideways: 58 the x = 2 sticky pistons (extended at 56) pull the x = 1 block
   east; 58 the shuttle is pushed under the column again, 61 it extends into the
   emptied floor cell, 62 it pulls the last glass down into the floor; 70 it is pushed
   back; 68–77 the conveyor returns everything south. The doorway is clear of glass at
   62 and fully open at 80, when the lintel is whole again.

**The observer press** (x = 1, y 17–18) is the costliest timing element: two rows of
three (observers at 1 17 −6..−4, output down; sticky pistons facing down at 1 18 −6..−4
over glass) are slid three cells south during the closing by carried pushers (12, 15, 18
at y 17 and at y 18; 18 pistons in all, powered through quasi-connectivity from wool
under the repeaters of a chain at 2 18 −9..−5), which stacks the pistons over the
observers above the doorway's x = 1 edge. In the opening the press fires: 48 the pistons
(fed by repeaters at 2 18 −3..−1) push the observers down to 1 16 and the quartz under
them to 1 15 (spit 50); the observers pulse on landing (52–53, R-015) into the quartz
1 15, which quasi-powers the stack's stage at 0 14 (53); 60 the pistons extend again,
and the observers pulse a second time (62–63; inferred: they watch the cell the head
enters) for the stage at 0 15 (63); 66 they are pulled back up; 70, 73, 76 the rows
slide home; 79–80 the y 17 sticky pistons lift the quartz back into the lintel (1 16),
in the tick the x = 0 lintel is restored.

**Moving observers are the clock.** The door's one-shot pulses are observers moved by
pistons (R-015: a pushed observer pulses 2 ticks after landing; [[../patterns]] "moving
power sources"; the census counts 56 observer moves here): the bank of four at
−1 8 −4..−1 is pushed south at 12 (lands 14, pulses 16: the shuttle's push) and north at
56 (lands 58, pulses 60–62: the shuttle, landed at 60, fires at 61); the bank at 2 8 at
16 (pulse 20: the x = 2 pistons) and 52 (pulse 56); single observers are lifted or slid
at 5 (−5 10 −8 and −5 10 4), 8, 18, 22, 50, 60, 64, 70, 72, 74, 78, 82. The rest of the
controller: the lever's edge is turned into moved blocks in its first tick (2: four
redstone blocks pushed by sticky pistons at −9 6 9, −5 8 7, −3 21 11 and −6 9 −4, wool
blocks at −6 4 0, −2 3 8, 2 23 6, a target pulled at −1 20 11), all returned at 44;
repeater chains of delay 1 along the conveyors (y 9) and the press (y 18); target blocks
as wire-fed conductors at the heads of lines (33 extensions); detector rails pushed and
pulled at 66–78 (−3 17, −3 19) whose purpose is not traced; two pistons (−4 19 −4 and
−4 19 0) fire into air at 70.

**What the second flip must wait for** ([[../robustness]]: safe gap 38, no-overlap 41,
designed 42). The lift's last piston (0 7) retracts at tick 40 (flip + 39) and the lintel
stack's top stage fires one tick after the second flip. At gap 38 both run in tick 40:
the retraction's block event runs first and frees 0 8 (a retracting piston's head cell
is air at once), the push follows with its 11 blocks. At gap 37 the push is due at 39
with the head still in 0 8, so no event is queued; when the stages are next updated (42)
the third stage (0 18) fires first with 9 blocks and the two above it fail on it
("immovable sticky piston at 0 18", R-027): the stack is split, six glass blocks stay in
rows y 12–13 (`gap37.redsim.json`); one more flip recovers the door. So the safe gap is
the lift's last retraction less the stack's one tick of lead, and the three ticks
between 38 and the no-overlap gap are the lift's heads finishing a retraction the
stack's first push does not need.

**Experiment A** (`exp_a_floor_line_13.redsim.json`): a quartz block at 0 10 −5, the free
cell at the north end of the x = 0 floor line. The first pusher (0 10 8) never fires (its
line is 13); the second (0 10 6, a line of 12 again) fires at 4 and the third at 7, the
x = 0 line is shifted twice instead of four times, and quartz instead of glass is carried
into the doorway's middle column: the frames still read "closed" at 42 (a solid cell is a
solid cell) and 7 floor cells end differently. The 12-block lines are exact, and the
door's closed state is only all glass when every line moves its full four cells.

**Why the stripped door differs from tick 16** ([[../mechanism]]). The mechanism /
controller split keeps a piston at the cell it fires from; the shuttle fires at
0 9 −3..−1 but is *built* at −1 9: in the stripped build that cell is air, the pushers of
tick 4 move one quartz, and the pulse at 16 finds glass where the piston should be, so
the bottom row never rises. A mechanism piston that is carried into place must be kept
at its build cell (the refinement D4 asks for slime-carried parts, for carried pistons
too). The 11 same-tick "retract, then extend" ticks (12, 16, 18, 22, 50, 54, 56, 58, 68,
72, 76) are the carried-pusher chains and the shuttle: a pusher retracts in the tick the
next one fires, on independent cells, so they do not constrain the contract.

**Against Purplers' vault lamp door** (the other 5x5, [[5x5-vault-lamp-door-purplers]],
[[../metrics]]): 57 pistons, 373 blocks, a 660-cell box, closed in 7 ticks and open in 2,
safe gap 10, but a funnel of visible wool whose 25 cells lie five planes deep, and it
jams in 2 of 8 orientations. ashevoy's door pays 171 pistons, 1954 blocks and 36 / 37
ticks for a doorway that is one flat plane of glass with nothing visible around it: all
25 blocks leave through the floor and the walls, the pillars, lintel and floor are the
mechanism, and nothing depends on orientation.

**Lessons.** (1) *Carried pushers in series* turn one power line into a 3-tick-per-cell
sequence: a row of n pistons pushes a line n cells with no timing circuit beyond
"power the cell each one lands on" (landing checks, R-025 / R-026); the lift, the lintel
stack, both conveyors and the press rows are all this one primitive. (2) *The frame is a
moving part*: a pillar pulled out and pushed back in is a free extension block for a
two-cell push by a one-cell piston; the lintel's middle is the opening's pusher head; the
floor row is a shift register of exactly 12 blocks. (3) *A stack that pushes a column
down also repacks the ladder that pushed it up*: the four down-pushes carry the lift's
retracted pistons back into their compact column, so the closing's lift and the opening's
drop share one column and nothing resets it. (4) *Moved observers are the clock*: every
one-shot pulse is an observer pushed or pulled, including a press that pulses twice (on
landing, and when a head enters its view); it costs 18 pistons for two pulses, and the
user a 38-tick gap.

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 5×5 in the plane x = 0; 1 more output cells outside it.
- Timeline: use lever at 1, use lever at 43; markers Closing 1, Closed 42, Opening 43, Opened 101
- Reference states: closed at tick 42, open at tick 101. Fully closed at ticks 37-43, 46, 49, 52, 55; fully open at 0-15, 80-115.
- Pistons by role: door 98, fires, moves nothing 2, helper 27, idle 21, power mover 22, power switch 8, stack 33
- How extensions were powered (block giving the signal; QC = through the block above the piston): wire 55, block←wire 54, block←repeater 40, target 33, block←wire (QC) 27, wire (QC) 25, block←observer 15, repeater (QC) 13, observer 12, repeater 8, target (QC) 7, block←observer+wire (QC) 6, block←observer+wire 6, block←repeater (QC) 6, redstone_block 3, redstone_block (QC) 3, block←observer (QC) 3, comparator 1, bud (QC) 1, bud 1
- Phases (bursts of piston events): 2–40 (305 events, 103 pistons); 44–84 (499 events, 161 pistons); 88–90 (4 events, 4 pistons); 98–98 (1 events, 1 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
    0     16     18     26     27     28     29     31     32     34
.....  .....  .....  .....  ~...~  ~...~  #...#  #...#  #...#  #...#
.....  .....  .....  .....  ~...~  ~...~  #...#  #...#  #~~~#  #####
.....  .....  .....  .....  ~...~  ~...~  #~~~#  #####  #~~~#  #####
.....  .....  .....  .~~~.  ~~~~~  ~###~  #~~~#  #####  #~~~#  #####
.....  .~~~.  .###.  .~~~.  ~~~~~  ~###~  #~~~#  #####  #~~~#  #####

   35     37     44     46     47     49     50     52     53     55
#~~~#  #####  #~~~#  #####  #~~~#  #####  #~~~#  #####  #####  #####
#~~~#  #####  #~~~#  #####  #~~~#  #####  #~~~#  #####  #####  #####
#~~~#  #####  #~~~#  #####  #~~~#  #####  #~~~#  #####  #~~~#  #####
#~~~#  #####  #~~~#  #####  #~~~#  #####  #~~~#  #####  #~~~#  #####
#~~~#  #####  #~~~#  #####  #~~~#  #####  #~~~#  #####  #~~~#  #####

   56     58     60     62     63     64     66     68     71     72
#####  #####  .~~~.  .###.  .###.  .~~~.  .###.  .....  .~~~.  .~~~.
#~~~#  #####  .....  .....  .~~~.  .~~~.  .###.  .###.  .###.  .....
#~~~#  #####  .###.  .###.  .###.  .....  .....  .....  .....  .....
#...#  #...#  .....  .....  .....  .....  .....  .....  .....  .....
#####  #####  .###.  .....  .....  .....  .....  .....  .....  .....

   74     80
.###.  .....
.....  .....
.....  .....
.....  .....
.....  .....

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| below | 15 | 52 | 8×6, 12×3, 18×6 | down 4, east 1, south 4 (3), down 5, south 4 (3), down 4 (9) |
| above | 6 | 18 | 6×3, 8×3 | stays (6) |
| north | 5 | 20 | 6×5 | east 1, north 2 (5) |
| south | 5 | 20 | 6×5 | east 1, south 2 (5) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| -3 9 -3 | east | door | 4+2→spat, 58+2→spat | target 2 |
| -3 9 -2 | east | door | 4+2→spat, 58+2→spat | target 2 |
| -3 9 -1 | east | door | 4+2→spat, 58+2→spat | target 2 |
| -2 11 -6 S | east | door | 23+2→spat, 50+2→pulled, 72+2→spat | block←wire (QC) 3 |
| -2 11 2 S | east | door | 23+2→spat, 50+2→pulled, 72+2→spat | block←wire (QC) 3 |
| -2 12 -6 S | east | door | 23+2→spat, 50+2→pulled, 72+2→spat | block←wire 3 |
| -2 12 2 S | east | door | 23+2→spat, 50+2→pulled, 72+2→spat | block←wire 3 |
| -2 13 -6 S | east | door | 23+2→spat, 50+2→pulled, 72+2→spat | wire 3 |
| -2 13 2 S | east | door | 23+2→spat, 50+2→pulled, 72+2→spat | wire 3 |
| -2 14 -6 S | east | door | 23+2→spat, 50+2→pulled, 72+2→spat | wire (QC) 3 |
| -2 14 2 S | east | door | 23+2→spat, 50+2→pulled, 72+2→spat | wire (QC) 3 |
| -2 15 -6 S | east | door | 23+2→spat, 50+2→pulled, 72+2→spat | wire 3 |
| -2 15 2 S | east | door | 23+2→spat, 50+2→pulled, 72+2→spat | wire 3 |
| 0 1 -3 | up | door | 26+2→spat | block←wire 1 |
| 0 1 -2 | up | door | 26+2→spat | block←wire 1 |
| 0 1 -1 | up | door | 26+2→spat | block←wire 1 |
| 0 3 -3 | up | door | 29+1→spat | block←wire 1 |
| 0 3 -2 | up | door | 29+1→spat | block←wire 1 |
| 0 3 -1 | up | door | 29+1→spat | block←wire 1 |
| 0 5 -3 | up | door | 32+4→retracted | block←wire 1 |
| 0 5 -2 | up | door | 32+4→retracted | block←wire 1 |
| 0 5 -1 | up | door | 32+4→retracted | block←wire 1 |
| 0 7 -3 | up | door | 35+5→retracted | target 1 |
| 0 7 -2 | up | door | 35+5→retracted | target 1 |
| 0 7 -1 | up | door | 35+5→retracted | target 1 |
| 0 9 -3 S | up | door | 16+2→spat, 61+1→pulled | block←observer 2 |
| 0 9 -2 S | up | door | 16+2→spat, 61+1→pulled | block←observer 2 |
| 0 9 -1 S | up | door | 16+2→spat, 61+1→pulled | block←observer 2 |
| 0 10 -12 | south | door | 68+8→retracted | target 1 |
| 0 10 -10 | south | door | 71+7→retracted | block←repeater 1 |
| 0 10 -8 | south | door | 74+6→retracted | block←repeater 1 |
| 0 10 -6 | south | door | 77+5→retracted | block←repeater 1 |
| 0 10 2 | north | door | 11+3→retracted, 50+6→retracted | block←repeater 2 |
| 0 10 4 | north | door | 8+4→retracted, 48+6→retracted | block←repeater 2 |
| 0 10 6 | north | door | 5+5→retracted, 46+6→retracted | block←repeater 2 |
| 0 10 8 | north | door | 2+7→retracted, 44+6→retracted | target 2 |
| 0 11 -7 S | south | door | 11+2→pulled, 20+1→spat, 27+2→spat, 46+2→pulled, 67+1→pulled, 76+2→spat | block←observer+wire (QC) 2, block←wire (QC) 4 |
| 0 11 -6 S | south | door | 59+1→pulled | target (QC) 1 |
| 0 11 2 S | north | door | 58+2→pulled | target (QC) 1 |
| 0 11 3 S | north | door | 11+2→pulled, 20+1→spat, 27+2→spat, 46+2→pulled, 67+1→pulled, 76+2→spat | block←observer+wire (QC) 2, block←wire (QC) 4 |
| 0 12 -7 S | south | door | 11+2→pulled, 20+1→spat, 27+2→spat, 46+2→pulled, 67+1→pulled, 76+2→spat | block←observer+wire 2, block←wire 4 |
| 0 12 -6 S | south | door | 59+1→pulled | target 1 |
| 0 12 2 S | north | door | 58+2→pulled | target 1 |
| 0 12 3 S | north | door | 11+2→pulled, 20+1→spat, 27+2→spat, 46+2→pulled, 67+1→pulled, 76+2→spat | block←observer+wire 2, block←wire 4 |
| 0 13 -7 S | south | door | 11+2→pulled, 20+1→spat, 27+2→spat, 46+2→pulled, 67+1→pulled, 76+2→spat | wire 6 |
| 0 13 -6 S | south | door | 59+1→pulled | target (QC) 1 |
| 0 13 2 S | north | door | 58+2→pulled | target (QC) 1 |
| 0 13 3 S | north | door | 11+2→pulled, 20+1→spat, 27+2→spat, 46+2→pulled, 67+1→pulled, 76+2→spat | wire 6 |
| 0 14 -7 S | south | door | 11+2→pulled, 20+1→spat, 27+2→spat, 46+2→pulled, 67+1→pulled, 76+2→spat | wire (QC) 6 |
| 0 14 -6 S | south | door | 59+1→pulled | target 1 |
| 0 14 -3 S | down | door | 53+3→pulled | block←observer (QC) 1 |
| 0 14 -2 S | down | door | 53+3→pulled | block←observer (QC) 1 |
| 0 14 -1 S | down | door | 53+3→pulled | block←observer (QC) 1 |
| 0 14 2 S | north | door | 58+2→pulled | target 1 |
| 0 14 3 S | north | door | 11+2→pulled, 20+1→spat, 27+2→spat, 46+2→pulled, 67+1→pulled, 76+2→spat | wire (QC) 6 |
| 0 15 -7 S | south | door | 11+2→pulled, 20+1→spat, 27+2→spat, 46+2→pulled, 67+1→pulled, 76+2→spat | wire 6 |
| 0 15 -6 S | south | door | 59+1→pulled | target (QC) 1 |
| 0 15 -3 S | down | door | 63+1→pulled, 68+None→held | block←wire (QC) 2, block←observer 1 |
| 0 15 -2 S | down | door | 63+1→pulled, 68+None→held | block←wire (QC) 2, block←observer 1 |
| 0 15 -1 S | down | door | 63+1→pulled, 68+None→held | block←observer 1, block←wire (QC) 1 |
| 0 15 2 S | north | door | 58+2→pulled | target (QC) 1 |
| 0 15 3 S | north | door | 11+2→pulled, 20+1→spat, 27+2→spat, 46+2→pulled, 67+1→pulled, 76+2→spat | wire 6 |
| 0 16 -3 S | down | door | 50+10→pulled, 71+1→pulled | block←wire 2 |
| 0 16 -2 S | down | door | 50+10→pulled, 71+1→pulled | block←wire 2 |
| 0 16 -1 S | down | door | 50+10→pulled, 71+1→pulled | block←wire 2 |
| 0 17 -3 S | down | door | 68+0→pulled, 79+1→pulled | wire 2 |
| 0 17 -2 S | down | door | 68+0→pulled, 79+1→pulled | wire 2 |
| 0 17 -1 S | down | door | 68+0→pulled, 79+1→pulled | wire 2 |
| 0 18 -3 S | down | door | 47+18→pulled, 75+1→pulled | wire (QC) 1, observer 1 |
| 0 18 -2 S | down | door | 47+18→pulled, 75+1→pulled | wire (QC) 1, observer 1 |
| 0 18 -1 S | down | door | 47+18→pulled, 75+1→pulled | wire (QC) 1, observer 1 |
| 0 20 -3 S | down | door | 44+24→pulled | block←wire 1 |
| 0 20 -2 S | down | door | 44+24→pulled | bud 1 |
| 0 20 -1 S | down | door | 44+24→pulled | block←wire 1 |
| 1 10 -12 | south | door | 68+8→retracted | target 1 |
| 1 10 -10 | south | door | 71+7→retracted | block←repeater 1 |
| 1 10 -8 | south | door | 74+6→retracted | block←repeater 1 |
| 1 10 -6 | south | door | 77+5→retracted | block←repeater 1 |
| 1 10 2 | north | door | 11+3→retracted, 50+6→retracted, 59+3→retracted | block←repeater 2, target (QC) 1 |
| 1 10 4 | north | door | 8+4→retracted, 48+6→retracted | block←repeater 2 |
| 1 10 6 | north | door | 5+5→retracted, 46+6→retracted | block←repeater 2 |
| 1 10 8 | north | door | 2+7→retracted, 44+6→retracted | target 2 |
| 2 10 -3 S | west | door | 20+2→spat, 56+2→pulled | block←observer 2 |
| 2 10 -2 S | west | door | 20+2→spat, 56+2→pulled | block←observer 2 |
| 2 10 -1 S | west | door | 20+2→spat, 56+2→pulled | block←observer 2 |
| 3 11 -6 | west | door | 17+2→spat | block←observer+wire (QC) 1 |
| 3 11 2 | west | door | 17+2→spat | block←observer+wire (QC) 1 |
| 3 12 -6 | west | door | 17+2→spat | block←observer+wire 1 |
| 3 12 2 | west | door | 17+2→spat | block←observer+wire 1 |
| 3 13 -6 | west | door | 17+2→spat | wire 1 |
| 3 13 2 | west | door | 17+2→spat | wire 1 |
| 3 14 -6 | west | door | 17+2→spat | wire (QC) 1 |
| 3 14 2 | west | door | 17+2→spat | wire (QC) 1 |
| 3 15 -6 | west | door | 17+2→spat | wire 1 |
| 3 15 2 | west | door | 17+2→spat | wire 1 |
| 5 9 -3 | west | door | 22+2→spat, 70+2→spat | target 2 |
| 5 9 -2 | west | door | 22+2→spat, 70+2→spat | target 2 |
| 5 9 -1 | west | door | 22+2→spat, 70+2→spat | target 2 |
| -4 19 -4 | south | fires, moves nothing | 70+8→retracted | block←wire 1 |
| -4 19 0 | north | fires, moves nothing | 70+8→retracted | block←wire 1 |
| -6 4 0 S | up | helper | 2+42→pulled | block←wire 1 |
| -6 13 -11 S | north | helper | 5+39→pulled | target 1 |
| -6 13 7 S | south | helper | 5+39→pulled | target 1 |
| -6 15 3 S | up | helper | 68+22→pulled | repeater (QC) 1 |
| -6 21 6 S | up | helper | 60+24→pulled | repeater (QC) 1 |
| -5 18 2 S | up | helper | 58+22→pulled | block←wire 1 |
| -5 23 1 S | north | helper | 74+24→pulled | repeater 1 |
| -4 6 9 S | south | helper | 6+42→pulled | block←repeater 1 |
| -4 17 2 S | east | helper | 68+22→pulled | comparator 1 |
| -4 22 -8 S | east | helper | 52+24→pulled | repeater (QC) 1 |
| -3 17 -4 S | east | helper | 66+6→pulled | block←wire 1 |
| -3 17 -3 S | east | helper | 66+6→pulled | block←wire 1 |
| -3 17 0 S | east | helper | 66+6→pulled | block←wire 1 |
| -3 19 -4 S | east | helper | 70+8→pulled | block←wire (QC) 1 |
| -3 19 -1 S | east | helper | 70+8→pulled | block←wire (QC) 1 |
| -3 19 0 S | east | helper | 70+8→pulled | block←wire (QC) 1 |
| -3 21 3 S | east | helper | 62+22→pulled | block←repeater 1 |
| -2 3 8 S | south | helper | 2+42→pulled | wire 1 |
| -2 4 4 S | up | helper | pulled at 14, 56+None→held | repeater (QC) 1 |
| -2 7 -13 S | up | helper | pulled at 18, 60+None→held | repeater (QC) 1 |
| 0 4 7 S | up | helper | pulled at 4, 46+None→held | block←wire 1 |
| 1 20 -8 S | up | helper | 44+11→pulled | block←wire 1 |
| 2 17 7 S | up | helper | 64+24→pulled | repeater (QC) 1 |
| 2 20 1 S | up | helper | 66+24→pulled | repeater (QC) 1 |
| 2 23 6 S | west | helper | 2+42→pulled | block←wire 1 |
| 4 17 -9 S | up | helper | 8+42→pulled | repeater (QC) 1 |
| 5 4 -10 S | up | helper | pulled at 26, 68+None→held | repeater (QC) 1 |
| -9 6 9 S | east | power mover | 2+0→spat, 8+36→pulled | block←wire 2 |
| -6 3 -5 S | up | power mover | 8+42→pulled | block←wire 1 |
| -6 9 -4 S | north | power mover | 2+42→pulled | wire 1 |
| -6 19 -2 S | down | power mover | 74+8→pulled | repeater (QC) 1 |
| -5 8 7 S | east | power mover | 2+42→pulled | block←wire 1 |
| -5 10 -8 S | east | power mover | 5+39→pulled | block←wire 1 |
| -5 10 4 S | east | power mover | 5+39→pulled | block←wire 1 |
| -5 22 -3 S | east | power mover | 70+8→pulled | wire 1 |
| -3 2 -5 S | south | power mover | 22+42→pulled | repeater 1 |
| -3 21 11 S | east | power mover | 2+0→spat, 8+36→pulled | target 2 |
| -1 8 -5 | south | power mover | 12+2→spat | block←wire 1 |
| -1 8 1 | north | power mover | 56+6→retracted | wire 1 |
| -1 20 11 S | west | power mover | pulled at 2, 5+39→pulled, 47+None→held | redstone_block 1, redstone_block (QC) 1 |
| -1 22 4 S | down | power mover | 44+24→pulled | block←wire 1 |
| 0 23 -4 S | north | power mover | 44+0→spat, 50+18→pulled | block←wire 2 |
| 1 18 -3 S | down | power mover | 48+2→spat, 60+6→pulled | repeater 2 |
| 1 18 -2 S | down | power mover | 48+2→spat, 60+6→pulled | repeater 2 |
| 1 18 -1 S | down | power mover | 48+2→spat, 60+6→pulled | repeater 2 |
| 2 8 -5 | south | power mover | 16+2→spat | block←repeater 1 |
| 2 8 1 | north | power mover | 52+6→retracted | block←wire 1 |
| 3 18 3 S | north | power mover | 72+6→pulled | block←repeater 1 |
| 5 2 -7 S | up | power mover | 18+42→pulled | wire 1 |
| -7 5 9 S | west | power switch | pulled at 2, 5+39→pulled, 47+None→held | redstone_block 1, redstone_block (QC) 1 |
| 0 22 -6 S | south | power switch | pulled at 44, 47+21→pulled, 71+None→held | redstone_block 1, redstone_block (QC) 1 |
| 1 8 -3 S | up | power switch | 28+2→spat, 50+2→pulled | observer 2 |
| 1 8 -2 S | up | power switch | 28+2→spat, 50+2→pulled | observer 2 |
| 1 8 -1 S | up | power switch | 28+2→spat, 50+2→pulled | observer 2 |
| 1 17 -3 S | down | power switch | 79+1→pulled | repeater (QC) 1 |
| 1 17 -2 S | down | power switch | 79+1→pulled | repeater (QC) 1 |
| 1 17 -1 S | down | power switch | 79+1→pulled | repeater (QC) 1 |
| 0 11 -8 S | south | stack | 56+8→pulled | block←wire (QC) 1 |
| 0 11 4 S | north | stack | 54+10→pulled | block←wire (QC) 1 |
| 0 12 -8 S | south | stack | 56+8→pulled | block←wire 1 |
| 0 12 4 S | north | stack | 54+2→retracted, pulled at 64 | block←wire 1 |
| 0 13 -8 S | south | stack | 56+8→pulled | wire 1 |
| 0 13 4 S | north | stack | 54+2→retracted, pulled at 64 | wire 1 |
| 0 14 -8 S | south | stack | 56+8→pulled | wire (QC) 1 |
| 0 14 4 S | north | stack | 54+2→retracted, pulled at 64 | wire (QC) 1 |
| 0 15 -8 S | south | stack | 56+8→pulled | wire 1 |
| 0 15 4 S | north | stack | 54+2→retracted, pulled at 64 | wire 1 |
| 0 19 -3 S | down | stack | 71+1→pulled | block←wire (QC) 1, observer 1 |
| 0 19 -2 S | down | stack | 71+1→pulled | bud (QC) 1, observer 1 |
| 0 19 -1 S | down | stack | 71+1→pulled | observer 1 |
| 1 17 -9 | south | stack | 12+4→retracted | block←repeater (QC) 1 |
| 1 17 -7 | south | stack | 15+3→retracted | block←repeater (QC) 1 |
| 1 17 -5 | south | stack | 18+4→retracted | block←repeater (QC) 1 |
| 1 17 1 | north | stack | 76+6→retracted | block←repeater (QC) 1 |
| 1 17 3 | north | stack | 73+5→retracted | block←repeater (QC) 1 |
| 1 17 5 | north | stack | 70+6→retracted | block←repeater (QC) 1 |
| 1 18 -9 | south | stack | 12+4→retracted | block←repeater 1 |
| 1 18 -7 | south | stack | 15+3→retracted | block←repeater 1 |
| 1 18 -5 S | down | stack | 18+4→retracted, 50+15→retracted | block←repeater 1, block←wire (QC) 2 |
| 1 18 1 | north | stack | 76+6→retracted | block←repeater 1 |
| 1 18 3 | north | stack | 73+5→retracted | block←repeater 1 |
| 1 18 5 | north | stack | 70+6→retracted | block←repeater 1 |
| 2 10 -12 | south | stack | 26+7→retracted, 68+8→retracted | target 2 |
| 2 10 -10 | south | stack | 29+6→retracted, 71+7→retracted | block←repeater 2 |
| 2 10 -8 | south | stack | 32+5→retracted, 74+6→retracted | block←repeater 2 |
| 2 10 -6 | south | stack | 35+4→retracted, 77+5→retracted | block←repeater 2 |
| 2 10 2 S | west | stack | 11+3→retracted, 53+3→retracted | block←repeater 2 |
| 2 10 4 | north | stack | 8+4→retracted, 50+4→retracted | block←repeater 2 |
| 2 10 6 | north | stack | 5+5→retracted, 47+5→retracted | block←repeater 2 |
| 2 10 8 | north | stack | 2+7→retracted, 44+6→retracted | target 2 |

<!-- end generated -->
