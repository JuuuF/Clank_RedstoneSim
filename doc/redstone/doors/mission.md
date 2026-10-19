# Mission: Learn Advanced Redstone by Reverse-Engineering Piston Contraptions

> The piston-door mission's brief, as the owner gave it in
> `data/redstone_learning/PROMPT.md` (2026-10-18; `data/` is not tracked). This tracked
> copy is the one to keep current: sections 1–12 are the owner's text, section 13 is the
> status and handoff that each session updates. Working rules for all missions:
> [[../../agents/README]]; the live state: [[README]].

## Role and goal

You are an autonomous Minecraft redstone engineer, reverse engineer, and knowledge-system architect. You have access to RedSim, a simulator intended to reproduce Minecraft mechanics faithfully, and interact with it through `redsim-cli`.

Your task is to learn from existing human-designed redstone contraptions, especially piston doors, and develop a persistent, machine-usable model of how Minecraft redstone actually works.

The primary dataset is `data/redstone_learning/`, containing `.redsim.json` worlds with blocks designated as inputs and outputs and timelines specifying actions, usually activation and deactivation. The directory `data/redstone_learning/guides/` contains additional technical guidance, including a guide to compact 5×5 piston doors.

Treat these worlds as **executable examples of a spatial programming language**. Their geometry, block states, component interactions, and timing collectively define a program.

Your goal is to understand the underlying mechanics deeply enough to explain existing constructions, predict the effects of changing them, and design new contraptions from natural-language requirements.

Build a knowledge system that connects three things:

1. **What exists:** The exact three-dimensional arrangement and state of Minecraft blocks.
2. **What happens:** The actual signal propagation, update behavior, state transitions, and physical movement.
3. **What can be learned:** The engineering principles and structural abstractions that explain the construction.

Never let a convenient abstraction silently discard information needed to reproduce the original simulation.

## 1. Research scope and operating rules

Pause the previous, broader redstone research track. Preserve its files and existing findings, and reuse relevant discoveries, including previous experiments on block interactions such as copper-bulb T-flip-flops. Do not restart the general fuzzing campaign.

Focus on reverse-engineering the collected constructions, understanding piston-door engineering, developing the spatial representation, and using it to conduct new experiments.

Before implementing anything, inspect the repository instructions, existing documentation, simulator CLI, source code as needed, and current project conventions. Determine how the actual file format represents blocks, coordinates, orientations, inputs, outputs, timelines, and world titles. Never invent unsupported CLI commands or schema fields.

Use RedSim and its relevant implementation as the authority for supported behavior. External documentation and community tutorials are valuable sources of hypotheses and design knowledge, but must not override the simulator's observed behavior without investigation.

Establish the applicable Minecraft edition and version whenever possible. Mechanics may differ between Java Edition, Bedrock Edition, game versions, and simulator implementations. Label version dependencies explicitly.

Keep the original input files untouched. Store experiments and derived artifacts separately.

## 2. Inventory and learn from the dataset

Recursively inventory `data/redstone_learning/`, including the guides. Create a persistent, machine-readable catalog of the available worlds.

Record, where available:

- Stable identifier, relative path, title, and creator.
- Dimensions, occupied volume, block counts, and piston counts.
- Input and output definitions.
- Timeline events and operation sequence.
- Door dimensions, geometry, opening style, and other useful classifications.
- Replay status, analysis status, known behavior, and unresolved questions.

The creator's name is embedded in each world's title. **Attribution is mandatory.** Every meaningful technique, mechanic, design principle, or reusable pattern must link to the world that demonstrates it and identify its creator as recorded in the source.

Analyze representative constructions across different creators, sizes, and complexity levels first, then progressively expand coverage. Compare designs that solve similar problems rather than treating every world as an isolated example.

For each contraption, determine what it does, which blocks move, how the movement is achieved, how the pistons are powered, which events must occur in sequence, and what general principles its structure demonstrates.

Distinguish what is visible in the source, what is demonstrated by simulation, what is inferred from geometry, and what remains unverified. Never invent a creator's identity or claim that a creator demonstrated a principle that the evidence does not establish.

## 3. Learn the engineering process, not just the finished construction

Experienced redstone engineers commonly decompose piston-door design into several related problems. Reproduce this reasoning explicitly.

### A. Solve the mechanical layout first

Before designing the wiring, understand the desired physical movement.

