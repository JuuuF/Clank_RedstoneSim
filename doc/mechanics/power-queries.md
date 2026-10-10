# Power queries: weak, strong, and "wire-weak" power

- **Status:** researched; implemented as `Level` signal methods; unit-tested; confirmed in game through every scenario.
- **Summary:** The game asks two questions of an emitter: `getSignal` (power into an
  adjacent block or component) and `getDirectSignal` (strong power into the block it
  touches). A conductor block re-emits the maximum strong power it receives as an ordinary
  signal. What players call "weak power from dust" is not a separate channel: it is dust's
  strong signal, hidden only from other dust by a global flag.
- **Scope:** All in-scope emitters and receivers.

## Source

- `net/minecraft/world/level/SignalGetter.java`: `getDirectSignal`, `getDirectSignalTo` L17,
  `getControlInputSignal` L48, `getSignal` L65, `hasNeighborSignal` L76, `getBestNeighborSignal` L90.
- `net/minecraft/world/level/block/state/BlockBehaviour.java` L360–385 (defaults).
- `net/minecraft/world/level/block/RedstoneWireBlock.java` `getBlockSignal` L278, `getDirectSignal`
  L356, `getSignal` L361, `isSignalSource` L396 (`shouldSignal` flag).

## Rules

**Direction convention.** In `getSignal(pos, dir)` and `getDirectSignal(pos, dir)`, `pos` is
the emitter and `dir` points **from the receiver to the emitter**: the receiver is at
`pos.relative(dir.opposite())`. Example: `hasNeighborSignal(p)` asks
`getSignal(p.below(), DOWN)`.

- `level.getSignal(pos, dir)`: `s = state.getSignal(dir)`; if the block is a conductor,
  `max(s, getDirectSignalTo(pos))`.
- `getDirectSignalTo(pos)`: max of `getDirectSignal(neighbor, dir)` over D, U, N, S, W, E,
  stopping early at 15.
- `hasNeighborSignal(pos)`: any `getSignal(neighbor, dir) > 0` over D, U, N, S, W, E (short-circuit).
- `getBestNeighborSignal(pos)`: max over `Direction.values()` (D, U, N, S, W, E), early exit at 15.
- `getControlInputSignal(pos, dir, onlyDiodes)` (diode side inputs):
  - repeater (`onlyDiodes`): `getDirectSignal` of a diode, 0 for anything else;
  - comparator: redstone block → 15; wire → its POWER (whatever its connections); other
    signal source → `getDirectSignal(pos, dir)`; anything else → 0.

| Emitter | `getSignal(dir)` (weak) | `getDirectSignal(dir)` (strong) |
|---|---|---|
| Redstone block | 15 in all directions | 0 |
| Lever / button (powered) | 15 in all directions | 15 only into the attached block |
| Torch (lit) | 15 except into the block below it (`dir ≠ UP`) | 15 only into the block above (`dir == DOWN`) |
| Wall torch (lit) | 15 except into the attached block (`dir ≠ FACING`) | 15 only into the block above |
| Repeater / comparator (powered) | output only into the block in front (`dir == FACING`) | same as `getSignal` |
| Redstone wire | POWER into the block below (`dir == UP`) and into each side it connects to (connection recomputed live via `getConnectionState`); never upward | same as `getSignal` while `shouldSignal` |

### Why dust gives "weak" power

`RedstoneWireBlock.getBlockSignal` sets the static flag `shouldSignal = false`, calls
`getBestNeighborSignal`, then restores it. While the flag is false, every wire reports
`isSignalSource == false`, `getSignal == 0`, and `getDirectSignal == 0`. So when a wire
computes its own input, a conductor powered only by dust contributes nothing, but every
other receiver (repeater, torch, piston, lamp, comparator) sees that conductor as powered.
This is the in-code definition of "weakly powered".

## Edge cases and quirks

- [[quirks]] Q-POW-TORCH-SIDE: a torch beside a comparator is not a side input (a torch's
  direct signal goes only upward). The same holds for levers and buttons, whose direct
  signal goes only into their attached block.
- [[quirks]] Q-POW-WIRE-SIDE: any wire next to a comparator's side counts at full POWER,
  even if it does not visually point into the comparator.
- Signal queries read the world as it is at the moment of the query. Nothing caches power,
  except the stored states of wire (POWER), diodes (POWERED, comparator output), and torches
  (LIT).

## Tests

- `tests/sim/test_components.py`: lever strong power only into the attached block; torch
  strong power upward only; wire-powered block activates a lamp but not other wire.
- Comparator side-input cases follow when the comparator is implemented.

## Related

[[block-properties]] · [[redstone-wire]] · [[repeater]] · [[comparator]] · [[redstone-torch]]
