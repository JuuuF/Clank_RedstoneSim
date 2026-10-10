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
│   ├── trace.py           causal trace records
│   └── engine.py          tick phases as steps, actions, snapshots
├── io/                    (planned) save/load
└── ui/                    (planned) PySide6 application
tests/                     pytest suites (core, world, sim); tests/sim/probe.py = test-only blocks
tools/
├── java_oracle/           HashOrderOracle.java (real-JVM check for javahash)
└── gameserver/            sandboxed 26.3 server harness, scenarios, comparison runner
experiments/results/       JSON recordings from the real game (evidence, replayed by tests)
doc/                       this documentation (Obsidian vault)
```

Dependency direction is strictly downward: `ui → io → sim → world → core`. `tools` and
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
  - `set_block` → raw `Level.setBlock` with explicit flags (editor tool, not vanilla).
- `snapshot()` / `restore()` capture the whole engine (level clone, phase, step index,
  block-entity iteration index). Restoring and re-running reproduces the same steps
  (tested).

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

## User interface (planned, M2)

PySide6 (Qt Widgets) main window with a `QOpenGLWidget` viewport using PySide6's own
OpenGL wrappers (no PyOpenGL). Picking uses a CPU voxel ray cast against the world model.
Meshes are rebuilt from the world by a renderer that only reads state. Controls are
Minecraft-like: WASD plus mouse look while the right button is held, left-click breaks,
right-click places, middle-click picks a block (confirmed by the owner). Under Wayland the
app uses `QT_QPA_PLATFORM=xcb` (ADR-002).

## Related

[[project-state]] · [[decisions]] · [[roadmap]] · [[research/source-map]] · [[mechanics/index]]
