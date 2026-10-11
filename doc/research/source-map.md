# Source map: where Java Edition 26.3 implements the simulated mechanics

All paths are relative to `data/minecraft_src/client-src/` (identical in `server-src/`, see
[[repository-report]]). `L123` is the line number in this decompile. Line numbers belong to
this decompiled copy and serve only to locate code; they are not part of the game.

## Tick loop and phases

| Concern | Location | Notes |
|---|---|---|
| Server tick order | `net/minecraft/server/MinecraftServer.java` `tickChildren` L1067 | Command functions → clocks → each `ServerLevel.tick` → connections → players. Player packets (block use/placement/breaking) run as main-thread tasks **between** ticks (`waitUntilNextTick` → `runAllTasks`, L838). |
| Level tick phases | `net/minecraft/server/level/ServerLevel.java` `tick` L359 | world border → weather → `tickTime` (game time +1, L481) → **block ticks** (`blockTicks.tick`, max 65 536) → fluid ticks → raid → chunk source (random ticks, spawning) → **block events** (`runBlockEvents`) → entities → **block entities** (`tickBlockEntities`). |
| Freeze / step | `ServerLevel.tick` uses `TickRateManager.runsNormally()` | When frozen, time, scheduled ticks, block events and block entities do not advance. |
| `isHandlingTick` | `ServerLevel.java` L648 | True from the start of `tick` until after block events. Used by the piston retraction decision. |

## Scheduled ticks

| Concern | Location |
|---|---|
| Tick record and ordering | `net/minecraft/world/ticks/ScheduledTick.java`: `DRAIN_ORDER` L9 (triggerTick, priority, subTickOrder), `INTRA_TICK_DRAIN_ORDER` L18 (priority, subTickOrder), `UNIQUE_TICK_HASH` (type + pos). |
| Priorities | `net/minecraft/world/ticks/TickPriority.java`: EXTREMELY_HIGH −3 … EXTREMELY_LOW +3. |
| Creation | `net/minecraft/world/level/LevelAccessor.java` `createTick` L31: `triggerTick = gameTime + delay`, `subTickOrder = level.nextSubTickCount()` (`Level.java` L1090, a level-wide counter incremented on every attempt, even rejected duplicates). |
| Dedup per (pos, block) | `net/minecraft/world/ticks/LevelChunkTicks.java` `schedule` L53 (`ticksPerPosition` set). |
| Collect then run | `net/minecraft/world/ticks/LevelTicks.java` `tick` L81 → `collectTicks` → `drainContainers` L126 → `runCollectedTicks` L182. Ticks scheduled while running are **not** run in the same tick. |
| `willTickThisTick` | `LevelTicks.java` L208: true while a collected tick for (pos, block) is still waiting in `toRunThisTick`. |
| `hasScheduledTick` | `LevelTicks.java` L202: true while the tick is still pending in the chunk container (not yet collected). |
| Execution | `ServerLevel.tickBlock` L823: runs `state.tick` only if the block at pos is still the scheduled block type. |

## Neighbor updates, shape updates, block events

| Concern | Location |
|---|---|
| Update order constant | `net/minecraft/world/level/redstone/NeighborUpdater.java` `UPDATE_ORDER` L18: W, E, D, U, N, S. |
| Shape-update order | `net/minecraft/world/level/block/state/BlockBehaviour.java` `UPDATE_SHAPE_ORDER` L85: W, E, N, S, D, U. |
| Collecting updater (depth-first queue) | `net/minecraft/world/level/redstone/CollectingNeighborUpdater.java` `addAndRun` L68, `runUpdates` L87, update records L117–205. Max chain 1 000 000 (`SharedConstants.MAX_CHAINED_NEIGHBOR_UPDATES`, configurable per server). |
| Level entry points | `ServerLevel.updateNeighborsAt` L1170, `updateNeighborsAtExceptFromFacing`, `neighborChanged`; `Level.neighborShapeChanged` L320. |
| Shape-update execution | `NeighborUpdater.executeShapeUpdate` L36 → `BlockState.updateShape` → `Block.updateOrDestroy` (`Block.java` L212). Flag 128 skips redstone wire. |
| setBlock pipeline | `net/minecraft/world/level/Level.java` `setBlock` L216 and `net/minecraft/world/level/chunk/LevelChunk.java` `setBlockState` L269. |
| Update flags | `net/minecraft/world/level/block/Block.java` L90–106 (1 neighbors, 2 clients, 4 invisible, 8 immediate, 16 known shape, 32 suppress drops, 64 moved by piston, 128 skip wire shape, 256 skip BE side effects, 512 skip onPlace; limit 512). |
| Comparator output updates | `Level.updateNeighbourForOutputSignal` L1008. |
| Block events | `ServerLevel.blockEvent` L1260 (insertion-ordered dedup set `ObjectLinkedOpenHashSet<BlockEventData>`), `runBlockEvents` L1264, `doBlockEvent` L1291 (runs only if the block type still matches). `BlockEventData` is a record (pos, block, paramA, paramB). |
| Block-entity ticking | `Level.tickBlockEntities` L527, `addBlockEntityTicker` L523; `LevelChunk.updateBlockEntityTicker` L709 (rebinding wrapper per position) and `removeBlockEntityTicker` L504. |

