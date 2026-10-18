# In-game experiments

Comparisons between the simulator and the real Java Edition 26.3 game. On 2026-10-10 the
owner approved running the supplied dedicated server headlessly for testing only, and
accepted the Minecraft EULA for that sandbox. Experiments run automatically through
`tools/gameserver` ([[decisions]] ADR-008, [[implementation-notes]]).

## Method

- **Server:** `data/minecraft_jars/server.jar` (the 26.3 bundler, only read). It runs in the
  gitignored sandbox `.sandbox/gameserver/` with a fresh superflat world per run. Offline
  mode, bound to 127.0.0.1, no RCON/query/status/management endpoints, peaceful.
- **World setup:** game rules `random_tick_speed 0`, `advance_time false`,
  `advance_weather false`, `spawn_mobs false`; the scenario area is force-loaded so blocks and
  block entities tick without players (`TicketType.FORCED` keeps the level active;
  `pause-when-empty-seconds=0`).
- **Terrain:** each scenario gets bedrock at y=-64, stone at -63..-62, and a stone floor at
  -61, using `fill … strict` (no updates). The simulator builds identical columns.
- **Timing:** `/tick freeze`, then `/tick step 1` per game tick, waiting until
  `/time query gametime` has advanced. Commands run between ticks, like player actions.
- **Inputs:** `/setblock` commands (mostly redstone blocks placed/removed). The simulator
  mirrors them with `Action("setblock")`, a port of `SetBlockCommand.setBlock` +
  `BlockInput.place` + `ServerLevel.updateNeighboursOnBlockSet`. Scenarios can also issue
  `/fill` and `/clone`, mirrored by `Action("fill")` and `Action("clone")`.
- **Observation:** after every tick, the simulator's predicted full state of each watched
  block is tested in game with `execute if block`. A failed test is resolved by testing
  each candidate block and property value, so the report shows the game's real state.
- **Evidence:** `experiments/results/<scenario>.json` holds every tick's simulator and game
  states, the origin, start game time, and a scenario fingerprint.
  `tests/sim/test_game_verified.py` replays each recording offline and fails if the
  simulator diverges or the scenario definition changed (stale evidence).
- **Sensitivity check (2026-10-11):** with the lamp's off-delay deliberately changed to 3 in
  the simulator, the harness reported a mismatch at exactly the affected tick. A match
  therefore means agreement, not an insensitive comparison.

Limits: only tick-boundary states are observable, not sub-tick order. Levers and buttons
cannot be operated without a player, so player-interaction paths are verified by source
reading and unit tests only.

## Results

