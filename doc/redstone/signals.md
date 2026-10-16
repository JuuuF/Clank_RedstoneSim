# Signals and power

How power gets from a source to a component: which blocks give power, to which
neighbors, and how solid blocks pass it on. Evidence labels:
[[redstone/README#Scope and trust]]. The source-level description (the game's
`getSignal` / `getDirectSignal`) is [[power-queries]].

## Words

- A **component** reacts to power: lamp, torch, repeater, comparator, piston, dropper,
  note block, copper bulb, door, rail, hopper, wire.
- A **solid block** (stone, planks, wool, …: the game's *redstone conductors*) can be
  *powered* and then powers the components around it. Glass, glowstone, slabs, leaves,
  redstone blocks and most non-full blocks are not conductors ([[block-properties]]).
- **Strongly powered** block: powered by a source other than wire. It powers every
  component around it **and wire beside, on and under it**.
- **Weakly powered** block: powered only by wire. It powers every component around it
  (lamps, torches attached to it, repeaters and comparators facing away from it, pistons,
  droppers, …) but **not wire**.

## What powers a solid block (R-002)

| Source next to the block | Block powered? | Evidence |
|---|---|---|
| Lever or button **attached to** it (on any face) | strongly | V [[R-002-what-powers-a-block]] |
| Lever or button beside it but attached to another block | no | V R-002 |
| Torch **under** it (standing on the block below) | strongly | V R-002, G EXP-005 |
| Torch standing beside it, or hanging **on** it | no | V R-002 |
| Repeater, comparator **pointing into** it | strongly | V R-002 |
| Observer **output** into it | strongly (for its 2-tick pulse) | V R-002 |
| Wire **pointing into** it, or **lying on top of** it | weakly | V R-002, G EXP-002 |
| Wire running past it (not pointing in) | no | V R-002 |
| Redstone block beside it | no (the redstone block powers components and wire directly) | V R-002, S Q-PROP-REDBLOCK |
| Another powered block | no: power never chains block to block | V R-002 |

## What a source powers directly (without a block in between)

| Source | Powers these neighbors directly | Evidence |
|---|---|---|
| Lever, button | every adjacent component and wire (any side), plus the block it is attached to (strongly) | V R-001, R-002 |
| Torch | every adjacent component and wire except the block it is attached to; the block above it strongly | V R-002 |
| Redstone block | every adjacent component and wire | V R-002 |
| Repeater, comparator | only the component or block in front (the output side) | V R-001 |
| Observer | only the component or block behind it (its output side) | V R-001 |
| Wire | the block or component it points into, and the block under it; wire it connects to | V R-001, R-002 |

## Wire

- Power drops by 1 per wire: a lever's 15 reaches 15 wires (the 15th has power 1). V R-001.
- Wire changes in the same tick as its source (no delay). V R-001.
- A wire beside, on or under a strongly powered block takes that block's power (15 from
  a lever or torch, a comparator's value from a comparator, R-005). V R-002,
  [[R-004-wire-geometry]], [[R-005-signal-strength]]. This also happens when you did not
  mean it: a wire routed past another circuit's input block picks up its power
  ([[circuits]] combination lock).
- **What a wire powers:** the block under it and every neighbor its shape **points
  into**. V R-004
  - a lone wire placed by a player is a **cross**: it points into all four sides;
  - right-clicked (`use`) it becomes a **dot**: it powers only the block under it;
    `use` again turns it back into a cross;
  - a wire with one connection is a **line** pointing on through its far end;
  - a **corner** points into its two arms only, not the other two sides;
  - a wire running past a block or component (beside it, not pointing in) does not
    power it.
- **Steps:** wire connects one block up onto a solid block beside it, and down from one,
  unless a solid block sits directly over the lower wire (it cuts the step). Over
  **glass** and **top slabs** (non-conductors that hold wire) power climbs **up but never
  down**. V R-004, G EXP-007
- Wire passing along a repeater's side does not power or lock it. V R-004
- **Which blocks hold wire, and which pass power down** ([[R-019-wire-supports-and-dropper-qc]]):
  wire lies on full blocks, top slabs, upside-down stairs, closed top trapdoors, hoppers,
  observers, pistons, glass, glowstone, lamps, copper bulbs, target blocks, barrels; not on
  bottom slabs or stairs, bottom trapdoors, fences, composters. Power climbs onto all of
  them but steps **down** only from conductors (stone, lamps, target blocks, barrels…);
  glass, glowstone, top slabs, upside-down stairs, hoppers, observers and copper bulbs
  pass it up only. V

## Signal strength (R-005)

| Through | Strength out | Evidence |
|---|---|---|
| Wire | −1 per wire | V R-001, [[R-005-signal-strength]] |
| A solid block | the strongest signal powering it (a comparator's 7 → wire beside the block gets 7; wire at 10 into a block → a comparator behind it reads 10) | V R-005 |
| Repeater | always 15 | V R-005 |
| Comparator, compare mode | rear if rear ≥ side, else 0 | V R-005, G EXP-012 |
| Comparator, subtract mode | max(rear − side, 0) | V R-005, G EXP-012 |
| Comparator → comparator | unchanged | V R-005 |

**Comparator side inputs** (the larger of the two sides counts): wire beside it (at its
power), a redstone block, a repeater or comparator pointing into the side. **Not** side
inputs: torches, levers, buttons, powered solid blocks. An observer's 2-tick pulse at a
side was lost (comparator with nothing in front, R-005), as it is at the rear (R-003; it
passes the rear of a comparator that feeds a repeater or comparator, R-012).
V R-005, G EXP-014

**Comparator rear input:** a container or other analog block directly behind, or behind
one solid block (unless that block has power 15: then 15). V R-005, G EXP-013

**Container readings:** 1 + ⌊14 × fullness⌋, 0 when empty; fullness = Σ(count / max stack
size) / slots, so a 16-stack item (ender pearl) counts 4× a 64-stack item. Items of a
64-stack item needed for each reading (thresholds 1, 2, 14, 15 tested, V R-005; the rest
computed with the simulator's own float32 formula, I):

| Reading | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Hopper (5 slots) | 1 | 23 | 46 | 69 | 92 | 115 | 138 | 160 | 183 | 206 | 229 | 252 | 275 | 298 | 320 |
| Dropper, dispenser (9) | 1 | 42 | 83 | 124 | 165 | 206 | 247 | 288 | 330 | 371 | 412 | 453 | 494 | 535 | 576 |
| Barrel, chest (27) | 1 | 124 | 247 | 371 | 494 | 618 | 741 | 864 | 988 | 1111 | 1235 | 1358 | 1482 | 1605 | 1728 |
| Double chest (54) | 1 | 247 | 494 | 741 | 988 | 1235 | 1482 | 1728 | 1975 | 2222 | 2469 | 2716 | 2963 | 3210 | 3456 |

The CLI's `source POS barrel N` builds a barrel of reading N directly.

## Quasi-connectivity

Pistons (and, by the source, droppers and dispensers) also count power next to the space
**above** them, but only check when they get a neighbor update: they can sit powered but
unmoved, or stay out after the power is gone, until the next update. A repeater pointing
into that space updates the piston, so it reacts at once. V [[R-009-pistons]] (pistons),
[[R-019-wire-supports-and-dropper-qc]] (droppers), G EXP-044.

## Open

See [[backlog]].
