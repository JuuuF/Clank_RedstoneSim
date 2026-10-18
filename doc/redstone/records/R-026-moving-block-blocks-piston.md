# R-026: a moving block stops a piston until it lands

- **Date:** 2026-10-18 · **Simulator:** 4449fd4 · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-026-moving-block-blocks-piston.cli.txt` · **Status:** verified
- **Question:** The 5x5 guide ([[../doors/guide-5x5]], claim G3, exercise PF.1) explains an
  extender that pushes 3 blocks when opening but only 2 when closing: during the closing
  the blocks in front are "movable from 9gt", later than the pulse. Can a piston push a
  block that is still moving? If not, what does a powered piston do when the block
  lands?
- **Hypothesis** (decompiled source, `PistonBaseBlock.checkIfExtend` L93, ported in
  `piston.py check_if_extend`): a piston only queues its extension if
  `PistonStructureResolver.resolve()` succeeds; a `moving_piston` block is immovable
  (push reaction BLOCK), so a powered piston facing a moving block queues nothing. It
  tries again on its next neighbor update; the block landing (its moving-piston entity
  placing it) is such an update, so it then extends one tick later if still powered.
- **Setup:** (a) sticky piston B (2 1 0, facing east) with a stone in front; (b) sticky
  piston A (3 1 5, facing south) pushes stone X from 3 1 6 into 3 1 7, the cell in front
  of sticky piston B (2 1 7, facing east); (c) the same at z = 12..14.
- **Procedure:** editor pulses (a piston powered by a pulse at T starts at T+1, like from a
  lever): (a) B at 2 for 6; (b) A at 2 for 10, B at 3 for 6 (B is powered while X moves);
  (c) A at 2 for 10, B at 3 for 1 (B's power ends at the start of tick 5).
- **Observations** (`changes`):

```
(a) B extended at 3; the stone moving 3..4, solid one cell east at 5
(b) X: moving_piston 3..4, stone at 3 1 7 at 5; B: no block event at 4 (trace 4 shows only
    the moving blocks' ticks), extended=true at 6, X pushed on (solid at 4 1 7 at 8)
(c) X lands at 5; B never extends; X stays until A pulls it back (13)
```

- **Result:** as predicted, 3 of 3 cases.
- **Conclusion** (in [[../components]], Piston):
  - **A powered piston facing a moving block does nothing** (it queues no event), and
    starts on its next update. The block's landing is one: the piston extends **one tick
    after the block lands**. Timing a piston "just as the block arrives" therefore costs a
    tick or two, not a failed push.
  - If the power is gone by the landing, the piston never moves: a **short pulse that
    arrives while the blocks in front still move is lost**. This is the guide's PF.1
    effect: the top stage of an extender gets its pulse while the door blocks it should
    push are still moving (closing), so the extender pushes one block less than when the
    space in front is empty (opening).
- **Open:** the guide's exact PF.1 timings (observer slider updates at 0, 3, 4 gt) need its
  exercise world, which is not in the dataset (claim G4 stays open).
- **Used by:** [[../doors/guide-5x5]] (G3, G5), [[../doors/patterns]].
