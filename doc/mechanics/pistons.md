# Pistons and sticky pistons

- **Status:** researched (source).
- **Summary:** A piston decides to move in `neighborChanged`, but moves in a **block event**.
  Moving blocks become `moving_piston` blocks with block entities that finish in the
  block-entity phase two ticks later. Quasi-connectivity, block-update detection, and the
  0-tick behaviors all follow from this split.
- **Scope:** Normal and sticky pistons, push limit, pushability, slime and honey
  attachment, retraction variants. Entity movement is out of scope.

## Source

`net/minecraft/world/level/block/piston/PistonBaseBlock.java`: `setPlacedBy` L64,
`neighborChanged` L71, `onPlace` L80, `checkIfExtend` L93, `getNeighborSignal` L116,
`triggerEvent` L139, `isPushable` L213, `moveBlocks` L257.
`PistonStructureResolver.java`: `resolve` L37, `canStickToEachOther` L68, `addBlockLine` L76,
`reorderListAtCollision` L164, `addBranchingBlocks` L177.
`PistonMovingBlockEntity.java`: `finalTick` L259, `tick` L291, `getLastTicked` L377.
`MovingPistonBlock.java` (`destroy` L68); `PistonHeadBlock.java` (`canSurvive` L99,
`neighborChanged` L105); `ServerLevel.isHandlingTick` L648.

## Rules

### Activation (`checkIfExtend`, called from `neighborChanged`, `onPlace` of a new piston, and `setPlacedBy`)

`getNeighborSignal` is true if any of these has a signal:

1. the 5 neighbors except the front (`hasSignal(pos+d, d)`, D, U, N, S, W, E order);
2. the piston's own position queried with DOWN (always 0 in vanilla: the piston is neither a
   conductor nor a signal source);
3. the 5 neighbors of the block **above** the piston, excluding the piston itself
   (quasi-connectivity).

- Powered and not extended: if `PistonStructureResolver(extending).resolve()` succeeds, queue
  block event **0** (extend). If the push is impossible, nothing is queued.
- Unpowered and extended: queue block event **2** if the block two in front is a
  `moving_piston` with the same facing that is still **extending**, and (its progress is
  below 0.5, or it was ticked this game tick, or the server is still inside the
  scheduled-tick/block-event part of the tick, `isHandlingTick`). Otherwise queue event **1**.
- Event parameter `b1` = facing's 3D data value (D0, U1, N2, S3, W4, E5).

### Block event (`triggerEvent`)

1. Re-check power with `getNeighborSignal`. Powered while handling a retract event (1 or 2):
   set `EXTENDED=true` with flags 2 and stop. Unpowered while handling an extend event: stop.
2. **Extend (0):** `moveBlocks(extending)`; on failure stop; then set the base to
   `EXTENDED=true` with flags 67 (neighbor updates, moved-by-piston).
3. **Retract (1, 2):** finish the head's moving block entity in front, if any (`finalTick`);
   replace the base with a `moving_piston` (flags 276) holding the retracted base;
   `updateNeighborsAt(base)`; shape updates around the base.
   - Sticky: if the block two in front is a `moving_piston` still extending in the same
     direction, finish it in place (`finalTick`): the block is left behind
     ("block dropping"/"spitting"). Otherwise, for event 1 with a pullable block
     (not air, pushable when pulled, push reaction PUSH_PULL or a retracted piston),
     `moveBlocks(retracting)`; else (event 2, or nothing pullable) remove the head.
   - Normal piston: remove the head (`removeBlock`, flags 3).

### Moving blocks (`moveBlocks`)

1. Resolve the structure (max **12** blocks; popped blocks go to `toDestroy`).
2. Destroy `toDestroy` from last to first (`setBlock(air, 18)`).
3. Replace each pushed block, from last to first, at its destination with a
   `moving_piston` (flags 324) carrying the original state.
4. Extending: put the head's `moving_piston` (source = true) in front of the base (flags 324).
5. Set vacated positions to air (flags 82) in **Java `HashMap` order**, then send their shape
   updates (old state's indirect, air's direct, air's indirect; flags 2).
6. Neighbor updates: destroyed blocks (`affectNeighborsAfterRemoval`, indirect shapes,
   `updateNeighborsAt`), then original positions of pushed blocks (last to first), then the
   head position when extending.

### Moving block entities

Created during the block event; they are appended to the block-entity list and tick in
the same tick's block-entity phase. Progress per tick: 0 → 0.5 → 1.0. On the third tick
(`progressO >= 1`) the moving block is replaced by its final state, adjusted with
`updateFromNeighbourShapes` (flags 67), followed by a `neighborChanged` at that position. A
pushed block therefore becomes real in the block-entity phase **2 game ticks after the
block event**. `finalTick` (used when a retraction interrupts a move, or when the
`moving_piston` block is replaced) completes the move instantly.

### Pushability (`isPushable`)

Outside the build height or world border: no. Air: yes. Moving down from the bottom row or
up from the top row: no. A piston base: only when retracted. Otherwise: destroy speed −1
→ no; IMMOVEABLE → no; POPPED → only where destroying is allowed (the line being pushed);
PUSH → only when moved in its own push direction; then **no if the block has a block
entity**.

## Edge cases and quirks

- [[quirks]] Q-PISTON-QC: quasi-connectivity, power at the space above activates the piston.
- [[quirks]] Q-PISTON-BUD: a QC-powered piston only reacts when it receives a neighbor
  update, so it can stay retracted while "powered".
- [[quirks]] Q-PISTON-SPIT: a sticky piston that retracts before its push has completed
  leaves the block behind (0-tick and short pulses).
- [[quirks]] Q-PISTON-EVENT-RECHECK: power is re-checked when the block event runs, so a
  pulse that ends between `neighborChanged` and the event never extends.
- [[quirks]] Q-PISTON-HASHMAP: the order of the air placements in `moveBlocks` depends on
  coordinates.
- Pushing does not change the pushed block's neighbors immediately: destinations get
  `moving_piston` states with flags 324 (no neighbor updates).

## Tests

Planned: `tests/sim/test_piston.py`: extend/retract timing per phase, QC activation and BUD
state, push limit 12, immovable blocks, popping wire, sticky pull, block spitting on a
short pulse, slime branch, honey/slime non-adhesion.

## Unknowns

- `pistonEntity.getProgress(0.0F) < 0.5F` uses `progressO`; reasoning is complete, but an
  in-game timing experiment is planned to confirm the event-2 window ([[experiments/index]]).
- Entity pushing is out of scope.

## Related

[[tick-scheduling]] · [[neighbor-updates]] · [[block-properties]]
