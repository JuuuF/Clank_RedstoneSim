# Project state

The authoritative "where are we" page. Update it at the end of every work slice. For design
rationale see [[architecture]] and [[decisions]]; for the plan see [[roadmap]].

*Last updated: 2026-10-14, after working through the open list ([[todo-pass]]: Select
World look, timeline groups for every category, several selections acting together,
"why did this change?" and a heat view, real signs with text, world builds index and
reconnecting, schematics, composters and more signal sources). Before that: the
overnight refactor, stability and speed pass ([[refactor-plan]]). Before that: 2026-10-12, after the missing blocks, world streaming and the E block popup
(all merged into `main` and pushed). The session log of the work is in git history; this
page is the summary to start from.*

## Summary

- **Research (M0, M1):** complete for the initial scope. Every in-scope mechanic has a
  source-backed page under [[mechanics/index]].
- **Simulation core (M3):** done. It ports the server's setBlock pipeline, the collecting
  neighbor updater, scheduled ticks, block events and block-entity tickers, behind a
  steppable engine with snapshots.
- **Components (M4):** done for the initial scope: lever, stone/oak buttons, redstone
  lamp, redstone torch and wall torch (including deterministic burnout), redstone wire,
  repeater, comparator (block entity, compare/subtract, side inputs, analog input), analog
  sources (barrel, lectern, cake; [[analog-sources]]), the redstone block, and simple and
  non-conducting blocks. Added after the third round, in the owner's order: observers,
  rails (plain, powered, activator), target blocks and hoppers; on 2026-10-12: note
  blocks, copper bulbs (all 8), dispensers, droppers, chests (double, trapped) and
  pressure plates (stone, 12 woods, weighted).
- **In-game verification:** a sandboxed 26.3 dedicated server compares the simulator tick by
  tick, including block-entity data (comparator outputs, hopper contents and cooldowns).
  All 48 named scenarios and 60 random circuits (every supported block, 0-tick inputs,
  live edits) match ([[experiments/index]]).
- **Editor (M2):** done. PySide6 window with a 3D viewport, orbit camera, vim-like modes
  and a rebindable keymap ([[controls]], with a keymap editor and Mac defaults); BUILD
  mode places with left click (drag: a straight line), removes with right click, turns
  with Q, with a translucent preview; E opens any block's inspector as a popup;
  a Trackmania-style inventory with block previews, recent blocks and quick search; an
  immediate-apply inspector (`/setblock` edits, container contents, target hits),
  sections, groups and prefabs; a Blender-like timeline with keyframe rows and monitor
  tracks; a hint bar, F3 debug screen, X-ray and info overlay; JSON save/open of the
  complete engine state. Launch with `redsim` or `python -m redsim`.
- **Pistons (M5):** done for the core scope. Normal and sticky pistons, heads, moving blocks
  with their block entity, structure resolution (12-block limit, slime/honey branching),
  quasi-connectivity, BUD behavior and short-pulse block dropping, all confirmed in game.
  Pulses that start and end in scheduled ticks are confirmed too (EXP-047).
- **Playback and history (M6):** done. An event-sourced timeline (keyframes + action log +
  deterministic replay) supports step back, tick back, scrubbing, forward and backward
  playback and warp. Tick 0 is the build state (not replayed); edits at later ticks form
  per-tick batches shown as color-coded keyframes that can be moved, merged, deleted or
  moved into the build; undo/redo restore whole history states (ADR-022). Exact replay is
  tested.
- **Real-time rendering:** done. Meshes are built per 8³ chunk and only where blocks
  changed; the run loop is paced by the wall clock and decoupled from drawing; the viewport
  shows the achieved ticks/s. Measured 19.9 ticks/s at target 20 on the owner's desktop
  (ADR-017).
