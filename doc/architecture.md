# Architecture

## Goal of the design

Reproduce Java Edition 26.3 redstone state and timing by **porting the relevant server-side
algorithms one-to-one into Python**, not by designing an independent redstone model. Every
simulation module mirrors a specific Java class or method and cites it. Anything without
redstone relevance (lighting, sounds, particles, entities, game events, client sync) is left
out and documented as out of scope ([[decisions]] ADR-001).

## Repository layout

```text
src/redsim/
├── core/                  no game logic
│   ├── direction.py       Direction (Java ordinals), Axis, HORIZONTAL/VERTICAL, update orders
│   ├── pos.py             Pos = (x, y, z) tuples, offset helpers, java_hash (Vec3i.hashCode)
│   └── javahash.py        JavaHashMap / JavaHashSet iteration-order emulation
├── world/                 the "what": blocks and states (no engine loop)
│   ├── properties.py      Property definitions with the game's value order
│   ├── shape.py           16³ voxel shapes, SupportType checks (FULL/CENTER/RIGID)
│   ├── block.py           Block (BlockBehaviour hooks), interned BlockState, UpdateFlags,
│   │                      PushReaction, Conductor, PlacementContext
│   ├── block_entity.py    BlockEntity base (valid_blocks, tick, clone, pre-removal hook)
│   ├── ids.py             block ids used for Java's state.is(Blocks.X) checks
│   └── blocks/            registry (__init__.py) and behaviors:
│       ├── simple.py      air, full cubes, non-conductors, immovable, slabs, honey, redstone block
│       ├── attached.py    face-attached sources: lever, buttons
│       ├── lamp.py        redstone lamp
│       ├── torch.py       redstone torch + wall torch (incl. burnout)
│       └── redstone_wire.py
├── sim/                   the "when/how": server-side update machinery
│   ├── level.py           Level: setBlock pipeline, signals, scheduling, events, block entities
│   ├── neighbor_updater.py CollectingNeighborUpdater port
│   ├── ticks.py           LevelTicks port (ScheduledTick, TickPriority)
│   ├── trace.py           causal trace records (capped, stable ids)
│   ├── engine.py          tick phases as steps, actions, snapshots
│   └── timeline.py        history: keyframes + action log, rewind/replay
├── io/save.py             JSON save/load of the complete engine state (mid-tick safe)
├── editor/                editing without Qt: Document (engine + timeline + annotations +
│                          files), player-like placement, sections, clipboard/prefabs (regions,
│                          rotation), groups with exposed ports
└── ui/                    PySide6 application: viewport (camera, picking, renderer), panels,
                           main window, app entry point (`python -m redsim`)
tests/                     pytest suites (core, world, sim); tests/sim/probe.py = test-only blocks
tools/
├── java_oracle/           HashOrderOracle.java (real-JVM check for javahash)
└── gameserver/            sandboxed 26.3 server harness, scenarios, comparison runner
experiments/results/       JSON recordings from the real game (evidence, replayed by tests)
doc/                       this documentation (Obsidian vault)
```

Dependency direction is strictly downward: `ui → editor → io → sim → world → core`. `tools` and
`tests` may import anything. The simulation never imports Qt and never reads rendering
state. Section colors and labels will be stored as annotations next to the world, never
inside block states.

## World model

- **Positions** are `(x, y, z)` tuples, hashable and immutable. `java_hash(pos)`
  reproduces `BlockPos.hashCode()` for hash-order emulation.
- **Directions** follow Java's ordinal order `DOWN, UP, NORTH, SOUTH, WEST, EAST`, because
  many loops iterate `Direction.values()`. Named orders: `NEIGHBOR_UPDATE_ORDER` (W, E, D, U,
  N, S), `SHAPE_UPDATE_ORDER` (W, E, N, S, D, U), `HORIZONTAL` (N, E, S, W), `VERTICAL` (U, D).
- **Block states** are interned. `StateDefinition` creates every property combination once,
  so `a is b` is Java's `==` on states. `with_(prop, value)` (Java `setValue`) is a cached
  table lookup, and `cycle` follows the property's declared value order.
- **Blocks** are singletons in `redsim.world.blocks.REGISTRY`. Mechanically relevant
  attributes are separate: `has_collision`, `push_reaction`, `destroy_speed`, `conductor`
  (default/never/always), `is_air`, `has_block_entity`, `has_ticker`, `is_diode`, `is_rail`.
  Shapes (`get_shape`, `get_collision_shape`, `get_block_support_shape`) feed the
  conductor default and `is_face_sturdy(direction, SupportType)`.
