# Dispensers, droppers and chests

## Dispenser and dropper (`DispenserBlock.java`, `DropperBlock.java`)

- `neighborChanged` L77: triggered by power at the block itself **or the block above**
  (quasi-connectivity); on the rising edge `triggered=true` (flags 2) and a 4-tick
  scheduled tick dispenses; on the falling edge only `triggered=false`.
- `getRandomSlot`: reservoir sampling over the non-empty slots with the level's random
  source. With one stack this is exact. With several the game itself is random; the
  simulator draws from its own random source, seeded with the game time and position
  (a replay gives the same choice).
- Dropper: one item into the container in front (`HopperBlockEntity.addItem`), else it is
  dropped. The slot is always rewritten (`setItem`: comparators notified even if nothing
  moved).
- Dispenser: every item uses the default behavior in the simulator (one item leaves);
  arrows, buckets, bone meal, TNT etc. have effects in the game (entities, fluids) that
  are not simulated.
- Comparators read the container fill; 9 slots.

## Chest and trapped chest (`ChestBlock.java`, `DoubleBlockCombiner`, `CompoundContainer`)

- Properties `facing`, `type` (single/left/right), `waterlogged` (always false here).
- Placing beside a single chest facing the same way joins it (`getChestType`); `updateShape`
  joins a half that points here and splits when the partner goes.
- A double chest is one 54-slot container, the `right` half first; changes notify
  comparators at both halves (`CompoundContainer.setChanged`).
- **Blocked chests:** a redstone conductor on top of either half makes `getContainer`
  return nothing for comparators (signal 0). Hoppers and droppers ignore blocking.
- Trapped chest: a signal source of strength 0 here (its signal counts players looking
  in, not simulated); redstone wire still points at it.
- Drawn from the chest entity texture (the game uses a block-entity renderer): a base, a
  lid and a latch, turned by `facing` (`ui/assets.py chest_model`).

Status: implemented (`world/blocks/dispenser.py`, `chest.py`). Tests:
`tests/sim/test_dispenser.py`, `test_chest.py`; game EXP-044 (`droppers`), EXP-045
(`chests`), both comparing container contents.
