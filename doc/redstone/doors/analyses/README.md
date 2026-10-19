# Door analyses

One page per world of the dataset. The facts part of each page (between
`<!-- generated -->` markers) comes from `python -m tools.doorlab.report SLUG`: doorway
frames over time, groups by exit side, every piston that fires with its pulses and power,
phases. The **How it works** part is written by hand from those facts, `why` / causal
links and maps (`redsim-cli … show`), and says what is verified.

| World | Explained | Notes |
|---|---|---|
| [[3x3-piston-door-mumbo-jumbo]] | **yes** | double extender under the center; the spit made by pulling away the powering block ("power switch"); landing check |
| [[3x3-piston-door-zhus]], [[3x3-piston-door-monchicarp]] | **yes** (below) | the same design built twice |
| [[3x3-piston-door-rubik]] | facts | |
| [[3x3-piston-door-sacredredstone]] | **yes** | the whole door in one plane (48 blocks, the smallest); an observer-chain controller; a corner block blinks for 8 ticks because a lamp flickers within a tick (R-028, game EXP-075/076). The build has a comparator tick and two piston events pending at tick 0 |
| [[3x3-spiral-piston-door-purplers]] | facts | |
| [[3x3-spiral-vault-door-lutal]] | **yes** | showpiece vault wheel: two 8-block rings and a lit hub, 14 ticks each way; one 2-tick observer pulse per piston spits in / pulls out; the sweep is 1-tick repeater steps; the hub rides a stack with a wireless, landing-checked rider (delay 4 exact, R-026); four separator blocks; direction-independent |
| [[3x3-seamless-glass-door-nile]] | facts | built closed; pending piston event at tick 0; orientation-dependent from tick 59 (still works), [[../symmetry]] |
| [[3x3-flush-enchanting-table-door-purplers]] | facts | |
| [[3x4-piston-door-pal1]] | facts | no input section |
| [[4x4-piston-door-kwipla]] | **yes** | one-bit memory (a redstone block toggled by a sticky piston) turns one button into close / open; observer chains as the clock, two delay-4 repeaters giving push / pull pairs 8 ticks apart; furnaces as immovable caps that veto a wrongly timed lift (counterfactual-verified) |
| [[4x4-piston-door-sydney600mc]] | facts | same grouping as Kwipla's: 4 up, 4 down, 2×4 sideways in 2 moves |
| [[4x4-sliding-piston-door-purplers]] | **yes** | two 12-block slime / honey assemblies per half (skins of quartz), carried pistons for the second stroke, floor and ceiling retracted first to break adhesion, a controller of moving redstone blocks (spit chains, QC update relays); 5 one-change experiments |
| [[5x5-glass-piston-door-ashevoy]] | facts | the largest piston count of the 5x5s (171); 17-piston extender chains |
| [[5x5-vault-door-nile]] | facts | slime; opens and closes in 9 ticks |
| [[5x5-vault-lamp-door-purplers]] | **yes** | funnel door: 16 singles, 8 double extenders, a triple extender lowering a lamp lit by a carried redstone block; opens in 2 ticks (all 25 cells); the top line switched by a redstone block spat within tick 3; lifted-wool comparator / repeater timers; **jams in 2 of 8 orientations** (R-027, EXP-074) |
| [[1-wide-hidden-staircase-purplers]] | facts | not a door: a staircase; "Opened" = stairs out |
| [[7x7-piston-door-legden]], [[8x8-piston-door-legden]] | facts | do not open fully in the replay, which matches the 26.3 server (EXP-068): the build itself stops, the same at every position and orientation tried. 69 / 40 extensions move nothing: lost 0-tick pulses (36 / 25) and pushes into moving blocks (24 / 6) (backlog D3) |

## Zhus's and monchiCARP's 3x3: one design, two builds

Found with `python -m tools.doorlab.compare` (2026-10-18):

| Level | Similarity | Meaning |
|---|---|---|
| exact states | 0.37 | the builds look different |
| structure | 0.37 | (no dynamic properties) still different: the materials differ (iron + yellow wool vs white concrete) |
| abstract (blocks by simulator facts) | **0.79** | 46 cells agree, 5 / 7 differ: materials do not matter, the wiring is nearly the same |
| pistons only | **1.00** | the same 11 pistons after a quarter turn |
| behavior (door-block trajectories) | **9 of 9** | every door block moves at the same ticks through the same cells; identical frames |

Both close 14 ticks after the lever and open 14 ticks after it, with the same 10 spits
and 6 quasi-connected extensions. The two builds differ in materials and in a few cells of
the controller (one dropper more in monchiCARP's, one wire less). Which one came first,
or whether both follow a common tutorial, the data cannot say.

What the design does (from the facts pages of both; Zhus's doorway lies across x,
monchiCARP's across z): three
blocks leave north and two south (singles), one up, and three go **below** (one cell
down, two cells down, one down and one north), moved by 4 pistons including a sticky
piston stacked on a sticky piston under the center column.

Most of its pistons are **pulse-driven and rest retracted in both states**: closing gives
each one a 2-tick pulse (an observer, or a block an observer powers) that pushes its
block one cell into the doorway and **spits** it there; opening gives the same piston
another 2-tick pulse: it extends into the air gap and its retraction **pulls the block
back** (a sticky piston extending into air pulls the block beyond its head, R-015). Only
two singles hold their blocks with a long pulse (17 ticks). So the
door's state lives in where the blocks are, not in which pistons are extended, and
closing and opening are both runs of short pulses: 14 ticks each.
