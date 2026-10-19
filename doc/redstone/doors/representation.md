# The spatial representation of a contraption

How the door lab (`tools/doorlab`) represents a world, in three layers. The rule behind
it (mission, "Never let a convenient abstraction silently discard information"): every
higher layer is **computed** from the one below by the simulator's own code, and the
lowest one is **lossless**, so any statement on a higher layer can be traced to blocks
and ticks and checked again.

```
layer 3  knowledge      door blocks' trajectories, groups (exit sides), piston roles,
         (analysis,     moves (pulses, spits), power access, phases, comparisons,
          compare,      symmetry behavior
          symmetry)              ▲ computed from the replay + layer 2
layer 2  interactions   static: roles, simulator facts per block, pistons with their
         (interactions, push/pull structures and power positions, the doorway
          replay)       dynamic: piston block events, what they moved, power notes,
                        causal links, doorway frames
                                 ▲ computed by the simulator from layer 1
layer 1  canonical      blocks, block entities, pending engine state, timeline,
         (canonical)    annotations: exactly the world file, sorted
```

## Layer 1: the canonical world (`canonical.py`)

The world file holds the build as an engine snapshot, the recorded actions and the
editor's annotations. The canonical form is the same information as sorted plain data:

| Field | What | Why it is kept |
|---|---|---|
| `blocks` | `[x, y, z, state]` for every block of the build, the floor too, sorted by y, z, x; states with every property | geometry and orientation are the program |
| `block_entities` | type, position, state, saved data (items, comparator output), in engine order | container contents are inputs (comparator readings, droppers); their order is the order of block-entity ticks |
| `engine_runtime` | game time, pending scheduled ticks, block events, ticker lists … | a build can be **unsettled**: three worlds start with piston events or a comparator tick pending at tick 0 (Nile's seamless door, SacredRedstone's 3x3, LegDen's 7x7); dropping them changes the run |
| `timeline` | the recorded actions with their ticks (here always `use` of the lever), the simulated length | the stimulus |
| `annotations` | sections (`input`, `output`, …), markers ("Closing", "Closed" …), groups, labels, notes, targets | the designer's statement of intent: what the doorway is and when it should be closed or open |

`to_save` writes it back as a world file and `rebuild` opens that as an editor document.
Not kept: the camera, the editor's undo history and prefabs (no effect on the
simulation).

**Validation** (`tests/doorlab/test_doorlab.py`, all 19 worlds): canonical → rebuild →
canonical is identical text, and the rebuilt world replays with the same block changes at
every tick (a per-tick fingerprint of all changes).

## Layer 2: interactions

**Static** (`interactions.py`), from the build:

- `role(block)`: piston, wire, repeater, comparator, observer, torch, redstone block,
  target, lever, button, bud (note block), lamp, dropper, hopper, rail, sticky block
  (slime, honey), analog source (barrel, furnace …), structure (everything else).
- `block_facts`: conductor (`isRedstoneConductor`), push reaction as a piston sees it here
  (move, push only, break, blocks), sticks (slime/honey), foreign (not simulated). Asked
  from the simulator, not from block names: an iron block and white concrete are both
  "solid, movable".
- `pistons`: facing, sticky, extended, head cell; **what it would move now**
  (`PistonStructureResolver` on the build: the push of a retracted piston, the pull of an
  extended sticky one, with the head removed first as `moveBlocks` does); the positions
  that can switch it in `getNeighborSignal` order, including the five quasi-connected
  ones, with the redstone parts there.
- `doorway`: the output section as a door: the plane holding most cells (x = c or z = c),
  its width, height, rows and columns; cells outside the plane are kept as `extra_cells`
  (stairs, frames, lamps).
- `floor_top`: the ground layer (a new world's floor at y=0, an imported superflat's
  grass at y=−61), so "the contraption" is everything above it.

**Dynamic** (`replay.py`), from the run: the recorded history is replayed **engine step
by engine step**, and around each block event the moving-block entities are compared:

