# Repeater

- **Status:** researched (source).
- **Summary:** A diode with a delay of 2, 4, 6 or 8 game ticks. It turns on and off through
  scheduled ticks with priorities that depend on what it outputs into. Side inputs from
  other diodes lock it.
- **Scope:** Normal operation, locking, placement, removal. Pushed repeaters pop.

## Source

`net/minecraft/world/level/block/DiodeBlock.java`: `tick` L50, `neighborChanged` L66,
`checkTickOnNeighbor` L84, `shouldTurnOn` L105, `getInputSignal` L109, `getAlternateSignal`
L121, `getSignal` L148, `setPlacedBy` L158, `onPlace` L165, `affectNeighborsAfterRemoval`
L170, `updateNeighborsInFront` L176, `shouldPrioritize` L196.
`net/minecraft/world/level/block/RepeaterBlock.java`: `useWithoutItem` L35, `getDelay` L47,
`getStateForPlacement` L52, `updateShape` L58, `shouldRedstoneWireConnectTo` L78, `isLocked` L84,
`sideInputDiodesOnly` L89.

## Rules

- **Orientation.** `FACING` points **toward the input**. The input block is `pos + FACING`;
  the output goes into `pos − FACING`. (In-game F3 shows `facing=north` for a repeater that
  outputs south.)
- **Delay.** `DELAY` ∈ {1, 2, 3, 4}; scheduled delay = `2 × DELAY` game ticks.
- **Input.** `getSignal(pos+FACING, FACING)`; if below 15, also the POWER of a wire at
  `pos+FACING` (regardless of its connections).
- **Lock.** `isLocked` = max side input > 0, where side inputs (`getControlInputSignal` with
  `onlyDiodes`) only count diodes outputting into the side. Behavior always uses the **live**
  `isLocked()`; the `LOCKED` state property is only refreshed through `updateShape` when a
  neighbor on the perpendicular axis changes (shape update), and by placement.
- **neighborChanged** → `checkTickOnNeighbor`: when not locked, `POWERED != shouldTurnOn`, and
  no tick for this repeater is waiting to run this tick (`willTickThisTick`), schedule a tick
  after the delay with priority:
  - **EXTREMELY_HIGH (−3)** if the block in front is a diode that does not point back into
    this repeater (`shouldPrioritize`);
  - else **VERY_HIGH (−2)** if currently powered (turning off);
  - else **HIGH (−1)** (turning on).
- **tick** (skipped entirely if locked):
  - powered and input gone → `POWERED=false` (flags 2);
  - unpowered → `POWERED=true` (flags 2), and if the input is already gone, schedule the
    turn-off after the full delay with VERY_HIGH. This makes the minimum output pulse equal
    to the delay.
  - powered with input present → nothing.
- **Output updates.** `onPlace` (every state change) → `updateNeighborsInFront`:
  `neighborChanged(front)` then `updateNeighborsAtExceptFromFacing(front, skip = FACING)`
  (the 5 neighbors of the front block other than the repeater itself).
- **Placement.** `setPlacedBy`: if input is present, schedule a tick with **delay 1** and
  NORMAL priority (not the configured delay).
- **Removal** (not by piston): `updateNeighborsInFront`.
- **Delay change** (right-click): `setBlock(DELAY cycled, 3)`.
- **Support.** Needs a RIGID top face below; `updateShape(DOWN)` pops it otherwise.
- **Wire connection.** Wire connects only along the repeater's axis.

## Edge cases and quirks

- [[quirks]] Q-REP-PRIORITY: repeater chains and repeaters feeding a diode's side tick
  before other components scheduled for the same game tick.
- [[quirks]] Q-REP-PULSE-EXTEND: input pulses shorter than the delay are extended to the delay.
- [[quirks]] Q-REP-PLACE-DELAY1: a newly placed, already-powered repeater turns on after 1 tick.
- [[quirks]] Q-REP-LOCKED-STALE: the `LOCKED` property can be stale; behavior uses the
  live side input.
- Because `tick` re-evaluates the live input, a repeater can stay on if the input returned
  before its turn-off tick.

## Tests

Planned: `tests/sim/test_repeater.py`: delays 1–4, pulse extension, priority classes,
locking by a side repeater, lock ignored for wire/torch on the side, placement delay 1.

## Related

[[comparator]] · [[tick-scheduling]] · [[power-queries]]
