# Hopper

- **Status:** researched, implemented (`src/redsim/world/blocks/hopper.py`), unit-tested and
  confirmed in game, contents and cooldowns compared every tick: chains and stack sizes
  (EXP-038), redstone locking (EXP-039), facing pairs and pull-while-pushed (EXP-040),
  `/item replace` (EXP-041), and inside 40 random circuits (EXP-031).
- **Source:** `net/minecraft/world/level/block/HopperBlock.java`,
  `net/minecraft/world/level/block/entity/HopperBlockEntity.java`, `Hopper.java`;
  containers: `BaseContainerBlockEntity.java`, `ContainerHelper.java`;
  registration `Blocks.HOPPER` (L2985, `strength(3.0F, 4.8F)`).
- **Scope:** block containers only (hoppers and barrels; no chests, composters, minecarts
  or item entities in the simulator).

## Block

- `FACING` (`FACING_HOPPER`: down, north, south, west, east) is where the spout points;
  placement uses the clicked face reversed, and up becomes down. `ENABLED` is the lock.
- `checkPoweredState` (from `onPlace` when a different block was there, and from every
  `neighborChanged`): `ENABLED = !hasNeighborSignal(pos)`, set with flags 2 (no neighbor
  updates, but shape updates, so observers see it).
- Shape: a bowl (16×16, y 10-16, hollow inside 12×12 from y 11), a funnel (8×8, y 4-10)
  and a spout. Not a full block, so **not a conductor**; the top face has only rigid
  support, so torches cannot stand on it, but dust can (`RedstoneWireBlock.canSurviveOn`
  names the hopper).
- Comparator output: the fill level (`getRedstoneSignalFromContainer`, the same formula as
  barrels, over 5 slots). Removal updates comparators. A block entity: pistons cannot move
  it.

## Block entity: the transfer cycle

Every game tick, in the block-entity phase in registration order ([[tick-scheduling]],
Q-BE-ORDER), `pushItemsTick`:

1. `cooldownTime − 1`; remember the game time (`tickedGameTime`).
2. If the cooldown is ≤ 0: set it to 0, and if the hopper is **enabled**:
   - not empty → `ejectItems`: one item into the container the spout points at, unless
     every slot there is full; the hopper's slots are tried in order and the first item
     that fits anywhere moves;
   - not full (every slot a full stack) → `suckInItems`: one item from the container above,
     its slots in order, the first that fits;
   - if either moved: cooldown **8** and `setChanged` (comparators update).

So a locked hopper keeps its cooldown at 0 and moves at the first tick after unlocking. A
new hopper starts at −1 and moves at its first tick.

`tryMoveInItem`: an empty slot takes the item, a stack of the same item grows up to the
item's maximum (64, 16 for ender pearls and snowballs, 1 for tools). When a hopper that
was **empty** receives an item, its cooldown becomes 8, or **7** if it has already ticked
in this game tick at least as late as the sending hopper (`tickedGameTime ≥` the
sender's). The rule makes chains move one item per 8 ticks whatever the ticker order: a
receiver that ticks after the sender loses one tick of its 8 in the same game tick.

`HopperBlockEntity.setItem` and `removeItem` do **not** call `setChanged`, unlike other
containers. Moving items notifies comparators anyway (`setChanged` on the receiving
container and at the end of `tryMoveItems`), but `/item replace` into a hopper does not:
a comparator reading it keeps its old value until something else updates it
(Q-HOPPER-ITEM-REPLACE, EXP-041).

`tickedGameTime` is not saved in NBT. The simulator keeps it in its own saves
(`BlockEntity.runtime_json`), not in the block-entity data that `/clone` copies, as in the
game.

## Editor

Inventory folder **Items**. The inspector's **Contents** row edits any barrel or hopper
slot: slot number, item (redstone dust, stone, ender pearl, wooden sword), count, **Set**,
and **Empty all slots**; each is one `/setblock` with the block-entity data (comparators
update, the hopper keeps its cooldown). A locked hopper is drawn with a red bowl floor. The
F3 screen shows contents and cooldown.

## Game verification

| EXP | Scenario | What it pins down |
|---|---|---|
| EXP-038 | `hopper_chain` | barrel → 3 hoppers → barrel, 5 dust then 3 ender pearls; the third hopper ticks before the second; contents, cooldowns (8/7) and comparators every tick |
| EXP-039 | `hopper_lock` | locks from a redstone block beside, a 0-tick lock, a block on top; an observer sees the lock changes |
| EXP-040 | `hopper_clock` | two hoppers facing each other; a fed pair whose lower hopper also pulls from the one above |
| EXP-041 | `hopper_item_replace` | `/item replace` updates a barrel's comparator but not an idle hopper's |

Sensitivity: with the 7-tick rule removed, `hopper_chain` fails from tick 16 and
`hopper_clock` from tick 9; with a notifying `setItem`, `hopper_item_replace` fails from
tick 4.
