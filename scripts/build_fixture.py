# SPDX-License-Identifier: Apache-2.0
import argparse
import pathlib
import random

from PIL import Image, ImageDraw


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    args = ap.parse_args()

    random.seed(args.seed)
    args.out.mkdir(parents=True, exist_ok=True)

    for i in range(2000):
        img = Image.new(
            "RGB",
            (96, 96),
            ((i * 7) % 255, (i * 13) % 255, (i * 29) % 255),
        )
        d = ImageDraw.Draw(img)
        x = 8 + (i % 24)
        d.rectangle((x, 10, x + 48, 58), outline=(255, 255, 255))
        img.save(args.out / f"{i:06d}.png")


if __name__ == "__main__":
    main()
