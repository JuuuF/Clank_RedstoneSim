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
   - [ ] R-006 repeater locking (who locks, timing of lock/unlock, held state)
   - [ ] R-007 torch burnout thresholds as a design limit (fastest safe torch clock)
   - [ ] R-008 observers: what they see (wire power levels, piston movement), chains
   - [ ] R-009 pistons: push limit, immovable blocks, slime and honey, spitting blocks,
     quasi-connectivity and budding
   - [ ] R-010 copper bulb, dropper/hopper and note block as circuit elements
3. **Interactions and timing inside a tick**
   - [ ] R-011 races: two signals arriving in the same tick (repeater priorities, piston
     block-event order)
   - [ ] R-012 0-tick pulses: what makes them and what reacts to them
4. **Primitives** ([[circuits]])
   - [ ] gates: NOT, OR, AND, NAND, NOR, XOR, XNOR (torch and comparator versions)
   - [ ] edge detectors (rising, falling, both), pulse limiter, pulse extender
   - [ ] memory: RS latch, D latch, T flip-flop (copper bulb, others), counters
   - [ ] clocks: repeater loop, comparator subtract clock, observer clock, hopper clock
   - [ ] monostable / delay lines, signal strength encoders
5. **Compositions:** a binary counter, a sequencer, piston doors, a combination lock.

## Open questions

| # | Question | Why it matters | Planned in |
|---|---|---|---|
| Q3 | Does a comparator pass a 0-tick pulse? | edge detectors | R-012 |
| Q5 | Which circuit-made 2-tick pulses end *after* a torch's tick (and so pass)? Block events, block entities, lower-priority sources? | pulse design | R-011 |

## Hypotheses waiting for a test

- (none open)

## Done

| Question | Answer | Record |
|---|---|---|
| Base delays of every component | [[timing]] | [[R-001-response-times]] |
| What powers a block, strong vs weak | [[signals]] | [[R-002-what-powers-a-block]] |
| Q2: does a repeater fill short gaps? Yes, below its delay | [[timing]] | [[R-003-short-pulses]] |
| Comparators and torches lose 1-tick and circuit-made 2-tick pulses; sticky pistons need 3 ticks | [[timing]] | [[R-003-short-pulses]] |
| Q4: a lone placed wire is a cross (powers 4 sides), a dot powers only below | [[signals]] | [[R-004-wire-geometry]] |
| Q1: a block powered with N by a comparator gives wire beside it N | [[signals]] | [[R-005-signal-strength]] |