| ID | Scenario | Ticks | Result | Date |
|---|---|---|---|---|
| EXP-001 | `lamp_redstone_block`: lamp on at once, off 4 ticks after its source is removed | 10 | match | 2026-10-11 |
| EXP-002 | `torch_inverter`: wire powers a block; the torch on top inverts after 2 ticks | 12 | match | 2026-10-11 |
| EXP-003 | `wire_line_lamp`: 15 wires decay 15→1, the lamp stays lit; all drop together | 10 | match | 2026-10-11 |
| EXP-004 | `and_gate`: torch AND gate; output and lamp on only with both inputs on | 30 | match | 2026-10-11 |
| EXP-005 | `torch_burnout`: self-oscillating torch burns out after 8 turn-offs and **stays out** | 260 | match | 2026-10-11 |
| EXP-006 | `torch_burnout_update`: an update more than 60 ticks later relights it; it burns out again | 140 | match | 2026-10-11 |
| EXP-007 | `glass_up_not_down`: wire climbs onto glass from either side, never descends | 4 | match | 2026-10-11 |
| EXP-008 | `repeater_delays`: delays 1–4 give 2/4/6/8 ticks on and off | 30 | match | 2026-10-11 |
| EXP-009 | `repeater_pulse_extension`: a 1-tick pulse into a delay-4 repeater becomes 8 ticks | 24 | match | 2026-10-11 |
| EXP-010 | `repeater_lock_priority`: same-tick race; the locking repeater (scheduled second) wins by priority | 14 | match | 2026-10-11 |
| EXP-011 | `repeater_chain`: three delay-1 repeaters add 2 ticks each | 20 | match | 2026-10-11 |
| EXP-012 | `comparator_modes`: cake input, wire side input, compare → side wins → subtract | 20 | match | 2026-10-11 |
| EXP-013 | `comparator_through_block`: reads cake through stone; strong power 15 on the stone skips the lookup | 16 | match | 2026-10-11 |
| EXP-014 | `comparator_side_torch`: a lit torch beside it is not a side input; powered wire is | 12 | match | 2026-10-11 |
| EXP-015 | `piston_push_pull`: normal and sticky piston push a block; only the sticky one pulls it back | 14 | match | 2026-10-11 |
| EXP-016 | `sticky_short_pulses`: 1- and 2-tick pulses leave the block behind, a 3-tick pulse pulls it back | 12 | match | 2026-10-11 |
| EXP-017 | `piston_qc_bud`: QC-powered piston extends only after a later neighbor update | 10 | match | 2026-10-11 |
| EXP-018 | `piston_door`: 1×2 QC door; the top piston's update wakes the bottom one in the same tick | 14 | match | 2026-10-11 |
| EXP-019 | `slime_branch_push`: slime drags attached stone (top and side), honey stays; pulled back together | 12 | match | 2026-10-11 |
| EXP-020 | `piston_pops_components`: dust on a pushed block pops, a torch in the push line is destroyed | 6 | match | 2026-10-11 |
| EXP-021 | `clone_inverter`: a torch inverter copied with `/clone`; the copy settles and reacts like the original | 14 | match | 2026-10-11 |
| EXP-022 | `fill_removes_line`: `/fill` air cuts a powered wire line; the rest depowers, the torch relights | 8 | match | 2026-10-11 |
| EXP-023 | `clone_move_running`: `/clone … replace move` of a repeater with a pending tick (the tick is copied; the moved repeater turns on at its old trigger time) and of a powered wire line onto itself (overlap) | 16 | match | 2026-10-11 |
| EXP-024 | `barrel_signals`: comparators read barrels at the 1/2, 7/8 and 14/15 fill thresholds and an ender-pearl fill; `/item replace` changes update them after the comparator delay | 12 | match | 2026-10-11 |
| EXP-025 | `lectern_signals`: lecterns with 1-100 page books at various pages (incl. a clamped page), no book, and `has_book=false` with a book | 4 | match | 2026-10-11 |
| EXP-026 | `clone_strict_bud`: a budded (QC-powered, never updated) piston cloned with `/clone … strict` stays budded; a normal `/clone` makes the copy extend; a strict move keeps it budded | 8 | match | 2026-10-11 |
| EXP-027 | `zero_tick_inputs`: 0-tick pulses (redstone block placed and removed at one boundary) at a piston, a sticky piston, a repeater, a comparator, a torch, a lamp and dust: pistons ignore them (the extend event finds no power), the repeater stretches them into a full pulse, the torch ignores them, the lamp and comparator flash | 24 | match | 2026-10-11 |
| EXP-028 | `piston_race`: two pistons push into one free cell in the same tick: the one powered first (first block event) wins, in both orders; a piston powered, unpowered and powered again at one boundary moves once (block-event dedup) | 12 | match | 2026-10-11 |
| EXP-029 | `wire_grid`: a 6×6 dust carpet powered from corners and edges at different ticks, with lamps: dust update order and shapes in a dense grid | 20 | match | 2026-10-11 |
| EXP-030 | `torch_tower`: a 4-stage torch tower (repeater-driven) with short and long pulses, then 3-on/3-off toggling until the bottom torch burns out at tick 64 | 90 | match | 2026-10-11 |
| EXP-031 | `fuzz_1` … `fuzz_40`: 40 seeded random circuits (every supported block, 2 layers, 4 toggled inputs with 0-tick pulses, 10 live edits inside the circuit), whole volume compared for 50 ticks | 50 each | match | 2026-10-11 |
| EXP-032 | `observer_clock`: two observers facing each other oscillate, lamps behind them follow | 30 | match | 2026-10-11 |
| EXP-033 | `observer_detects`: observers watching dust being powered, a lamp, a piston extending, and a chain of four observers fired by a placed block; lamps and dust behind. First run found the simulator treated observers as conductors | 24 | match | 2026-10-11 |
| EXP-034 | `observer_pushed`: a sticky piston moves a pulsing observer back and forth (placement and removal rules) | 24 | match | 2026-10-11 |
| EXP-035 | `rail_shapes`: plain rails: straight line, corner, a T junction switching to a curve when a redstone block powers it, a slope up a step | 10 | match | 2026-10-11 |
| EXP-036 | `powered_rails`: 12 powered rails fed from one end power exactly 9 (8 past the first), the same for activator rails, a mixed line stops at the activator rail; all turn off when the inputs go | 12 | match | 2026-10-11 |
| EXP-037 | `target_block`: an arrow (tick 2) and a snowball (tick 4) hit two targets' top centers: power 15 from tick 3 to 23 and from 5 to 13; dust bends into the targets, lamps follow; a target set with `power=12` reads 0. The first simulator version applied hits between ticks (one tick early); hits now land in the entity phase | 34 | match | 2026-10-11 |
| EXP-038 | `hopper_chain`: a barrel (5 dust, 3 ender pearls) feeds three hoppers into a second barrel, the third hopper registered before the second; contents, transfer cooldowns and comparators compared every tick | 90 | match | 2026-10-11 |
| EXP-039 | `hopper_lock`: a redstone block beside the first hopper (ticks 10-30), a 0-tick lock on the second (tick 40), a redstone block on top of the second (50-60); an observer watching the first hopper fires on each lock change | 80 | match | 2026-10-11 |
| EXP-040 | `hopper_clock`: two hoppers facing each other pass 4 items back and forth; a barrel above a down hopper feeds a second facing pair whose lower hopper also pulls from the one above | 80 | match | 2026-10-11 |
| EXP-041 | `hopper_item_replace`: `/item replace` of 64 dust into an idle hopper, a barrel and a hopper facing a barrel: the barrel's comparator updates at once, the idle hopper's only after a block placed beside the comparator (tick 10 → 12), the third when the hopper moves its first item | 16 | match | 2026-10-11 |
| EXP-042 | `note_blocks`: instruments from the block below (stone, glass, planks, wool), powered by a redstone block and through a repeater, an observer watching one, power from above with a block on top | 24 | match | 2026-10-12 |
| EXP-043 | `copper_bulbs`: T flip-flop toggling, comparator reading 15 into a lamp, bulbs never conduct, a bulb placed next to power lights | 30 | match | 2026-10-12 |
| EXP-044 | `droppers`: a dropper feeds a hopper chain into a chest per rising edge; a dispenser fires after a later neighbor update (QC); container contents compared | 40 | match | 2026-10-12 |
| EXP-045 | `chests`: a barrel and hopper fill a double chest; comparators on both halves; a block on one half blocks both readings; a trapped chest beside wire; contents compared | 60 | match | 2026-10-12 |
| EXP-046 | `pressure_plates`: armor stands and items (real entities) on stone, oak and weighted plates; pressed next tick, released at the recheck | 60 | match | 2026-10-12 |
| EXP-047 | `piston_scheduled_pulses`: sticky pistons on pulses that start and end in scheduled ticks (`isHandlingTick`): a 2-tick pulse through a 1-tick repeater spits the block; observer-driven pistons push, pull and re-trigger their observers through the moving blocks; states and extension progress compared | 30 | match | 2026-10-12 |
| EXP-048 | `signs`: standing and wall signs on stones pushed by pistons stay (moving blocks and heads count as solid); a sign in front of a piston stops it (block entity: not pushable); standing and wall signs pop when their support is removed | 6 | match | 2026-10-14 |
| EXP-049 | `composters`: level 7 becomes 8 after 20 ticks (comparator output compared), a hopper below a full composter takes the bone meal and the composter empties, a piston pushes a composter | 24 | match | 2026-10-14 |
| EXP-050 | `mirrored_qc_furnaces` (the owner's "simulation_bug" world): slime and honey carry sticky pistons onto quasi-powered spots in two mirrored halves; both extend on arrival. Furnaces beside the slime stay (block entities are never moved: `isPushable`); the simulator had treated the unmodeled furnaces as pushable, so one push failed | 14 | match | 2026-10-15 |
| EXP-051 | `catalog_blocks`: the game's ordinary blocks: conduction through wool, quartz, logs, double slabs and copper (not stained glass, leaves, sea lanterns, slabs, stairs), stair corners from neighbors, leaves' distance a tick after the log goes (an observer sees it), a carpet losing its support, podzol under snow, huge mushroom sides, glazed terracotta pushed but never pulled | 16 | match | 2026-10-15 |
| EXP-052 | `openables`: doors (oak, iron, spruce, birch, copper), trapdoors and fence gates opened and closed by signals at either door half, doors popping without support and when a piston pushes them, an observer watching a door, a lever and dust dropping when their trapdoor opens, a torch dropping from an opening fence gate, a gate between walls (`in_wall`) | 14 | match | 2026-10-15 |
| EXP-053 | `connections`: fences, bars, panes and walls connecting and disconnecting through shape updates (an observer sees a fence connect), nether brick vs oak fences and pumpkins not connecting, gates connecting across a fence only, panes joining walls and bars, wall posts and tall sides under a stone, a raised post under a redstone torch (`WALL_POST_OVERRIDE`), corners | 10 | match | 2026-10-15 |
| EXP-054 | `gravity_blocks`: sand, gravel, red sand, concrete powder, an anvil and the dragon egg fall as entities; every falling block's state, exact position and motion compared each tick (`data get entity`). Long and short falls, gravel pressing a wooden plate while passing (then breaking on it), powder on a slab and red sand on a carpet breaking, an anvil on a fence (from 0.5 above: a longer fall rolls the game's random damage, which chipped it in the first run), sand held by a torch, a falling stack, the dragon egg's 5-tick delay, sand on slime, an observer seeing sand leave | 45 | match | 2026-10-15 |
| EXP-055 | `gravity_pistons`: a piston head pushes falling sand sideways, a slime block on a sticky piston launches falling sand 10 blocks up (it falls back onto the slime), a piston lifts sand that falls back once the piston retracts; positions and motion compared each tick | 80 | match | 2026-10-15 |
| EXP-056 | `campfires`: a hay bale put under a campfire and taken away again (`signal_fire`, an observer and lamp fire both times), a piston facing a soul campfire does not extend (block entity), a torch below a campfire does not light a lamp next to it, food cooks while lit and leaves at its cooking time (8 and 12 ticks), progress cools by 2 per tick while unlit, falling sand breaks on a campfire; food slots and `CookingTimes` compared each tick (int arrays written as `[I; …]`) | 30 | match | 2026-10-15 |
| EXP-057 | `piston_zero_tick` (redstone research R-018): pistons make a 0-tick pulse. In four rows an observer (fired by its own `/setblock`) makes a sticky piston spit a redstone block into a cell, and a quasi-powered, never-updated piston beside the cell pushes it out in the same block-event phase. A repeater beside the cell gives a 2-tick pulse, a comparator nothing, a lamp flashes 4 ticks, a copper bulb toggles; sticky pistons updated before the remover (west, east, down, up, north, south) move their stone one cell at once, those updated after it never move | 14 | match | 2026-10-16 |
| EXP-058 | `instant_piston_wire` (redstone research R-023): chains of extended sticky pistons, each holding a redstone block against the next piston's back, collapse in one tick when the input goes (row A: 5 stages 3 blocks apart; row B: 3 stages joined by 14-wire lines, 38 blocks); row C: an input that pushes the first block away (rising edge) and a last stage that pulls a stone off a wire step (the output lights in the same tick); re-extending takes 3 ticks per stage | 64 | match | 2026-10-17 |
| EXP-059 | `piston_door_timing` (redstone research R-025): (a) a repeater into the upper of two stacked sticky pistons: the lower one is quasi-powered too but never moves (its push fails on the extended upper piston); (b) a sticky piston powered directly and through the block beside its head cell, both off in the tick its head lands: it retracts one tick later; (c) a sticky piston set down by another one next to an already powered block extends one tick after landing, and pulls the block two above it down when the power goes | 40 | match | 2026-10-18 |
| EXP-060 | `instant_edges` (redstone research: the `instant_edges` module, backlog Q17): two instant piston chains act on one output step; chain R removes a cut on the input's rising edge, chain F removes the source on its falling edge, and F's head is powered by the input or by NOT input 8 ticks late, so F re-arms by itself after R. Built by `/setblock` in the script's order (F arms after the input's first change); then the output follows the input one tick after every change (81, 111, 129 after the 18-tick minimum gap, 151) | 180 | match | 2026-10-18 |
| EXP-061 | `door_3x3` (redstone research: the `door_3x3` module, backlog Q18): the whole 3x3 flush piston door with its controller and lockout, built by `/setblock` in the script's order (a repeater fed by a redstone block stands in for the test lever; pistons A and B are placed at tick 6, after the observers' own `/setblock` pulse of R-018). Input off at 40: closed by 59; on at 100: all nine cells clear by 134 (the center goes down two cells through the gap a third piston makes); off at 170: closed by 189 | 210 | match | 2026-10-18 |
| EXP-062 | `cauldrons_furnaces` ([[mechanics/cauldron-and-furnace]]): comparators read an empty cauldron (0), water cauldrons of level 1–3, a lava cauldron (3), a powder snow cauldron of level 2, a furnace with one redstone dust (1), one with a wooden shovel in its fuel slot (5: it stacks to 1), a blast furnace with 64 cobblestone and 7 stone (6), a smoker with 8 ender pearls (3); a sticky piston moves a full water cauldron in front of a comparator and back (3, then 0), another moves a stone between a comparator and a furnace (5, then 0); a piston facing a furnace does not extend; a repeater into a cauldron does not light the lamp behind it. Furnace contents compared every tick | 40 | match | 2026-10-18 |
| EXP-063 | Whole doors with furnace and cauldron signals ([[mechanics/cauldron-and-furnace]]; recordings not committed: third-party designs in the owner's `data/` folder, scenarios built from the worlds' tick-0 states by `/setblock`, the lever replaced by a repeater fed by a redstone block). 4x4 Slisind slime door by Purplers (0-tick pistons; four furnaces with one redstone dust each, taken from the original save): input on at 5, the gap is full of slime and honey by 30, input off at 60, open again and in its start state by 130; the same door with empty furnaces never closes, in the game too (888 positions). 5x5 vault lamp door by Purplers (a water cauldron a piston moves, furnaces with a redstone dust and a wooden shovel): close at 5, open at 45, back in its start state (716 positions) | 130, 110 | match | 2026-10-18 |
| EXP-064 | `tripwires` ([[mechanics/tripwire-and-scaffolding]]): five lines of hooks and tripwire, lamps on the hooks' blocks. An armor stand in a wire (summoned at 2, killed at 9) powers both hooks in the next tick, off at the 10-tick recheck (13); removing a wire at 30 pulses the hooks until their recheck (40); a disarmed wire: stepping on it detaches the line until the hook's recheck, removing it gives no pulse; a piston popping a wire pulses them; hooks put by `/setblock` after the wire stay unattached until an armor stand presses the wire; when a hook breaks the other one detaches but the wires stay `attached`; sand falling through a wire presses it (falling block compared every tick) | 50 | match | 2026-10-18 |
| EXP-065 | `scaffolding` ([[mechanics/tripwire-and-scaffolding]]): a tower with a 6-long bridge and wire on top collapses when its base goes (distances count up between the pieces, then each breaks; the wire pops); a scaffolding put in the air falls to the floor, a second one onto another scaffolding (falling blocks compared every tick); a torch stands on top; a repeater into it does not light the lamp behind it; a piston pops it and the one above breaks | 40 | match | 2026-10-18 |
| EXP-066 | `lightning_rods` ([[mechanics/lightning-rod]]): lightning bolts summoned on five rods at 3 and on one again at 25: each rod is powered in the next tick for 8 ticks, the lamps beside the blocks they stand on light, wire beside a rod connects to it and carries 15; oxidized and exposed rods become `lightning_rod`, a waxed weathered one stays; a struck rod pushed by a piston (at 7) stays powered where it lands until 17, lighting the lamp beside it there | 40 | match | 2026-10-18 |
| EXP-067 | `crafters_jukeboxes` ([[mechanics/crafter-and-jukebox]], [[mechanics/rails]]): a redstone block next to a crafter makes it `triggered` and an observer watching it pulses (again when the power goes); a comparator reads a crafter with 2 items and 2 disabled slots (4); a powered crafter without a recipe crafts nothing; wire connects to jukeboxes; a disc put in by `/item replace` plays (wire 15, comparator 11) and stops when taken out; a jukebox saved 10 ticks before the end of its song stops then; wire connects to detector rails, a comparator reads 0, a powered one put by `/setblock` turns off at once | 40 | match | 2026-10-18 |
| EXP-068 | The three worlds marked "[broken sim]" (recordings not committed: third-party designs in the owner's `data/redstone_learning/piston_doors/`), run whole with `python -m tools.gameserver.run_world` (build by `/setblock … strict`, the wall lever replaced by a repeater fed by a redstone block, its recorded pulls replayed, every block compared). They used tripwire hooks, lightning rods, crafters, jukeboxes and detector rails, all foreign before. Nile's 5x5 vault door (78 ticks, 427 blocks): match. LegDen's 8x8 (94 ticks, 1963 blocks): a stone brick wall under a retracting sticky piston turned `low` in the simulator, `tall` in the game (the wall read the moving piston's context-free shape, empty; the game asks its block entity); fixed, then match. LegDen's 7x7 (131 ticks, 2369 blocks, the build settled 2 ticks first): match (once the harness wrote a falling block's `-0.0` motion as `0.0`, as the game's NBT does). The wall case alone: `walls_under_moving_blocks` (a retracting sticky piston above a wall; a stone pushed across another wall's top; observers watching both), match | 78, 94, 131, 24 | match | 2026-10-18 |
| EXP-069 | `enchanting_tables` ([[mechanics/crafter-and-jukebox]]): a repeater into an enchanting table does not light the lamp behind it; a piston facing one does not extend; sand falling onto one breaks (falling block compared every tick) | 30 | match | 2026-10-18 |

