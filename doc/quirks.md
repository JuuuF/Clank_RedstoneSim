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
| Q-PROP-GLASS | Glass and glowstone carry components but are not conductors. | S | `Blocks.GLASS`/`GLOWSTONE` (`isRedstoneConductor(never)`) |
| Q-PROP-REDBLOCK | The redstone block is a signal source but not a conductor. | S | `Blocks.REDSTONE_BLOCK`, `PoweredBlock` |
| Q-POW-TORCH-SIDE | Torches, levers and buttons beside a comparator are not side inputs (only direct signal counts). | S | `SignalGetter.getControlInputSignal`, `RedstoneTorchBlock.getDirectSignal` |
| Q-POW-WIRE-SIDE | Any wire beside a comparator is a side input at full POWER, regardless of its shape. | S | `SignalGetter.getControlInputSignal` |
| Q-WIRE-HASH | Wire power changes update positions in `HashSet<BlockPos>` order (coordinate dependent). | S | `DefaultRedstoneWireEvaluator.updatePowerStrength` |
| Q-WIRE-INSTANT | Wire never schedules ticks; it settles within one update cascade. | S | `RedstoneWireBlock.neighborChanged` |
| Q-WIRE-REDUNDANT | A depowering wire line passes through intermediate power levels, each firing a full update burst. | S | `DefaultRedstoneWireEvaluator`, `RedstoneWireEvaluator.getIncomingWireSignal` |
| Q-REP-PRIORITY | Repeater ticks: −3 if outputting into a diode not facing back, −2 when turning off, −1 when turning on. | S | `DiodeBlock.checkTickOnNeighbor`, `shouldPrioritize` |
| Q-REP-PULSE-EXTEND | Pulses shorter than the delay are extended to the delay. | S | `DiodeBlock.tick` |
| Q-REP-PLACE-DELAY1 | A repeater placed with input powers on after 1 tick (NORMAL), not after its delay. | S | `DiodeBlock.setPlacedBy` |
| Q-REP-LOCKED-STALE | The `LOCKED` property is display state; ticking uses the live side input. | S | `DiodeBlock.tick`, `RepeaterBlock.isLocked`/`updateShape` |
| Q-COMP-DOUBLE-FRONT | A comparator changing POWERED updates its front twice. | S | `ComparatorBlock.refreshOutputState`, `DiodeBlock.onPlace` |
| Q-COMP-COMPARE-UPDATES | In compare mode every comparator tick updates the front, even without change. | S | `ComparatorBlock.refreshOutputState` |
| Q-COMP-OUTPUT-NO-STATE | Output strength lives in the block entity; strength-only changes cause no shape updates. | S | `ComparatorBlock.refreshOutputState` |
| Q-TORCH-STRONG-UP | Torches strongly power the block above them. | S | `RedstoneTorchBlock.getDirectSignal` |
| Q-TORCH-BURNOUT-DET | Torch burnout is deterministic (8 toggles in 60 ticks). Out of initial scope. | S | `RedstoneTorchBlock.tick`, `isToggledTooFrequently` |
| Q-LEVER-DOUBLE | A lever toggle updates its own neighbors twice. | S | `LeverBlock.pull` |
| Q-LAMP-ASYM | Lamps turn on instantly and off after 4 ticks; toggles send no neighbor updates. | S | `RedstoneLampBlock.neighborChanged` |
| Q-PISTON-QC | Pistons also check power around the block above them. | S | `PistonBaseBlock.getNeighborSignal` |
| Q-PISTON-BUD | Pistons only re-check power on updates, so they can stay in a stale state. | S | `PistonBaseBlock.neighborChanged` |
| Q-PISTON-SPIT | A sticky piston retracting before its push completes leaves the block behind. | S | `PistonBaseBlock.checkIfExtend`/`triggerEvent` (event 2) |
| Q-PISTON-EVENT-RECHECK | Power is re-checked when the block event runs. | S | `PistonBaseBlock.triggerEvent` |
| Q-PISTON-HASHMAP | Air placement order after a push follows `HashMap<BlockPos>` order. | S | `PistonBaseBlock.moveBlocks` |
