"""The redstone research scripts (doc/redstone/README.md) still reproduce what they record.

Every experiment script in experiments/redstone/ and every circuit in examples/circuits/
creates its own world (its first command is `new … force`), builds, and ends with a
`check` whose targets hold the observed behavior. A failure here means the simulator
no longer behaves as the knowledge base says: re-run the script, then fix the record or
the simulator.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from redsim.cli.main import main

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = sorted((ROOT / "experiments" / "redstone").glob("*.cli.txt")) + sorted(
    (ROOT / "examples" / "circuits").glob("*.cli.txt")
)


class _Stdin(io.StringIO):
    def isatty(self) -> bool:
        return False


@pytest.mark.parametrize("script", SCRIPTS, ids=[p.name.split(".")[0] for p in SCRIPTS])
def test_research_script_reproduces_its_record(script: Path, tmp_path: Path) -> None:
    out = io.StringIO()
    code = main([str(tmp_path / "w.redsim.json")], stdin=_Stdin(script.read_text()), out=out)
    text = out.getvalue()
    assert code == 0, text
    assert "error:" not in text and "FAIL" not in text
    assert "check:" in text
