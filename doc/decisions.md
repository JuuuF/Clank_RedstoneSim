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
- **Implemented (2026-10-11):** `redsim.sim.timeline.Timeline`. Undo/redo of edits uses the
  same timeline (ADR-013 updated). Saves store only the current state, not the history.

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

## ADR-008

**Compare against the real game with a sandboxed dedicated server**

- **Context:** Unit tests alone only check the simulator against its own reading of the
  source. The brief asks for in-game comparison, and the agent cannot run the client.
- **Decision:** With the owner's approval and EULA acceptance (2026-10-10), run the supplied
  `server.jar` headlessly in `.sandbox/gameserver/`: offline, 127.0.0.1, no remote
  endpoints, fresh superflat world, used for behavior testing only. `tools/gameserver`
  drives it through the console and compares every watched block state after every tick.
  Recordings go to `experiments/results/` and are replayed by tests.
- **Trade-offs:** Only tick-boundary states are observable, and only command-driven inputs
  are possible (no player to pull levers). Each run takes about 10 s of startup plus about
  0.1 s per tick per scenario.

## ADR-009

**Command-driven inputs mirrored exactly in the simulator**

- **Context:** A game comparison needs identical inputs. `/setblock` is not the same as a
  player placing a block: it skips `getStateForPlacement` and `setPlacedBy`, and it uses
  flags 258 plus `updateNeighboursOnBlockSet`.
- **Decision:** Port `SetBlockCommand` (replace mode) as `Action("setblock")` and use it for
  scenario setup and inputs on both sides. Player actions (`place`, `use`, `break`) remain
  separate, faithful ports for the editor.
- **Trade-offs:** Scenario states can differ from hand-built ones. For example,
  `/setblock redstone_wire` creates a dot when nothing connects. This is intended: it is what
  the game does.

## ADR-010

**Torch burnout is simulated**

- **Context:** The brief listed "random burnout" as out of scope. The 26.3 source shows
  burnout is deterministic (8 turn-offs of one position within 60 game ticks; 160-tick
  restart; a per-level toggle list shared by all torches).
- **Decision:** The owner approved implementing it (2026-10-10). The toggle list lives in
  `Level.torch_toggles`, so snapshots and future saves include it. Verified in game
  (EXP-005, EXP-006).

## ADR-011

**Wiki pages are hints, the source is proof**

- **Context:** The owner supplied stripped Minecraft Wiki pages in `data/wiki/` (redstone
  components, quasi-connectivity, instant repeaters, redstone tutorial).
- **Decision:** Use them to find test ideas and known quirks, and confirm every claim in the
  26.3 source or in game before relying on it. See [[research/wiki-hints]].

## ADR-012

**Repository docs are the project's long-term memory**

- **Context:** Work spans many sessions; the owner asked for project state and
  architecture to live in the docs, and for agent-side notes to stay minimal.
- **Decision:** [[project-state]] is the handoff page, updated after every slice together with
  [[roadmap]], [[architecture]], mechanics pages and the experiment log. New sessions start
  from [[README]].

## ADR-013

**Editor edits are engine actions; inspector edits use /setblock semantics**

- **Context:** The editor needs both "play like a player" and "set this exact state". A raw
  state write without updates would create states the game never produces.
- **Decision:** Viewport clicks map to the player actions (`place`, `break`, `use`), with
  orientation ported from `BlockPlaceContext`. Inspector property edits use `/setblock`
  semantics, which is a vanilla, documented behavior and the same one the game harness
  uses. All edits happen between ticks. Undo rewinds the timeline to just before the most
  recent edit (including any simulation steps after it); redo replays forward. Section
  annotations are not part of the timeline.
- **Trade-offs:** A `/setblock` edit can leave components un-updated, exactly as in the game
  (for example, setting a lever to `powered=true` does not update the attached block's
  neighbors). The tooltip says so.

## ADR-014

**Cursor targeting instead of a crosshair**

- **Context:** Minecraft targets the screen center. In an editor with free mouse movement,
  aiming with the cursor is faster.
- **Decision:** Hover/target follows the mouse cursor; looking around needs a right-drag.
  Placement orientation still uses the camera's yaw/pitch like the game's player view.

## ADR-015

**Paste follows `/clone`, delete follows `/fill`**

- **Context:** Copying circuits needs defined update behavior. Inventing a placement order
  would produce states the game never produces.
- **Decision:** Paste ports the placement half of `CloneCommands.clone` (replace mode, not
  strict): grouping, barrier placeholders, flags, block-entity data and reverse-order
  neighbor updates. Delete uses `FillCommand` with air. Both are recorded as timeline
  actions. Verified in game (EXP-021, EXP-022).
- **Trade-offs:** `/clone` also copies pending scheduled ticks; prefabs do not (they are
  stored snapshots that can be pasted much later), so paste circuits at rest. Rotation has
  no `/clone` equivalent: a rotated prefab behaves as if captured from a rotated copy of the
  region (z/y/x order of the rotated positions).

## ADR-016

**Groups are annotations; abstract (black-box) models are deferred**

- **Context:** The brief asks for grouping with exposed inputs/outputs, without hiding
  internal behavior or changing timing unless the user explicitly chooses an abstract model.
- **Decision:** A group is a named region with named input/output ports. The simulation
  is unaffected. The UI shows live port readings and can toggle input ports that hold a
  usable block.
- **Future option:** An explicit "abstract model" could replace a group's internals with a
  declared truth table and delay. That would change timing semantics, so it needs its own
  design and opt-in. Not implemented.

## ADR-017

**Real-time rendering: chunked dirty meshes, simulation paced by the wall clock**

- **Context:** The owner saw about half speed. The engine ran about 1 000 ticks/s; the
  renderer rebuilt the whole world mesh (51 ms) after every tick, and the run timer ran one
  tick per timeout, so drawing set the tick rate.
- **Decision:** As the game client does it: per-chunk meshes with dirty tracking and
  rendering decoupled from ticking. Chunks are 8³ rather than the game's 16³ sections,
  because a Python rebuild of a dense 16³ section would take several milliseconds. Changes
  are found by diffing the block map (0.04 ms for 1 000 blocks, 2.3 ms for 50 000), not by a
  change journal in `Level`. The diff needs no hook in the simulation hot path and also
  covers timeline restores, loads and direct test writes. The run loop computes due ticks
  from the wall clock (`redsim.ui.pacing.TickPacer`) and repaints once afterwards.
- **Trade-offs:** Blocks carried by a moving piston are never treated as full cubes for face
  culling, so a few hidden faces are drawn while something moves. If worlds grow far beyond
  50 000 blocks, a journal in `Level._chunk_set_block_state` can replace the diff. Vertices
  are world-space float32, which loses precision at very large coordinates (chunk-relative
  vertices plus a per-chunk offset would fix that).