## Power queries

| Concern | Location |
|---|---|
| Signal queries | `net/minecraft/world/level/SignalGetter.java`: `getDirectSignalTo` L17, `getControlInputSignal` L48, `getSignal` L65, `hasNeighborSignal` L76, `getBestNeighborSignal` L90. |
| Per-block hooks | `BlockBehaviour.java`: `isSignalSource`, `getSignal` (defaults to `ownSignal`), `ownSignal` (0), `getDirectSignal` (0), `shouldRedstoneWireConnectTo` (signal source and direction ≠ null), `hasAnalogOutputSignal`, `getAnalogOutputSignal` (L360–385). |
| Conductor predicate | `BlockBehaviour.Properties.isRedstoneConductor` L1030, default `isCollisionShapeFullBlock`; overrides in `net/minecraft/world/level/block/Blocks.java` (`Blocks::never` for glass, glowstone, redstone block, observer, pistons, moving piston, leaves, TNT, ice, …; `Blocks::always` for soul sand and mud). |
| Support faces | `net/minecraft/world/level/block/SupportType.java` (FULL, CENTER, RIGID), `Block.canSupportRigidBlock` L330, `Block.canSupportCenter` L334. |

## Components

| Block | Location (key methods) |
|---|---|
| Redstone wire | `net/minecraft/world/level/block/RedstoneWireBlock.java`: `getConnectionState` L117, `getMissingConnections` L149, `updateShape` L163, `updateIndirectNeighbourShapes` L204, `getConnectingSide` L233, `updatePowerStrength` L264, `getBlockSignal` L278, `checkCornerChangeAt` L285, `onPlace` L296, `affectNeighborsAfterRemoval` L309, `updateNeighborsOfNeighboringWires` L320, `neighborChanged` L336, `getSignal` L361. Evaluators: `world/level/redstone/DefaultRedstoneWireEvaluator.java` `updatePowerStrength` L18, `RedstoneWireEvaluator.getIncomingWireSignal` L29. `ExperimentalRedstoneWireEvaluator` is used only with the `redstone_experiments` feature flag. |
| Diode base | `net/minecraft/world/level/block/DiodeBlock.java`: `tick` L50, `neighborChanged` L66, `checkTickOnNeighbor` L84, `getInputSignal` L109, `getAlternateSignal` L121, `getSignal` L148, `setPlacedBy` L158, `onPlace` L165, `updateNeighborsInFront` L176, `shouldPrioritize` L196. |
| Repeater | `net/minecraft/world/level/block/RepeaterBlock.java`: `getDelay` L47 (2 × DELAY), `updateShape` L58 (locking), `isLocked` L84. |
| Comparator | `net/minecraft/world/level/block/ComparatorBlock.java`: `calculateOutputSignal` L64, `shouldTurnOn` L79, `getInputSignal` L90, `checkTickOnNeighbor` L140, `refreshOutputState` L151, `tick` L174; `block/entity/ComparatorBlockEntity.java` (stored output). |
| Redstone torch | `net/minecraft/world/level/block/RedstoneTorchBlock.java`: `onPlace` L37, `notifyNeighbors` L41, `tick` L61 (includes burnout via `RECENT_TOGGLES`), `neighborChanged` L83, `getDirectSignal` L92, `getSignal` L107; wall variant `RedstoneWallTorchBlock.java` `hasNeighborSignal` L75, `getSignal` L81. |
| Lever | `net/minecraft/world/level/block/LeverBlock.java`: `pull` L82, `getDirectSignal` L119, `updateNeighbours` L133; attachment in `FaceAttachedHorizontalDirectionalBlock.java` `getConnectedDirection` L69. |
| Button | `net/minecraft/world/level/block/ButtonBlock.java`: `press` L92, `tick` L131, `checkPressed` L146, `updateNeighbours` L164. Stone button 20 ticks, wooden 30 (`Blocks.java`). |
| Redstone block | `net/minecraft/world/level/block/PoweredBlock.java` (`ownSignal` 15, no direct signal). |
| Redstone lamp | `net/minecraft/world/level/block/RedstoneLampBlock.java`: `neighborChanged` L29 (on: instant; off: 4-tick delay), `tick` L45. |
| Observer | `net/minecraft/world/level/block/ObserverBlock.java`: `tick` L45, `updateShape` L57, `updateNeighborsInFront` L80, signals L90-112, `onPlace` L114; `Blocks.OBSERVER` `isRedstoneConductor(Blocks::never)`. See [[mechanics/observer]]. |
| Rails | `BaseRailBlock.java`, `RailState.java`, `RailBlock.java`, `PoweredRailBlock.java` (`findPoweredRailSignal`, 8-rail limit). See [[mechanics/rails]]. |
| Target block | `net/minecraft/world/level/block/TargetBlock.java`: `updateRedstoneOutput` L44, `getRedstoneStrength` L54, `tick` L78, `onPlace` L100. See [[mechanics/target-block]]. |
| Hopper | `HopperBlock.java` (`checkPoweredState` L118, placement L77); `entity/HopperBlockEntity.java` (`removeItem` L74, `setItem` L80, `pushItemsTick` L97, `tryMoveItems` L106, `ejectItems` L143, `suckInItems` L218, `tryMoveInItem` L314). See [[mechanics/hopper]]. |
| Containers | `entity/BaseContainerBlockEntity.java` (`removeItem` L111, `setItem` L126), `ContainerHelper.java`, `inventory/AbstractContainerMenu.java` `getRedstoneSignalFromContainer` L766. |