- `PistonEvent`: tick, rank in the tick, piston, kind (extend / retract / drop = the
  game's event types 0 / 1 / 2), outcome (pushed, extended into air, failed, pulled,
  retracted, spat = a retract that ended an extension early and left the block,
  skipped = the piston had changed before its event ran), the blocks it set moving (from,
  to, state) and the ones it ended early;
- `failure` of an extension that moved nothing, read just before its event ran:
  `unpowered` (its power ended before the event: a 0-tick pulse lost), `moving block at
  …` (R-026), `immovable … at …` (an extended piston, R-027; a block entity),
  `more than 12 blocks`, `sticky branch`;
- `power` of each extension: the trace note the piston leaves when it queues it (the
  block giving the signal, `via`; whether through the block above the piston =
  quasi-connectivity; what powers a solid `via`);
- `links` (optional): for each block change, the change that caused it (the same rules
  as `redsim-cli why`), with how (update, scheduled tick, block event, moved block,
  player action);
- `frames`: the doorway's cells per tick (`#` solid, `.` open, `~` moving) and
  `check_markers`: the world's "Closed" / "Opened" markers against the frames.

## Layer 3: knowledge (`analysis.py`, `compare.py`, `symmetry.py`)

- **Tokens**: every block a piston moves is followed from move to move, so each door
  block has a trajectory (its cell when closed, the cells it passes, where it rests when
  open). Reference states come from the world's own markers.
- **Groups**: door blocks by the side they leave through (above, below, the two sides,
  a recess in the wall): the guide's "grouping" ([[guide-5x5]]), read from behavior.
- **Piston roles**: door (moves door blocks), stack (moves pistons: an extender's lower
  stage), power mover (moves observers, redstone blocks …: sliders, block swappers),
  power switch (moves a solid block that carried power to a piston: it switches power by
  moving the conductor), helper (moves other blocks), fires without moving anything, idle.
- **Moves**: each piston's events as pulses (start, length, end: pulled / spat / held).
- **Power access**: how each extension was powered, as words: `observer`, `wire (QC)`,
  `block←repeater` (a solid block powered by a repeater) …
- **Phases**: bursts of events separated by three quiet ticks.
- **Comparison** (`compare.py`): two builds up to the eight horizontal symmetries, at
  three levels (exact states; structure without dynamic properties; abstract with
  building blocks named by simulator facts), and two behaviors (door-block trajectories
  in doorway coordinates).
- **Symmetry** (`symmetry.py`, `transform.py`): the world turned and mirrored as a whole
  (blocks, entities, pending events with their directions, timeline, sections) and
  replayed: does every orientation do the same thing?

## What the layers made visible (examples)

- The replay shows *how* Mumbo Jumbo's 3x3 makes its spit: no pulse circuit, a second
  piston pulls away the iron block that powers the extender ("power switch").
- Zhus's and monchiCARP's 3x3 doors share 0.37 of their exact blocks, but the abstract
  comparison gives 0.79 (materials differ) and all nine door-block trajectories are equal
  tick for tick: one design, two builds ([[analyses/README]]).
