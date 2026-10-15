"""Target commands: ``target``, ``targets``, ``check`` (model and runner:
``redsim.cli.targets``)."""

from __future__ import annotations

from typing import Any

from redsim.cli import targets as model
from redsim.cli.commands.common import name_of
from redsim.cli.language import Args, CliError, join_words, split_commands
from redsim.cli.registry import Output, command
from redsim.cli.session import Session
from redsim.cli.views import wave_row


@command(
    "target",
    group="targets",
    usage=(
        'target new NAME ["DESCRIPTION"] | target NAME do COMMAND ... | '
        "target NAME expect POS CONDITION at T|during A..B|within A..B | "
        "target NAME truth INPUTS -> OUTPUTS rows ROW ... [settle N] | "
        "target NAME show | target NAME remove N | target NAME delete | "
        "target NAME load [CASE]"
    ),
    summary="Define an acceptance test: stimuli, expected results, or a truth table.",
    help="""
    A target says what a contraption must do; `check` runs it. Build it up line by line:

    - `target new NAME "DESCRIPTION"`: an empty target (one case, "main").
    - `target NAME do COMMAND …`: a stimulus for every case: `pulse POS at T for N`,
      `at T use POS`, `at T set POS BLOCK`, `at T plate …`, or an edit without `at`, which
      changes the build for the test only.
    - `target NAME expect POS CONDITION WHEN`: CONDITION is `KEY=VALUE` (also `!=`, `<`,
      `<=`, `>`, `>=` for numbers), KEY a block property (`lit`, `powered`, `extended`,
      `power`, …) or `block` (the block id), `power` (the value `waves` shows), `signal`
      (strongest signal received) or `direct` (how much a solid block is powered). WHEN is `at T`,
      `during A..B` (every tick) or `within A..B` (some tick).
    - `target NAME truth @IN1 @IN2 -> @OUT rows 00:0 01:0 10:0 11:1 [settle N]`: one case
      per row (input bits, `:`, output bits). Inputs that are 1 switch on at tick 1 (a
      lever is flipped, anything else gets a power pulse that lasts the run); each output
      must be on (`power>=1`) or off (`power=0`) at tick 1 + settle (default 10).
    - `target NAME show` lists its lines (numbered), `remove N` deletes line N,
      `delete` the whole target.
    - `target NAME load [CASE]` replaces the world's timeline with the case's stimuli
      (undo brings the old one back), so `show`, `waves`, `why` can look at that run.

    Targets are saved in the world. Their ticks count from the build (tick 0) of each run.
    """,
    examples=(
        'target new and "lamp only when both A and B are on"',
        "target and truth @A @B -> @OUT rows 00:0 01:0 10:0 11:1",
        'target new clock "the clock pulses every 4 ticks"',
        "target clock do pulse @START at 1 for 1",
        "target clock expect @OUT powered=true within 2..6",
        "target and load 11",
    ),
    kind="meta",
    data='{"target": {"name", "description", "cases": [{"name", "lines"}]}}',
)
def target(session: Session, args: Args) -> Output:
    doc = session.doc
    first = args.word("new or a target name")
    if first == "new":
        name = args.word("a target name")
        description = " ".join(args.rest())
        if any(t["name"] == name for t in doc.targets):
            raise CliError(f"target: {name!r} exists (target {name} delete, or another name)")
        doc.targets.append(
            {"name": name, "description": description, "cases": [{"name": "main", "lines": []}]}
        )
        return _changed(session, name, f"new target {name}")
    entry = model.find(doc, first)
    verb = args.choice(("do", "expect", "truth", "show", "remove", "delete", "load"), "what to do")
    if verb == "show":
        args.done()
        return _show(session, entry)
    if verb == "delete":
        args.done()
        doc.targets.remove(entry)
        session.changed = True
        doc.dirty = True
        return Output([f"deleted target {first}"], {"target": None})
    if verb == "remove":
        number = args.number("a line number")
        args.done()
        lines = _numbered(entry)
        if not 1 <= number <= len(lines):
            raise CliError(f"target: {first} has no line {number} (see: target {first} show)")
        case_name, line = lines[number - 1]
        for case in entry["cases"]:
            if (case["name"] == case_name or case_name == "*") and line in case["lines"]:
                case["lines"].remove(line)
        return _changed(session, first, f"removed line {number}: {line}")
    if verb == "load":
        case_name = args.word("a case") if args.more() else entry["cases"][0]["name"]
        args.done()
        return _load(session, entry, case_name)
    if verb == "truth":
        return _truth(session, entry, args)
    words = args.rest()
    if not words:
        raise CliError(f"target {first} {verb}: what? (see: help target)")
    line = join_words(["expect", *words] if verb == "expect" else words)
    model.check_line(line, doc)
    for case in entry["cases"]:
        case["lines"].append(line)
    return _changed(session, first, f"{first}: {line}")


