# Mechanics index

| Page | Topic | Research | Simulator | Verification |
|---|---|---|---|---|
| [[tick-scheduling]] | Tick phases, scheduled ticks, block events, block entities | researched | implemented (`sim/engine.py`, `sim/ticks.py`) | unit tests; game (timings in all EXPs) |
| [[neighbor-updates]] | Neighbor/shape updates, `setBlock` pipeline | researched | implemented (`sim/level.py`, `sim/neighbor_updater.py`) | unit tests |
| [[block-properties]] | Conductors, support faces, push reactions | researched | implemented for the initial block set (`world/shape.py`, `world/blocks/simple.py`) | unit tests; game (glass, EXP-007) |
| [[power-queries]] | Weak/strong power, signal queries | researched | implemented (`Level` signal methods) | unit tests; game |
| [[redstone-wire]] | Dust connectivity, power, update order | researched | implemented | unit tests; JDK oracle (hash order); game EXP-002…004, 007 |
| [[repeater]] | Delay, locking, priorities | researched | implemented (`world/blocks/diode.py`) | unit tests; game EXP-008…011 |
| [[comparator]] | Compare/subtract, side inputs, analog input | researched | implemented (containers pending) | unit tests; game EXP-012…014 |
| [[redstone-torch]] | Inversion, timing, burnout | researched | implemented (incl. burnout) | unit tests; game EXP-002, 004, 005, 006 |
| [[manual-sources]] | Lever, buttons, redstone block, lamp | researched | implemented | unit tests; game (lamp, redstone block) |
| [[pistons]] | Extension/retraction, QC, moved blocks | researched | implemented (`world/blocks/piston.py`) | unit tests; game EXP-015…020 |

Source locations for all of these: [[research/source-map]]. Quirks: [[quirks]]. Overall
state: [[project-state]].
