#!/usr/bin/env python3
"""Generate a deterministic set of PNG frames for benchmarking."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


def build_fixture(
    out: Path,
    n: int,
    Image: Any,
    ImageDraw: Any,
    ImageFont: Any,
) -> None:
    out.mkdir(parents=True, exist_ok=True)
    width, height = 640, 640
    font = ImageFont.load_default()
    for idx in range(n):
        img = Image.new("RGB", (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), str(idx), fill=(0, 0, 0), font=font)
        img.save(out / f"frame_{idx:04d}.png")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path, help="output directory")
    parser.add_argument("--n", type=int, default=400, help="number of frames")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ModuleNotFoundError:  # pragma: no cover - explicit exit
        print("Missing dependency: pillow", file=sys.stderr)
        sys.exit(3)
    try:
        build_fixture(args.out, args.n, Image, ImageDraw, ImageFont)
    except Exception as err:  # pragma: no cover - user errors
        print(str(err), file=sys.stderr)
        sys.exit(2)
    print(f"Wrote {args.n} frames to {args.out}")


if __name__ == "__main__":
    main()