- **Contraptions (M7):** done for the core scope. Axiom-style box selection with resize
  handles, drag-to-move and drag-to-copy (full `/clone … move|force`, scheduled ticks
  included, game-verified EXP-023), copy/paste with a preview and `/clone` semantics
  (game-verified), clipboard rotation, delete with `/fill` semantics (game-verified),
  a prefab library (save, import/export JSON), and groups with exposed input/output ports and
  live readings. Abstract (black-box) group models are deferred (ADR-016).
- **Minecraft worlds:** File → Open Minecraft world… opens a Java 26.x save around the
  player and streams further chunks in around the camera up to a view distance; blocks the
  simulator does not model come in as inert "foreign" blocks drawn with their real model
  ([[world-import]]). Not yet: the "go to builds" index, an on-disk cache, writing back.

## What exists, module by module

| Module | Purpose | Status | Tests |
|---|---|---|---|
| `redsim.core.direction` | Directions in Java ordinal order; update-order constants | done | `tests/core/test_direction.py` |
| `redsim.core.pos` | Positions as tuples; `BlockPos.hashCode` | done | `tests/core/test_javahash.py` |
| `redsim.core.javahash` | `java.util.HashMap`/`HashSet` iteration order | done, **checked against a real JDK 25** (400 random cases) | `tests/core/test_javahash.py` |
| `redsim.world.properties` | Block-state properties with the game's value order | done | indirectly |
| `redsim.world.shape` | 16³ voxel shapes; FULL/CENTER/RIGID support checks | done | indirectly (support rules in component tests) |
| `redsim.world.block` | `Block` (BlockBehaviour hooks), interned `BlockState`, update flags | done | all sim tests |
| `redsim.world.block_entity` | Block-entity base | done (comparator entity uses it) | `tests/sim/test_diodes.py` |
| `redsim.world.tick_priority` | `TickPriority` | done | scheduling tests |
| `redsim.world.blocks.*` | Block registry and behaviors | initial scope done (see block table) | `tests/sim/test_components.py`, game recordings |
| `redsim.sim.level` | `Level`: setBlock pipeline, signal queries, ticks, events, block entities, clone | done | `tests/sim/test_set_block.py` and others |
| `redsim.sim.neighbor_updater` | `CollectingNeighborUpdater` port | done | `tests/sim/test_neighbor_updater.py` |
| `redsim.sim.ticks` | `LevelTicks` port (collect-then-run, dedup, priorities) | done | `tests/sim/test_scheduling.py` |
| `redsim.sim.trace` | Causal trace records | done (basic) | used in component tests |
| `redsim.sim.engine` | Tick phases as steps; player and command actions; snapshots | done | `tests/sim/test_scheduling.py` |
| `redsim.sim.timeline` | History: keyframes, action log, seek/rewind/replay | done | `tests/sim/test_timeline.py` |
| `redsim.io.save` | Save/load of the complete engine state | done (mid-tick safe) | `tests/io/test_save.py` |
| `redsim.mcworld` | Minecraft saves: NBT, region files, sections, streaming, opening as a document | phases 1–3 of [[world-import]] (no cache, no write-back) | `tests/mcworld/*` (the example-save test skips without `data/`) |
| `redsim.editor` | Document, placement orientation, sections, undo, clipboard/prefabs, groups | done | `tests/editor/test_editor.py`, `tests/editor/test_contraptions.py` |
| `redsim.world.rotation` | State/offset rotation (`Rotation.CLOCKWISE_90`) | done | `tests/editor/test_contraptions.py` |
| `redsim.ui` | PySide6 editor (viewport, panels, main window), chunked meshes with the game's textured models (`assets`, `atlas`), run pacing, smooth orbit camera, keymap and modes, theme and pixel font, hotbar inventory, block search, timeline with keyframe rows, F3 screen, gizmos | done | `tests/ui/*` (offscreen; asset tests skip without the jar) |
| `tools/java_oracle` | JVM oracle for hash order | done | `tests/core/test_javahash.py` |
| `tools/gameserver` | Sandboxed server harness, scenarios, comparison runner | done | `tests/sim/test_game_verified.py` replays its recordings |

