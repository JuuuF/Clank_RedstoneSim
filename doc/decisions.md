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

## ADR-018

**Controls: modes, orbit camera and a rebindable keymap**

- **Context:** The owner disliked overloaded clicks and the Shift+T rewind (Shift also moved
  the fly camera down) and chose vim-like modes, a Blender-style orbit camera, Minecraft
  build clicks and a keymap that can be rebound later ([[ui-direction]]).
- **Decision:** All inputs are named actions with defaults in `redsim.ui.keymap`; a JSON
  file overrides them. Mouse actions are prefixed with the mode they belong to
  (`build.place`) or are mode-independent (`camera.orbit`, `pick`); mode-specific bindings
  win. The camera is an orbit camera (pivot, distance, yaw, pitch). Modifier keys never act
  on their own, so they cannot collide with shortcuts; rewinding moved to ← / Shift+←.
  Choosing a block enters BUILD. Placement orientation uses the cursor ray, i.e. a player
  looking from the camera at the targeted block.
- **Alternatives:** Qt's own shortcut settings only cover keys, not mouse gestures or held
  keys. A rebinding dialog can be built on the same keymap later.
- **Trade-offs:** Several defaults share a key across contexts (Left Click in each mode);
  conflicts are only reported within one context. Laptop users without a middle button get
  Alt+left drag (Blender's emulation).

## ADR-019

**Selection drags are `/clone … move` and `/clone … force`**

- **Context:** Axiom-like editing moves and copies selections in place. The simulator must
  not invent an update order for that.
- **Decision:** A drag becomes one engine action `clone_region` that ports the whole
  `CloneCommands.clone` reading the live source: the overlap check (normal mode), the area
  limit (32 768), block grouping, the clear list and barrier/air clearing of `move`, the
  placement passes and `LevelTicks.copyAreaFrom`. Moving uses `move`, copying uses `force`
  (copies may overlap). Game-verified (EXP-023), including the copied scheduled tick.
- **Consequences:** A moved circuit keeps running (its pending ticks come along); one drag
  is one undo step. Paste of a stored prefab still uses the placement half only (no
  ticks), since prefabs are snapshots.
- **Amendment (owner, 2026-10-11): editor clones cause no block updates.** Paste, move,
  copy and stack use `/clone … strict` (flags 818: no shape updates, no `onPlace`, no final
  `updateNeighboursOnBlockSet`; block-entity `setChanged` still runs, as in the game).
  Budded components stay budded. Game-verified against a normal clone (EXP-026). Deleting
  a selection (`/fill` with air) still updates neighbors, so blocks that lose their support
  pop as in the game.

## ADR-021

**Rotate, flip and stack selections in place: editor tools without block updates**

- **Context:** The owner called rotating and flipping essential (blocks inside must turn
  too) and wanted stack/repeat. The game has no command that turns a region in place.
- **Decision:** One engine action `transform_region` captures the box (states,
  block-entity data, pending ticks), clears it and places the transformed blocks with the
  strict `/clone` placement passes; states turn with the ported `BlockState.rotate` /
  `mirror` rules (`world/rotation.py`); ticks are rescheduled at their blocks' new places.
  `stack_region` is N strict force-clones. Both are one undo step, without block updates
  (consistent with the ADR-019 amendment).
- **Pivot:** a quarter turn only maps cells onto cells around points whose doubled x and z
  have equal parity. The default pivot is the box center, shifted half a block when exactly
  one side length is odd; the editor keeps that pivot while the same selection is turned
  again, so turning back, or four times, returns exactly to the start.
- **Verification:** unit tests and source reading (state rules); the placement passes are
  the game-verified strict `/clone` ones (EXP-026).
- **Addendum (2026-10-14, several selections):** `transform_regions` generalizes it to
  several boxes moved together: every cell of the boxes is captured once (in z/y/x order
  over their bounding box), the sources are cleared unless copying, and the blocks are
  mirrored within the bounding box, turned around its middle and shifted; ticks go along
  (copied ticks sort after the existing ones, like `copyAreaFrom`). Moving boxes one by
  one would let a box land on another's source before that one is read. A single box
  still drags with the game's `/clone … strict move` and turns through the same code.

## ADR-020

**One "signal source" in the UI, real blocks underneath, set with `/setblock` data**

- **Context:** The owner found the cake odd as the comparator source and asked for a generic
  signal-strength source backed by real blocks, hot-swappable, with tooltips on how they
  differ ([[ui-direction]]).
- **Decision:** Barrel and lectern are implemented as real blocks with block entities
  ([[mechanics/analog-sources]]). The editor's source operations (place, change strength,
  swap kind) are `/setblock <state>{<data>}` edits: barrels get the fewest redstone dust for
  the strength, lecterns a 15-page book at page `strength − 1`, cakes the matching bites
  (even values only). Turning a lectern page like a player is a separate action, because it
  also pulses.