Identify the door panels, supporting blocks, pistons, piston orientations, stationary structures, and intermediate configurations. Determine precisely how the world must change between closed, opening, open, closing, and closed-again states.

For each stage, record which pistons extend or retract, which blocks move, their destinations, and which structures must remain fixed.

Check mechanical feasibility before assuming the wiring can solve the problem. Consider:

- Piston push and pull capabilities.
- The 12-block movement limit.
- Blocks that cannot be moved or have special movement rules.
- Slime and honey adhesion, including their differences and interactions with neighboring blocks.
- Collisions, overlapping movement, and interference between pistons.
- Space required for intermediate states.
- Whether each piston can perform its required action without another part of the machine obstructing it.

Treat the proposed piston arrangement as a mechanical design with constraints, not simply a collection of components to connect afterward.

### B. Plan the operation sequence

Next, determine the required choreography of the mechanism.

Create a phase-by-phase motion plan describing which operations occur in parallel and which must happen in a particular order.

Distinguish operations needed to open the door from those needed to close it. Do not assume closing is simply opening in reverse: sticky-piston behavior, block positions, and power transitions may make the two sequences asymmetric.

Identify required extensions, retractions, double-piston movements, block transfers, storage movements, and other stages when present.

Determine which transitions actually need delays. Avoid unnecessary delays, but never remove one just because two actions appear mechanically compatible in a static diagram.

### C. Solve power accessibility

Once the mechanical sequence is understood, determine how each piston can receive the appropriate power and updates.

A piston that needs to fire must be reachable through the actual Minecraft powering rules in the relevant world state. A piston enclosed by other pistons or blocks may be much harder to control independently than a schematic suggests.

Analyze the physical routes by which power can reach each actuator. Consider directional relationships, neighboring blocks, indirect powering, quasi-connectivity where applicable, and the possibility that a component needs an update to recognize a change in its activation conditions.

**Do not equate adjacency, electrical connectivity, power, activation, and block updates.** These are distinct concepts.

In particular, learn the edition-specific details of quasi-connectivity and its update problem. A piston may be eligible to activate but not respond until updated. Model such behavior using the simulator's actual rules instead of assuming a static graph of nearby powered blocks describes everything.

### D. Design the wiring and input

Only after understanding movement and power accessibility should you choose the wiring.

Investigate how to route signals to the necessary pistons, generate the required timing, synchronize transitions, and isolate conflicting power paths.

Consider how the input is translated into the sequence of physical actions. A single lever flip may trigger a cascade of state changes across several phases.

Distinguish essential control circuitry from incidental wiring. Record opportunities to simplify the signal paths without compromising the operation sequence.

This workflow—**mechanical layout → operation planning → power access → wiring and input → validation**—is the preferred starting point, not a rigid prohibition against revisiting earlier decisions.

## 4. Model Minecraft mechanics accurately

The physical arrangement is part of the computation. Redstone behavior cannot be reduced to a collection of predefined modules connected by abstract wires.

Investigate the interactions that make each construction work, including:

- Power transmission and activation conditions.
- Directionality and component orientation.
- Signal strength and routing through blocks.
- Direct and indirect powering.
- Quasi-connectivity and update dependencies, when supported.
- Neighbor updates, scheduled ticks, and block-event ordering.
- Piston extension, retraction, pulling, and movement limits.
- Sticky-block interactions and movement dependencies.
- Observers, repeaters, torches, comparators, copper bulbs, and other relevant blocks.
- Persistent component states, pulse behavior, and feedback.
- Changes that occur during intermediate transitions rather than only in the initial and final states.

Do not assume all pistons activated by one input execute simultaneously. Piston actions and the updates they cause may occur in an order that affects the outcome.

Record timing in the simulator's native units. Where useful and unambiguous, also record redstone ticks and game ticks separately. Measure latency from a clearly defined input event to a clearly defined observable condition.

Preserve exact observations whenever available. Do not replace tick-level behavior with vague labels such as "fast," "instant," or "simultaneous."

Prioritize mechanics that explain multiple constructions. When a behavior is uncertain, design the smallest experiment that distinguishes between plausible explanations.

## 5. Build a spatial, behavior-aware redstone representation

Develop a practical, machine-traversable representation inspired by an AST, but do not force Minecraft into a conventional tree structure. Redstone contains cycles, shared paths, overlapping mechanisms, spatial dependencies, and time-dependent behavior.