## Blocks

| Block(s) | Implementation | Unit tests | In-game verified |
|---|---|---|---|
| air, stone, smooth stone, cobblestone, oak planks, white wool, white concrete | `simple.py` | yes (as floor/conductors) | yes (stone) |
| glass, glowstone (non-conductors) | `simple.py` | glass: wire climbing | glass: EXP-007 |
| obsidian (immovable), bedrock (unbreakable) | `simple.py` | — | — (relevant once pistons exist) |
| slime block, honey block, smooth stone slab | `simple.py` | — | — |
| redstone block | `simple.py` | yes | yes (inputs of every scenario) |
| lever | `attached.py` | strong/weak power, double update, popping | no (needs a player) |
| stone button (20), oak button (30) | `attached.py` | timings, re-press | no (needs a player) |
| redstone lamp | `lamp.py` | timing | EXP-001, EXP-003, EXP-004 |
| redstone torch, wall torch | `torch.py` | inversion, strong power, burnout counter | EXP-002, EXP-004, EXP-005, EXP-006 |
| redstone wire | `redstone_wire.py` | decay, step up/down, glass, dot, weak power, hash order | EXP-002…EXP-004, EXP-007 |
| repeater | `diode.py` | placement delay 1, priorities, no lock from wire/torch, axis connection | EXP-008…EXP-011 |
| comparator (+ block entity) | `comparator.py` | mode click refresh, double front update | EXP-012…EXP-014 |
| piston, sticky piston, head, moving piston (+ block entity) | `piston.py` | push limit, immovables, popping, slime/honey, pull, head removal | EXP-015…EXP-020 |
| cake (analog source) | `cake.py` | via comparator tests | EXP-012, EXP-013 |
| rail, powered rail, activator rail | `rail.py` | shapes, T junction, slope, 8-rail propagation | EXP-031, 035, 036 |
| observer | `observer.py` | pulse timing, clock, non-conductor | EXP-031..034 |
| hopper (+ block entity, 5 slots) | `hopper.py` | cooldown 8/7, locking, pull/push order, `/item replace` quirk, save | EXP-031, 038..041 (contents and cooldowns compared) |
| target block | `target.py` | hit duration, entity-phase timing, dust connection | EXP-031, 037 |
| barrel (+ block entity, 27 slots) | `container.py` | thresholds, `/item replace` updates, immovable, save | EXP-024 |
| lectern (+ block entity) | `lectern.py` | page formula, page-turn pulse, save | EXP-025 (signals; pulse: source only) |
| note block | `note_block.py` | instrument from the block below/above, rising edge, block event | EXP-042 |
| copper bulb (all 8 oxidation/wax ids) | `copper_bulb.py` | T flip-flop, light, comparator output | EXP-043 |
| dispenser, dropper (+ block entity, 9 slots) | `dispenser.py` | QC trigger, 4-tick delay, random slot, dropper into containers | EXP-044 (dispense effects not simulated) |
| chest, trapped chest (+ block entity, single/double) | `chest.py` | double-chest slots, blocked chest reads 0, hoppers ignore blocking | EXP-045 |
| pressure plates (stone, polished blackstone, 12 woods, light/heavy weighted) | `pressure_plate.py` | press/release timing, weights, "visitors" instead of entities | EXP-046 |
| composter (levels 0–8, a signal source kind) | `composter.py` | level timing, comparator, player/hopper emptying, pistons | EXP-049 |
| standing and wall signs (12 woods, + block entity with front/back text) | `sign.py` | placement, popping, blocking pistons, text edits, saving, rotation | EXP-048 |
| the game's ordinary blocks (~580: full cubes, pillars, facing blocks, slabs, stairs, leaves, carpets, all wood/stone buttons, poplar plates and signs) | `catalog.py` + generated `catalog_data.py` | settings from `Blocks.java` (conductor rule, push reaction, destroy time, see-through); stair corners and mirroring, leaves distance (ticked), carpets breaking | `tests/world/test_catalog.py` (not yet checked in the game) |
| doors (22), trapdoors (22), fence gates (13) | `openable.py` | signals at either door half, hand use (not iron), hinge and click-height placement, creative breaking of door pairs, shapes (support, no conduction), `in_wall` | EXP-052; `tests/world/test_openable_connecting.py` |
| fences (14), bars and panes (26), walls (32) | `connecting.py` | connections through shape updates (exceptions, fence kinds, gates), wall posts and low/tall sides from the block above, turning and mirroring | EXP-053 |
| foreign blocks (anything else from an opened save) | `foreign.py` | kept as state text, inert, saved | — |

