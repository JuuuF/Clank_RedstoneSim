"""Binary NBT (``NbtIo``), the format of ``level.dat``, player files and chunks.

Tags map to Python values, and back: compound → ``dict``, list → ``NbtList`` (a ``list``
that remembers its element type, so empty lists round-trip), strings → ``str``, numeric
arrays → ``NbtArray`` (with their kind), and numbers → ``Byte``/``Short``/``Int``/``Long``/
``Float``/``Double`` wrappers, so a value written back has the tag type it was read with.
Strings use Java's modified UTF-8 (surrogate pairs; NUL as two bytes).
"""

from __future__ import annotations

import gzip
import io
import struct
import zlib
from typing import Any, BinaryIO

END, BYTE, SHORT, INT, LONG, FLOAT, DOUBLE = 0, 1, 2, 3, 4, 5, 6
BYTE_ARRAY, STRING, LIST, COMPOUND, INT_ARRAY, LONG_ARRAY = 7, 8, 9, 10, 11, 12


class _Number:
    """A number that remembers its NBT tag type."""

    tag = 0
    __slots__ = ()


class Byte(int, _Number):
    tag = BYTE


class Short(int, _Number):
    tag = SHORT


class Int(int, _Number):
    tag = INT


class Long(int, _Number):
    tag = LONG


class Float(float, _Number):
    tag = FLOAT


class Double(float, _Number):
    tag = DOUBLE


class NbtList(list[Any]):
    """A list tag: its element type is kept (needed for empty lists)."""

    def __init__(self, items: Any = (), element: int = END) -> None:
        super().__init__(items)
        self.element = element


class NbtArray(list[Any]):
    """A byte, int or long array tag."""

    def __init__(self, items: Any = (), kind: int = INT_ARRAY) -> None:
        super().__init__(items)
        self.kind = kind


_NUMBERS: dict[int, tuple[str, type]] = {
    BYTE: (">b", Byte),
    SHORT: (">h", Short),
    INT: (">i", Int),
    LONG: (">q", Long),
    FLOAT: (">f", Float),
    DOUBLE: (">d", Double),
}
_ARRAYS = {BYTE_ARRAY: "b", INT_ARRAY: "i", LONG_ARRAY: "q"}


# ---------------------------------------------------------------------- reading
class _Reader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.pos = 0

    def take(self, size: int) -> bytes:
        chunk = self.data[self.pos : self.pos + size]
        if len(chunk) != size:
            raise ValueError("truncated NBT data")
        self.pos += size
        return chunk

    def unpack(self, fmt: str) -> Any:
        size = struct.calcsize(fmt)
        return struct.unpack(fmt, self.take(size))[0]

    def string(self) -> str:
        return decode_mutf8(self.take(self.unpack(">H")))

    def payload(self, tag: int) -> Any:
        if tag in _NUMBERS:
            fmt, cls = _NUMBERS[tag]
            return cls(self.unpack(fmt))
        if tag == STRING:
            return self.string()
        if tag in _ARRAYS:
            count = self.unpack(">i")
            code = _ARRAYS[tag]
            values = struct.unpack(f">{count}{code}", self.take(count * struct.calcsize(code)))
            return NbtArray(values, tag)
        if tag == LIST:
            element = self.unpack(">b")
            count = self.unpack(">i")
            return NbtList((self.payload(element) for _ in range(count)), element)
        if tag == COMPOUND:
            result: dict[str, Any] = {}
            while True:
                child = self.unpack(">b")
                if child == END:
                    return result
                name = self.string()
                result[name] = self.payload(child)
        raise ValueError(f"unknown NBT tag type {tag}")


def decode_mutf8(raw: bytes) -> str:
    """Java's modified UTF-8: NUL as C0 80, and characters outside the BMP as surrogate
    pairs encoded separately."""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.replace(b"\xc0\x80", b"\x00").decode("utf-8", "surrogatepass")
        return text.encode("utf-16", "surrogatepass").decode("utf-16")


def encode_mutf8(text: str) -> bytes:
    out = bytearray()
    for char in text:
        code = ord(char)
        if code == 0:
            out += b"\xc0\x80"
        elif code < 0x80:
            out.append(code)
        elif code < 0x10000:
            out += char.encode("utf-8", "surrogatepass")
        else:  # a surrogate pair, each half encoded as three bytes
            code -= 0x10000
            for half in (0xD800 + (code >> 10), 0xDC00 + (code & 0x3FF)):
                out += chr(half).encode("utf-8", "surrogatepass")
    return bytes(out)


def loads(data: bytes) -> tuple[str, dict[str, Any]]:
    """Uncompressed NBT bytes → (root name, root compound)."""
    reader = _Reader(data)
    tag = reader.unpack(">b")
    if tag != COMPOUND:
        raise ValueError("the NBT root is not a compound")
    name = reader.string()
    return name, reader.payload(COMPOUND)


def decompress(data: bytes) -> bytes:
    """Gzip or zlib compressed (or plain) NBT bytes."""
    if data[:2] == b"\x1f\x8b":
        return gzip.decompress(data)
    if data[:1] == b"\x78":
        return zlib.decompress(data)
    return data


def read_file(path: Any) -> dict[str, Any]:
    """A gzipped NBT file (``level.dat``, player data) → its root compound."""
    with open(path, "rb") as handle:
        return loads(decompress(handle.read()))[1]


# ---------------------------------------------------------------------- writing
def tag_of(value: Any) -> int:
    if isinstance(value, _Number):
        return value.tag
    if isinstance(value, bool):
        return BYTE
    if isinstance(value, int):
        return INT
    if isinstance(value, float):
        return DOUBLE
    if isinstance(value, str):
        return STRING
    if isinstance(value, NbtArray):
        return value.kind
    if isinstance(value, list):
        return LIST
    if isinstance(value, dict):
        return COMPOUND
    raise TypeError(f"cannot write {type(value).__name__} as NBT")


def _write_string(out: BinaryIO, text: str) -> None:
    raw = encode_mutf8(text)
    out.write(struct.pack(">H", len(raw)))
    out.write(raw)


def _write_payload(out: BinaryIO, tag: int, value: Any) -> None:
    if tag in _NUMBERS:
        out.write(struct.pack(_NUMBERS[tag][0], value))
    elif tag == STRING:
        _write_string(out, value)
    elif tag in _ARRAYS:
        out.write(struct.pack(">i", len(value)))
        out.write(struct.pack(f">{len(value)}{_ARRAYS[tag]}", *value))
    elif tag == LIST:
        element = getattr(value, "element", END)
        if value:
            element = tag_of(value[0]) if element == END else element
        out.write(struct.pack(">bi", element, len(value)))
        for item in value:
            _write_payload(out, element, item)
    elif tag == COMPOUND:
        for name, child in value.items():
            child_tag = tag_of(child)
            out.write(struct.pack(">b", child_tag))
            _write_string(out, name)
            _write_payload(out, child_tag, child)
        out.write(b"\x00")
    else:
        raise ValueError(f"unknown NBT tag type {tag}")


def dumps(root: dict[str, Any], name: str = "") -> bytes:
    """A root compound → uncompressed NBT bytes."""
    out = io.BytesIO()
    out.write(struct.pack(">b", COMPOUND))
    _write_string(out, name)
    _write_payload(out, COMPOUND, root)
    return out.getvalue()


def write_file(path: Any, root: dict[str, Any], name: str = "") -> None:
    """Write a gzipped NBT file."""
    with open(path, "wb") as handle:
        handle.write(gzip.compress(dumps(root, name)))
