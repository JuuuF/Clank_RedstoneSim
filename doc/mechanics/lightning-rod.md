# Lightning rods

Ported in `world/blocks/lightning_rod.py` (`LightningRodBlock`, `RodBlock`,
`WeatheringLightningRodBlock`; the strike from `LightningBolt`). Verified on the real 26.3
server: EXP-066 (`lightning_rods`), lightning bolts summoned on rods, block states compared
every tick.

All eight ids behave the same: `lightning_rod`, `exposed_`, `weathered_`, `oxidized_`, and
the `waxed_` ones (oxidation is a random tick, not simulated).

- **State:** `facing` (the clicked face: up when placed on top of a block), `powered`,
  `waterlogged` (inert). A 4×4 rod along `facing`'s axis; it needs no support, is pushed and
  pulled by pistons, is `solid` (`forceSolidOn`) but never a conductor.
- **Always a signal source**, so redstone wire next to it connects to it (EXP-066).
- **Struck by lightning** (`onLightningStrike`): `powered`; 15 to every side, strong power
  only into the block behind it (the one it was placed against); the neighbors of that
  block are updated; a tick 8 later turns it off (EXP-066: lamps beside those blocks light
  in the strike's tick and go off 4 ticks after the rod).
- **Weathered rods are cleaned:** after powering it, the bolt turns a struck exposed,
  weathered or oxidized rod into a plain `lightning_rod` with the same state; waxed rods
  stay as they are (EXP-066). The new block keeps the power and schedules its own 8-tick
  turn-off (the old block's tick no longer matches).
- **Moved while powered:** a piston moves a struck rod as it is; arriving as a new block
  it schedules a fresh 8-tick turn-off (EXP-066: struck at 4, pushed at 7, off at 17).
- Removed while powered, it updates the neighbors of the block behind it.

**The strike.** Weather is not simulated; the editor stand-in is a lightning bolt summoned
on top of the rod (`strike POS`, the inspector's "Strike with lightning"). A summoned bolt
acts in its first tick, the next tick's entity phase: it powers the rod in the block it is
in or just below (`powerLightningRod`). In the simulator the strike comes after projectile
hits and before plate and tripwire visitors (see [[differences]], section 3).

Not simulated: the bolt's fire (none on peaceful, the test server's difficulty), damage to
mobs, and its random walk that cleans copper blocks touching the struck one (it changes
nothing when no other copper block touches the rod).
