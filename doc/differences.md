# Differences from the game

The simulator's rule (owner, 2026-10-15) is that everything simulated works **exactly** like
Minecraft Java 26.3. This page lists every known place where it does not: what the game
does, what the simulator does instead, and why. It is the complete list; if something is
not here, it is meant to match the game exactly (and a mismatch is a bug).

In the source, each of these is marked where it happens with a comment or docstring that
starts with **`Not as in the game:`** (`grep -rn "Not as in the game" src`). Module
docstrings sum up the differences of their module. Every entry here names the place.

Why things differ, in short: some game mechanics are **random** (the simulator cannot know
the game's random numbers), some belong to systems the simulator does **not model at all**
(water, items, mobs, light), and some are **editor stand-ins** for things only a player or
an entity could do.

## 1. Not modeled at all (whole systems)

| System | In the game | In the simulator | Consequences |
|---|---|---|---|
| Water and lava | Flow, waterlog, push entities, put out fire | Water blocks of an opened world are foreign (inert); `waterlogged` is kept as a property but schedules no fluid tick | Nothing flows. Concrete powder still hardens next to water blocks and waterlogged blocks (`falling.py`); campfires placed into water are unlit (`campfire.py`) |
| Item entities | Popped blocks, failed falling blocks, cooked food, dispensed and dropped items become items on the ground | No items exist; such things just disappear | Hoppers never pick up items from the ground; an item on a wooden plate never presses it. The test server runs with `block_drops false` and `entity_drops false` so the game matches ([[experiments/index]]) |
| Mobs, players, minecarts, boats, projectiles | Entities that press plates, trigger tripwires, ride rails, collide | Only falling blocks are entities (`sim/entities.py`); the rest are editor stand-ins (section 3) | No detector rails, no tripwires, no entity collisions |
| Light | Light levels, daylight | Not computed | No daylight sensors; light does not matter for any simulated block |
| Random ticks | Leaf decay, copper oxidation, grass spreading, crops, redstone ore cooling | None (the test server runs with `random_tick_speed 0`) | Leaves keep their `distance` updates but never decay (`catalog.py`) |
| Weather, time of day | Rain, day/night | None | Daylight sensors not simulated |
| Sounds, particles, game events | Sounds, vibrations (sculk sensors) | None | No sculk sensors |
| Menus and items in hand | Anvils, crafting, using items on blocks | The editor has no items in hand: `use` is an empty-hand click | Flint and steel, shovels, buckets, food on campfires, bone meal… are not available |
| Explosions | TNT, wind charges | None | TNT is a foreign block |
| Blocks not modeled yet | Their own mechanics | **Foreign blocks** (`foreign.py`): kept as text, drawn with the game's model, inert; pistons treat them by the game's table; their shape is a full cube or nothing (guessed from the name) | A non-full foreign block (bed, snow layer, scaffolding, …) supports nothing and has **no collision**: falling blocks fall through it |
| Idle server | Entities and block entities stop after 300 ticks without players (`emptyTime`) | Always ticking | — |
| Experimental redstone | `redstone_experiments` changes | Not in scope (ADR-006) | — |

## 2. Random in the game

The simulator cannot reproduce the game's random numbers (per-entity and per-level random
sources seeded at startup). Where the game rolls dice:

