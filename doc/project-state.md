# Project state

The authoritative "where are we" page. Update it at the end of every work slice. For design
rationale see [[architecture]] and [[decisions]]; for the plan see [[roadmap]].

*Last updated: 2026-10-11, after the fourth feedback round (all merged into `main`).*

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
  rails (plain, powered, activator), target blocks and hoppers.
- **In-game verification:** a sandboxed 26.3 dedicated server compares the simulator tick by
  tick, including block-entity data (comparator outputs, hopper contents and cooldowns).
  All 40 named scenarios and 40 random circuits (every supported block, 0-tick inputs,
  live edits) match ([[experiments/index]]).
- **Editor (M2):** done. PySide6 window with a 3D viewport, orbit camera, vim-like modes
  and a rebindable keymap ([[controls]]); BUILD mode places with left click (drag: a
  straight line), turns with right click, removes with Del, with a translucent preview;
  a Trackmania-style inventory with block previews, recent blocks and quick search; an
  immediate-apply inspector (`/setblock` edits, container contents, target hits),
  sections, groups and prefabs; a Blender-like timeline with keyframe rows and monitor
  tracks; a hint bar, F3 debug screen, X-ray and info overlay; JSON save/open of the
  complete engine state. Launch with `redsim` or `python -m redsim`.
- **Pistons (M5):** done for the core scope. Normal and sticky pistons, heads, moving blocks
  with their block entity, structure resolution (12-block limit, slime/honey branching),
  quasi-connectivity, BUD behavior and short-pulse block dropping, all confirmed in game.
  Open: retraction triggered from scheduled ticks (repeater-driven 0-tick setups), observers.
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

## Verification status

- `python -m pytest`: **404 tests pass** (2026-10-12), including the JDK oracle, the 80
  game-recording replays (40 named, 40 random), save round trips, history rewriting,
  chunked-mesh consistency, run pacing and offscreen UI tests. `ruff check`,
  `ruff format --check` and `mypy src tools` are clean. Tests use a private config
  directory (`tests/conftest.py`).
- Real-game comparisons (`python -m tools.gameserver.run`): 46 of 46 named scenarios match
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
- Containers are barrels and hoppers only (no chests, droppers, composters).
- Overdue scheduled ticks (more than 65 536 due in one tick) are reported but not merged
  per chunk (cannot occur in scope).
- Experimental redstone (`redstone_experiments`) is out of scope (ADR-006).
- The trace keeps the last 200 000 records; the UI shows the last step's records as an
  indented causal list (no interactive tree yet).
- Saves contain the current state only, not the timeline history.
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

All seven owner feedback rounds ([[ui-direction]]) are done. Round 7 (2026-10-12): the
wheel moves the camera up and down, uniform inventory rows, the game's block names, 1-pixel
dust and rails, 30 %/50 % X-ray defaults, a fading layer grid. Then an overnight UI polish
pass ([[ui-direction]], ADR-025): pixel-art icons everywhere, the game's hotbar sprites,
a grass superflat horizon with the game's clouds (View → Scenery), a restyled timeline,
container slot grids, Minecraft-style tooltips, remembered window layout, and fixes found
on the way (guide-line blending, unpainted tab gaps, an unbounded text cache, late GL
texture destruction). Round 6: "Set tick 0 here" restarts the clock, the game's models
and textures (ADR-023), the dark Minecraft-meets-Blender theme (ADR-024).

Suggested next steps:

1. **Owner review** of round 7 and the polish pass on the desktop
   (`redsim examples/showcase.redsim.json`); open questions are listed in the round-7
   summary (grass vs. stone ground, name fade, Lock/region button dimming).
2. **Mechanics:** done 2026-10-12: note blocks, copper bulbs, droppers/dispensers,
   chests, pressure plates (entities as editor visitors), scheduled-tick piston pulses
   (EXP-047). Left: dispense effects (entities, fluids), detector rails, daylight sensors.
3. **World loading:** done 2026-10-12: opened Minecraft worlds stream in around the
   camera ([[world-import]], phase 3). Left: the "go to the builds" index, the on-disk
   cache, write-back (phase 4).
4. **Diagnostics:** an interactive causal trace ("why did this block change?"), a
   signal-strength heat view in the viewport.
5. **Editing comfort:** named bookmarks on the timeline, a
   "compare two ticks" view (blocks that differ highlighted).
6. **Scale:** profile larger builds (the engine is pure Python); history rewrites re-run
   from tick 0, which is fine for hundreds of ticks but should keep keyframes for long
   histories.

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
