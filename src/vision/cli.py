"""Command-line interface for vision."""

from __future__ import annotations

import argparse
from typing import Sequence

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="vision",
        description="Vision CLI"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print the version and exit.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the main program."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(f"Vision {__version__}")
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