- **Hooks** mirror `BlockBehaviour` with snake_case names and the same parameters (minus
  `orientation`, which is always null in default worlds): `neighbor_changed`, `update_shape`,
  `update_indirect_neighbour_shapes`, `on_place`, `affect_neighbors_after_removal`, `tick`,
  `trigger_event`, `can_survive`, `get_signal`, `get_direct_signal`, `own_signal`,
  `is_signal_source`, `should_redstone_wire_connect_to`, `has_analog_output_signal`,
  `get_analog_output_signal`, plus the player hooks `get_state_for_placement`,
  `set_placed_by`, `use_without_item`, `player_will_destroy`, `destroy`.

### How a Java block becomes a Python block

1. Read the block class and its `Blocks.java` registration (properties, push reaction,
   conductor override, collision).
2. Create a `Block` subclass with the same properties (value order from
   `BlockStateProperties`) and default state.
3. Port each overridden hook line by line, citing `Class.method` and decompile line.
4. Register it in `blocks/__init__.py`, add its id to `ids.py` if engine code checks it.
5. Write unit tests (`tests/sim/test_components.py` style, with `tests/sim/bench.py`) and,
   where commands can drive it, a game scenario in `tools/gameserver/scenarios.py`.
6. Update its mechanics page and [[project-state]].

## Simulation engine

### Level (`sim/level.py`)

Holds all mutable world state:

| Field | Java counterpart |
|---|---|
| `blocks: dict[Pos, BlockState]` (absent = air) | chunk sections |
| `block_entities: dict[Pos, BlockEntity]` | `LevelChunk.blockEntities` |
| `game_time`, `sub_tick_count` | `LevelData.gameTime`, `Level.subTickCount` |
| `block_ticks: LevelTicks` | `ServerLevel.blockTicks` |
| `block_events: dict[(pos, block_id, b0, b1), None]` | `ObjectLinkedOpenHashSet<BlockEventData>` |
| `tickers`, `pending_tickers`, `tickers_by_pos` | `Level.blockEntityTickers`, pending list, `LevelChunk.tickersInLevel` |
| `ticking_block_entities`, `handling_tick` | same names |
| `torch_toggles` | `RedstoneTorchBlock.RECENT_TOGGLES.get(level)` |
| `neighbor_updater` | `Level.neighborUpdater` |

Main operations: `set_block(pos, state, flags, limit)` (the full flag pipeline, see
[[mechanics/neighbor-updates]]), `update_neighbors_at`, `neighbor_changed`,
`neighbor_shape_changed`, the `SignalGetter` queries (`get_signal`, `get_direct_signal_to`,
`has_neighbor_signal`, `get_best_neighbor_signal`, `get_control_input_signal`),
`schedule_tick`, `block_event`, block-entity management, and `clone()` for snapshots.

### Engine (`sim/engine.py`)

A tick is an explicit state machine, so it can stop between any two engine steps:

```text
BETWEEN_TICKS ──step: tick_start (time+1, collect due ticks)──▶ BLOCK_TICKS
BLOCK_TICKS   ──step: one scheduled tick──▶ … (settle when empty) ──▶ BLOCK_EVENTS
BLOCK_EVENTS  ──step: one block event────▶ … (settle when empty: handling_tick=false,
                                               pending tickers join) ──▶ BLOCK_ENTITIES
BLOCK_ENTITIES──step: one ticker─────────▶ … (settle when done) ──▶ BETWEEN_TICKS
BETWEEN_TICKS ──apply(Action)──▶ BETWEEN_TICKS   (player/command input)
```

- `step()` runs exactly one engine step; `_settle()` then skips empty phases (bookkeeping
  only, no game logic), so `engine.phase` always names the phase of the next step.
- `run_tick()`, `finish_tick()`, `run_ticks(n)`; `peek_next_step()` describes the next step.
- `apply(Action)` accepts inputs only between ticks, as in the game:
  - `place` → `BlockItem.place` (flags 11 + `setPlacedBy`); the editor supplies the
    orientation in the requested state;
  - `break` → `ServerPlayerGameMode.destroyBlock`;
  - `use` → `useWithoutItem`;
  - `setblock` → `SetBlockCommand` (replace mode): `BlockInput.place` with flags 258
    (state adjusted by neighbor shapes, explicit properties re-applied), then
    `updateNeighboursOnBlockSet`;
  - `set_block` → raw `Level.setBlock` with explicit flags (editor tool, not vanilla);
  - `fill` → `FillCommand` (replace mode): `/setblock`-style placement of a box (x fastest,
    then y, z), then `updateNeighboursOnBlockSet` for every changed position;
  - `clone` → placement half of `CloneCommands.clone` (replace mode): blocks grouped solid →
    block entities → others, barrier placeholders, flags 2, block-entity data, reverse-order
    neighbor updates. Used for paste; scheduled ticks are not copied (ADR-015).
