# redsim-cli internals: how the command line is built

For developers who change or extend `redsim-cli`. What the command line does and how to
use it is in [[cli]] (the guide) and [[cli-reference]] (every command); the design
decisions are [[decisions]] ADR-027. The code is in `src/redsim/cli/`; it never imports
Qt.

## 1. The pieces

| Module | Job |
|---|---|
| `main.py` | The program: global options, the ways of calling it (one command, `-c`, standard input, `shell`), `help`. |
| `language.py` | The command language: splitting text into commands and words (`split_commands`), the argument reader `Args` (positions, labels, blocks, directions, ticks, ranges, options) and `CliError`. |
| `registry.py` | The registry: the `command` decorator, `Command` (with its help text), `Output`, and the help/reference renderers. |
| `session.py` | A session: opening the world, running commands, where edits go (`editing`), the view, saving, the undo file, the shell. |
| `views.py` | Text renderings: map codes and legends, map grids, signals per side, signal timelines. |
| `targets.py` | Targets: parsing expectations, checking lines, running a case in a copy, truth tables. |
| `commands/` | The commands, one module per chapter of the reference: `world`, `build`, `time`, `inspect`, `annotate`, `targets`, `io`, `meta`; `common.py` holds shared helpers. Importing `redsim.cli.commands` registers them all. |

Everything a command changes goes through the editor's `Document`
(`redsim.editor.document`), the same object the GUI edits: building commands call its
edit methods (`place_state`, `set_state`, `fill`, `use`, …), timeline commands its history
methods (`add_pulse`, `move_edits`, `settle_build`, …). The CLI adds no simulation logic
of its own; whatever the editor can do, it does the same way.

## 2. A run, from the command line to the saved file

1. `main.main` strips the options (`--json`, `--dry-run`, `--keep-going`), creates a
   `Session(world)` and calls `Session.open`, which loads the world file with
   `Document.open` (re-simulating the recorded history) and, through `Session.adopt`,
   moves to the saved view (`extra["cli"]["view"]`: a tick and a number of engine steps
   into the next tick) and enters `Document.deferred()` for the whole run.
2. The commands come from the argument list, from `-c` (split by `split_commands`) or from
   standard input. `Session.run` runs them one by one: `Session.execute` looks the name up
   (`registry.lookup`), returns the view first unless the command is an edit
   (`restore_view`, see 3), builds an `Args` reader over the remaining words and calls the
   command's function, which returns an `Output`. Notices the editor left
   (`Document.notice`, e.g. "2 later edits could not be applied") are appended as
   `note: …` lines.
3. Printing: text mode writes the output's lines (preceded by `> command` when several
   commands run); `--json` writes `{"command", "ok", "data"}` per command. A `CliError`
   prints `error: …` and stops the run (unless `keep_going`).
4. Commands that are not pure views are written to the session log.
5. `Session.finish` returns the view, leaves `deferred()` (re-running anything still
   held back) and, if something changed, `Session.save`: the old file content is pushed
   to the undo file (`WORLD.undo`, gzip JSON `{"undo": [...], "redo": [...]}`, 20
   versions, files over 20 MB are skipped), then `Document.save` writes the world with
   `extra["cli"] = {"log": last 500 lines, "view": [tick, steps]}`.

## 3. Where edits go, and the view

The rule (ADR-027): **edits change the build (tick 0) unless the line starts with `at
T`**; the view only says what inspections look at.

- `Session.edit_tick` is 0, or T while an `at T` line runs (`commands/time.py: at`).
- `Session.editing()` is the context every editing command uses: if the document is not
  at `edit_tick` (or is inside a tick) it moves there with `goto` (simulating further if
  T is past the recorded end), wraps the command's edits in `Document.batch()` (one undo
  step per command), turns `EditError` into `CliError` and sets `changed`. It remembers the
  view it left in `_pending_view` but does **not** go back yet.
