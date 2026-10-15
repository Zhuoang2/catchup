"""Draw the C7 mark with the Python standard library, reproducibly."""

import argparse
import struct
import zlib
from pathlib import Path

BG = (0xF4, 0xF0, 0xE6)
FG = (0x15, 0x14, 0x12)


def chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(
        ">I", zlib.crc32(kind + data) & 0xFFFFFFFF
    )


def pixel(x: int, y: int, size: int, maskable: bool) -> tuple[int, int, int]:
    # The maskable mark stays entirely within the central 80% safe zone.
    left = int(size * (0.21 if maskable else 0.16))
    right = size - left
    top = left
    bottom = right
    if not (left <= x < right and top <= y < bottom):
        return BG
    width = right - left
    bar_left, bar_right = left + int(width * .23), right - int(width * .23)
    bar_height = max(1, int(width * .055))
    for bar_y in (top + int(width * .38), top + int(width * .57)):
        if bar_left <= x < bar_right and bar_y <= y < bar_y + bar_height:
            return BG
    return FG


def png(size: int, maskable: bool = False) -> bytes:
    image = bytearray()
    for y in range(size):
        image.append(0)  # PNG filter: none
        for x in range(size):
            image.extend(pixel(x, y, size, maskable))
    header = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return header + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(image), 9)) + chunk(b"IEND", b"")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "public")
    output = parser.parse_args().output
    output.mkdir(parents=True, exist_ok=True)
    for size in (192, 512, 1024):
        (output / f"icon-{size}.png").write_bytes(png(size))
    (output / "icon-maskable-512.png").write_bytes(png(512, maskable=True))
    (output / "icon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">'
        '<rect width="1024" height="1024" fill="#f4f0e6"/>'
        '<rect x="164" y="164" width="696" height="696" fill="#151412"/>'
        '<path d="M324 430h376M324 562h376" stroke="#f4f0e6" stroke-width="38"/>'
        '</svg>\n', encoding="utf-8"
    )


if __name__ == "__main__":
    main()
