# Architecture decision records

Short records. Each one states the context, the decision, and its trade-offs.

## ADR-001

**Port the server algorithms instead of modelling redstone abstractly**

- **Context:** Fidelity to 26.3 timing and update order is the main success criterion.
  Update order emerges from many interacting details: the collecting neighbor updater, wire
  hash-set order, setBlock flags, shape updates, scheduled-tick priorities, block-event
  dedup, block-entity ticker order.
- **Decision:** Mirror the Java methods one-to-one in Python (same control flow, same
  iteration orders, same flags), restricted to the blocks in scope. Each ported method cites
  its source method.
- **Trade-offs:** More code per block than a simplified model, and Python is slower than
  Java. In return, behavior such as locational wire order, bud-powering, and
  quasi-connectivity emerges without special-casing. Contraptions in scope are small
  enough that speed is acceptable.

## ADR-002

**PySide6 + QOpenGLWidget for the UI**

- **Context:** A 3D viewport plus conventional panels (palette, inspector, controls,
  diagnostics) is needed. Installed: PySide6 6.9.2, PyQt5/6, tkinter, numpy. Not installed:
  PyOpenGL, moderngl, pyglet, panda3d, vispy.
- **Prototype:** A 60-line test (job scratch area, not in the repo) rendered shaded cubes
  through `QOpenGLShaderProgram`, `QOpenGLBuffer`, `QOpenGLVertexArrayObject` and
  `QOpenGLFunctions.glDrawArrays` into an FBO, under both `xcb` and `offscreen` platforms.
- **Decision:** PySide6 Widgets with a `QOpenGLWidget` viewport and PySide6's built-in GL
  wrappers. No new dependency.
- **Alternatives considered:** pyglet or panda3d (would need a second toolkit for the
  panels); PyOpenGL or moderngl (an extra dependency for no capability we need); Qt3D
  (deprecated in Qt 6).
- **Trade-offs/constraints:** This PySide6 build cannot create a GL context on the native
  Wayland platform plugin, so the app selects `xcb` (XWayland) under Wayland unless
  `QT_QPA_PLATFORM` is set. Offscreen rendering works, which enables headless UI smoke
  tests.

## ADR-003

**Engine steps as the "sub-tick" unit, trace for finer detail**

- **Context:** The brief asks for event stepping without inventing equal-sized sub-ticks.
- **Decision:** The pausable unit is one *engine step* (one scheduled tick, one block event,
  one block-entity tick, tick start and end, one player action). Finer events inside a step
  (each neighbor/shape update and block change) are recorded in a causal trace that the UI
  can replay for inspection.
- **Trade-offs:** The user cannot change the world between two neighbor updates of the same
  step. The game cannot pause there either, so no real behavior is lost.

## ADR-004

**Event-sourced history with keyframes and deterministic replay**

- **Context:** Rewind must restore world state, scheduled ticks, block events, ordering
  metadata (sub-tick counter, ticker order) and in-tick progress, and replay must match the
  original trace.
- **Decision:** Store the initial engine state, a log of player inputs with the engine-step
  index at which they were applied, and full snapshots every N ticks. Rewind = restore the
  nearest earlier snapshot, then re-execute. Editing after a rewind truncates the future
  (as with undo).
- **Trade-offs:** Rewinding far back costs re-simulation time instead of memory. Full
  snapshots are cheap here because block states are interned and immutable.

## ADR-005

**Emulate Java hash iteration order**

- **Context:** `DefaultRedstoneWireEvaluator.updatePowerStrength` iterates a
  `HashSet<BlockPos>`, and `PistonBaseBlock.moveBlocks` iterates a `HashMap<BlockPos, …>`. Their
  iteration orders depend on `BlockPos.hashCode()` and the table size, which is the source
  of location-dependent behavior.
- **Decision:** Implement a small `JavaHashMap`/`JavaHashSet` emulation (bucket index
  `(h ^ (h >>> 16)) & (cap − 1)`, insertion order within a bucket, resize at 0.75 load, order
  preserved on split) and use it exactly where Java uses those collections.
- **Trade-offs:** Treeified buckets (8 or more colliding keys with capacity ≥ 64) are not
  emulated; the emulator raises an error in that case instead of silently diverging. In-scope
  sets have at most a few dozen entries.

## ADR-006

**Experimental redstone is out of scope**

- **Context:** 26.3 still contains `ExperimentalRedstoneWireEvaluator` and `Orientation`,
  active only with the `redstone_experiments` feature flag (`FeatureFlags.REDSTONE_EXPERIMENTS`).
- **Decision:** Simulate default worlds only: orientation is always `null`, and the default
  wire evaluator is used.

## ADR-007

**World model before editor**

- **Context:** The roadmap orders the editor (M2) before the simulation foundation (M3).
  Placing a block correctly needs the block's placement-state logic and the setBlock
  pipeline (wire connections, repeater locking, placement updates).
- **Decision:** Build the shared world model first, then the editor and the engine on top of
  it, so the editor never relies on a throwaway model. The milestone deliverables stay the
  same.