Hopper recordings also compare each hopper's `Items` and `TransferCooldown` (and the
barrels' `Items`, `watch_items`) every tick with `data get block`.

Evidence files: `experiments/results/<scenario>.json`.

### EXP-031: differential fuzzing, and what it found

`tools/gameserver/fuzz.py` builds a random circuit per seed; `python -m tools.gameserver.run
fuzz_1 fuzz_2 …` runs them (recordings are stored gzip-compressed as
`experiments/results/fuzz_<seed>.json.gz` and replayed by `tests/sim/test_game_verified.py`).

The first batch of 20 found two mismatches (seeds 3 and 15), both the same cause, and not a
simulator bug: a sticky piston pushing a slime or honey block drags the **ground** under it
(sticky blocks stick to it). In the game the ground row continues past the prepared test
area into the superflat world's grass, so the push exceeds 12 blocks and fails; the
simulator's terrain ended 2 blocks past the area, so the push succeeded. The harness now
mirrors the superflat terrain (bedrock, dirt, dirt, grass) 16 blocks around each area
(`compare.build_terrain`); both seeds match, and every earlier recording still replays.

Adding hoppers to the palette found a second harness issue: in the game, components that
pop (dust losing its support, for example) drop **item entities**, and a hopper nearby
collected one (`fuzz_1`: a redstone item appeared in a hopper at tick 7). The simulator has
no item entities by design, so the harness now sets `gamerule block_drops false`
(`Block.popResource` checks it; container contents only spill when a container is removed
with side effects, which `/setblock` skips) and kills stray items before each scenario.
Both seeds then matched. Neither change affects redstone behavior.

