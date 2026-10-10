# Redstone torch

- **Status:** researched (source).
- **Summary:** An inverter with a 2-tick delay at NORMAL priority. Its state change sends a
  large number of neighbor updates, and it strongly powers the block above it.
- **Scope:** Standing and wall torches. Burnout is out of initial scope (see Unknowns).

## Source

`net/minecraft/world/level/block/RedstoneTorchBlock.java`: `onPlace` L37, `notifyNeighbors` L41,
`affectNeighborsAfterRemoval` L50, `hasNeighborSignal` L56, `tick` L61, `neighborChanged` L83,
`getDirectSignal` L92, `ownSignal` L102, `getSignal` L107, `isToggledTooFrequently` L126.
`net/minecraft/world/level/block/RedstoneWallTorchBlock.java`: `canSurvive` L38, `updateShape`
L43, `hasNeighborSignal` L75, `getSignal` L81. `BaseTorchBlock.java` (`canSurvive` L43:
`canSupportCenter` below).

## Rules

- **Input.** Standing: `hasSignal(below, DOWN)`. Wall: `hasSignal(attached, dir)`, where the
  attached block is at `pos − FACING`.
- **neighborChanged:** if `LIT == input` (state disagrees with what it should be) and no tick
  is waiting this tick, schedule a tick after **2** game ticks, NORMAL priority.
- **tick:** lit and powered → `setBlockAndUpdate(LIT=false)`; unlit and unpowered →
  `setBlockAndUpdate(LIT=true)`. The input is re-read at tick time.
- **Output:** signal 15 to every side except into its support block; strong (direct) signal
  only into the block above.
- **Updates on change:** `onPlace` runs `notifyNeighbors` (`updateNeighborsAt` around each of
  the 6 neighbors, in D, U, N, S, W, E order: 36 calls), then `setBlockAndUpdate` adds
  `updateNeighborsAt(pos)` and the shape updates. From a scheduled tick these run as
  separate top-level cascades, each completing before the next starts.
- **Support:** standing torch needs CENTER support below; wall torch needs a FULL face on
  the attached block. Losing support makes it pop (`updateShape`).

## Edge cases and quirks

- [[quirks]] Q-TORCH-STRONG-UP: a torch strongly powers the block above, so wire on a block
  above a torch is powered.
- [[quirks]] Q-TORCH-BURNOUT-DET: burnout is deterministic in 26.3, not random
  (8 toggles of one position within 60 game ticks, then a 160-tick re-check).

## Tests

Planned: `tests/sim/test_torch.py`: inversion timing, wall torch input, strong power upward,
torch tower timing, notification order.

## Unknowns

- Burnout: out of scope by the brief. The source shows a global per-level list
  (`RECENT_TOGGLES`) shared by all torches and pruned only during torch ticks. Implementing
  it is a scope decision for the owner ([[README]]).

## Related

[[power-queries]] · [[tick-scheduling]] · [[neighbor-updates]]
