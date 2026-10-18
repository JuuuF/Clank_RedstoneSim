# Implementation notes

Practical notes for working on the code. Design rationale lives in [[decisions]], the
structure in [[architecture]], the current state in [[project-state]].

## Environment

- Conda environment `redsim` (owner-approved, 2026-10-11): `conda env create -f
  environment.yml`, then `python -m pip install -e . --no-deps`. Python 3.12 comes from conda-forge
  (avoiding the Anaconda defaults channel's terms prompt). numpy, PySide6 (pinned to the
  tested 6.9.2 wheel), pytest, ruff and mypy come from pip.
- The base Anaconda interpreter also works (same PySide6 wheel). Code must type-check with
  both mypy 1.19 (base) and 2.x (env).
- Java: the game needs Java 25 (`/usr/lib/jvm/java-25-openjdk`). It is used by the hash
  oracle test and the game server harness; `REDSIM_JDK_HOME` overrides the location.
- Under Wayland the UI sets `QT_QPA_PLATFORM=xcb` unless set (verified on the owner's
  desktop: XWayland, OpenGL 3.3), because this PySide6
  build cannot create an OpenGL context with the native Wayland plugin. Headless rendering
  works with `QT_QPA_PLATFORM=offscreen`.

## Everyday commands

```sh
python -m redsim                          # start the editor (PYTHONPATH=src if not installed)
python -m pytest                          # all tests (~2 s); pythonpath = src and repo root
ruff check src tests tools                # lint
ruff format src tests tools               # format (line length 100)
mypy src tools                            # types
python -m tools.gameserver.run            # all game comparisons (sandboxed 26.3 server)
python -m tools.gameserver.run and_gate   # selected scenarios
python -m tools.gameserver.run fuzz_61    # a new random circuit (seed 61) against the game
python -m tools.bench                     # speed numbers (compare before/after a change)
python -m tools.build_compiled            # optional compiled build (about 2× faster)
REDSIM_PURE=1 python -m pytest            # force plain Python when a build exists
python -m redsim.cli W.redsim.json info   # the command line (doc/cli.md, doc/cli-internals.md)
python -m redsim.cli help --markdown > doc/cli-reference.md   # after changing any command's help
```

Large modules are split into mixins (`viewport_*`, `window_*`, `timeline_lines`,
`document_history`, `document_sequences`): their methods start with
`view = cast("<Class>", self)` and use `view`, which keeps them fully type-checked
without mypy exceptions. Prefer adding new behavior to the matching mixin module.

`python -m tools.gameserver.run` needs `PYTHONPATH=src` unless the package is installed.

## Compiled build (optional, about 2× faster simulation)

`python -m tools.build_compiled` compiles the engine core and the block behaviors with
mypyc (ships with mypy; needs a C compiler) into `build/compiled/<fingerprint>/`, a copy
of `src/redsim` with compiled modules. `import redsim` puts that copy in front of the
sources **only if its fingerprint (a hash of every source file) matches**, so after any
edit the program runs as plain Python again until the next build; `REDSIM_PURE=1` forces
plain Python. `python -m tools.build_compiled --clean` removes all builds. Measured
2026-10-13 (`python -m tools.bench`): 168 pistons on observer clocks 27 → 48 ticks/s,
dust update storms 11.7 → 23 ticks/s.

Rules for code in compiled modules (`tools/build_compiled.MODULES`), checked by building:
- class-level settings that subclasses override are `ClassVar` (`properties`,
  `has_block_entity`, `type_id`, `SIZE`, …); constants in `UpdateFlags` are `Final`;
- classes that plain Python subclasses carry `@mypyc_attr(allow_interpreted_subclasses=
  True)` (`Block`, `SimpleBlock`, `BlockEntity`); no other class decorators (register
  block entities with a call after the class);
- attribute types are enforced at runtime (a double chest's slots are a `Slots`
  protocol, not a `list`); `copy.copy` does not work on compiled objects
  (`BlockEntity.clone` rebuilds them from `__mypyc_attrs__`);
- file paths come from `redsim.REPO_ROOT`, never from a module's `__file__` (a compiled
  build lives in another folder); positional-only parameters are not enforced (name
  them so they cannot clash with `**kwargs`).