Gravity blocks (EXP-054, 055) added `gamerule entity_drops false`: a falling block that
cannot land drops itself as an item with that rule on (an item on a wooden plate would
keep it pressed), and the simulator has no items. Scenarios with `watch_entities` also
compare every falling block (`execute as @e[type=falling_block] run data get entity
@s`: block state, `Pos`, `Motion`, exact doubles). In 26.3 the entity's `BlockState` is
saved as a bare id for a default state and as `{id, properties}` otherwise.

### EXP-023 sensitivity

With `LevelTicks.copy_area` disabled in the simulator, ticks 8–16 no longer match the game
recording: the moved repeater would never turn on. So the scenario checks that `/clone`
copies scheduled ticks (`LevelTicks.copyAreaFrom`), which the editor's selection drag
relies on ([[decisions]] ADR-019).

### EXP-004 timeline (game)

Input A at tick 4, B at 10, A off at 17, B off at 23. Observed: torch A off at 6; torch B
off at 12; joining wire 0 at 12; output torch on at 14 (2 + 2 ticks); output off at 21;
lamp off at 25 (4-tick lamp delay).

### EXP-005 finding: a burnt-out torch can stay out forever

`RedstoneTorchBlock.tick` requests a 160-tick restart tick on the 8th turn-off within 60
ticks. In this loop the torch's own turn-off cascade reaches it again first, and its
`neighborChanged` schedules a 2-tick check. The restart request is then dropped by
`LevelChunkTicks.schedule`'s per-(pos, block) dedup. The 2-tick check still sees 8 recent
toggles, so the torch stays off, and nothing schedules another tick. The simulator predicted
this before the game confirmed it. EXP-006 shows that any later neighbor update (once the
toggle list has aged out) relights the torch. See [[quirks]] Q-TORCH-BURNOUT-STUCK.

