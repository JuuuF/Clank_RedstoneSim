# Campfires

`CampfireBlock.java` and `CampfireBlockEntity.java`, ported in `world/blocks/campfire.py`
(campfire and soul campfire). Verified on the real 26.3 server: EXP-056 (`campfires`), block
states, food slots and cooking progress compared every tick.

## Block

- Properties in the game's order: `lit` (default true), `signal_fire`, `waterlogged`,
  `facing`. Placed by a player: facing the player's horizontal direction, `signal_fire` if
  a **hay bale** is right below, unlit and waterlogged when placed into water
  (`getStateForPlacement`).
- `updateShape`: from below, `signal_fire` follows whether the block below is a hay bale.
  That is a shape update, so an observer facing the campfire fires when a hay bale is put
  under it or taken away (EXP-056).
- Shape and collision `Block.column(16, 0, 7)`: not a full block, so it never conducts
  (a torch below does not power a lamp through it) and nothing is sturdy on its top. A
  falling block lands in its cell and breaks ([[gravity-blocks]]).
- It has a block entity, so pistons cannot move it (`isPushable`: blocks with a block
  entity stay; EXP-056: a piston facing a campfire does not extend).

## Block entity: cooking

Four food slots (`Items`), each with its progress (`CookingTimes`) and cooking time
(`CookingTotalTimes`). The ticker depends on `lit` (`getTicker`):

- lit, `cookTick`: every food's progress grows by 1; when it reaches its cooking time the
  slot empties (the game drops the result as an item entity; items are not simulated) and
  the progress keeps its value;
- unlit, `cooldownTick`: progress drops by 2 (not below 0).

Any change calls `setChanged`, which updates comparators around it. Players put food on a
campfire with an item in hand, which the editor cannot do; `/setblock` data can
(`campfire{Items:[…],CookingTotalTimes:[I;…]}`; a given array overwrites as many slots as
it has, a missing one is zeroed, as `loadAdditional` does).

## Not modeled (stated)

Light, smoke and particles, hurting mobs (`entityInside`), lighting and dousing with items
(flint and steel, fire charges, shovels, water bottles), burning projectiles lighting it,
water (a waterlogged campfire's water does not flow: the water tick it schedules is not
simulated), beehives calmed by smoke (`isSmokeyPos`).
