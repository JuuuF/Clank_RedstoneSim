# Quirk and source-reference index

One searchable list of non-obvious behaviors. IDs are stable; mechanic pages link here.
Evidence: **S** = verified by reading the 26.3 source; **T** = covered by a simulator test;
**G** = confirmed in game (see [[experiments/index]]).

| ID | Quirk | Evidence | Source |
|---|---|---|---|
| Q-UPD-ORDER | Neighbor updates go W, E, D, U, N, S; shape updates go W, E, N, S, D, U. | S | `NeighborUpdater.UPDATE_ORDER`, `BlockBehaviour.UPDATE_SHAPE_ORDER` |
| Q-UPD-DFS | Updates emitted by a handler run after it returns, depth-first, before the handler's remaining siblings. | S | `CollectingNeighborUpdater.addAndRun`/`runUpdates` |
| Q-UPD-ONPLACE | `onPlace` runs on every state change (unless flag 512), not only on placement. | S | `LevelChunk.setBlockState` |
| Q-UPD-SHAPE-NOUPD | State changes caused by shape updates emit no neighbor updates (flag 1 cleared). | S | `Level.setBlock` (`updateFlags & -34`), `Block.updateOrDestroy` |
| Q-SCHED-COLLECT | Scheduled ticks are collected once per tick before any run; ticks scheduled during the phase wait for the next tick. | S | `LevelTicks.tick` |
| Q-SCHED-DEDUP | A tick request for a (pos, block) that is still pending is dropped, including its priority. | S | `LevelChunkTicks.schedule` |
| Q-SCHED-SUBTICK | The sub-tick counter advances on every request, even rejected ones. | S | `LevelAccessor.createTick` |
| Q-SCHED-OVERDUE | Overdue ticks (from an overflowing or non-ticking earlier tick) merge across chunks by priority only. Not reproduced: cannot arise in scope. | S | `LevelTicks.drainContainers` |
| Q-BE-ORDER | Block entities tick in level-wide registration order; a replaced entity keeps its wrapper's place in the list. | S | `LevelChunk.updateBlockEntityTicker` |
| Q-EVT-SAMETICK | Block events queued during the block-event phase run in the same phase. Identical queued events are merged. | S | `ServerLevel.runBlockEvents` |

Mechanic-specific quirks are added by the mechanic pages as they are written.
