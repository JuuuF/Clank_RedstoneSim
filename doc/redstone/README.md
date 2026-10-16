# Redstone engineering knowledge base

What a builder needs to know to design working redstone in Minecraft Java **26.3**,
learned by experiment with the simulator's command line ([[cli]]) and kept reproducible.
The rest of `doc/` describes how the simulator is built (ported from the game's source,
[[mechanics/index]]) and how it was checked against the real game ([[experiments/index]]);
this part describes **how redstone behaves and how to use it**: rules, timings, circuit
building blocks with contracts, and the experiments behind them.

Start with [[timing]] (how long everything takes) and [[signals]] (what powers what),
then pick building blocks from [[circuits]].

## Pages

| Page | What it holds |
|---|---|
| [[timing]] | Measured delays, pulse lengths and durations of every component, in game ticks |
| [[signals]] | How power travels: sources, strong and weak power, wire, conductors, what activates components |
| [[components]] | Per component: inputs, outputs, state, timing, edge cases (rules extracted from the records) |
| [[circuits]] | The circuit library: validated primitives with their contracts (inputs, outputs, latency, reset, failure cases) |
| [[backlog]] | Open questions, hypotheses, the research roadmap |
| `records/R-NNN-*.md` | One record per experiment: question, hypothesis, setup, observations, conclusion ([[#Experiment records]]) |

Scripts: every record has a script in `experiments/redstone/R-NNN-*.cli.txt`, every circuit
one in `examples/circuits/NAME.cli.txt` (with the world it builds next to it, to open in
the editor). Each script makes its own world, builds, and ends with a `check` whose
targets state what was observed; `tests/cli/test_research.py` runs them all, so the
knowledge base fails loudly if the simulator ever stops behaving as written here.

## Scope and trust

- **Version:** Minecraft Java Edition 26.3, the version the simulator ports. Nothing here
  is claimed for other versions or for Bedrock Edition.
- **Authority:** the simulator reproduces the mechanics it implements exactly (ported
  from the decompiled source; 55 scenarios and 60 random circuits compared tick by tick
  with a real 26.3 server, [[experiments/index]]). An experiment here is therefore
  evidence about the game *for the mechanics the simulator implements*. What it does not
  implement (water, items on the ground, mobs, minecarts, light, randomness) is listed
  in [[differences]]; designs depending on those cannot be tested here.
- **Evidence labels** used on every page:

| Label | Meaning |
|---|---|
| **V** | Verified: observed in a RedSim experiment (record and script named) |
| **G** | Also confirmed in the real game on the 26.3 test server (EXP-NNN, [[experiments/index]]) |
| **S** | Source-confirmed: read in the decompiled 26.3 code (the mechanics page or class named) |
| **I** | Inferred: follows from verified rules, not isolated by its own experiment |
| **H** | Hypothesis: not tested yet (listed in [[backlog]]) |
| **L** | Simulator limitation: cannot be tested here ([[differences]]) |

## Vocabulary and conventions

- **Positions** `x y z`: +x east, +z south, +y up. Experiment worlds use the CLI's floor
  at y=0, so builds start at y=1.
- **Tick** means **game tick** (1/20 s). A *redstone tick* is 2 game ticks; this
  knowledge base never uses redstone ticks.
- **Tick T** (or "view T") is the world after tick T has run, including the edits
  recorded at T. An input "at T" (`at T use @L`, `pulse … at T`) happens *between* tick T
  and T+1, like a player acting; anything that reacts instantly is already visible at T.
- **Delay** (Δ) is the difference between the tick an input changes and the tick an
  output changes, as `delays FROM TO` measures it. "On at once" means Δ = 0.
- **Pulse length** is the number of consecutive ticks a value is on (`waves` shows one
  character per tick).
- **Directions:** repeaters, comparators and observers are written with `out=DIR`, the
  side their signal leaves (the game's `facing` points the other way).
- **Powered block** (a solid block such as stone): *strongly powered* if a lever,
  button, torch, repeater, comparator or observer powers it (it then also powers wire
  beside it); *weakly powered* if only wire powers it (it powers components but not
  wire). See [[signals]].
- **Order inside a tick** (doc/mechanics/tick-scheduling.md): scheduled ticks (by
  priority, then by the order they were scheduled), block events (pistons), entities,
  block entities (moving pistons, hoppers), then player actions. `trace T` and `step`
  show it.

## How to run and record an experiment

1. **Question and hypothesis** first, in the record (copy the template below).
2. **Script** `experiments/redstone/R-NNN-short-name.cli.txt`: first command
   `new size N force` (a fresh world), then the smallest build that separates the
   hypotheses: one row per variant, rows 2–4 blocks apart so they cannot touch (a block
   powered in one row must not be next to a component of another), every input and
   output labeled. Use `place` for components, `set` for floating structure. `settle`.
3. **Run it** in a scratch directory and look: `redsim-cli w.redsim.json < script`, then
   stimuli on the timeline (`at T use @IN`, `pulse @IN at T for N`), `run N`, `waves`,
   `changes`, `delays`, `trace T`, `step`. Use the finest resolution needed: `waves`
   for ticks, `trace` / `step` for the order inside a tick.
4. **Encode the observations as targets** (`target NAME do …`, `target NAME expect …`)
   and end the script with `check`. Add the script to the record with the observed
   `waves` or `changes` output. Run `pytest tests/cli/test_research.py`.
5. **Extract the rule** into [[timing]], [[signals]], [[components]] or [[circuits]], with
   its evidence label and a link to the record; add new questions to [[backlog]].

Pitfalls found while doing this (also in [[cli]] section 13):

- Rows must not share neighbors: a lever on the floor also strongly powers the floor
  block under it, and wire steps up and down diagonally to reach wire one block higher or
  lower unless a solid block above the lower wire cuts it.
- A probe wire next to a block only shows *strong* power; to see weak power use a lamp
  (or a repeater) as the probe.
- `waves` shows a redstone block as 0 (it shows what a block *receives*); probe what it
  powers instead.

### Record template

```markdown
# R-NNN: title

- **Date:** YYYY-MM-DD · **Simulator:** commit · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-NNN-….cli.txt` · **Status:** verified / partial / open
- **Question:** …
- **Hypothesis:** … (and why)
- **Setup:** rows, positions, orientations, initial states (a map if it helps)
- **Procedure:** stimuli and ticks
- **Observations:** waves / changes / trace output, tick by tick
- **Result:** expected vs observed
- **Conclusion:** the rule, its scope, confidence; what it rules out
- **Open:** caveats, follow-up questions (also in the backlog)
- **Used by:** pages and circuits that rely on it
```

## Experiment records

| ID | Title | Rules it established | Status |
|---|---|---|---|
| [[R-001-response-times]] | Response times of the basic components | [[timing]] base table | verified |
| [[R-002-what-powers-a-block]] | Which sources power a block, strongly or weakly | [[signals]] power rules | verified |
| [[R-003-short-pulses]] | Short pulses and short gaps into each component | [[timing]] short-pulse table | verified |
| [[R-004-wire-geometry]] | Wire shapes and what they power; steps up and down | [[signals]] wire rules | verified |

## Status

*2026-10-16:* knowledge base started: method, timing table, power rules. Next steps are
in [[backlog]].
