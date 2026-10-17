"""Opening worlds in the background behind the loading screen, and its progress reports."""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["REDSIM_KEYMAP"] = os.devnull + ".missing"  # defaults, not the user's keymap
os.environ["REDSIM_CONFIG_DIR"] = os.devnull + ".missing"  # default preferences, never saved
QtWidgets = pytest.importorskip("PySide6.QtWidgets")
from PySide6.QtCore import QEvent, Qt  # noqa: E402
from PySide6.QtGui import QKeyEvent  # noqa: E402

from redsim.editor.clipboard import Region  # noqa: E402
from redsim.editor.document import Document  # noqa: E402
from redsim.io import save as save_io  # noqa: E402
from redsim.ui.app import configure_gl  # noqa: E402
from redsim.world import blocks  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
AND_GATE = ROOT / "examples" / "cli" / "and_gate.redsim.json"


@pytest.fixture(scope="module")
def app() -> Iterator[object]:
    configure_gl()
    instance = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield instance


class Reports:
    def __init__(self) -> None:
        self.seen: list[tuple[str, int, int]] = []

    def __call__(self, stage: str, done: int, total: int) -> None:
        self.seen.append((stage, done, total))

    def stages(self) -> list[str]:
        out: list[str] = []
        for stage, _, _ in self.seen:
            if not out or out[-1] != stage:
                out.append(stage)
        return out


def test_opening_a_world_reports_reading_and_its_blocks() -> None:
    reports = Reports()
    document = Document.open(AND_GATE, reports)
    assert reports.stages() == ["read", "world"]
    count = len(document.level.blocks)
    assert reports.seen[-1] == ("world", count, count)


