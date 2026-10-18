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
- A chain of latches on one lock bus released for 3–4 ticks moves data exactly one stage
  (2: none; 5+: race-through). V [[R-021-unlock-window]]

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
- **Moved by a piston:** it pulses once, 2 ticks after landing (any facing), unless it was
  powered when moved: then it lands, switches off at once and gives no pulse.
  V [[R-015-moving-observers]]
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
- Starts moving in the **same tick** when its power comes from a component switching
  during the scheduled ticks (repeater, torch, comparator, observer); one tick later from
  a lever or button. V [[R-009-pistons]]
- Pushes up to 12 blocks; not at all if a 13th, an immovable block (obsidian, bedrock)
  or a block with a block entity (barrel, chest, …) is in the line. Torches in the line
  break. V R-009
- Sticky: pulls the block in front back, but not push-only blocks (glazed terracotta).
  Slime moves everything touching it except honey, **including the floor under it** (a
  slime block on a long stone floor cannot be pushed: stand it on obsidian). V R-009
- A sticky piston extending into air pulls the block beyond its head when it retracts,
  even after a 2-tick pulse (only a block it was still pushing is left behind).
  V [[R-015-moving-observers]]
- Quasi-connectivity: power next to the space above it powers it, but it only checks on
  a neighbor update (BUD): it can stay retracted while powered, and extended after the
  power is gone, until the next update. V R-009
- **Spitting:** a sticky piston losing power while its block still moves places the block
  at its destination at once (in the retract's block event) and leaves it: after a 1-tick
  lever pulse the block is in place 1 tick before a full push would land it.
  V [[R-018-piston-zero-tick]], G EXP-016
- **0-tick moves:** a piston gets a 0-tick pulse made inside the block-event phase (a
  block arriving and leaving there, e.g. pushed by pistons) and still moves if its event
  was queued before the pulse ended: neighbors of a changing cell are updated west,
  east, down, up, north, south. A sticky piston then moves its block one cell in 0 ticks;
  a normal piston's head goes out and back in one tick and its block lands 2 ticks
  later. A 0-tick pulse between ticks (a player, [[R-013-zero-tick]]) never moves one.
  V R-018, G EXP-057
- **Chains collapse at once:** a piston's block event updates the cells its blocks leave
  inside the event (a `moving_piston` gives no power), and a piston depowered by that
  queues its retract into the same block-event phase. Extended sticky pistons holding
  redstone blocks against each other's backs all retract in one tick (instant wire);
  re-extending takes 3 ticks a stage. V [[R-023-instant-piston-wire]], G EXP-058
- **Landing check:** a piston moved into place by another piston checks its power when it
  lands and, if powered (also by quasi-connectivity), extends one tick later. A powered
  block beside the destination makes a self-timed trigger. V [[R-025-piston-door-timing]], G EXP-059
- **Blocked by a moving block:** a powered piston whose push line holds a block that is
  still moving queues nothing (its push check fails); the block's landing updates it and it
  extends one tick after the landing, if still powered. A pulse that ends before the
  landing is lost (an extender then pushes one block less). V [[R-026-moving-block-blocks-piston]]
- **Lost update:** held only by quasi-connectivity through a block beside its head cell, a
  piston gets no update when that block turns off while the head is still moving (the
  moving head does not pass updates on): it retracts when the head lands, one tick late.
  V R-025, G EXP-059
- **Stacked pistons:** a repeater or observer pointing into the upper of two stacked
  pistons updates it first; the lower one is quasi-powered too, but its push then fails on
  the extended upper piston. V R-025, G EXP-059

## Dropper, dispenser

- Reads: power at any side (and quasi-connectivity, R-010). Acts on a rising edge only:
  `triggered` at once, the item leaves 4 ticks later. V R-001

## Note block, copper bulb, iron trapdoor, powered rail, hopper

- React in the same tick (Δ 0). The copper bulb toggles `lit` on each rising edge and
  keeps it when power goes (a T flip-flop); the hopper locks while powered.
  V R-001
- The copper bulb toggles once for every pulse, even a 1-tick one; a dropper fires once
  per pulse of any length. Both react even to a 0-tick pulse. V R-003, [[R-013-zero-tick]]

## Rails, doors, gates

- Powered and activator rails: a powered rail feeds up to **8 more rails of its kind**
  along its straight line, both ways; instant. Detector rails are not simulated (L).
  V [[R-014-other-components]]
- Iron doors open both halves from power at either half; fence gates and trapdoors open
  while powered; all at once (Δ 0). V R-001, R-014

## Target block and lectern

- Target block: a projectile hit gives its strength for 20 ticks (arrow) or 8 (others);
  wire next to it connects and takes that strength (`hit` is an editor stand-in, L for
  real projectiles). V R-014
- Lectern: a comparator reads ⌊page / (pages − 1) · 14⌋ + 1; turning a page (a player)
  gives a 2-tick pulse. V R-014

## Hopper

- Moves one item per 8 ticks (block-entity phase); locked while powered (Δ 0). Unlocked,
  it moves on the next tick. N items empty in 1 + 8·(N − 1) ticks; an item crosses a
  straight chain at 7 ticks per hopper. A comparator reads its fill (5 slots). Pistons
  cannot move it (block entity). V [[R-011-hoppers]]

## Gravity blocks and pressure plates

- Sand and other gravity blocks fall 2 ticks after their support goes (fall times in
  [[timing]]); landing is a state change observers see. A falling block passing into a
  wooden pressure plate presses it (stone plates ignore it); it cannot land there and is
  gone (in the game it becomes an item that keeps the plate pressed: L).
  V [[R-016-falling-blocks]]
- Pressure plates with mobs and items: only the editor's `plate` stand-in (L).

## Buttons and levers

- A lever stays until flipped; a stone button is on for 20 ticks, an oak button for 30.
  V R-001
- Both power every adjacent component and the block they are attached to (strongly),
  not other adjacent blocks. V R-002
