"""Locate JDK tools for the Java oracle tests."""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def find_jdk_tool(name: str) -> str | None:
    """Locate a JDK tool (javac/java), preferring a Java 25 JDK like the game's runtime."""
    candidates = [
        os.environ.get("REDSIM_JDK_HOME", ""),
        "/usr/lib/jvm/java-25-openjdk",
        "/usr/lib/jvm/default",
    ]
    for home in candidates:
        if home and (Path(home) / "bin" / name).exists():
            return str(Path(home) / "bin" / name)
    return shutil.which(name)
