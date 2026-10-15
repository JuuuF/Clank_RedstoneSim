"""doc/differences.md lists every difference from the game; each source file it names must
mark the difference where it happens (``Not as in the game:``, doc/implementation-notes.md)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "redsim"


def test_every_file_named_in_the_differences_page_marks_its_difference() -> None:
    text = (ROOT / "doc" / "differences.md").read_text()
    names = sorted(set(re.findall(r"`([\w/]+\.py)", text)))
    assert names, "the page names no source files"
    for name in names:
        files = [p for p in SOURCE.rglob("*.py") if p.as_posix().endswith("/" + name)]
        assert files, f"{name} (named in doc/differences.md) does not exist"
        assert any("Not as in the game" in p.read_text() for p in files), (
            f"{name} is named in doc/differences.md but has no 'Not as in the game' marker"
        )
