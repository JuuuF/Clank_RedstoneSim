# R-016: falling blocks as timers and triggers

- **Date:** 2026-10-16 · **Simulator:** 864a6da · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-016-falling-blocks.cli.txt` · **Status:** verified
  (with one limitation, below)
- **Question:** How long does a gravity block take to fall a given height once its
  support goes? Can its fall drive circuits (observers, pressure plates)?
- **Hypothesis** ([[gravity-blocks]]): the block schedules a fall 2 ticks after its
  support changes, becomes an entity with gravity 0.04 per tick² and drag 0.98, and
  places itself where it lands (state change: observers fire 2 ticks later). Passing
  through a wooden plate's cell presses it (entities count for wooden plates, not for
  stone plates); a block that cannot land in a plate's cell is discarded.
- **Setup:** a 48×48 world; sand on floating stones at heights h = 1, 2, 3, 4, 8, 16, 24
  (the sand falls h blocks to the floor), observers watching the landing cells; two sands
  falling 3 blocks into a wooden and a stone pressure plate.
- **Procedure:** the stones broken at tick 2; `changes` of the landing cells, `waves`.
- **Observations:**

| Fall height h | 1 | 2 | 3 | 4 | 8 | 16 | 24 |
|---|---|---|---|---|---|---|---|
| sand in the landing cell at tick (support removed at 2) | 10 | 13 | 16 | 18 | 24 | 34 | 42 |
| ticks after the support went | 8 | 11 | 14 | 16 | 22 | 32 | 40 |

  Observers watching the landing cells pulse 2 ticks after the landing (h=4: 20..21).
  The wooden plate was pressed at 17 (the sand's entity passed into its cell) and released
  at 37 (its 20-tick recheck); the sand was discarded (it cannot land in a plate's cell).
  The stone plate never reacted.
- **Result:** as predicted.
- **Conclusion** (in [[timing]], [[components]]):
  - A gravity block falls **2 ticks** after losing its support and lands after the times
    above (falls accelerate: 8 ticks for 1 block, 40 for 24). Usable as a delay you can
    "arm" by placing sand, and as a detector: an observer on the landing cell.
  - A falling block passing into a **wooden** pressure plate presses it; stone plates
    ignore it (they count mobs only).
  Confidence: high for times and the plate press (V; G EXP-054 compares falling-block
  positions and motion tick by tick, including gravel pressing a wooden plate).
- **Limitation (L, [[differences]]):** in the game (default rules) the block that cannot
  land on the plate drops as an **item**, and an item lying on a wooden plate keeps it
  pressed. The simulator has no items (like `entity_drops false`): the plate released at
  37 here would stay pressed in a normal game world. Do not rely on the release time.
- **Used by:** [[timing]], [[components]].