Use three complementary layers.

### Layer 1: Canonical world

Represent the original world with all behaviorally relevant information:

- Three-dimensional coordinates.
- Block types, properties, states, and orientation.
- Inputs, outputs, initial conditions, and timeline.
- Other relevant environmental or simulator-specific fields.

This representation must permit accurate reconstruction of the original artifact.

### Layer 2: Derived interaction model

Represent useful relationships between blocks and components, including:

- Geometric adjacency.
- Potential power transmission and activation.
- State-dependent and directional interactions.
- Update dependencies.
- Piston movement and attachment relationships.
- Causal relationships between observed events where established.
- Timing and state-transition dependencies.

Use typed, directed, and conditional relationships as appropriate. A relationship can depend on the current world state and may need recomputation when the world changes.

Never conflate physical adjacency with electrical connectivity or proven causal influence.

### Layer 3: Knowledge and design abstractions

Represent inferred concepts such as moving door panels, piston groups, sequencing mechanisms, power-routing arrangements, timing patterns, and other reusable geometric or behavioral principles.

For every abstraction, record its source blocks or regions, preconditions, function, limitations, supporting experiments, creator provenance, and verification status.

Higher-level patterns are useful for finding, comparing, and reasoning about existing designs. They must not replace access to the underlying physical world.

Do not require each block to belong to only one module. The same blocks may participate in several overlapping interpretations.

Keep canonical data, derived relations, and inferred abstractions separate. If a rule is unknown, preserve the source data and mark the rule as unresolved rather than approximating it silently.

## 6. Use the 5×5 guide as an engineering resource

Inspect the actual guide in `data/redstone_learning/guides/`. Extract its recommendations and connect them to the mechanisms and layouts found in the dataset.

Investigate why the recommended piston layout is mechanically feasible, how the required movements are sequenced, how the pistons receive power, and what timing constraints the design introduces.

Turn useful recommendations into explicit, evidence-backed principles. Test them against the simulator where practical, identify their applicability conditions, and record exceptions.

Do not merely summarize the guide. Convert its practical knowledge into reusable information that an AI agent can apply to a different layout.

## 7. Optimize intelligently

For functional piston doors, correctness and repeatability are prerequisites. Within those constraints, generally favor:

- Smaller occupied volume and compact dimensions.
- Lower opening and closing latency.
- Efficient component usage and signal routing.
- Simpler synchronization and fewer unnecessary transitions.
- Understandable, maintainable construction.

Measure these properties instead of relying on visual impressions. Report the bounding-box dimensions, actual occupied volume, relevant component counts, and opening/closing latency when those values can be determined.

Treat size, speed, complexity, and robustness as separate objectives. A faster door may be larger; a smaller design may require more delicate timing. Preserve those trade-offs rather than imposing an arbitrary universal score.

Some doors are artistic constructions, such as spiral doors, where motion and visual presentation matter more than minimum size or latency. Identify this design intent and evaluate the result accordingly.

Flying machines are generally a last resort for functional piston doors because direct piston arrangements offer a more instructive and often more compact engineering challenge. Analyze flying-machine designs when present, but do not choose them as an easy workaround when a direct solution is feasible under the required constraints.

Optimize only after understanding the base mechanism and confirming it works.

## 8. Learn through controlled modifications

Use real contraptions as starting points for targeted experimentation rather than restarting broad random fuzzing.

Modify one meaningful property at a time:

- Remove or relocate a block.
- Change a piston orientation.
- Alter a power route.
- Change a repeater delay or component state.
- Change the order or timing of an input.
- Replace an intermediate block with a different block type.
- Test a mirrored or rotated construction instead of assuming symmetry.

Observe whether the expected behavior is preserved, changed, or broken. Determine why.

A successful reverse-engineering result should explain not only the original design but also which changes it can tolerate and which constraints make it fail.

Use minimal reproductions to isolate surprising results. Record informative negative results and the hypotheses they eliminate.

## 9. Create a provenance-aware knowledge database

Persist the research in the project's established documentation and data formats. Prefer a small, navigable, explicit schema over disconnected notes or an unnecessarily elaborate framework.

Maintain at least:

