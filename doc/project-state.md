# Project state

The authoritative "where are we" page. Update it at the end of every work slice. For design
rationale see [[architecture]] and [[decisions]]; for the plan see [[roadmap]].

*Last updated: 2026-10-11, branch `feat/sim-core`.*

## Summary

- **Research (M0, M1):** complete for the initial scope. Every in-scope mechanic has a
  source-backed page under [[mechanics/index]].
- **Simulation core (M3):** done. It ports the server's setBlock pipeline, the collecting
  neighbor updater, scheduled ticks, block events and block-entity tickers, behind a
  steppable engine with snapshots.
- **Components (M4):** done for the initial scope: lever, stone/oak buttons, redstone
  lamp, redstone torch and wall torch (including deterministic burnout), redstone wire,
  repeater, comparator (block entity, compare/subtract, side inputs, analog input), cake
  (analog source), the redstone block, and simple and non-conducting blocks. Open: a
  container analog source (barrel with inventory).
- **In-game verification:** a sandboxed 26.3 dedicated server compares the simulator tick by
  tick. All 20 recorded scenarios match ([[experiments/index]]).
- **Editor (M2):** done for the minimal scope. PySide6 window with a 3D viewport, fly camera,
  cursor picking, place/break/use with player-like orientation, block palette and hotbar,
  inspector (`/setblock` edits), sections (color annotations), simulation controls (run,
  step tick, step event, speed), diagnostics (scheduled ticks, block events, last-step
  trace), undo/redo for edits, and JSON save/open of the complete engine state. Launch with
  `python -m redsim`.
- **Pistons (M5):** done for the core scope. Normal and sticky pistons, heads, moving blocks
  with their block entity, structure resolution (12-block limit, slime/honey branching),
  quasi-connectivity, BUD behavior and short-pulse block dropping, all confirmed in game.
  Open: retraction triggered from scheduled ticks (repeater-driven 0-tick setups), observers.
- **History/playback UI (M6), contraptions (M7):** not started. The engine already supports
  snapshot/restore, which M6 will build on.

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
| `redsim.io.save` | Save/load of the complete engine state | done (mid-tick safe) | `tests/io/test_save.py` |
| `redsim.editor` | Document, placement orientation, sections, undo | done | `tests/editor/test_editor.py` |
| `redsim.ui` | PySide6 editor (viewport, panels, main window) | done (minimal scope) | `tests/ui/test_geometry.py`, `tests/ui/test_ui_smoke.py` (offscreen) |
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

## Verification status

- `python -m pytest`: **110 tests pass** (2026-10-11), including the JDK oracle, the 20
  game-recording replays, save round trips and an offscreen UI smoke test. `ruff check`, `ruff format --check` and `mypy src tools` are clean.
- Real-game comparisons (`python -m tools.gameserver.run`): 20 of 20 scenarios match.
  Sensitivity was confirmed by deliberately breaking the lamp delay ([[experiments/index]]).

## Known limitations (current)

- Only tick-boundary states are compared in game; sub-tick order is verified against the
  source and unit tests only.
- Levers and buttons cannot be operated on the dedicated server (no player), so player
  interaction paths (`BlockItem.place`, `useWithoutItem`) are verified by source reading and
  unit tests, not in game.
- Rails, trapdoors and hoppers are referenced by ported code paths (wire support, rail
  removal rule) but are not blocks yet.
- Overdue scheduled ticks (more than 65 536 due in one tick) are reported but not merged
  per chunk (cannot occur in scope).
- Experimental redstone (`redstone_experiments`) is out of scope (ADR-006).
- The trace grows without a cap; the UI shows only the last step's records.
- The editor has no rewind yet (M6); undo covers edits only.
- The GUI was verified offscreen (smoke test and screenshots), not on the owner's desktop.

## Next steps (in order)

1. Playback and history (M6) on top of `Engine.snapshot()`: rewind ticks and steps, event
   scrubbing with a causal trace view, warp, saving at intermediate points from the UI.
2. Piston follow-ups: game scenarios with scheduled-tick-driven retraction (repeater 0-tick
   pulses); then observers (later scope).
3. Small M4 follow-up: barrel/container analog source (inventory fill formula in 32-bit
   float), with `/item replace`-driven game scenarios.

## How to resume

```sh
git switch feat/sim-core
python -m redsim                       # start the editor
python -m pytest                       # all tests, ~2 s, no server needed
python -m tools.gameserver.run         # re-run game comparisons (~1-2 min, sandboxed server)
```

Read [[implementation-notes]] for conventions, the "adding a block" checklist and harness
details.
