# Open questions and distinguishing tests

Source reading resolved the update orders and timings for the in-scope paths. What remains
open are (a) things the source cannot settle alone, because they depend on runtime context
the decompile might misrepresent, and (b) places where a plausible-looking simplification
would give different results. Each entry names a test that tells the interpretations apart.

| ID | Question | Competing interpretations | Distinguishing test | Status |
|---|---|---|---|---|
| OQ-1 | Is wire update order really coordinate dependent in 26.3? | (a) Java `HashSet` order; (b) fixed direction order | Two identical lever→wire→2 pistons setups at coordinates with different hash layouts. The simulator predicts which piston gets its update first; check in game which one moves first when both are on BUD edges. | source: (a). In-game check pending |
| OQ-2 | Repeater priority when outputting into a side-locked repeater | (a) EXTREMELY_HIGH (`shouldPrioritize`); (b) uniform HIGH | Repeater A locks repeater B while repeater C feeds B's input; both ticks due in the same game tick. (a) locks B before it can turn on. | **resolved: (a)**, game EXP-010 |
| OQ-3 | Piston retraction event 2 window | (a) moving block progressO < 0.5, same tick, or `isHandlingTick`; (b) only progress | Sticky piston fed by pulses of length 1, 2, 3 game ticks from repeaters (scheduled-tick phase) and from a player lever (between ticks). Record whether the block is pulled back. | **between-tick inputs resolved: (a)**, EXP-016 (2-tick pulse still drops); scheduled-tick inputs pending |
| OQ-4 | Block-entity order of moving blocks pushed by two pistons in the same tick | (a) registration order (block-event order); (b) position order | Two pistons pushing into the same target region in one tick; check which block lands first via observers (later scope). | source: (a). Later |
| OQ-5 | Player action timing | (a) between ticks (before time increment); (b) inside a tick phase | Lever flipped while `/tick freeze`, then `/tick step 1`: a torch fed by the lever must change after exactly 2 steps under (a). | source: (a). In-game check pending |
| OQ-6 | Comparator reading through a block when the rear block emits ≥ 15 | (a) through-block lookup skipped at 15; (b) always replaced by the far container | Lever-powered block behind comparator with an empty barrel behind it: (a) output 15, (b) 0. | **resolved: (a)**, game EXP-013 (torch-powered stone, cake behind) |

## Decompilation sanity checks

- `SignalGetter.getDirectSignalTo` ends with `return result >= 15 ? result : result;`, a
  harmless decompiler artifact of the early-exit chain. Both branches return `result`.
- `NeighborUpdater.updateNeighborsAtExceptFromFacing` (interface default) passes a `null`
  orientation; the method is overridden by `CollectingNeighborUpdater`, which the level
  uses, so the default is not on the simulated path.
- No method relevant to the current scope looked incorrectly decompiled. Bytecode
  inspection (`javap -c` on `server-runtime.jar`) is the fallback if one does.

## Related

[[research/source-map]] · [[experiments/index]] · [[quirks]]