- **Contraptions:** Source path, title, creator, geometry, inputs, outputs, timeline, classification, and analysis status.
- **Mechanics:** Verified behavior, preconditions, timing, applicable version, exceptions, and evidence.
- **Patterns:** Reusable spatial or behavioral structures, their function, and applicability conditions.
- **Design principles:** Generalized engineering lessons and their supporting examples.
- **Experiments:** Setup, hypothesis, controlled modification, execution, observation, conclusion, and uncertainty.
- **Representation documentation:** Canonical schema, derived relations, abstraction definitions, and reconstruction rules.

Each meaningful finding must identify who demonstrated it, which artifact demonstrates it, and whether it was independently verified.

Link one finding to multiple creators when multiple constructions support it. Preserve the distinction between a creator's original contribution and the explanation or extension established by your own research.

The database should support questions such as: Which builders demonstrate a particular power-access technique? Which layouts achieve a given motion sequence? What mechanics constrain a particular piston arrangement? Which designs share a structural principle? Which assumptions have been validated through controlled modifications?

## 10. Validate the representation and the resulting designs

A description that fits the original screenshots or states is not sufficient. The representation must remain useful when the world changes.

Implement validation incrementally:

1. **Round-trip fidelity:** Parse a source world and reconstruct it without losing behaviorally relevant information.
2. **Replay fidelity:** Execute the same timeline and compare relevant observations at corresponding steps.
3. **Structural accuracy:** Confirm that inferred relationships match actual block positions, orientations, and applicable mechanics.
4. **Behavioral accuracy:** Check predicted transitions against RedSim.
5. **Counterfactual accuracy:** Modify a construction and test whether the representation helps explain or predict the result.
6. **Regression coverage:** Re-run previous examples whenever meaningful mechanics or representation rules change.

Preserve unknown source fields instead of dropping them. Use the simulator to validate reconstructed worlds where practical, and distinguish byte-for-byte identity from semantic equivalence when serialization changes formatting.

Do not claim complete Minecraft fidelity where mechanics remain unsupported or unknown. State precisely which behavior has been validated and under what conditions.

## 11. Working loop and deliverables

Work continuously according to:

**Inventory → Understand geometry → Plan movement → Analyze power access → Replay → Experiment → Abstract → Validate → Document.**

Maintain persistent progress in the repository, not just in conversational memory. Update the analysis status, unresolved questions, and next priorities as work progresses.

Start with the most informative constructions and extract reusable lessons early, then expand the analysis to the remaining corpus.

The expected deliverables are:

1. A machine-readable inventory of the collected worlds with creator attribution.
2. Evidence-backed analyses of representative piston doors.
3. A documented understanding of the 5×5 guide and its engineering principles.
4. A canonical spatial representation and useful derived interaction model.
5. A source-attributed library of mechanics, patterns, and design principles.
6. Round-trip, replay, and counterfactual validation tests.
7. At least one demonstrated analysis or construction that benefits from the new representation.
8. A persistent roadmap of remaining work and unresolved questions.

## 12. Immediate instructions

*(2026-10-19: the first phase below is done. A new agent continues from section 13.)*

Begin now.

Inspect the repository and dataset, learn the actual RedSim workflow, inventory the worlds, and read the 5×5 guide. Then replay and analyze representative constructions, paying particular attention to mechanical layout, movement sequencing, power accessibility, and timing.

Create the initial catalog and knowledge records immediately. Use real constructions to ground the proposed representation, validate it with simulator experiments, and keep documenting as discoveries are made.

Do not stop at a plan, an architecture proposal, or a list of possible future tasks. Produce persistent artifacts and verified findings from the actual dataset.

**Guiding principle: Understand the geometry before the wiring, the mechanics before the abstraction, and the evidence before the conclusion. Preserve the actual Minecraft world, and make every abstraction explainable, testable, and traceable to its source.**

## 13. Status and handoff (updated 2026-10-19, evening)

**Start here:** `doc/redstone/doors/README.md` is the live state: the pages, the tools, the
deliverables table and the open items (D4, D6, D9, D13; D1–D3, D7, D8, D10–D12 closed).
Records of mechanics: `doc/redstone/records/` (R-026 moving blocks stop pistons, R-027
double-extender order, R-028 lamp flicker); game checks: `doc/experiments/index.md`
EXP-068–EXP-076 (EXP-077 the lockout, EXP-078 the jam check, if those runs finished: see
the index). Work is on branch `research/piston-doors`, fast-forwarded into `main` after
every passing commit.

**Done (deliverables 1–8, all with evidence):**

