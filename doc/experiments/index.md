# In-game experiments

Comparisons between the simulator and the real Java Edition 26.3 game. On 2026-10-10 the
owner approved running the supplied dedicated server headlessly for testing only, and
accepted the Minecraft EULA for that sandbox. Experiments run automatically through
`tools/gameserver` ([[decisions]] ADR-008, [[implementation-notes]]).

## Method

- **Server:** `data/minecraft_jars/server.jar` (the 26.3 bundler, only read). It runs in the
  gitignored sandbox `.sandbox/gameserver/` with a fresh superflat world per run. Offline
  mode, bound to 127.0.0.1, no RCON/query/status/management endpoints, peaceful.
- **World setup:** game rules `random_tick_speed 0`, `advance_time false`,
  `advance_weather false`, `spawn_mobs false`; the scenario area is force-loaded so blocks and
  block entities tick without players (`TicketType.FORCED` keeps the level active;
  `pause-when-empty-seconds=0`).
- **Terrain:** each scenario gets bedrock at y=-64, stone at -63..-62, and a stone floor at
  -61, using `fill … strict` (no updates). The simulator builds identical columns.
- **Timing:** `/tick freeze`, then `/tick step 1` per game tick, waiting until
  `/time query gametime` has advanced. Commands run between ticks, like player actions.
- **Inputs:** `/setblock` commands (mostly redstone blocks placed/removed). The simulator
  mirrors them with `Action("setblock")`, a port of `SetBlockCommand.setBlock` +
  `BlockInput.place` + `ServerLevel.updateNeighboursOnBlockSet`.
- **Observation:** after every tick, the simulator's predicted full state of each watched
  block is tested in game with `execute if block`. A failed test is resolved by testing
  each candidate block and property value, so the report shows the game's real state.
- **Evidence:** `experiments/results/<scenario>.json` holds every tick's simulator and game
  states, the origin, start game time, and a scenario fingerprint.
  `tests/sim/test_game_verified.py` replays each recording offline and fails if the
  simulator diverges or the scenario definition changed (stale evidence).
- **Sensitivity check (2026-10-11):** with the lamp's off-delay deliberately changed to 3 in
  the simulator, the harness reported a mismatch at exactly the affected tick. A match
  therefore means agreement, not an insensitive comparison.

Limits: only tick-boundary states are observable, not sub-tick order. Levers and buttons
cannot be operated without a player, so player-interaction paths are verified by source
reading and unit tests only.

## Results

| ID | Scenario | Ticks | Result | Date |
|---|---|---|---|---|
| EXP-001 | `lamp_redstone_block`: lamp on at once, off 4 ticks after its source is removed | 10 | match | 2026-10-11 |
| EXP-002 | `torch_inverter`: wire powers a block; the torch on top inverts after 2 ticks | 12 | match | 2026-10-11 |
| EXP-003 | `wire_line_lamp`: 15 wires decay 15→1, the lamp stays lit; all drop together | 10 | match | 2026-10-11 |
| EXP-004 | `and_gate`: torch AND gate; output and lamp on only with both inputs on | 30 | match | 2026-10-11 |
| EXP-005 | `torch_burnout`: self-oscillating torch burns out after 8 turn-offs and **stays out** | 260 | match | 2026-10-11 |
| EXP-006 | `torch_burnout_update`: an update more than 60 ticks later relights it; it burns out again | 140 | match | 2026-10-11 |
| EXP-007 | `glass_up_not_down`: wire climbs onto glass from either side, never descends | 4 | match | 2026-10-11 |

Evidence files: `experiments/results/<scenario>.json`.

### EXP-004 timeline (game)

Input A at tick 4, B at 10, A off at 17, B off at 23. Observed: torch A off at 6; torch B
off at 12; joining wire 0 at 12; output torch on at 14 (2 + 2 ticks); output off at 21;
lamp off at 25 (4-tick lamp delay).

### EXP-005 finding: a burnt-out torch can stay out forever

`RedstoneTorchBlock.tick` requests a 160-tick restart tick on the 8th turn-off within 60
ticks. In this loop the torch's own turn-off cascade reaches it again first, and its
`neighborChanged` schedules a 2-tick check. The restart request is then dropped by
`LevelChunkTicks.schedule`'s per-(pos, block) dedup. The 2-tick check still sees 8 recent
toggles, so the torch stays off, and nothing schedules another tick. The simulator predicted
this before the game confirmed it. EXP-006 shows that any later neighbor update (once the
toggle list has aged out) relights the torch. See [[quirks]] Q-TORCH-BURNOUT-STUCK.

### EXP-007 finding: glass is a one-way staircase

A lower wire only looks *below* a non-conductive neighbor for wire, and never on top of it,
so power climbs onto glass but cannot come down (`RedstoneWireEvaluator.getIncomingWireSignal`).
Both sides were tested by moving the source from east to west. See [[quirks]]
Q-WIRE-GLASS-UP.

## Template for manual experiments

```markdown
## EXP-NNN: <short title>
- Date / game version: 26.3, clean superflat world
- Setup, procedure, in-game observation, simulator result, verdict, evidence
```
