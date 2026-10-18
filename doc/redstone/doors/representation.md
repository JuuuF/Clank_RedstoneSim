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
1112 variants in 16 doors ([[robustness]]). Before looking at the results, layer 2 sorts
each block by the role it plays in the designed run (`ablation.glass_roles`;
`python -m tools.doorlab.ablation --predict --out .sandbox/doors/ablation WORLD` scores
the saved results):

| role (layer 2) | glass breaks the door (or changes its timing) |
|---|---|
| receives power at some tick (`has_neighbor_signal` during the replay) | 270 of 736 |
| never powered, but a wire cutter (wire under it, wire beside it) | 11 of 12 |
| never powered, immovable (obsidian) | 1 of 5 |
| none of these | **0 of 359** |

So the model's "this block does not matter" is exact here: a third of the conductors can
be told apart without running anything. The four never-powered obsidian blocks that
can be glass are never pushed. The powered class is where layer 2 is not yet precise:
it includes blocks that are powered but feed nothing, and blocks whose power has
another path. On its own, the piston power trace (`replay`'s source of each extension)
finds about half of the breaking conductors: 145 of the 204 conductors that delivered an
extension's power break. The other 137 of the 282 that break are the 12 cutters and
stoppers, and 125 powered blocks that never deliver an extension's power themselves.
They must matter further upstream or for other components; this is not traced yet
(backlog D12).
