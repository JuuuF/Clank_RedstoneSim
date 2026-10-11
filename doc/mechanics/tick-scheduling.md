# Tick phases, scheduled ticks, block events, block entities

- **Status:** researched; implemented in `sim/engine.py`, `sim/ticks.py`, `sim/level.py`; unit-tested; timings confirmed in game (all EXPs).
- **Summary:** One game tick runs fixed phases. Redstone timing comes from three of them:
  scheduled block ticks, block events, and block-entity ticks. Player actions arrive
  between ticks.
- **Scope:** Overworld-style level, all positions loaded and block-ticking, normal tick rate
  or `/tick freeze` + `/tick step`. Fluid ticks, raids, random ticks, entities: out of scope.

## Source

- `net/minecraft/server/level/ServerLevel.java` `tick` L359, `tickTime` L481, `tickBlock` L823,
  `blockEvent` L1260, `runBlockEvents` L1264, `doBlockEvent` L1291, `isHandlingTick` L648.
- `net/minecraft/server/MinecraftServer.java` `tickChildren` L1067, `waitUntilNextTick` L838.
- `net/minecraft/world/ticks/LevelTicks.java` `tick` L81, `drainContainers` L126,
  `runCollectedTicks` L182, `hasScheduledTick` L202, `willTickThisTick` L208.
- `net/minecraft/world/ticks/LevelChunkTicks.java` `schedule` L53;
  `ScheduledTick.java` `DRAIN_ORDER` L9, `INTRA_TICK_DRAIN_ORDER` L18; `TickPriority.java`.
- `net/minecraft/world/level/LevelAccessor.java` `createTick` L31; `Level.nextSubTickCount` L1090.
- `net/minecraft/world/level/Level.java` `tickBlockEntities` L527, `addBlockEntityTicker` L523;
  `net/minecraft/world/level/chunk/LevelChunk.java` `updateBlockEntityTicker` L709,
  `removeBlockEntityTicker` L504.

## Rules (verified by reading the source)

### Phase order inside `ServerLevel.tick`

1. world border, weather (only when running normally)
2. sleep handling, sky brightness
3. `tickTime`: **game time += 1** (only when running normally)
4. **block ticks** (`blockTicks.tick(gameTime, 65536, tickBlock)`), then fluid ticks
5. raids, chunk source (random ticks, spawning)
6. **block events** (`runBlockEvents`)
7. entities (the simulator only models projectiles landing on target blocks here,
   `Phase.ENTITIES`; [[target-block]])
8. **block entities** (`tickBlockEntities`)

`MinecraftServer.tickChildren` ticks every level in turn. Player packets (use, place, break)
are executed as server-thread tasks in `waitUntilNextTick`/`pollTask`, which run **between**
`tickChildren` calls. A player action therefore sees game time T (after tick T finished) and
acts before tick T+1's time increment.

### Scheduled ticks

- `scheduleTick(pos, block, delay[, priority])` creates
  `ScheduledTick(block, pos, triggerTick = gameTime + delay, priority, subTickOrder)`.
  `subTickOrder` comes from the level-wide counter `nextSubTickCount()`, which is incremented
  for **every** call, including calls rejected as duplicates.
- **Deduplication:** `LevelChunkTicks.schedule` ignores the new tick if a tick for the same
  `(pos, block type)` is still pending in the chunk container. Priority and delay of the
  rejected call are lost.
- **Collect then run:** at the start of the block-tick phase, all ticks with
  `triggerTick <= gameTime` are moved from the containers into `toRunThisTick` (at most
  65 536). Only afterwards are they executed, in order. Ticks scheduled while running are
  not executed this tick, even with a trigger tick ≤ now.
- **Order:** within a chunk `DRAIN_ORDER` = (triggerTick, priority, subTickOrder); across
  chunks the containers are merged by `INTRA_TICK_DRAIN_ORDER` = (priority, subTickOrder).
  When every due tick has `triggerTick == gameTime` (always true unless ticks were left over
  from an earlier overflowing or frozen-chunk tick), the global order is simply
  **priority ascending (−3 first), then scheduling order**.
- A collected tick leaves the container immediately, so `hasScheduledTick(pos, block)` is
  false for it, and a new tick for the same `(pos, block)` can be scheduled during the
  current tick (for example a repeater rescheduling itself).
- `willTickThisTick(pos, block)` is true while that tick sits in `toRunThisTick` and has not
  yet run.
- Execution (`tickBlock`): the tick runs `state.tick` **only if the block at pos is still the
  scheduled block type** (`state.is(type)`). The state's properties may differ.

### Block events

- `blockEvent(pos, block, a, b)` adds `BlockEventData(pos, block, a, b)` to an insertion-ordered
  hash set. An identical record already queued is not added again.
- `runBlockEvents` removes the first element until the set is empty. Events queued while
  processing are appended and **run in the same phase of the same tick**.
- `doBlockEvent` calls `state.triggerEvent` only if the block at pos still has the queued
  block type.

### Block entities

- One level-wide `ArrayList` of ticker wrappers in registration order.
- A block entity created outside the block-entity phase is appended directly and ticks in
  the same tick's block-entity phase. One created during that phase goes to a pending list
  and starts ticking next tick.
- Each position keeps one rebindable wrapper. Replacing a ticking block entity at a position
  that still has a live wrapper rebinds it **in place**, keeping the list position. Removing
  the block entity rebinds the wrapper to a null ticker, which is dropped from the list at
  the next iteration. A later block entity at that position gets a new wrapper at the end of
  the list.

### Freeze and step

With `/tick freeze`, `runsNormally()` is false: no time increment, no scheduled ticks, no
block events, no block-entity ticks. Player actions still run their immediate updates.
`/tick step N` runs N normal ticks.

## Edge cases and quirks

- Scheduled ticks with delay 0 would only run next tick; no in-scope block uses delay 0.
- Because collection happens before running, a component cannot react within the same
  block-tick phase to a tick it scheduled itself.
- Block events can cascade within one tick: an event can queue another event that runs in
  the same phase (piston extension → neighbor update → another piston's event).

## Tests

- `tests/sim/test_scheduling.py`: delay counted from the current game time, priority then
  scheduling order, duplicate dropped but sub-tick consumed, ticks scheduled during the phase
  wait for the next tick (even delay 0), `willTickThisTick`/`hasScheduledTick`, block-type
  mismatch skip, block events FIFO/dedup/same-phase cascade, phase order, actions only
  between ticks, snapshot/restore replay.
- In game: every scenario in [[experiments/index]] depends on these timings (lamp 4,
  torch 2, button 20/30 not testable without a player).
- Block-entity ticker order is implemented but untested until moving pistons exist.

## Unknowns

- None in source reading for the in-scope paths. The multi-chunk merge with overdue ticks is
  not reproduced (they cannot arise in scope); see [[quirks]] Q-SCHED-OVERDUE.

## Related

[[neighbor-updates]] · [[repeater]] · [[comparator]] · [[redstone-torch]] · [[pistons]]
