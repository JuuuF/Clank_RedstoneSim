# Observer

- **Status:** researched, implemented (`src/redsim/world/blocks/observer.py`), unit-tested
  and confirmed in game: observer clock (EXP-032), detection of dust, lamps, pistons and
  observer chains (EXP-033), observers moved by a piston while pulsing (EXP-034), and inside
  40 random circuits (EXP-031).
- **Source:** `net/minecraft/world/level/block/ObserverBlock.java`; registration
  `Blocks.OBSERVER` (`isRedstoneConductor(Blocks::never)`, L3762).

## Behavior

- `FACING` (six-way) is the watched side; the output is the back. Placement: `FACING` = the
  nearest looking direction (the face points away from the player).
- A **shape update** coming from the watched side while unpowered schedules a tick in 2
  (`updateShape` → `startSignal`, unless one is pending). Any state change of the watched
  block causes one (`setBlock` sends shape updates unless flag 16 is set), so observers
  react to dust power changes, lamps lighting, pistons moving, other observers pulsing.
- `tick`: unpowered → powered and another tick in 2; powered → unpowered. Both then update
  the block behind (`neighborChanged`, then its neighbors except towards the observer).
  So a pulse lasts 2 ticks, starting 2 ticks after the change.
- Signals: weak and strong 15 towards the back only; dust connects only at the back.
- **Not a redstone conductor:** power never passes through an observer. The first game
  comparison caught this (a lamp in front lit up in the simulator only); the registry
  flag is now ported.
- Placed while powered without a pending tick (e.g. pushed): turns unpowered (flags 18) and
  updates the block behind. Removed while powered with a pending tick: the block behind is
  updated as if unpowered. Pistons can move observers.