def test_blocks_are_read_in_batches_with_a_report_each(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(save_io, "REPORT_BLOCKS", 100)
    reports = Reports()
    document = Document.open(AND_GATE, reports)
    world = [done for stage, done, _ in reports.seen if stage == "world"]
    assert world == sorted(world) and world[-1] == len(document.level.blocks)
    assert len(world) == len(document.level.blocks) // 100 + 2  # every batch, and the end
    assert document.level.blocks == Document.open(AND_GATE).level.blocks


def test_recorded_edits_report_each_tick_when_reopened(tmp_path: Path) -> None:
    doc = Document.new_flat()
    doc.setblock((0, 1, 0), blocks.parse_state("lever[face=floor,facing=north]"))
    doc.setblock((1, 1, 0), blocks.parse_state("redstone_lamp"))
    doc.run_ticks(3)
    doc.use((0, 1, 0))  # recorded at tick 3
    doc.run_ticks(5)
    path = tmp_path / "edits.redsim.json"
    doc.save(path)
    reports = Reports()
    Document.open(path, reports)
    ticks = [(done, total) for stage, done, total in reports.seen if stage == "history"]
    assert ticks and ticks[-1][0] == ticks[-1][1] == 8
    assert [done for done, _ in ticks] == sorted(done for done, _ in ticks)


def test_chunk_meshes_report_each_chunk() -> None:
    from redsim.ui.geometry import ChunkedMesh

    document = Document.open(AND_GATE)
    reports = Reports()
    mesh = ChunkedMesh()
    mesh.update(document.level, reports)
    total = reports.seen[-1][2]
    assert reports.stages() == ["meshes"] and reports.seen[-1] == ("meshes", total, total)
    assert len(mesh.chunks) <= total


def test_progress_fills_once_and_inserts_stages_it_did_not_expect() -> None:
    from redsim.ui.loading import LoadCancelled, LoadProgress

    progress = LoadProgress(["read", "world", "meshes"])
    progress("read", 1, 1)
    progress("world", 50, 100)
    halfway = progress.fraction()
    progress("history", 0, 10)  # a world with recorded edits: before the meshes
    assert progress.stages == ["read", "world", "history", "meshes"]
    progress("world", 0, 100)  # the history's own base engine reports its blocks again
    assert progress.fraction() >= halfway  # the bar does not move back
    assert progress.text() == "Building the world: 0 of 100 blocks"
    progress("meshes", 10, 10)
    assert progress.fraction() == pytest.approx(1.0)
    progress.cancel()
    with pytest.raises(LoadCancelled):
        progress("meshes", 10, 10)


def test_a_world_opens_behind_the_loading_screen(app: object) -> None:
    from redsim.ui.geometry import ChunkedMesh, Mesher
    from redsim.ui.icons import cached_prefab_pixmap
    from redsim.ui.loading import LoadingScreen
    from redsim.ui.main_window import MainWindow
    from redsim.ui.panel_circuit import PREVIEW_SIZE

    window = MainWindow()
    window.resize(1000, 700)
    window.show()
    run = window.load_path(AND_GATE)
    assert run is not None and window.loading is run
    assert window.findChild(LoadingScreen) is not None  # shown while it loads
    assert window.load_path(AND_GATE) is None  # one at a time
    run.wait()
    assert window.loading is None
    document = window.document
    assert document.path == AND_GATE and document.labels["A"]
    # The view shows the meshes the loading thread made, all of them.
    viewport = window.viewport
    fresh = ChunkedMesh(Mesher(viewport.assets, viewport.atlas))
    fresh.update(document.level)
    assert set(viewport.world_mesh.chunks) == set(fresh.chunks)
    assert viewport._upload_all  # uploaded whole on the next frame
    for prefab in document.prefabs.values():  # previews drawn by the loading thread
        assert cached_prefab_pixmap(prefab, PREVIEW_SIZE) is not None
    QtWidgets.QApplication.processEvents()
    assert (
        window.findChild(LoadingScreen) is None or not window.findChild(LoadingScreen).isVisible()
    )
    document.dirty = False
    window.close()


def test_loading_can_be_cancelled_and_the_old_world_stays(app: object) -> None:
    from redsim.ui.loading import LoadingRun
    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    before = window.document
    outcome: list[object] = []

    def slow(progress: object) -> None:
        for i in range(1000):
            progress("world", i, 1000)  # type: ignore[operator]
            time.sleep(0.005)

    run = LoadingRun(
        window, "Loading world", "slow", ["world"], slow, outcome.append, outcome.append
    )
    run.cancel()
    run.wait()
    assert outcome == [None] and window.document is before  # cancelled: nothing changes
    window.close()


def test_the_loading_screen_takes_the_input_and_esc_cancels(app: object) -> None:
    from redsim.ui.loading import LoadingScreen

    parent = QtWidgets.QWidget()
    parent.resize(400, 300)
    screen = LoadingScreen(parent, "Loading world", "test")
    asked: list[bool] = []
    screen.cancel_requested.connect(lambda: asked.append(True))
    space = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier)
    assert screen.eventFilter(parent, space)  # swallowed: no shortcut runs while loading
    assert not asked
    escape = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    assert screen.eventFilter(parent, escape) and asked == [True]
    parent.resize(500, 320)
    screen.eventFilter(parent, QEvent(QEvent.Type.Resize))
    assert screen.size() == parent.size()  # covers the whole window
    screen.show_progress("Building the view: 3 of 9 chunks", 0.5)
    assert not screen.grab().isNull()
    screen.close_screen()


def test_previews_skip_hidden_blocks_and_are_cached_by_prefab(app: object) -> None:
    from redsim.ui.icons import _visible_blocks, cached_prefab_pixmap, prefab_pixmap

    stone, lamp = blocks.STONE.default_state, blocks.parse_state("redstone_lamp")
    states = {(0, 0, 0): lamp, (1, 1, 1): stone, (2, 0, 0): lamp}
    visible = _visible_blocks(states, {(1, 1, 1)})
    assert set(visible) == {(1, 1, 1), (2, 0, 0)}  # the lamp behind the stone is hidden
    doc = Document.new_flat()
    doc.setblock((0, 1, 0), lamp)
    prefab = doc.save_prefab("one", Region((0, 1, 0), (0, 1, 0)))
    assert cached_prefab_pixmap(prefab, 40) is None
    first = prefab_pixmap(prefab, 40)
    assert cached_prefab_pixmap(prefab, 40) is first and prefab_pixmap(prefab, 40) is first
