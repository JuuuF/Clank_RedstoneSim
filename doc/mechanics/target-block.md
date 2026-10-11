# Target block

- **Status:** researched, implemented (`src/redsim/world/blocks/target.py`), unit-tested and
  confirmed in game: dust connection, arrow and snowball hits, the placement reset
  (EXP-037), and inside 40 random circuits (EXP-031).
- **Source:** `net/minecraft/world/level/block/TargetBlock.java`; registration
  `Blocks.TARGET` (L4744: `strength(0.5F)`, default conductor predicate).

## Behavior

- `POWER` (0-15) is the output. `isSignalSource` is true, so dust connects to a target from
  any side (dust passing by bends into it), and `ownSignal` = `POWER`: a weak signal on all
  six sides. It is a full block with the default conductor predicate, so it also passes on
  strong power from other components like stone does.
- **Projectile hit** (`onProjectileHit` → `updateRedstoneOutput`): unless a reset tick is
  already pending, the target gets `POWER` = the hit strength (`setBlockAndUpdate`) and a
  tick in **20** ticks for arrows (`AbstractArrow`, including tridents) or **8** for any
  other projectile (snowball, egg, …). A second hit while powered changes nothing.
- **Hit strength** (`getRedstoneStrength`): the larger of the two in-face offsets of the hit
  point from the face center, `d` ∈ [0, 0.5], gives `max(1, ceil(15 · (0.5 − d) / 0.5))`:
  15 at the center, 1 at the edge.
- `tick`: back to 0 (`setBlockAndUpdate`).
- `onPlace` (a different block was there): placed with power and no pending tick → reset to
  0 with flags 18 (no neighbor updates, no shape updates). So `/setblock target[power=12]`
  gives an unpowered target.

## Timing in the simulator

The simulator has no projectiles. The engine action `projectile_hit` (position, strength,
duration) queues a hit in `Level.projectile_hits`; the next tick's **entity phase**
(`Phase.ENTITIES`, after block events and before block entities, as in
`ServerLevel.tick`) applies `updateRedstoneOutput`. This is where a projectile summoned
between ticks lands in the game: the first version applied the hit at once and was one tick
early against EXP-037.

Editor: select a target block; the inspector offers a hit strength and **🏹 Arrow** (20
ticks) / **❄ Snowball** (8 ticks) buttons ([[controls]]).

## Game verification (EXP-037)

`target_block`: an arrow and a snowball are summoned 1.5 blocks above two targets' top
centers with a downward motion of 3 blocks per tick, at ticks 2 and 4. The arrow's target
gives 15 from tick 3 to tick 23, the snowball's from tick 5 to tick 13; the dust beside
them and the lamps follow. A target placed with `power=12` reads 0.
