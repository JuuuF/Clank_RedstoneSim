# R-009: pistons as building blocks

- **Date:** 2026-10-16 · **Simulator:** 864a6da · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-009-pistons.cli.txt` · **Status:** verified
- **Question:** What can a piston push and pull, and what stops it? How do slime and
  honey behave in practice? How does quasi-connectivity behave? When does a piston start
  moving relative to the component that powers it?
- **Hypothesis** ([[pistons]]): push limit 12; obsidian and block-entity blocks stop the
  push; torches in the line break; a sticky piston does not pull push-only blocks (glazed
  terracotta); slime carries every touching block except honey, including the **floor**
  under it (Q-PISTON-SLIME-FLOOR), which makes the push fail on a long floor; power at
  the space above the piston counts, but the piston only checks on an update (BUD); a
  pushed redstone block powers its new neighbors when it lands. The piston moves in a
  block event, which runs after the scheduled ticks of the same tick: a repeater or torch
  that switches in tick T moves the piston in tick T; a lever flipped after tick T (a
  player action) moves it in tick T+1.
- **Setup:** a 64×64 world, pistons at x=0 facing east (the script's header lists the
  rows). SLIME's slime block stands on obsidian (`set 1 0 z obsidian`); SLIMEFLOOR's on
  the stone floor. QCBUD: a redstone block set at (0,2,z+1), touching the space above the
  piston but not the piston; at 10 a stone placed beside the piston (an update), at 20 the
  redstone block removed, at 30 the stone broken. QCREP: a repeater on a stone west of the
  piston, one block up, pointing into the space above the piston.
- **Observations** (`waves`, `changes`; levers at tick 2):

```
@P_PUSH12 extended at 3, the 12th stone lands at 13 1 z at tick 5
@P_PUSH13 / @P_OBSID / @P_BARREL      never extend
@P_POP    extends; the torch at 2 1 z is gone, the stone lands there at 5
TERRA     terracotta pushed to 2 1 z (5); after retracting (lever off at 20) it stays there
SLIME     slime + the stone on top move east (5), honey beside stays; pulled back at 23
SLIMEFLOOR  never extends (the slime grabs the floor row: more than 12 blocks)
@P_QCBUD  ...........ffffffffffffffffffff..........  (extends at the update at 10,
          stays out after the redstone block goes at 20, retracts after the update at 30)
@P_QCREP  extends at 4: the same tick its repeater turns on
@LAMP_RBPUSH  lit at 5, when the redstone block lands
REPDRV    repeater on at 4, piston extended at 4
TORCHDRV  torch off at 4, sticky piston starts retracting at 4
```

- **Result:** every hypothesis held.
- **Conclusion** (in [[components]] Piston, [[timing]]):
  - **Push:** up to 12 blocks; a 13th, an immovable block (obsidian, bedrock), or any
    block with a block entity (barrel, chest, furnace, …) anywhere in the line: the piston
    does not move at all. Torches (and other "popping" blocks) in the line break.
  - **Pull (sticky):** pulls the block in front back, except push-only blocks (glazed
    terracotta), which are left where they were pushed.
  - **Slime:** moves every block touching it that can stick (not honey), **including the
    block under it**: a slime block resting on a long pushable floor makes the push fail.
    Stand slime on immovable blocks (obsidian) or keep it off the ground.
  - **Quasi-connectivity:** power next to the space **above** the piston powers it, but
    the piston only notices on a neighbor update. It can sit unpowered-but-powered (BUD)
    and stays extended after that power is gone until the next update.
  - **Same-tick reaction:** a piston powered by a component that switches during the
    scheduled ticks (repeater, torch, comparator, observer) starts moving **in that same
    tick**; powered by a lever or button (player action between ticks) it starts in the
    next tick. The pushed block is solid 2 ticks after the start.
  - A pushed redstone block powers its new neighbors only when it lands.
  Confidence: high (V, S; G in EXP-015…020, 047).
- **Open:** pushing observers, droppers and other components that react to being moved;
  double piston extenders; 0-tick piston tricks (R-012).
- **Used by:** [[components]], [[timing]], piston circuits in [[circuits]].
