# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
"""Command-line interface for vision."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from . import __version__, evaluator, webcam
from .config import get_config

_ = get_config()


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the CLI."""
    parser = argparse.ArgumentParser(prog="latvision", description="Latency Vision CLI")
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print the version and exit.",
    )

    subparsers = parser.add_subparsers(dest="command")
    webcam_parser = subparsers.add_parser("webcam", help="Run the webcam capture loop.")
    webcam_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip the webcam loop and print a message instead.",
    )
    webcam_parser.add_argument(
        "--use-fake-detector",
        action="store_true",
        help="Run the webcam loop with the FakeDetector stub.",
    )

    eval_parser = subparsers.add_parser("eval", help="Run evaluator over images.")
    eval_parser.add_argument("--input", required=True, help="Dir of images")
    eval_parser.add_argument("--output", required=True, help="Dir for artifacts")
    eval_parser.add_argument(
        "--warmup",
        type=int,
        default=100,
        help="Number of warmup frames to skip",
    )
    eval_parser.add_argument(
        "--sustain-minutes",
        type=int,
        default=0,
        help="Run for N minutes (wall clock); 0 disables sustained mode",
    )
    eval_parser.add_argument(
        "--budget-ms",
        type=int,
        default=33,
        help="Latency budget for SLO tracking",
    )
    eval_parser.add_argument(
        "--fixture-manifest",
        type=str,
        default=None,
        help="Path to JSON manifest with eval settings (e.g., unknown_band).",
    )
    eval_parser.add_argument(
        "--unknown-rate-band",
        type=str,
        default="0.10,0.40",
        help="Fallback band for unknown rate as LOW,HIGH (overridden by manifest).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the main program."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(f"Latency Vision {__version__}")
    elif args.command == "webcam":
        webcam.loop(dry_run=args.dry_run, use_fake=args.use_fake_detector)
    elif args.command == "eval":
        try:
            import numpy  # noqa: F401
            from PIL import Image  # noqa: F401
        except Exception:
            print(
                (
                    "latvision eval requires numpy and pillow. "
                    "Install with: pip install numpy pillow "
                    "(or run pip install -e .)."
                ),
                file=sys.stderr,
            )
            return 3
        low, high = (float(x) for x in args.unknown_rate_band.split(",", 1))
        ret = evaluator.run_eval(
            args.input,
            args.output,
            args.warmup,
            budget_ms=args.budget_ms,
            sustain_minutes=args.sustain_minutes,
            fixture_manifest=args.fixture_manifest,
            unknown_band=(low, high),
        )
        sys.exit(ret)
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
