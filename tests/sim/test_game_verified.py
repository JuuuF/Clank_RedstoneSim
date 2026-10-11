"""Replay recordings from the real 26.3 server (experiments/results/*.json) offline.

Each recording was made by ``python -m tools.gameserver.run``: the same scenario ran in the
sandboxed dedicated server and in the simulator, and the game's block states were captured
after every tick. These tests re-run the simulator and require it to reproduce the game's
states exactly, so they guard game-verified behavior without needing the server.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

import pytest

from tools.gameserver.compare import run_sim
from tools.gameserver.scenarios import lookup

RESULTS_DIR = Path(__file__).resolve().parents[2] / "experiments" / "results"
RESULTS = sorted([*RESULTS_DIR.glob("*.json"), *RESULTS_DIR.glob("*.json.gz")])


def load(path: Path) -> dict[str, Any]:
    raw = gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()
    data: dict[str, Any] = json.loads(raw)
    return data


@pytest.mark.parametrize("path", RESULTS, ids=[p.name.split(".")[0] for p in RESULTS])
def test_simulator_reproduces_game_recording(path: Path) -> None:
    data = load(path)
    scenario = lookup(data["scenario"])
    assert data["fingerprint"] == scenario.fingerprint(), "recording is stale: re-run the server"
    assert data["match"], "the recording itself documents a mismatch"
    x, y, z = data["origin"]
    frames = run_sim(scenario, (x, y, z), data["start_time"])
    assert len(frames) == len(data["frames"])
    for frame, recorded in zip(frames, data["frames"], strict=True):
        assert frame == recorded["game"], f"tick {recorded['tick']}"


def test_recordings_exist() -> None:
    assert {load(p)["scenario"] for p in RESULTS} >= {
        "lamp_redstone_block",
        "torch_inverter",
        "wire_line_lamp",
        "and_gate",
        "torch_burnout",
    }
