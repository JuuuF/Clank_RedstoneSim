# spiral piston door by Purplers

World: `piston_doors/3x3 spiral piston door by Purplers.redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(Hand-written 2026-10-19 from the replay's piston events, `why` traces, `waves` and
`changes` on a copy in `.sandbox/doors/explain/3x3-spiral-piston-door-purplers/`
(`gaps.py` there replays the input gaps); the saved ablation, mechanism and input-sweep
results ([[../robustness]], [[../mechanism]], [[../metrics]], [[../symmetry]]). Every
tick below is from the simulator; what is only read from the maps says so. Not run on
the game server.)

**A showpiece in two layers.** The doorway is the plane x = −1 (cells y 4..6, z −1..1)
and the whole machine stands in that plane and the one behind it (x = 0); only the lever
sticks out at 1 1 3. Box 3 × 8 × 7 = 168 cells, 81 blocks above the floor, 12 pistons
(11 sticky, 1 plain), 20 observers, 3 repeaters, 8 wire. Among the 3x3s only
SacredRedstone's (112 cells, 48 blocks) and the Zhus / monchiCARP pair (126, 51 / 53)
are smaller; for a showpiece it is compact (Lutal's vault: 880 cells, 205 blocks), and
[[../metrics]] lists it as one. Closing takes 19 ticks (lever at 1, all nine cells solid
at 20), opening 21 (lever at 23, open at 44): slower than the plain 3x3s (Zhus 14 / 14,
Mumbo Jumbo 10 / 24), because the cells fill one at a time. All eight orientations
replay identically ([[../symmetry]]). The ablation keeps 70 of the 81 blocks: the 11 that can go
are frame quartz at x = 0 (0 3 −1..1, 0 4 ±2, 0 5 ±2, 0 6 2, 0 7 0) and the two chiseled
corners −1 6 ±2, decoration around the doorway.

**Piston layout.** Nine chiseled quartz blocks are the door; open, they rest in the
frame around the doorway, in the same plane, like Sacred's ring:

- **Seven singles**, one sticky piston per block, one cell out: the top row comes down
  from y = 7 (pistons −1 8 −1, −1 8 0, −1 8 1 facing down), the two north cells come in
  from z = −2 (−1 4 −3, −1 5 −3 facing south), the two south cells from z = 2 (−1 4 3,
  −1 5 3 facing north).
- **The two lower center cells (−1 4 0, −1 5 0) come from below**, the hard cells of a
  flush 3x3 (compare Mumbo Jumbo's). Open, block A rests at −1 3 0 under the center
  column and block B at −1 3 1 beside it. Closing: the sticky piston −1 2 0 (facing up)
  spits A up one (4); the sticky piston −1 3 2 (facing north) slides B under the column,
  −1 3 1 → −1 3 0 (8); −1 2 0 pushes both up together (12: A to −1 5 0, B to −1 4 0).
  Opening: −1 2 0 pulls B down (28), −1 3 2 pulls it back south (32), then A is two cells
  up and out of reach: the **stack** −1 1 0 (sticky, facing up) lifts −1 2 0 to −1 3 0
  (32), the lifted piston pulls A down one (36), the stack takes it back down (40) and it
  pulls A home (44). The same move order as Mumbo Jumbo's center, with a lifted piston
  instead of a second extender stage.
- **A sliding observer** (0 1 −2, facing east): the sticky piston 0 1 0 (facing north)
  pulls it one cell south when closing (6) and pushes it back when opening (26). Where it
  lands decides which direction gets the extra moves (below).
- **An input relay**: the plain piston 0 1 2 (facing up) stands beside the lever's block
  0 1 3 and extends into air at 2, retracts at 24. It moves nothing; its head appearing at
  0 2 2 and vanishing again is what three observers watch (0 2 1 and 0 2 3 look at the
  head cell, −1 1 2 at the piston). Lutal's vault uses the same trick for its stack
  clock ([[3x3-spiral-vault-door-lutal]]).

**The spiral.** Every two ticks one more cell fills, going round the doorway: bottom
center (4), then the south column from the bottom up (−1 4 1 at 6, −1 5 1 at 8, −1 6 1
at 10), the center column (12: the top block comes down, A and B go up), then the north
column from the top down (−1 6 −1 at 14, −1 5 −1 at 16, −1 4 −1 at 18): closed at 20.
Seen from the east that is a loop starting at the bottom, up the south side, over the
top and down the north side, with the center filled on the way. **Opening runs the same
loop, not the reverse**: bottom center (28), south column up (30, 32, 34), center (36),
north column down (38, 40, 42), bottom center last (44). The frames in the facts show
both. The order is the same because every door piston gets one 2-tick pulse per lever
edge from the same chain (below): on the way in it spits the block (extend, drop two
ticks later, the block stays), on the way out the pulse finds the piston retracted and
its block in front, so the extension and the retraction two ticks later pull it back
(the pattern library's "one pulse for both directions", as in Lutal's vault).

**Closing** (lever off → on at 1; ticks from the replay):

| tick | what happens |
|---|---|
| 2 | the lever powers its block 0 1 3; the relay piston 0 1 2 extends, its head appears at 0 2 2 |
| 4 | three observers fire together: 0 2 1 powers the wool 0 2 0 (piston −1 2 0 spits A up to −1 4 0; the slider 0 1 0 extends), 0 2 3 and −1 1 2 start two chains |
| 6 | the slider retracts and pulls the observer 0 1 −2 to 0 1 −1; observer 0 3 3 fires into the note block 0 4 3, which is the conductor beside −1 4 3: it spits −1 4 2 into the doorway |
| 8 | observer 0 5 3 (watching the note block's `powered`) fires into the wire 0 6 3, which quasi-powers −1 5 3 (through the empty cell −1 6 3): spit; observer −1 2 3 fires into the wire −1 3 3: −1 3 2 slides B under the column |
| 10 | observer 0 7 3 (watching the wire 0 6 3) powers the wool 0 8 3; the wires −1 8 3 and 0 8 2 come on; the wool −1 8 2, powered by the wire −1 8 3, powers −1 8 1: it spits the top-south block down |
| 12 | repeater 0 8 1 (1 tick = 2 game ticks) powers the wool 0 8 0: −1 8 0 spits the top-center block down; observer −1 2 1 (end of the chain −1 1 2 → −1 1 3 → −1 2 3 → −1 2 2 → −1 2 1) fires north into −1 2 0: it pushes A and B up together. The same pulse quasi-powers the stack −1 1 0 (−1 2 0 is the cell above it) a moment later; its push fails on the extended piston and nothing happens |
| 14 | repeater 0 8 −1 powers the wool 0 8 −2; the wires −1 8 −2, −1 8 −3 and 0 7 −2 come on: −1 8 −1 spits the top-north block down |
| 16 | observer −1 7 −3 (watching the wire −1 8 −3) quasi-powers −1 5 −3 through −1 6 −3: spit; repeater 0 6 −3, fed through the quartz block 0 6 −2 under the wire 0 7 −2, turns on |
| 18 | observer 0 5 −3 (watching that repeater) powers the wool 0 4 −3: −1 4 −3 spits the last block in |
| 20 | its drop; all nine cells solid (the markers say Closed at 22) |

**Opening** (lever on → off at 23): the relay's head vanishes at 24 and the same three
observers fire at 26, so the chain runs again with the same spacing, two ticks later
than the closing's: −1 2 0 at 26 (pull B down at 28), −1 4 3 at 28 (pull at 30), −1 5 3
and −1 3 2 at 30 (pulls at 32: B goes back to −1 3 1), −1 8 1 at 32, −1 8 0 at 34,
−1 8 −1 at 36, −1 5 −3 at 38, −1 4 −3 at 40 (pull at 42). What the closing did not need
is bringing A down from −1 5 0, and that is the one asymmetric part:

| tick | what happens |
|---|---|
| 26–28 | the slider 0 1 0 pushes the observer back to 0 1 −2 and spits it (lands at 28) |
| 30 | the landed observer fires (R-015): its output cell is the redstone lamp −1 1 −2, which lights, and as a powered block also powers the note block −1 1 −3 beside it |
| 32 | observer −1 1 −1 (watching the lamp) fires south into the stack −1 1 0: it lifts −1 2 0 to −1 3 0; observer −1 2 −3 (watching the note block) fires into the wire −1 3 −3 |
| 34 | observer −1 3 −2 (watching that wire) powers the quartz block −1 3 −1; the lifted piston, landed at 34 beside it, extends at 35 (a landing check) and at 36 pulls A down to −1 4 0 |
| 34–36 | observer −1 2 1 (the chain's end, 2 ticks after the closing's timing) quasi-holds the stack extended; at 36 the stack retracts, ordered before the lifted piston's own retraction in the same tick, so it pulls nothing (an extended piston cannot be moved) and the piston stays at −1 3 0 |
| 36 | the lamp goes out: a lamp turns off 4 ticks after losing power (the pulse into it ended at 32) |
| 38 | observer −1 1 −1 fires again on the lamp going out: the stack extends at 39 (its event, queued when it landed at 38, runs the next tick) and at 40 pulls the piston back down to −1 2 0 |
| 42–44 | the chain −1 3 −2 → 0 3 −2 → 0 2 −2 → −1 2 −2 → −1 2 −1 reaches −1 2 0 at 42: it extends at 43 (landed at 42) and at 44 pulls A home to −1 3 0. Open at 44 |

So the sliding observer is a **direction switch**: pulled south (closing) it lands at
0 1 −1 and its pulse goes into the side of the observer −1 1 −1, which ignores power;
pushed north (opening) it lands at 0 1 −2 and its pulse goes into the lamp. The lamp is
three things at once: the conductor that passes the pulse to the note block (whose
`powered` change starts the pull-A chain), the block whose `lit` change the observer
−1 1 −1 watches, and a delay: its 4-tick turn-off makes the second edge that gives the
stack its second stroke. The note block at the top of the south wall (0 4 3) is the
same double use: a conductor beside a piston and an observable for the observer above
it. (The build's other note block −1 1 −3 is saved as a harp and becomes a bass drum at
its first shape update, tick 32: the one block whose rest state differs from the saved
build, [[../robustness]].)

**The controller is one relay and three observer chains, two ticks per stage.** Every
step of the spiral is 2 ticks because every stage is either an observer (fires 2 ticks
after what it watches changes) or a 1-tick repeater (2 game ticks): the south-wall chain
0 2 3 → 0 3 3 → note block → 0 5 3 → wire → 0 7 3 → repeater 0 8 1 → repeater 0 8 −1 →
wires → observer −1 7 −3 / repeater 0 6 −3 → observer 0 5 −3 serves seven of the ten
door pistons in spiral order (6, 8, 10, 12, 14, 16, 18); the floor chain −1 1 2 → −1 1 3
→ −1 2 3 → −1 2 2 → −1 2 1 serves −1 3 2 (8) and the two-block push (12); the observer
0 2 1 alone serves the first step (4) and the slider. No wire runs more than two cells:
the signal travels by observers watching each other and by powered blocks (eight
wools, the note block, the lamp, one quartz block). The ablation agrees: all 20
observers, all 12 pistons, the lamp, both note blocks, all 8 wires and the 3 repeaters
break the door when removed; the repeaters must be delay 1 (delay 2 on 0 6 −3 only
changes the timing, every other change breaks a step); 9 of the 33 solid blocks break
the door as glass (the lever's block 0 1 3, the wool 0 2 0, the quartz −1 3 −1 and
0 6 −2, the wools 0 4 −3, 0 8 −2, 0 8 0, −1 8 2, 0 8 3: every one a powered block that a
piston or a repeater reads).

**Contract.** The mechanism split ([[../mechanism]]) reads 24 pulses for the 11
mechanism pistons and finds 13 ticks with a retract before an extend; the stripped door
driven by editor pulses differs from tick 10. The replay of the stripped world shows why:
the editor pulse on −1 5 3 (7–9) also quasi-powers the piston directly below it, −1 4 3,
which therefore does not spit at 8 but retracts at 10 and pulls its block back out. That
is the stacked-side-pistons artifact of the split (backlog D4), not a property of the
design: in the original, −1 4 3's power (the note block) and −1 5 3's (the wire 0 6 3,
two cells up) never reach the other piston.

**Input window** ([[../robustness]]: clean at gaps 9–10, stuck at 11, clean from 12).
The opening's first pulse is the observer 0 2 1's, 3 to 5 ticks after the second flip,
into the center piston −1 2 0, and the closing's last use of that piston is the
two-block push at 12 with its drop at 14 (the piston is a moving block from 14 to 16).
Replayed gap by gap (`gaps.py`): at gap 12 the pulse (16–18) begins the tick the piston
lands; it extends at 17 and pulls B down at 18, one tick later than designed, and the
rest follows. At gap 11 the pulse runs 15–17: the piston lands at 16, reads it and queues
its extension, but the event runs at 17 after the pulse has ended (`unpowered`, the
lost-pulse rule of R-026), so B is never pulled down: A and B stay at −1 5 0 and −1 4 0,
the center column stays closed, and no later input repairs it. At gap 10 the pulse
(14–16) arrives at the drop event at 14: the piston finds itself powered again, keeps
its blocks up, and at 16, when the pulse ends, pulls B down as designed. At gap 9 the pulse (13–15) finds the
piston extended since 12 and still powered, so its end at 15 is the pull of B: the
closing's last center step and the opening's first merge, and the door still ends clean.
Gap 11 is the one spacing at which a 2-tick pulse starts inside the target piston's
own 2-tick retraction with one tick left when it lands. The safe gap is 12; the world's
own timeline waits 22.

**Compared with Lutal's vault** ([[3x3-spiral-vault-door-lutal]]): both are showpieces
that give every door piston the same 2-tick observer pulse on both lever edges, both
make the sweep with 2-tick stages (Lutal: 1-tick repeaters; Purplers: observers watching
observers), both put a "clock" piston in front of observers as the input, and both
park the hard block with a lifted piston that extends by a landing check. Lutal turns
two 8-block rings around a lit hub in 14 ticks each way with 19 pistons in 880 cells;
Purplers fills a real 3x3 doorway in 19 / 21 ticks with 12 pistons in 168 cells. Where
Lutal's hub stack has its own observer clock, Purplers' stack is driven by the lamp's
two edges, which only the opening produces.

**Lessons.** (1) A spiral is a sequencing problem: one chain of 2-tick stages, each
stage powering the next door piston, gives any order of cells; the geometry (which
wall each block waits in) is the ordinary flush-3x3 layout. (2) One observer pulse per
piston serves both directions when the pistons are singles (spit in, pull out); only
the move that needs a second reach (A, two cells up) needs direction-specific logic.
(3) A block a piston slides can be the direction switch: a moved observer fires into
whatever stands at its landing cell, a lamp on one side and a deaf observer on the
other. (4) Conductors can be observables: a note block or a lamp passes a signal to the
piston beside it and, by changing state, triggers the observer above it, so one block
does a wire's and a repeater's job. (5) A lamp's 4-tick turn-off is a free second edge.
(6) The input window of a chain-driven door is set by one pair of events: the last
closing use of a piston and the first opening pulse into it; a gap that lands the
pulse's end on the piston's landing is lost (R-026).

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 3×3 in the plane x = -1; 0 more output cells outside it.
- Timeline: use lever at 1, use lever at 23; markers Closing 1, Closed 22, Opening 23, Opened 47
- Reference states: closed at tick 22, open at tick 47. Fully closed at ticks 20-27; fully open at 0-3, 44-47.
- Pistons by role: door 10, fires, moves nothing 1, power mover 1, stack 1
- How extensions were powered (block giving the signal; QC = through the block above the piston): block←observer 7, observer (QC) 4, observer 4, wire 4, bud 2, wire (QC) 2, block←repeater 2, block←wire 2, block←lever 1
- Phases (bursts of piston events): 2–20 (35 events, 12 pistons); 24–44 (43 events, 13 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
  0    4    6    8   10   12   14   16   18   20   28   30   32   34
...  ...  ...  ...  ..~  .~#  ~##  ###  ###  ###  ###  ###  ###  ##.
...  ...  ...  ..~  ..#  .~#  .##  ~##  ###  ###  ###  ###  ##.  ##.
...  .~.  .#~  .##  .##  .~#  .##  .##  ~##  ###  #.#  #..  #..  #..

 35   36   38   40   42   44
##.  #..  ...  ...  ...  ...
##.  #..  #..  ...  ...  ...
#~.  #~.  ##.  ##.  .#.  ...

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| above | 3 | 3 | 2×3 | up 1 (3) |
| below | 2 | 3 | 4×2 | down 2 (1), down 1, south 1 (1) |
| south | 2 | 2 | 2×2 | south 1 (2) |
| north | 2 | 2 | 2×2 | north 1 (2) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| -1 2 0 S | up | door | 4+2→spat, 12+2→spat, 26+2→pulled, 43+1→pulled | block←observer 2, observer 2 |
| -1 3 0 S | up | door | 35+1→pulled | block←observer 1 |
| -1 3 2 S | north | door | 8+2→spat, 30+2→pulled | wire 2 |
| -1 4 -3 S | south | door | 18+2→spat, 40+2→pulled | block←observer 2 |
| -1 4 3 S | north | door | 6+2→spat, 28+2→pulled | bud 2 |
| -1 5 -3 S | south | door | 16+2→spat, 38+2→pulled | observer (QC) 2 |
| -1 5 3 S | north | door | 8+2→spat, 30+2→pulled | wire (QC) 2 |
| -1 8 -1 S | down | door | 14+2→spat, 36+2→pulled | wire 2 |
| -1 8 0 S | down | door | 12+2→spat, 34+2→pulled | block←repeater 2 |
| -1 8 1 S | down | door | 10+2→spat, 32+2→pulled | block←wire 2 |
| 0 1 2 | up | fires, moves nothing | 2+22→retracted | block←lever 1 |
| 0 1 0 S | north | power mover | 4+2→pulled, 26+2→spat | block←observer 2 |
| -1 1 0 S | up | stack | 32+4→retracted, 39+1→pulled, 43+None→held | observer (QC) 2, observer 2 |

<!-- end generated -->
