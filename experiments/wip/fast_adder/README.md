# Work in progress: a fast 4-bit adder (backlog Q15)

Worlds to open in the editor (`redsim FILE`) or inspect with `redsim-cli FILE …`. Each has a
`note` saying what it shows. Failed and unfinished stages are kept on purpose.

| File | Status | What it shows |
|---|---|---|
| `01-carry-lines.redsim.json` | works (164/164) | R-024: two analog wire lines (G z=0, K z=2) with one glass step per bit; levers inject generate/kill per bit; comparators @C0..@C4 give every carry 2 ticks after the injections |
| `02-core-with-levers.redsim.json` | works (162/162) | the per-bit core: carry lines, the read comparator, the analog C wire, two repeaters and an XOR (C1 = C − H, C2 = H − C) per bit; G, K and H come from levers (inverted: nG, nK, nHa/nHb). Outputs @S0..@S3 (wire on the sum block), @R4 (carry out) |
| `03-relocated-injections.redsim.json` | works (162/162) | as 02 with the injections moved so the input logic can reach them: the G torch hangs on the next slice's corner block (lever nG), K is injected by a repeater from the south whose rear is the X = NOR(A,B) torch (lever nX), the H torches are wall torches whose blocks are powered by a wire on top |
| `03b-strong-levers-fail.redsim.json` | **fails** (110/162) | the same with the H levers standing on the H-torch blocks: a lever powers its block strongly, and that block also powers the previous bit's C wire next to it, so the previous bit's sum breaks. Lesson: blocks fed from outside must be powered weakly (wire on top) |
| `04-routed-slice-unfinished.redsim.json` | unfinished, not functional | one bit slice laid out by the wire router (`scripts/router.py`), copied 4 times: NAB (not-A or not-B) into the G torch block, the notH feed into the H torches, part of the south input logic. A, B, S and part of notH are not routed yet |
| `05-north-deck-partial.redsim.json` | unfinished, not functional | second router attempt: the input logic (not-A, not-B, X = NOR(A,B), G_n, the delay repeaters for notH) on a deck above the XOR north of the lines; routed in physical coordinates with each wire tagged by its bit (the first router mixed up wires of neighbouring bits). NAB into the G block, part of X, S and A are routed; X to the K repeater, G_n, notH and B are not (the deck around z -3..-6 is too crowded for the greedy router) |
| `06-north-deck-own-slice-partial.redsim.json` | unfinished, not functional | third layout: the G torch now hangs on the cap block above c3 inside its own slice (in 03-05 it hung on the next slice's corner, which crammed the G block, the NAB end and G_n into the column that also carries the notH line); S's start, the notH line along the H-torch blocks and their caps are placed by hand. 8 of 11 routes; NAB, A into the NOR block and notH still collide |

Try: `redsim-cli 03-relocated-injections.redsim.json check`, or
`redsim-cli 03b-strong-levers-fail.redsim.json --dry-run -c "target sum load 101100110011000111:11101; run 16; waves @S0 @S1 @S2 @S3 ticks 0..16"`.

## What the router taught me

- In a periodic 3-wide slice every column touches the other two (the next bit starts right
  after), so at each depth each level can carry **one** signal; signals one level apart in
  different columns need a solid block above the lower one. A slice of 13 levels holds
  roughly 6-10 parallel signals at one depth.
- A wire crossing into the next bit's slice must be told apart from that bit's own copy of
  the same wire: the router now works in physical coordinates and tags every wire with its
  bit (the first versions mixed neighbouring bits up, and could even end on the wrong bit's
  block).
- Blocks that are read from outside (torch blocks, repeater rears) must be powered weakly
  (a wire on top); strong power leaks into every wire beside the block (03b).
- Greedy shortest-path routing gets stuck in crowded corners: reserved landing cells must
  never get support blocks, and keeping several partial paths per cell matters.

## The design so far

- **Carry:** bit j injects 15 into the G line when A=B=1, into the K line when A=B=0; a
  subtracting comparator per bit (rear G, side K) is on iff the carry into bit j is 1.
  All carries settle 2 ticks after the injections (R-024).
- **Sum:** S = H xor C, from the analog carry through two delay-1 repeaters into an XOR
  whose H inputs are two torches. Planned timing: A,B at 0 → G, K at 4 → carries 6 →
  repeaters 8 → S at **10 ticks for all four bits** (the library's ripple adder needs 24).
- **The hard part (now):** each bit is a 3-block-wide slice (the lines need 3 wires a bit
  to fit 4 bits into the 15-block wire range). In such a slice every column touches the
  other two (the next bit's slice starts right after), so at each depth each level can
  carry only one signal. The input logic (not-A, not-B, NOR, notH) and the wires A, B, S
  must be stacked in levels. `scripts/pchk.py` checks a slice for wires that would join,
  leak diagonally or be powered by the wrong source; `scripts/router.py` searches wire
  paths that pass the checker.

`scripts/` is a snapshot of the generator scripts (paths point at the agent's scratch
directory); the finished generator will move to `tools/circuitgen/`.
