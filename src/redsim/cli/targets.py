"""Targets: acceptance tests for contraptions (doc/cli.md, "Targets").

A target says what a contraption must do. It is stored in the world file
(``Document.targets``, plain JSON) as command lines, so it reads like the commands a
person would type:

    {"name": "and", "description": "lamp only with both inputs",
     "cases": [{"name": "11", "lines": ["at 1 use @A", "at 1 use @B",
                                        "expect @OUT lit=true at 11"]}, ...]}

Each **case** is one run. Its lines are of two kinds:

* **stimuli** (``do`` lines): editing commands that happen in that run: ``pulse POS at T
  …``, ``at T COMMAND`` (``use``, ``set``, ``plate``, ``hit``, …), or an edit without
  ``at`` that changes the build for that run only;
* **expectations**: ``expect POS CONDITION WHEN``, where CONDITION is ``KEY OP VALUE``
  (``lit=true``, ``power>=1``, ``block=piston``; OP is ``=``, ``!=``, ``<``, ``<=``,
  ``>``, ``>=``) and WHEN is ``at T`` (that tick), ``during A..B`` (every tick of the
  range) or ``within A..B`` (at least one tick of it). KEY is a block property, or
  ``block`` (the block id), ``power`` (the monitor value, as ``waves`` shows it),
  ``signal`` (the strongest signal the block receives) or ``direct`` (the direct power
  into it: how much a solid block is powered).

``check`` runs every case **from the build, in a copy** of the world: the timeline of the
world itself is not used and not changed. It applies the case's stimuli, simulates to the
last tick an expectation needs, and evaluates every expectation at its ticks. The result
names each failing expectation with the values it saw.

A **truth table** (``target NAME truth``) makes one case per row: inputs that are 1 are
switched on at tick 1 (a lever by using it, any other block by a power pulse that lasts
to the end of the run), and each output is expected on (``power>=1``) or off
(``power=0``) at tick 1 + settle (default 10).
"""

from __future__ import annotations

import operator
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from redsim.cli.language import Args, CliError, join_words, split_commands
from redsim.core.pos import Pos

if TYPE_CHECKING:
    from redsim.editor.document import Document

OPS: dict[str, Callable[[Any, Any], bool]] = {
    "=": operator.eq,
    "!=": operator.ne,
    "<=": operator.le,
    ">=": operator.ge,
    "<": operator.lt,
    ">": operator.gt,
}
_CONDITION = re.compile(r"([a-z_]+)(!=|<=|>=|=|<|>)(.+)$")
#: Keys that are not block properties.
PSEUDO_KEYS = ("block", "power", "signal", "direct")
DEFAULT_SETTLE = 10


# ---------------------------------------------------------------------------- model
@dataclass(frozen=True)
class Expectation:
    pos: Pos
    key: str
    op: str
    value: str
    when: str  # "at", "during" or "within"
    low: int
    high: int
    text: str  # the line as written

    def holds(self, observed: Any) -> bool:
        expected: Any = self.value
        if isinstance(observed, int) and not isinstance(observed, bool):
            try:
                expected = int(self.value)
            except ValueError:
                return False
        elif isinstance(observed, bool):
            observed = "true" if observed else "false"
        return OPS[self.op](observed, expected)


def parse_expectation(words: list[str], document: Document | None) -> Expectation:
    """``expect POS KEY<OP>VALUE at T | during A..B | within A..B`` (without ``expect``)."""
    args = Args(list(words), document, "expect")
    pos = args.pos()
    condition = args.word("a condition like lit=true or power>=1")
    match = _CONDITION.match(condition)
    if not match:
        raise CliError(f"expect: {condition!r} is not KEY=VALUE (or !=, <, <=, >, >=)")
    key, op, value = match[1], match[2], match[3]
    if (
        op not in ("=", "!=")
        and key not in ("power", "signal", "direct")
        and not value.lstrip("-").isdigit()
    ):
        raise CliError(f"expect: {op} compares numbers; {key}={value} is not a number")
    when = args.choice(("at", "during", "within"), "at, during or within")
    low, high = args.tick_range()
    if when == "at" and low != high:
        when = "during"
    args.done()
    return Expectation(pos, key, op, value, when, low, high, join_words(["expect", *words]))


def is_stimulus(words: list[str]) -> bool:
    from redsim.cli.registry import lookup

    cmd = lookup(words[0]) if words else None
    if cmd is None:
        return False
    if cmd.name == "pulse":
        return True
    if cmd.name == "at":
        inner = lookup(words[2]) if len(words) > 2 else None
        return inner is not None and inner.kind == "edit"
    return cmd.kind == "edit"


def check_line(line: str, document: Document | None) -> None:
    """Raise ``CliError`` unless ``line`` is a valid stimulus or expectation."""
    for words in split_commands(line):
        if words[0] == "expect":
            parse_expectation(words[1:], document)
        elif not is_stimulus(words):
            raise CliError(
                f"target: {words[0]!r} is not a stimulus (pulse, at T COMMAND, or an edit) "
                "nor an expectation (expect …)"
            )


