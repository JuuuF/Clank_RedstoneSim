# Demonstration: the door lab on the project's own 3x3 door

The dataset's designs are third-party, so their derived worlds stay uncommitted. To show
the whole pipeline end to end with every artifact in the repository, it runs here on
`door_3x3`, the 3x3 flush door designed in this project (Q18, Q21; contract in
[[../circuits]], "3x3 flush door"; build `examples/circuits/door_3x3.redsim.json`).

```
PYTHONPATH=src python experiments/doors/door_3x3/annotate.py   # sections, lever pulls, markers
PYTHONPATH=src python experiments/doors/door_3x3/lab.py        # every tool, ~5 minutes
```

`annotate.py` adds what the door lab reads and the example lacks: the input section (the
test lever `@L`), the output section (the nine cells `@D00`–`@D22`), the lever pulled at 5
and 60 (the `lever` target's case) and markers "Opening" 5, "Opened" 37, "Closing" 60,
"Closed" 77. This door opens when its input is on (the dataset's doors close).
`lab.py` writes `experiments/doors/door_3x3/results.json`, the stripped mechanism and the
trimmed build (2026-10-18).

## Results

| Step | Tool | Result |
|---|---|---|
| Round trip | `canonical`, `replay` | canonical form and replay identical after save → load |
| Analysis | `analysis` | 10 pistons, 11 firing positions (B fires at home and raised): 10 door, 1 stack (A lifts B); open 37–67, closed 0–12 and 77–100; the markers hold |
| Exit groups | `analysis` | west 3 and east 3 (one move each), above 1 (the top, up 1), below 2 (C down 2; M down 1 and east 1) |
| Power access | `analysis` | 13 extensions: 5 block←wire, 3 wire, 2 block←wire by QC, observer, observer by QC, comparator, block←repeater |
| Mechanism split | `mechanism` | 23 pulses on the 11 positions, no same-tick order needed: **the stripped door moves identically** |
| Input timing | `inputs` | clean for **every** gap 1–70 between the pulls (the lockout); no dataset door is clean below 9 ([[robustness]]) |
| Two cycles | `inputs --repeat` | the second cycle identical, the same rest state |
| Symmetry | `symmetry` | identical in all 8 orientations and 4 one-block shifts: no direction or location dependence |
| Ablation | `ablation` | 420 variants (piston heads are not removed alone): 229 break, 17 timing, 79 internal, 95 inert. All 10 pistons, the lever, the torch, both observers needed |
| Trim | `ablation --trim` | 225 → 209 blocks above the floor, box 1768 → 1632; the trimmed build replays inert |
| Comparison | `compare` | with Mumbo Jumbo's 3x3: piston layout 0.83 (abstract, pistons only), whole build 0.03; no trajectory equal (opposite lever sense, other timing) |

### The contract

Read by `mechanism` from the door's piston events (`pulse POS at e−1 for r−e`; a piston
powered in the build has its pulse from the start):

| Pulse (extends → retracts) | Piston | Effect |
|---|---|---|
| build → 13 | the 6 side singles (x 5, x 11) and the top (8 8 2) | open: pull the edges into the wall |
| build → 17 | B (8 2 2) | pull M down into the floor |
| build → 21 | W (10 3 2) | pull M east, out from under C |
| 23 → 31 | A (8 1 2) | lift B one cell; set it down |
| 26 → 27 | B raised (8 3 2) | a 1-tick pulse: pull C down one |
| 34 → 37 | B | pull C into the floor (open at 37) |
| 68 → end | the 7 singles | close the edges |
| 68 → 70 | B | spit C up one (a 2-tick pulse) |
| 68 → end | A | its push fails on the moving B (R-026), harmless |
| 72 → end | W | push M under C |
| 75 → end | B | push M and C up: closed at 77 |

Any controller that gives these pulses (in this order) runs the mechanism. The table is
also the specification for a smaller or faster controller (Q21: 26 of the 32 opening
ticks go to this sequence).

## What the comparison says

Mumbo Jumbo's door ([[analyses/3x3-piston-door-mumbo-jumbo]]) and `door_3x3` solve the
flush 3x3 the same way: singles on the sides and top, a double extender under the
center and one sideways floor piston (piston layouts 83% equal). The differences are in
the controller:

| | Mumbo Jumbo | `door_3x3` |
|---|---|---|
| Blocks above the floor (trimmed) | 87 (78) | 225 (209), with test buttons and the lockout |
| Box above the floor | 189 | 1768 |
| Close | 10 ticks | 17 ticks |
| Open | 24 ticks | 32 ticks (28 without the lockout) |
| Shortest safe gap between the pulls | 10 ticks (gaps 2–9 jam; one more cycle repairs 2 and 7–9, not 3–6) | any |
| Same in all orientations and positions | yes | yes |
| Center block's way down | P1 pulls it down one, P2 lowers P1, P1 pulls again | B pulls it down one, A lowers B, B pulls again |

The trade-off is the one [[patterns]] names: Mumbo Jumbo's controller is compact and
fast but trusts its user to wait; `door_3x3` spends ticks and blocks on a lockout that
makes every input timing safe. A lockout in front of Mumbo Jumbo's mechanism, built to
its 14-pulse contract ([[mechanism]]), would combine both (backlog D6).