- `Session.restore_view()` goes back: `Document.flush()` (re-run what `deferred` held
  back, see 4), then `goto_view`. `execute` calls it before every command that is not an
  edit, and `finish` before saving. So a script of 100 `place` lines stays at tick 0 the
  whole time and re-simulates once.
- `goto(T)`: `Document.seek_tick` inside the recorded history, else seek to the end and
  `run_ticks` the rest. `view_now()` describes the view as (tick boundary, steps after it)
  so a view inside a tick survives saving.

## 4. Deferred re-runs (in `Document`)

Editing inside the recorded history keeps the later edits: `Document._apply` holds them
in `_kept_future` and re-simulates them after the edit (`_rerun_future`, ADR-022). Inside
`Document.deferred()` that re-run waits until `flush()` or the end of `deferred`. Between
edits the history then ends at the edit point. `_history_state()` (what undo stores)
includes the held-back edits, so undoing a deferred edit restores them correctly.

## 5. Commands

A command is a function registered with `@command` (`registry.py`):

```python
@command(
    "place",                       # the name typed
    group="build",                 # the chapter of the reference (registry.GROUPS)
    usage="place POS BLOCK [PROP=VALUE ...]",
    summary="One line for 'help' and the overview.",
    help="""
    The full description: paragraphs, '-' lists. Written for agents and people; this is
    the documentation (it becomes doc/cli-reference.md).
    """,
    examples=("place 0 1 0 redstone_wire", "at 10 place 4 1 0 redstone_block  # a comment"),
    kind="edit",                   # edit | view | time | file | meta (see below)
    data='{"pos", "state", "tick"}',  # what --json puts in "data"
)
def place(session: Session, args: Args) -> Output:
    pos = args.pos()
    state = args.block()
    args.done()                    # fail on leftover words (typos)
    with session.editing() as doc:
        doc.place_state(pos, state)
    return Output([f"placed …"], {"pos": list(pos), ...})
```

`kind` decides how the session treats it:

| kind | Meaning | Session behavior |
|---|---|---|
| `edit` | changes blocks | must use `session.editing()`; `at T` records it at tick T |
| `view` | only reads | the view is restored first; `at T` runs it at tick T and returns |
| `time` | moves the view or changes the timeline | the view is restored first; sets `session.changed` itself |
| `file` | whole-world operations (`new`, `save-as`, `open-save`) | as `time` |
| `meta` | help, annotations, `at`, `monitor`, `target` | as `time` |

Reading arguments: always through `Args` (`pos`, `block`, `direction`, `tick`,
`tick_range`, `number`, `word`, `choice`, `option`/`option_int` for keyword options like
`for 3`, `pop_key` for `key=value` options, `rest`), and end with `args.done()`. Every
reader raises `CliError` with "expected X, found Y". Errors from the editor
(`EditError`) become `CliError` inside `editing()`; raise `CliError` yourself for
anything else, with a message that says how to fix it.

Output: `Output(lines, data)`. Lines are plain text (no colors, no box drawing), positions
written `x y z` (`language.format_pos`, or `commands.common.name_of`/`named` to show
labels), states with `views.state_text` (no `minecraft:` prefix). `data` holds the same
facts as JSON values (positions as lists). Keep text and data in sync; describe `data` in
the registry entry.

**Adding a command**: write the function in the module of its chapter, register it with
full help and examples, add tests to `tests/cli/test_cli.py`, regenerate the reference
(`redsim-cli help --markdown > doc/cli-reference.md`; `tests/cli/test_cli.py` fails until
you do) and mention it in [[cli]] where it fits. If it does something the game does not
(an editor stand-in, an approximation), mark it `Not as in the game:` and list it in
[[differences]] (doc/implementation-notes.md, "Conventions").

## 6. Targets (`targets.py`)

