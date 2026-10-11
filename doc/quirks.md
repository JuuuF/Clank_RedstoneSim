# Quirk and source-reference index

One searchable list of non-obvious behaviors. IDs are stable; mechanic pages link here.
Evidence: **S** = verified by reading the 26.3 source; **T** = covered by a simulator test;
**G** = confirmed in the real game ([[experiments/index]]).

## Engine: updates and scheduling

| ID | Quirk | Evidence | Source / test |
|---|---|---|---|
| Q-UPD-ORDER | Neighbor updates go W, E, D, U, N, S; shape updates go W, E, N, S, D, U. | S T | `NeighborUpdater.UPDATE_ORDER`, `BlockBehaviour.UPDATE_SHAPE_ORDER`; `test_update_order_is_w_e_d_u_n_s`, `test_flags_3_neighbor_updates_then_shape_updates` |
| Q-UPD-DFS | Updates emitted by a handler run after it returns, depth-first, before the handler's remaining siblings. | S T | `CollectingNeighborUpdater.addAndRun`/`runUpdates`; `test_handler_finishes_before_emitted_updates` |
| Q-UPD-ONPLACE | `onPlace` runs on every state change (unless flag 512), not only on placement. | S T | `LevelChunk.setBlockState`; `test_on_place_runs_for_property_changes_without_removal` |
| Q-UPD-SHAPE-NOUPD | State changes caused by shape updates emit no neighbor updates (flag 1 cleared). | S T | `Level.setBlock` (`updateFlags & -34`), `Block.updateOrDestroy`; `test_shape_change_from_shape_update_sends_no_neighbor_updates` |
| Q-UPD-OLDSOURCE | `setBlock`'s neighbor updates name the *old* block as their source; `/setblock`'s follow-up updates name the *new* block. | S | `Level.setBlock` L245, `ServerLevel.updateNeighboursOnBlockSet` |
| Q-SCHED-COLLECT | Scheduled ticks are collected once per tick before any run; ticks scheduled during the phase wait for the next tick. | S T | `LevelTicks.tick`; `test_ticks_scheduled_during_the_phase_wait_for_next_tick` |
| Q-SCHED-DEDUP | A tick request for a (pos, block) that is still pending is dropped, including its delay and priority. | S T G | `LevelChunkTicks.schedule`; `test_duplicate_request_is_dropped_but_consumes_a_sub_tick`; EXP-005 |
| Q-SCHED-SUBTICK | The sub-tick counter advances on every request, even rejected ones. | S T | `LevelAccessor.createTick` |
| Q-SCHED-OVERDUE | Overdue ticks (from an overflowing earlier tick) merge across chunks by priority only. Not reproduced: cannot arise in scope. | S | `LevelTicks.drainContainers` |
| Q-BE-ORDER | Block entities tick in level-wide registration order; a replaced entity keeps its wrapper's place in the list. | S | `LevelChunk.updateBlockEntityTicker` |
| Q-EVT-SAMETICK | Block events queued during the block-event phase run in the same phase; identical queued events are merged. | S T | `ServerLevel.runBlockEvents`; `test_block_events_fifo_dedup_and_same_phase_cascade` |
| Q-SETBLOCK-DOT | `/setblock redstone_wire` with nothing to connect to creates a dot; it reshapes when neighbors change. | S G | `BlockInput.place` + `updateFromNeighbourShapes`; EXP-002 tick 0 |

## Blocks and power

