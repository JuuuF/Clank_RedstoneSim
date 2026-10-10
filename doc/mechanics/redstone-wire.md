# Redstone wire (dust)

- **Status:** researched (source).
- **Summary:** Wire recomputes its power instantly (no scheduled ticks) whenever it receives a
  neighbor update. On a change it emits a large, location-dependent burst of neighbor
  updates. Connections (the NORTH/EAST/SOUTH/WEST properties) are maintained through shape
  updates.
- **Scope:** Default (non-experimental) wire evaluator; `redstone_experiments` is out of scope.

## Source

`net/minecraft/world/level/block/RedstoneWireBlock.java`: `getConnectionState` L117,
`getMissingConnections` L149, `updateShape` L163, `updateIndirectNeighbourShapes` L204,
`getConnectingSide` L229/L233, `canSurviveOn` L260, `updatePowerStrength` L264,
`getBlockSignal` L278, `checkCornerChangeAt` L285, `onPlace` L296, `affectNeighborsAfterRemoval`
L309, `updateNeighborsOfNeighboringWires` L320, `neighborChanged` L336, `getSignal` L361,
`useWithoutItem` L482, `updatesOnShapeChange` L503.
`net/minecraft/world/level/redstone/DefaultRedstoneWireEvaluator.java` `updatePowerStrength` L18;
`RedstoneWireEvaluator.java` `getIncomingWireSignal` L29.

## Rules

### Power level

`target = getBlockSignal(pos)` (best neighbor signal with all wires muted, see
[[power-queries]]); if `target < 15`, `target = max(target, incomingWire − 1)` where
`incomingWire` is the highest POWER among:

- the four horizontal neighbors that are wire;
- for each horizontal neighbor that **is a conductor**: the wire on top of it, but only if
  the block above this wire is **not** a conductor (step up);
- for each horizontal neighbor that **is not a conductor**: the wire below it (step down).

`updatePowerStrength`: if POWER differs from the target, `setBlock(pos, POWER=target, 2)`
(only if the stored state is still the evaluated one), then call `updateNeighborsAt` on a
`HashSet` containing `pos` and its 6 neighbors, **in Java HashSet iteration order** (7
multi-neighbor updates, 42 `neighborChanged` calls). The evaluator does not compare against
the previous power first; any difference triggers the full burst.

### Update sources

| Event | Effect |
|---|---|
| `neighborChanged` | if it can still survive: `updatePowerStrength`; otherwise drop and `removeBlock` |
| `onPlace` (new wire only) | `updatePowerStrength`, then `updateNeighborsAt` above, then below, then `updateNeighborsOfNeighboringWires` |
| `affectNeighborsAfterRemoval` (not by piston) | `updateNeighborsAt` for all 6 neighbors (D, U, N, S, W, E), `updatePowerStrength`, `updateNeighborsOfNeighboringWires` |
| `updateNeighborsOfNeighboringWires` | for N, E, S, W: `checkCornerChangeAt(pos+dir)`; then for N, E, S, W: if `pos+dir` is a conductor `checkCornerChangeAt(pos+dir+up)`, else `checkCornerChangeAt(pos+dir+down)` |
| `checkCornerChangeAt(p)` | only if `p` is wire: `updateNeighborsAt(p)` and `updateNeighborsAt` for all 6 neighbors of `p` |

### Connections (shape)

- `getConnectingSide(dir)`: if the block above is not a conductor and the side neighbor can
  carry wire on top (sturdy UP face, hopper, or trapdoor) and there is wire on top of it:
  `UP` if the neighbor's facing side is sturdy, else `SIDE`. Otherwise `SIDE` if the neighbor
  itself connects (`shouldRedstoneWireConnectTo`) or (the neighbor is not a conductor and
  there is wire below it); else `NONE`.
- `shouldRedstoneWireConnectTo`: wire always; repeater only along its axis; other blocks if
  they are signal sources and the query has a direction (comparators, torches, levers,
  buttons, redstone block). Blocks outside the current scope (observers, …) override this and
  are researched when added.
- `getConnectionState`: recompute all sides; a dot (no connections) whose recomputed
  connections are also empty stays a dot; otherwise, a side that has no connection on its
  axis is filled in so that a single connection becomes a straight line and no connections
  become a cross.
- `updateShape`: DOWN → air if support is lost (the wire pops); UP → full `getConnectionState`;
  sides → update one side, or recompute everything if connectedness on that side changed or
  the wire was a cross.
- Right-click toggles between dot and cross when the wire has no forced connections.

### Output

Wire powers the block below it and every side it currently connects to (connections are
recomputed live by `getSignal`, so the stored properties only matter for the dot/cross
distinction). It never powers upward. A dot powers only the block below it.

## Edge cases and quirks

- [[quirks]] Q-WIRE-HASH: update order of a wire power change depends on world coordinates
  through `BlockPos.hashCode()` and Java's hash table layout ("locational" behavior).
- [[quirks]] Q-WIRE-INSTANT: wire changes propagate within a single neighbor-update cascade,
  never through scheduled ticks.
- [[quirks]] Q-WIRE-REDUNDANT: a falling wire line first decreases step by step and can
  briefly hold intermediate values; each step fires the full burst (the classic
  "redstone lag" pattern). The order of these intermediate states is fully deterministic.
- Wire power changes use flags 2, so the change itself sends shape updates (observers can see
  it) but no neighbor updates from `setBlock`; all neighbor updates come from the explicit
  burst.

## Tests

Planned: `tests/sim/test_wire.py`: decay along a line, step up/down with conductor and
non-conductor tops, glass step-down, dot vs cross output, hash-order trace at two different
coordinates, removal cascades.

## Unknowns

- None in the default evaluator. The experimental evaluator is out of scope ([[decisions]]
  ADR-006).

## Related

[[power-queries]] · [[neighbor-updates]] · [[block-properties]]