A target is stored as JSON in `Document.targets`:
`{"name", "description", "cases": [{"name", "lines": [command lines]}]}`. Lines are
stimuli (any editing command, `pulse`, or `at T EDIT`) or expectations (`expect POS
KEY<OP>VALUE at T | during A..B | within A..B`). `check_line` validates a line when it is
added (`target NAME do/expect`), so stored targets always parse.

`run_case`: `case_document` copies the world's build (`Engine.restore(history.base)`,
labels too) into a new `Document`; a throw-away `Session` (dry run) adopts it and
executes the stimuli as ordinary commands; then it visits every tick an expectation
needs (`goto`, in increasing order) and records `observe(level, pos, key)` (a property,
or `block`, `power` = `monitor_value`, `signal` = best neighbor signal, `direct` =
`getDirectSignalTo`). `Expectation.holds` compares (numbers numerically, booleans as
`true`/`false`). `during` needs every tick, `within` one. The world's own document is
never touched.

`truth_cases` turns a truth table into cases: a 1 input is `at 1 use POS` for a lever,
`pulse POS at 1 for settle+1` for anything else; outputs become `power>=1` / `power=0`
expectations at tick 1 + settle.

## 7. Maps (`views.py`)

`block_code(state, level, pos, plane)` returns a two-character code and a legend key;
`WORDS` maps keys to the legend's words; `Legend` assigns two-letter codes to blocks
without a fixed one and collects what a map used. A `Plane` maps world directions to
arrows for a view (`y`, `z` or `x`). `render_map` returns the text lines and the grid of
codes (the JSON `layers`). To give a block its own code: add a branch to `block_code`
and its words to `WORDS`, and describe it in [[cli]] section 7.1 and the module
docstring.

## 8. Causes: `why` and `effects`

Both read the simulation trace (`redsim.sim.trace`: one record per block change, neighbor
update, scheduled tick, block event and engine step, each with a `parent` record) through
`redsim.sim.causes`. `why` (`causes.why`) walks from the block's last change back along
`parent` links; where a link ends at an engine step, `_origin` finds the record that
queued it (the `schedule_tick` for a scheduled tick, the queued block event, and for a
moving piston's block-entity tick the change that placed the moving piston), so the
chain crosses ticks and piston movements. `effects` (`causes.effects`) does the same forwards: starting from
the change it collects every later record whose parent is already collected, every
scheduled tick and block event step that a collected record queued (matched by position,
trigger tick and sub-tick, or position and event numbers), the block-entity ticks of
moving pistons a collected change placed (until that moving piston is gone), and
neighbor updates sent in
the same engine step from the position of a collected change, or from a position next to
it that names the changed block as the update's source. Both cases are blocks that change
first and update afterwards, so the updates are not child records of the change: wire
sets its power, then updates around itself; buttons, levers, torches, repeaters and
observers change, then update around the block they are attached to or point into
(`_source_change` applies the same rule backwards for `why`). `effects` merges a block's
changes within one tick into one line. `effects` first goes to the end of the history
and `why` to the view with `Document.trace_through` (`Timeline.seek_traced`), which
replays every step instead of jumping to keyframes, so the trace has no gap; both return
to the view afterwards. `trace T` needs only tick T: `Document.trace_tick` replays it
from the boundary before it, and the steps of tick T are those between the boundaries
after T-1 and T (`Document.tick_steps`).

## 9. Tests and documentation

- `tests/cli/test_cli.py` runs `main` the way users do (arguments, `-c`, standard input)
  on temporary worlds and checks the printed text and JSON; it also checks that
  `doc/cli-reference.md` equals `render_reference()`.
- `tests/cli/test_examples.py` runs every script in `examples/cli/` on a new world and
  requires every `check` in it to pass.
- `tests/editor/test_timeline_view.py` covers the `Document` parts (deferred re-runs,
  saving the build after running).
- [[cli]] is written by hand; when behavior changes, change it in the same commit. Its
  example outputs were copied from real runs: re-run and re-paste rather than editing
  them by hand.
