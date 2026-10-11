"""Preferences: defaults, round trip, clamping, broken files."""

from __future__ import annotations

from pathlib import Path

import pytest

from redsim.ui.preferences import Preferences


def test_preferences_round_trip_and_clamp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDSIM_CONFIG_DIR", str(tmp_path))
    assert Preferences.load() == Preferences()  # no file: defaults
    prefs = Preferences(xray_building_alpha=0.3, xray_circuit_alpha=0.6)
    prefs.save()
    assert Preferences.load() == prefs
    Preferences.path().write_text('{"xray_building_alpha": 7, "xray_circuit_alpha": "x"}')
    loaded = Preferences.load()
    assert loaded.xray_building_alpha == 1.0  # clamped
    assert loaded.xray_circuit_alpha == Preferences().xray_circuit_alpha  # invalid: default
    Preferences.path().write_text("{broken")
    assert Preferences.load() == Preferences()
