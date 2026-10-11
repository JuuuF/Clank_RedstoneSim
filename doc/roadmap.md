# Roadmap

Status values: ☐ not started · ◐ in progress · ☑ done for current scope. The detailed current
state is in [[project-state]].

| # | Milestone | Status | Notes |
|---|---|---|---|
| 0 | Repository reconnaissance | ☑ | [[research/repository-report]], [[research/source-map]], [[architecture]], [[decisions]] |
| 1 | Source research and mechanics reference | ☑ | [[mechanics/index]], [[quirks]], [[research/open-questions]], [[research/wiki-hints]] |
| 2 | Minimal 3D editor and world model | ☑ | `python -m redsim`: viewport, place/break/use, inspector, sections, save/open, sim controls |
| 3 | Deterministic simulation foundation | ☑ | engine, neighbor updater, scheduled ticks, block events, block-entity tickers, trace, snapshots |
| 4 | Core redstone logic | ☑ | lever, buttons, lamp, torch (+ burnout), wire, repeater, comparator, cake, barrel, lectern |
| 5 | Pistons and timing-sensitive behavior | ◐ | core done and game-verified (EXP-015…020); open: scheduled-tick-driven 0-tick cases, observers |
| 6 | Playback, history, diagnostics | ☑ | timeline rewind/replay, step/tick back, slider, warp, diagnostics panel; polish open (trace tree) |
| 7 | Contraptions and abstraction | ☑ | selection, /clone paste, rotation, /fill delete, prefab library, groups with ports; abstract models deferred (ADR-016) |
| — | In-game verification harness | ☑ | `tools/gameserver`, [[experiments/index]] (26/26 match) |

Order note: the world model was built before the editor because both the editor and the
engine depend on it ([[decisions]] ADR-007).

## Next steps (after owner feedback, see [[ui-direction]])

0. ☑ **Real-time speed:** chunked, dirty-tracked meshes; simulation decoupled from
   rendering; ticks/s display (ADR-017).
0. ☑ **Interaction redesign, part 1:** vim-like modes, orbit camera around a visible pivot,
   rebindable keymap (ADR-018, [[controls]]).
0. ☑ **Interaction redesign, part 2:** Axiom-like selections: handles, drag to move/copy
   (`/clone … move|force`, ADR-019), paste preview.
0. ☑ **Signal sources:** barrel and lectern (game-verified EXP-024/025), one hot-swappable
   source in the UI (ADR-020).
0. ☑ **Second feedback round:** update-free editor cloning (EXP-026), selection looks,
   Trackmania paste, build preview, X-ray, info overlay, inspector controls, rotate/flip/
   stack (ADR-021), hotkeys panel.
0. **Next:** observers, hoppers, target blocks; the "technical Minecraft" look.

1. Owner review of the editor on the real desktop.
2. Diagnostics polish (causal trace tree, "why did this change?").
3. More mechanics: piston 0-tick from scheduled ticks, observers, containers, target block.
