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
- A wire beside a strongly powered block takes power 15 from it. V R-002.
- Shapes (dot, line, cross), stepping up and down, and what a wire points into: R-004
  ([[backlog]]).

## Open

Signal strength through blocks (a comparator with output 7 into a block: does wire beside
it get 7?), wire shapes, quasi-connectivity: [[backlog]].
