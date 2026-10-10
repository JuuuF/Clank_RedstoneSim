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
| 6 | Playback, history, diagnostics | ☑ | timeline rewind/replay, step/tick back, slider, warp, diagnostics panel; polish open (trace tree) |
| 7 | Contraptions and abstraction | ☑ | selection, /clone paste, rotation, /fill delete, prefab library, groups with ports; abstract models deferred (ADR-016) |
| — | In-game verification harness | ☑ | `tools/gameserver`, [[experiments/index]] (22/22 match) |

Order note: the world model was built before the editor because both the editor and the
engine depend on it ([[decisions]] ADR-007).

## Next steps (after owner feedback, see [[ui-direction]])

0. ☑ **Real-time speed:** chunked, dirty-tracked meshes; simulation decoupled from
   rendering; ticks/s display (ADR-017).
0. **Interaction redesign:** vim-like modes, orbit camera around a visible pivot, Axiom-like
   selections, hot-swappable analog source block.

1. Owner review of the editor on the real desktop.
2. Diagnostics polish (causal trace tree, "why did this change?").
3. More mechanics: piston 0-tick from scheduled ticks, observers, containers, target block.
