# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
"""Command-line interface for latency_vision."""

from __future__ import annotations

import argparse
import os
import sys
import time
from collections.abc import Sequence
from pathlib import Path

from . import __version__, evaluator, webcam
from .config import get_config

_ = get_config()

_ALIAS_WARNED = False


def _warn_alias_once() -> None:
    """Emit the deprecated alias warning once per process."""
    global _ALIAS_WARNED
    if _ALIAS_WARNED:
        return
    if os.getenv("VISION_SILENCE_DEPRECATION") == "1":
        return

    argv0 = Path(sys.argv[0]).name
    if argv0 == "vision" or (__package__ == "vision" and argv0 == "__main__.py"):
        msg = (
            "[deprecation] 'vision' is an alias of 'latvision' and will be removed in M1.2. "
            "Use 'latvision'."
        )
        print(msg, file=sys.stderr)
        _ALIAS_WARNED = True


def _cpu_flags() -> str:
    """Best-effort detection of CPU SIMD flags."""
    try:
        if sys.platform.startswith("linux") and Path("/proc/cpuinfo").exists():
            text = Path("/proc/cpuinfo").read_text().lower()
            for flag in ("avx512", "avx2", "avx", "neon", "sse4_2"):
                if flag in text:
                    return flag
            return "unknown"
    except Exception:
        pass
    return "unknown"


def _detect_backend() -> str:
    """Return the available matcher backend without importing heavy modules."""
    import importlib.util as _imputil

    if _imputil.find_spec("faiss") is not None:
        return "faiss"
    if _imputil.find_spec("numpy") is not None:
        return "numpy"
    return "none"


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
        "--duration-min",
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
        "--unknown-rate-band",
        type=str,
        default="",
        help=(
            "Unknown rate band as LOW,HIGH. If omitted, uses fixture manifest; "
            "if no manifest, defaults to 0.10,0.40."
        ),
    )

    subparsers.add_parser("hello", help="Print environment information.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the main program."""
    t0_process_ns = time.monotonic_ns()
    _warn_alias_once()
    parser = build_parser()
    args = parser.parse_args(argv)
    args._t0_process = t0_process_ns

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
        band_arg: tuple[float, float] | None
        if args.unknown_rate_band.strip():
            low, high = (float(x) for x in args.unknown_rate_band.split(",", 1))
            band_arg = (low, high)
        else:
            band_arg = None
        ret = evaluator.run_eval(
            args.input,
            args.output,
            args.warmup,
            budget_ms=args.budget_ms,
            duration_min=args.duration_min,
            unknown_rate_band=band_arg,
            process_start_ns=args._t0_process,
        )
        sys.exit(ret)
    elif args.command == "hello":
        import platform

        os_info = platform.platform()
        py_info = platform.python_version()
        flags = _cpu_flags()
        backend = _detect_backend()
        print(f"Latency Vision {__version__}")
        print(f"OS: {os_info}")
        print(f"Python: {py_info}")
        print(f"CPU: {flags}")
        print(f"Backend: {backend}")
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