def find(document: Document, name: str) -> dict[str, Any]:
    for target in document.targets:
        if target["name"] == name:
            return target
    known = ", ".join(t["name"] for t in document.targets) or "none yet"
    raise CliError(f"no target {name!r} (targets: {known})")


# ---------------------------------------------------------------------------- running
@dataclass
class ExpectationResult:
    expectation: Expectation
    passed: bool
    observed: dict[int, Any] = field(default_factory=dict)
    problem: str = ""

    def failing_ticks(self) -> list[int]:
        return [t for t, v in self.observed.items() if not self.expectation.holds(v)]


@dataclass
class CaseResult:
    target: str
    case: str
    results: list[ExpectationResult]
    error: str = ""

    @property
    def passed(self) -> bool:
        return not self.error and all(r.passed for r in self.results)


def observe(level: Any, pos: Pos, key: str) -> Any:
    """The value an expectation's KEY has for the block at ``pos``."""
    from redsim.cli.views import prop
    from redsim.editor.monitor import monitor_value

    state = level.get_block_state(pos)
    if key == "block":
        return state.block.id.removeprefix("minecraft:")
    if key == "power":
        return monitor_value(level, pos)
    if key == "signal":
        return level.get_best_neighbor_signal(pos)
    if key == "direct":
        return level.get_direct_signal_to(pos)
    value = prop(state, key)
    if value is None:
        return None
    if isinstance(value, bool | int | str):
        return value
    return getattr(value, "serialized", str(value))


def case_document(document: Document) -> Document:
    """A copy of the world at its build, with its labels, and no timeline."""
    from redsim.editor.document import Document
    from redsim.sim.engine import Engine

    engine = Engine()
    engine.restore(document.history.base)
    copy = Document(engine=engine)
    copy.labels = dict(document.labels)
    return copy


def run_case(document: Document, target: str, case: dict[str, Any]) -> CaseResult:
    """Run one case from the build in a copy and evaluate its expectations."""
    from pathlib import Path

    from redsim.cli.session import Session

    copy = case_document(document)
    session = Session(Path(document.path or "target.redsim.json"), dry_run=True)
    session.adopt(copy)
    expectations: list[Expectation] = []
    try:
        for line in case["lines"]:
            for words in split_commands(line):
                if words[0] == "expect":
                    expectations.append(parse_expectation(words[1:], copy))
                else:
                    session.edit_tick = 0
                    session.execute(words)
        session.restore_view()
        end = max([e.high for e in expectations], default=0)
        needed: dict[int, list[Expectation]] = {}
        for e in expectations:
            for tick in range(e.low, e.high + 1):
                needed.setdefault(tick, []).append(e)
        observed: dict[Expectation, dict[int, Any]] = {e: {} for e in expectations}
        for tick in range(0, end + 1):
            if tick not in needed:
                continue
            session.goto(tick)
            for e in needed[tick]:
                observed[e][tick] = observe(copy.level, e.pos, e.key)
    except CliError as exc:
        session.close()
        return CaseResult(target, case["name"], [], f"the case could not run: {exc}")
    session.close()
    results = []
    for e in expectations:
        values = observed[e]
        if any(v is None for v in values.values()):
            state = copy.level.get_block_state(e.pos).block.name
            results.append(ExpectationResult(e, False, values, f"{state} has no {e.key}"))
            continue
        holds = [e.holds(v) for v in values.values()]
        passed = any(holds) if e.when == "within" else all(holds)
        results.append(ExpectationResult(e, passed, values))
    return CaseResult(target, case["name"], results)


def truth_cases(
    inputs: list[tuple[str, Pos, bool]],
    outputs: list[str],
    rows: list[str],
    settle: int,
) -> list[dict[str, Any]]:
    """One case per row ``BITS:BITS`` (inputs, then outputs). ``inputs`` are (name, pos,
    is a lever)."""
    cases = []
    check_at = 1 + settle
    for row in rows:
        ins, sep, outs = row.partition(":")
        if (
            not sep
            or len(ins) != len(inputs)
            or len(outs) != len(outputs)
            or set(ins + outs) - {"0", "1"}
        ):
            raise CliError(
                f"truth: row {row!r} must be {len(inputs)} input bits, ':', "
                f"{len(outputs)} output bits (like 10:1)"
            )
        lines = []
        for (name, _, lever), bit in zip(inputs, ins, strict=True):
            if bit == "1":
                lines.append(f"at 1 use {name}" if lever else f"pulse {name} at 1 for {settle + 1}")
        for name, bit in zip(outputs, outs, strict=True):
            condition = "power>=1" if bit == "1" else "power=0"
            lines.append(f"expect {name} {condition} at {check_at}")
        cases.append({"name": row, "lines": lines})
    return cases