- **Why `/setblock` with data:** one action per change (one undo step), deterministic, and
  checkable on the test server (EXP-024, EXP-025). The game has no command for a player's
  page turn; that path is verified from the source.
- **Trade-offs:** A barrel's strength is not visible on the block itself (it lives in the
  block entity); the inspector and the comparator show it. Swapping kinds keeps the facing
  when the new block can take it (barrel up → lectern north).

## ADR-022

**Tick 0 is the build; edits form batches; history can be rewritten**

- **Context:** Fourth feedback round ([[ui-direction]]): the timeline replayed the whole build
  process, placements made at one moment appeared one after another during replay, replays
  sometimes stopped with "player actions happen between ticks", and the owner wants to move
  and merge keyframes (for example all placements made while the simulation ran).
- **Bug found:** `Engine.apply` counts the step before running the action. An edit that
  failed (clicking an occupied cell, missing support) consumed a step without being
  recorded, so every later recorded edit replayed one step off, inside a tick. Fixed in
  `Timeline.apply`: a failed action restores the engine to the snapshot before it.
- **Decision:**
  - The timeline's start is the **base** (tick 0, the build state). Edits made there are
    applied through the engine as usual (same block updates) and then folded into the base
    snapshot (`Timeline.apply_to_base` → `rebase`): never recorded, never replayed. Ticks
    are shown relative to the base, so a file saved at game time 4 starts at tick 0.
    "Set tick 0 here" rebases at any tick boundary: the history before it goes, edits
    recorded later move along (shifted) and the simulated length is kept (one undo step).
  - Edits at later ticks are recorded with their tick. Edits at one tick boundary form a
    **batch**: `run_tick` applies the recorded edits of a boundary together with that tick,
    so they appear at once (engine stepping still shows them one by one).
  - The history is defined by `HistoryState` = base snapshot + edit plan (tick → actions) +
    simulated length. `Timeline.rewrite` rebuilds it by re-simulating; moving, merging and
    deleting edit batches, moving them into the build (tick 0), and undo/redo are all
    "restore a different history state". Undo therefore removes an edit from the replay
    (it no longer comes back when the simulation runs again) and keeps the simulated
    length. Edits that cannot be applied at their new tick are dropped and reported.
  - Edit batches are shown per row (placed, removed, changed, used: `edit_row`), each row
    color-coded; an action carries an editor label for tooltips.
- **Trade-offs:** Rewrites re-simulate from the base, which costs time proportional to the
  recorded length (milliseconds per hundred ticks for typical circuits). Undo states keep
  their base snapshots alive (immutable, shared). Editing the past used to drop the recorded
  future (ADR-004); since 2026-10-15 (owner: keyframes "are supposed to remain where they
  are") an edit inside the recorded history, at tick 0 too, keeps every later edit at its
  tick: `Document._apply` puts them back after the edit (after the whole batch, so a dragged
  line re-runs once) and re-simulates to the old length. Later edits that no longer apply
  (their cell is taken) are dropped and reported; undo restores them.

## ADR-023

**The game's block models and textures, read at runtime from the supplied jar**

- **Context:** The owner asked whether the real models could be used: "using the real
  textures and updating only some of them would make it feel way better" (sixth round,
  [[ui-direction]]). The brief forbids modifying the supplied JARs or copying them
  wholesale.
