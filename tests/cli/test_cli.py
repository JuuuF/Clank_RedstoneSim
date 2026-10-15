"""``redsim-cli`` (doc/cli.md): the language, the session rules and the commands, run the
way agents and people run them (``main`` with arguments, ``-c`` or standard input)."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from redsim.cli.language import Args, CliError, parse_block, split_commands
from redsim.cli.main import main


class Run:
    """``redsim-cli WORLD …`` with captured output."""

    def __init__(self, tmp: Path) -> None:
        self.world = tmp / "w.redsim.json"

    def __call__(self, *args: str, stdin: str = "", code: int = 0) -> str:
        out = io.StringIO()
        result = main([str(self.world), *args], stdin=_Stdin(stdin), out=out)
        text = out.getvalue()
        assert result == code, text
        return text

    def batch(self, text: str, code: int = 0) -> str:
        return self("-c", text, code=code)


class _Stdin(io.StringIO):
    def isatty(self) -> bool:
        return False


@pytest.fixture
def rs(tmp_path: Path) -> Run:
    run = Run(tmp_path)
    run("new", "size", "16")
    return run


NOT_GATE = (
    "place 0 1 0 lever face=floor; place 1 1 0 redstone_wire; place 2 1 0 stone; "
    "place 3 1 0 redstone_wall_torch facing=east; place 4 1 0 redstone_wire; "
    "place 5 1 0 redstone_lamp; label A 0 1 0 lever; label OUT 5 1 0 lamp"
)


# ---------------------------------------------------------------------------- language
def test_commands_split_on_lines_and_semicolons_with_quotes_and_comments() -> None:
    text = 'place 0 1 0 stone; note "a; b # c" # comment\n\nrun 3'
    assert list(split_commands(text)) == [
        ["place", "0", "1", "0", "stone"],
        ["note", "a; b # c"],
        ["run", "3"],
    ]


def test_positions_labels_and_offsets() -> None:
    from redsim.editor.document import Document

    doc = Document.new_flat()
    doc.set_label("A", (3, 1, -2))
    args = Args(["1", "2", "3", "4,5,6", "@A", "@A+1,0,-1", "@A-2,0,0"], doc, "test")
    assert [args.pos() for _ in range(5)] == [
        (1, 2, 3), (4, 5, 6), (3, 1, -2), (4, 1, -3), (1, 1, -2)
    ]  # fmt: skip
    with pytest.raises(CliError, match="no label @B"):
        Args(["@B"], doc, "test").pos()


def test_blocks_with_properties_out_alias_and_helpful_errors() -> None:
    state = parse_block("repeater", ["out=east", "delay=3"])
    assert repr(state) == "minecraft:repeater[facing=west,delay=3,locked=false,powered=false]"
    assert parse_block("minecraft:observer[facing=up]").properties_dict()["facing"] == "up"
    with pytest.raises(CliError, match="did you mean redstone_lamp"):
        parse_block("redstone_lmp")
    with pytest.raises(CliError, match="values: 1, 2, 3, 4"):
        parse_block("repeater[delay=9]")
    assert parse_block("tnt").block.id == "minecraft:tnt"  # a foreign (inert) block


# ---------------------------------------------------------------------------- building
def test_build_a_not_gate_and_read_its_map(rs: Run) -> None:
    out = rs.batch(NOT_GATE + "; show y=1")
    assert "placed 5 1 0: redstone_lamp[lit=true] (the build)" in out
    assert "z=  0  .. v. w0 ## T> wf L. .." in out
    assert "L/l  redstone lamp" in out


def test_edits_after_running_still_change_the_build(rs: Run) -> None:
    rs.batch(NOT_GATE)
    rs("run", "20")
    out = rs("place", "6", "1", "0", "stone")
    assert "(the build)" in out
    assert "tick 20 of 20" in rs("where")
    assert "the timeline is empty" in rs("edits")


def test_timeline_edits_waves_and_why(rs: Run) -> None:
    rs.batch(NOT_GATE)
    rs.batch("at 3 use @A; at 12 use @A; run 20")
    out = rs("waves")
    assert "@A lever            ...fffffffff........." in out
    assert "@OUT redstone_lamp  fffffffff.....fffffff" in out
    edits = rs("edits")
    assert "E1   tick 3" in edits and "E2   tick 12" in edits
    why = rs("why", "@OUT")
    assert "last changed at tick 14: redstone lamp: lit false → true" in why
    assert "edit or player action: use" in why
    assert "t> w0 L." in rs("at", "5", "show", "y=1")  # torch off, lamp still lit (off at 9)
    assert "tick 20 of 20" in rs("where")


def test_moving_and_deleting_edits(rs: Run) -> None:
    rs.batch(NOT_GATE + "; at 3 use @A; at 12 use @A; run 20")
    rs("edit", "move", "E2", "to", "15")
    assert "E2   tick 15" in rs("edits")
    rs("edit", "delete", "all")
    assert "the timeline is empty" in rs("edits")


def test_pulses_drive_inputs(rs: Run) -> None:
    rs.batch("place 0 1 0 redstone_lamp; label L 0 1 0")
    rs("pulse", "@L", "at", "2", "for", "3")
    out = rs("waves", "@L", "ticks", "0..10")
    assert "@L redstone_lamp  ..fffffff.." in out  # on at tick 2 (the pulse), off at 2+3+4+0
    assert "power 15 for 3 ticks" in rs("edits")


def test_step_shows_the_order_inside_a_tick(rs: Run) -> None:
    rs.batch(NOT_GATE + "; at 1 use @A; run 2")  # the torch's tick is due in tick 3
    out = rs("step")
    assert "step" in out and "tick start" in out and "inside tick 3" in out
    assert "inside tick 3 (1 step after tick 2)" in rs("where")  # saved inside the tick
    out = rs("step")
    assert "scheduled tick at 3 1 0 redstone_wall_torch" in out
    assert (
        "redstone_wall_torch[facing=east,lit=true] → redstone_wall_torch[facing=east,lit=false]"
        in out
    )
    assert "tick 3 is complete" in out  # nothing else happens in tick 3


def test_inspect_reports_signals_by_side(rs: Run) -> None:
    rs.batch(NOT_GATE)
    out = rs("inspect", "4", "1", "0")
    assert "receives  down 15, west 15, east 15" in out  # the torch at the west
    assert "east 15 (direct 15)" in out
    data = json.loads(rs("--json", "inspect", "@OUT").splitlines()[0])
    assert data["ok"] and data["data"]["blocks"][0]["state"] == "redstone_lamp[lit=true]"


def test_diff_find_ticks_and_info(rs: Run) -> None:
    rs.batch(NOT_GATE + "; at 3 use @A; run 10")
    assert "redstone_lamp[lit=true] → redstone_lamp[lit=false]" in rs("diff", "0")
    assert "2 × redstone_wire" in rs("find", "redstone_wire")
    assert "scheduled ticks" in rs("at", "3", "ticks")
    info = rs("info")
    assert "@A 0 1 0" in info and "1 recorded edits" in info


# ---------------------------------------------------------------------------- targets
def test_truth_table_targets_pass_and_failures_explain_themselves(rs: Run) -> None:
    rs.batch(NOT_GATE)
    rs.batch(
        "target new not 'lamp is the inverse of the lever'; target not truth @A -> @OUT rows 0:1 1:0"
    )
    assert "2 passed, 0 failed" in rs("check")
    rs.batch(
        "target new wrong; target wrong do at 2 use @A; target wrong expect @OUT lit=true at 9"
    )
    out = rs("check", "wrong", code=1)
    assert "FAIL  wrong" in out and "saw tick 9: lit=false" in out
    shown = rs("target", "wrong", "show")
    assert "1. at 2 use @A" in shown and "2. expect @OUT lit=true at 9" in shown


def test_targets_do_not_touch_the_world_timeline(rs: Run) -> None:
    rs.batch(
        NOT_GATE
        + "; target new t; target t do at 2 use @A; target t expect @OUT lit=false within 3..10"
    )
    rs("check")
    assert "the timeline is empty" in rs("edits")
    rs("target", "t", "load")
    assert "E1   tick 2" in rs("edits")


def test_target_lines_are_validated_when_added(rs: Run) -> None:
    rs("target", "new", "t")
    assert "is not a stimulus" in rs("target", "t", "do", "show", code=1)
    assert "not KEY=VALUE" in rs("target", "t", "expect", "0", "1", "0", "lit", "at", "3", code=1)


# ---------------------------------------------------------------------------- files
def test_json_mode_prints_one_object_per_command(rs: Run) -> None:
    out = rs("--json", "-c", "place 0 1 0 stone; place 0 1 0 stone", code=1)
    first, second = (json.loads(line) for line in out.splitlines())
    assert first["ok"] and first["data"]["state"] == "stone"
    assert not second["ok"] and "holds stone" in second["error"]


def test_scripts_on_standard_input(rs: Run) -> None:
    out = rs(stdin="place 0 1 0 stone\n# a comment\nplace 1 1 0 stone\n")
    assert out.count("> place") == 2


def test_undo_within_a_run_and_across_runs(rs: Run) -> None:
    rs.batch("place 0 1 0 stone; place 1 1 0 stone; undo")
    assert "1 × stone" in rs("find", "stone", "in", "-5", "1", "-5", "5", "1", "5")
    rs("place", "2", "1", "0", "stone")
    assert "2 × stone" in rs("find", "stone", "in", "-5", "1", "-5", "5", "1", "5")
    rs("undo")  # the previous run
    assert "1 × stone" in rs("find", "stone", "in", "-5", "1", "-5", "5", "1", "5")
    rs("redo")
    assert "2 × stone" in rs("find", "stone", "in", "-5", "1", "-5", "5", "1", "5")


def test_the_world_file_is_the_editors_format(rs: Run) -> None:
    from redsim.editor.document import Document

    rs.batch(NOT_GATE + "; at 3 use @A; run 6; target new t; note 'a NOT gate'")
    doc = Document.open(rs.world)
    assert doc.tick == 6 and doc.labels["OUT"].pos == (5, 1, 0)
    assert doc.notes == ["a NOT gate"] and doc.targets[0]["name"] == "t"
    assert "at 3 use @A" in doc.extra["cli"]["log"]


def test_export_and_import_schematics(rs: Run, tmp_path: Path) -> None:
    rs.batch(NOT_GATE)
    target = tmp_path / "not.litematic"
    assert "wrote 6 blocks" in rs("export", str(target))
    out = rs("import", str(target), "at", "0", "1", "5")
    assert "imported 6 blocks" in out
    assert "2 × redstone_lamp" in rs("find", "redstone_lamp")


def test_errors_say_what_is_wrong(rs: Run) -> None:
    assert "unknown command 'plac'" in rs("plac", "0", "1", "0", code=1)
    assert "did you mean" in rs("place", "0", "1", "0", "redstone_lmp", code=1)
    rs("place", "0", "1", "0", "stone")
    assert "holds stone" in rs("place", "0", "1", "0", "stone", code=1)


def test_the_reference_document_is_generated_from_the_help() -> None:
    from redsim.cli.registry import render_reference

    path = Path(__file__).resolve().parents[2] / "doc" / "cli-reference.md"
    assert path.read_text() == render_reference(), (
        "doc/cli-reference.md is out of date: redsim-cli help --markdown > doc/cli-reference.md"
    )
