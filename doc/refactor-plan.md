# Refactor, stability and performance pass (all-nighter, from 2026-10-13)

Owner request: "go back over the code and refactor it, look for bugs and make sure
everything's stable. Maybe find some things you can improve etc. Maybe some parts of the
game can be compiled down in order to get better performance." Keep the open list in
[[feedback-status]] in mind while doing it (nothing there is part of this pass).

Branch: `refactor/stability-pass`; verified steps are fast-forwarded to `main` and pushed
(both) after each item. **A scheduled nudge restarts the work after a usage-limit pause:
whoever picks this up reads this page, continues with the first unchecked item, and adds
a line to the log.**

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
2. [ ] **Engine hot paths (pure Python first):** profile, then trim per-call overhead in
   `Level.get_block_state`, signal queries, the neighbor updater, scheduled ticks and the
   trace (e.g. no keyword dicts per record when nobody reads them), keeping semantics.
3. [x] **Compile the hot core (optional speed-up):** try mypyc (ships with mypy) or
   Cython on `core/`, `sim/neighbor_updater.py`, `sim/level.py`, `sim/ticks.py`, with
   the pure-Python modules as the fallback when no compiler is available; measure;
   keep only if the gain is real and tests pass both ways. Document how to build.
4. [ ] **Bug hunt, engine and editor:** more fuzzing (new seeds against the game),
   property tests for save/load round trips, history rewrite and replay determinism,
   undo/redo with sequences, clone/move edge cases, streaming worlds.
5. [ ] **Bug hunt, UI:** every action on an empty document and on a busy one without a
   crash (an automated "click everything" smoke test), signal handlers that can raise,
   stale state after opening another document, timers after closing.
6. [ ] **Refactor the big UI modules:** `ui/viewport.py` (2 000 lines),
   `ui/main_window.py` (1 600), `ui/panels.py` (1 400), `ui/timeline.py` (1 300) into
   focused modules (overlays, input handling, picking; window actions per area; one
   module per panel; timeline lines vs. transport), without behavior changes.
7. [ ] **Refactor editor/document.py** (900 lines): history operations, sequences, world
   streaming and annotations in separate parts.
8. [ ] **Memory and large worlds:** copy-on-write block maps for keyframes, measure a
   streamed world at view distance 12 for an hour of ticks.
9. [ ] **Docs:** architecture and implementation notes updated to the new structure;
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