- `snapshot()` / `restore()` capture the whole engine (level clone, phase, step index,
  block-entity iteration index). Restoring and re-running reproduces the same steps
  (tested).

### Timeline (`sim/timeline.py`): history, rewind, replay

Implements [[decisions]] ADR-004. Every engine step and every action advances
`Engine.step_index`. The timeline stores keyframe snapshots (at the start, before every
action, and every `keyframe_interval` steps, thinned when there are more than 400), the action
applied at each step index, and the indices of tick starts.

- `step()`/`run_tick()` advance; inside the recorded range they re-apply recorded actions.
- `apply(action)` records a new action; doing so before the recorded end drops the future
  (a new branch).
- `seek(i)` restores the nearest keyframe ≤ i and re-executes. `step_back()`, `tick_back()`
  (previous tick boundary), and undo/redo targets (just before / after an action) build on it.
- On rewind the trace is truncated to steps before the target. Replay regenerates identical
  records with identical ids.

Tested: seeking to random points reproduces the recorded world state exactly (keyframe
intervals 1, 7, 200), and replay after rewind reproduces the trace.

### What counts as "sub-tick"

The game has no universal sub-tick concept. The pausable unit is the engine step above.
Inside a step, the trace records each neighbor update, shape update, block change, tick
request and block-event request with its causal parent ([[decisions]] ADR-003).

### Trace (`sim/trace.py`)

`Trace.emit(kind, pos, parent=…, **detail)` appends a `TraceRecord(id, kind, parent,
game_time, step, pos, detail)`. Engine steps are roots. A neighbor or shape update records
the cause that queued it, because the collecting updater may run it later than it was
requested. Kinds: `step`, `neighbor_update`, `shape_update`, `set_block`, `schedule_tick`,
`block_event_queued`, `block_entity`, `note`.

## Verification architecture

| Layer | Tool | What it proves |
|---|---|---|
| Java library behavior | `tools/java_oracle` + `tests/core/test_javahash.py` | hash iteration order equals a real JDK's |
| Engine semantics | `tests/sim/probe.py` probe blocks | update order, depth-first semantics, flags, priorities, phases, snapshot replay |
| Block rules | `tests/sim/test_components.py` with `tests/sim/bench.py` | source-derived behavior of each block |
| Real game | `tools/gameserver` → `experiments/results/*.json` | tick-by-tick states equal the 26.3 server's |
| Regression | `tests/sim/test_game_verified.py` | the simulator still reproduces every recording (no server needed) |

The game harness ([[decisions]] ADR-008) runs the supplied server in `.sandbox/gameserver`
(gitignored, offline, 127.0.0.1 only). It builds each scenario with `/setblock`, advances
with `/tick step 1`, and checks the simulator's predicted full state of every watched block
with `execute if block`. Details: [[experiments/index]], [[implementation-notes]].

## Editor layer (`redsim.editor`, no Qt)

- `Document` owns the `Engine`, the `Sections` annotations, the file path, a revision counter
  (the UI updates the changed mesh chunks when it changes) and a snapshot-based undo/redo stack for edits.
- Edits are engine actions and are only allowed between ticks, as in the game:
  `place` (player placement), `break`, `use` (right click), and inspector edits as `setblock`
  (`/setblock` semantics, stated in the UI tooltip) ([[decisions]] ADR-013).
- `placement.py` ports `Direction.orderedByNearest`,
  `BlockPlaceContext.getNearestLookingDirections` and the per-block placement rules
  (face-attached, torch item, diodes), so the editor produces the states a player at that
  yaw/pitch clicking that face would get.
- `annotations.py`: named sections with colors, purely visual, saved in the file's `extra`.

## Contraptions (`redsim.editor.clipboard`, `redsim.editor.groups`)

- `Region` (two corners, `/clone` iteration order), `Prefab` (all positions of a region,
  relative, with state strings and block-entity data; JSON format `redsim-prefab`).
  `Prefab.rotated(n)` rotates offsets and states (`redsim.world.rotation`).
- Paste = `Action("clone")` at the target, so it is recorded in the timeline (undo/replay).
- Moving or copying a selection in place = `Action("clone_region")`, the full
  `/clone … replace move|force` on the live world, scheduled ticks included (ADR-019).
  Delete = `Action("fill")` with air.
