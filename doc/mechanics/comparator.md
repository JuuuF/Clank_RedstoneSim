# Comparator

- **Status:** researched (source).
- **Summary:** A diode with a fixed 2-tick delay that outputs an analog signal stored in its
  block entity. It reads containers and other analog blocks directly or through one
  conductor, and compares or subtracts its side inputs.
- **Scope:** Compare/subtract, side inputs, analog block input; item frames out of scope
  (entities).

## Source

`net/minecraft/world/level/block/ComparatorBlock.java`: `getDelay` L39, `updateShape` L44,
`getOutputSignal` L60, `calculateOutputSignal` L64, `shouldTurnOn` L79, `getInputSignal` L90,
`useWithoutItem` L123, `checkTickOnNeighbor` L140, `refreshOutputState` L151, `tick` L174.
`net/minecraft/world/level/block/entity/ComparatorBlockEntity.java` (`output`).
Shared diode logic: [[repeater]] (`DiodeBlock`).
`net/minecraft/world/level/Level.java` `updateNeighbourForOutputSignal` L1008.
`net/minecraft/world/inventory/AbstractContainerMenu.java` `getRedstoneSignalFromContainer`;
`net/minecraft/util/Mth.java` `lerpDiscrete` L545.

## Rules

- **Rear input.** Start with the diode input (`getSignal` of the rear block, or wire POWER).
  If the rear block has analog output, use **only** its analog value. Otherwise, if the
  input is below 15 and the rear block is a conductor, look one block further: if that block
  has analog output (or an item frame is there), use that value instead.
- **Side input.** `max(controlInput(left), controlInput(right))`: wire → POWER, redstone
  block → 15, other signal sources → their *direct* signal into the comparator, else 0
  ([[power-queries]]).
- **Output** (`calculateOutputSignal`): rear = 0 → 0; side > rear → 0; SUBTRACT → rear − side;
  COMPARE → rear.
- **POWERED** (`shouldTurnOn`): rear > 0 and (rear > side, or rear == side in COMPARE mode).
- **neighborChanged** → `checkTickOnNeighbor`: unless a tick is waiting this tick, if the
  computed output differs from the stored output or POWERED differs from `shouldTurnOn`,
  schedule a tick after 2 game ticks with **HIGH** if `shouldPrioritize` (the front block is
  a diode not pointing back), else **NORMAL**.
- **tick** → `refreshOutputState`: store the new output; if it changed **or the mode is
  COMPARE**: update POWERED with flags 2 if needed, then `updateNeighborsInFront`.
- **Mode change** (right-click): `setBlock(MODE cycled, 2)` then immediately
  `refreshOutputState`, with no delay.
- **Analog source updates.** Any `setBlock` with flag 1 of a block with analog output calls
  `updateNeighbourForOutputSignal`, which sends `neighborChanged` to comparators directly
  beside it horizontally, or behind one conductor.
- **Container signal.** `lerpDiscrete(fill, 0, 15) = floor(fill × 14) + (fill > 0 ? 1 : 0)`,
  where `fill = Σ(count / min(99, maxStack)) / slots`, computed in 32-bit float.

## Edge cases and quirks

- [[quirks]] Q-COMP-DOUBLE-FRONT: when POWERED changes, the front receives
  `updateNeighborsInFront` twice: once from `onPlace` and once explicitly.
- [[quirks]] Q-COMP-COMPARE-UPDATES: in COMPARE mode every comparator tick updates the
  front, even if nothing changed.
- [[quirks]] Q-COMP-OUTPUT-NO-STATE: output-strength changes that keep POWERED unchanged
  change only the block entity, so no shape update reaches observers.
- An analog block directly behind replaces the redstone input completely, even a higher
  one.

## Tests

Planned: `tests/sim/test_comparator.py`: compare and subtract truth table, side input
sources (wire, redstone block, repeater, torch → 0), reading a container directly and through
a conductor, 2-tick delay with NORMAL/HIGH priority, mode toggle without delay.

## Related

[[repeater]] · [[power-queries]] · [[tick-scheduling]]
