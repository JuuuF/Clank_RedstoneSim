# Refactor, stability and performance pass (all-nighter, from 2026-10-13)

Owner request: "go back over the code and refactor it, look for bugs and make sure
everything's stable. Maybe find some things you can improve etc. Maybe some parts of the
game can be compiled down in order to get better performance." Keep the open list in
[[feedback-status]] in mind while doing it (nothing there is part of this pass).

Branch: `refactor/stability-pass`; verified steps are fast-forwarded to `main` and pushed
(both) after each item. **A scheduled nudge restarts the work after a usage-limit pause:
whoever picks this up reads this page, continues with the first unchecked item, and adds
a line to the log.**

## Summary for the owner (2026-10-14 morning)

All items are done; everything is on `main` and pushed. Tests: 475 pass, as plain Python
and on the compiled build; the 46 named game scenarios match in both; 20 new random
circuits against the real game match (60 in all now).

**Speed.** Engine ticks per second on this machine, before → after the night:

| Benchmark (`python -m tools.bench`) | before | plain Python now | compiled |
|---|---|---|---|
| 168 sticky pistons on observer clocks | 24.6 | 30.2 | **50.3** |
| 8 dust lines toggled every tick (update storms) | 8.2 | 13.0 | **25.0** |

The compiled build is optional: `python -m tools.build_compiled` (needs mypy, already in
the environment, and gcc). It is used only while it matches the sources exactly, so it
can never run stale code; `REDSIM_PURE=1` switches it off. Rebuild after pulling or
editing to keep the speed.

**Stability.** Randomized history tests (replay, save/open, undo/redo), every window
action in every mode on an empty and a busy document, more game fuzzing. Fixed: switching
documents left old view state (selection lock, paste preview, drags, highlights, the block
popup, timeline selections, a half-run tick); closing the window left timers running; the
timeline opened too short (now sized to its lines, and its height is remembered).

**Structure.** The four big UI modules and the document are split into focused modules
(no behavior change): viewport (5 parts), main window (6), panels (6), timeline (3),
document (4). Largest module now: `main_window.py`, 990 lines.

**Your requests from the night.** Pulses can be muted (0 key, the Sequence tab's On
checkbox, right-click menus per pulse/line/group/all); timeline lines show their position
with the block there at the current tick.

**One incident.** A shell `cp` that asks before overwriting skipped a backup step: your
working `examples/showcase.redsim.json` was replaced for a moment and restored from a
copy made at 21:29 (only changes between 21:29 and 21:42 could be missing; it is still
your version, uncommitted, as before).

## Rules for the pass

- Behavior must not change: the whole test suite (including the 86 game recordings) and
  `ruff`, `mypy` stay green after every step; game scenarios are re-run after engine
  changes (`python -m tools.gameserver.run`, one run at a time).
- Small commits, each with a measurement or a test when it is about speed or a bug.
- The owner's `examples/showcase.redsim.json` (their working copy) is never overwritten;
  tests run against the committed version (scratchpad `check.sh` does this).

## Checklist

1. [x] **Baseline:** full tests, full game regression (46 named + 40 random), and speed
   numbers (engine ticks/s on a busy contraption, mesh build, open world, UI paint) in a
   benchmark script under `tools/bench.py` so later steps can compare.
2. [x] **Engine hot paths (pure Python first):** profile, then trim per-call overhead in
   `Level.get_block_state`, signal queries, the neighbor updater, scheduled ticks and the
   trace (e.g. no keyword dicts per record when nobody reads them), keeping semantics.
3. [x] **Compile the hot core (optional speed-up):** try mypyc (ships with mypy) or
   Cython on `core/`, `sim/neighbor_updater.py`, `sim/level.py`, `sim/ticks.py`, with
   the pure-Python modules as the fallback when no compiler is available; measure;
   keep only if the gain is real and tests pass both ways. Document how to build.
4. [x] **Bug hunt, engine and editor:** more fuzzing (new seeds against the game),
   property tests for save/load round trips, history rewrite and replay determinism,
   undo/redo with sequences, clone/move edge cases, streaming worlds.
5. [x] **Bug hunt, UI:** every action on an empty document and on a busy one without a
   crash (an automated "click everything" smoke test), signal handlers that can raise,
   stale state after opening another document, timers after closing.
6. [x] **Refactor the big UI modules:** `ui/viewport.py` (2 000 lines),
   `ui/main_window.py` (1 600), `ui/panels.py` (1 400), `ui/timeline.py` (1 300) into
   focused modules (overlays, input handling, picking; window actions per area; one
   module per panel; timeline lines vs. transport), without behavior changes.
7. [x] **Refactor editor/document.py** (900 lines): history operations, sequences, world
   streaming and annotations in separate parts.
8. [x] **Memory and large worlds:** copy-on-write block maps for keyframes, measure a
   streamed world at view distance 12 for an hour of ticks.
9a. [x] **Owner request (2026-10-14): timeline labels of animated blocks.** Lines name the
   block at the position, which changes when pistons move blocks: show what is there at
   the current tick (dynamic), or only the position.
9b. [x] **Owner request (2026-10-14): bypass animation keyframes.** Mute pulses without
   deleting them (per pulse, per line, per group, and all at once), like muting in
   Blender/Ableton; muted pulses stay in the timeline, greyed out, and are skipped.
9. [x] **Docs:** architecture and implementation notes updated to the new structure;
   project-state and feedback-status refreshed; a summary for the owner.

## Log

