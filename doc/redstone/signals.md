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
- A wire beside, on or under a strongly powered block takes power 15 from it. V R-002,
  [[R-004-wire-geometry]].
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

## Open

Signal strength through blocks (a comparator with output 7 into a block: does wire beside
it get 7?), wire shapes, quasi-connectivity: [[backlog]].