| ID | Quirk | Evidence | Source / test |
|---|---|---|---|
| Q-PROP-GLASS | Glass and glowstone carry components but are not conductors. | S T G | `Blocks.GLASS`/`GLOWSTONE`; EXP-007 |
| Q-PROP-REDBLOCK | The redstone block is a signal source but not a conductor. | S | `Blocks.REDSTONE_BLOCK`, `PoweredBlock` |
| Q-POW-TORCH-SIDE | Torches, levers and buttons beside a comparator are not side inputs (only direct signal counts). | S G | `SignalGetter.getControlInputSignal`; EXP-014 (torch) |
| Q-POW-WIRE-SIDE | Any wire beside a comparator is a side input at full POWER, regardless of its shape. | S G | `SignalGetter.getControlInputSignal` |
| Q-WIRE-HASH | Wire power changes update positions in `HashSet<BlockPos>` order (coordinate dependent). | S T | `DefaultRedstoneWireEvaluator.updatePowerStrength`; `test_wire_update_burst_follows_java_hashset_order` (+ JDK oracle) |
| Q-WIRE-INSTANT | Wire never schedules ticks; it settles within one update cascade. | S G | `RedstoneWireBlock.neighborChanged`; EXP-003 |
| Q-WIRE-REDUNDANT | A depowering wire line passes through intermediate power levels, each firing a full update burst. | S | `RedstoneWireEvaluator.getIncomingWireSignal` |
| Q-WIRE-GLASS-UP | Signals climb onto glass/glowstone but never descend from them (one-way staircase). | S T G | `RedstoneWireEvaluator.getIncomingWireSignal`; `test_glass_lets_power_climb_but_not_descend`; EXP-007 |
| Q-WIRE-INPUT-ANY | A wire's input ignores its connections (a dot still receives); only its output checks them. | S T G | `getIncomingWireSignal`, `RedstoneWireBlock.getSignal`; `test_dot_powers_only_the_block_below`; EXP-005 |
| Q-WIRE-WEAK | Dust-powered blocks activate components but never power other dust (the `shouldSignal` mute). | S T | `RedstoneWireBlock.getBlockSignal`; `test_wire_powered_block_does_not_power_other_wire` |
| Q-REP-PRIORITY | Repeater ticks: −3 if outputting into a diode not facing back, −2 when turning off, −1 when turning on. | S T G | `DiodeBlock.checkTickOnNeighbor`, `shouldPrioritize`; `test_repeater_priorities_by_situation`; EXP-010 |
| Q-REP-PULSE-EXTEND | Pulses shorter than the delay are extended to the delay. | S G | `DiodeBlock.tick`; EXP-009 |
| Q-REP-PLACE-DELAY1 | A repeater placed with input powers on after 1 tick (NORMAL), not after its delay. | S T | `DiodeBlock.setPlacedBy`; `test_placed_repeater_with_input_turns_on_after_one_tick` |
| Q-REP-LOCKED-STALE | The `LOCKED` property is display state; ticking uses the live side input. | S G (LOCKED updates, EXP-010) | `DiodeBlock.tick`, `RepeaterBlock.isLocked`/`updateShape` |
| Q-COMP-DOUBLE-FRONT | A comparator changing POWERED updates its front twice. | S T | `ComparatorBlock.refreshOutputState`, `DiodeBlock.onPlace`; `test_comparator_power_change_updates_front_twice` |
| Q-COMP-COMPARE-UPDATES | In compare mode every comparator tick updates the front, even without change. | S | `ComparatorBlock.refreshOutputState` |
| Q-COMP-THROUGH-15 | A comparator reads an analog block through a conductor only if the conductor's own signal is below 15. | S G | `ComparatorBlock.getInputSignal`; EXP-013 |
| Q-COMP-SETBLOCK-MODE | Changing a comparator's mode with `/setblock` does not re-evaluate it; only input changes or clicks do. | S G | `SetBlockCommand`, `DiodeBlock.onPlace`; EXP-012 |
| Q-COMP-OUTPUT-NO-STATE | Output strength lives in the block entity; strength-only changes cause no shape updates. | S | `ComparatorBlock.refreshOutputState` |
| Q-TORCH-STRONG-UP | Torches strongly power the block above them. | S T G | `RedstoneTorchBlock.getDirectSignal`; EXP-005 |
| Q-TORCH-BURNOUT-DET | Torch burnout is deterministic (8 turn-offs within 60 ticks, 160-tick re-check). | S T G | `RedstoneTorchBlock.tick`, `isToggledTooFrequently`; EXP-005 |
| Q-TORCH-BURNOUT-STUCK | A burnt-out torch whose own cascade re-schedules it loses the 160-tick restart (dedup) and stays out until a later update. | S G | EXP-005, EXP-006 |
| Q-LEVER-DOUBLE | A lever toggle updates its own neighbors twice. | S T | `LeverBlock.pull`; `test_lever_toggle_updates_its_own_neighbors_twice` |
| Q-HOPPER-ITEM-REPLACE | `/item replace` into a hopper does not update comparators (the hopper's `setItem` has no `setChanged`); moving items does. | S T G | `HopperBlockEntity.setItem`; `test_comparator_reads_a_hopper_but_item_replace_does_not_update_it`; EXP-041 |
| Q-HOPPER-COOLDOWN-7 | An empty hopper that receives an item from a hopper that ticked no later than itself in this game tick waits 7 ticks instead of 8, so chains move one item per 8 ticks in either ticker order. | S T G | `HopperBlockEntity.tryMoveInItem`; `test_chained_hoppers_move_one_item_per_8_ticks_in_either_ticker_order`; EXP-038, EXP-040 |
| Q-HOPPER-LOCK-COOLDOWN | A locked hopper's cooldown still counts down (to 0), so it moves on the first tick after unlocking. | S T G | `HopperBlockEntity.pushItemsTick`; EXP-039 |
| Q-LAMP-ASYM | Lamps turn on instantly and off after 4 ticks; toggles send no neighbor updates. | S T G | `RedstoneLampBlock.neighborChanged`; EXP-001 |

## Pistons

| ID | Quirk | Evidence | Source |
|---|---|---|---|
| Q-PISTON-QC | Pistons also check power around the block above them. | S G | `PistonBaseBlock.getNeighborSignal`; EXP-017, EXP-018 |
| Q-PISTON-BUD | Pistons only re-check power on updates, so they can stay in a stale state. | S G | `PistonBaseBlock.neighborChanged`; EXP-017 |
| Q-PISTON-SPIT | A sticky piston retracting before its push completes leaves the block behind; for between-tick inputs even after a 2-tick pulse. | S G | `PistonBaseBlock.checkIfExtend`/`triggerEvent` (event 2); EXP-016 |
| Q-PISTON-SLIME-FLOOR | Slime resting on pushable blocks drags them (often past the 12-block limit). | S T | `PistonStructureResolver.addBranchingBlocks`; `test_slime_on_the_floor_grabs_the_floor` |
| Q-PISTON-POP-ON-MOVE | Dust on a block that starts moving pops at once: the `moving_piston` has no support until its block entity exists. | S G | `PistonBaseBlock.moveBlocks` (flags 324 shape updates before `setBlockEntity`); EXP-020 |
| Q-PISTON-EVENT-RECHECK | Power is re-checked when the block event runs. | S | `PistonBaseBlock.triggerEvent` |
| Q-PISTON-HASHMAP | Air placement order after a push follows `HashMap<BlockPos>` order. | S | `PistonBaseBlock.moveBlocks` |
