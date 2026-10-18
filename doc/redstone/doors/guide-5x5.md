# The 5x5 guide: "Compact Redstone: A Piston Door Making View" (MYuen222)

Source: `data/redstone_learning/guides/5x5 piston door with compact redstone by MYuen222/`
(course content and exercise solutions, course "2-P"; two .docx files, not committed). The
guide is a design method, not a single build: it shows how a seamless 5x5 piston door is
planned from the piston layout to the wiring, with two "pathways" (layouts). Its timing
claims are community knowledge for Java Edition (the version is not stated; the guide
mentions observers and "pre-observer" designs, so 1.11 or later). Here they are
**hypotheses** until checked in the simulator (26.3): the table at the end tracks them.

Vocabulary of the guide, in this knowledge base's words: **1t** = 1 redstone tick = 2 game
ticks (gt); this knowledge base counts game ticks only. **SPE / DPE / TPE / quad** = single
/ double / triple / quadruple piston extender (a column of pistons that pushes a block 1,
2, 3, 4 cells out and must pull it back stage by stage). **Spit** = a short pulse that
leaves the pushed block in place ([[../components]] "Spitting").

## 1. The engineering process the guide teaches

The order of decisions (each step constrains the next; this matches the order of the
mission: geometry before wiring):

1. **Piston layout** (section 2): which pistons move which door blocks where.
2. **Operation planning / sequencing** (sections 3, 8): the list of moves for closing and
   for opening.
3. **Powering layout** (sections 4, 9): how each piston can be powered at each position it
   takes (pistons in a stack move, so the power must reach them where they are).
4. **Input placement** (sections 5, 10).
5. **Wiring** of each move set (sections 6, 7, 11, 12).

### 1.1 Piston layout: grouping and storage

- **Grouping** ("2-11 Methods of compacting"): split the 25 door cells into groups that one
  piston arrangement clears. For the 5x5: two **side singles** (a column of 5 sticky
  pistons per side, each pulling one edge column of 5 blocks sideways into the wall) and
  the **center 15** (3 columns × 5 rows) pulled from the **top and bottom** by vertical
  piston stacks.
- **Storage**: the center 15 blocks need room. The frame above and below offers only 10
  cells, so blocks are stored **beside** the stacks: storage pistons perpendicular to the
  stack pull a block out of the stack's column into a side cell, which frees the column
  for the next block. Corners are ignored ("ignore the 4 corner blocks") because the side
  singles already clear them.
- **Storage ratio** top:bottom. The simple choice is 3:2 (a quad on top is easier than at
  the bottom "due to quasi-connectivity"); the guide prefers **2:3** without changing the
  stacks, because the top then runs the same move set twice (circuit reuse, 1.2) and the
  bottom has more room for one more storage layer.
- **First pathway** (the layout of image 3): top quad + bottom triple, storage over and
  under the frame with a 1-block air gap to the frame. **Second pathway** (image 6):
  storage partly inside the frame (ceiling and floor cells), placed lower, *discretized*
  (single storage pistons instead of groups), no air gap; asymmetric storage (it can be
  mirrored). Much harder to wire, much smaller.

### 1.2 Sequencing: moves, move sets and circuit efficiency

- A **move** is one piston action (pulse, on, off, double pulse); a **move set** (A, B, C,
  TE …) is a sequence of moves that one circuit performs.
- **Circuit efficiency** ("2-12 Introduction to planning and sequencing"): wire as few move
  sets as possible and **reuse** them, both within an operation (the top runs A then B
  twice when opening) and **between closing and opening**.
- **Minimum moves sequence (MMS)**: first write the shortest sequence for closing and the
  shortest for opening, separately. Then make them alike by adding **redundant moves**
  (moves that change nothing in that operation, e.g. firing a storage piston that has
  nothing to pull) until one circuit serves both. Moves that remain different need a
  **toggle** (state): "opening only" moves, a 4-state toggle where a move happens on
  every 4th run.
- First pathway sequences: top closing `A`, opening `B, EM, A, B` (EM = extra moves);
  bottom closing `C, TE`, opening `C, TE, TR` (triple extension, triple retraction:
  only TR needs a toggle). Second pathway: bottom `C, C, D`; top `A, TE, B`.
