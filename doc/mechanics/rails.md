# Rails

- **Status:** researched, implemented (`src/redsim/world/blocks/rail.py`), unit-tested and
  confirmed in game: shapes (EXP-035), powered/activator propagation (EXP-036), and inside
  40 random circuits (EXP-031). Detector rails are not implemented: they only change when a
  minecart rides over them, and the simulator has no entities.
- **Source:** `net/minecraft/world/level/block/BaseRailBlock.java`, `RailState.java`,
  `RailBlock.java`, `PoweredRailBlock.java`.

## Shapes (`RailState`)

- A rail chooses its shape from neighboring rails (same level, one up or one down) that can
  still connect (`removeSoftConnections`, `canConnectTo`: a rail with two connections only
  accepts a neighbor it already points to). Plain rails can curve; powered, activator (and
  detector) rails are straight. A neighbor rail one block higher makes it ascend.
- After choosing, the rail sets itself (flags 3) and lets its connected neighbors connect
  back (`connectTo`), which can re-shape them in turn.
- A plain rail at a T junction re-runs the shape choice when a signal source updates it
  (`RailBlock.updateState`: three potential connections); with a signal the curve choice
  prefers south-east, south-west, north-east, north-west (in that order of override),
  without one north-west, north-east, south-west, south-east.
- A rail needs a rigid top face below (and, for slopes, at the high side); otherwise a
  neighbor update removes it. No collision; pistons push rails.

## Power (`PoweredRailBlock`, powered and activator rails)

- Powered when it receives a neighbor signal, or when a powered rail of the **same kind**
  along its line (straight or one step up/down) is powered and itself has a signal or
  finds one further on, up to 8 rails away (`findPoweredRailSignal`).
- On a change: set the new state (flags 3), update the block below (and above for slopes).
- Placement: east-west when looking east or west, else north-south; then `RailState`
  adjusts it.
