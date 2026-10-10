# Redstone torch

- **Status:** researched; implemented in `world/blocks/torch.py` including deterministic burnout (owner decision, ADR-010); unit-tested; confirmed in game (EXP-002, EXP-004, EXP-005, EXP-006).
- **Summary:** An inverter with a 2-tick delay at NORMAL priority. Its state change sends a
  large number of neighbor updates, and it strongly powers the block above it.
- **Scope:** Standing and wall torches, including burnout.

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

- `tests/sim/test_components.py`: strong power into the block above but not the support;
  wall torch input from the attached block and 2-tick inversion; burnout counter (8 entries
  within the window).
- Game: EXP-002 (inverter), EXP-004 (AND gate), EXP-005 (burnout that stays out),
  EXP-006 (burnout reset by a later update).

## Unknowns

- None for the implemented paths. Burnout state (`RECENT_TOGGLES`) is one list per level,
  pruned only when a torch ticks; the simulator keeps it in `Level.torch_toggles`.
- [[quirks]] Q-TORCH-BURNOUT-STUCK: a burnt-out torch can stay out forever when its own
  cascade re-schedules it before the 160-tick restart is requested (EXP-005).

## Related

[[power-queries]] · [[tick-scheduling]] · [[neighbor-updates]]