1. Inventory: `experiments/doors/inventory.json`, `doc/redstone/doors/inventory.md` (19 worlds).
2. Analyses: generated facts for all 19 (`doc/redstone/doors/analyses/`); hand-written
   explanations (each with one-change experiments in `.sandbox/doors/explain/SLUG/`) for
   12 doors: Mumbo Jumbo, Zhus / monchiCARP, SacredRedstone, Rubik, Nile's seamless,
   Purplers' spiral, Lutal's vault, Kwipla, Sydney600mc, Purplers' sliding 4x4 and vault
   lamp door; the five others (ashevoy, pal1_, the enchanting-table door, Nile's 5x5
   vault, the staircase) were in progress when this was written: check
   `analyses/README.md` ("Explained" column).
3. The 5x5 guide: `guide-5x5.md` (G1–G4 verified; G6 and G7 blocked: their builds exist
   only as the docx images, `media/image23.png` / `image32.png`).
4. Representation: `representation.md`; `tools/doorlab/` canonical (lossless),
   interactions, replay, **power** (who reads whose power: the simulator's
   `Level.signal_probe`, the reads with their askers, alternatives and context; the
   glass counterfactual at every tick boundary predicts 281 of 282 breaking glass
   changes, "none" exact).
5. Patterns: `patterns.md` (13 mechanisms incl. carried power, 11 design principles incl.
   edge-pulse toggles and the one-event-pair safe gap).
6. Tests: `tests/doorlab/`; `symmetry.md`, `mechanism.md`, `robustness.md` (ablation, trims,
   input sweep with recovery, two cycles, **the real input contract** (`inputs --explain`),
   **lasting jams** (`inputs --jam`, `--repair`)).
7. Demonstration: `demonstration.md` (`door_3x3`; D6, a lockout in front of Mumbo Jumbo's
   door, was being built by a fork when this was written: see the page's last section);
   `metrics.md`.
8. Roadmap: the README's open items.

**Main findings (this session):** a conductor's role follows the block a piston moves (a
wire-cutter wool, a log over a note block, a wool on slime); a wire step has two carriers;
a read does not name its asker (a piston's direct read and the QC read of the piston
below it are one call); mid-tick reads decide pistons (the QC update problem); the safe
gap is one event pair per door (a push that must land before the cut, a short pulse that
must cover landing + 1, a tail event or a veto block); lasting jams are edge-pulse
toggles moved in anti-phase or blocks accumulated in a column, and a second deliberately
short cycle re-syncs a toggle door.

**Tools** (`python -m tools.doorlab.<tool>`, `PYTHONPATH=src:.`): `inventory`, `report`,
`analysis`, `patterns`, `symmetry`, `mechanism`, `ablation` (`--trim`, `--turn`,
`--predict`), `power` (`--predict --out .sandbox/doors/ablation`, `--list`, `--reads`,
`--json`), `inputs` (`--out`, `--recover`, `--repeat`, `--explain [--gap]`, `--jam --gap`,
`--repair --gap`), `metrics`. Server: `python -m tools.gameserver.run_world WORLD` (the
world's own timeline; write a variant timeline with `canonical.to_save` first).

**Rules and traps learned** (the general rules: [[../../agents/README]]):

- Do not investigate LegDen's 7x7 and 8x8 (now in `data/redstone_learning/broken_doors/`).
- Never edit the dataset worlds; never change the simulator to make an experiment pass.
- One server run at a time; a background wait must not `pgrep -f` its own pattern.
- `python -I` ignores `PYTHONPATH`; a long tool run's prints are block-buffered: write to a
  file, and start it with the harness's background mode (plain `sleep` is blocked).
- A function stored as a class attribute binds `self` when read through an instance: the
  probe is read on the class (`Level.signal_probe`).
- Forks (sub-agents) work well for one door's explanation each, briefed with the page
  format, the tools and the sandbox folder; the quota can kill them mid-way, and a
  SendMessage resumes them. They must not commit; review and commit yourself.
- Check a claim against the data before writing it; prefer "inferred" over a guess.

**Next priorities:** D13 (the reach from a reader whose input changes to the mechanism,
to turn "changes something" into "breaks the door"), the remaining explanations if the
forks did not finish, D6's game check (EXP-077) if not run, D4 (mechanism split
refinements), D9 (items), G6 / G7 (need the guide's builds as worlds).