- Groups name a region and expose ports (named input/output positions). They are
  annotations only: the circuit inside still simulates block by block with unchanged timing
  (ADR-016). The panel shows live port readings and can use an input port's block.
- Prefab library and groups are saved in the document's `extra`.

## Persistence (`redsim.io.save`)

One JSON document (`format: redsim-save`, `version: 1`) with a block palette, block
entities, pending and collected scheduled ticks, block events, ticker wrappers (identity
preserved), counters, torch toggles, flags and the engine position, plus editor `extra`
(sections). Loading a save made mid-tick and continuing reproduces the original steps
(tested).

## User interface (`redsim.ui`)

| Module | Role |
|---|---|
| `style.py` | Block → colored boxes in pixels by functional category (no textures); wire color uses the game's power formula; orientation transforms |
| `geometry.py` | Vectorized mesh building per 8³ chunk with dirty tracking (`Mesher`, `ChunkedMesh`: face culling between full cubes, separate translucent buffer, checkerboard tint) and CPU picking (voxel traversal + ray/box tests on the same boxes) |
| `camera.py` | Orbit camera around a pivot with Minecraft yaw/pitch conventions; view/projection matrices; cursor rays; JSON form (reads the old fly-camera form) |
| `keymap.py` | All input bindings as actions with defaults; user overrides from a JSON file; conflict checks; mode-aware mouse lookup (no Qt) |
| `renderer.py` | One shader through PySide6's GL wrappers; an opaque and a translucent buffer per chunk, plus one line buffer |
| `pacing.py` | Real-time run pacing (`TickPacer`) and rate measurement (`RateMeter`), no Qt |
| `selection_tools.py` | Selection handles, resize and drag-plane math (no Qt); the edits are `/clone` actions (ADR-019) |
| `viewport.py` | `QOpenGLWidget`: modes, mouse gestures via the keymap, orbit camera, hover, selection box, pivot and mode badge; emits edit signals only |
| `panels.py` | Palette (with hotbar), inspector, simulation controls, diagnostics, sections, controls help |
| `main_window.py` | Wires panels to the `Document`; menus and shortcuts; run loop |
| `app.py` | Entry point; selects `xcb` under Wayland; requests an OpenGL 3.3 core context |

Controls: vim-like modes (NORMAL/BUILD/SELECT), an orbit camera around a drawn pivot and a
rebindable keymap; the full reference is [[controls]], the design is ADR-018. Mouse input
is resolved as *(mode, modifiers, button, click|drag|wheel) → action*; a press becomes a drag
after 4 pixels of movement, otherwise a click on release.

The viewport targets the block under the mouse cursor (an editor convenience; the game
uses the screen center). The renderer never writes world state.

### Look (owner: "simple but slick, still Minecraft")

- Full blocks get Minecraft-like smooth-lighting corner shading (each face corner darkened
  by how many of its three outer neighbors are full blocks) and a stable ±5 % per-block
  brightness variation instead of a checkerboard (`geometry.AO_LEVELS`, `block_noise`).
- A sky gradient behind the world and soft distance fog into the horizon color; selection
  gizmos, outlines and overlays are never fogged (`renderer.py` shaders).

### Rendering and the run loop ([[decisions]] ADR-017)

- **Chunked meshes.** The world mesh is split into 8³-block chunks. Before drawing, when the
  document revision changed, `ChunkedMesh.update` diffs the block map against the last one
  it saw (so timeline seeks, which swap in a restored level, need no special case). A
  changed block dirties its chunk and its 6 neighbors' chunks (culling looks across
  borders). Only dirty chunks are rebuilt and re-uploaded. Chunks with moving pistons are
  rebuilt on every update, because their look follows the block entity's progress.
- **Vectorized geometry.** Each distinct face (box, direction, color) is a cached template of
  6 vertices; a block state maps to its template ids. Building a chunk is one lookup per
  block, then a numpy gather plus offset.
- **Decoupled simulation.** A precise 5 ms timer asks `TickPacer` how many ticks are due by
  the wall clock and runs them (at most 35 ms per call, so input stays responsive), then
  requests a single repaint. Falling more than 0.25 s behind drops the backlog instead of
  racing. Panels refresh at most 10 times per second while running. The viewport overlay
  shows the achieved ticks/s and frames/s.
- Measured on the example world (2026-10-11, owner's desktop): 19.9 ticks/s at target 20,
  paint 1.9 ms mean; full mesh build 9 ms (was 51 ms); one tick plus incremental mesh update
  0.17 ms; warp on the idle world about 160 000 ticks/s.

## Related

[[project-state]] · [[decisions]] · [[roadmap]] · [[research/source-map]] · [[mechanics/index]]
