# Analog sources: barrel, lectern, cake

- **Status:** researched, implemented, unit-tested and confirmed in game: barrel
  (EXP-024), lectern (EXP-025), cake (EXP-012/013). The lectern's page-turn pulse is
  verified from the source only: the test server has no player to turn pages.
- **Code:** `src/redsim/world/blocks/container.py`, `lectern.py`, `cake.py`; editor
  `src/redsim/editor/sources.py`. Paths below are relative to
  `data/minecraft_src/client-src/net/minecraft/`.

A comparator reads the block behind it with `getAnalogOutputSignal` when that block has
one ([[comparator]]). The editor exposes these blocks as one "signal source" with a chosen
strength ([[controls]]); the real block underneath keeps the simulation exact.

## Barrel (container)

- `world/inventory/AbstractContainerMenu.java` `getRedstoneSignalFromContainer` L766:
  `f = Σ count / maxStack(slot) / slots` in **32-bit float**, then `Mth.lerpDiscrete(f, 0,
  15)` = `floor(f · 14) + (f > 0 ? 1 : 0)` (`util/Mth.java` L545).
- `world/Container.java` L34-40: a slot holds at most `min(99, item max stack)`; 64 for
  most items, 16 for ender pearls etc.
- Thresholds for 27 slots of 64-stacks: 1, 124, 247, 371, 494, 618, 741, 864, 988, 1111,
  1235, 1358, 1482, 1605, 1728 items for signals 1-15 (unit test and EXP-024).
- `world/level/block/entity/BaseContainerBlockEntity.java` `setItem` L126: store, limit the
  count, `setChanged` → `updateNeighbourForOutputSignal` (`BlockEntity.java` L198). So each
  `/item replace` (or hopper/player change) updates comparators; they then follow their
  own 2-tick delay.
- `world/level/block/BarrelBlock.java`: full solid block (conducts), facing from the
  nearest look direction (like pistons), removal updates comparators
  (`Containers.updateNeighboursAfterDestroy`). Pistons cannot move it (block entity).
- Float32 search: for 64-stack fills from 1 to 1 728 items the float result equals exact
  arithmetic everywhere (no rounding quirk in this range).

## Lectern (book page)

- `world/level/block/entity/LecternBlockEntity.java` `getRedstoneSignal` L172:
  `floor(page / (pageCount − 1.0F) · 14.0F) + 1` (float), with progress 1 when the book
  has at most one page. `world/level/block/LecternBlock.java` L197: 0 unless `HAS_BOOK`.
  So a 1-page book gives 15, and a block whose state says `has_book=false` gives 0 even
  with a book in its data (EXP-025).
- `loadAdditional` L196: `Page` is clamped to the book (`Mth.clamp`, so a page past the end
  reads as the last page; EXP-025 uses page 20 of 10 → 15).
- Turning a page (`setPage` L159, a player in the lectern menu): `setChanged` (comparator
  update) and `signalPageChange` L148: `POWERED` on, a scheduled tick in 2, neighbor updates
  around the block below. While powered the lectern gives weak power 15 around it and
  strong power 15 into the block below (`ownSignal`/`getDirectSignal` L182-189).
- Not a full block (no conduction); pistons cannot move it (block entity). The slanted top
  of its outline shape is not modeled (collision shape is exact).

## Cake

`(7 − bites) · 2`: even values 2-14 only; needs a solid block below; popped by pistons
([[block-properties]]). Eating (right click) changes it.

## Editor operations

| Operation | Game equivalent | Verified |
|---|---|---|
| Place or change a source | `/setblock <pos> <state>{<data>}`: `BlockInput.place` loads the data and calls `setChanged` only if it changed (`commands/arguments/blocks/BlockInput.java` L79) | game (EXP-024, EXP-025) |
| Change one barrel slot | `/item replace block <pos> container.<n> with <item> <count>` | game (EXP-024) |
| Turn a lectern page | player in the lectern menu (`setPage`) | source only |

Barrels are filled with the fewest redstone dust for a strength; lecterns get a 15-page
writable book open at page `strength − 1`.
