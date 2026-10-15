# Gravity blocks and falling block entities

Sand, red sand, gravel, the 16 concrete powders, the three anvils and the dragon egg fall
when the block below them is free. In the game a falling block is an **entity**
(`FallingBlockEntity`) with real physics; the simulator ports it, with the parts of
`Entity` it uses, in `sim/entities.py` (blocks: `world/blocks/falling.py`). Verified on
the real 26.3 server tick for tick, **with exact positions and motion** of every falling
block: EXP-054 (`gravity_blocks`) and EXP-055 (`gravity_pistons`).

## When a block falls

- `FallingBlock.onPlace` and every `updateShape` schedule a tick after
  `getDelayAfterPlace()`: **2 ticks** (dragon egg: **5**).
- The tick (`FallingBlock.tick`) falls if `isFree(below)` and `y >= minY`. Free: air,
  `BlockTags.FIRE`, liquids, and replaceable blocks (`canBeReplaced()`: tall grass, …).
  A torch, a carpet, a slab or a moving piston below holds the block up.
- `FallingBlockEntity.fall`: the entity at the block's bottom center `(x+0.5, y, z+0.5)`,
  the block becomes air (`setBlockAndUpdate`: neighbors update, the block above schedules
  its own fall), then the entity joins the entity list. It ticks **in the same game tick**
  (entities tick after block ticks and block events): the first position update happens
  in the tick of the fall.

## Each tick of a falling block

`ServerLevel.tick` → `tickNonPassenger` (`commonTick`: old position) → `FallingBlockEntity.tick`
(source L148):

1. `time++`; gravity: motion.y −= 0.04 (`getDefaultGravity`).
2. `Entity.move(SELF, motion)`: collision against block collision shapes (below), then
   the collision flags; `onGround` = a vertical collision while moving down. On the
   server `isLocalInstanceAuthoritative()` is true, so the flags are recomputed on every
   move (a sideways piston push clears `onGround`). The supporting block
   (`checkSupportingBlock`) is the colliding block nearest the entity. Landing on a
   bouncy block (slime: restitution 1.0 × 0.8 for non-living entities) reverses motion
   (`restituteMovementAfterCollisions`); honey suppresses bouncing. Horizontal motion is
   multiplied by the speed factor of the block at/below the entity (honey, soul sand
   0.4).
3. `applyEffectsFromBlocks`: `stepOn` of the block below when on the ground (slime slows
   horizontal motion), then `entityInside` of every block the box passed through
   (`BlockGetter.forEachBlockIntersectedBetween`; all simulated blocks use the full block
   as their "inside" shape). Pressure plates are pressed here; honey makes entities slide
   down its sides.
4. In the air: discarded after 600 ticks (or 100 outside the build height).
   On the ground (or concrete powder in water): motion ×(0.7, −0.5, 0.7); unless the
   entity's own cell holds a **moving piston** (then it waits and tries again), it places
   its block if the cell is replaceable and the block survives and would not fall on;
   otherwise it is discarded (with the game rule `entity_drops` it would drop as an item;
   the simulator has no items, like `entity_drops false`). On landing `Fallable.onLand`:
   concrete powder hardens next to water.
5. Drag: motion × 0.98F.

Float constants follow Java exactly: the box is `0.98F` wide and high (half width
`0.98F / 2.0F`), drag `0.98F`, offsets such as `getOnPosLegacy` `0.2F`.

## Collision

`Entity.collide` → `collideWithShapes`: per axis in `Direction.axisStepOrder` (Y first,
then the larger horizontal axis), `Shapes.collide` over every block collision shape near
the swept box (`BlockCollisions`: the cursor's border cells only count for blocks with a
large collision shape, edges only for moving pistons). `VoxelShape.collideX` (L251) is
ported on a grid made from each shape's boxes. Fences, walls and closed fence gates
collide up to 1.5 blocks; a moving piston's collision shape is the moved block's shape
shifted by its progress, plus the piston base for a retracting source
(`PistonMovingBlockEntity.getCollisionShape`).

## Pistons and entities

`PistonMovingBlockEntity.tick` moves entities before each progress step
(`moveCollidedEntities`, `moveStuckEntities`):

- Entities in the area the moving block sweeps are moved by the overlap + 0.01, at most
  0.51 per axis and tick (`limitPistonMovement`), with `NOCLIP` (the piston's own moving
  blocks do not collide with them while moving that way). A retracting head also fixes
  entities inside the piston base.
- A moving **slime block** sets the entity's motion on the movement axis to ±1.0 (falling
  sand is launched upwards).
- A moving **honey block** carries entities standing on it sideways.

## Placing near falling blocks

A player cannot place a block where a falling block is (`BlockItem.canPlace` →
`isUnobstructed`: falling blocks have `blocksBuilding`); commands like `/setblock` can.

## Not as in the game

All of these are also in [[differences]] and marked in the code with `Not as in the
game:`.

- The anvil's damage on landing: when it fell more than one block the game rolls its
  per-entity random (5 % + 5 % per block) to turn it chipped or damaged; the simulator
  keeps it as it is. EXP-054 drops its anvil from 0.5 blocks so no roll happens. The
  anvil's menu.
- The dragon egg's teleport when used (the level's random): the editor refuses "use" on
  a dragon egg with a message instead of guessing a spot. Breaking it in the editor is
  creative breaking, which removes it as in the game (it teleports when hit only in
  survival).
- Concrete powder moving faster than one block per tick: the game also ray casts for
  water it passed between two positions; not ported (water is not simulated anyway).
- Item drops, other entities (falling blocks do not collide with entities), fall damage,
  water and lava: falling blocks pass foreign water like air; concrete powder still
  hardens next to water blocks of an opened world and waterlogged blocks.
- Where an entity already overlaps a block, the game's `VoxelShape` grid of that block
  (which can differ from the box split used here) decides the push-out distance.
- **Blocks the simulator does not model (foreign blocks) have no collision unless they are
  full cubes:** a falling block falls through an unmodeled bed, cauldron, snow layer or
  scaffolding, where the game lands it on top.
- The piston head's arm where it reaches into the piston base is missing from the
  collision shapes (shapes end at the block's cell; no entity fits there).
- Blocks with a `canBeReplaced` of their own (snow layers, …) are foreign: whether a
  falling block may replace them follows the game's `replaceable` flag.
- Suspicious sand and gravel (loot, brushing) and pointed dripstone stay foreign blocks.

## Ordering

Falling blocks tick in the order they were created (`EntityTickList`: insertion order),
after the editor's stand-ins for other entities (0-tick ends, projectile hits, plate
visitors) in the same entity phase.
