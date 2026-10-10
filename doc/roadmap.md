# Roadmap

Status values: ☐ not started · ◐ in progress · ☑ done for current scope. The detailed current
state is in [[project-state]].

| # | Milestone | Status | Notes |
|---|---|---|---|
| 0 | Repository reconnaissance | ☑ | [[research/repository-report]], [[research/source-map]], [[architecture]], [[decisions]] |
| 1 | Source research and mechanics reference | ☑ | [[mechanics/index]], [[quirks]], [[research/open-questions]], [[research/wiki-hints]] |
| 2 | Minimal 3D editor and world model | ◐ | world model done (shared with M3); UI framework chosen and prototyped; editor not started |
| 3 | Deterministic simulation foundation | ☑ | engine, neighbor updater, scheduled ticks, block events, block-entity tickers, trace, snapshots |
| 4 | Core redstone logic | ◐ | done: lever, buttons, lamp, torch (+ burnout), wire; next: repeater, comparator |
| 5 | Pistons and timing-sensitive behavior | ☐ | researched ([[mechanics/pistons]]) |
| 6 | Playback, history, diagnostics | ☐ | engine snapshots exist |
| 7 | Contraptions and abstraction | ☐ | |
| — | In-game verification harness | ☑ | `tools/gameserver`, [[experiments/index]] (7/7 match) |

Order note: the world model was built before the editor because both the editor and the
engine depend on it ([[decisions]] ADR-007).

## Next steps

1. **Repeater** (delay, priorities, locking, pulse extension), then **comparator** (compare,
   subtract, side inputs, analog input via a container/cake provider). Each gets unit tests
   and game scenarios.
2. **Editor (M2):** PySide6 window, viewport, camera, picking, place/break/use, inspector,
   section colors, JSON save/load.
3. **Pistons (M5):** owner's first targets are a sliding piston and a simple door, then QC,
   BUD and 0-tick cases.
4. **Playback (M6):** run/pause, tick step, event step, warp, rewind on `Engine.snapshot()`.
