"""The example scripts in examples/cli/ (doc/cli.md, "Workflows") run on a new world and
every target in them passes."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from redsim.cli.main import main

EXAMPLES = sorted((Path(__file__).resolve().parents[2] / "examples" / "cli").glob("*.cli.txt"))


class _Stdin(io.StringIO):
    def isatty(self) -> bool:
        return False


@pytest.mark.parametrize("script", EXAMPLES, ids=[p.name.split(".")[0] for p in EXAMPLES])
def test_example_script_runs_and_its_targets_pass(script: Path, tmp_path: Path) -> None:
    world = tmp_path / "w.redsim.json"
    assert main([str(world), "new", "size", "16"], out=io.StringIO()) == 0
    out = io.StringIO()
    code = main([str(world)], stdin=_Stdin(script.read_text()), out=out)
    text = out.getvalue()
    assert code == 0, text
    assert "error:" not in text and "FAIL" not in text
    assert "check:" in text


def test_shell_runs_lines_and_saves(tmp_path: Path) -> None:
    world = tmp_path / "w.redsim.json"
    main([str(world), "new"], out=io.StringIO())
    lines = iter(["place 0 1 0 stone; where", "place 1 1 0 nope", "exit"])
    out = io.StringIO()

    def read(prompt: str) -> str:
        return next(lines)

    from redsim.cli.session import Session

    session = Session(world, out=out)
    session.open()
    assert session.interactive(read) == 1  # one line failed
    assert "placed 0 1 0: stone" in out.getvalue() and "unknown block" in out.getvalue()
    assert "1 × stone" in _run(world, "find", "stone", "in", "0", "1", "0", "0", "1", "0")


def _run(world: Path, *args: str) -> str:
    out = io.StringIO()
    main([str(world), *args], out=out)
    return out.getvalue()
