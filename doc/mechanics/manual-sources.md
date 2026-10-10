# Manual sources and simple outputs: lever, buttons, redstone block, lamp

- **Status:** researched; implemented in `world/blocks/attached.py`, `lamp.py`, `simple.py`; unit-tested; lamp and redstone block confirmed in game. Levers and buttons need a player and are not testable on the dedicated server.
- **Summary:** Inputs used to drive test circuits, plus the lamp as a simple output.
- **Scope:** Lever, stone and wooden buttons (no arrows), redstone block, redstone lamp.

## Source

- `net/minecraft/world/level/block/LeverBlock.java`: `pull` L82, `affectNeighborsAfterRemoval`
  L112, `getDirectSignal` L119, `updateNeighbours` L133.
- `net/minecraft/world/level/block/ButtonBlock.java`: `useWithoutItem` L70, `press` L92,
  `tick` L131, `checkPressed` L146, `updateNeighbours` L164. Durations in `Blocks.java`
  (`STONE_BUTTON` 20, `OAK_BUTTON` 30 game ticks).
- `net/minecraft/world/level/block/FaceAttachedHorizontalDirectionalBlock.java`:
  `canAttach` L28, `getConnectedDirection` L69.
- `net/minecraft/world/level/block/PoweredBlock.java`.
- `net/minecraft/world/level/block/RedstoneLampBlock.java`: `getStateForPlacement` L24,
  `neighborChanged` L29, `tick` L45.

## Rules

- **Attachment.** `FACE` ∈ {floor, wall, ceiling}. The attached block is at
  `pos − connectedDirection`, where `connectedDirection` is UP for floor, DOWN for ceiling,
  and `FACING` for wall.
- **Lever.** `pull`: `setBlockAndUpdate(POWERED cycled)`, which updates the lever's
  neighbors, then `updateNeighbours`: `updateNeighborsAt(pos)` **again**, then
  `updateNeighborsAt(attached block)`. Removal while powered repeats `updateNeighbours`.
- **Button.** `press` (only when unpowered): `setBlockAndUpdate(POWERED=true)`,
  `updateNeighbours`, then schedule a tick after 20 (stone) or 30 (wood) game ticks, NORMAL
  priority. The tick releases it (no arrows are simulated), with the same update pattern.
- **Signals.** Lever and button: 15 weak in all directions; 15 strong only into the
  attached block.
- **Redstone block.** Signal source 15 in all directions, no strong power, not a conductor.
- **Lamp.** On `neighborChanged`, if `LIT != hasNeighborSignal`: turning on happens
  **immediately** (`setBlock(LIT, 2)`); turning off is scheduled 4 game ticks later (NORMAL)
  and re-checked in `tick`. Lamp changes use flags 2, so they send shape updates but no
  neighbor updates. Placement sets `LIT` from `hasNeighborSignal`.

## Edge cases and quirks

- [[quirks]] Q-LEVER-DOUBLE: a lever toggle updates its own neighbors twice.
- [[quirks]] Q-LAMP-ASYM: lamps turn on instantly and off after 4 ticks.

## Tests

- `tests/sim/test_components.py`: lever strong/weak power, lever through a block lights a
  lamp, lever double update, stone 20 / oak 30 tick buttons, pressing a pressed button,
  popping without support.
- Game: EXP-001 (lamp on/off timing), redstone block as input in all scenarios.

## Related

[[power-queries]] · [[tick-scheduling]]
