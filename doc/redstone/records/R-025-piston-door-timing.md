# R-025: piston timing rules behind the 3x3 door

- **Date:** 2026-10-18 · **Simulator:** c9a3f56 · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-025-piston-door-timing.cli.txt` · **Status:** verified (simulator and game: EXP-059)
- **Question** (from building the 3x3 flush door, backlog Q18): three piston behaviors the
  door's middle column depends on, isolated:
  - (a) Two sticky pistons stacked, both facing up; a repeater powers the upper one from
    the side. The lower one is quasi-powered by the same repeater (it points into the cell
    above the lower piston). Does the lower one move?
  - (b) A sticky piston is powered directly and also by quasi-connectivity through a block
    beside its head cell, and both turn off in the same tick while its head is still
    moving out. When does it retract?
  - (c) A sticky piston set down by another piston next to an already powered block: does
    it extend, and when?
- **Hypothesis** (the piston code of R-009, R-015, R-018): (a) the repeater updates the
  block in front of it first, so the upper piston queues its extension before the lower
  one does; when the lower one's event runs, the piston above it is extended and cannot
  be pushed. (b) The update for the side block's power change reaches the head cell, a
  moving piston block, which does not pass updates on, so the piston keeps its extension
  until the head lands and updates it. (c) A block landing from a piston move is placed
  like a new block; a piston checks its power on placement.
- **Setup** (24×24 world, ground y=0):
  - (a) sticky pistons AL 1 1 0 and AU 1 2 0 facing up, stone 1 3 0 on top; repeater AR
    1 2 1 pointing north into AU.
  - (b) sticky piston P 6 1 0 facing up, air above it, stone 6 3 0 two above; repeater D
    6 1 1 pointing into P; stone 7 2 0 beside P's head cell, powered by repeater R 8 2 0
    pointing west.
  - (c) a lifting sticky piston 1 1 4 (driven by repeater K 1 1 5) under sticky piston
    Q 1 2 4, both facing up; stone 1 5 4 two above Q's raised position; stone 2 3 4 beside
    the raised position, powered by repeater YR 3 3 4.
- **Observations:**
  - (a) AU extends at 4 and retracts at 10 (home by 12); AL never moves (target `masked`).
  - (b) Direct power only (a 1-tick pulse into D, so P powered 4..5): P retracts at 6 and
    the stone two above is pulled down by 8 (`direct`). Direct plus the side block, both
    off at 6: P is still extended at 6 with its head landed at 6, retracts at 7, stone
    down by 9 (`headqc`). `why` on P names the head's landing (block entity tick → piston
    head → neighbor update to P) as the cause of the retraction.
  - (c) Q lands at 1 3 4 at 6 and extends at 7; when YR turns off (24) it retracts and pulls
    the stone two above it down by 26 (`landing`).
- **Conclusion:**
  - A repeater (or an observer) pointing into a piston updates that piston before the
    other neighbors of its front cell. A piston below it, quasi-powered by the same
    component, still tries to push but fails, because the upper piston is already
    extended. Stacked piston columns can share drivers this way. The upper piston's queued
    extension is what blocks the lower one; it is not a general immunity to
    quasi-connectivity.
  - **Lost update:** a piston held by quasi-connectivity through a block beside its head
    cell gets no update when that block turns off while the head is still moving. It
    retracts only when the head lands, one tick late. It never hangs: the landing always
    updates it. In a sequence, count +1 tick for this.
  - **Landing check:** a piston moved into place checks its power when it lands. Next to
    a powered block (or quasi-powered), it extends one tick after landing (its event is
    queued in the block-entity phase and runs in the next tick's block events). A block
    that powers a piston's destination is therefore a self-timing trigger: the piston fires
    exactly when it arrives (the library's double piston extender uses this; the 3x3 door
    uses it twice).
- **In the game:** EXP-059 (`tools/gameserver` scenario `piston_door_timing`, the three setups
  with redstone blocks placed behind the repeaters as inputs): every watched block matched
  the simulator for 40 ticks: AL never moves, P retracts at 7 after its head landed at 6, Q
  lands at 6 and extends at 7. Confidence: high (V; G EXP-059).
- **Used by:** [[circuits]] 3x3 flush door, [[components]] pistons.
