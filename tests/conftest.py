"""Shared pytest configuration."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.jdk import find_jdk_tool

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def java_oracle(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Compile tools/java_oracle and return the class directory (skip if no JDK)."""
    javac = find_jdk_tool("javac")
    java = find_jdk_tool("java")
    if javac is None or java is None:
        pytest.skip("no JDK available for the Java oracle")
    out = tmp_path_factory.mktemp("oracle")
    source = REPO_ROOT / "tools" / "java_oracle" / "HashOrderOracle.java"
    result = subprocess.run([javac, "-d", str(out), str(source)], capture_output=True, text=True)
    if result.returncode != 0:
        pytest.skip(f"javac failed: {result.stderr.strip()[:200]}")
    return out


@pytest.fixture(autouse=True)
def _private_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Never read or write the user's real preferences, keymap or recent blocks."""
    monkeypatch.setenv("REDSIM_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("REDSIM_KEYMAP", str(tmp_path / "config" / "keymap.json"))