## Pistons

| Concern | Location |
|---|---|
| Activation and QC | `net/minecraft/world/level/block/piston/PistonBaseBlock.java`: `neighborChanged` L71, `onPlace` L80, `checkIfExtend` L93, `getNeighborSignal` L116. |
| Block events | `PistonBaseBlock.triggerEvent` L139 (0 extend, 1 retract, 2 retract with drop of a moving block). |
| Pushability | `PistonBaseBlock.isPushable` L213, `world/level/material/PushReaction.java`. |
| Moving blocks | `PistonBaseBlock.moveBlocks` L257, `PistonStructureResolver.java` (`resolve` L37, `addBlockLine` L76, `addBranchingBlocks` L177, limit 12). |
| Moving block entity | `PistonMovingBlockEntity.java`: `finalTick` L259, `tick` L291 (progress +0.5 per tick, finalize when `progressO >= 1`). |
| Head and B36 | `PistonHeadBlock.java` (`canSurvive` L99, `neighborChanged` L105 relays to base), `MovingPistonBlock.java` (`destroy` L68). |

## Player interaction (for editor semantics)

| Concern | Location |
|---|---|
| Placement | `net/minecraft/world/item/BlockItem.java` `place` L55: `setBlock(pos, state, 11)` then `Block.setPlacedBy`. |
| Breaking | `net/minecraft/server/level/ServerPlayerGameMode.java` `destroyBlock` L286: `playerWillDestroy` → `removeBlock(pos, false)` (flags 3) → `Block.destroy`. |
| Use | `useWithoutItem` on lever (`pull`), button (`press`), repeater (cycle DELAY with flags 3), comparator (cycle MODE with flags 2 then `refreshOutputState`), wire (dot/cross toggle). |

## Java-library behavior the game relies on

| Behavior | Where it matters |
|---|---|
| `java.util.HashSet<BlockPos>` / `HashMap<BlockPos, …>` iteration order (bucket = `(h ^ h>>>16) & (n−1)` with `h = BlockPos.hashCode()`) | Wire update order (`DefaultRedstoneWireEvaluator.updatePowerStrength`) and piston air-replacement order (`PistonBaseBlock.moveBlocks`, `deleteAfterMove`). |
| `BlockPos.hashCode()` = `(y + z·31)·31 + x` in 32-bit arithmetic | `net/minecraft/core/Vec3i.java` L53. |
| `Direction.values()` order D, U, N, S, W, E; `Plane.HORIZONTAL` N, E, S, W; `Plane.VERTICAL` U, D | `net/minecraft/core/Direction.java` L33, L540. |

## Related

- [[mechanics/index]] for the behavior derived from these classes.
- [[quirks]] for a searchable list of non-obvious consequences.
