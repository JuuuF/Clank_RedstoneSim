# R-019: wire on partial and special blocks; dropper quasi-connectivity

- **Date:** 2026-10-16 · **Simulator:** 864a6da · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-019-wire-supports-and-dropper-qc.cli.txt` ·
  **Status:** verified (support list: probe, below)
- **Question:** Which blocks can wire lie on, and does power come *down* from a wire on
  them? Are droppers quasi-connected like pistons?
- **Hypothesis** ([[redstone-wire]], `RedstoneWireBlock.canSurviveOn` and
  `getIncomingWireSignal`): wire needs a full sturdy top face (or a hopper's); a lower
  wire takes power from a wire diagonally above only if the block between is a
  conductor, while a wire on any block takes power from a wire diagonally below (R-004's
  glass rule generalised). Droppers check power with the same quasi-connectivity rule as
  pistons (EXP-044).
- **Setup and observations:**
  - **Support probe** (`place` on each block in a scratch world): wire **stays** on a top
    slab, upside-down stairs, a closed top trapdoor, a hopper, an observer, a piston,
    glass, glowstone, a lamp, a copper bulb, a target block, a barrel; it **cannot be
    placed** on a bottom slab, bottom stairs, a bottom trapdoor, a fence, a composter. (A
    wire on a trapdoor or piston falls off when the trapdoor opens or the piston
    extends.)
  - **Step down** (script, rows 4 apart; a lever on a stone powers a wire on block X; a
    floor wire east of X can only be fed by stepping down): the upper wire had 15 on
    every X; the lower wire got 14 for **stone, redstone lamp, target block, barrel**,
    and 0 for top slab, upside-down stairs, hopper, observer, glass, glowstone, copper bulb.
  - **Dropper QC** (script): a redstone block set at tick 2 next to the space above a
    dropper did nothing until a stone was placed beside the dropper at tick 10; then
    `triggered` at 10 and the item in the barrel at 14.
- **Result:** as predicted.
- **Conclusion** (in [[signals]]):
  - Power climbs onto any block that holds wire; it **steps down only from conductors**
    (full solid blocks such as stone, lamps, target blocks, barrels). Glass, glowstone,
    top slabs, upside-down stairs, hoppers, observers and copper bulbs are one-way
    (up only): useful as diodes in vertical wiring (glass towers carry signals up only).
  - Droppers (and by the source dispensers) are quasi-connected and update-checked like
    pistons: power next to the space above them works only after a neighbor update.
  Confidence: high (V, S; G EXP-007 for glass, EXP-044 for the dropper).
- **Used by:** [[signals]].
