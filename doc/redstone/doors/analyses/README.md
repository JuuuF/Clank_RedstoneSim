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
| [[3x3-piston-door-rubik]] | **yes** | one-plane flush 3x3; observers on a note block give one 2-tick pulse train for both directions (spit in / pull out); Mumbo Jumbo's center layout with a delay-4 repeater whose stretched 8-tick pulse is exact (R-026); the bottom-middle door block conducts the controller's pulse to the lifted piston; the stripped door fails via the x = −12 piston column (D4) |
| [[3x3-piston-door-sacredredstone]] | **yes** | the whole door in one plane (48 blocks, the smallest); an observer-chain controller; a corner block blinks for 8 ticks because a lamp flickers within a tick (R-028, game EXP-075/076). The build has a comparator tick and two piston events pending at tick 0 |
| [[3x3-spiral-piston-door-purplers]] | **yes** | showpiece in two layers (168 cells, 81 blocks): one 2-tick observer pulse per piston on both lever edges, so the spiral fills and empties in the same loop; 20 observers watching observers, a note block and a lamp as conductor-plus-observable; a sliding observer as the direction switch; the lamp's 4-tick turn-off gives the stack its second stroke; gap 11 alone loses the first opening pulse (R-026) |
| [[3x3-spiral-vault-door-lutal]] | **yes** | showpiece vault wheel: two 8-block rings and a lit hub, 14 ticks each way; one 2-tick observer pulse per piston spits in / pulls out; the sweep is 1-tick repeater steps; the hub rides a stack with a wireless, landing-checked rider (delay 4 exact, R-026); four separator blocks; direction-independent |
| [[3x3-seamless-glass-door-nile]] | **yes** | every piston inside the door columns: a self-carrying stack shifted 4 down (pushes 10 / 14 / 18 / 21, tidy pulls to 40) and back up by an inchworm (pushes 54–77, same-tick pulls); wall rows read by quasi-connectivity with arranged updates; an observer chain and a redstone-block shuttle clock; the alternating glass is a 2-tick pulse that spits or pulls depending on what is in front (EXP-073); built closed with a pending piston event; location-dependent at tick 59 (harmless, EXP-070) |
| [[3x3-flush-enchanting-table-door-purplers]] | **yes** | built around an immovable table: the door stores as floor and wall; one redstone dust in two droppers as the memory bit (comparator → torch tower); carried pistons for the top row's 3-cell reach; moved observers as switches; obsidian caps and the oak button's 30 ticks as timing (counterfactual-verified); simulator-only after the first cycle (D9) |
| [[3x4-piston-door-pal1]] | **yes** | one plane, 2 deep: Mumbo Jumbo's center solution from both floor and ceiling (two double extenders, two floor pistons); observer chains on both lever edges, hoppers and note blocks as relays; a parked observer slider and two repeaters as the timer for the last pull (quasi-connectivity is one-way, so the mirrored top needs it); 3 one-change experiments; no input section |
| [[4x4-piston-door-kwipla]] | **yes** | one-bit memory (a redstone block toggled by a sticky piston) turns one button into close / open; observer chains as the clock, two delay-4 repeaters giving push / pull pairs 8 ticks apart; furnaces as immovable caps that veto a wrongly timed lift (counterfactual-verified) |
| [[4x4-piston-door-sydney600mc]] | **yes** | Kwipla's mechanism three blocks deep: a lever door using both edges of one level (observer chains, hoppers as lockable relays, a one-item dropper / hopper timer giving the 7-tick stack pulse, a lifted observer as off-edge detector); the parked door block carries power to the moved pistons; the hopper caps the column; the safe gap is set by the stacks' return, quick flips lose edges to busy observers |
| [[4x4-sliding-piston-door-purplers]] | **yes** | two 12-block slime / honey assemblies per half (skins of quartz), carried pistons for the second stroke, floor and ceiling retracted first to break adhesion, a controller of moving redstone blocks (spit chains, QC update relays); 5 one-change experiments |
| [[5x5-glass-piston-door-ashevoy]] | facts | the largest piston count of the 5x5s (171); 17-piston extender chains |
| [[5x5-vault-door-nile]] | **yes** | stepped vault (ring, inner square, center at three depths); honey and slime elevators with riding pistons that pick up outer rows; the lever is only an update (on glass); a bounced redstone block as a sub-tick pulse; leaves, bulbs, hoppers and note blocks as observed indicators; a piston head across the trigger's path is a built-in input lockout (gaps 1–12 ignored, not jams); 9 ticks each way |
| [[5x5-vault-lamp-door-purplers]] | **yes** | funnel door: 16 singles, 8 double extenders, a triple extender lowering a lamp lit by a carried redstone block; opens in 2 ticks (all 25 cells); the top line switched by a redstone block spat within tick 3; lifted-wool comparator / repeater timers; **jams in 2 of 8 orientations** (R-027, EXP-074) |
| [[1-wide-hidden-staircase-purplers]] | **yes** | not a door: a staircase hidden in a floor, "Opened" = stairs out; four row swaps (recess · shaft · store) with lifters, two fillers are sticky pistons that lift after a landing check; one clock edge fanned out by a ladder of repeater delays, a 2+4 hold chain brings the stairs back last; the bad gaps 8–9 drop the last lift; the frames cannot tell a stair from a filler |
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