## Verification status

- `python -m pytest`: **522 tests pass** (2026-10-14, after the open-list pass; also on the
  compiled build), including
  the JDK oracle, the 107 game-recording replays (47 named recordings, 60 random),
  randomized history checks (replay, save/open, undo/redo), every window action in every
  mode, save round trips, history rewriting,
  chunked-mesh consistency, run pacing and offscreen UI tests. `ruff check`,
  `ruff format --check` and `mypy src tools` are clean. Tests use a private config
  directory (`tests/conftest.py`).
- Real-game comparisons (`python -m tools.gameserver.run`): 48 of 48 named scenarios match (signs and
  composters added 2026-10-14); 46 of them
  in one fresh full run (2026-10-11); the 40 random circuits were re-recorded after hoppers
  joined the palette and all match. The harness fails loudly on rejected commands.
  Sensitivity was confirmed by deliberately breaking the lamp delay, the hopper 7-tick
  rule and the hopper `setItem` quirk ([[experiments/index]], [[mechanics/hopper]]).

## Known limitations (current)

- Only tick-boundary states are compared in game; sub-tick order is verified against the
  source and unit tests only.
- Levers and buttons cannot be operated on the dedicated server (no player), so player
  interaction paths (`BlockItem.place`, `useWithoutItem`) are verified by source reading and
  unit tests, not in game.
- No entities: no minecarts (so no detector rails), no item entities (the test server runs
  with `block_drops false`), no projectiles except the target-block hit action.
- Containers: barrels, hoppers, chests, dispensers and droppers (no composters, furnaces,
  shulker boxes). What a dispenser shoots or places, and items a dropper drops, are not
  simulated (the item just leaves the container).
- Overdue scheduled ticks (more than 65 536 due in one tick) are reported but not merged
  per chunk (cannot occur in scope).
- Experimental redstone (`redstone_experiments`) is out of scope (ADR-006).
- The trace keeps the last 200 000 records; the UI shows the last step's records as an
  indented causal list (no interactive tree yet).
- Saves keep the timeline's recorded edits (sequences too) with the build they start
  from, and opening re-runs them; undo history and samples are not saved.
- Chunks of an opened Minecraft world that stream in later join every stored level as if
  they had always been loaded; their pending scheduled ticks are not imported (only those
  of the first area are). A `.redsim.json` saved from an opened world keeps the blocks
  loaded so far but no longer streams.
- Section edits are not part of undo/rewind.
- The GUI is verified offscreen (smoke tests) and on the owner's desktop (XWayland,
  OpenGL 3.3) with scripted input: orbit, pan, Ctrl+wheel, zoom, mode keys, BUILD place and
  SELECT drag behave as specified. The owner has used the earlier fly-camera version; the
  new controls await their hands-on review.

## Next steps (in order)

Everything the owner has asked for, done and open, is listed in [[feedback-status]].

**The ninth feedback round** (2026-10-13) is done: 15 items with what changed and where
in [[ui-direction]] ("Ninth round of feedback"). Open from it: copying several selections
at once, sign text for signs placed in the editor, and game-speed limits of very heavy
contraptions (pure Python engine).