- **Decision:** `redsim.ui.assets` opens `data/minecraft_jars/client.jar` (or
  `$REDSIM_MINECRAFT_JAR`) read-only at runtime and ports the client's model pipeline:
  blockstate variants and multipart, model parents and texture references, and face baking
  as in `FaceBakery` (default UVs, `FaceInfo` vertex order, UV rotation, element rotation
  with rescale, variant x-then-y rotation, cull faces, tint index, shade override).
  `redsim.ui.atlas` packs the referenced textures into one atlas; the mesher draws model
  quads with the game's cull faces, our corner shading and tints (dust by power). Item
  sprites and textured block renders serve as inventory previews; the game's bitmap font
  is used for overlays. Nothing from the jar is written into the repository.
- **Fallback:** without the jar (or with View → Game textures off, or
  `REDSIM_NO_GAME_ASSETS`), the colored box models of `style.py` are used, as before.
- **Trade-offs:** `uvlock` is not applied (no in-scope block needs it); animated textures
  show their first frame; the renderer now culls back faces like the game (flat parts show
  one side). Simulation and game verification are unaffected (presentation only).

## ADR-024

**One look: Blender's dark UI with a Minecraft soul**

- **Context:** "Make everything look like it belongs together … mainly a Minecraft vibe,
  but Blender's UI in mind … a dark theme."
- **Decision:** `redsim.ui.theme` owns the palette (charcoal panels, redstone-red accent,
  the game's gold), one app-wide stylesheet with the Fusion style and a dark palette, and
  the game's pixel font (drawn from the jar's font providers with the game's drop shadow).
  Overlays in the viewport (status, mode badge, hints, F3, signal labels) use the pixel
  font; panels use a clean sans font, like Blender. The inventory is custom painted as a
  hotbar with tab rows for the upper folder levels (growing upwards). Mode colors are
  shared by the toolbar buttons and the viewport badge. The camera glides (70 ms) for
  zoom, layer steps and focus.
- **Trade-offs:** Custom painting (inventory, timeline, overlays) needs its own tests
  (layout order, hit testing) instead of relying on Qt widgets.

## ADR-025

**Pixel-art icons instead of emoji and font glyphs**

- **Context:** After round 7 the owner asked to keep polishing the UI. Buttons mixed color
  emoji (🔒, 📈, 🔍, 🏹), unicode arrows from different fonts (⏮ rendered smaller than ◀)
  and plain text, so nothing lined up.
- **Decision:** `redsim.ui.pixel_icons` draws every button and menu icon from small ASCII
  art at 2× with the game's 1-pixel drop shadow (1× for menus, so they stay crisp; a dim
  variant for disabled actions). Derived icons are mirrored or transposed art (rotate back,
  flip front/back, right mouse). Mouse gestures in keycaps (hint bar, Hotkeys panel) use
  the same art, like Blender's status bar.
- **Trade-offs:** New icons are hand-drawn in code; a test keeps all art rectangular and
  the common canvas size.
- **Also:** where the game has a sprite for the exact thing (the hotbar, its selection
  frame, the clouds), the jar's sprite is used at runtime instead of pixel art, with a
  painted fallback without the jar (ADR-023: assets are never committed).

## ADR-026

**Power pulses: editor power locked to positions (sequences)**

**Date:** 2026-10-13 · **Status:** accepted · **Context:** the owner wants to test piston
sequences: power chosen positions at chosen ticks for chosen durations, locked to the
coordinates (the blocks there may move), set up like keyframes in Blender's animation mode.

