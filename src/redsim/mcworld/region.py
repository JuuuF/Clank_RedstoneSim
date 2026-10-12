"""Region files (``r.<x>.<z>.mca``, ``RegionFile``): 32×32 chunks each, stored as
compressed NBT in 4 KiB sectors behind an 8 KiB header (locations and timestamps)."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path
from typing import Any

from redsim.mcworld import nbt

SECTOR = 4096
#: Compression ids of a chunk's payload (``RegionFileVersion``).
GZIP, ZLIB, NONE, LZ4 = 1, 2, 3, 4
EXTERNAL = 128  # the payload lives in a separate .mcc file


def region_of(chunk_x: int, chunk_z: int) -> tuple[int, int]:
    return chunk_x >> 5, chunk_z >> 5


class RegionFile:
    """Read access to one region file; the header is read once, chunks on demand."""

    def __init__(self, path: Path) -> None:
        self.path = path
        with open(path, "rb") as handle:
            header = handle.read(2 * SECTOR)
        if len(header) < 2 * SECTOR:
            header = header.ljust(2 * SECTOR, b"\0")
        self.locations = struct.unpack(">1024I", header[:SECTOR])
        self.timestamps = struct.unpack(">1024I", header[SECTOR:])

    @staticmethod
    def index(chunk_x: int, chunk_z: int) -> int:
        return (chunk_x & 31) + (chunk_z & 31) * 32

    def has_chunk(self, chunk_x: int, chunk_z: int) -> bool:
        return self.locations[self.index(chunk_x, chunk_z)] != 0

    def chunks(self) -> list[tuple[int, int]]:
        """Chunk coordinates (relative, 0–31) of the chunks stored in this file."""
        return [(i & 31, i >> 5) for i, loc in enumerate(self.locations) if loc]

    def read_raw(self, chunk_x: int, chunk_z: int) -> tuple[int, bytes] | None:
        """(compression id, compressed payload) of a chunk, or None if it is absent."""
        location = self.locations[self.index(chunk_x, chunk_z)]
        if location == 0:
            return None
        offset, sectors = (location >> 8) * SECTOR, location & 0xFF
        with open(self.path, "rb") as handle:
            handle.seek(offset)
            data = handle.read(sectors * SECTOR)
        length, compression = struct.unpack(">IB", data[:5])
        payload = data[5 : 4 + length]
        if compression & EXTERNAL:
            mcc = self.path.parent / f"c.{chunk_x}.{chunk_z}.mcc"
            payload = mcc.read_bytes()
            compression &= ~EXTERNAL
        return compression, payload

    def read_chunk(self, chunk_x: int, chunk_z: int) -> dict[str, Any] | None:
        """A chunk's NBT root, or None if the region does not hold it."""
        raw = self.read_raw(chunk_x, chunk_z)
        if raw is None:
            return None
        compression, payload = raw
        if compression == ZLIB:
            data = zlib.decompress(payload)
        elif compression == GZIP:
            data = nbt.decompress(payload)
        elif compression == NONE:
            data = payload
        else:
            raise ValueError(f"chunk compression {compression} is not supported (LZ4?)")
        return nbt.loads(data)[1]
