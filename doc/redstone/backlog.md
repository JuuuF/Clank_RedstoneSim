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
   - [x] R-011 hoppers and droppers as timing elements (drain, travel, locking)
3. **Interactions and timing inside a tick**
   - [x] R-010 glitches from unequal path delays; balancing
   - [x] R-012 order inside a tick: which 2-tick pulses pass; piston races
   - [x] R-013 0-tick pulses: what reacts to them
   - [x] R-014 rails, doors, gates, target blocks, lecterns
   - [x] R-015 observers moved by pistons; pulling across a gap (flying machines)
   - [x] R-016 falling blocks as timers and triggers
   - [ ] R-018 making 0-tick pulses with pistons (block dropping, redstone block pushes)
   - [x] R-019 wire on partial blocks (supports, one-way steps); dropper quasi-connectivity
   - [x] R-017 wire update order: position-dependent races (Q6)
4. **Primitives** ([[circuits]])
   - [x] gates: NOT, OR, NOR, AND (torch, comparator), NAND
   - [x] XOR (balanced, crossing-free layout); XNOR = XOR + NOT
   - [x] edge detectors (rising, falling, both)
   - [x] monostable (exact duration from a delay line and a copper bulb)
   - [x] retriggerable timer (comparator fade ring)
   - [x] analog memory: peak-hold register (comparator ring without wire)
   - [x] memory: RS latch, D latch, T flip-flop (copper bulb)
   - [x] clocks: comparator clock with enable, observer clock
   - [x] hopper clock (long periods, stop input)
   - [x] analog adder (three subtracting comparators)
   - [ ] signal strength decoder (1-of-16), multiplexer
5. **Compositions:** [x] 4-bit counter; [x] 2x2 piston door; [x] monostable; [x] combination lock + door; [x] button-toggled door; [x] sequencer, crossing; [x] flying machine; [x] double piston extender; [x] item sorter; [ ] a flush door, a timed door (monostable + door).

## Open questions

| # | Question | Why it matters | Planned in |
|---|---|---|---|

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
| Which neighbors lock a repeater; inputs while locked are dropped | [[components]] | [[R-006-repeater-locking]] |
| Torch burnout: 8 turn-offs in 60 ticks; recovery after 160 unless self-unpowered | [[components]] | [[R-007-torch-burnout]] |
| Observers pulse 2 ticks after being moved (not if moved while powered); sticky pistons pull across a gap on 2-tick pulses | [[components]] | [[R-015-moving-observers]] |
| Rails reach 8 past the powered one; doors from either half; target, lectern sources | [[components]] | [[R-014-other-components]] |
| Q6: yes, a race fed by one wire change flips with the build's position (z sign here) | [[timing]] | [[R-017-wire-order]] |
| Q7/H4: the counter follows lever edges every 2 ticks and an observer clock | [[circuits]] | `counter4` targets |
| Q8: a retriggerable timer: comparator fade ring; inputs must last a lap | [[circuits]] | `fade_timer` |
| Q9: double piston extender: three timed control blocks; inputs ≥ 8 ticks | [[circuits]] | `double_piston_extender` |
| Observers see state changes only (not comparator strength or container contents) | [[components]] | [[R-008-observers]] |
| Pistons: limits, slime grabs the floor, QC/BUD, same-tick start from circuits | [[components]] | [[R-009-pistons]] |
| H3: balancing path delays removes the compact AND's (and XOR's) glitch | [[circuits]] | [[R-010-hazards]] |
| Hopper drain 1+8(N-1) ticks, 7 ticks per hop, lock pauses | [[timing]] | [[R-011-hoppers]] |
| Q5: a 2-tick pulse passes iff the receiver's tick runs first (priority, then order); piston races: first powered wins | [[timing]] | [[R-012-same-tick-order]] |
| Q3: comparators (and torches, pistons) ignore 0-tick pulses; repeaters, lamps, bulbs, droppers react | [[timing]] | [[R-013-zero-tick]] |
