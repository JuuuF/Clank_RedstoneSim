# Research backlog

Open questions, hypotheses and the roadmap of the redstone knowledge base
([[redstone/README]]). Take the highest open item; when it is answered, move it to "Done"
with the record that answered it.

The piston-door track (reverse-engineering the dataset's designs) keeps its own open items
D1–D8 in [[redstone/doors/README]], "Status and roadmap".

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
   - [x] R-018 making 0-tick pulses with pistons (spit + BUD push; spit timing; 0-tick piston moves)
   - [x] R-019 wire on partial blocks (supports, one-way steps); dropper quasi-connectivity
   - [x] R-020 vertical signal transmission compared
   - [x] R-021 latch chains: the unlock window
   - [x] R-022 rotated module pastes
   - [x] R-017 wire update order: position-dependent races (Q6)
   - [x] R-023 instant piston wire: chains that collapse in one tick (Q11)
   - [x] R-024 analog carry lines: every carry of 4 bits at once (Q15)
   - [x] R-025 piston timing in a door: masked quasi-connectivity, lost update through a moving head, landing check
4. **Primitives** ([[circuits]])
   - [x] gates: NOT, OR, NOR, AND (torch, comparator), NAND
   - [x] XOR (balanced, crossing-free layout); XNOR = XOR + NOT
   - [x] edge detectors (rising, falling, both)
   - [x] monostable (exact duration from a delay line and a copper bulb)
   - [x] retriggerable timer (comparator fade ring)
   - [x] analog memory: peak-hold register (comparator ring without wire)
   - [x] memory: RS latch, D latch, T flip-flop (copper bulb), shift register (unlock-window timing)
   - [x] clocks: comparator clock with enable, observer clock
   - [x] hopper clock (long periods, stop input)
   - [x] analog adder (three subtracting comparators)
   - [x] signal strength decoder (1-of-16, `decoder16`), analog 2:1 multiplexer (`analog_mux`)
   - [x] 4:1 analog selector from three pasted multiplexers (`analog_mux4`)
   - [x] instant wire: a rising edge 39+ blocks in 0 ticks (`instant_wire`, R-023)
   - [x] 4-bit DAC: binary to strength, balanced (`dac4`)
   - [x] 4x1 RAM from a literal crossbar (`ram4`)
   - [x] lookup table: hex 7-segment decoder and ADC (`seg7`, `adc4`)
5. **Compositions:** [x] binary 4-to-16 decoder (`bin_decoder16`); [x] full adder and 4-bit ripple-carry adder (`full_adder`, `adder4`); [x] 4-bit counter; [x] 2x2 piston door; [x] monostable; [x] combination lock + door; [x] button-toggled door; [x] sequencer, crossing; [x] flying machine; [x] double piston extender; [x] item sorter; [x] timed door (worked requirement, [[workflow]]); [x] 3x3 flush door (`door_3x3`, Q18, R-025); [x] lockout (`lockout`, Q22); [x] 7-segment display (`seg7_display`, Q20); [x] instant wire, both edges (`instant_edges`, Q17).

## Open questions

| # | Question | Why it matters | Planned in |
|---|---|---|---|
| Q10 | A re-armable piston 0-tick (or 1-tick) pulse generator: the R-018 ones are one-shot (the BUD piston stays out, the redstone block is moved away) | a library module for 0-tick pulses on demand | after the decoder and adder |
| Q14 | Glitch-free multi-input changes in the full adder: balance the CIN paths (S 6, COUT 4 ticks) with the A/B paths (8/8) without slowing the carry | adders feeding edge-triggered logic | later |
| Q15 | A fast carry. **Found (R-024):** two analog wire lines with glass diodes give all carries of 4 bits 2 ticks after the injections. **Paused (2026-10-18):** the per-bit core works with levers (S at 10 ticks planned, `experiments/wip/fast_adder/02`, `03`); the input logic (not-A, not-B, NOR, notH delays) and the A, B, S wires do not yet fit the 3-wide periodic slice: the best router layouts leave 2-3 of 11 wires unrouted. Next ideas: inject K from the north through a torch block fed by two repeaters A', B' (no long X wire south); a negotiated-congestion router; or a wider slice by giving each bit 4 wires of line and splitting into 3-bit blocks. Round 2 (2026-10-18): the H inputs are derived on top of the core (WIP 07, 162/162: a wire over the G and X torches' above-blocks carries G or K); per bit only NAND and OR remain as inputs, but that wire fills y=7 over the core and the nG feed into the G torch's block is blocked (WIP 08 fails); ideas in the README. Round 3 (WIP 09, 34/162, unfinished): G and K taps at y=5, nH at y=7 over the core and into one y=4 path joining both H blocks, nG through a repeater, K repeaters delay 2; open fault: with bit 3 generating, bit 0's H block 1 (1 3 -7) gets power 4 from an untraced source (next step in PROMPT.md's TODO list). State and tools: `experiments/wip/fast_adder/README.md` | 32-bit arithmetic, ALUs | paused |
| Q20 | Glitch-free `seg7_display`: the segments flicker from about 30 ticks after a change until 54; latch them (a D latch per segment, enabled 54 ticks after the last change, e.g. by a `fade_timer`) | clean displays | later |
| Q21 | A faster 3x3 door open: `door_3x3` clears all nine cells 32 ticks after its input (6 of them input torch and lockout; 28 without the lockout). Where the 26 ticks after the trunk falls go: hold release 6 (it must cover the falling-edge spit pulse), M down 2, W 2, A 2, B raised 4, A down 2, B home 6 (1 of them the lost update of R-025). Ideas, each worth 2-4 ticks: an asymmetric hold (lock its driver during the rise only; needs a spit on the rising edge only), a direct final pull without the floor block's quasi-power at that moment (needs the raised-push pulse gated, which costs 2 again) | fast doors | paused: small gains |

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
| Can pistons make 0-tick pulses? Yes: a spat block pushed out by a BUD piston in the same block-event phase; pistons updated before it ends still move (a sticky one in 0 ticks) | [[timing]], [[components]] | [[R-018-piston-zero-tick]] |
| Q13: a faster carry: 4 ticks per bit (the CIN repeater and G2); YC's wire runs 15 blocks straight over the top to the next copy's CIN repeater, no repeater between copies | [[circuits]] composition rules | `full_adder`, `adder4` targets |
| Q12: a 4:1 analog selector: three `analog_mux` pasted turned, outputs pointing straight into the next inputs; S0 on its own top layer; S1 delayed so both address bits may change together | [[circuits]] composition rules | `analog_mux4` targets |
| Q11: yes for one edge: extended sticky pistons holding redstone blocks against each other's backs collapse in one tick (any length; 17 blocks a stage with wire); re-arming 3 ticks a stage | [[timing]], [[components]] | [[R-023-instant-piston-wire]] |
| Q16: an instant-wire module: head pushes the first block away, stages joined by 14-wire lines, tail uncuts a wire step; 0 ticks on, 3·(stages + 2) off; failure cases short pulses and early re-triggers | [[circuits]] | `instant_wire` targets |
| Q19: a 16-word lookup table: decoder16's lines as rows (nested corners), a tap crossbar as the OR plane; `seg7` (hex 7-segment decoder) and `adc4` (strength to bits) | [[circuits]] | `seg7`, `adc4` targets |
| Q18: a 3x3 flush door: the center goes down two cells in two steps through a gap made by a third piston; B's hold and the final pull by quasi-connectivity through a floor block, W's asymmetric timing by a repeater lock | [[circuits]] | `door_3x3` targets, [[R-025-piston-door-timing]] |
| Q21 (part): an input-safe 3x3 door: a lockout repeater between the input torch and the trunk, locked after each change of its own output while the sequence runs; locks react 2 ticks after the change, the lockout repeater needs 4 | [[circuits]] | `door_3x3` targets `stone`, `spam`, `burnout` |
| Q22: the lockout as a module: a repeater locked by two subtracting comparators reading its own output and a delayed copy; levels held D + 6; both D within 6 ticks of each other | [[circuits]] | `lockout` targets |
| Q20 (part): a 7-segment lamp display for `seg7`: decoder columns reordered f e a g d b c so the lines reach a 4×7 lamp digit without crossing; settled 54 ticks after a change | [[circuits]] | `seg7_display` targets |
| Q17: both edges instant: two instant chains act on one output step, R removes a cut (on), F removes the source (off); F's head is powered by IN or by NOT IN 8 ticks late, so F re-arms by itself after R | [[circuits]] | `instant_edges` targets |