Eight owner feedback rounds are done ([[ui-direction]]). The owner's latest priority order
(2026-10-12) was: missing blocks → improve world (game) loading → diagnostics; the owner
tests the Mac support themselves. Status and what is left:

1. **Missing blocks: done** (note blocks, copper bulbs, dispensers/droppers, chests,
   pressure plates, scheduled-tick piston pulses, all game-verified). Left, lower priority:
   dispense effects (entities, fluids, placing), detector rails (need minecarts), daylight
   sensors (need time of day and sky light), composters and furnaces.
2. **World loading: mostly done.** Streaming around the camera works (phase 3 of
   [[world-import]]). Left: an index of the save's builds with "go to the builds" (the
   palette scan already exists in `mcworld/chunk.py`), an on-disk cache keyed by chunk
   timestamps, dropping far chunks again, re-attaching the stream when a `.redsim.json`
   saved from a world is reopened, then write-back to a copy (phase 4).
3. **Diagnostics: next.** An interactive causal trace ("why did this block change?": click
   a block, see the chain of updates and ticks that changed it, from `sim/trace.py`
   records, which already carry causes), and a signal-strength heat view in the viewport.
4. **Owner review** of rounds 7–8, the polish pass, the popup and Mac support on real
   hardware.
5. **Editing comfort:** a "compare two ticks" view (blocks that differ highlighted).
6. **Scale:** with the compiled build the engine is about 2× faster; keyframes are full
   level copies (a streamed world at view distance 12: ~12 MB each, at most 34 kept,
   about 500 MB in all). Delta keyframes against the base would make them cheap; they
   must keep `Level.blocks` a real dict (compiled code) and receive streamed chunks.

## How to resume

```sh
conda activate redsim                  # environment.yml; see implementation-notes
redsim examples/showcase.redsim.json   # example world, see [[tour]]
git switch main
python -m pytest                       # all tests, ~15 s, no server needed
python -m tools.gameserver.run         # re-run named game comparisons (~5 min, sandboxed server)
```

Read [[implementation-notes]] for conventions, the "adding a block" checklist and harness
details.

## Handing over (for the next developer)

- **Branches:** `main` is always the latest verified state and is pushed to
  `origin` (github.com:JuuuF/RedstoneSim). Work on a feature branch, run the checks, then
  fast-forward `main` and push both. Nothing is left uncommitted or half-merged.
- **Checks before every commit:** `ruff format src tests tools`, `ruff check src tests
  tools`, `mypy src tools`, `python -m pytest` (all must pass; the UI tests run offscreen).
  Behavior changes to blocks also need a game scenario ([[implementation-notes]],
  "Checklist: adding a game scenario"); run `python -m tools.gameserver.run <name>` and
  commit its recording under `experiments/results/`.
- **Supplied, not committed (`data/`, git-ignored):** the decompiled 26.3 source
  (`data/minecraft_src/client-src/`, cited with line numbers throughout the docs), the
  client and server jars (`data/minecraft_jars/`; textures, models and the font are read
  from the client jar at runtime, the server jar runs the game comparisons) and the
  example save (`data/minecraft_saves/Redstone/`). Tests that need them skip without them.
- **Where things are explained:** mechanics with source references in [[mechanics/index]],
  every experiment in [[experiments/index]], design decisions as ADRs in [[decisions]],
  owner requests and how each was answered in [[ui-direction]], controls in [[controls]],
  conventions and gotchas in [[implementation-notes]], structure in [[architecture]].
- **Owner preferences that shape the work:** game sprites over pixel art over anything
  else (never emoji); Minecraft vibe with a Blender-like UI; wiki pages are hints, the
  source and the game are proof (ADR-011); docs are the project's memory (ADR-012), so
  update this page at the end of every slice.

