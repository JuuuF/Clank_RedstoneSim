# Cauldrons and furnaces

Two comparator sources that circuits use for fixed signal strengths, ported in
`world/blocks/cauldron.py` and `world/blocks/furnace.py`. Verified on the real 26.3 server:
EXP-062 (`cauldrons_furnaces`), block states, comparator outputs and furnace contents
compared every tick.

Why they matter: piston doors by Purplers read a full water cauldron (signal 3) that a
piston moves in front of a comparator, and furnaces holding one item (signal 1) or a
wooden shovel (signal 5, it stacks to 1) through blocks pistons move. While these blocks were
foreign (inert), those comparators read 0, so the 5x5 vault lamp door broke when it opened
and the 4x4 slime door never closed. With the ports, and the furnace contents taken from the
original saves, both doors match the server tick by tick (see "Whole doors" below).

## Cauldrons

`AbstractCauldronBlock`, `CauldronBlock`, `LayeredCauldronBlock`, `LavaCauldronBlock`:

| Block | Property | Comparator signal |
|---|---|---|
| `cauldron` | none | 0 |
| `water_cauldron`, `powder_snow_cauldron` | `level` 1–3 (default 1) | the level |
| `lava_cauldron` | none | 3 |

- Shape and collision: a full block without the inside (`column(12, 4, 16)`) and without
  the gaps between its four legs. Not a full block, so it does not conduct (EXP-062: a
  repeater into a cauldron does not light the lamp behind it).
- No block entity: pistons push and pull it like stone (EXP-062: a sticky piston moves a
  full cauldron in front of a comparator and back, and the comparator follows, 3 and 0).

## Furnaces

`AbstractFurnaceBlock` and `AbstractFurnaceBlockEntity` (furnace, blast furnace, smoker):

- Properties `facing` (horizontal, placed facing the player) and `lit` (placed unlit).
- A block entity with three slots (0 ingredient, 1 fuel, 2 result), so pistons cannot
  move it (EXP-062). The comparator signal is the container formula of
  [[analog-sources]] (barrels): the sum of `count / max stack size` over the slots, divided by 3, then
  `lerpDiscrete` to 1–15 (0 when empty). Max stack sizes come from the game's data
  generator (`world/items_data.py`, written by `tools/extract_item_table.py`): one redstone
  dust gives 1, one wooden shovel 5, 64 cobblestone and 7 stone 6, 8 ender pearls (stacks
  to 16) 3.
- Its NBT keeps the cooking timers (`cooking_time_spent`, `cooking_total_time`,
  `lit_time_remaining`, `lit_total_time`, `speed_multiplier`, `RecipesUsed`) as they were
  loaded and saves them back. Fill one with `redsim-cli container POS SLOT ITEM COUNT`, the
  editor's inspector, `/setblock … {Items:[…]}` or `/item replace block`.

## Not as in the game

Also in [[differences]] and marked in the code with `Not as in the game:`.

- Furnaces do not tick: they never burn fuel or cook (that needs the game's recipes and
  fuel values), so `lit` stays as it is and the contents change only by edits. In the game a
  furnace without an ingredient, or with an ingredient but neither fuel nor fire, does not
  change either, which is how circuits use them.
- Hoppers and droppers do not move items into or out of furnaces (the game's furnace is a
  `WorldlyContainer`: the face decides the slot, only fuel goes into slot 1).
- Nothing fills or empties a cauldron: buckets and bottles, rain and snow, dripstone, mobs
  on fire. Lava hurting mobs is not modeled either.

## Whole doors

Checked on the server with the comparison harness (scenario built from the world's tick-0
state by `/setblock`, the lever replaced by a repeater fed by a redstone block). The
recordings are not committed: the doors are third-party designs kept in the owner's
`data/` folder.

- 5x5 vault lamp door by Purplers (water cauldron, furnaces with a redstone dust and a
  wooden shovel): close and open again, 110 ticks, 716 positions: match. Ends in exactly
  its start state.
- 4x4 Slisind slime door by Purplers (0-tick pistons; four furnaces with one redstone dust
  each): closes, opens again and ends in its start state: match, 130 ticks, 888 positions.
  With empty furnaces (as an import that lost their contents left them) the door never
  closes, and the game agrees: the 0-tick pistons were never the problem.

Both are EXP-063.
