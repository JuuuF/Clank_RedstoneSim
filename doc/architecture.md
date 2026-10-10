# Architecture

## Goal of the design

Reproduce Java Edition 26.3 redstone state and timing by **porting the relevant server-side
algorithms one-to-one into Python**, not by designing an independent redstone model. Every
simulation module mirrors a specific Java class or method and cites it. Anything without
redstone relevance (lighting, sounds, particles, entities, game events, client sync) is left
out and documented as out of scope.

## Layers

```text
src/redsim/
├── core/          Direction, BlockPos helpers, Java collection-order emulation (no game logic)
├── world/         Properties, block states, block definitions + behaviors, registry
├── sim/           Level (setBlock pipeline, signal queries), neighbor updater, scheduled ticks,
│                  block events, block-entity ticking, engine phases, trace, history
├── io/            Save/load (JSON) of world + full engine state + annotations
└── ui/            PySide6 application: viewport, camera, picking, palette, inspector,
                   simulation controls, diagnostics (depends on everything above)
tests/             pytest suites; no test imports `redsim.ui` except explicit UI smoke tests
```

Dependency direction is strictly downward: `ui → io → sim → world → core`. The simulation
never imports Qt and never reads rendering state. Section colors and labels are stored as
annotations next to the world, not inside block states.

## Simulation core

### World model

- **Positions** are plain `(x, y, z)` integer tuples (hashable, immutable, fast).
- **Directions** use Java's ordinal order `DOWN, UP, NORTH, SOUTH, WEST, EAST`, because
  several update loops iterate `Direction.values()`.
- **Block states** are interned immutable objects, one per property combination, so state
  identity (`is`) behaves like Java reference equality on `BlockState`.
- **Blocks** carry mechanically relevant attributes as separate, explicit methods:
  collision-full-block, redstone conductor, face sturdiness per support type, push reaction,
  destroy speed, block entity presence, signal source, and so on. They are deliberately not
  merged into one "solid" flag (see [[mechanics/block-properties]]).

### Engine (mirrors `ServerLevel`)

- `Level.set_block(pos, state, flags, limit)` ports `Level.setBlock` +
  `LevelChunk.setBlockState`: remove side effects, `onPlace`, neighbor updates, comparator
  output updates, shape updates, flag handling.
- `CollectingNeighborUpdater` is ported line for line (depth-first stack plus
  `addedThisLayer`, chain limit).
- `LevelTicks` behavior: collect due ticks once per tick, run in (priority, subTickOrder) order,
  dedupe per (pos, block), level-wide sub-tick counter, `willTickThisTick`/`hasScheduledTick`.
- Block events: insertion-ordered dedup queue processed until empty, including events
  queued while processing.
- Block-entity tickers: one level-wide ordered list with per-position rebindable wrappers.
- `java.util.HashSet`/`HashMap` iteration order is emulated where the game relies on it.

### Engine steps and the "sub-tick" question

Minecraft has no single universal "sub-tick" concept. The simulator exposes the server's
own structure:

| Engine step (atomic unit) | Java origin |
|---|---|
| `tick start` | `ServerLevel.tick` up to `tickTime` + scheduled-tick collection |
| `scheduled tick` (one per collected tick) | `LevelTicks.runCollectedTicks` → `ServerLevel.tickBlock` |
| `block event` (one per dequeued event) | `ServerLevel.runBlockEvents` → `doBlockEvent` |
| `block entity` (one per ticker) | `Level.tickBlockEntities` |
| `tick end` | end of `ServerLevel.tick` |
| `player action` (between ticks) | packet tasks between `tickChildren` calls |

An engine step can be paused before or after, saved, and rewound to. Inside a step, the
engine records a **trace** of everything it did (neighbor updates, shape updates, block
changes, scheduled ticks, queued block events), each with a causal parent. The UI can scrub
through the trace's block changes for inspection, but execution only stops at step
boundaries (the Java call stack inside a step is not resumable, and the game itself never
pauses there). See [[decisions#ADR-003]].

### History and determinism

The engine is fully deterministic: no randomness enters any simulated decision (randomness in
the source only affects sounds, particles, and the disabled experimental redstone).
History is event-sourced: an initial state, a log of player inputs with their step position,
and periodic keyframe snapshots of the full engine state. Rewinding restores the nearest
keyframe and re-executes deterministically. See [[decisions#ADR-004]].

## User interface

PySide6 (Qt Widgets) main window with a `QOpenGLWidget` viewport using PySide6's own
OpenGL wrappers (no PyOpenGL dependency). Picking uses a CPU voxel ray cast against the world
model. Meshes are rebuilt from world snapshots by a renderer module that only reads world
state. See [[decisions#ADR-002]].

## Related

[[decisions]] · [[roadmap]] · [[research/source-map]] · [[mechanics/index]]
