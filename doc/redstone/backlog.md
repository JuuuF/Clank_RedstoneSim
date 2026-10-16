# Research backlog

Open questions, hypotheses and the roadmap of the redstone knowledge base
([[redstone/README]]). Take the highest open item; when it is answered, move it to "Done"
with the record that answered it.

## Roadmap

1. **Foundations** (every circuit depends on them)
   - [x] R-001 response times of the basic components
   - [x] R-002 what powers a block, strongly or weakly
   - [x] R-003 short pulses and gaps into each component; lever vs circuit-made pulses
   - [x] R-004 wire geometry: cross, dot, line, corner; steps; glass and slabs
   - [x] R-005 signal strength: through blocks, comparator modes and side inputs, containers
2. **Components in depth**
   - [x] R-006 repeater locking (who locks, timing of lock/unlock, held state)
   - [x] R-007 torch burnout thresholds and recovery
   - [x] R-008 observers: what they see (state changes only), chains
   - [x] R-009 pistons: push limit, immovable blocks, slime and honey, QC and BUD, same-tick start
   - [ ] R-011 copper bulb, dropper/hopper and note block as circuit elements (hopper
     clocks, item counters)
3. **Interactions and timing inside a tick**
   - [x] R-010 glitches from unequal path delays; balancing
   - [ ] R-012 races: two signals arriving in the same tick (repeater priorities, piston
     block-event order)
   - [ ] R-013 0-tick pulses: what makes them and what reacts to them
4. **Primitives** ([[circuits]])
   - [x] gates: NOT, OR, NOR, AND (torch, comparator), NAND
   - [x] XOR (balanced, crossing-free layout); XNOR = XOR + NOT
   - [x] edge detectors (rising, falling, both)
   - [ ] pulse extender (long pulses), monostable with long delay lines
   - [x] memory: RS latch, D latch, T flip-flop (copper bulb)
   - [x] clocks: comparator clock with enable, observer clock
   - [ ] hopper clock (long periods), signal strength encoders/decoders
5. **Compositions:** [x] 4-bit counter; [ ] a sequencer, piston doors, a combination lock.

## Open questions

| # | Question | Why it matters | Planned in |
|---|---|---|---|
| Q3 | Does a comparator pass a 0-tick pulse? | edge detectors | R-013 |
| Q5 | Which circuit-made 2-tick pulses end *after* a torch's tick (and so pass)? Block events, block entities, lower-priority sources? | pulse design | R-012 |

## Hypotheses waiting for a test

- H4: the 4-bit counter counts input edges as close as 4 ticks apart.

## Done

| Question | Answer | Record |
|---|---|---|
| Base delays of every component | [[timing]] | [[R-001-response-times]] |
| What powers a block, strong vs weak | [[signals]] | [[R-002-what-powers-a-block]] |
| Q2: does a repeater fill short gaps? Yes, below its delay | [[timing]] | [[R-003-short-pulses]] |
| Comparators and torches lose 1-tick and circuit-made 2-tick pulses; sticky pistons need 3 ticks | [[timing]] | [[R-003-short-pulses]] |
| Q4: a lone placed wire is a cross (powers 4 sides), a dot powers only below | [[signals]] | [[R-004-wire-geometry]] |
| Q1: a block powered with N by a comparator gives wire beside it N | [[signals]] | [[R-005-signal-strength]] |
| Which neighbors lock a repeater; inputs while locked are dropped | [[components]] | [[R-006-repeater-locking]] |
| Torch burnout: 8 turn-offs in 60 ticks; recovery after 160 unless self-unpowered | [[components]] | [[R-007-torch-burnout]] |
| Observers see state changes only (not comparator strength or container contents) | [[components]] | [[R-008-observers]] |
| Pistons: limits, slime grabs the floor, QC/BUD, same-tick start from circuits | [[components]] | [[R-009-pistons]] |
| H3: balancing path delays removes the compact AND's (and XOR's) glitch | [[circuits]] | [[R-010-hazards]] |