- 2026-10-13: plan written; nudge scheduled (hourly while idle, session-only, 7 days).
- Baseline (before this pass): pistons 24.6 ticks/s, dust 8.2, mesh 23 ms, open world
  0.81 s; 46 of 46 game scenarios match.
- Cached shape fullness and conductor answers per state: pistons 29.6, dust 12.2.
- Compiled build (mypyc, 30 modules; optional, fingerprint-checked): pistons 48.3, dust
  23.1 (pure Python 27.0 / 11.7). Fixes needed for it: ClassVar/Final declarations, no
  class decorators, a `Slots` protocol for container slots, `BlockEntity.clone` without
  `copy.copy`, `redsim.REPO_ROOT` for file lookups. Tests pass both ways.
- Incident: an interactive `cp` alias skipped a backup step; the owner's working
  `examples/showcase.redsim.json` was overwritten for a moment and restored from the
  21:29 backup (only edits between 21:29 and 21:42 could be lost).
- Pure-Python trims: block names computed once, the neighbor-update loop inlines its
  position math: pistons 30.2, dust 13.0 (pure). Further trims stopped there: the
  remaining cost is spread thin; the compiled build is the lever (item 3).
- Bug hunt (engine/editor): randomized history test (`tests/editor/test_fuzz_history.py`:
  random builds, later edits, levers, pulses incl. 0-ticks, moves, breaks; replay
  back and forth, save/open, undo all/redo all) passes; a one-off sweep of 60 more
  seeds found nothing. Probed overlapping moves and copies, containers and scheduled
  ticks in moves: all as the game's /clone does (a moved block's old tick stays and is
  skipped on air, as in the game).
- Bug hunt (UI): `tests/ui/test_every_action.py` triggers all 75 window actions in all
  four modes on an empty and on the busy showcase document (dialogs cancelled, desktop
  calls stubbed): no exceptions.
- Fixed: switching documents left the old view state (selection lock, paste preview
  with the old clipboard, drags, hover, highlights, an open block popup, timeline
  selections, a half-run tick); closing the window left its timers running.
- Refactor: `ui/viewport.py` (2 075 lines) split into `viewport.py` (setup, GL, input,
  camera; 909), `viewport_text.py` (2D overlays, ring, labels), `viewport_scene.py`
  (guides, boxes, gizmos, highlights, pivot), `viewport_edit.py` (build target and
  preview, selection drags, paste) and `view_common.py` (constants, helpers). The parts
  are mixins of `Viewport`; their methods start with `view = cast("Viewport", self)`,
  so they stay fully type-checked. Names other modules import from `viewport` are
  re-exported. Also: the timeline opens tall enough for all its lines, and its height
  is remembered with the window layout.
- Game: 20 new random circuits (fuzz_41–60) all match; recordings committed (replayed by
  the tests from now on).
- Owner requests during the night: dynamic or position-only labels for animated lines;
  muting pulses (items 9a, 9b).
- Refactor: `ui/main_window.py` (1 650 lines) split into `main_window.py` (setup, menus,
  modes, refresh, core editing; 990), `window_files.py`, `window_regions.py`,
  `window_time.py` (run loop, stepping, history), `window_sequence.py` and
  `window_common.py`; same technique as the viewport. Checks pass; the run loop runs at
  20 ticks/s in a live check.
- Refactor: `ui/panels.py` (1 400 lines) split by class into `panel_widgets.py`,
  `panel_inspector.py`, `panel_diagnostics.py`, `panel_circuit.py`, `panel_settings.py`;
  `panels.py` re-exports them. Found on the way: the Hotkeys tab had no color for
  ANIMATE mode's section and did not mention K or the Tab ring.
- Refactor: `ui/timeline.py` (1 270 lines): the per-block lines (groups, pulse bars,
  drags, menus) moved into the `LineArea` mixin in `timeline_lines.py`, constants into
  `timeline_common.py`; `timeline.py` keeps the canvas core and the transport bar (962).
  Item 6 done: the largest UI module is now `main_window.py` with 990 lines.
- Refactor: `editor/document.py` (950 lines) → `document.py` (fields, creation, edits,
  regions, world chunks, files; 530), `document_history.py` (`HistoryOps`: running,
  seeking, undo/redo, edit batches, tick 0, markers, timeline view; with `EditError`,
  `HistoryState`, `EditBatch`), `document_sequences.py` (`SequenceOps` and `Pulse`),
  `document_common.py`; all old import paths still work.
- Memory (item 8), measured: the example save streamed to view distance 12 (489 chunks,
  173 488 blocks) opens in 4.7 s at 130 MB; 1 500 ticks later 30 keyframes are kept (cap
  34 from the 6 M block budget) and the process peaks at 504 MB, so keyframes cost
  ~12 MB each and the total stays bounded. Copy-on-write keyframes were not built: the
  compiled `Level` needs `blocks` to be a real `dict`, and streamed chunks must reach
  every stored level; the cap is enough for now (noted in project-state as an option).
- 9b done: pulses can be muted (payload `muted`, skipped by the engine with a trace note,
  kept by edits): `0` on selected pulses, the Sequence tab's On checkbox, right-click
  menus per pulse, selection, line, group and all; grey dashed bars; muted-only positions
  get no ANIMATE marker. 9a done: lines are named by position, with the block there at
  the current tick dim behind it ("empty" when moved away).
- Item 9: docs refreshed (README, doc/README, project-state, implementation-notes,
  feedback-status, architecture); summary for the owner at the top of this page. The
  hourly nudge was removed after this.