- Not compiled: `sim/engine.py` (mypyc internal error), `core/direction.py` (its Enum
  crashes compiled code), `world/blocks/foreign.py`, editor, I/O, UI.
- Run the tests in both modes before committing engine changes: build, run the suite,
  then `REDSIM_PURE=1` and run it again.

## Conventions

- Source citations use paths relative to `data/minecraft_src/client-src/` plus class,
  method and decompile line, for example `CollectingNeighborUpdater.addAndRun` L68. The
  server tree is identical for shared classes.
- Python methods that port Java methods keep the Java name in snake_case and say so in the
  docstring. Control flow, iteration order and flags stay as in Java, even where a shortcut
  would look equivalent.
- `orientation` parameters (experimental redstone) are dropped; they are always null in
  default worlds.
- Never import Qt in `redsim.core`, `redsim.world`, `redsim.sim` or `redsim.io`.
- Engine code that needs Java's `state.is(Blocks.X)` uses ids from `redsim.world.ids`.
  Component modules import `redsim.world.blocks` lazily (inside functions) to avoid
  import cycles.
- Commits: small and verified, on feature branches (`feat/...`), with docs updated in the
  same slice ([[decisions]] ADR-012). Nothing is pushed without the owner's request.
- **Differences from the game are always written down** (owner, 2026-10-15: "an essential
  part of the project"). Wherever the code does not do exactly what the game does
  (randomness, items, water, approximated shapes, editor stand-ins), a comment or
  docstring there starts with `Not as in the game:` and says what the game does instead.
  The module docstring sums them up, the mechanics page has a section for them, and
  [[differences]] lists every one of them. `grep -rn "Not as in the game" src` must find
  each row of [[differences]].

## Checklist: adding a block

1. Research the class: hooks, properties (value order from `BlockStateProperties`),
   `Blocks.java` registration (collision, push reaction, conductor override, destroy speed).
2. Implement it in `src/redsim/world/blocks/<name>.py` as a line-by-line port with citations.
3. Register it in `blocks/__init__.py`; add an id to `ids.py` if engine code checks it.
4. Unit tests in `tests/sim/test_components.py` (or a new file) using `tests/sim/bench.py`.
5. Game scenario(s) in `tools/gameserver/scenarios.py`, run `python -m tools.gameserver.run
   <name>`, commit the JSON in `experiments/results/`, and log it in [[experiments/index]].
6. Update the mechanics page (Status, Tests), [[mechanics/index]], [[quirks]] and
   [[project-state]].
7. List everything that is not exactly the game's: mark it in the code (`Not as in the
   game:`), describe it on the mechanics page and add it to [[differences]]. Design the
   game scenario around it (for example a random outcome must not be compared).

## Checklist: adding a game scenario

- Positions are relative: y=1 is the first layer above the stone floor (absolute y=-60).
  Keep inside `size` (the floor footprint); the runner spaces scenarios 24 blocks apart.
- Build with `/setblock` strings (`minecraft:id[prop=value]`), not player placement.
  Remember that `/setblock redstone_wire` makes a dot unless a neighbor makes it connect.
- Inputs: `inputs[t]` is applied after `t` ticks, between ticks. Prefer redstone blocks
  placed and removed as inputs, since levers can't be pulled without a player.
- Region commands: `commands[t]` holds `("fill", a, b, state)` or `("clone", a, b, dest)`
  (relative positions), sent as `/fill`/`/clone` in game. Clone only regions without
  pending scheduled ticks (the simulator's paste does not copy ticks).
- Watch every block whose state matters; the comparison checks full states.
- A recording becomes stale when the scenario changes (fingerprint check): re-run the server.

## Game server harness details

- Sandbox: `.sandbox/gameserver/` (gitignored). The bundler extracts `libraries/` and
  `versions/` there on first start; `fresh_world=True` deletes only the sandbox world.
- Properties: offline, `server-ip=127.0.0.1`, port 25599, RCON/query/status/management
  off, peaceful, flat, `pause-when-empty-seconds=0`, `max-tick-time=-1`.
- Game rules at startup: `random_tick_speed 0`, `advance_time false`, `advance_weather
  false`, `spawn_mobs false`, `block_drops false` (no item entities: the simulator has none,
  and hoppers would collect them), then `tick freeze`. `prepare_area` also kills stray item
  entities.
- Synchronization: every command is followed by
  `scoreboard players set #sync redsim_sync <n>`; output lines are collected until that
  marker's feedback appears. Feedback lines arrive as `System chat: …`.
- Tick control: `tick freeze` once at startup; `tick step 1` and then poll
  `time query gametime` until it advances.
- State checks: `execute if block x y z <state>` gives "Test passed"/"Test failed".
- Block-entity data: `data get block x y z <path>` for comparator `OutputSignal`, a moving
  piston's `progress`, a hopper's `TransferCooldown` and `Items` (parsed to
  `slot:id*count …`, the same text as `ContainerBlockEntity.contents`); barrels' `Items`
  only in scenarios with `watch_items=True` (older recordings stay valid).

## Gotchas found so far

- `/setblock` is not player placement: no `getStateForPlacement`/`setPlacedBy`, flags
  2|256, then `updateNeighboursOnBlockSet` (the source block of those updates is the *new*
  block).
- In `setBlock`'s own neighbor updates, the source block is the *old* block
  (`updateNeighborsAt(pos, oldState.getBlock())`).
- `BlockStateProperties.FACING` lists N, E, S, W, U, D, which is not ordinal order. It
  matters for cycling.
- A wire's input ignores its connections; only its output checks them (via a live
  `getConnectionState`).