**Decision:** a *power pulse* edit (`Action("power_pulse")`, payload strength and ticks)
gives a position editor power (`Level.forced_power`): every signal query asked *by* that
position (`Level.get_signal` with the receiver at the position) sees at least that
strength, from every side, like an invisible redstone block next to it on all sides.
It does not strongly power the block (a powered stone does not power dust next to it).
Switching on happens between ticks when the edit applies; switching off happens between
ticks too, at the start of the tick step after the duration (before `handling_tick` is
set). Both send one neighbor update to the block at the position (source: redstone
block). Pulses are recorded edits in the timeline's new "Powered" row; adding or changing
one re-runs the history from tick 0 with the plan (`Document.add_pulse`, `edit_pulse`),
so later edits stay. This is an editor tool, not a game mechanic; game comparisons do not
use it.

**Consequences:** sequences replay deterministically, survive saving (mid-pulse too) and
undo. The UI: an ANIMATE mode (K, or the Tab ring), a Sequence tab, red marks on powered
positions.

**Addendum to ADR-019 (2026-10-13):** strict clones (the editor's drags, pastes and
copies) keep a moving piston's movement: the moving_piston at the destination gets its
block entity back from the copied data. The game's `/clone` leaves a moving_piston without
a block entity (an invisible "block 36" that never finishes), which made dragged pistons
saved mid-movement disappear in the editor. Plain `/clone` commands (game comparisons)
keep the vanilla behavior.

**Addendum to ADR-026 (2026-10-13):** a 0-tick pulse (duration 0) is on *inside* one
tick: on at the next tick's start step (with `handling_tick` set), off in a step of its
own right after that tick's block events (`Level.zero_tick_pulses`, `zero_tick_ends`).
The first version switched on and off at one moment between ticks, where a piston's own
extension event cancels itself (`triggerEvent` with no signal), so 0-ticks did nothing
to pistons. Sequences are saved with the document now: a file with recorded edits keeps
the build (`extra["history"]["base"]`) and the plan, and opening re-runs them.

**Addendum to ADR-026 (2026-10-14):** pulses can be muted (`payload["muted"]`): the
engine applies the edit as a step with no effect, so muting keeps the timeline, the
undo history and the step numbering of everything else as it was.


## ADR-027

**A command line for agents and humans (`redsim-cli`), with the world file as its state**

**Date:** 2026-10-15 · **Status:** accepted · **Context:** the owner wants the simulator to
be "the bridge between Minecraft and AI agents": an agent (or a person in a terminal) must
be able to build, change and test contraptions step by step, inspect what happens
(signals, timing, causes) and leave the result as an ordinary world file that the editor
opens. Everything must be documented carefully, in one format for agents and humans.

**Decision:**

- **One program, one language.** `redsim-cli WORLD COMMAND ARGS…` runs one command;
  `redsim-cli WORLD -c "a; b"`, a script file (`script FILE`) or commands on standard input
  run several in one go; `redsim-cli WORLD shell` is an interactive prompt. The same
  commands, with the same words, are typed on the command line, written in scripts and
  stored in targets.
