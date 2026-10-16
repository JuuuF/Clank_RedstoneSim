# Research backlog

Open questions, hypotheses and the roadmap of the redstone knowledge base
([[redstone/README]]). Take the highest open item; when it is answered, move it to "Done"
with the record that answered it.

## Roadmap

1. **Foundations** (every circuit depends on them)
   - [x] R-001 response times of the basic components
   - [x] R-002 what powers a block, strongly or weakly
   - [ ] R-003 short pulses: how each component treats a pulse shorter than its delay
     (repeater extends, comparator, torch, observer, piston spitting, lamp) and short
     gaps between pulses (does a repeater fill them?)
   - [ ] R-004 wire geometry: dot, line, cross, what each shape points into, steps up and
     down, cutting by a block above, glass and slabs, wire into repeaters from the side
   - [ ] R-005 signal strength: through blocks, into comparators and their side inputs,
     subtraction, container fill levels
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
| Q1 | Does a block powered by a comparator with output N < 15 give wire beside it N? | analog signals through blocks | R-005 |
| Q2 | Does a repeater fill an input gap shorter than its delay? | pulse shaping, clock design | R-003 |
| Q3 | Does a comparator pass a 1-tick pulse? A 0-tick pulse? | edge detectors | R-003, R-012 |
| Q4 | Does a lone placed wire (cross) power all four neighbors, and a dot only the block below? | compact wiring | R-004 |

## Hypotheses waiting for a test

- H1: a repeater with delay d turns a pulse shorter than 2·d into one of exactly 2·d.
  (G EXP-009 for d=4 and a 1-tick pulse.)
- H2: a torch ignores pulses shorter than 2 ticks? (EXP-027: it ignores 0-tick pulses.)

## Done

| Question | Answer | Record |
|---|---|---|
| Base delays of every component | [[timing]] | [[R-001-response-times]] |
| What powers a block, strong vs weak | [[signals]] | [[R-002-what-powers-a-block]] |
