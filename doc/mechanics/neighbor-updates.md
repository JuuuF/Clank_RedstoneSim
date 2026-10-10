# Neighbor updates, shape updates, and the setBlock pipeline

- **Status:** researched (source).
- **Summary:** A block change notifies neighbors through two distinct channels:
  *neighbor updates* (`neighborChanged`, what redstone components react to) and *shape
  updates* (`updateShape`, what connection and support logic reacts to). Both go through the
  level's `CollectingNeighborUpdater`, which runs them depth-first but never re-entrantly.
- **Scope:** Server-side behavior; client-side flags (2, 4, 8) are irrelevant for state.

## Source

- `net/minecraft/world/level/Level.java` `setBlock` L216, `removeBlock` L268, `destroyBlock` L274,
  `neighborShapeChanged` L320, `updateNeighbourForOutputSignal` L1008.
- `net/minecraft/world/level/chunk/LevelChunk.java` `setBlockState` L269.
- `net/minecraft/server/level/ServerLevel.java` `updateNeighborsAt` L1170 and the
  `neighborChanged` overloads below it.
- `net/minecraft/world/level/redstone/NeighborUpdater.java` (`UPDATE_ORDER` L18,
  `executeShapeUpdate` L36, `executeUpdate`), `CollectingNeighborUpdater.java` (`addAndRun` L68,
  `runUpdates` L87).
- `net/minecraft/world/level/block/state/BlockBehaviour.java` `UPDATE_SHAPE_ORDER` L85,
  `updateNeighbourShapes` L735; `net/minecraft/world/level/block/Block.java` flags L90–106,
  `updateOrDestroy` L212, `updateFromNeighbourShapes` L194.

## Rules

### Update kinds

| Kind | Entry point | Recipients | Order |
|---|---|---|---|
| Neighbor update (6 neighbors) | `updateNeighborsAt(pos, block)` | `neighborChanged` of the 6 blocks around `pos` | **W, E, D, U, N, S** (`UPDATE_ORDER`) |
| Neighbor update except one side | `updateNeighborsAtExceptFromFacing(pos, block, skip)` | 5 blocks | same order minus `skip` |
| Single neighbor update | `neighborChanged(pos, block)` | block at `pos` | n/a |
| Shape update | `neighborShapeChanged` (from `updateNeighbourShapes`) | `updateShape` of each neighbor | **W, E, N, S, D, U** (`UPDATE_SHAPE_ORDER`) |
| Comparator update | `updateNeighbourForOutputSignal(pos, block)` | comparators beside `pos`, or one block further behind a conductor; horizontal only, order N, E, S, W | `Plane.HORIZONTAL` |

`neighborChanged` is called with the **current** state at the target position when the
update executes (`SimpleNeighborUpdate` and `MultiNeighborUpdate` read the state at run time;
`FullNeighborUpdate` carries a state captured when queued).

### `CollectingNeighborUpdater`

State: a stack of pending update records, a list `addedThisLayer`, and a `count`.

1. `addAndRun(update)`: if no update is running (`count == 0`), push the update and run
   the loop immediately. Otherwise append it to `addedThisLayer` and return at once.
2. Loop: push `addedThisLayer` onto the stack in reverse (so the first-added ends on top),
   clear it, take the top record, and execute its sub-updates one at a time **until a
   sub-update adds something**. A finished record is popped. Repeat until stack and layer
   are empty.

Consequences:

- A handler (`neighborChanged`, `updateShape`) always runs to completion before any update
  it emitted runs. Updates are never re-entrant.
- Updates emitted by one handler run in emission order, and each one's whole cascade
  finishes before the next emitted update starts (depth-first).
- A multi-neighbor update interrupted by children resumes with its next direction after the
  children's cascades finish.
- Calls made outside any running update (from a scheduled tick, block event, block-entity
  tick, or player action) execute synchronously and fully inside the call. Two consecutive
  top-level calls therefore run one complete cascade after the other.
- The number of updates queued per top-level run is capped at
  `max-chained-neighbor-updates` (default 1 000 000). Later updates are dropped and an error
  is logged.

### `setBlock(pos, state, flags, limit=512)`

1. Store the state. If it equals the old state, stop (no side effects at all).
2. If the block type changed and the old state had a block entity: unless flag 256, call the
   block entity's `preRemoveSideEffects`; remove the block entity.
3. If (block type changed **or** the new block is a rail) and (flag 1 or flag 64): call
   `oldState.affectNeighborsAfterRemoval(level, pos, movedByPiston = flag 64)`.
4. If the block at pos is no longer of the new type, stop (`setBlock` returns false).
5. Unless flag 512: `newState.onPlace(level, pos, oldState, movedByPiston)`. This runs on
   **every** state change, not only on placement; many components rely on it.
6. Create the block entity if the new block has one.
7. If the state at pos is no longer the state we set (changed during steps 3–6), stop
   (returns true, no further updates).
8. Flag 1: `updateNeighborsAt(pos, oldState.block)`; if the new state has analog output,
   `updateNeighbourForOutputSignal`.
9. Unless flag 16, and when `limit > 0`: shape updates with flags `flags & ~(1|32)` and
   `limit − 1`, in this order: `oldState.updateIndirectNeighbourShapes`,
   `newState.updateNeighbourShapes` (6 directions), `newState.updateIndirectNeighbourShapes`.

Common flag values: 3 = `setBlockAndUpdate`; 2 = state change without neighbor updates
(shape updates still happen); 18 = 16|2; 67 = 64|3; 82 = 64|16|2; 276 = 256|16|4;
324 = 256|64|4; 340 = 256|64|16|4; 11 = player placement.

### Shape updates

`executeShapeUpdate`: unless flag 128 is set and the target is redstone wire, compute
`newState = state.updateShape(...)` and call `updateOrDestroy`. `updateOrDestroy` destroys
the block if the new state is air (`destroyBlock` → `setBlock(air, 3)`: full neighbor
updates), otherwise calls `setBlock(newState, flags & ~32)`. Since shape-update flags lack
bit 1, **state changes caused by shape updates emit no neighbor updates of their own**, only
further shape updates (and `onPlace`).

## Edge cases and quirks

- [[quirks]] Q-UPD-DFS: an update emitted inside a handler is delayed until the handler
  returns, but runs before the handler's own remaining sibling updates.
- [[quirks]] Q-UPD-ONPLACE: `onPlace` fires for property-only changes too (diodes use it to
  notify their output).
- Blocks that only re-check their power in `neighborChanged` (pistons, lamps) can be left
  in a stale state when power changes without a neighbor update reaching them
  (block-update detection, "BUD"). Quasi-connectivity is the most common way this happens.

## Tests

Planned: `tests/sim/test_neighbor_updater.py` (order, depth-first behavior, chain limit),
`tests/sim/test_set_block.py` (flags pipeline).

## Unknowns

None for the in-scope paths. Rails (step 3's rail exception) are not simulated yet.

## Related

[[tick-scheduling]] · [[power-queries]] · [[redstone-wire]] · [[pistons]]
