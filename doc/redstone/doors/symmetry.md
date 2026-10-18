# Direction and location: do the doors work turned, mirrored or moved?

A counterfactual run over the whole dataset (2026-10-18): every world is turned to all
eight horizontal orientations (four quarter turns, with and without an east-west mirror)
and, for the sensitive ones, moved without turning; each copy is replayed and every block
change of every tick is compared with the original's, turned or moved the same way.
Tools: `python -m tools.doorlab.symmetry [WORLD …] [--shift DX,DZ …]` (layer-1
`transform`: blocks, block entities, pending events with their directions, timeline and
sections all move together; states turn by the game's `rotate`/`mirror` rules).

## Why a design can depend on direction or position

The game's redstone is not symmetric (all ported in the simulator, [[../../mechanics/index]]):

- **Direction:** a block updates its neighbors in a fixed order (west, east, down, up,
  north, south); quasi-connectivity looks only up. When two things react to one change in
  the same tick, which one goes first can depend on how the build is turned.
- **Position** ("locational"): some update sets are Java `HashSet`s / `HashMap`s of
  positions (the redstone wire's update burst, `RedstoneWireBlock` via
  `redstone_wire.py`; a piston's moved-block map, `moveBlocks`), iterated in hash order.
  The hash of a position depends on its coordinates, so moving a build can reorder
  updates.

## Results

| World | 8 orientations | moved (1,0) (0,1) (16,0) (0,16) | Verdict |
|---|---|---|---|
| 15 worlds (all others) | identical | (not needed) | independent of direction |
| `5x5-vault-lamp-door-purplers` | 6 identical; **90° and mirror+270° differ from tick 3 and the door fails** | identical (also (5,7), (−13,4), …) | **directional** |
| `3x3-seamless-glass-door-nile` | 5 identical; 270°, mirror+0°, mirror+270° differ from tick 59–62 for 12–14 ticks, the door still works | (0,16) differs from 62 | **locational** (harmless here) |
| `8x8-piston-door-legden` | all 7 differ (from tick 8–38) | (0,16) differs from 38 | locational (the door fails in every copy, as in the original) |
| `7x7-piston-door-legden` | all 7 differ (from tick 2–75) | (1,0), (0,1), (0,16) differ from 78 | locational (fails in every copy, as in the original) |

"Identical" is strict: every block state at every tick, the build's own wiring
included, not just the doorway.

### The vault lamp door's race (directional)

Found with `why` on the turned copy. A horizontal double extender: a rear sticky piston R
with a front sticky piston F in front of it (both facing the door), and one orange wool
block W above R. When the controller's wire line turns on (tick 3), W is powered by a wire
beside it: W powers R directly and F through quasi-connectivity. Both pistons queue their
extension in the same tick, and **the order decides the outcome**:

- original orientation: R queues first, pushes F (and F's block) one cell; F's own event
  finds a moving block and is skipped (the extender does its intended single stage);
- turned 90°: F is updated first, by another wire of the same line passing **under F**
  (`why`: "neighbor update from redstone wire at −2 4 −1"), and extends; R's push then
  fails (an extended piston cannot be pushed), and the door jams.

The wire line's update order follows the directions of its pieces, so turning the build
changes which branch reaches its piston first. Six orientations keep R first, two do not.
Moving the build (8 translations) never changed it: the race is decided by direction,
not by position.

**The input device is part of the race.** The floor lever is the line's source: a pull
updates the lever's neighbors and then its block's neighbors, in direction order. With
the lever replaced by a repeater into the same block (switched by a redstone block, the
stand-in `run_world` used at first), the door works **in all eight orientations**; with
the lever set by `/setblock` alone (no update of the block's neighbors) it never moves.
So the jam needs a player's pull. Since 2026-10-19 `run_world` reproduces one: the
lever set by `/setblock` (between two ticks, like a player) and the block it is on set
to stone and back in the same moment (its neighbors' update). In the simulator that
stand-in acts exactly like the pull (every block, every tick). On the server, the
original orientation and the 90° copy both match the simulator, and the 90° copy jams
in the game too (EXP-074). The rule behind it is game-verified on its own: in a double
extender powered in one tick, rear first works and front first jams
([[../records/R-027-double-extender-order]], EXP-072). The locational case below is
server-verified (EXP-070).

**Design rule.** Do not let two pistons of one mechanism be triggered by the same
change in the same tick when their order matters; give the one that must go first a
tick of lead (a repeater), or power the other one only through the first one's motion
(landing check). A design that relies on update order should be tested in all
orientations it may be built in (`symmetry`). **V** (dataset replay; minimal
reproduction [[../records/R-027-double-extender-order]], game EXP-072)

### Locational doors

Nile's seamless 3x3 differs in three orientations and when moved 16 blocks south, from
tick 59–62 (during the closing), for 12–14 ticks, but every copy still closes and opens
at the marked ticks: the order of some same-tick piston events changes and the sequence
tolerates it. LegDen's doors differ under most transformations, even a one-block move
(7x7); their door is stuck in the original too (EXP-068), so these differences only say
that their controller has many same-tick, hash-ordered races.

Server check of locationality: see EXP-070 in doc/experiments/index.md (the seamless door
run at two origins on the 26.3 server and in the simulator).

**Translations across the corpus** (2026-10-18, every door but LegDen's moved by (1, 0),
(0, 1), (7, −3) and (0, −16), `.sandbox/doors/shifts.json`): 16 of the 17 doors run
identically in all four copies. Only the seamless door differs, in the (7, −3) copy,
and that copy still closes and opens on time. Position dependence is rare in this corpus.
The hash-ordered sets matter only where several same-tick events have an order that
changes the result.