def _changed(session: Session, name: str, text: str) -> Output:
    session.changed = True
    session.doc.dirty = True
    entry = model.find(session.doc, name)
    return Output([text], {"target": entry})


def _numbered(entry: dict[str, Any]) -> list[tuple[str, str]]:
    """The target's lines, numbered across cases; a line in every case counts once."""
    cases = entry["cases"]
    shared = [line for line in cases[0]["lines"] if all(line in c["lines"] for c in cases)]
    out: list[tuple[str, str]] = [("*", line) for line in shared]
    if len(cases) > 1:
        for case in cases:
            out += [(case["name"], line) for line in case["lines"] if line not in shared]
    return out


def _show(session: Session, entry: dict[str, Any]) -> Output:
    out = Output([f"target {entry['name']}: {entry.get('description') or '(no description)'}"])
    for number, (case_name, line) in enumerate(_numbered(entry), 1):
        where = "" if case_name == "*" else f"[{case_name}] "
        out.add(f"  {number:>3}. {where}{line}")
    if len(entry["cases"]) > 1:
        out.add(f"  cases: {', '.join(c['name'] for c in entry['cases'])}")
    out.data = {"target": entry}
    return out


def _truth(session: Session, entry: dict[str, Any], args: Args) -> Output:
    doc = session.doc
    inputs: list[tuple[str, Any, bool]] = []
    while args.more() and args.peek() != "->":
        word = args.peek() or ""
        pos = args.pos("an input")
        inputs.append((word if word.startswith("@") else "{} {} {}".format(*pos), pos, False))
    if not args.option("->"):
        raise CliError("truth: write the inputs, then ->, then the outputs")
    outputs: list[str] = []
    while args.more() and args.peek() != "rows":
        word = args.peek() or ""
        pos = args.pos("an output")
        outputs.append(word if word.startswith("@") else "{} {} {}".format(*pos))
    if not args.option("rows"):
        raise CliError("truth: list the rows after 'rows', like 00:0 01:0 10:0 11:1")
    rows = []
    while args.more() and args.peek() != "settle":
        rows.append(args.word())
    settle = args.option_int("settle", model.DEFAULT_SETTLE)
    args.done()
    if not inputs or not outputs or not rows:
        raise CliError("truth: needs inputs, outputs and rows")
    base = doc.history.base.level
    resolved = []
    for name, pos, _ in inputs:
        state = base.get_block_state(pos)
        resolved.append((name, pos, state.block.id == "minecraft:lever"))
        if state.block.id == "minecraft:lever" and state.properties_dict().get("powered") == "true":
            raise CliError(f"truth: the lever {name} is on in the build; switch it off first")
    shared = [
        line
        for line in entry["cases"][0]["lines"]
        if all(line in c["lines"] for c in entry["cases"])
    ]
    cases = model.truth_cases(resolved, outputs, rows, settle)
    for case in cases:
        case["lines"] = shared + case["lines"]
    entry["cases"] = cases
    return _changed(
        session,
        entry["name"],
        f"{entry['name']}: {len(cases)} cases from the truth table "
        f"(outputs checked at tick {1 + settle})",
    )


def _load(session: Session, entry: dict[str, Any], case_name: str) -> Output:
    case = next((c for c in entry["cases"] if c["name"] == case_name), None)
    if case is None:
        raise CliError(
            f"target load: no case {case_name!r} "
            f"(cases: {', '.join(c['name'] for c in entry['cases'])})"
        )
    doc = session.doc
    if doc.history.inputs:
        doc.delete_edits(list(doc.history.inputs))
    count = 0
    for line in case["lines"]:
        for words in split_commands(line):
            if words[0] == "expect":
                continue
            session.edit_tick = 0
            session.execute(words)
            count += 1
    session.edit_tick = 0
    session.changed = True
    return Output(
        [
            f"loaded {count} stimuli of {entry['name']} [{case_name}] onto the timeline "
            "(undo restores the old one)"
        ],
        {"target": entry["name"], "case": case_name, "stimuli": count},
    )


