# Composters and signs

Two blocks added on 2026-10-14 (owner's open list O6/O7 and O4). Code:
`world/blocks/composter.py`, `world/blocks/sign.py`. Game-verified: EXP-048 (signs),
EXP-049 (composters).

## Composter (`ComposterBlock.java`)

- `level` 0–8; 8 means "ready". A comparator reads the level (`getAnalogOutputSignal`).
- Placed at level 7 (`onPlace`), or reaching 7, it schedules a tick in **20 ticks**; the
  tick turns 7 into 8 with `setBlockAndUpdate` (comparators around update).
- A player's right click on a full composter empties it (`useWithoutItem` →
  `extractProduce`: the bone meal item entity is not simulated).
- A **hopper below** a full composter takes its bone meal at once (the composter's
  `OutputContainer`; its `setChanged` empties the composter). Levels below 7 offer an
  input container that only takes compostable items, which the editor does not offer
  (composting adds a layer only by chance, so it could not be simulated exactly).
- Shapes: a full block hollowed by a 12-wide column from `max(2, 1 + 2·level)` up; the
  collision shape is always the level-0 one. It counts as solid (`isSolid`), does not
  conduct (not a full collision cube), and pistons move it (no block entity).

## Signs (`SignBlock`, `StandingSignBlock`, `WallSignBlock`, `SignBlockEntity`)

- Standing signs (`rotation` 0–15, default 8 in 26.3) need a **solid** block below;
  wall signs (`facing`) a solid block behind. Without it they become air in
  `updateShape` (they pop).
- Signs are `forceSolidOn`, have no collision, and have a block entity: pistons cannot
  push them (the piston stays retracted). A sign on a block that a piston moves stays:
  the moving block and then the piston head count as solid.
- Placement (`StandingAndWallBlockItem` with attachment down): looking down first gives a
  standing sign turned to face the player (`RotationSegment.convertToSegment(yRot +
  180)`); else the first wall in the nearest looking directions.
- Text: front and back, 4 lines each, in the block entity; `updateSignText` calls
  `setChanged` (comparators around re-read their input). Hanging signs are not simulated
  (foreign blocks).