- Timing priorities decide the **input position**: put it where the first, most
  time-critical move happens (the top: the quad must extend before the bottom moves), so
  the other side gets its delay "for free" from the signal's travel.

### 1.3 Powering layout: reaching moving pistons

- **Dust lines on the ceiling** above a piston stack power the pistons *below* them
  through **quasi-connectivity** when the stack is extended (a dust line beside the cell
  above a piston powers it). One line per stack level.
- **Updater pistons**: quasi-connectivity only acts on a neighbor update ([[../components]]
  "Quasi-connectivity", "Lost update"); a dust line that should retract a quasi-powered
  piston needs a piston beside it that moves to give that update ("BUD").
- **Observer sliders**: an observer pushed by a piston fires when it moves; a row of
  observers on a slider fires all pistons of a layer at once. A **0-tick slider** pushes
  and pulls the observers in one go (it "resets itself by default") and powers all
  pistons simultaneously.
- **Redstone cross**, **dust dot**: dust shapes that power in all directions without
  running into each other.
- **Piston tape** (exercise PF.5): a moving strip that carries power blocks along the
  stack; alternative: observers below the floor pushed into the stack.
- **Conductor blocks inside the stack**: storage blocks pushed into the stack position can
  carry power to pistons (the floor blocks "must be solid").

### 1.4 Wiring tips (reusable sub-circuits the guide names)

- "Powering a always powers b, pulsing a double-pulses b" (a link circuit, image 21/22).
- **Joining two alternating inputs with observers** (c and d, or b and c): "requires at
  least a 4.5-tick pulse" (9 gt).
- **Repeater input trick**, **input bug** (topics "2-4"): the delay of the input
  (lever vs. circuit, [[../timing]] "a piston starts one tick later from a lever")
  changes the order of events.
- **Toggles** (T flip-flops, 4-state toggles: exercise PF.3), toggles made by moving a
  component out.
- Rising-edge toggles for storage (a falling-edge toggle breaks when a sequence refires
  the storage line with a long pulse).

## 2. Claims to check in the simulator (26.3)

| # | Claim (guide section) | Status | Evidence |
|---|---|---|---|
| G1 | A short (1t / 2 gt) pulse to a piston extender spits the block (leaves it) (3, 6) | **V** already | [[../components]] "Spitting", R-018, G EXP-016 |
| G2 | Dust beside the cell above a piston powers it by quasi-connectivity, only on an update (4) | **V** already | R-009, R-025 |
| G3 | A block that is still moving cannot be pushed: an extender powered before the blocks in front land pushes fewer blocks (PF.1: "movable from 9gt") | **V** | [[../records/R-026-moving-block-blocks-piston]]: the piston queues nothing while the block moves and extends 1 tick after it lands; a pulse that ends first is lost |
| G4 | A piston pushing an observer gives block updates at 0, 3 and 4 gt after it starts; the observer then powers from 2 to 4 gt (PF.1) | **V** (read from the landing) | [[../records/R-015-moving-observers]] (game-verified): the observer lands 2 ticks after the push starts and pulses 2 ticks after landing, for 2 ticks, whatever it faces. Counted from the push: 0 the moving block appears, 2 it lands, 4–6 the pulse; the guide's "2 to 4" is the pulse counted from the landing (re-measured 2026-10-19: push at 3, lands 5, on 7–8, off from 9, in three orientations) |
| G5 | A triple extender fed by a 2-tick repeater extends 2 blocks when blocks are in front (closing) and 3 when not (opening) (PF.1) | I | follows from G3 (R-026); the exact case needs the exercise world |
| G6 | A 0-tick slider powers all observers' pistons at once and resets itself (4) | H | to test |
| G7 | Joining two alternating inputs with observers needs a pulse of at least 4.5t = 9 gt (6, 11) | H | not built yet |
| G8 | "Half-tick timings" (1.5 t): a move 3 gt after another (6) | I | game ticks make 3 gt exact; nothing "half" about it in 26.3 |

Records of the tests are in the knowledge base's `records/` (R-026 …).
