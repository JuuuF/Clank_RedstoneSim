# R-027: a double extender powered in one tick: the update order decides

- **Date:** 2026-10-18 · **Simulator:** 1f96d86 · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-027-double-extender-order.cli.txt` · **Status:** verified, game EXP-072 (match)
- **Question:** Purplers' 5x5 vault lamp door jams in 2 of its 8 orientations
  ([[../doors/symmetry]], backlog D2): a horizontal double extender's two pistons get
  power in the same tick, and the turned copies update the front piston first. Is the
  order alone enough to change what an extender does, without the door around it?
- **Hypothesis** (decompiled source): each piston queues its extension when it is updated
  while powered (`PistonBaseBlock.checkIfExtend`), and the block events run in queue
  order. If the rear piston R goes first, it pushes the front piston F and F's block X; F's
  queued event then finds a `moving_piston` at its position and is dropped
  (`ServerLevel.doBlockEvent` L1291 runs an event only if the block there is still the
  same, `engine.py`). If F goes first, F extends; R's event then fails, because an
  extended piston cannot be pushed, and R stays retracted while powered until something
  updates it.
- **Setup:** two copies of R (sticky, facing east) – F (sticky, facing east) – stone X in a
  row, at z 0 and z 6. Each piston gets its own power: a redstone block set on its north
  side (beside it, not beside the other piston).
- **Procedure:** both redstone blocks are set between ticks 2 and 3 (`at 2 set …`, recorded
  edits that run in their recorded order): (a) R's first, then F's; (b) F's first, then
  R's.
- **Observations** (`changes`, `inspect`):

```
(a) R extended at 3; F moving 3..4, at rest one cell east from 5, unextended; X one cell east
(b) F extended at 3, X one cell east at 5; R retracted to the end (inspect: "receives north 15")
```

- **Result:** as predicted, 2 of 2 cases.
- **Conclusion** (in [[../components]], Piston):
  - **Two pistons powered in the same tick run in the order they were updated.** For a
    double extender that order is the difference between a working first stage (R
    first: both move one cell, F's own event is dropped) and a jam (F first: R's push
    fails on the extended F and R stays in, powered).
  - When one change powers both (a wire line, one block powering R directly and F by
    quasi-connectivity), the order is the update order of that change. It follows the
    directions of the line's pieces, so the same build can work in one orientation and
    jam in another (the vault lamp door). Design rule: give the piston that must go first
    a tick of lead, or power the other one only through the first one's motion
    ([[../doors/symmetry]]).
- **Used by:** [[../doors/symmetry]], [[../doors/patterns]] ("Same-tick races depend on
  orientation").
