# Component reference

Per component: what it reads, what it gives, its state and timing, and its edge cases,
as established by the experiment records. Timings are collected in [[timing]], power
rules in [[signals]]; the simulator's source-level pages are under [[mechanics/index]].
Evidence labels: [[redstone/README#Scope and trust]].

## Redstone lamp

- Reads: power from any side (a powered block, wire pointing into it or under it, any
  adjacent source). V [[R-002-what-powers-a-block]]
- Timing: on at once, off 4 ticks after its power goes. V [[R-001-response-times]]
- Gives: nothing (not a source; it does not conduct power). S

## Redstone wire

- Reads: any adjacent source and strongly powered blocks; power falls by 1 per wire.
  V R-001, R-002
- Gives: the block or component it points into and the block under it (weak power).
  V R-002
- Timing: instant. V R-001

## Redstone torch

- Reads: the block it is attached to (a standing torch: the block under it; a wall torch:
  the block behind it). Turns off 2 ticks after that block is powered (strongly or
  weakly), on 2 ticks after it is not. V R-001, R-002
- Gives: every adjacent component and wire except its own block; the block above it
  strongly. V R-002
- Short pulses: ignores 1-tick pulses and circuit-made 2-tick pulses (observer,
  repeater); fills 1-tick gaps; anything of 3+ ticks passes with its length.
  V [[R-003-short-pulses]]
- **Burnout:** the 8th turn-off within 60 ticks burns it out (off, input ignored).
  Turned off every 8 ticks or faster it burns out; every 9 or slower never. It relights
  160 ticks after burning out if its block is unpowered then, except when its own
  turn-off unpowered its block at once (a pure wire loop): then it stays off until some
  block next to it changes. V [[R-007-torch-burnout]]

## Repeater

- Reads: its back (input) side only: a source, a wire pointing into it, or a powered
  block (strong or weak). V R-001, R-002
- Gives: 15 to the component or block in front, strongly. V R-002
- Timing: 2 ticks per delay step, on and off. V R-001
- Short pulses: once it sees a change it ignores the input until its tick runs: pulses
  and gaps shorter than its delay D come out exactly D long. Sees every pulse, also
  1-tick and circuit-made ones. V R-003
- **Locking:** a repeater or comparator pointing into its side (strength ≥ 1) locks it
  in the same tick; nothing else does (wire, torches, powered or redstone blocks,
  observers). Locked, it holds its output and ignores input changes (a change already
  waiting is dropped); unlocked, it re-reads the input and switches after its delay.
  V [[R-006-repeater-locking]]

## Comparator

- Reads: its back side: a signal (wire, a powered block, a source), or a container or
  other analog block directly behind or behind one solid block. Side inputs: wire,
  redstone blocks, repeaters and comparators pointing in (not torches, levers or powered
  blocks). Timing 2 ticks. V R-001, [[R-005-signal-strength]]
- Gives: compare mode: the rear strength if it is ≥ the side, else 0; subtract mode:
  rear − side (at least 0); strongly into a block in front. V R-002, R-005
- Short pulses: like a torch: loses 1-tick pulses and circuit-made 2-tick pulses, fills
  1-tick gaps. V R-003

## Observer

- Reads: changes of the block it watches (its `facing` side): any **state** change (a
  lever turning off, wire power 15 → 14, a repeater's delay, a block placed or broken, a
  piston head arriving or leaving). Not block-entity data (a comparator's strength while
  it stays powered, container contents) and not updates without a state change.
  V R-001, [[R-008-observers]]
- Chains of observers: 2 ticks each. Changes less than 4 ticks apart merge into one
  pulse (the [[circuits]] both-edge detector). V R-008
- Gives: a 2-tick pulse from its back (output) side, 2 ticks after the change, strongly
  into a block there. V R-001, R-002
- Its pulse is a *circuit-made 2-tick pulse*: repeaters, pistons, lamps, copper bulbs,
  droppers and wire react to it; **torches and comparators do not** (directly or through
  a block). Stretch it with a repeater of delay 2+ first. V R-003

## Piston and sticky piston

- Reads: power at any side except its front (from a powered block, wire, an adjacent
  source); quasi-connectivity is R-009. V R-001, R-002
- Timing: `extended` 1 tick after power, the pushed block in place after 3; retracting
  takes 3 (a sticky piston pulls the block back at +3). V R-001
- Short pulses: a sticky piston powered for 1 or 2 ticks (by a lever or a circuit)
  pushes its block and leaves it there; 3 ticks or more and it pulls the block back.
  V R-003

## Dropper, dispenser

- Reads: power at any side (and quasi-connectivity, R-010). Acts on a rising edge only:
  `triggered` at once, the item leaves 4 ticks later. V R-001

## Note block, copper bulb, iron trapdoor, powered rail, hopper

- React in the same tick (Δ 0). The copper bulb toggles `lit` on each rising edge and
  keeps it when power goes (a T flip-flop); the hopper locks while powered.
  V R-001
- The copper bulb toggles once for every pulse, even a 1-tick one; a dropper fires once
  per pulse of any length. V R-003

## Buttons and levers

- A lever stays until flipped; a stone button is on for 20 ticks, an oak button for 30.
  V R-001
- Both power every adjacent component and the block they are attached to (strongly),
  not other adjacent blocks. V R-002
