# Patterns of piston-door engineering in the dataset

Mechanisms the 19 worlds use, each with the rule behind it (knowledge-base record), how
the door lab recognizes it in a replay, and where it occurs. Counts come from
`python -m tools.doorlab.patterns` (table below; data in `experiments/doors/patterns.json`).
Java 26.3; evidence labels as in [[../README]].

## The mechanisms

### Singles (one piston per door block)

A sticky piston beside the doorway holds one door block in its cell and pulls it one cell
into the frame (or wall) to open. Every door uses them for the edge cells: in the census
they are the groups whose blocks move 2 times (out and back) by one piston. Simple,
fast (the cell clears 2–3 ticks after the piston's power changes), but they need room in
the frame on every side. **V** (all 19 replays).

### Floor storage (flush doors)

The cells a single cannot reach (the center of a 3x3, the inner cells of larger doors) go
**down into the floor** or **up into the lintel** and the floor/lintel cell they leave is
filled again from the side. Mumbo Jumbo's 3x3: the bottom-middle block is slid aside in
the floor, the center block rides a double extender; group "below" with 4 moves per
block. In the census: groups with exit "below"/"above" and more than 2 moves. **V**

### Extenders (stacks)

Pistons that push other pistons: an extender's lower stage (role "stack"). Depth in the
census = the most pistons that move one door block (Mumbo 2, ashevoy's 5x5 17). The 5x5
guide's vocabulary (DPE, TPE, quad) describes them ([[guide-5x5]]). Retracting an
extender needs one pull per stage, hence the long opening sequences. **V**

### Spits: placing a block and leaving it

A sticky piston that loses power while its block still moves places the block at once and
leaves it ([[../components]] "Spitting", R-018, G EXP-016). Doors use it to move a block
**one cell and leave it** (to stage blocks for an extender, to feed a block into a column).
The usual driver is an **observer's 2-tick pulse** (enough to start the push, short enough
to spit). Very common: 1 (Mumbo) to 776 (LegDen's 7x7) per run; in most 3x3 doors 40–50 %
of the extensions end in a spit. **V**

### Power switches: moving the conductor

Instead of a pulse circuit, a piston **moves the solid block that powers another piston**:
pulling it away cuts the power (an exact short pulse, e.g. a spit), pushing it back
restores it. Mumbo Jumbo's 3x3 makes its center spit this way ([[analyses/3x3-piston-door-mumbo-jumbo]]).
Recognized as role "power switch": a piston that moved a block which was, at that
moment, the `via` of another piston's power. In 8 worlds. **V**

### Quasi-connectivity (QC) power

A piston is powered by power next to the cell **above** it (R-009, R-025), but only acts
on a neighbor update. Doors use it to power pistons from a line above (the guide's "dust
lines on the ceiling", [[guide-5x5]] 1.3) and to power two stacked pistons from one block.
In the census: extensions whose power note says `quasi`. Every door uses it: 1–480 per run.
**V**

### Landing checks: pistons that start themselves

A piston moved into place by another piston checks its power when it lands and extends
one tick later if powered there ([[../components]] "Landing check", R-025, G EXP-059). Doors
use it to chain extender stages without wiring the upper stage: Mumbo's raised center
piston extends by itself. Census column "landings" (extensions of a piston that had just
been moved). **V**

### Moving power sources: observer sliders and block swappers

Pistons that move observers (an observer pulses 2 ticks after it lands, R-015) or redstone
blocks (power travels with the block). The guide's **observer sliders** fire a whole row
of pistons at once ([[guide-5x5]] 1.3). Census columns "observers moved", "redstone blocks
moved"; role "power mover". Large doors rely on them (ashevoy's 5x5 moves 56 observers,
LegDen's doors hundreds). **V**

### Slime and honey assemblies

Slime moves everything touching it except honey (R-009): a slime/honey pair carries a
whole door column sideways in one push. Purplers' sliding 4x4 slides each half (8 blocks)
two cells with 4 pistons; Nile's 5x5 vault uses slime too. Census column "slime/honey
moved". **V**

### A moving block stops a piston

A powered piston facing a block that is still moving does nothing until the block lands,
then extends one tick later; a short pulse that ends first is lost
([[../records/R-026-moving-block-blocks-piston]]). The 5x5 guide's PF.1 explanation of an
extender that pushes one block less when closing than when opening. **V**

### Same-tick races depend on orientation

When two pistons of one mechanism are triggered **in the same tick**, the order of their
block events follows the order of neighbor updates, which depends on direction. Purplers'
5x5 vault lamp door works in 6 of its 8 orientations and breaks in 2: its horizontal
double extender's front piston queues before the rear one and the rear's push fails
([[symmetry]]). **V** (dataset replay)

## Census

Generated by `python -m tools.doorlab.patterns` (2026-10-18). "lever → state": ticks from
each lever action to the next fully closed / open doorway (— = never; the LegDen doors
do not open fully, see [[inventory]]).

| world | door | volume | pistons firing | lever → state | ext | spits | QC | landings | switches | observers moved | redstone blocks moved | slime/honey moved | depth | moves |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `1-wide-hidden-staircase-purplers` | 4x4 | 168 | 13 | closed 25; — | 14 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 3 | 4 |
| `3x3-flush-enchanting-table-door-purplers` | 3x3 | 360 | 33 | closed 36; open 56 | 107 | 46 | 54 | 42 | 3 | 8 | 0 | 0 | 3 | 6 |
| `3x3-seamless-glass-door-nile` | 3x3 | 512 | 53 | open 39; closed 27 | 118 | 56 | 41 | 65 | 0 | 14 | 24 | 0 | 8 | 8 |
| `3x3-spiral-vault-door-lutal` | 3x3 | 880 | 20 | closed 14; open 14 | 40 | 17 | 4 | 4 | 0 | 0 | 0 | 0 | 3 | 4 |
| `3x3-piston-door-mumbo-jumbo` | 3x3 | 189 | 13 | closed 10; open 24 | 18 | 1 | 2 | 2 | 1 | 0 | 0 | 0 | 2 | 4 |
| `3x3-piston-door-rubik` | 3x3 | 180 | 11 | closed 14; open 26 | 22 | 9 | 5 | 3 | 0 | 0 | 0 | 0 | 3 | 4 |
| `3x3-piston-door-sacredredstone` | 3x3 | 112 | 11 | closed 19; open 42 | 41 | 17 | 10 | 5 | 0 | 0 | 0 | 0 | 3 | 8 |
| `3x3-piston-door-zhus` | 3x3 | 126 | 12 | closed 14; open 14 | 23 | 10 | 6 | 3 | 0 | 0 | 0 | 0 | 3 | 4 |
| `3x3-piston-door-monchicarp` | 3x3 | 126 | 12 | closed 14; open 14 | 22 | 10 | 6 | 2 | 0 | 0 | 0 | 0 | 3 | 4 |
| `3x3-spiral-piston-door-purplers` | 3x3 | 168 | 13 | closed 19; open 21 | 28 | 11 | 6 | 2 | 0 | 2 | 0 | 0 | 2 | 4 |
| `3x4-piston-door-pal1` | 3x4 | 280 | 17 | closed 28; open 44 | 36 | 13 | 10 | 7 | 0 | 2 | 0 | 0 | 3 | 4 |
| `4x4-piston-door-kwipla` | 4x4 | 1080 | 32 | closed 27; open 39 | 70 | 29 | 15 | 12 | 0 | 4 | 2 | 0 | 3 | 4 |
| `4x4-piston-door-sydney600mc` | 4x4 | 270 | 28 | closed 16; open 26 | 52 | 16 | 12 | 12 | 0 | 4 | 0 | 0 | 3 | 4 |
| `5x5-glass-piston-door-ashevoy` | 5x5 | 8625 | 190 | closed 36; open 37 | 319 | 95 | 91 | 133 | 8 | 56 | 12 | 0 | 17 | 18 |
| `5x5-vault-door-nile` | 5x5 | 1050 | 71 | closed 9; open 9 | 129 | 58 | 50 | 8 | 3 | 0 | 28 | 30 | 4 | 6 |
| `5x5-vault-lamp-door-purplers` | 5x5 | 660 | 57 | closed 7; open 2 | 70 | 3 | 17 | 24 | 2 | 0 | 8 | 0 | 4 | 6 |
| `7x7-piston-door-legden` | 7x7 | 3887 | 415 | closed 18; — | 1223 | 776 | 480 | 171 | 14 | 310 | 246 | 71 | 7 | 8 |
| `8x8-piston-door-legden` | 8x8 | 3312 | 351 | closed 21; — | 885 | 577 | 375 | 97 | 8 | 212 | 150 | 180 | 9 | 12 |
| `4x4-sliding-piston-door-purplers` | 4x4 | 880 | 66 | closed 9; open 4 | 78 | 6 | 28 | 4 | 8 | 0 | 40 | 68 | 2 | 4 |

## Design principles read from the corpus

1. **Group by exit side, then solve the hard cells.** Every door's blocks fall into exit
   groups (above, below, the two sides, a recess); singles take the edges; the work goes
   into the few cells no single reaches (the center of a 3x3: always "below" with 4
   moves). Same as the guide's grouping ([[guide-5x5]] 1.1). **V**
2. **Speed comes from vault and slime layouts, not from wiring.** The fastest doors open
   in 2–9 ticks (Purplers' vault lamp 5x5: 2; sliding 4x4: 4; Nile's vault 5x5: 9): their
   blocks move in one or two pistons' strokes (recess then slide, or slime assemblies).
   Flush doors with extenders need 14–56 ticks. **V** (census)
3. **The opening is the long part** of flush doors. Closing pushes stacks out in one go;
   opening must pull them back one stage at a time (one pull per extender stage). Of the
   16 doors that both close and open, 10 open slower than they close, 4 take equally long
   (Zhus/monchiCARP, Lutal's spiral vault, Nile's vault) and the two fastest (vault lamp,
   sliding) open faster: their blocks need no extender. **V** (census)
4. **Short pulses are made mechanically**: observers (2 ticks), moved conductors (power
   switches), moved observers. Spits are the most common move after plain pushes. **V**
5. **Same-tick triggers are fragile.** Designs that fire stages of one extender in the
   same tick depend on the build's orientation ([[symmetry]]). **V**