- **The world file is the state.** Every invocation opens the `.redsim.json` file (the
  editor's format), runs the commands and saves it back if something changed. Nothing
  else is needed to continue later. Labels, notes and targets are saved in the file too
  (the editor keeps them). A small undo file next to the world (`WORLD.undo.gz`) keeps the
  last versions so `undo` can revert earlier invocations.
- **Edits go to the build; the timeline is explicit.** Building commands (`place`, `set`,
  `fill`, …) change the build (tick 0) wherever the view is; `at T COMMAND` records the
  edit at tick T instead, and `pulse` adds sequence power. The view tick (`run`, `back`,
  `seek`, `step`) only says what inspection commands look at. This differs from the editor,
  where edits happen at the playhead: an agent that ran 20 ticks to look at a result and
  then fixes a wire must change the contraption, not record a timeline edit at tick 20.
- **Output is text first, readable by both.** Plain, stable, compact text (no colors, no
  boxes): one block per command, positions as `x y z`, block states as `/setblock`
  strings. `--json` prints one JSON object per command instead (`{"command", "ok",
  "data" | "error"}`) for programs. Maps (`show`) draw a layer as a grid of two-character
  codes with a legend; signal timelines (`waves`) as one hex digit per tick.
- **Labels and targets.** `label NAME POS` names a position (`@NAME` works wherever a
  position does). A *target* is an acceptance test for a contraption: stimuli at ticks
  (`do T COMMAND`) and expectations (`expect @OUT lit=true at 4..9`), or a truth table;
  `check` runs every target from the build in a copy and reports what passed and, for
  what failed, the values it saw. This is how an agent knows it is done.
- **Help is the documentation.** Every command's help (usage, description, examples) lives
  in its registry entry; `redsim-cli help` prints it and `doc/cli-reference.md` is
  generated from it (a test keeps them equal). The guide `doc/cli.md` explains the concepts
  and workflows for both readers.

**Also changed:** a world saved after running (without recorded edits) keeps its build:
the file stores the build, the simulated length and the view tick whenever the view is not
at tick 0 (before, the state at the playhead silently became the new build). Edits made
while re-runs are deferred (`Document.deferred`, used by the CLI to run many build edits
with one re-run) keep correct undo states.

**Consequences:** agents work through files and text, which suits shell tools and keeps
every step visible to a person; the same file opens in the editor with its labels and
targets. Each invocation re-simulates the recorded history when it opens the file, which
costs milliseconds for typical contraptions.

## ADR-028

**Opening worlds in a loading thread, behind a loading screen**

**Date:** 2026-10-17 · **Status:** accepted · **Context:** the owner: "loading worlds takes
a long time and the simulator does not respond during that time. Try to look into adding
a loading screen, showing how far it is with loading the world. Also think about ways to
increase the performance while loading since the builds may get even bigger." Measured
before: opening `seg7` (14 000 blocks) froze the window for 11 s: 10 s drawing the
Circuit panel's prefab preview (every face read its texture from the jar again), 1.2 s
of chunk meshes in the first frame, 0.03 s for the file itself.

**Decision:**

- **One loading thread per open** (`ui/loading.py`, the first thread in the code base).
  It runs only code without Qt widgets: `Document.open` (reading, recorded edits re-run),
  `ChunkedMesh.update` with a copy of the view's mesher, `icons.prefab_image` (QImage,
  which Qt allows off the GUI thread), `Atlas.for_blocks` for Minecraft worlds. It shares
  nothing it changes with the GUI: the document is new, the mesher a copy made on the
  GUI thread. When it is done, the GUI thread takes everything over at once
  (`MainWindow._finish_open`, `Viewport.set_document(document, prepared)`).
- **Progress through plain callbacks** (`core/progress.py`: `report(stage, done,
  total)`), passed down to `save_io.load`, `Document.open`, the history replay,
  `WorldStream.load` and `ChunkedMesh.update`; layers below the UI know nothing about the
  screen. The GUI polls the progress every 33 ms. Cancelling sets a flag; the next report
  raises `LoadCancelled` in the thread and the old world stays open.
- **The loading screen** looks like the game's (dirt, pixel font, a white bar) and covers
  the whole window; it swallows all input while shown (no shortcut can touch a document
  half-way), Esc cancels. One load at a time.
- **`open_path` stays synchronous** (tests, scripts); `load_path` and
  `open_minecraft_world` use the loading thread, and so does a world given on the command
  line (after the window is shown).
- **Faster loading:** prefab previews cache decoded and tinted textures, skip blocks hidden
  along the view diagonal, draw blocks only a few pixels wide as their colored boxes, and
  are cached by object (the panel asked for them after every edit, re-parsing every
  block); first mesh builds go through `_build_all` and the bulk `Mesher.cube_faces`;
  a new `Mesher` starts from a copy of the view's models and templates.

**Consequences:** `seg7` opens in 1.6 s and the window stays responsive (frames every
10 ms while it loads, a pause of up to ~100 ms when the preview is drawn); a 78 000-block
world (3.3 MB) opens in 1.3 s. Python threads share the GIL: the gain is responsiveness,
not parallel speed; for much bigger builds, meshing in worker processes and keeping
meshes between sessions are the next steps (owner's backlog, [[roadmap]]).