- Three builds carry pending events at tick 0 (layer 1's `engine_runtime`); a
  blocks-only description of them would run differently.

## Does layer 2 predict a change? (counterfactual accuracy, 2026-10-19)

The ablation turned every conducting block above the floor into glass, one at a time:
1112 variants in 16 doors ([[robustness]]). Layer 2 is asked to say, before any variant
runs, which of them matter. Two generations of the answer:

**Static roles** (`ablation.glass_roles`, the first attempt): a block that receives power
at some tick may matter (270 of 736 did), a never-powered wire cutter (11 of 12), a
never-powered obsidian (1 of 5), none of these: **0 of 359**. Exact on the harmless side,
blind inside the powered class.

**Who reads whom** (`tools/doorlab/power.py`; `python -m tools.doorlab.power --predict
--out .sandbox/doors/ablation WORLD…` scores the saved results, `--list` prints every
block, `--reads` adds the read roles). The simulator got a probe (`Level.signal_probe`,
not game logic: every signal read that returns more than 0, with the level's state) and
the lab records the designed run with it: for each read the component whose code asked
(found on the call stack: a piston's `getNeighborSignal`, wire's muted block signal, a
diode's input, a torch's block; a read of a cell that is not one of the asker's neighbors
is a quasi-connectivity read), what else the asker could read at that moment, and the
context (a neighbor update, a piston's block event, a scheduled tick). Reads follow a
block when a piston moves it. What layer 2 then *predicts* is a **local counterfactual at
every tick boundary**: the block swapped for glass, every component that reads it
(its six neighbors, the pistons and droppers one below them) recomputes its own input
with its own rule (a piston: what it would do now, extend / blocked / retract / nothing;
wire: its target strength; a diode: its input; a torch: its block; the rest:
`hasNeighborSignal`), plus one read that boundaries cannot see (below). The result:

| layer 2 says | variants | break the door | change other blocks only | change nothing |
|---|---|---|---|---|
| some component reads a different input with the block as glass (at a tick boundary, or a retracted piston's update read that nothing else made positive) | 347 | 280 | 59 | 8 |
| an immovable block a push failed on, or that a sticky piston's retraction or a slime block would otherwise move | 3 | 0 | 3 | 0 |
| a falling block (sand) | 1 | 1 | 0 | 0 |
| none of these | 761 | **1** | 250 | 510 |

281 of the 282 breaking glass changes are predicted (the one missed: an obsidian above a
piston in the sliding door that is never powered at a boundary), and "none" is as exact
as before. The 59 "reads → other blocks only" are real: a component's input does change,
and the change never reaches the doorway; telling those apart needs the reach from a
reader to the mechanism (open, below). The 250 "none → other blocks only" are mostly the
variant's own block being moved (glass instead of wool in the moving records), not an
effect.

The intermediate read roles are kept (`power.roles`, `--reads`): a block read decisively
by some component (223 of 283 broke), read but never without an alternative (0 of 13),
powered but read by nothing (2 of 349), a wire cutter (24 of 26), a step carrier (32 of
80). They are what the counterfactual replaced, and each wrong prediction, replayed to its
first differing tick, taught a rule:

- **A conductor's role follows the block, not the cell.** Mumbo Jumbo's wire-cutter wool
  is harmless where it is built and cuts the step where the helper piston puts it; in
  Nile's 5x5 vault an oak log pushed over a note block carries a wire's power down to it
  at tick 4; in Purplers' sliding door a wool riding on the slime delivers a carried
  redstone block's power to a wire at its landing cell. Static roles must be evaluated at
  every cell the block occupies (`power.cells_of`).
- **A wire step has two carriers.** The block above the lower wire is the cutter (known);
  the block under the upper wire is the step: the lower wire reads the upper one only if
  that block conducts (`getIncomingWireSignal` looks above a conducting neighbor and
  below any other). It matters only downward: the upper wire reads the lower one through
  the air above the lower wire, whatever the block is. Static "step" fires 80 times, 32 of
  which matter; the wire recomputation needs no such rule.
- **A read does not name its asker.** A piston reading the block above it and the
  quasi-connectivity read of the piston below that one are the same call; only the call
  stack tells them apart (`power.asker_of`). Judged for the wrong piston, Zhus's 2 7 −7
  looked redundant (the wire two above would power the upper piston) and broke.
- **Mid-tick reads decide pistons.** In Nile's seamless door a piston that lands at tick
  58 is updated while one block alone powers it; the other source arrives later in the
  tick without updating a quasi-connected piston (the update problem), so the landing
  read is what queues the extension. Tick-boundary states show no difference; the probe
  does. Boolean readers ignore 15 against 14: a level difference only matters to wire.
- **Glass changes more than conduction.** An obsidian that a sticky piston's retraction
  or a slime block would move as glass (the enchanting-table door, the sliding door); a
  sand block that falls (Nile's vault); a part that could not stand on glass (none in the
  corpus, checked with `can_survive`).

Open (D12, next step): the reach from a reader whose input changed to a mechanism piston,
to turn "changes something" into "breaks the door"; the same probe can answer the input
question of [[robustness]] (which first-sequence reads the second input cuts).
