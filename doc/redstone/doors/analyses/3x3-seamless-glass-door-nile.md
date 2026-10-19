# Seamless Glass Door by Nile

World: `piston_doors/3x3 Seamless Glass Door by Nile` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(Hand-written 2026-10-19 from the replay's piston events, `why` chains, `show` maps and
the two-cycle replay, on a copy in `.sandbox/doors/explain/3x3-seamless-glass-door-nile/`
(`events.txt` lists every event with what it moved); [[../symmetry]], [[../robustness]],
[[../mechanism]], [[../representation]]. Positions `x y z`; the lever (5 16 −1, on the
lime concrete 5 16 −2) is used at 1 and at 46. Not run on the game server here; the
door's two cycles (EXP-073) and its two origins (EXP-070) were.)

**Seamless.** The doorway is 3×3 glass in the wall plane z = −3 (cells x 0..2, y 8..10),
framed by quartz and cyan concrete. Nothing in that plane ever shows a piston: closed,
the opening is glass; open, it is air with quartz above (y 11) and below (y 7), the same
blocks as the frame. Every piston stands in the three door columns themselves, above
the lintel (y 12..16) and under the floor line (y 1..6; the import's floor is at y = 0, so
the design's ground level, y = 7, is inferred from the geometry), and the wiring is in the
two planes behind and in front of the wall (z = −4 and z = −2). Box 8×16×4 = 512, 252
blocks above the floor, 35 pistons (18 sticky), 27 observers, 7 note blocks, 6 repeaters,
4 redstone blocks ([[../metrics]]). Built **closed**; it opens in 39 ticks (open at 40,
marker 45) and closes in 33 (closed at 79, marker 83).

**The column (geometry).** Each door column x = 0, 1, 2 at z = −3 is one stack of blocks
that a piston moves as a whole. Closed, from the bottom: a plain piston facing up (y 4),
air (y 5), a sticky piston facing down (y 6, "A"), quartz (y 7, "a"), the three glass
blocks (y 8..10), quartz (y 11, "b"), quartz (y 12, "c"), three sticky pistons facing
down (y 13..15, "B", "C", "D") and a plain piston facing down (y 16). The door opens by
**shifting the stack four cells down** and closes by shifting it back up; what makes it
seamless is that the quartz blocks a and b move with the glass and always end at the
floor line and the lintel. Open, from the bottom: the plain piston (y 1), A (y 2), a (y 3),
the glass (y 4..6), b (y 7), air (y 8..10), c (y 11), B, C, D (y 12..14), air, the top piston
(y 16). The pistons in the stack are its own movers: each is carried into position by the
push before it and then pushes or pulls itself (a self-carrying stack; [[../patterns]]
"Extenders").

**Opening** (lever on at 1; ticks from the replay, the column x = 0 stands for all three,
which run identically):

| tick | what happens |
|---|---|
| 2 | the lever's block powers the sticky pistons 5 15 −2 (directly) and 5 14 −2 (quasi-connectivity, QC); they push two observers one cell north (5 15 −3 → −4 facing east, 5 14 −3 → −4 facing up; landed at 4) and hold them there until the lever goes off |
| 6 | the moved observer 5 15 −4 pulses (R-015: 2 ticks after landing) into 4 15 −4; the slider 4 16 −4 (facing west) pushes the row of three observers 1..3 16 −4 (facing north) one cell west to 0..2 16 −4 (landed 8) |
| 10 | the three observers pulse into the top pistons 0..2 16 −3: each pushes its whole stack down one cell (10 blocks: A, a, the glass, b, c, B, C, D). At 12 the pulse ends and the pistons spit (the head is withdrawn, the blocks land at 12) |
| 14 | the observer 4 16 −3 saw the slider move (8) and the repeater 4 16 −2 (delay 2) turns on at 12; the observer 3 16 −2 watching it pulses at 14 into the wire row y 16 at z = −2 (2 16 −2 at 15 down to −1 16 −2 at 12), which powers the concrete row y 15 under it. D (now at 0 14 −3) is powered by QC through 0 15 −2 and gets its **update from the helper piston −1 15 −3**, whose head appears beside it in the same tick; D pushes 10 blocks (the plain piston at y 4 is now in contact and goes along). The slider −1 16 −4 pushes the observer row back east at the same time (their second pulse at 18 fires the top pistons into air: harmless) |
| 16 | the row goes off; D spits |
| 18 | the vertical observer chain at x = 4, z = −2 (4 15 −2 watches the repeater, 4 14 −2 watches 4 15 −2, both facing up) reaches the observer 3 14 −2, which pulses into the wire row y 14; C (at 0 12 −3) is powered by QC through 0 13 −2 and updated by the helper −1 13 −3; C pushes 9 blocks and spits at 20 |
| 20–21 | 4 13 −2 fires the note block 4 12 −2 (a BUD: its `powered` flag changes at 18) and the observer 3 12 −2 watching the note block pulses into the wire row y 12 at 20; B (at 0 10 −3) is QC-powered through 0 11 −2 and is updated by the quartz block b landing under it at 20, so it extends at **21** (one tick after the landing, R-026) and pushes the lower 8 blocks: the stack is four cells down, but b (y 7), c (y 8) and B's head (y 9) and B (y 10) are still in the doorway |
| 24 | B retracts (its row went off at 22; its update is its own head landing at 23) and pulls c up 8 → 9 |
| 26–28 | the helper 1 12 −4 (facing west, behind the wall) spits the white stained glass 0 12 −4 one cell west (below); the glass turning into a moving block beside the three C pistons is **their update** (`why` at 26): C (y 12), QC-powered by the row y 14 again, extends into air at 26 and at 28 retracts, pulling B up 10 → 11 |
| 30–32 | D (y 14) extends at 30 and pulls C up 12 → 13 at 32; B (y 11) extends at 31 and pulls c up 9 → 10 at 32 |
| 35–36 | C (y 13) extends and pulls B up 11 → 12 |
| 39–40 | B (y 12) extends and at 40 pulls c up 10 → 11: the doorway is empty. (C's extension at 39 fails: B below it is extended, an immovable block, R-027.) |

So the opening is four pushes (10, 14, 18, 21) that bring the glass under the floor line,
then five one-cell pulls (24, 28, 32, 36, 40) in which the three sticky pistons B, C, D
walk themselves and the quartz block c back up out of the doorway. The pulls ride on
later pulses of the same three rows (y 14 at 26, 35 and 39, y 16 at 30, y 12 at 31; the
power of each extension is in the facts table), which the observer chain produces from
the edges of its earlier pulses, with the helper plain pistons −1 15 −3 and −1 13 −3 and
the sliders giving the quasi-connected pistons their updates.

**Closing** (lever off at 46):

| tick | what happens |
|---|---|
| 47 | 5 15 −2 and 5 14 −2 retract and pull the two observers back south (landed 49) |
| 51 | the observer 5 14 −3 (facing up) pulses into 5 13 −3; the piston 5 13 −2 pushes the **x = 5 column** (glass 5 5..12 with redstone blocks at 5 4 and 5 9) one cell down (spit at 53): the lower redstone block now powers the wire 5 3 −3 / 5 3 −4 and the upper one the note block 5 8 −3 |
| 53 | the observer 5 2 −2 sees the column move and fires the piston 4 1 −2 (QC-powered by the redstone block 4 3 −2): it lifts the **x = 4 pair of redstone blocks** (4 3, 4 4 −2) and the glass under them one cell. From here 4 1 −2 (up, at 53, 59, 65, 71, 77) and 4 6 −2 (down, at 56, 62, 68, 74, 80) shuttle the pair up and down every 3 ticks: a piston clock of period 6 made of a moved power source ([[../patterns]] "Moving power sources"). Each stroke blanks the wire 3 4 −2 for the 2 ticks of the move and so pulses the long wire that runs from it along z = −2 |
| 54 | the redstone block standing at 5 3 −2 since 53 lights the wire row y 2 at z = −4 and the plain pistons 0..2 1 −3 queue their extension; at 54 the piston 5 1 −2 pushes the x = 5 column back up, the row drops, and the pistons push the lower six blocks up (A, a, the glass, b) and withdraw their heads in the same tick (a push with no hold, "spat" in the facts); the blocks land at 56 and b fills the bottom doorway row |
| 55–57 | the upper redstone block (now 5 8 −2) powers the note block 5 8 −3, the observer 4 8 −3 fires the note block 3 7 −3, and the sticky piston 3 7 −2 (QC through 3 8 −3) pulls the concrete 3 5 −2 up to 3 6 −2 at 57 (and pushes it back at 75–77): a conductor moved into place for the lower rows |
| 59 | the wire row y 4 at z = −4 pulses: A (0..2 3 −3, facing down) extends **and** retracts within tick 59 and the retraction pulls the plain piston below it up one, 1 → 2 (landed 61). The plain pistons' own extension events in the same tick fail ("moving block", "unpowered") |
| 62 | landed at 61 next to the concrete 0 2 −2 (powered by the wire 0 3 −2, fed from the clock's wire 3 4 −2 at 61), the plain piston extends by itself (landing check) and pushes six blocks up; the first glass row lands in the doorway at 64; it retracts at 65 |
| 68 | A (y 4) pulls the plain piston up 2 → 3 (the row y 4 again; the plain pistons' extensions fail on the moving A) |
| 71 | the plain piston (y 3) pushes six blocks up and spits |
| 74 | A (y 5) pulls the plain piston up 3 → 4 |
| 77 | the plain piston (y 4) pushes the nine blocks above it (a, the glass, b, c, B, C, D) up one and spits; the glass lands in y 8..10 at **79**: closed. 80 is the clock's last stroke |

The closing is an **inchworm**: push the stack up one (the plain piston, from y 1, 2, 3, 4
at 54, 62, 71, 77), then let A, the sticky piston riding at the bottom of the stack,
extend and retract in one tick to pull the plain piston up after it (59, 68, 74), and
repeat. The plain piston and A end where they were built (y 4 and y 6); B, C, D ride back
up to y 13..15 with the last push.

**Power access.** 87 of the 117 extensions are powered through a solid block (under a
wire, or in front of a repeater, an observer or the lever) and 41 by quasi-connectivity: the pistons sit inside the wall, so the wall's
own blocks are the conductors and the wires run on top of alternating rows at z = −2
(wires at y 3, 5, 12, 14, 16 on blocks at y 2, 4, 11, 13, 15) and z = −4 (wires at y 2,
4, 6 on blocks at y 1, 3, 5). A sticky piston in the stack is powered by QC from the row
beside the cell above it, and because QC power gives no update, every such piston has an
update source arranged for it: a helper plain piston whose head lands beside it (−1 15 −3,
−1 13 −3, the sliders), a block of its own stack landing under it (B at 20, the plain
pistons at 61), or its own head finishing (B at 23). [[../representation]] found the
same thing from the other side: a glass change in this door is predicted only with
mid-tick reads, because a piston landing at 58 is updated while one block alone powers
it and the other source arrives later in the tick without an update.

**Why it alternates between two rest states** ([[../robustness]], EXP-073). The sticky
piston 1 12 −4 (facing west) gets the same 2-tick observer pulse every opening (26–28,
from 2 12 −4 ← 3 12 −4 ← the note block 3 11 −4 ← the repeater 4 11 −3 at 22). In the
first cycle the white stained glass 0 12 −4 is in front of it: the push moves it to
−1 12 −4 and the retraction, coming while the pushed block is still moving, is a *drop*
(the game's event type 2), which never pulls: a spit. In the second cycle (the two-cycle
world, `two_cycles.redsim.json`: events at 131 and 133) the cell in front is air, the
piston extends into it, and the retraction is a *contract* (type 1), which pulls the
block beyond the head: the glass comes back to 0 12 −4. One pulse, two outcomes,
decided by what stands in front. The door does not depend on where the glass is: the
helper's job is the update it gives the C pistons at 26 (a moving block appearing
beside them, the pushed glass in one cycle, the head alone in the other), and the
white glass in front of it is a leftover of the build (inferred: it powers nothing in
either cell).

**Why it is location-dependent** ([[../symmetry]], EXP-070): the copies differ from tick
59 (the orientations) or 66 (the second origin) for 12–14 ticks and all close on time.
Tick 59 is the densest tick of the run: in every column A extends and retracts, the
plain piston at y 1 queues an extension that fails, and 2 1 −2 and 4 1 −2 fire as well,
eleven events whose order comes from the hash-ordered update sets; the order changes
which failures happen, not where the blocks end. The three quartz blocks 0..2 12 −3
that [[../representation]] lists as stoppers are the cells c was built in: at 39 the
cell holds B, extended, and C's extension fails on it; the failure is counted at the cell,
the stopper is B.

**The controller, and why the stripped door differs from tick 10** ([[../mechanism]]).
The timing elements are the observers: the two lever-moved ones give one pulse per
lever edge; the slider turns one pulse into the top pistons' pulse; the repeater 4 16 −2
and the chain 4 15 → 4 14 → 4 13 −2 → note block 4 12 −2 → the three horizontal observers
space the rows y 16, 14, 12 four ticks apart (14, 18, 20/21) and fire them again on the
pulse's falling edges (the tidy pulls); the moving redstone blocks at x = 4 and x = 5
clock the closing at 3-tick strokes. The stripped door replaces all this by editor
pulses on the piston cells, and an editor pulse on the top piston 0 16 −3 at 10 also
quasi-powers D directly below it (the mechanism page's D4): in the original D's event at
10 is skipped because the top piston has already pushed D away.

**Lessons.** (1) A seamless door can keep every piston inside the door columns: a
**self-carrying stack** of sticky pistons rides with the blocks it moves and the stack
walks down (pushes) and up (an inchworm of one plain piston and one sticky piston)
without a single piston outside the wall plane; the price is 39 / 33 ticks and 35
pistons for nine door cells. (2) Pistons buried in a wall are powered through the wall:
**wire rows on conductor rows**, read by quasi-connectivity, with a separate update
source for every QC-powered piston (a helper piston's head, a landing block, the piston's
own head). (3) **Observers are the clock**: moved observers for the lever's edges, a
vertical observer chain for the 4-tick spacing, note blocks as update relays, and a
piston-shuttled redstone block as a 6-tick oscillator. (4) A 2-tick pulse into a sticky
piston **spits when there is something to push and pulls when there is not**, so a
piston that faces an alternating cell alternates the world (EXP-073).

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 3×3 in the plane z = -3; 0 more output cells outside it.
- Timeline: use lever at 1, use lever at 46; markers Opening 1, Opened 45, Closing 46, Closed 83
- Reference states: closed at tick 83, open at tick 45. Fully closed at ticks 0-9, 12-13, 16-17, 20, 23, 73-76, 79-116; fully open at 40-53.
- Pistons by role: door 30, fires, moves nothing 9, helper 2, idle 3, power mover 9, stack 3
- How extensions were powered (block giving the signal; QC = through the block above the piston): block←wire 57, block←wire (QC) 23, observer 6, redstone_block (QC) 6, target (QC) 5, target 5, observer (QC) 4, repeater 3, block←observer 2, block←repeater (QC) 1, block←observer+wire 1, block←observer (QC) 1, bud 1, block←lever (QC) 1, block←lever 1
- Phases (bursts of piston events): 1–2 (3 events, 2 pistons); 6–42 (126 events, 27 pistons); 47–47 (2 events, 2 pistons); 51–80 (166 events, 24 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
  0   10   12   14   16   18   20   21   23   24   26   28   31   32
###  ~~~  ###  ~~~  ###  ~~~  ###  ###  ###  ~~~  ###  ...  ~~~  ~~~
###  ~~~  ###  ~~~  ###  ~~~  ###  ~~~  ###  ~~~  ###  ###  ###  ...
###  ~~~  ###  ~~~  ###  ~~~  ###  ~~~  ###  ...  ...  ...  ...  ...

 34   40   54   56   62   64   71   73   77   79
###  ...  ...  ...  ...  ...  ~~~  ###  ~~~  ###
...  ...  ...  ...  ~~~  ###  ~~~  ###  ~~~  ###
...  ...  ~~~  ###  ~~~  ###  ~~~  ###  ~~~  ###

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| below | 12 | 24 | 8×12 | down 4 (12) |
| above | 6 | 21 | 6×3, 8×3 | down 1 (6) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| 0 1 -3 | up | door | 54+0→spat | block←wire 1 |
| 0 2 -3 | up | door | 62+3→retracted, retracted at 65, 68+None→held | block←wire 2 |
| 0 3 -3 S | down | door | 59+0→pulled, 71+0→spat, 74+None→held | block←wire 4 |
| 0 4 -3 | up | door | 68+0→pulled, 77+0→spat | block←wire 3 |
| 0 10 -3 S | down | door | 21+3→pulled | block←wire (QC) 1 |
| 0 11 -3 S | down | door | 31+1→pulled | block←wire 1 |
| 0 12 -3 S | down | door | 18+2→spat, 26+2→pulled, 39+1→pulled | block←wire (QC) 3 |
| 0 13 -3 S | down | door | 35+1→pulled, 39+None→held | block←wire 2 |
| 0 14 -3 S | down | door | 14+2→spat, 30+2→pulled | block←wire (QC) 2 |
| 0 16 -3 | down | door | 10+2→spat | observer 1 |
| 1 1 -3 | up | door | 54+0→spat, 59+None→held | block←wire 1, block←wire (QC) 1 |
| 1 2 -3 | up | door | 62+3→retracted, retracted at 65, 68+None→held | block←wire 2 |
| 1 3 -3 S | down | door | 59+0→pulled, 71+0→spat, 74+None→held | block←wire 4 |
| 1 4 -3 | up | door | 68+0→pulled, 77+0→spat | block←wire 3 |
| 1 10 -3 S | down | door | 21+3→pulled | block←wire (QC) 1 |
| 1 11 -3 S | down | door | 31+1→pulled | block←wire 1 |
| 1 12 -3 S | down | door | 18+2→spat, 26+2→pulled, 39+1→pulled | block←wire (QC) 3 |
| 1 13 -3 S | down | door | 35+1→pulled, 39+None→held | block←wire 2 |
| 1 14 -3 S | down | door | 14+2→spat, 30+2→pulled | block←wire (QC) 2 |
| 1 16 -3 | down | door | 10+2→spat, 18+2→spat | observer 2 |
| 2 1 -3 | up | door | 54+0→spat, 59+None→held | block←wire 1, block←wire (QC) 1 |
| 2 2 -3 | up | door | 62+3→retracted, retracted at 65, 68+None→held | block←wire 2 |
| 2 3 -3 S | down | door | 59+0→pulled, 71+0→spat, 74+None→held | block←wire 4 |
| 2 4 -3 | up | door | 68+0→pulled, 77+0→spat | block←wire (QC) 3 |
| 2 10 -3 S | down | door | 21+3→pulled | block←wire (QC) 1 |
| 2 11 -3 S | down | door | 31+1→pulled | block←wire 1 |
| 2 12 -3 S | down | door | 18+2→spat, 26+2→pulled, 39+1→pulled | block←wire (QC) 3 |
| 2 13 -3 S | down | door | 35+1→pulled, 39+None→held | block←wire 2 |
| 2 14 -3 S | down | door | 14+2→spat, 30+2→pulled | block←wire (QC) 2 |
| 2 16 -3 | down | door | 10+2→spat, 18+2→spat | observer 2 |
| -2 13 -4 | east | fires, moves nothing | 28+2→spat | block←repeater (QC) 1 |
| -1 13 -3 | down | fires, moves nothing | 18+2→spat, 26+4→retracted, 34+2→spat, 39+1→spat | block←wire 4 |
| -1 15 -3 | down | fires, moves nothing | 14+2→spat, 30+2→spat | block←wire 2 |
| 0 15 -3 S | down | fires, moves nothing |  | observer (QC) 1 |
| 1 15 -3 S | down | fires, moves nothing |  | observer (QC) 1 |
| 2 1 -2 | east | fires, moves nothing | 59+0→spat, 62+0→spat, 65+0→spat, 68+0→spat, 71+0→spat, 74+0→spat, 77+0→spat | block←wire 7 |
| 2 15 -3 S | down | fires, moves nothing |  | observer (QC) 1 |
| 4 7 -2 | up | fires, moves nothing | 56+0→spat, 62+0→spat, 68+0→spat, 74+0→spat, 80+0→spat | target 5 |
| 5 1 -3 | north | fires, moves nothing | 54+0→spat | block←wire 1 |
| 1 12 -4 S | west | helper | 26+2→spat | observer 1 |
| 3 7 -2 S | down | helper | 55+2→pulled, 75+2→spat | block←observer (QC) 1, bud 1 |
| -1 16 -4 | east | power mover | 14+2→spat, 20+6→retracted, 30+2→spat, 36+6→retracted | block←wire 1, repeater 2, block←observer+wire 1 |
| 3 2 -3 S | up | power mover | 61+8→pulled | repeater 1 |
| 4 1 -2 | up | power mover | 53+1→spat, 59+0→spat, 65+0→spat, 71+0→spat, 77+0→spat | redstone_block (QC) 5 |
| 4 6 -2 | down | power mover | 56+0→spat, 62+0→spat, 68+0→spat, 74+0→spat, 80+0→spat | target (QC) 5 |
| 4 16 -4 | west | power mover | 6+2→spat | block←observer 1 |
| 5 1 -2 S | up | power mover | 54+0→spat, 58+2→pulled | redstone_block (QC) 1, observer (QC) 1 |
| 5 13 -2 | down | power mover | 51+2→spat | block←observer 1 |
| 5 14 -2 S | north | power mover | 2+45→pulled | block←lever (QC) 1 |
| 5 15 -2 S | north | power mover | 2+45→pulled | block←lever 1 |
| 0 5 -3 S | down | stack | 74+0→pulled | block←wire 2 |
| 1 5 -3 S | down | stack | 74+0→pulled | block←wire 2 |
| 2 5 -3 S | down | stack | 74+0→pulled | block←wire 2 |

<!-- end generated -->
