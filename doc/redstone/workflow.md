# From a requirement to a verified contraption

How to turn a request in plain words into a contraption that provably does what was
asked, with the knowledge base ([[redstone/README]]) and `redsim-cli` ([[cli]]). The
steps are shown on one complete example: the [[circuits]] Timed door
(`examples/circuits/timed_door.cli.txt`).

## 1. Formalize the requirement

Write down, before building, what can be checked in the simulator:

- **Inputs:** which blocks the user (or another circuit) operates, and how (button: 20
  ticks on; lever: held; pulse lengths matter, [[timing]]).
- **Outputs and conditions:** block states at ticks (`block=air`, `lit=true`, `power>=1`).
- **Timing:** latencies and windows, as tick ranges with a tolerance. Convert seconds to
  game ticks (×20).
- **Sequences:** what happens when inputs repeat, overlap, or come early (retrigger,
  reset).
- **Constraints:** size, materials, what must not happen (glitches, jams).

*Example.* "A 2×2 door that opens when either of two buttons is pressed and closes 5
seconds after the last press; pressing again while it is open keeps it open." →
inputs: two stone buttons (20-tick pulses); output: four door cells, stone = closed, air
= open; acceptance: cells clear within 20 ticks of a press; closing starts 95–110 ticks
after the **last** press; a press while open restarts the time; either button works.

## 2. Design from verified parts

Break the function into parts the library already has, and check each part's contract
against the requirement:

| Need | Part | Contract fact that matters |
|---|---|---|
| open a 2×2 doorway | [[circuits]] 2x2 piston door | opens 4 ticks after its bus is powered, closing starts 4 after it is unpowered |
| "5 s after the *last* press", restartable | Fade timer | retriggerable; off 54 ticks after its input falls; inputs ≥ 8 ticks |
| either button | wire OR | buttons on one input wire |
| the missing ~24 ticks | off-delay | OR of a signal and its delayed copy: no gap when the signal is longer than the delay (composition rules) |

Then the timing budget: press at T → button on T..T+19 → timer output off at T+20+54 →
off-delay +24 → door closing at about T+102. ✓ within 95–110.

Where no verified part exists, **run a small experiment first** (the method in
[[redstone/README]]) instead of trusting an assumption inside the full build.

## 3. Build, label, and write the acceptance test first

- Paste parts with `import examples/circuits/NAME.nbt at X Y Z`, wire them with `place`.
- `label` every input and output; write the acceptance cases as targets (`target … do
  at T use @B1`, `target … expect @D1 block=air during 20..103`) before running anything.
- `settle`, `check`.

## 4. Debug from the first divergence

When a case fails: `target NAME load CASE`, `run`, then `changes` / `waves` of the
outputs and the parts' ports, find the **first** tick where reality differs from the
plan, and `inspect`, `why`, `trace` there ([[cli]] section 10.2). Reduce the failing
part to a small reproduction if the cause is not obvious; check the composition rules
in [[circuits]].

*Example, two iterations:*

1. **The door never closed.** `changes` showed the second timer's output on forever. The
   timer's output wire joined the door bus, and the tap feeding the next stage sat on
   that wire: the bus (powered by the second stage) fed back into the tap and latched.
   Fix: the output powers a block; the bus branch and the tap each read the block
   through a repeater (diodes stop back-feed). Rule recorded in [[circuits]].
2. **It closed after 134 ticks, not ~100.** The two-timer cascade was too long: the
   button's own 20 ticks and each timer's 54-tick tail add up. Redesign: one timer plus a
   24-tick off-delay. Measured: closing at press + 102.

## 5. Verify more than the happy path

Test the sequences the requirement implies: a single press, a press while open (with
the other button), a press after it closed. Add failure cases you know of (short
inputs, simultaneous inputs) as targets, so the contract states them.

## 6. Report

Record the contraption in [[circuits]]: function, ports, measured timings, tested
sequences, failure cases, the bugs found on the way, and the parts and rules it relies
on. Keep the script (it is the reproducible evidence) and regenerate its world and
`.nbt` with `tools/make_circuits.py`. If the requirement cannot be met (an unmodeled
mechanic: [[differences]]), say exactly which part is missing and what experiment would
settle it.
