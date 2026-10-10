# Roadmap

Status values: ☐ not started · ◐ in progress · ☑ done for current scope. The detailed current
state is in [[project-state]].

| # | Milestone | Status | Notes |
|---|---|---|---|
| 0 | Repository reconnaissance | ☑ | [[research/repository-report]], [[research/source-map]], [[architecture]], [[decisions]] |
| 1 | Source research and mechanics reference | ☑ | [[mechanics/index]], [[quirks]], [[research/open-questions]], [[research/wiki-hints]] |
| 2 | Minimal 3D editor and world model | ☑ | `python -m redsim`: viewport, place/break/use, inspector, sections, save/open, sim controls |
| 3 | Deterministic simulation foundation | ☑ | engine, neighbor updater, scheduled ticks, block events, block-entity tickers, trace, snapshots |
| 4 | Core redstone logic | ☑ | lever, buttons, lamp, torch (+ burnout), wire, repeater, comparator, cake; follow-up: barrel/container source |
| 5 | Pistons and timing-sensitive behavior | ◐ | core done and game-verified (EXP-015…020); open: scheduled-tick-driven 0-tick cases, observers |
| 6 | Playback, history, diagnostics | ☐ | engine snapshots exist |
| 7 | Contraptions and abstraction | ☐ | |
| — | In-game verification harness | ☑ | `tools/gameserver`, [[experiments/index]] (20/20 match) |

Order note: the world model was built before the editor because both the editor and the
engine depend on it ([[decisions]] ADR-007).

## Next steps

1. **Playback (M6):** rewind, event scrubbing with causal trace view, warp, save at
   intermediate points from the UI.
2. **Pistons follow-up:** scheduled-tick 0-tick scenarios, then observers.
3. **Contraptions (M7):** selection, copy/paste, reusable prefabs.