| Mechanic | In the game | In the simulator | Where |
|---|---|---|---|
| Dispenser / dropper slot | A random non-empty slot (`getRandomSlot`, the level's random) | Its own random source, seeded with game time and position (a replay gives the same choice). Exact when only one slot is filled | `dispenser.py`, [[mechanics/dispensers-and-chests]] |
| Anvil landing damage | After a fall of more than one block: 5 % + 5 % per block chance to become chipped, then damaged, then to break (the falling entity's random) | The anvil always lands unchanged | `falling.py` `AnvilBlock.falling`, `sim/entities.py` item 2, [[mechanics/gravity-blocks]] |
| Dragon egg teleport | Using it teleports it to a random free spot within 15 blocks | The editor refuses "use" on a dragon egg with a message | `falling.py` `DragonEggBlock.use_without_item` |
| Composting | Each compostable item adds a layer only by chance | Not available (no items in hand; editor container items are not compostable) | `composter.py` |

## 3. Editor stand-ins (not game mechanics)

These let you do in the editor what only players and entities can do in the game. They
are recorded as edits on the timeline and replayed exactly, but they are not the game's
own mechanics.

| Stand-in | Replaces | How it works | Where |
|---|---|---|---|
| Plate visitors | Mobs and items standing on a pressure plate | A number of mobs and of other entities on a plate from the next tick on, for some ticks; the plate is pressed in the entity phase and released at its next recheck | `pressure_plate.py`, `Level.plate_visitors`, [[mechanics/pressure-plates]] (game-checked with real armor stands and items, EXP-046) |
| Projectile hits | Arrows and snowballs hitting a target block | The hit lands in the next tick's entity phase with the chosen strength, power for 20 ticks (arrow) or 8 | `target.py`, `Level.projectile_hits` (EXP-037) |
| Sequence pulses | Nothing in the game | Power locked to a position, like an invisible redstone block next to it from every side, for a number of ticks | `Level.forced_power`, ADR-026 |
| 0-tick pulses | Nothing directly (contraptions make them) | On at the start of a tick, off right after its block events, inside one tick | `Level.zero_tick_pulses` |
| Container slots, sign text, sources | `/item replace`, `/setblock … {…}`, a player writing a sign | Applied with the commands' semantics (`setChanged`, comparators update) | `engine.py` actions |
| Editing the history | Nothing in the game | Edits inside the recorded history keep the later ones and re-run (ADR-022) | `editor/document.py` |
| Settling the build (`redsim-cli settle`) | Nothing in the game | The build simulated alone until quiet becomes the new build (the editor's "Set tick 0 here" without moving the timeline) | `editor/document_history.py` |
| Placing with a given orientation (`redsim-cli place`, the editor's look) | The player's look direction and clicked point decide `facing`, `face`, `half`, `axis`, a door's `hinge` | The orientation is given directly; every other property follows the block's `getStateForPlacement` (power, shapes, neighbors), and properties a player sets by right-clicking are set with real right-clicks (`place`). An orientation a player could not get at that spot (a door hinge against its neighbors) is possible | `world/block.py` `PlacementContext`, `cli/commands/build.py` |
| Truth-table inputs (`redsim-cli target … truth`) | A player or a circuit switching the input | A lever input is flipped with `use` (a player); any other input gets a sequence power pulse (editor power) | `cli/targets.py` |

Order inside the entity phase: the editor's stand-ins (0-tick ends, projectile hits,
plate visitors) come before falling blocks, which tick in the order they were created. In
the game every entity has its place in one list by creation order, so a stand-in and a
falling block that act on the same block in the same tick may come in another order there
(`engine.py`).

## 4. Differences in simulated blocks and entities

| Block / mechanic | In the game | In the simulator | Where |
|---|---|---|---|
| Pressure plates (pressed) | Pressed shape half a pixel high | One pixel (plates have no collision; nothing rests on them, so no outcome changes) | `pressure_plate.py` |
| Lectern | Slanted top in its outline shape | Flat (support and collision use the exact collision shape) | `lectern.py` |
| Falling blocks: items | A block that cannot land drops as an item | It disappears (as with `entity_drops false`) | `sim/entities.py` item 1 |
| Falling blocks: fall distance | Kept; `Block.fallOn` called on landing | Not kept (only matters for the anvil damage above and hurting mobs) | `sim/entities.py` item 2 |
| Falling blocks: collision shapes | The blocks' `VoxelShape`s | Boxes from the voxel shapes (fences, walls, gates raised to 1.5); the piston head's arm inside the base is left out; foreign non-full blocks have none; the collision grid is made from the boxes (differs only for an entity already inside a block) | `sim/entities.py` item 3 |
| Falling blocks: concrete powder in water | Also ray casts for water it passed when moving faster than one block per tick | Only checks the water where it is | `sim/entities.py` item 5 |
| Falling blocks: slowing blocks | Cobwebs, berry bushes, powder snow slow entities; fire burns them | Those blocks are foreign | `sim/entities.py` item 5 |
| Campfire: cooking | Cooked food drops as an item | It leaves the campfire and disappears | `campfire.py` |
| Campfire: water | A waterlogged campfire schedules a water tick | No water tick | `campfire.py` |
| Comparator | Reads an item frame behind a block | Item frames do not exist: that input is always absent | `comparator.py` |
| Trapped chest | Signal = players looking in | Always 0 | `chest.py` |
| Chest blocked by a cat | Cats sitting on it block it | Only conductors on top block it | `chest.py` |
| Dispenser | Each item has its behavior (arrows, buckets, TNT, bone meal, …) | One item leaves; nothing else happens | `dispenser.py` |
| Hopper | Also picks up item entities above | Only containers above | `hopper.py` |
| Note block | Plays a custom head's sound | A head's block entity is not simulated: fails like a head without a sound | `note_block.py` |
| Sign | Block entity ticker (who may edit) | No ticker (no effect on the world) | `sign.py` |
| Buttons | Arrows hold wooden buttons down | No arrows | `attached.py` |
| Rails | Detector rails (need minecarts); waterlogged rails | Not simulated; `waterlogged` always false | `rail.py` |
| Doors, trapdoors, gates, fences, walls | Wind charges open doors; water; leads on fences | Not simulated | `openable.py`, `connecting.py` |
| Catalog blocks | Silverfish in infested blocks; carved pumpkins making golems; ice turning into water when broken; sponges | Not simulated (carved pumpkins and jack o'lanterns stay foreign) | `catalog.py` |
| Copper bulbs | Oxidation (random ticks), light level | Not simulated (all oxidation stages behave the same, as in the game's logic) | `copper_bulb.py` |
| Composter | Composting items | Not available | `composter.py` |
| Furnace, blast furnace, smoker: cooking | Burn fuel and cook the ingredient (recipes, fuel values); `lit` follows | They do not tick: nothing burns or cooks, `lit` stays as it is, contents change only by edits (as in the game when there is no ingredient, or neither fuel nor fire) | `furnace.py` |
| Furnace, blast furnace, smoker: hoppers | Hoppers and droppers fill them by face (top: ingredient, sides: fuel only) and take the result from below | Hoppers and droppers leave furnaces alone | `furnace.py`, `hopper.py` (`container_at`) |
| Cauldrons | Buckets, bottles, rain, snow, dripstone and burning mobs change the level; lava hurts mobs | The level changes only by edits | `cauldron.py` |
| Scheduled ticks | Overdue ticks (more than 65 536 due) are merged per chunk | Reported but not merged per chunk (cannot happen in scope) | `sim/ticks.py` |

## 5. Opened Minecraft worlds

| Topic | In the game | In the simulator | Where |
|---|---|---|---|
| Foreign blocks | Their own behavior | Inert, full cube or nothing by name (see section 1) | [[world-import]] |
| Chunks streamed in later | Loaded with their pending ticks | They join as if always loaded; their pending scheduled ticks are not imported (only those of the first area) | [[world-import]] |

## Keeping this page right

- Porting a mechanic: list its differences before committing, mark each in the code with
  `Not as in the game:` and add it here (and to the mechanics page's own section).
- A difference that gets fixed: remove its row and the code marker in the same commit.
- Verification: the server comparisons ([[experiments/index]]) are designed around these
  differences (for example, the anvil in EXP-054 falls only half a block, so no random
  damage roll happens; the test server runs with `entity_drops false`).