### EXP-007 finding: glass is a one-way staircase

A lower wire only looks *below* a non-conductive neighbor for wire, and never on top of it,
so power climbs onto glass but cannot come down (`RedstoneWireEvaluator.getIncomingWireSignal`).
Both sides were tested by moving the source from east to west. See [[quirks]]
Q-WIRE-GLASS-UP.

### EXP-010 finding: priorities decide same-tick races

Both repeaters get their input in the same between-tick gap: M (main, delay 1) first, then
L (locks M from the side, delay 1). Both ticks are due in the same game tick. L outputs
into a diode's side, so `DiodeBlock.shouldPrioritize` gives it `EXTREMELY_HIGH` (−3); M
turning on gets `HIGH` (−1). L therefore runs first despite the later sub-tick order, and M
finds itself locked and never turns on (`LOCKED=true`, lamp off) until L turns off at tick 8.
M then turns on at tick 10. The game shows exactly this.

### EXP-012/013 notes

- A comparator mode set by `/setblock` (EXP-012, tick 8) changes nothing by itself. No
  neighbor update reaches the comparator, so it re-evaluates only when an input changes
  (tick 10).
- The comparator's stored output (block-entity data) is compared via
  `data get block … OutputSignal`.

### EXP-015…020 notes: pistons

- Moving blocks (`moving_piston`) are compared with their block-entity `progress` tag,
  which stores `progressO` (`PistonMovingBlockEntity.saveAdditional`).
- Timing confirmed: an input applied between ticks extends the piston in the next tick's
  block-event phase. The pushed block and head become real two ticks later, in the
  block-entity phase (progress 0 → 0.5 → 1, then finalize).

### EXP-016 finding: a 2-tick pulse also spits the block

The wiki says sticky pistons drop their block for pulses "shorter than 1.5 ticks". For an
input removed between ticks, the source gives a wider window. `checkIfExtend` chooses
event 2 (drop) if the moving block's `progressO < 0.5` **or** `gameTime == lastTicked` **or**
`isHandlingTick`. After a 2-tick pulse, progressO is already 0.5, but the block entity was
ticked in the same game tick (`lastTicked == gameTime`), so the block is dropped anyway. The
simulator predicted this before the game run confirmed it. A 3-tick pulse arrives after the
move finished and pulls the block back. Open question OQ-3 is resolved for
between-tick inputs; scheduled-tick inputs (`isHandlingTick`) remain to be tested.

## Template for manual experiments

```markdown
## EXP-NNN: <short title>
- Date / game version: 26.3, clean superflat world
- Setup, procedure, in-game observation, simulator result, verdict, evidence
```
