#!/usr/bin/env python3
"""Generate a deterministic set of PNG frames for benchmarking."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import struct
import zlib
from pathlib import Path
from typing import cast


def _chunk(tag: bytes, data: bytes) -> bytes:
    """Create a PNG chunk with *tag* and *data*."""

    return (
        struct.pack("!I", len(data))
        + tag
        + data
        + struct.pack("!I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def _solid_png(width: int, height: int, color: tuple[int, int, int]) -> bytes:
    """Return PNG bytes for an RGB image of *width*×*height* filled with *color*."""

    r, g, b = color
    row = b"\x00" + bytes([r, g, b]) * width
    raw = row * height
    comp = zlib.compress(raw)
    header = _chunk(b"IHDR", struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0))
    data = _chunk(b"IDAT", comp)
    end = _chunk(b"IEND", b"")
    return b"\x89PNG\r\n\x1a\n" + header + data + end


def build_fixture(out: Path, n: int, seed: int) -> None:
    random.seed(seed)
    out.mkdir(parents=True, exist_ok=True)
    for idx in range(n):
        color = cast(tuple[int, int, int], tuple(random.randint(0, 255) for _ in range(3)))
        png = _solid_png(640, 640, color)
        (out / f"frame_{idx:04d}.png").write_bytes(png)

    files = sorted(out.glob("frame_*.png"))
    file_names = [f.name for f in files]
    transforms: list[str] = []
    h = hashlib.sha256()
    h.update(str(seed).encode("utf-8"))
    for name in file_names:
        h.update(name.encode("utf-8"))
    h.update(json.dumps(transforms, sort_keys=True).encode("utf-8"))
    manifest = {
        "seed": seed,
        "ids": file_names,
        "transforms": transforms,
        "fixture_hash": h.hexdigest(),
        # Synthetic generator → all detections resolve to unknown in stubs.
        # Use a permissive band so CI doesn’t fail until we switch to a real fixture.
        "unknown_rate_band": [0.0, 1.0],
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path, help="output directory")
    parser.add_argument("--n", type=int, default=400, help="number of frames")
    parser.add_argument("--seed", type=int, default=42, help="random seed")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_fixture(args.out, args.n, args.seed)
    print(f"Wrote {args.n} frames to {args.out}")


if __name__ == "__main__":
    main()
