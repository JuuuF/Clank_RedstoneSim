# Mechanics index

| Page | Topic | Research | Simulator | Verification |
|---|---|---|---|---|
| [[tick-scheduling]] | Tick phases, scheduled ticks, block events, block entities | researched | implemented (`sim/engine.py`, `sim/ticks.py`) | unit tests; game (timings in all EXPs) |
| [[neighbor-updates]] | Neighbor/shape updates, `setBlock` pipeline | researched | implemented (`sim/level.py`, `sim/neighbor_updater.py`) | unit tests |
| [[block-properties]] | Conductors, support faces, push reactions | researched | implemented for the initial block set (`world/shape.py`, `world/blocks/simple.py`) | unit tests; game (glass, EXP-007) |
| [[power-queries]] | Weak/strong power, signal queries | researched | implemented (`Level` signal methods) | unit tests; game |
| [[redstone-wire]] | Dust connectivity, power, update order | researched | implemented | unit tests; JDK oracle (hash order); game EXP-002…004, 007 |
| [[repeater]] | Delay, locking, priorities | researched | implemented (`world/blocks/diode.py`) | unit tests; game EXP-008…011 |
| [[comparator]] | Compare/subtract, side inputs, analog input | researched | implemented | unit tests; game EXP-012…014 |
| [[redstone-torch]] | Inversion, timing, burnout | researched | implemented (incl. burnout) | unit tests; game EXP-002, 004, 005, 006 |
| [[manual-sources]] | Lever, buttons, redstone block, lamp | researched | implemented | unit tests; game (lamp, redstone block) |
| [[pistons]] | Extension/retraction, QC, moved blocks | researched | implemented (`world/blocks/piston.py`) | unit tests; game EXP-015…020, 047 (scheduled-tick pulses) |
| [[rails]] | Rail shapes, powered/activator rail propagation (8 rails) | researched | implemented (`world/blocks/rail.py`; no detector rails) | unit tests; game EXP-031, 035, 036 |
| [[observer]] | Shape-update detection, 2-tick pulses, observer clocks | researched | implemented (`world/blocks/observer.py`) | unit tests; game EXP-031..034 |
| [[target-block]] | Target block: dust connection, projectile hits (20/8 ticks), hit strength | researched | implemented (`world/blocks/target.py`; hits are an editor action) | unit tests; game EXP-031, 037 |
| [[hopper]] | Hopper item transfer (8-tick cooldown, 7-tick rule), locking, comparator output | researched | implemented (`world/blocks/hopper.py`; block containers only) | unit tests; game EXP-031, 038..041 |
| [[analog-sources]] | Barrel (container fill), lectern (book page, page-turn pulse), cake | researched | implemented (`world/blocks/container.py`, `lectern.py`, `cake.py`) | unit tests; game EXP-012/013, 024, 025 |
| [[note-block-and-copper-bulb]] | Note block (instrument, block event), copper bulb (T flip-flop) | researched | implemented (`world/blocks/note_block.py`, `copper_bulb.py`) | unit tests; game EXP-042, 043 |
| [[dispensers-and-chests]] | Dispenser/dropper (QC, 4-tick delay, random slot), chests (double, blocked), trapped chest | researched | implemented (`world/blocks/dispenser.py`, `chest.py`; dispense effects not simulated) | unit tests; game EXP-044, 045 |
| [[pressure-plates]] | Stone/wooden/weighted plates with entities as editor "visitors" | researched | implemented (`world/blocks/pressure_plate.py`) | unit tests; game EXP-046 |
| [[composter-and-signs]] | Composter (levels, 7→8 after 20 ticks, hopper takes bone meal); standing and wall signs (support, piston-blocking, text) | researched | implemented (`world/blocks/composter.py`, `sign.py`) | unit tests; game EXP-048, 049 |
| [[gravity-blocks]] | Sand, gravel, concrete powder, anvils, dragon egg; falling block entities (physics, collision, landing, plates, pistons pushing and launching them) | researched | implemented (`world/blocks/falling.py`, `sim/entities.py`) | unit tests; game EXP-054, 055 (positions and motion compared) |
| [[campfire]] | Campfires: signal fire from a hay bale (observers see it), immovable (block entity), food cooking and cooling | researched | implemented (`world/blocks/campfire.py`) | unit tests; game EXP-056 |

Source locations for all of these: [[research/source-map]]. Quirks: [[quirks]]. Overall
state: [[project-state]].
