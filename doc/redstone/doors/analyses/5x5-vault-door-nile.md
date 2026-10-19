# Vault Door by Nile

World: `piston_doors/5x5 Vault Door by Nile [broken sim].redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(Hand-written 2026-10-19 from the replay (`analysis --json`: every piston event with the
blocks it moved and its power), `why` traces, `inspect`, the maps, the state histories of
single cells, and three one-change experiments on copies in
`.sandbox/doors/explain/5x5-vault-door-nile/` (A–C below, README there);
[[../robustness]], [[../mechanism]], [[../representation]], [[../patterns]]. Not run on
the game server for this page; the whole door matched the 26.3 server when it was the
owner's `[broken sim]` report (EXP-068). Positions `x y z`; the lever is pulled at 1 and
at 18. Every tick below is from the simulator; what is only read from the geometry says so.)

**What the player sees.** The doorway is 5 wide and 5 high (x −2..2, y 5..9) seen from
the north, where the lever is (z −4 is open air). Only the outer ring of 16 cells lies in
the wall plane z −3: the 8 cells around the center are one block deeper (z −2) and the
center two blocks deeper (0 7 −1). Closed, the door is a stepped recess: a ring of quartz
standing one block proud of the quartz frame, an inner square flush with the frame, and a
square hole in the middle with the center block at its bottom (the "vault"). All 25 door
blocks are quartz, and the frame around the opening is largely the door's own parked
blocks (the columns x ±3, the rows y 10 and y 4 at z −3), so nothing of the mechanism
shows open or closed except three empty corner cells (−3 10 −3, 3 10 −3, 3 4 −3; read from the maps).
Open, the passage is clear through z −3..0. 425 blocks above the floor (387 after the
trim), box 15×14×5 = 1050 ([[../robustness]], [[../metrics]]); 69 pistons, 66 of them
fire, 27 sticky ones move the 25 door blocks (29 firing positions: the two extender
fronts fire from two cells each).

**The mechanism: four kinds of movement** (all from the move lists of the replay).

- **Ring columns (x ±2, 10 blocks): ten singles.** A sticky piston per row in the wall
  plane (x −4 facing east, x 4 facing west), its block parked one cell out (x ∓3). A
  2-tick pulse *spits* the block in: the piston pushes, loses power while the block is
  still moving, drops its head, and the block lands in the doorway with the piston back
  home ("8+2→spat"). The same 2-tick pulse with the block in extends the piston against
  it and pulls it out ("24+2→pulled"). East at 7 (landed 9), west at 8 (landed 10); out:
  east 24→26, west 25→27. The frame cell between piston and door block is air while the
  door is closed.
- **Ring top row (x −1..1, y 9): three singles from above** (x 11 −3, facing down),
  parked at y 10: spat in at 8, pulled out at 27.
- **The two bottom rows: a honey elevator from below.** Three honey blocks (−1..1 3 −2)
  carry the inner bottom row (x −1..1 4 −2) on top of them; a sticky piston rides on the
  east end (1 2 −2) under the base piston 0 2 −2 (facing up). Tick 5: the base pushes 7
  blocks one up (honey 3→4, inner row 4→5, rider 2→3). The honey at y 4 is now beside
  the ring's bottom row (x −1..1 4 −3) and picks it up: tick 8 the rider, now 1 3 −2,
  pushes 9 blocks (honey, inner row, ring row) one more; inner row at y 6 (z −2), ring row
  at y 5 (z −3), landed 10. Opening: 19 the rider pulls the 9 back down, 22 the base
  pulls 7 (honey, inner row, rider) home.
  Two things must not come along. The frame corners ±2 4 −2 beside the honey's first
  landing row are pulled down to y 3 by the extended sticky pistons ±2 2 −2 at tick 5,
  earlier in the tick's queue than the honey push (events 19–20 against 23), and pushed
  back at 25. And the row of six quartz at y 4, z −3 (x −3..2, the ring's bottom row and
  three frame blocks) is shifted one cell east by the plain piston −4 4 −3 in the same
  tick 22 in which the base pulls the honey down from y 4 (event 10 against 12): a block
  that is still moving is not stuck to honey, so the pull takes only the honey's own three
  quartz and leaves the ring row at y 4; 4 4 −3 shifts the row back at 25.
- **The inner ring's side cells (±1 7 −2): double extenders from the sides**
  (−5 7 −2 and the front −4 7 −2, facing east; 5 7 −2 / 4 7 −2 facing west). Tick 5 the
  base pushes the front piston and the block one cell; tick 8 the front, now at ∓3 7 −2,
  pushes the block into the cell. Opening: 19 the front pulls the block one cell back,
  22 the base pulls the front home, 25 the front extends against the block and 26 pulls it
  the last cell.
- **The inner top row (x −1..1 8 −2) and the center (0 7 −1): a slime elevator from
  above.** Three slime blocks (−1..1 11 −1) with three quartz under them at y 10 (the
  center block and its two neighbours, which end up at ±1 7 −1 as the backing of the
  recess) and two sticky pistons riding on the outer slimes (±1 12 −1), under the base
  piston 0 12 −1 (facing down). Tick 2: the base pushes 8 blocks one down (slime 11→10,
  quartz 10→9, riders 12→11). The slime at y 10 is now beside the inner top row
  (x −1..1 10 −2) and picks it up: tick 5 the west rider, now −1 11 −1, pushes 10 blocks
  (slime, three quartz, inner row, the east rider); tick 8 the east rider, now 1 10 −1,
  pushes 9 (slime, quartz, inner row): center at 0 7 −1, inner row at y 8, landed 10.
  Each stage's pusher is delivered by the stage before it: a self-carrying triple
  extender, 8, 10 and 9 blocks per push. Opening: 19 the east rider pulls 9 up; 22 the
  west rider extends into the gap and 23 pulls 10 (the east rider back to y 11); 24 the
  base extends and 26 pulls 11 (riders home at y 12, slime at 11, center at 10). The
  inner row comes along to y 11, one cell too high, because it is stuck to the slime's
  home row; the three plain pistons x 12 −2 (facing down) push it back to y 10 at 29
  (spat 31). At 13 the same pistons extend into air, harmlessly.
  The path is cleared the same way as below: the quartz beside the slime's first landing
  row (±2 10 −1) are pulled away by ∓4 10 −1 at 2 (pushed back 10, pulled 19, pushed
  27), and the rows of six quartz at y 10 z 0 and at y 4 z −1 are shifted one cell
  sideways while an assembly passes them (−4 10 0 at 4 and 21, back by 4 10 0 at 8 and
  25; −4 4 −1 at 7 and 21, back by 4 4 −1 at 10 and 25): a row that is moving is not taken.
  That is what the 13 "helper" pistons of the facts do.

**Timing.** Lever at 1 → 2 the slime base (and 52 controller events), 4, 5 (slime
rider 1, honey base, extender bases), 7 (east singles), 8 (west and top singles, slime
rider 2, honey rider, extender fronts), landings 9–10: **closed at 10**, nine ticks after
the lever; the controller's last events at 15. Lever at 18 → 19 (66 events: the honey
rider, the slime east rider and the extender fronts pull), 22–23, 24–27 the singles and
the last pulls: **open at 27**, nine ticks after the lever; last events at 31. The markers
say Closed 17 and Opened 34. The east ring runs one tick ahead of the west (7 against 8,
24 against 25); why is below.

**Power: an update, a bounce, and chains of observed moves.** The controller has no
clock and few delays: 40 observers, 14 targets, 9 note blocks, 9 repeaters, 5 hoppers,
4 comparators, 3 copper bulbs, 12 redstone blocks, 5 oak logs with 5 oak leaves, a
barrel, 3 composters, 2 jukeboxes, 4 powered rails, one sand block.

1. **The lever is only an update** (experiment A). It stands on a lime stained glass
   block (−6 10 −3), which conducts nothing. The trigger piston −5 10 −3 (facing up)
   beside the glass is quasi-connected to the wire −6 11 −3 on top of the glass, and that
   wire is powered all the time by the redstone block −5 11 −3 standing in front of the
   piston. A flip of the lever updates the glass block's neighbours, the piston notices
   the power it always had and pushes the redstone block up. Built with the lever in the
   other position, the run is identical in every block at every tick except the lever
   itself. So the input is an edge with no polarity, and the mechanism must know by
   itself whether it is open or closed: the singles do (spit when out, pull when in), the
   elevators do by where their riders stand.
2. **The bounce, a pulse inside one tick.** Within tick 2 the trigger pushes the block to
   −5 12 −3, loses its own power the moment the block has left −5 11 −3, drops the push
   (the block lands at once), and −5 13 −3 (facing down, powered through the target
   −5 14 −2 by the wire the raised block feeds) pushes it straight back and drops it too:
   the block is at y 12 for part of one tick and home at the tick's end (its cell never
   changes at a tick boundary). In that moment the wire network at y 12–14 (−5 12 −2 …
   −2 14 −2, −6 13 0, −5 14 −1) is on, every piston it reaches queues an extension, and
   by the time their events run the power is gone: they push and drop. All of it is in
   tick 2 (52 piston events): a redstone block spat from −3 12 0 to −2 12 0, a target
   from 1 14 −2 to 2 14 −2 (it lands beside the powered rails 3 14 −2 / 4 13 −2, which is
   where the east side starts: inferred from the maps and the `effects` list), an oak log
   from −7 11 0 to −7 10 0, and on the east side the mirror bounce: 5 13 −2 pushes the
   east block 5 12 −2 down to 5 11 −2 and 5 9 −2 pushes it back up together with the sand
   block 5 10 −2 under it. The sand lands on the raised block's cell (y 11 at 4), falls
   off by itself when the cell under it is empty (gone at 8, landed back at 5 10 −2 at 14;
   again 25 → 31), so each cycle finds the same stack: a self-resetting spacer. What the
   spacer is for is not determined; replacing it with glass, which does not fall, breaks
   the door ([[../representation]]).
3. **From there, moves are the clock.** A pushed block lands 2 ticks after its event, an
   observer that sees it fires 2 ticks later for 2 ticks, and the stages are built from
   that (all traced with `why`):
   - *West ring:* the log spat to −7 10 0 (2) → observer −7 10 −1 (4) → observer
     −7 10 −2 (6) → its output through the wool −7 10 −3 into the wire −7 9 −3 → the
     copper bulb −6 9 −3 turns on (6) → observer −5 9 −3, which watches the bulb, fires
     (8) → −4 9 −3 and, by quasi-connectivity, −4 8 −3 spit at 8 (traced); the three
     lower singles fire at 8 as well, through the wire −5 7 −3 and the wool −5 6 −3,
     whose own feed was not traced. The observer's 2-tick pulse is what makes a spit. The
     bulb's `powered` goes off again at 8 when the upstream pulse ends, and the observer,
     turning on in that same tick, gives one pulse only (the pulse table: 8+2). Opening: the same chain from the
     log pulled back at 19: bulb at 23, observer 25, singles pull at 27.
   - *East ring:* a log spat to 7 9 −1 (2) → the oak leaves 6 9 −1 recompute their
     distance one tick later (3, `distance` 7 → 1) → observer 6 9 −2, which watches the
     leaves, fires (5) → bulb 6 9 −3 on (5) → observer 5 9 −3 (7) → 4 9 −3 and 4 8 −3 at
     7 (traced; the lower three fire at 7 through the wool 4 6 −2 fed by the observer
     5 6 −2 and the wire 5 7 −3, not traced). Leaves next to a moved log are a one-tick stage; a second observer would be two:
     that is the east side's one-tick lead.
   - *Top row:* the east bounce's wire 4 11 −2 / 3 11 −2 toggles the copper bulb 2 11 −2
     within tick 2 (`lit` false → true; it stays lit until the next bounce) → observers
     2 11 −3 (4), 2 12 −3 (6), 1 12 −3 (8) → the wire 0 12 −3 → the three top pistons
     at 8 (two of them by quasi-connectivity). The bulb turns a pulse that is over within
     the tick into a lasting state change; its `lit` bit is also a memory (lit while
     closed), but nothing reads it except observers, which fire on both edges anyway.
   - *Honey base 0 2 −2 at 5:* the redstone block −7 6 0 pushed down at 2 (landed 4)
     powers the wires −7 4 0 → −6 3 0 → −5 2 0 → the piston −4 3 0 (4), which spits a
     redstone block from −3 3 0 to −2 3 0 at 5 (its own conductor, the target −4 2 0, is
     pulled away by −2 2 0 in the same tick) → wires −1 3 0, 0 2 0 → the target 0 2 −1 →
     the base extends at 5.
   - *Extender bases at 5:* a wool pushed down into −4 7 0 at 2 (landed 4), the output
     cell of the repeater −5 7 0 (fed from the bounce through the wire −6 8 0 and the
     note block −6 7 0): the wool powers the wire −4 7 −1 → the target −5 7 −1 → −5 7 −2.
     The same wire powers the quartz −3 7 −1 beside the front piston's landing cell: the
     front lands at 7 and extends at 8 by itself (landing check).
   - *Riders:* the west slime rider −1 11 −1 at 5 through the jukebox −2 11 −1 (a
     conductor) from the wires −2 12 −1 / −2 11 −2 that the redstone block spat to
     −2 12 0 powers; the honey rider 1 3 −2 at 8 through the jukebox 1 3 −1 from the wire
     2 3 −1; the east slime rider 1 10 −1 at 8 by quasi-connectivity from the redstone
     block that 3 11 0 pushes to 1 11 0 at 5. That piston is itself quasi-connected to the
     oak log that 1 13 0 pushes to 3 13 0 at 2 (landed 4), the output cell of the
     comparator 3 13 −1, which reads the barrel 3 13 −2 (one stack of levers: signal 1).
     **Carried power:** the log matters only where the piston puts it; where it lands it
     is a powered block, the note block 3 12 0 under it turns on at 4, and that change is
     the update the quasi-connected piston below needs ([[../patterns]] "Carried power",
     found by the glass counterfactual of [[../representation]]).
4. **Indicators, conductors, constant sources.** Note blocks, hoppers (`enabled` flips
   when they are powered), copper bulbs and powered rails are used as blocks whose state
   changes with power: observers watch them, and a note block's flip updates the
   quasi-connected piston under it. Targets and jukeboxes are conductors that wire runs
   into (Lutal's vault uses targets the same way). The comparators read composters and
   the barrel: constant signals whose output cells are switched by moving a conductor
   into them (the logs at −7 10 0 and 3 13 0: "power switches"). The nine repeaters are
   fine delays (1–3): 5 4 −2 (delay 2) times the bottom-row shifters at 10 and 25.
5. **A built-in input lockout.** The plain piston −6 12 −3 (facing east, "fires, moves
   nothing") extends at 4 and its head sits in −5 12 −3, the cell the trigger pushes
   into, until 14 (and 21–31 in the opening). It is held by three sources in turn (state
   histories): the observer −6 13 −3 above it (4–6), the wool −7 12 −3 west of it,
   powered by the observer −7 13 −3 (6–8), and the repeater −6 12 −2 behind it (delay 3,
   8–14): the bounce's pulse of tick 2 reaches the repeater's input, and a repeater whose
   input pulse is shorter than its delay turns on anyway one delay later and off one
   delay after that (`why`: "scheduled a tick for 8", "for 14"). While the head is
   there the trigger's push cannot resolve, and since a flip is only an update, the flip
   is lost. The trigger is also a moving block at ticks 2–3 (its own head coming back
   after the drop), so flips then are lost too. That is the whole input window of
   [[../robustness]]: the flips at 2–13 (gaps 1–12) do nothing, the door finishes closing
   and stays closed, and the next flip opens it (the sweep's "works again"); from the flip
   at 14, the tick the head withdraws (gap 13), the door opens normally; the no-overlap
   gap (16) is not needed. Experiments B (gap 12) and C (gap 2) show the closed door after
   the ignored flip. The D11 line of [[../robustness]] ("no piston event differs; a
   controller state is left") holds only for the events that happen: the opening
   sequence's 186 events are missing (11 events after the flip, none after 15), and what is
   left is the closed door with its controller in the closed state (195 blocks differ from
   the open rest state). This is the one dataset door that ignores an early input instead
   of jamming; the price is that a flip during the lockout is lost, not queued (compare the
   project's `door_3x3`, [[../demonstration]], whose lockout holds the input).

**Mechanism and controller** ([[../mechanism]]). The stripped door (29 piston positions,
48 pulses) differs from tick 8: the west slime rider never fires at 5 and the honey rider
not at 8 — no event at all, not a failed one — because the helpers that clear the
assemblies' paths count as controller and are removed: with the quartz −2 10 −1 left in
place (the original pulls it away at 2) the slime at y 10 is stuck to it and the rider's
push does not resolve; the honey's corners the same. The mechanism page's reason for this
door (redstone blocks riding in the slime assemblies) is not what the moves show: no
redstone block is ever part of a slime or honey push here; the riders are pistons, and
their power comes from outside. For D4: the path-clearing helpers (∓4 10 −1, ±2 2 −2, the
four row shifters) belong to the mechanism. The same-tick "retract, then extend" ticks 22,
24 and 29 are the row shifts and pulls above: at 22 the shifter's push must run before the
base's pull.

**Against Purplers' sliding door** ([[4x4-sliding-piston-door-purplers]]), the other
slime door: both move conductors and redstone blocks in spit chains inside one tick, clear
an assembly's neighbours before it moves (pulled away or set moving earlier in the same
tick), carry pistons for the next stroke, relay updates through note blocks and switch
constant comparator sources by moving a conductor. Purplers' halves are 24-block
assemblies at the 12-block limit moved sideways in two strokes; Nile's are 7–11 blocks
moved vertically in two and three strokes with riders, and pick up their outer rows on the
way. Purplers' controller has no delay component; Nile's has nine repeaters and uses
leaves, bulbs, hoppers and rails as indicators. Purplers' door is faster (9 and 4 ticks
against 9 and 9) and smaller (401 blocks, box 880, against 425 and 1050), Nile's has the
lockout (safe at every gap, where Purplers' jams below 9).

**Lessons.** (1) **A lever can be nothing but an update:** on a non-conducting block next
to a quasi-connected piston, each flip starts the machine whatever the lever's level
(experiment A); the input is then an edge, and the mechanism's own state decides what the
edge means. (2) **A bounced redstone block is a pulse shorter than a tick:** pushed and
pushed back within one tick, it powers a network for a moment and every piston on it
spits; a repeater on that network stretches the moment to its delay. (3) **Slime and
honey collect what they pass:** the elevators pick up their outer rows on the way, and
everything else that would stick is pulled away or set moving, earlier in the same tick,
before the assembly moves. (4) **Observed moves are the clock:** landings seen by
observers, leaves recomputing their distance one tick after a log arrives, a note block
flipping under a landed powered log; the east ring's one-tick lead is a leaves stage
against an observer stage. (5) **A piston head across the trigger's path is an input
lockout:** early flips are ignored instead of jamming the door.

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 5×5 in the plane z = -3; 9 more output cells outside it.
- Timeline: use lever at 1, use lever at 18; markers Closing 1, Closed 17, Opening 18, Opened 34
- Reference states: closed at tick 17, open at tick 34. Fully closed at ticks 10-18; fully open at 0-6, 27-36.
- Pistons by role: door 29, fires, moves nothing 10, helper 13, idle 3, power mover 16, power switch 3
- How extensions were powered (block giving the signal; QC = through the block above the piston): block←wire 19, wire 17, target 15, wire (QC) 14, observer 12, block←wire (QC) 8, block←observer (QC) 8, target (QC) 7, block←observer 7, redstone_block (QC) 6, observer (QC) 5, redstone_block 4, block←repeater 3, block←comparator (QC) 2, bud 2
- Phases (bursts of piston events): 2–15 (160 events, 69 pistons); 19–31 (179 events, 71 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
    0      7      8      9     10     19     26     27
.....  ....~  ~~~~~  ~~~~#  #####  #####  ####.  .....
.   .  .   ~  ~   ~  ~   #  #   #  #   #  #   .  .   .
.   .  .   ~  ~   ~  ~   #  #   #  #   #  #   .  .   .
.   .  .   ~  ~   ~  ~   #  #   #  #   #  #   .  .   .
.....  ....~  ~~~~~  ~~~~#  #####  #...#  #....  .....

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| above | 7 | 9 | 2×3, 6×4 | up 3 (1), up 2 (3), up 1 (3) |
| west | 6 | 8 | 2×5, 4×1 | west 2 (1), west 1 (5) |
| east | 6 | 8 | 2×5, 4×1 | east 2 (1), east 1 (5) |
| below | 6 | 4 | 4×6 | down 2 (3), down 1 (3) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| -5 7 -2 S | east | door | 5+17→pulled | target 1 |
| -4 4 -3 | east | door | 22+2→spat | block←observer 1 |
| -4 5 -3 S | east | door | 8+2→spat, 25+2→pulled | block←wire (QC) 2 |
| -4 6 -3 S | east | door | 8+2→spat, 25+2→pulled | block←wire 2 |
| -4 7 -3 S | east | door | 8+2→spat, 25+2→pulled | wire 2 |
| -4 7 -2 S | east | door | 25+1→pulled | wire (QC) 2 |
| -4 8 -3 S | east | door | 8+2→spat, 25+2→pulled | observer (QC) 2 |
| -4 9 -3 S | east | door | 8+2→spat, 25+2→pulled | observer 2 |
| -3 7 -2 S | east | door | 8+11→pulled | block←wire 1 |
| -1 11 -3 S | down | door | 8+2→spat, 25+2→pulled | wire (QC) 2 |
| -1 11 -1 S | down | door | 5+14→retracted, 22+1→pulled | block←wire 2 |
| -1 12 -2 | down | door | 13+2→spat, 29+2→spat | wire (QC) 2 |
| 0 2 -2 S | up | door | 5+17→pulled | target 1 |
| 0 11 -3 S | down | door | 8+2→spat, 25+2→pulled | wire 2 |
| 0 12 -2 | down | door | 13+2→spat, 29+2→spat | wire 2 |
| 0 12 -1 S | down | door | 2+17→retracted, 24+2→pulled | block←wire 1, observer (QC) 1 |
| 1 3 -2 S | up | door | 8+11→pulled | block←wire 1 |
| 1 10 -1 S | down | door | 8+11→pulled | redstone_block (QC) 1 |
| 1 11 -3 S | down | door | 8+2→spat, 25+2→pulled | wire (QC) 2 |
| 1 12 -2 | down | door | 13+2→spat, 29+2→spat | wire (QC) 2 |
| 3 7 -2 S | west | door | 8+11→pulled | block←wire 1 |
| 4 4 -3 | west | door | 10+4→retracted, 25+4→retracted | block←repeater 2 |
| 4 5 -3 S | west | door | 7+2→spat, 24+2→pulled | block←observer (QC) 2 |
| 4 6 -3 S | west | door | 7+2→spat, 24+2→pulled | block←observer 2 |
| 4 7 -3 S | west | door | 7+2→spat, 24+2→pulled | wire 2 |
| 4 7 -2 S | west | door | 25+1→pulled | block←observer 1 |
| 4 8 -3 S | west | door | 7+2→spat, 24+2→pulled | observer (QC) 2 |
| 4 9 -3 S | west | door | 7+2→spat, 24+2→pulled | observer 2 |
| 5 7 -2 S | west | door | 5+17→pulled | target 1 |
| -6 12 -3 | east | fires, moves nothing | 4+10→retracted, 21+10→retracted | observer 2 |
| -5 1 -1 | up | fires, moves nothing | 5+14→retracted | block←wire 1 |
| -5 10 -2 | south | fires, moves nothing | retracted at 2, 5+14→retracted, 22+None→held | redstone_block (QC) 2 |
| -5 14 -3 | west | fires, moves nothing | 2+0→spat, 19+0→spat | target 2 |
| -3 11 -3 | west | fires, moves nothing | 8+2→spat, 25+2→spat | observer 2 |
| 4 11 -1 | south | fires, moves nothing | 5+14→retracted | wire 1, target (QC) 1 |
| 5 9 -1 | down | fires, moves nothing | 2+0→spat, 10+2→spat, 19+0→spat, 25+2→spat | block←wire 2, block←observer (QC) 2 |
| 5 14 -2 | south | fires, moves nothing | retracted at 2, 5+14→retracted, 22+None→held | target 2 |
| 6 11 0 | down | fires, moves nothing | 2+0→spat, 19+0→spat | target 2 |
| 7 11 -2 | down | fires, moves nothing | 2+0→spat, 19+0→spat | wire (QC) 2 |
| -7 9 -1 S | east | helper | 2+17→pulled | block←comparator (QC) 1 |
| -6 2 -1 S | north | helper | 5+14→pulled | block←wire 1 |
| -4 4 -1 | east | helper | 7+2→spat, 21+2→spat | block←observer 2 |
| -4 9 0 S | down | helper | 2+17→pulled | wire 1 |
| -4 10 -1 S | east | helper | 2+0→pulled, 10+2→spat, 19+0→pulled, 27+2→spat | block←wire (QC) 2, bud 2 |
| -4 10 0 | east | helper | 4+2→spat, 21+2→spat | block←observer (QC) 2 |
| -2 2 -2 S | up | helper | pulled at 5, 25+None→held | target 1 |
| 2 2 -2 S | up | helper | pulled at 5, 25+None→held | redstone_block 1 |
| 4 4 -1 | west | helper | 10+5→retracted, 25+4→retracted | block←repeater 1, target 1 |
| 4 9 0 S | down | helper | 2+17→pulled, 22+1→spat, 26+1→pulled | wire 3 |
| 4 10 -1 S | west | helper | 2+0→pulled, 10+2→spat, 19+0→pulled, 27+2→spat | block←wire 2, observer 2 |
| 4 10 0 | west | helper | 8+11→retracted, 25+2→spat | block←wire (QC) 1, block←observer 1 |
| 7 11 -1 S | down | helper | 2+0→spat, 19+0→pulled | wire 2 |
| -7 7 0 S | down | power mover | 2+17→pulled | block←wire 1 |
| -5 10 -3 S | up | power mover | 2+0→spat, 19+0→spat | wire (QC) 2 |
| -5 13 -3 S | down | power mover | 2+0→spat, 19+0→spat | target (QC) 2 |
| -4 3 0 S | east | power mover | 5+0→spat, 11+8→pulled | target 2 |
| -4 12 0 S | east | power mover | 2+0→spat, 19+0→pulled | block←wire 2 |
| -2 2 0 S | west | power mover | pulled at 5, 8+11→pulled, 22+None→held | redstone_block 1, redstone_block (QC) 1 |
| 0 3 0 S | east | power mover | 5+14→pulled | wire 1 |
| 0 14 -2 S | east | power mover | 2+0→spat, 19+0→pulled | target 2 |
| 1 2 -3 S | west | power mover | pulled at 5, 22+None→held | redstone_block 1 |
| 2 1 -3 S | west | power mover | 5+14→pulled | block←wire (QC) 1 |
| 3 11 0 S | west | power mover | 5+14→pulled | block←comparator (QC) 1 |
| 5 2 -2 S | west | power mover | pulled at 5, 22+None→held | redstone_block 1 |
| 5 9 -2 | up | power mover | 2+0→spat, 5+1→spat, 19+0→spat, 22+1→spat | redstone_block (QC) 2, block←observer (QC) 2 |
| 5 13 -2 S | down | power mover | 2+0→spat, 19+0→spat, 22+None→held | target (QC) 4 |
| 6 1 -2 S | west | power mover | 5+14→pulled | block←wire (QC) 1 |
| 7 6 0 S | down | power mover | 2+17→pulled | block←wire (QC) 1 |
| -7 4 -3 S | east | power switch | 12+2→spat, 27+2→pulled | observer 2 |
| -7 12 0 S | down | power switch | 2+0→spat, 19+0→pulled | block←wire 2 |
| 1 13 0 S | east | power switch | 2+17→pulled | wire 1 |

<!-- end generated -->
