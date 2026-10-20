# Brief: the contraption graph (a machine-traversable representation of a door)

> A follow-up brief to the piston-door mission ([[mission]], section 5: "a practical,
> machine-traversable representation inspired by an AST, but do not force Minecraft into
> a conventional tree structure"). Written 2026-10-20 after the mission's last session.
> Working rules for every mission: [[../../agents/README]]. The live state of the door
> research: [[README]]. Keep this page's section 8 current (status and handoff).

## 1. Role and goal

You are an autonomous redstone reverse engineer and knowledge-system architect working on
RedSim, a Minecraft Java 26.3 simulator, through `redsim-cli` and the door lab
(`tools/doorlab/`). The door research has three layers of representation
([[representation]]): a lossless canonical world, derived interactions, and inferred
knowledge. Each layer exists, but as separate tools that each recompute their own view
and hand it back as their own data. The explanations of the 19 doors are prose
([[analyses/README]]).

Your goal is **one graph per door** that ties the three layers together, can be walked
by a program, and answers questions about the door without re-running the tools:
*which blocks does this piston depend on, and from which tick; which blocks make up
the wire cutter; what does this read feed; what breaks if this cell becomes glass; which
abstractions share this block.* The graph is written from what the existing tools
already compute, tested by reproducing their results from the graph alone, and then
extended with the hand-written explanations as abstraction nodes.

Everything you add is computed by the simulator's own code or marked as inferred; the
canonical data stays untouched below it. A rule you don't know is recorded as
unresolved, never approximated silently.

## 2. Rules that bite here

Read [[../../agents/README]] first; these are the ones this task runs into:

- **`data/` is the owner's and read-only**; the 19 worlds are third-party designs.
  Graphs and results derived from them go to `.sandbox/doors/graph/` (git-ignored) and
  are never committed. The project's own door, `experiments/doors/door_3x3/`, is the one
  world whose graph is committed, next to its other results.
- **Never change the simulator to make something fit.** If a relation you need is not
  observable, add an observability hook like `Level.signal_probe` (no game logic), and
  say so in the module's docstring.
- **Docs are the memory.** Each finished step is documented and committed at once:
  the page [[graph]] (new, the schema and the queries), the tools table in [[README]],
  the layer description in [[representation]], and section 8 of this page. Push after
  every commit (`git push origin HEAD`); `git push origin HEAD:main` when
  `pytest tests/doorlab` and `ruff check` pass.
- **Branch**: `research/door-graph`, from `main`.
- **Quota**: filter what you print; run sweeps in the background and write their output
  to files; sub-agents only for a whole step with a short report.
- **Time**: the owner sets a hard end time per session. Before it, and before the quota
  runs out, everything found is committed and section 8 is current.

## 3. What exists (do not redo)

The sources the graph is assembled from, all in `tools/doorlab/`:

| Source | Layer | What it gives you |
|---|---|---|
| `canonical.from_file(path)` (`rebuild`, `to_save`) | 1 | blocks with full state text, block entities, pending engine state, timeline, sections and markers; lossless |
| `interactions.pistons(level)` | 2 static | per piston: `would_move`, `would_break`, `movable_now`, `neighbors` (the positions that can switch it, quasi-connectivity included) |
| `interactions.block_facts` | 2 static | per block: conductor, push reaction, role |
| `replay.record(document, causes=True)` → `Recording` | 2 dynamic | `events` (`PistonEvent`: tick, order, kind, `moved` with origin → dest, failure, power note), `changes` per tick, `links` (`Link`: a block change and its cause with `via` = update / tick / event / moved) |
| `power.trace_reads(document)` → `list[Read]` | 2 dynamic | every positive signal read: tick, asker, kind, target and its origin cell, value, `alt`, context (update / event / tick), `sources`, `update_from`; `Read.decisive`, `Read.queues` |
| `power.read_graph`, `power.reaches` | 2 → 3 | the time-collapsed graph of signal and update links used for D13 (in memory only, untyped edges) |
| `power.glass_effect`, `power.predict`, `power.roles` | 3 | the glass counterfactual per cell: which readers change, from which tick; the verdict (read / dead end / stopper / support / falling / none) |
| `analysis.analyze(path)` | 3 | tokens (door blocks' trajectories), exit groups, piston roles (door / stack / power mover / power switch / helper), pulses, power access, phases |
| `mechanism` | 3 | the mechanism / controller split, the contract (pulses per piston), `carried` |
| `ablation` results `.sandbox/doors/ablation/<slug>.json` (if present; regenerate with `python -m tools.doorlab.ablation WORLD`, slow) | 3 | the outcome of every one-block change: breaks / timing / internal / inert |
| `experiments/doors/patterns.json`, [[patterns]] | 3 | the mechanism census per world (counts, not instances) and the 13 mechanisms with the worlds that show them |
| [[analyses/README]] and the 19 pages | 3 | hand-written "How it works" sections with one-change experiments; the claims you turn into abstraction nodes |
| [[robustness]], [[mechanism]], [[metrics]], [[creators]] | 3 | the input contract per door, jams, the contract tables, the objectives, creator attribution |

Records of game-verified mechanics that edges may cite: `doc/redstone/records/`
(R-026 push into a moving block, R-027 double-extender order, R-029 pull meets a
moving block) and the experiments index `doc/experiments/index.md` (EXP-068 to EXP-080).

## 4. The deliverable

A module `tools/doorlab/graph.py` that builds, saves, loads and queries the graph, and
a page [[graph]] that documents its schema with examples from `door_3x3`.

### 4.1 Shape

A directed multigraph with typed nodes and typed edges. Not a tree: cycles (feedback,
wire loops), shared paths (one conductor feeding several pistons) and overlapping
membership (a block in two mechanisms) are normal.

**Nodes** (each with `id`, `kind`, `layer`, and its data):

| Kind | Layer | Identity | Data |
|---|---|---|---|
| `cell` | 1 | position | the block there at tick 0 with its full state; block entity if any |
| `component` | 2 | the block built at a cell (follows the block when a piston moves it) | type (piston, wire, repeater, …), facing, the facts from `block_facts` |
| `piston` | 2 | position of the base at tick 0 | sticky, facing, the static `Piston` record, its role from `analysis` |
| `token` | 3 | a moved door block (from `analysis.track`) | trajectory: cell per tick range, exit group |
| `event` | 2 | a `PistonEvent` (tick, order, piston) | kind, moved list, failure, power note |
| `input`, `output` | 1 | from the world's sections | the lever / button; the doorway cells |
| `abstraction` | 3 | a name and its world | see 4.3 |
| `evidence` | 3 | a record or experiment id | R-0xx, EXP-0xx, an ablation result, a one-change experiment |

**Edges** (each with `kind`, `from`, `to`, `layer`, `status`, `when`, `source`):

| Kind | Layer | Meaning | `when` |
|---|---|---|---|
| `adjacent` | 2 static | the cells touch | always |
| `can_power` | 2 static | this position can switch that piston (`Piston.neighbors`), QC marked | by state: the condition under which it holds |
| `powers` | 2 observed | a read: asker ← target, with value, `alt`, decisive, context | the tick |
| `updates` | 2 observed | the change of this cell caused an update read there (`Read.update_from`, `Link.via == "update"`) | the tick |
| `causes` | 2 observed | a `Link`: this change caused that change, with `via` | the tick |
| `moves` | 2 observed | an event moved this block from origin to dest | the tick |
| `carries` | 2 static+observed | a sticky piston and the block it holds / a stack piston and the piston it lifts | tick ranges |
| `supports` | 2 static | this block keeps that one in place (`can_survive`) | by state |
| `member_of` | 3 | a cell, component, piston or token belongs to an abstraction | tick ranges if the role is temporary |
| `evidence_for` | 3 | an evidence node supports an abstraction or an edge | — |
| `unresolved` | any | a relation you expected but could not establish; the note says what is missing | — |

`status` is one of `possible` (static, from the simulator's tables), `observed` (from
the replay or the reads of the designed run), `inferred` (from an analysis tool or a
hand-written claim), `verified` (an `evidence_for` edge from a game check exists).
`source` names the tool and function that produced the edge. `when` is in the
simulator's native ticks (`doc/cli.md` section 5), a single tick, a list of ticks or a
range; never a word like "fast".

Never conflate the kinds: adjacency is not power, `can_power` is not `powers`, and
`powers` is not proven causal influence (that is `causes` or an `evidence_for` edge).

### 4.2 Storage and API

- One JSON file per world: `.sandbox/doors/graph/<slug>.json`; `door_3x3`'s at
  `experiments/doors/door_3x3/graph.json` (committed). Deterministic order (sorted
  nodes and edges), so a diff is readable and a rebuild is comparable.
- `build(path) -> Graph`, `save`, `load`.
- Queries, each a function with a docstring and a test:
  `neighbors(node, kind=None, tick=None)`, `upstream(node, kinds, tick)` (what feeds
  it, following `powers` / `updates` / `causes` backwards), `downstream` (what it feeds),
  `members(abstraction)`, `abstractions_of(node)`, `at(tick)` (the sub-graph of what
  holds at that tick), `why(event)` (the chain from the event back to the input, the
  door lab's `why` for a piston), `without(cells)` (the sub-graph with those cells
  removed: the static part of a counterfactual).
- A CLI: `python -m tools.doorlab.graph WORLD [--build] [--query NAME ARGS] [--stats]`.

### 4.3 Abstractions

An abstraction node carries exactly what [[mission]] section 5 asks for:

```
name            "wire cutter"            (a mechanism of [[patterns]], or a new one: say so)
instance        "3x3-piston-door-mumbo-jumbo / helper piston 4 3 -3"
members         member_of edges (cells, components, pistons, tokens; overlap allowed)
preconditions   what must hold for it to work (state, timing), in ticks
function        one sentence: what it does for the door
limitations     what breaks it (from the ablation / input sweep), in ticks
evidence        evidence_for edges: EXP-/R- ids, ablation results, one-change experiments
creator         the world's creator as recorded in its title (never beyond that)
status          inferred | verified
```

The source for the first instances is the "How it works" section of each analysis
page. Encode every claim that names blocks; a claim you cannot pin to blocks and ticks
becomes an `unresolved` edge with the sentence as its note, not a guess.

## 5. Validation (the acceptance tests, `tests/doorlab/test_graph.py`)

The graph is right when it reproduces, **from the saved JSON alone**, what the tools
computed:

1. **Round trip**: build → save → load → save gives identical bytes; building the graph
   twice gives identical files (determinism).
2. **The contract**: the pulses per piston of [[mechanism]] (the `mechanism` entry of
   `experiments/doors/door_3x3/results.json` for the committed case) fall out of the `event` nodes and `moves` edges.
3. **The glass verdicts**: for every cell, `power.predict`'s verdict is recomputed by a
   graph query over `powers` / `updates` / `supports` edges (281 of 282 breaking
   variants, "none" exact: [[representation]] "Does layer 2 predict a change?").
4. **The exit groups**: the `token` nodes' trajectories give [[analyses/README]]'s groups.
5. **Symmetry**: the graph of the turned / mirrored world (`transform.py`) is the graph
   of the original with positions transformed, edge for edge.
6. **Abstractions**: for `door_3x3` and at least three dataset doors (Mumbo Jumbo's wire
   cutter and power switch, Zhus's spits, Nile's built-in lockout), every block named
   in the explanation is a member of the right abstraction, and `why(event)` of the
   door's first opening event ends at the input node.

Test 3 is the one that tells you whether the edge kinds are complete; if a verdict
cannot be reproduced, the missing relation is a finding (write it down), not a reason
to copy the tool's answer into the graph.

## 6. Steps, in order

Commit after each; the first four are assembly work, the fifth is the real work.

1. **Schema and `door_3x3`** (the committed case): `graph.py` with `build`, `save`,
   `load`, the node and edge kinds of 4.1 from layers 1 and 2 only; [[graph]] with the
   schema; tests 1 and 2.
2. **Reads and counterfactuals**: `powers`, `updates`, `causes`, `supports` edges from
   `power.trace_reads` and `replay`; the queries of 4.2; test 3 for `door_3x3`, then
   all 19 (in the background, results to `.sandbox/doors/graph/`).
3. **Layer 3 from the tools**: `token` nodes, piston roles, the census mechanisms as
   abstraction instances where the tools already identify members (`analysis`,
   `patterns`, `mechanism.carried`); tests 4 and 5.
4. **The reach, with time** (D13 in [[README]]): with `when` on every edge, redo the
   reach from a changed reader to the mechanism pistons at the tick it changes, add the
   missing edge kinds found on the way (shape updates: observers and note-block BUDs;
   wire shapes changed by moved blocks). Report how many of the 36 dead ends it
   explains. Stop after one honest attempt if it does not move (rule 7).
5. **Abstractions from the explanations**: encode the four doors of test 6, then as
   many of the remaining 15 as fit, each with its evidence edges; the unresolved claims
   listed in [[graph]] as the next agent's work.
6. **Use it once**: answer one question of [[README]]'s open items with a graph query
   rather than a new tool (for instance D4's same-tick order from `event` order and
   `carries` edges), and write the answer where that item lives.

## 7. Traps

- `python -I` ignores `PYTHONPATH`; run the lab's modules with
  `PYTHONPATH=src python -m tools.doorlab.graph …`.
- A foreground command has a 10-minute limit; the full ablation of a door takes longer:
  reuse `.sandbox/doors/ablation/<slug>.json` where it exists, and run the rest in the
  background with output to a file.
- `Level.signal_probe` is read on the class, not the instance (a function stored on a
  class attribute would otherwise be bound). `trace.current_cause` is a property;
  `Direction.clockwise()` is a method, not a property.
- The reads of a tick happen in the middle of it; the replay's `changes` are the state
  at the boundary. An edge's `when` says which (the `Read.context` field).
- A moved block keeps its `component` identity; its cell changes. Index by origin cell
  as `power.py` does (`Read.origin`), and record the cell per tick range.
- The 7x7 and 8x8 doors (`broken_doors/`) are out of the pool by the owner's rule:
  build their graphs if cheap, never investigate them.

## 8. Status and handoff

Not started (2026-10-20). The first step is section 6, step 1, on `door_3x3`.