@command(
    "targets",
    group="targets",
    usage="targets",
    summary="List the targets with their cases.",
    help="Lists every target: its name, description and cases.",
    examples=("targets",),
    kind="view",
    data='{"targets": [{"name", "description", "cases": [names]}]}',
)
def targets(session: Session, args: Args) -> Output:
    args.done()
    doc = session.doc
    out = Output()
    for entry in doc.targets:
        cases = ", ".join(c["name"] for c in entry["cases"])
        out.add(
            f"  {entry['name']}: {entry.get('description') or ''}  "
            f"({len(entry['cases'])} cases: {cases})"
        )
    if not doc.targets:
        out.add("  (no targets yet: target new NAME)")
    out.data = {
        "targets": [
            {
                "name": t["name"],
                "description": t.get("description", ""),
                "cases": [c["name"] for c in t["cases"]],
            }
            for t in doc.targets
        ]
    }
    return out


@command(
    "check",
    group="targets",
    usage="check [NAME ...] [verbose]",
    summary="Run the targets from the build and report what passes and what fails.",
    help="""
    Runs every case of the named targets (default: all) in a copy of the world from the
    build (tick 0), with the case's stimuli instead of the world's own timeline, and
    evaluates each expectation at its ticks. Prints PASS or FAIL per case; for a failing
    expectation the ticks where it failed and the values seen there, plus the block's
    values over the expectation's range (as `waves` would show them). `verbose` lists
    passing expectations too. The world itself is not changed.

    The exit code is 1 when any case fails, so scripts can stop on it.
    """,
    examples=("check", "check and clock", "check and verbose"),
    kind="view",
    data="""{"passed": cases passed, "failed": cases failed, "cases": [{"target", "case",
    "passed", "error", "expectations": [{"line", "passed", "failing_ticks", "observed":
    {tick: value}, "problem"}]}]}""",
)
def check(session: Session, args: Args) -> Output:
    doc = session.doc
    names: list[str] = []
    verbose = False
    while args.more():
        if args.option("verbose"):
            verbose = True
        else:
            names.append(args.word())
    chosen = [model.find(doc, n) for n in names] if names else list(doc.targets)
    if not chosen:
        raise CliError("check: no targets yet (target new NAME …)")
    results = [model.run_case(doc, t["name"], c) for t in chosen for c in t["cases"]]
    passed = sum(r.passed for r in results)
    cases = "1 case" if len(results) == 1 else f"{len(results)} cases"
    out = Output([f"check: {cases}, {passed} passed, {len(results) - passed} failed"])
    for r in results:
        title = r.target if r.case == "main" else f"{r.target} [{r.case}]"
        out.add(f"{'PASS' if r.passed else 'FAIL'}  {title}")
        if r.error:
            out.add(f"      {r.error}")
        for e in r.results:
            if e.passed and not verbose:
                continue
            mark = "ok  " if e.passed else "fail"
            out.add(f"      {mark} {e.expectation.text}")
            if e.problem:
                out.add(f"           {e.problem}")
            elif not e.passed:
                failing = e.failing_ticks()
                seen = ", ".join(
                    f"tick {t}: {e.expectation.key}={_fmt(e.observed[t])}" for t in failing[:6]
                )
                out.add(f"           saw {seen}" + (" …" if len(failing) > 6 else ""))
                numbers = [v for v in e.observed.values() if not isinstance(v, bool)]
                if len(numbers) == len(e.observed) and all(
                    isinstance(v, int) and 0 <= v <= 15 for v in numbers
                ):
                    values = [int(v) for v in numbers]
                    out.add(
                        f"           ticks {e.expectation.low}..{e.expectation.high}: "
                        f"{wave_row(values)}"
                    )
    if passed < len(results):
        out.add("hint: 'target NAME load CASE' puts a case on the timeline; then waves, why, show")
    out.data = {
        "passed": passed,
        "failed": len(results) - passed,
        "cases": [
            {
                "target": r.target,
                "case": r.case,
                "passed": r.passed,
                "error": r.error,
                "expectations": [
                    {
                        "line": e.expectation.text,
                        "passed": e.passed,
                        "failing_ticks": e.failing_ticks(),
                        "observed": {str(t): v for t, v in e.observed.items()},
                        "problem": e.problem,
                    }
                    for e in r.results
                ],
            }
            for r in results
        ],
    }
    session.failed_check = passed < len(results)
    return out


def _fmt(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


__all__ = ["check", "name_of", "target", "targets"]