- Change blocks through `Level.set_block` (the game's pipeline) or `Level.add_blocks`
  (no updates, like chunk loading). Both record the position in `Level.touched`, which the
  viewport's chunked mesh reads; a direct `level.blocks[pos] = …` is only safe before a
  level is shown (building a fresh level, loading a file). The mesh then falls back to a
  full diff only if the block count changed.
- Blocks of a Minecraft world that stream in later must reach every stored level, not only
  the current one: `Document.add_world_blocks` adds them to the keyframes and the undo
  bases too, or a seek or undo would make them vanish.
- Only one game-server run at a time (they share the sandbox); its stdout is buffered to
  the end when redirected to a file.
- **No desktop (GTK) dialogs**: on GNOME, Qt's gtk3 theme runs GTK's file and color
  dialogs inside our GLib event loop, and GTK draws and lists folders at idle priority
  (120 and lower), below every Qt source. The view's ~60 frames per second (drifting
  clouds, a breathing selection, a running simulation) starve that work: measured
  2026-10-18 with a GLib idle probe at priority 120, up to 2.7 s waits in the idle editor
  and none at all in 4 s with the simulation playing behind the Save dialog (the owner
  waited up to 15 s for a folder change or a typed name). `theme.apply` therefore sets
  `AA_DontUseNativeDialogs`: Qt's own dialogs use Qt's event priorities and stay
  responsive (folders listed in 0.02–0.14 s while playing).

## Checking the UI visually

Screenshots of the real window (xcb, the GPU) are the reliable way to see a change: start
a `MainWindow` in a small script with `QT_QPA_PLATFORM=xcb`, `REDSIM_KEYMAP` and
`REDSIM_CONFIG_DIR` pointing at missing files (defaults, nothing saved), drive it with
`QTimer.singleShot` steps (set `viewport.camera`, call window methods or trigger
`window._actions[...]`), then save `window.grab()` with `viewport.grabFramebuffer()`
painted over the viewport's rectangle (the GL widget is black in a plain grab; screen
grabs are black under XWayland). Popups are separate windows: paint their `grab()` at
their position. Keyboard shortcuts do not fire while the test window is not the active
window; trigger the `QAction` instead.

## History and the trace

- Every edit goes through `Document` → `Timeline.apply`; never call `engine.apply` directly
  from UI code, or the history cannot replay it.
- `Timeline.seek` restores a keyframe and re-executes, so code that runs during steps must
  stay deterministic (no wall clock, no randomness, no iteration over unordered Python sets
  where order matters).
- Trace record ids are global (`Trace.base_id + index`); use `Trace.get`/`Trace.after`
  instead of indexing `records` with an id.
